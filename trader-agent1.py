#!/usr/bin/env python3
import os
import json
import sys
import argparse
import asyncio
from dotenv import load_dotenv
from trader_agent_core import TraderAgent

# Load environment variables
load_dotenv()

async def main():
    parser = argparse.ArgumentParser(description="AI Trading Agent CLI")
    parser.add_argument("--token", type=str, required=True, help="Token symbol (e.g., SOL, BTC)")
    parser.add_argument("--chain", type=str, default="solana", help="Blockchain network (default: solana)")
    parser.add_argument("--mode", type=str, default="signal", choices=["signal", "analysis"], help="Output mode")
    parser.add_argument("--ai-provider", type=str, default="gemini", help="AI Provider (default: gemini)")
    
    args = parser.parse_args()
    
    try:
        agent = TraderAgent()
        
        # Fetch Data
        print(f"Fetching data for {args.token} on {args.chain}...")
        market_data, ohlcv_data = await agent.fetch_data(args.token, args.chain)
        
        if "error" in market_data:
            print(json.dumps({"error": market_data["error"]}))
            return

        # Analyze Market
        print("Analyzing market data...")
        analysis_result = agent.analyze_market(market_data, ohlcv_data)
        analysis_result["coin_symbol"] = args.token
        
        if args.mode == "analysis":
            print(json.dumps(analysis_result, default=str, indent=2))
        else:
            # Generate Signal
            print(f"Generating signal using {args.ai_provider}...")
            signal = await agent.generate_signal(analysis_result, args.ai_provider)
            print(json.dumps(signal, indent=2))
            
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(0)
