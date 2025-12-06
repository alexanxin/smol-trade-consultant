import asyncio
import logging
from trader_agent_core import TraderAgent
from backend.config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestFetch")

async def main():
    agent = TraderAgent()
    token = "SOL"
    chain = "solana"
    
    print(f"Testing data fetch for {token} on {chain}...")
    print(f"Birdeye Key present: {bool(Config.BIRDEYE_API_KEY)}")
    print(f"CoinGecko Key present: {bool(Config.COINGECKO_API_KEY)}")
    
    # Test Jupiter
    from jupiter_client import JupiterClient
    jup = JupiterClient()
    print("\n--- Testing Jupiter ---")
    try:
        quote = jup.get_quote("So11111111111111111111111111111111111111112", Config.USDC_MINT, 10**9)
        print(f"Quote: {quote}")
    except Exception as e:
        print(f"Jupiter Error: {e}")

    market_data, ohlcv_data = await agent.fetch_data(token, chain)
    
    print("\n--- Market Data ---")
    print(market_data)

    print("\n--- Running Analysis ---")
    analysis = agent.analyze_market(market_data, ohlcv_data)
    
    print("\n--- Fibonacci Levels (Daily) ---")
    daily_fib = analysis.get("technical_analysis", {}).get("daily", {}).get("fibonacci", {})
    print(daily_fib)

    print("\n--- Order Blocks (Daily) ---")
    daily_obs = analysis.get("technical_analysis", {}).get("daily", {}).get("order_blocks", [])
    for ob in daily_obs:
        print(ob)
        
    print("\n--- Fibonacci Levels (HTF) ---")
    htf_fib = analysis.get("technical_analysis", {}).get("htf", {}).get("fibonacci", {})
    print(htf_fib)

if __name__ == "__main__":
    asyncio.run(main())
