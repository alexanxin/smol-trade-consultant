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
        self.headers_birdeye = {"X-API-KEY": self.birdeye_api_key}
        self.headers_coingecko = {"x-cg-demo-api-key": self.coingecko_api_key}

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
            
            # Fetch OHLCV Data (CoinGecko) - Requires pool address first
            pool_address_task = self._get_top_pool_coingecko(session, token_address, chain)
            
            market_data, pool_address = await asyncio.gather(market_data_task, pool_address_task)
            
            if not pool_address:
                return market_data, {"ltf": [], "htf": [], "daily": []}

            # Fetch OHLCV for multiple timeframes concurrently
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
            print(f"Error fetching OHLCV: {e}")
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
                "candlestick_patterns": self._detect_candlestick_patterns(df)
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
        Vectorized Fair Value Gap calculation.
        """
        df = df.copy()
        # Shift for comparison
        df['prev_high'] = df['h'].shift(1)
        df['prev_low'] = df['l'].shift(1)
        df['next_high'] = df['h'].shift(-1)
        df['next_low'] = df['l'].shift(-1)
        
        # Bullish FVG: Low > Prev High AND High < Next Low (Gap between prev high and next low)
        # Wait, standard definition: 
        # Bullish FVG: Candle 1 High < Candle 3 Low. The gap is between Candle 1 High and Candle 3 Low.
        # In the original code:
        # bullish_fvg = df[(df['l'] > df['prev_high']) & (df['h'] < df['next_low'])]
        # This seems to be checking if the CURRENT candle is the gap.
        # Let's stick to the standard definition:
        # FVG is formed by 3 candles.
        # Bullish: Candle 0 High < Candle 2 Low. Gap is (Candle 0 High, Candle 2 Low).
        # Bearish: Candle 0 Low > Candle 2 High. Gap is (Candle 2 High, Candle 0 Low).
        
        # Let's re-implement strictly based on 3-candle pattern for accuracy
        # We want to find gaps created by the PREVIOUS candle (Candle 1), validated by Candle 2 (Current)
        # Actually, we usually detect FVG after Candle 2 closes.
        
        # Let's use the logic:
        # Index i: Current Candle
        # Index i-1: Gap Candle (Big move)
        # Index i-2: Pre-Gap Candle
        
        # Bullish FVG:
        # (i-2) High < (i) Low
        
        highs = df['h'].values
        lows = df['l'].values
        
        # Create boolean masks
        # We need to look at i-2, i-1, i
        # Shift 2 to get i-2 aligned with i
        prev_2_high = np.roll(highs, 2)
        prev_2_low = np.roll(lows, 2)
        
        # Bullish FVG condition: prev_2_high < current_low
        # And typically we want the middle candle (i-1) to be bullish and large, but the gap itself is the defining feature
        bullish_mask = (prev_2_high < lows) 
        bearish_mask = (prev_2_low > highs)
        
        # We only care about recent FVGs usually, but let's return the last few valid ones
        # Filter for valid indices (start from index 2)
        valid_indices = np.arange(len(df)) >= 2
        
        bullish_fvgs = []
        bearish_fvgs = []
        
        # Extract data
        for i in np.where(bullish_mask & valid_indices)[0]:
            bullish_fvgs.append({
                "type": "bullish",
                "top": float(lows[i]),
                "bottom": float(prev_2_high[i]),
                "index": int(i-1) # The gap is technically in the middle candle
            })
            
        for i in np.where(bearish_mask & valid_indices)[0]:
            bearish_fvgs.append({
                "type": "bearish",
                "top": float(prev_2_low[i]),
                "bottom": float(highs[i]),
                "index": int(i-1)
            })
            
        return bullish_fvgs + bearish_fvgs

    def _calculate_order_blocks_vectorized(self, df):
        """
        Vectorized Order Block calculation.
        """
        # Simplified OB detection:
        # Bullish OB: The last bearish candle before a strong bullish move that breaks structure or takes liquidity.
        # For simplicity/speed: Bearish candle followed by a bullish candle that engulfs or moves strongly away.
        
        opens = df['o'].values
        closes = df['c'].values
        highs = df['h'].values
        lows = df['l'].values
        
        # Identify candle colors
        is_bullish = closes > opens
        is_bearish = closes < opens
        
        # Shift to compare with next candle
        next_is_bullish = np.roll(is_bullish, -1)
        next_close = np.roll(closes, -1)
        next_open = np.roll(opens, -1)
        
        # Bullish OB: Current is Bearish, Next is Bullish and Strong (e.g. Next Close > Current High)
        bullish_ob_mask = is_bearish & next_is_bullish & (next_close > highs)
        
        # Bearish OB: Current is Bullish, Next is Bearish and Strong (e.g. Next Close < Current Low)
        bearish_ob_mask = is_bullish & (~next_is_bullish) & (next_close < lows)
        
        obs = []
        for i in np.where(bullish_ob_mask)[0][:-1]: # Exclude last element due to roll
            obs.append({
                "type": "bullish",
                "price_level": float(highs[i]), # Often the high of the bearish candle is the trigger
                "index": int(i)
            })
            
        for i in np.where(bearish_ob_mask)[0][:-1]:
            obs.append({
                "type": "bearish",
                "price_level": float(lows[i]),
                "index": int(i)
            })
            
        return obs

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
            
        return patterns

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
        Generates the prompt for the AI model.
        """
        # Construct a concise but data-rich prompt
        return json.dumps(analysis_result, default=str)

    async def generate_signal(self, analysis_result: Dict, provider: str = "gemini") -> Dict:
        """
        Generates a trading signal using the specified AI provider.
        """
        prompt = self.generate_signal_prompt(analysis_result)
        system_prompt = (
            "You are a professional trading agent. Analyze the provided market data and generate a trading signal. "
            "Output MUST be a JSON object with keys: action, entry_price, stop_loss, take_profit, conviction_score, reasoning."
        )
        
        if provider == "gemini":
            return await self._call_gemini(prompt, system_prompt)
        else:
            return {"error": f"Provider {provider} not supported"}

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
            
            # Extract JSON
            if response_text.startswith('```json') and response_text.endswith('```'):
                json_str = response_text[7:-3].strip()
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
