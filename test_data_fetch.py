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
    
    market_data, ohlcv_data = await agent.fetch_data(token, chain)
    
    print("\n--- Market Data ---")
    print(market_data)
    
    print("\n--- OHLCV Data Keys ---")
    print(ohlcv_data.keys())
    
    for tf, data in ohlcv_data.items():
        print(f"{tf}: {len(data)} candles")
        if data:
            print(f"First candle: {data[0]}")
            print(f"Last candle: {data[-1]}")

if __name__ == "__main__":
    asyncio.run(main())
