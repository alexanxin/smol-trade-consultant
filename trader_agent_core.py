import os
import json
import asyncio
import aiohttp
import pandas as pd
# import pandas_ta as ta  # Using pandas_ta if available, or standard ta
import numpy as np
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
import ta as technical_analysis_lib # Fallback to original library
import subprocess

# Load environment variables
load_dotenv()

class TraderAgent:
    def __init__(self):
        self.birdeye_api_key = os.getenv("BIRDEYE_API_KEY")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.coingecko_api_key = os.getenv("COINGECKO_API_KEY")
        self.coinmarketcap_api_key = os.getenv("COINMARKETCAP_API_KEY")
        self.headers_birdeye = {"X-API-KEY": self.birdeye_api_key}
        self.headers_coingecko = {"x-cg-demo-api-key": self.coingecko_api_key}
        self.headers_coinmarketcap = {"X-CMC_PRO_API_KEY": self.coinmarketcap_api_key}

    async def fetch_data(self, token_symbol: str, chain: str = "solana"):
        """
        Fetches market data and OHLCV data asynchronously.
        """
        token_address = await self._get_token_address(token_symbol, chain)
        if not token_address:
            return {"error": f"Token address not found for {token_symbol}"}, {}

        async with aiohttp.ClientSession() as session:
            # Fetch Market Data (Birdeye)
            market_data_task = self._fetch_birdeye_market_data(session, token_address, chain)

            # Try CoinGecko first for pool/OHLCV data
            pool_address = await self._get_top_pool_coingecko(session, token_address, chain)

            # If CoinGecko fails and we have CoinMarketCap key, try fallback
            if not pool_address and self.coinmarketcap_api_key:
                print("CoinGecko pool lookup failed, trying CoinMarketCap fallback...")
                pool_address = await self._get_top_pool_coinmarketcap(session, token_address, chain)

            market_data = await market_data_task

            if not pool_address:
                print("No pool data available from any provider")
                return market_data, {"ltf": [], "htf": [], "daily": []}

            # Fetch OHLCV for multiple timeframes concurrently
            # Note: OHLCV fallback is handled within _fetch_ohlcv_coingecko
            ohlcv_tasks = {
                "ltf": self._fetch_ohlcv_coingecko(session, pool_address, chain, "minute", 5, 100),
                "htf": self._fetch_ohlcv_coingecko(session, pool_address, chain, "hour", 1, 50),
                "daily": self._fetch_ohlcv_coingecko(session, pool_address, chain, "day", 1, 30)
            }

            ohlcv_results = await asyncio.gather(*ohlcv_tasks.values())
            ohlcv_data = dict(zip(ohlcv_tasks.keys(), ohlcv_results))

            return market_data, ohlcv_data

    async def _get_token_address(self, symbol: str, chain: str):
        # ... (Implementation similar to original but async or simplified if possible)
        # For now, we can reuse the logic or call the synchronous helper if needed, 
        # but ideally we want this async too. 
        # Simplified lookup for common tokens to avoid API calls
        common_tokens = {
            "solana": {"SOL": "So11111111111111111111111111111111111111112"},
            "ethereum": {"ETH": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"},
            "bsc": {"BNB": "0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c"}
        }
        if chain in common_tokens and symbol.upper() in common_tokens[chain]:
            return common_tokens[chain][symbol.upper()]
            
        # TODO: Implement full async token lookup if needed. 
        # For this iteration, we'll assume the user provides valid inputs or we use a synchronous fallback wrapper 
        # if we strictly need to keep the exact same lookup logic.
        # Let's implement a basic async Birdeye lookup.
        url = f"https://public-api.birdeye.so/public/tokenlist?includeNFT=false&chain={chain}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=self.headers_birdeye) as response:
                    if response.status == 200:
                        data = await response.json()
                        for token in data.get('data', []):
                            if token.get('symbol', '').upper() == symbol.upper():
                                return token.get('address')
            except Exception as e:
                print(f"Error fetching token address: {e}")
        return None

    async def _fetch_birdeye_market_data(self, session, token_address, chain):
        url = f"https://public-api.birdeye.so/defi/price?address={token_address}&include_liquidity=true&ui_amount_mode=raw"
        headers = {"X-API-KEY": self.birdeye_api_key, "X-CHAIN": chain}
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('data', {})
        except Exception as e:
            print(f"Error fetching Birdeye data: {e}")
        return {}

    async def _get_top_pool_coingecko(self, session, token_address, network):
        network_map = {
            'solana': 'solana',
            'ethereum': 'eth',
            'bsc': 'bsc-mainnet',
            'polygon': 'polygon-pos-mainnet'
        }
        mapped_network = network_map.get(network, network)
        url = f"https://api.coingecko.com/api/v3/onchain/networks/{mapped_network}/tokens/{token_address}/pools"
        
        try:
            async with session.get(url, headers=self.headers_coingecko) as response:
                if response.status == 200:
                    data = await response.json()
                    pools = data.get('data', [])
                    if pools:
                        return pools[0].get('attributes', {}).get('address') or pools[0].get('id')
        except Exception as e:
            print(f"Error fetching pool: {e}")
        return None

    async def _fetch_ohlcv_coingecko(self, session, pool_address, network, timeframe, aggregate, limit):
        network_map = {
            'solana': 'solana',
            'ethereum': 'eth',
            'bsc': 'bsc-mainnet',
            'polygon': 'polygon-pos-mainnet'
        }
        mapped_network = network_map.get(network, network)
        clean_pool_address = pool_address.split('_', 1)[1] if '_' in pool_address else pool_address
        
        url = f"https://api.coingecko.com/api/v3/onchain/networks/{mapped_network}/pools/{clean_pool_address}/ohlcv/{timeframe}?aggregate={aggregate}&limit={limit}"
        
        try:
            async with session.get(url, headers=self.headers_coingecko) as response:
                if response.status == 200:
                    data = await response.json()
                    ohlcv_list = data.get('data', {}).get('attributes', {}).get('ohlcv_list', [])
                    formatted_data = []
                    for item in ohlcv_list:
                        if len(item) >= 6:
                            formatted_data.append({
                                't': int(item[0]),
                                'o': float(item[1]),
                                'h': float(item[2]),
                                'l': float(item[3]),
                                'c': float(item[4]),
                                'v': float(item[5])
                            })
                    return formatted_data
        except Exception as e:
            print(f"Error fetching OHLCV from CoinGecko: {e}")
            # Try CoinMarketCap as fallback
            if self.coinmarketcap_api_key:
                print("Falling back to CoinMarketCap for OHLCV data...")
                return await self._fetch_ohlcv_coinmarketcap(session, token_address, network, timeframe, aggregate, limit)
        return []

    async def _get_top_pool_coinmarketcap(self, session, token_address, network):
        """
        Fallback method using CoinMarketCap API to get pool data.
        Note: CMC doesn't have the same pool-level data as CoinGecko, so this is limited.
        """
        # CoinMarketCap doesn't have detailed pool data like CoinGecko
        # We'll try to get basic OHLCV data directly if possible
        print("CoinMarketCap fallback: Pool data not available, trying direct OHLCV...")
        return None

    async def _fetch_ohlcv_coinmarketcap(self, session, token_address, network, timeframe, aggregate, limit):
        """
        Fallback method using CoinMarketCap API for OHLCV data.

        IMPORTANT: CoinMarketCap's free/basic plan does NOT include historical OHLCV data.
        They only provide current price data, not historical candlestick data needed for technical analysis.

        This method will return empty data to indicate CMC cannot provide OHLCV data.
        """
        print("⚠️ CoinMarketCap OHLCV: Free plan does not support historical OHLCV data")
        print("   Only current price data is available, not suitable for technical analysis")
        print("   Consider upgrading to CoinMarketCap Pro plan for historical data")
        return []

    def analyze_market(self, market_data: Dict, ohlcv_data: Dict) -> Dict:
        """
        Performs comprehensive technical analysis on the fetched data.
        """
        analysis_result = {
            "market_data": market_data,
            "technical_analysis": {}
        }
        
        for timeframe, data in ohlcv_data.items():
            if not data:
                continue
                
            df = pd.DataFrame(data)
            # Ensure correct types
            df['t'] = pd.to_numeric(df['t'])
            df['o'] = pd.to_numeric(df['o'])
            df['h'] = pd.to_numeric(df['h'])
            df['l'] = pd.to_numeric(df['l'])
            df['c'] = pd.to_numeric(df['c'])
            df['v'] = pd.to_numeric(df['v'])
            
            # Vectorized Calculations
            analysis_result["technical_analysis"][timeframe] = {
                "rsi": self._calculate_rsi(df),
                "macd": self._calculate_macd(df),
                "fvgs": self._calculate_fvgs_vectorized(df),
                "order_blocks": self._calculate_order_blocks_vectorized(df),
                "market_structure": self._calculate_market_structure_vectorized(df),
                "volume_profile": self._calculate_volume_profile(df),
                "candlestick_patterns": self._detect_candlestick_patterns(df),
                "fibonacci": self._calculate_fibonacci_levels(df)
            }
            
        # Fabio Valentino Specific Analysis
        analysis_result["fabio_analysis"] = self._perform_fabio_analysis(analysis_result["technical_analysis"])
        
        return analysis_result

    def _calculate_rsi(self, df, window=14):
        return technical_analysis_lib.momentum.rsi(df['c'], window=window).iloc[-1]

    def _calculate_macd(self, df):
        macd = technical_analysis_lib.trend.MACD(df['c'])
        return {
            "line": macd.macd().iloc[-1],
            "signal": macd.macd_signal().iloc[-1],
            "hist": macd.macd_diff().iloc[-1]
        }

    def _calculate_fvgs_vectorized(self, df):
        """
        Vectorized Fair Value Gap calculation with mitigation check.
        Only returns ACTIVE (unfilled) FVGs.
        """
        if len(df) < 3:
            return []

        highs = df['h'].values
        lows = df['l'].values
        closes = df['c'].values
        opens = df['o'].values
        
        # We need to look at i-2, i-1, i
        # Bullish FVG: (i-2) High < (i) Low
        # Bearish FVG: (i-2) Low > (i) High
        
        fvgs = []
        min_gap_percent = 0.001  # 0.1% minimum gap size
        
        # Iterate through candles starting from index 2
        for i in range(2, len(df)):
            # 1. Check for Bullish FVG
            if highs[i-2] < lows[i]:
                gap_size = lows[i] - highs[i-2]
                gap_percent = gap_size / highs[i-2]
                
                if gap_percent >= min_gap_percent:
                    # Check for mitigation in subsequent candles
                    is_mitigated = False
                    # Look at all candles AFTER i (i+1 to end)
                    for j in range(i + 1, len(df)):
                        # If a future candle's Low goes below the FVG Top (lows[i]), it starts filling
                        # If it goes below FVG Bottom (highs[i-2]), it's fully filled/invalidated
                        if lows[j] <= highs[i-2]:
                            is_mitigated = True
                            break
                    
                    if not is_mitigated:
                        fvgs.append({
                            "type": "bullish",
                            "top": float(lows[i]),
                            "bottom": float(highs[i-2]),
                            "index": int(i-1), # Gap is at the middle candle
                            "size_pct": float(gap_percent * 100)
                        })

            # 2. Check for Bearish FVG
            elif lows[i-2] > highs[i]:
                gap_size = lows[i-2] - highs[i]
                gap_percent = gap_size / highs[i]
                
                if gap_percent >= min_gap_percent:
                    # Check for mitigation
                    is_mitigated = False
                    for j in range(i + 1, len(df)):
                        # If future candle's High goes above FVG Bottom (highs[i]), it starts filling
                        # If it goes above FVG Top (lows[i-2]), it's fully filled/invalidated
                        if highs[j] >= lows[i-2]:
                            is_mitigated = True
                            break
                            
                    if not is_mitigated:
                        fvgs.append({
                            "type": "bearish",
                            "top": float(lows[i-2]),
                            "bottom": float(highs[i]),
                            "index": int(i-1),
                            "size_pct": float(gap_percent * 100)
                        })
        
        # Sort by index (most recent last) and take last 5
        return sorted(fvgs, key=lambda x: x['index'])[-5:]

    def _calculate_order_blocks_vectorized(self, df):
        """
        Vectorized Order Block calculation with mitigation check and displacement filter.
        Only returns ACTIVE (untested) Order Blocks.
        """
        if len(df) < 5:
            return []
            
        opens = df['o'].values
        closes = df['c'].values
        highs = df['h'].values
        lows = df['l'].values
        
        # Identify candle colors
        is_bullish = closes > opens
        is_bearish = closes < opens
        
        # Calculate body and range for displacement check
        body = np.abs(closes - opens)
        candle_range = highs - lows
        avg_body = pd.Series(body).rolling(10).mean().values
        
        obs = []
        
        # Iterate to find OBs (skip last candle as it's forming)
        for i in range(2, len(df) - 2):
            # Bullish OB: Bearish candle (i) followed by strong Bullish move (i+1)
            if is_bearish[i] and is_bullish[i+1]:
                # Displacement Check: Next candle body > Avg body * 1.5
                if body[i+1] > avg_body[i] * 1.5 and closes[i+1] > highs[i]:
                    # Mitigation Check
                    ob_high = highs[i]
                    ob_low = lows[i]
                    is_mitigated = False
                    
                    # Check future candles for retest
                    for j in range(i + 2, len(df)):
                        # If price drops below OB Low, it's invalidated/broken
                        if closes[j] < ob_low:
                            is_mitigated = True
                            break
                        # If price touches the OB zone (High to Low), it's mitigated (tested)
                        # For "Fresh" OBs, we might want untested ones. 
                        # But standard SMC says a retest IS the entry. 
                        # So we keep it unless it's BROKEN (closed below low).
                        # Actually, let's mark it as "mitigated" if it touched, but "broken" if closed below.
                        # For this agent, let's return valid zones that haven't been BROKEN.
                        pass
                    
                    if not is_mitigated:
                        obs.append({
                            "type": "bullish",
                            "top": float(ob_high),
                            "bottom": float(ob_low),
                            "index": int(i),
                            "strength": "strong"
                        })

            # Bearish OB: Bullish candle (i) followed by strong Bearish move (i+1)
            elif is_bullish[i] and is_bearish[i+1]:
                # Displacement Check
                if body[i+1] > avg_body[i] * 1.5 and closes[i+1] < lows[i]:
                    # Mitigation Check
                    ob_high = highs[i]
                    ob_low = lows[i]
                    is_mitigated = False
                    
                    for j in range(i + 2, len(df)):
                        # If price closes above OB High, it's broken
                        if closes[j] > ob_high:
                            is_mitigated = True
                            break
                            
                    if not is_mitigated:
                        obs.append({
                            "type": "bearish",
                            "top": float(ob_high),
                            "bottom": float(ob_low),
                            "index": int(i),
                            "strength": "strong"
                        })
            
        # Return last 5 valid OBs
        return sorted(obs, key=lambda x: x['index'])[-5:]

    def _calculate_market_structure_vectorized(self, df, window=5):
        """
        Identify swing highs and lows.
        """
        df['swing_high'] = df['h'].rolling(window=window, center=True).max() == df['h']
        df['swing_low'] = df['l'].rolling(window=window, center=True).min() == df['l']
        
        swing_highs = df[df['swing_high']]['h'].tolist()
        swing_lows = df[df['swing_low']]['l'].tolist()
        
        # Determine trend based on recent swings
        if len(swing_highs) >= 2 and len(swing_lows) >= 2:
            higher_highs = swing_highs[-1] > swing_highs[-2]
            higher_lows = swing_lows[-1] > swing_lows[-2]
            
            if higher_highs and higher_lows:
                trend = "bullish"
            elif not higher_highs and not higher_lows:
                trend = "bearish"
            else:
                trend = "neutral"
        else:
            trend = "unknown"
            
        return {
            "trend": trend,
            "swing_highs": swing_highs[-5:], # Last 5
            "swing_lows": swing_lows[-5:]
        }

    def _calculate_volume_profile(self, df, bins=24):
        """
        Calculates Volume Profile.
        """
        if df.empty:
            return {}
            
        price_range = df['h'].max() - df['l'].min()
        if price_range == 0:
            return {}
            
        # Create bins
        hist, bin_edges = np.histogram(df['c'], bins=bins, weights=df['v'])
        
        # Find POC (Point of Control)
        poc_index = np.argmax(hist)
        poc_price = (bin_edges[poc_index] + bin_edges[poc_index+1]) / 2
        
        # Value Area (70%)
        total_volume = np.sum(hist)
        sorted_indices = np.argsort(hist)[::-1]
        cumulative_vol = 0
        va_indices = []
        for idx in sorted_indices:
            cumulative_vol += hist[idx]
            va_indices.append(idx)
            if cumulative_vol >= total_volume * 0.7:
                break
                
        va_prices = [(bin_edges[i] + bin_edges[i+1])/2 for i in va_indices]
        vah = max(va_prices) if va_prices else poc_price
        val = min(va_prices) if va_prices else poc_price
        
        return {
            "poc": float(poc_price),
            "vah": float(vah),
            "val": float(val),
            "total_volume": float(total_volume)
        }

    def _detect_candlestick_patterns(self, df):
        """
        Detects key patterns: Engulfing, Doji, Hammer, Evening Star, Gravestone Doji.
        """
        patterns = []
        if len(df) < 3:
            return patterns
            
        # Extract arrays for speed
        opens = df['o'].values
        closes = df['c'].values
        highs = df['h'].values
        lows = df['l'].values
        
        # Basic properties
        body = np.abs(closes - opens)
        rng = highs - lows
        # Avoid division by zero
        rng = np.where(rng == 0, 1e-9, rng)
        ratio = body / rng
        
        is_bullish = closes > opens
        is_bearish = closes < opens
        
        # 1. Doji (Last candle)
        if ratio[-1] < 0.1:
            patterns.append({"name": "Doji", "index": -1})
            
        # 2. Gravestone Doji (Last candle)
        # Small body, long upper shadow, no lower shadow
        upper_shadow = highs - np.maximum(opens, closes)
        lower_shadow = np.minimum(opens, closes) - lows
        
        if (ratio[-1] < 0.1 and 
            upper_shadow[-1] > 0.6 * rng[-1] and 
            lower_shadow[-1] < 0.1 * rng[-1]):
            patterns.append({"name": "Gravestone Doji", "index": -1})
            
        # 3. Engulfing (Last 2 candles)
        # Bullish Engulfing: Prev Red, Curr Green, Curr Body engulfs Prev Body
        if (is_bearish[-2] and is_bullish[-1] and 
            closes[-1] > opens[-2] and opens[-1] < closes[-2]):
            patterns.append({"name": "Bullish Engulfing", "index": -1})
            
        # Bearish Engulfing: Prev Green, Curr Red, Curr Body engulfs Prev Body
        if (is_bullish[-2] and is_bearish[-1] and 
            closes[-1] < opens[-2] and opens[-1] > closes[-2]):
            patterns.append({"name": "Bearish Engulfing", "index": -1})
            
        # 4. Evening Star (Last 3 candles)
        # Bullish (Large), Gap Up (Small), Bearish (Large, closes into first)
        if (is_bullish[-3] and ratio[-3] > 0.6 and # First candle large bullish
            ratio[-2] < 0.3 and # Second candle small (star)
            is_bearish[-1] and ratio[-1] > 0.5 and # Third candle bearish
            closes[-1] < (opens[-3] + closes[-3])/2): # Closes below midpoint of first
            patterns.append({"name": "Evening Star", "index": -1})

        # 5. Morning Star (Last 3 candles)
        # Bearish (Large), Gap Down (Small), Bullish (Large, closes into first)
        if (is_bearish[-3] and ratio[-3] > 0.6 and # First candle large bearish
            ratio[-2] < 0.3 and # Second candle small (star)
            is_bullish[-1] and ratio[-1] > 0.5 and # Third candle bullish
            closes[-1] > (opens[-3] + closes[-3])/2): # Closes above midpoint of first
            patterns.append({"name": "Morning Star", "index": -1})

        # 6. Hammer (Last candle)
        # Small body, long lower shadow, small/no upper shadow, occurring after downtrend
        # We need a simple trend check, e.g., Close < Close[5]
        lower_shadow = np.minimum(opens, closes) - lows
        upper_shadow = highs - np.maximum(opens, closes)
        
        if (ratio[-1] < 0.3 and # Small body
            lower_shadow[-1] > 2 * body[-1] and # Long lower shadow
            upper_shadow[-1] < 0.2 * body[-1]): # Small upper shadow
            patterns.append({"name": "Hammer", "index": -1})

        # 7. Shooting Star (Last candle)
        # Small body, long upper shadow, small/no lower shadow, occurring after uptrend
        if (ratio[-1] < 0.3 and # Small body
            upper_shadow[-1] > 2 * body[-1] and # Long upper shadow
            lower_shadow[-1] < 0.2 * body[-1]): # Small lower shadow
            patterns.append({"name": "Shooting Star", "index": -1})
            
        return patterns

    def _calculate_fibonacci_levels(self, df, lookback=100):
        """
        Calculates Fibonacci retracement and extension levels based on recent significant swing points.
        """
        if len(df) < lookback:
            return {}
            
        # Get recent data
        recent_df = df.iloc[-lookback:]
        
        # Find max high and min low in the lookback period
        max_high = recent_df['h'].max()
        min_low = recent_df['l'].min()
        
        # Determine trend direction to set anchor points
        # Simple approach: check if the high or low occurred more recently
        idxmax = recent_df['h'].idxmax()
        idxmin = recent_df['l'].idxmin()
        
        trend = "bullish" if idxmin < idxmax else "bearish"
        
        levels = {}
        
        if trend == "bullish":
            # Low to High
            diff = max_high - min_low
            levels = {
                "trend": "bullish",
                "swing_low": float(min_low),
                "swing_high": float(max_high),
                "retracements": {
                    "0.236": float(max_high - 0.236 * diff),
                    "0.382": float(max_high - 0.382 * diff),
                    "0.5": float(max_high - 0.5 * diff),
                    "0.618": float(max_high - 0.618 * diff), # Golden Pocket
                    "0.786": float(max_high - 0.786 * diff)
                },
                "extensions": {
                    "1.272": float(max_high + 0.272 * diff),
                    "1.618": float(max_high + 0.618 * diff),
                    "2.618": float(max_high + 1.618 * diff)
                }
            }
        else:
            # High to Low
            diff = max_high - min_low
            levels = {
                "trend": "bearish",
                "swing_high": float(max_high),
                "swing_low": float(min_low),
                "retracements": {
                    "0.236": float(min_low + 0.236 * diff),
                    "0.382": float(min_low + 0.382 * diff),
                    "0.5": float(min_low + 0.5 * diff),
                    "0.618": float(min_low + 0.618 * diff), # Golden Pocket
                    "0.786": float(min_low + 0.786 * diff)
                },
                "extensions": {
                    "1.272": float(min_low - 0.272 * diff),
                    "1.618": float(min_low - 0.618 * diff),
                    "2.618": float(min_low - 1.618 * diff)
                }
            }
            
        return levels

    def _perform_fabio_analysis(self, tech_analysis):
        """
        Implements the Fabio Valentino specific logic.
        """
        ltf = tech_analysis.get("ltf", {})
        volume_profile = ltf.get("volume_profile", {})
        market_structure = ltf.get("market_structure", {})
        
        # 1. Market State Detection
        # We need current price. Since we don't have it passed explicitly, we assume it's the close of the last LTF candle.
        # In a real scenario, we'd pass the live price.
        # For now, let's assume the analysis is done on the latest data.
        
        market_state = "unknown"
        bias = "neutral"
        
        if volume_profile:
            poc = volume_profile.get("poc")
            vah = volume_profile.get("vah")
            val = volume_profile.get("val")
            
            # We need the current price from somewhere. 
            # Since this method takes the whole tech_analysis dict, we can't easily get the last close unless we stored it.
            # Let's assume we can't determine state without price.
            # BUT, we can infer from the trend in market_structure.
            
            trend = market_structure.get("trend", "neutral")
            
            if trend == "bullish":
                market_state = "imbalanced"
                bias = "bullish"
            elif trend == "bearish":
                market_state = "imbalanced"
                bias = "bearish"
            else:
                market_state = "balanced"
                bias = "neutral"
                
        return {
            "market_state": market_state,
            "bias": bias,
            "opportunities": self._detect_opportunities(market_state, bias, ltf)
        }

    def _detect_opportunities(self, market_state, bias, ltf_data):
        opportunities = []
        
        # Example logic:
        # If Imbalanced Bullish -> Look for retest of FVG or Order Block
        if market_state == "imbalanced" and bias == "bullish":
            fvgs = ltf_data.get("fvgs", [])
            bullish_fvgs = [f for f in fvgs if f['type'] == 'bullish']
            if bullish_fvgs:
                opportunities.append({
                    "type": "Trend Following",
                    "direction": "Long",
                    "trigger": "Retest of Bullish FVG",
                    "target": "Recent High"
                })
                
        # If Balanced -> Look for Mean Reversion from edges
        elif market_state == "balanced":
            # If RSI is overbought/oversold
            rsi = ltf_data.get("rsi", 50)
            if rsi < 30:
                opportunities.append({
                    "type": "Mean Reversion",
                    "direction": "Long",
                    "trigger": "Oversold RSI in Balance",
                    "target": "POC"
                })
            elif rsi > 70:
                opportunities.append({
                    "type": "Mean Reversion",
                    "direction": "Short",
                    "trigger": "Overbought RSI in Balance",
                    "target": "POC"
                })
                
        return opportunities

    def generate_signal_prompt(self, analysis_result: Dict) -> str:
        """
        Generates the prompt for the AI model with rich text summary.
        """
        # Create a text summary of the technicals
        tech_summary = self._generate_technical_summary(analysis_result)
        
        # Combine structured data and text summary
        prompt_data = {
            "summary": tech_summary,
            "data": analysis_result
        }
        
        return json.dumps(prompt_data, default=str)

    def _generate_technical_summary(self, analysis_result: Dict) -> str:
        """
        Generates a human-readable summary of the technical analysis.
        """
        summary = []
        
        # Fabio Analysis
        fabio = analysis_result.get("fabio_analysis", {})
        summary.append(f"Market State: {fabio.get('market_state', 'unknown').upper()}")
        summary.append(f"Bias: {fabio.get('bias', 'neutral').upper()}")
        
        opportunities = fabio.get("opportunities", [])
        if opportunities:
            summary.append(f"Detected Opportunities: {len(opportunities)}")
            for opp in opportunities:
                summary.append(f"- {opp.get('type')}: {opp.get('direction')} ({opp.get('trigger')})")
        else:
            summary.append("No specific Fabio Valentino opportunities detected.")
            
        # Technicals (LTF)
        ltf = analysis_result.get("technical_analysis", {}).get("ltf", {})
        
        # RSI
        rsi = ltf.get("rsi")
        if rsi:
            summary.append(f"RSI (LTF): {rsi:.2f}")
            
        # FVGs
        fvgs = ltf.get("fvgs", [])
        if fvgs:
            summary.append(f"Active FVGs (LTF): {len(fvgs)}")
            
        # Order Blocks
        obs = ltf.get("order_blocks", [])
        if obs:
            summary.append(f"Active Order Blocks (LTF): {len(obs)}")
            for ob in obs:
                summary.append(f"- {ob.get('type').upper()} OB at {ob.get('top'):.4f}-{ob.get('bottom'):.4f}")
            
        # Candlestick Patterns
        patterns = ltf.get("candlestick_patterns", [])
        if patterns:
            summary.append(f"Candlestick Patterns: {len(patterns)}")
            for p in patterns:
                summary.append(f"- {p.get('name')} (Strength: {p.get('strength', 'medium')})")

        # Fibonacci
        fib = ltf.get("fibonacci", {})
        if fib:
            trend = fib.get("trend", "unknown")
            summary.append(f"Fibonacci Trend: {trend.upper()}")
            
            retracements = fib.get("retracements", {})
            if "0.618" in retracements:
                summary.append(f"Fib Golden Pocket (0.618): {retracements['0.618']:.4f}")
                
            extensions = fib.get("extensions", {})
            if "1.618" in extensions:
                summary.append(f"Fib Extension (1.618): {extensions['1.618']:.4f}")
            
        return "\n".join(summary)

    async def generate_signal(self, analysis_result: Dict, provider: str = "gemini", feedback: str = None) -> Dict:
        """
        Generates a trading signal using the specified AI provider.
        """
        prompt = self.generate_signal_prompt(analysis_result)
        
        # Append feedback if provided (Debate Loop)
        if feedback:
            prompt += f"\n\nIMPORTANT FEEDBACK FROM RISK MANAGER:\n{feedback}\n\nPlease refine your analysis and signal based on this feedback. If the previous signal was rejected due to risk, find a better setup or adjust parameters."

        system_prompt = (
            "You are a professional trading agent following the Fabio Valentino Smart Money Concepts strategy. "
            "Your goal is to identify high-probability setups based on Market Structure, Liquidity, and Displacement.\n\n"
            "RULES:\n"
            "1. Identify the Market State (Balanced vs Imbalanced).\n"
            "2. Determine Bias based on Market Structure (Higher Highs/Lows).\n"
            "3. Look for Liquidity Sweeps followed by Displacement (FVGs).\n"
            "4. Validate setups with RSI and Order Blocks.\n"
            "5. Use Fibonacci Retracements (0.618) for entries and Extensions (1.272, 1.618) for Take Profit targets.\n"
            "6. ONLY signal a trade if conviction is HIGH (>70).\n\n"
            "Output MUST be a JSON object with keys: action (BUY/SELL/HOLD), entry_price, stop_loss, take_profit, conviction_score, reasoning."
        )
        
        if provider == "gemini":
            return await self._call_gemini(prompt, system_prompt)
        else:
            return {"error": f"Provider {provider} not supported"}

    async def generate_comprehensive_analysis(self, analysis_result: Dict, provider: str = "gemini") -> Dict:
        """
        Generates a comprehensive market analysis using the specified AI provider.
        """
        prompt = self.generate_signal_prompt(analysis_result)
        system_prompt = (
            "You are a professional trading agent. Analyze the provided market data and generate a comprehensive market analysis report. "
            "The report should cover: Market Structure, Trend Analysis, Key Levels (Support/Resistance), Volume Analysis, and Potential Scenarios. "
            "Also provide a 'Sentiment Score' from 0 (Bearish) to 100 (Bullish).\n\n"
            "Output MUST be a detailed text report in Markdown format. Include the Sentiment Score at the top."
        )
        
        if provider == "gemini":
            # We reuse _call_gemini but we need to handle the fact that it might expect JSON
            # Actually _call_gemini tries to parse JSON but returns raw text if it fails or if it's not JSON
            # Let's modify _call_gemini or create a new method if needed.
            # For now, let's use _call_gemini and if it returns a dict with "error" we know it failed.
            # But wait, _call_gemini returns a dict. If the AI returns text, _call_gemini might fail to parse it as JSON.
            # We should probably have a generic _call_ai method that returns text, and then specific wrappers for signal (JSON) vs analysis (Text).
            
            # Let's create a specific method for text generation to avoid breaking existing logic
            return await self._call_gemini_text(prompt, system_prompt)
        else:
            return {"error": f"Provider {provider} not supported"}

    async def _call_gemini_text(self, prompt: str, system_prompt: str) -> Dict:
        """
        Calls Gemini API and returns the raw text response.
        """
        full_prompt = f"{system_prompt}\n\n{prompt}"
        
        try:
            process = await asyncio.create_subprocess_exec(
                'gemini', full_prompt,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=os.environ.copy()
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                return {"error": f"Gemini CLI failed: {stderr.decode()}"}
                
            response_text = stdout.decode().strip()
            return {"analysis": response_text}
                
        except FileNotFoundError:
            return {"error": "Gemini CLI not found"}
        except Exception as e:
            return {"error": f"Error calling Gemini: {str(e)}"}

    async def _call_gemini(self, prompt: str, system_prompt: str) -> Dict:
        """
        Calls Gemini API via CLI (as per original implementation) or Library.
        Using subprocess for consistency with original setup if library setup is unknown.
        """
        full_prompt = f"{system_prompt}\n\n{prompt}"
        
        # Use asyncio.create_subprocess_exec for async subprocess
        try:
            process = await asyncio.create_subprocess_exec(
                'gemini', full_prompt,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=os.environ.copy()
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                return {"error": f"Gemini CLI failed: {stderr.decode()}"}
                
            response_text = stdout.decode().strip()
            
            # Extract JSON - handle multiple formats
            # 1. Try markdown code block with ```json
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()
            # 2. Try plain markdown code block with ```
            elif '```' in response_text:
                code_match = re.search(r'```\s*(\{.*?\})\s*```', response_text, re.DOTALL)
                if code_match:
                    json_str = code_match.group(1).strip()
                else:
                    json_str = response_text
            # 3. Try to find JSON object directly in the text
            else:
                # Look for a JSON object pattern
                obj_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
                if obj_match:
                    json_str = obj_match.group(0).strip()
                else:
                    json_str = response_text
                
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                return {"error": "Failed to decode JSON from Gemini response", "raw_output": response_text}
                
        except FileNotFoundError:
            return {"error": "Gemini CLI not found"}
        except Exception as e:
            return {"error": f"Error calling Gemini: {str(e)}"}

# Example usage block (commented out)
# async def main():
#     agent = TraderAgent()
#     market, ohlcv = await agent.fetch_data("SOL")
#     analysis = agent.analyze_market(market, ohlcv)
#     print(analysis)
# 
# if __name__ == "__main__":
#     asyncio.run(main())
