import os
import json
import asyncio
import aiohttp
import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, List, Optional, Union
from dotenv import load_dotenv
import ta as technical_analysis_lib
import google.generativeai as genai
from backend.config import Config

# Configure logging
logger = logging.getLogger("TraderAgentCore")

# Load environment variables
load_dotenv()

class TraderAgent:
    def __init__(self):
        self.birdeye_api_key = os.getenv("BIRDEYE_API_KEY")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.coingecko_api_key = os.getenv("COINGECKO_API_KEY")
        self.coinmarketcap_api_key = os.getenv("COINMARKETCAP_API_KEY")
        
        self.headers_birdeye = {"X-API-KEY": self.birdeye_api_key} if self.birdeye_api_key else {}
        self.headers_coingecko = {"x-cg-demo-api-key": self.coingecko_api_key} if self.coingecko_api_key else {}
        self.headers_coinmarketcap = {"X-CMC_PRO_API_KEY": self.coinmarketcap_api_key} if self.coinmarketcap_api_key else {}
        
        # Configure Gemini API
        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
        else:
            logger.warning("Gemini API Key not found. AI features will be disabled.")

    async def fetch_data(self, token_symbol: str, chain: str = "solana") -> tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Fetches market data and OHLCV data asynchronously.
        """
        logger.info(f"Fetching data for {token_symbol} on {chain}...")
        token_address = await self._get_token_address(token_symbol, chain)
        if not token_address:
            logger.error(f"Token address not found for {token_symbol}")
            return {"error": f"Token address not found for {token_symbol}"}, {}

        async with aiohttp.ClientSession() as session:
            # Fetch Market Data (Birdeye)
            market_data_task = self._fetch_birdeye_market_data(session, token_address, chain)

            # Try CoinGecko first for pool/OHLCV data
            pool_address = await self._get_top_pool_coingecko(session, token_address, chain)

            # If CoinGecko fails and we have CoinMarketCap key, try fallback
            if not pool_address and self.coinmarketcap_api_key:
                logger.info("CoinGecko pool lookup failed, trying CoinMarketCap fallback...")
                pool_address = await self._get_top_pool_coinmarketcap(session, token_address, chain)

            market_data = await market_data_task

            if not pool_address:
                logger.warning("No pool data available from any provider")
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

    async def _get_token_address(self, symbol: str, chain: str) -> Optional[str]:
        """
        Resolves token symbol to address.
        """
        common_tokens = {
            "solana": {"SOL": "So11111111111111111111111111111111111111111"},
            "ethereum": {"ETH": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"},
            "bsc": {"BNB": "0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c"}
        }
        if chain in common_tokens and symbol.upper() in common_tokens[chain]:
            return common_tokens[chain][symbol.upper()]
            
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
                logger.error(f"Error fetching token address: {e}")
        return None

    async def _fetch_birdeye_market_data(self, session: aiohttp.ClientSession, token_address: str, chain: str) -> Dict[str, Any]:
        url = f"https://public-api.birdeye.so/defi/price?address={token_address}&include_liquidity=true&ui_amount_mode=raw"
        headers = {"X-API-KEY": self.birdeye_api_key, "X-CHAIN": chain}
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('data', {})
        except Exception as e:
            logger.error(f"Error fetching Birdeye data: {e}")
        return {}

    async def _get_top_pool_coingecko(self, session: aiohttp.ClientSession, token_address: str, network: str) -> Optional[str]:
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
            logger.error(f"Error fetching pool: {e}")
        return None

    async def _fetch_ohlcv_coingecko(self, session: aiohttp.ClientSession, pool_address: str, network: str, timeframe: str, aggregate: int, limit: int) -> List[Dict[str, float]]:
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
            logger.error(f"Error fetching OHLCV from CoinGecko: {e}")
            if self.coinmarketcap_api_key:
                logger.info("Falling back to CoinMarketCap for OHLCV data...")
                # return await self._fetch_ohlcv_coinmarketcap(session, token_address, network, timeframe, aggregate, limit)
                # Placeholder for CMC fallback
                pass
        return []

    async def _get_top_pool_coinmarketcap(self, session: aiohttp.ClientSession, token_address: str, network: str) -> Optional[str]:
        logger.warning("CoinMarketCap fallback: Pool data not available, trying direct OHLCV...")
        return None

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

    def _calculate_rsi(self, df: pd.DataFrame, window: int = 14) -> float:
        return technical_analysis_lib.momentum.rsi(df['c'], window=window).iloc[-1]

    def _calculate_macd(self, df: pd.DataFrame) -> Dict[str, float]:
        macd = technical_analysis_lib.trend.MACD(df['c'])
        return {
            "line": macd.macd().iloc[-1],
            "signal": macd.macd_signal().iloc[-1],
            "hist": macd.macd_diff().iloc[-1]
        }

    def _calculate_fvgs_vectorized(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        if len(df) < 3:
            return []

        highs = df['h'].values
        lows = df['l'].values
        
        fvgs = []
        min_gap_percent = 0.001
        
        for i in range(2, len(df)):
            # Bullish FVG
            if highs[i-2] < lows[i]:
                gap_size = lows[i] - highs[i-2]
                gap_percent = gap_size / highs[i-2]
                
                if gap_percent >= min_gap_percent:
                    is_mitigated = False
                    for j in range(i + 1, len(df)):
                        if lows[j] <= highs[i-2]:
                            is_mitigated = True
                            break
                    
                    if not is_mitigated:
                        fvgs.append({
                            "type": "bullish",
                            "top": float(lows[i]),
                            "bottom": float(highs[i-2]),
                            "index": int(i-1),
                            "size_pct": float(gap_percent * 100)
                        })

            # Bearish FVG
            elif lows[i-2] > highs[i]:
                gap_size = lows[i-2] - highs[i]
                gap_percent = gap_size / highs[i]
                
                if gap_percent >= min_gap_percent:
                    is_mitigated = False
                    for j in range(i + 1, len(df)):
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
        
        return sorted(fvgs, key=lambda x: x['index'])[-5:]

    def _calculate_order_blocks_vectorized(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        if len(df) < 5:
            return []
            
        opens = df['o'].values
        closes = df['c'].values
        highs = df['h'].values
        lows = df['l'].values
        
        is_bullish = closes > opens
        is_bearish = closes < opens
        
        body = np.abs(closes - opens)
        avg_body = pd.Series(body).rolling(10).mean().values
        
        obs = []
        
        for i in range(2, len(df) - 2):
            if is_bearish[i] and is_bullish[i+1]:
                if body[i+1] > avg_body[i] * 1.5 and closes[i+1] > highs[i]:
                    ob_high = highs[i]
                    ob_low = lows[i]
                    is_mitigated = False
                    
                    for j in range(i + 2, len(df)):
                        if closes[j] < ob_low:
                            is_mitigated = True
                            break
                    
                    if not is_mitigated:
                        obs.append({
                            "type": "bullish",
                            "top": float(ob_high),
                            "bottom": float(ob_low),
                            "index": int(i),
                            "strength": "strong"
                        })

            elif is_bullish[i] and is_bearish[i+1]:
                if body[i+1] > avg_body[i] * 1.5 and closes[i+1] < lows[i]:
                    ob_high = highs[i]
                    ob_low = lows[i]
                    is_mitigated = False
                    
                    for j in range(i + 2, len(df)):
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
            
        return sorted(obs, key=lambda x: x['index'])[-5:]

    def _calculate_market_structure_vectorized(self, df: pd.DataFrame, window: int = 5) -> Dict[str, Any]:
        df['swing_high'] = df['h'].rolling(window=window, center=True).max() == df['h']
        df['swing_low'] = df['l'].rolling(window=window, center=True).min() == df['l']
        
        swing_highs = df[df['swing_high']]['h'].tolist()
        swing_lows = df[df['swing_low']]['l'].tolist()
        
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
            "swing_highs": swing_highs[-5:],
            "swing_lows": swing_lows[-5:]
        }

    def _calculate_volume_profile(self, df: pd.DataFrame, bins: int = 24) -> Dict[str, float]:
        if df.empty:
            return {}
            
        price_range = df['h'].max() - df['l'].min()
        if price_range == 0:
            return {}
            
        hist, bin_edges = np.histogram(df['c'], bins=bins, weights=df['v'])
        
        poc_index = np.argmax(hist)
        poc_price = (bin_edges[poc_index] + bin_edges[poc_index+1]) / 2
        
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

    def _detect_candlestick_patterns(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        patterns = []
        if len(df) < 3:
            return patterns
            
        opens = df['o'].values
        closes = df['c'].values
        highs = df['h'].values
        lows = df['l'].values
        
        body = np.abs(closes - opens)
        rng = highs - lows
        rng = np.where(rng == 0, 1e-9, rng)
        ratio = body / rng
        
        is_bullish = closes > opens
        is_bearish = closes < opens
        
        if ratio[-1] < 0.1:
            patterns.append({"name": "Doji", "index": -1})
            
        upper_shadow = highs - np.maximum(opens, closes)
        lower_shadow = np.minimum(opens, closes) - lows
        
        if (ratio[-1] < 0.1 and 
            upper_shadow[-1] > 0.6 * rng[-1] and 
            lower_shadow[-1] < 0.1 * rng[-1]):
            patterns.append({"name": "Gravestone Doji", "index": -1})
            
        if (is_bearish[-2] and is_bullish[-1] and 
            closes[-1] > opens[-2] and opens[-1] < closes[-2]):
            patterns.append({"name": "Bullish Engulfing", "index": -1})
            
        if (is_bullish[-2] and is_bearish[-1] and 
            closes[-1] < opens[-2] and opens[-1] > closes[-2]):
            patterns.append({"name": "Bearish Engulfing", "index": -1})
            
        return patterns

    def _calculate_fibonacci_levels(self, df: pd.DataFrame, lookback: int = 100) -> Dict[str, Any]:
        if len(df) < lookback:
            return {}
            
        recent_df = df.iloc[-lookback:]
        max_high = recent_df['h'].max()
        min_low = recent_df['l'].min()
        
        idxmax = recent_df['h'].idxmax()
        idxmin = recent_df['l'].idxmin()
        
        trend = "bullish" if idxmin < idxmax else "bearish"
        diff = max_high - min_low
        
        levels = {}
        if trend == "bullish":
            levels = {
                "trend": "bullish",
                "swing_low": float(min_low),
                "swing_high": float(max_high),
                "retracements": {
                    "0.236": float(max_high - 0.236 * diff),
                    "0.382": float(max_high - 0.382 * diff),
                    "0.5": float(max_high - 0.5 * diff),
                    "0.618": float(max_high - 0.618 * diff),
                    "0.786": float(max_high - 0.786 * diff)
                },
                "extensions": {
                    "1.272": float(max_high + 0.272 * diff),
                    "1.618": float(max_high + 0.618 * diff),
                    "2.618": float(max_high + 1.618 * diff)
                }
            }
        else:
            levels = {
                "trend": "bearish",
                "swing_high": float(max_high),
                "swing_low": float(min_low),
                "retracements": {
                    "0.236": float(min_low + 0.236 * diff),
                    "0.382": float(min_low + 0.382 * diff),
                    "0.5": float(min_low + 0.5 * diff),
                    "0.618": float(min_low + 0.618 * diff),
                    "0.786": float(min_low + 0.786 * diff)
                },
                "extensions": {
                    "1.272": float(min_low - 0.272 * diff),
                    "1.618": float(min_low - 0.618 * diff),
                    "2.618": float(min_low - 1.618 * diff)
                }
            }
            
        return levels

    def _perform_fabio_analysis(self, tech_analysis: Dict) -> Dict[str, Any]:
        ltf = tech_analysis.get("ltf", {})
        volume_profile = ltf.get("volume_profile", {})
        market_structure = ltf.get("market_structure", {})
        
        market_state = "unknown"
        bias = "neutral"
        
        if volume_profile:
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

    def _detect_opportunities(self, market_state: str, bias: str, ltf_data: Dict) -> List[Dict[str, str]]:
        opportunities = []
        
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
                
        elif market_state == "balanced":
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
        tech_summary = self._generate_technical_summary(analysis_result)
        ltf = analysis_result.get("technical_analysis", {}).get("ltf", {})
        market_structure = ltf.get("market_structure", {})
        trend = market_structure.get("trend", "unknown")
        
        prompt_data = {
            "market_context": {
                "trend": trend,
                "volatility_state": "High" if ltf.get("atr_pct", 0) > 0.02 else "Normal"
            },
            "summary": tech_summary,
            "data": analysis_result
        }
        
        return json.dumps(prompt_data, default=str)

    def _generate_technical_summary(self, analysis_result: Dict) -> str:
        summary = []
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
            
        ltf = analysis_result.get("technical_analysis", {}).get("ltf", {})
        rsi = ltf.get("rsi")
        if rsi:
            summary.append(f"RSI (LTF): {rsi:.2f}")
            
        fvgs = ltf.get("fvgs", [])
        if fvgs:
            summary.append(f"Active FVGs (LTF): {len(fvgs)}")
            
        obs = ltf.get("order_blocks", [])
        if obs:
            summary.append(f"Active Order Blocks (LTF): {len(obs)}")
            
        return "\n".join(summary)

    async def generate_signal(self, analysis_result: Dict, provider: str = "gemini", feedback: str = None) -> Dict:
        prompt = self.generate_signal_prompt(analysis_result)
        if feedback:
            prompt += f"\n\nIMPORTANT FEEDBACK FROM RISK MANAGER:\n{feedback}\n\nPlease refine your analysis and signal based on this feedback."
            
        model = genai.GenerativeModel(Config.MODEL_NAME)
        try:
            response = await model.generate_content_async(prompt)
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"Error generating signal: {e}")
            return {"error": str(e)}

    async def generate_comprehensive_analysis(self, analysis_result: Dict, provider: str = "gemini") -> Dict[str, Any]:
        prompt = self.generate_signal_prompt(analysis_result)
        prompt += "\n\nProvide a comprehensive market analysis report based on the data above. Focus on market structure, key levels, and potential scenarios."
        
        model = genai.GenerativeModel(Config.MODEL_NAME)
        try:
            response = await model.generate_content_async(prompt)
            return {"analysis": response.text}
        except Exception as e:
            logger.error(f"Error generating analysis: {e}")
            return {"error": str(e)}

    async def _call_gemini(self, user_content: str, system_instruction: str = None) -> Dict[str, Any]:
        """
        Helper method to call Gemini API, maintaining compatibility with backend agents.
        """
        try:
            model = genai.GenerativeModel(Config.MODEL_NAME)
            
            full_prompt = user_content
            if system_instruction:
                # Gemini 1.5/2.0 supports system instructions better via config, 
                # but prepending is a safe fallback for simple usage
                full_prompt = f"SYSTEM INSTRUCTION:\n{system_instruction}\n\nUSER CONTENT:\n{user_content}"
                
            response = await model.generate_content_async(full_prompt)
            text_response = response.text
            
            # Clean up markdown code blocks if present
            if "```json" in text_response:
                text_response = text_response.split("```json")[1].split("```")[0].strip()
            elif "```" in text_response:
                text_response = text_response.split("```")[1].split("```")[0].strip()
            
            # Try to parse JSON
            try:
                return json.loads(text_response)
            except json.JSONDecodeError:
                # If not JSON, return as text wrapped in dict, or try to find JSON-like structure
                logger.warning("Gemini response was not valid JSON. Returning raw text.")
                return {"response": text_response, "raw_text": response.text}
                
        except Exception as e:
            logger.error(f"Error calling Gemini: {e}")
            return {"error": str(e)}
