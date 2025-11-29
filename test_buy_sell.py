#!/usr/bin/env python3
"""
Test script to verify buy and sell functionality with Jupiter
This will execute a small test trade to verify the integration works
"""
import os
from dotenv import load_dotenv
from wallet_manager import SolanaWallet
from jupiter_client import JupiterClient

load_dotenv()

def test_buy_sell():
    print("🧪 Testing Buy/Sell Functionality\n")
    
    # Initialize wallet and Jupiter
    wallet = SolanaWallet()
    jupiter = JupiterClient(wallet)
    
    if not wallet.keypair:
        print("❌ No wallet configured. Add SOLANA_PRIVATE_KEY to .env")
        return
    
    print(f"Wallet: {wallet.get_public_key()}\n")
    
    # Test parameters
    SOL_MINT = "So11111111111111111111111111111111111111112"
    USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    
    # Very small amount for testing: 0.001 SOL
    amount_lamports = 1000000  # 0.001 SOL
    
    print("=" * 60)
    print("STEP 1: BUY TEST (SOL → USDC)")
    print("=" * 60)
    print(f"Amount: 0.001 SOL ({amount_lamports} lamports)\n")
    
    # Get quote first
    print("📊 Fetching quote...")
    quote = jupiter.get_quote(SOL_MINT, USDC_MINT, amount_lamports)
    
    if quote:
        output_amount = int(quote.get('outAmount', 0)) / 1e6  # USDC has 6 decimals
        print(f"✅ Quote: 0.001 SOL → {output_amount:.4f} USDC")
        print(f"   Price Impact: {quote.get('priceImpactPct', 'N/A')}%\n")
        
        # Ask for confirmation
        response = input("Execute BUY? (yes/no): ")
        if response.lower() == 'yes':
            print("\n🚀 Executing BUY...")
            result = jupiter.execute_swap(SOL_MINT, USDC_MINT, amount_lamports)
            
            if "signature" in result:
                print(f"✅ BUY Successful!")
                print(f"   Signature: {result['signature']}")
                print(f"   View on Solscan: https://solscan.io/tx/{result['signature']}\n")
                
                # Now test selling back
                print("=" * 60)
                print("STEP 2: SELL TEST (USDC → SOL)")
                print("=" * 60)
                
                # Use the amount we just received
                sell_amount = int(quote.get('outAmount', 0))
                print(f"Amount: {sell_amount / 1e6:.4f} USDC ({sell_amount} units)\n")
                
                print("📊 Fetching sell quote...")
                sell_quote = jupiter.get_quote(USDC_MINT, SOL_MINT, sell_amount)
                
                if sell_quote:
                    sol_back = int(sell_quote.get('outAmount', 0)) / 1e9
                    print(f"✅ Quote: {sell_amount / 1e6:.4f} USDC → {sol_back:.6f} SOL")
                    print(f"   Price Impact: {sell_quote.get('priceImpactPct', 'N/A')}%\n")
                    
                    response = input("Execute SELL? (yes/no): ")
                    if response.lower() == 'yes':
                        print("\n🚀 Executing SELL...")
                        sell_result = jupiter.execute_swap(USDC_MINT, SOL_MINT, sell_amount)
                        
                        if "signature" in sell_result:
                            print(f"✅ SELL Successful!")
                            print(f"   Signature: {sell_result['signature']}")
                            print(f"   View on Solscan: https://solscan.io/tx/{sell_result['signature']}\n")
                            
                            print("=" * 60)
                            print("🎉 COMPLETE CYCLE TEST PASSED!")
                            print("=" * 60)
                        else:
                            print(f"❌ SELL Failed: {sell_result.get('error')}")
                else:
                    print("❌ Failed to get sell quote")
            else:
                print(f"❌ BUY Failed: {result.get('error')}")
        else:
            print("❌ BUY cancelled by user")
    else:
        print("❌ Failed to get quote")

if __name__ == "__main__":
    test_buy_sell()
