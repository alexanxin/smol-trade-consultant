import asyncio
from typing import Dict, Any
from .prompts import TECHNICAL_ANALYST_PROMPT, SENTIMENT_ANALYST_PROMPT
from trader_agent_core import TraderAgent

class BaseAgent:
    def __init__(self, name: str):
        self.name = name

class TechnicalAnalyst(BaseAgent):
    def __init__(self):
        super().__init__("TechnicalAnalyst")
        self.core_agent = TraderAgent()

    async def analyze(self, token: str, chain: str) -> Dict[str, Any]:
        print(f"[{self.name}] Fetching data for {token}...", flush=True)
        market_data, ohlcv_data = await self.core_agent.fetch_data(token, chain)
        print(f"[{self.name}] Data fetched. Running analysis...", flush=True)
        
        print(f"[{self.name}] Running technical analysis...")
        analysis_result = self.core_agent.analyze_market(market_data, ohlcv_data)
        
        # Generate a detailed SMC & Fabio Valentino summary
        summary = self._generate_deep_dive_summary(analysis_result)
        
        return {
            "raw_data": analysis_result,
            "summary": summary,
            "market_data": market_data
        }

    def _generate_deep_dive_summary(self, analysis_result: Dict) -> str:
        """
        Generates a comprehensive SMC and Fabio Valentino analysis summary.
        """
        summary = []
        
        # 1. Fabio Valentino Analysis
        fabio = analysis_result.get("fabio_analysis", {})
        market_state = fabio.get('market_state', 'unknown').upper()
        bias = fabio.get('bias', 'neutral').upper()
        summary.append(f"🏛️ MARKET STATE: {market_state} | BIAS: {bias}")
        
        opportunities = fabio.get("opportunities", [])
        if opportunities:
            summary.append(f"⚡ TRADING OPPORTUNITIES ({len(opportunities)}):")
            for opp in opportunities:
                summary.append(f"   - {opp.get('type')}: {opp.get('direction')} on {opp.get('trigger')}")
        else:
            summary.append("   - No specific Fabio Valentino setups detected.")

        # 2. Key Technical Levels (LTF)
        ltf = analysis_result.get("technical_analysis", {}).get("ltf", {})
        
        # Volume Profile
        vp = ltf.get("volume_profile", {})
        if vp:
            summary.append(f"📊 VOLUME PROFILE:")
            summary.append(f"   - POC (Point of Control): {vp.get('poc', 'N/A')}")
            summary.append(f"   - VAH (Value Area High): {vp.get('vah', 'N/A')}")
            summary.append(f"   - VAL (Value Area Low): {vp.get('val', 'N/A')}")

        # Fair Value Gaps (FVGs)
        fvgs = ltf.get("fvgs", [])
        if fvgs:
            bullish_fvgs = [f for f in fvgs if f['type'] == 'bullish']
            bearish_fvgs = [f for f in fvgs if f['type'] == 'bearish']
            summary.append(f"🧱 FAIR VALUE GAPS (FVGs):")
            if bullish_fvgs:
                summary.append(f"   - Bullish FVGs: {len(bullish_fvgs)} found (Top: {bullish_fvgs[0].get('top')}, Bottom: {bullish_fvgs[0].get('bottom')})")
            if bearish_fvgs:
                summary.append(f"   - Bearish FVGs: {len(bearish_fvgs)} found (Top: {bearish_fvgs[0].get('top')}, Bottom: {bearish_fvgs[0].get('bottom')})")
        else:
            summary.append("🧱 FAIR VALUE GAPS: None detected nearby.")

        # Order Blocks
        obs = ltf.get("order_blocks", [])
        if obs:
            bullish_obs = [o for o in obs if o['type'] == 'bullish']
            bearish_obs = [o for o in obs if o['type'] == 'bearish']
            summary.append(f"🛡️ ORDER BLOCKS:")
            if bullish_obs:
                summary.append(f"   - Bullish OBs: {len(bullish_obs)} levels (e.g., {bullish_obs[0].get('price_level')})")
            if bearish_obs:
                summary.append(f"   - Bearish OBs: {len(bearish_obs)} levels (e.g., {bearish_obs[0].get('price_level')})")

        # Momentum
        rsi = ltf.get("rsi")
        if rsi:
            summary.append(f"📈 MOMENTUM:")
            summary.append(f"   - RSI (14): {rsi:.2f} ({'Overbought' if rsi>70 else 'Oversold' if rsi<30 else 'Neutral'})")

        return "\n".join(summary)

class SentimentAnalyst(BaseAgent):
    def __init__(self):
        super().__init__("SentimentAnalyst")
        # In the future, this will use FinGPT or specialized news APIs
        # For now, we can reuse the news agent from the original codebase if available,
        # or just return a placeholder/mock if the news agent isn't easily decoupled.
        from news_agent import NewsAgent
        self.news_agent = NewsAgent()

    async def analyze(self, token: str) -> Dict[str, Any]:
        # Handle Wrapped tokens for news search
        search_token = token
        if token.upper() == "WBTC":
            search_token = "BTC"
        elif token.upper() == "WETH":
            search_token = "ETH"
            
        print(f"[{self.name}] Fetching news for {search_token} (derived from {token})...", flush=True)
        # The original news agent is synchronous, so we might want to run it in an executor
        # But for simplicity in this phase, we'll call it directly if it's fast enough,
        # or wrap it.
        try:
            news_summary = self.news_agent.fetch_news(search_token)
            return {
                "summary": news_summary,
                "score": 0.0 # Placeholder for numeric score
            }
        except Exception as e:
            print(f"[{self.name}] Error fetching news: {e}")
            return {"summary": "No news available.", "score": 0.0}

class FundamentalAnalyst(BaseAgent):
    def __init__(self):
        super().__init__("FundamentalAnalyst")

    async def analyze(self, token: str) -> Dict[str, Any]:
        # Placeholder for RAG implementation
        return {
            "summary": "Fundamental analysis not yet implemented.",
            "score": 50
        }

class MasterTrader(BaseAgent):
    def __init__(self):
        super().__init__("MasterTrader")
        self.core_agent = TraderAgent()

    async def make_decision(self, debate_transcript: str) -> Dict[str, Any]:
        print(f"[{self.name}] Reviewing debate transcript...", flush=True)
        
        # The prompt is already imported
        from .prompts import MASTER_TRADER_PROMPT
        
        # Call Gemini via core agent
        # We pass the transcript as the user prompt
        decision = await self.core_agent._call_gemini(debate_transcript, MASTER_TRADER_PROMPT)
        
        return decision
