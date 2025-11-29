import os
from dotenv import load_dotenv
from wallet_manager import SolanaWallet
from jupiter_client import JupiterClient

# Load env
load_dotenv()

def verify_integration():
    print("🔍 Verifying Solana Wallet & Jupiter Integration...")
    
    # 1. Test Wallet
    print("\n1. Testing Wallet Manager...")
    wallet = SolanaWallet()
    if wallet.keypair:
        print(f"✅ Wallet loaded successfully: {wallet.get_public_key()}")
        balance = wallet.get_balance()
        print(f"   Balance: {balance} SOL")
    else:
        print("⚠️  No private key found in .env. Please add SOLANA_PRIVATE_KEY to test signing.")
        # Create a dummy wallet for testing Jupiter if no real key
        print("   Creating dummy wallet for Jupiter test...")
        from solders.keypair import Keypair
        wallet.keypair = Keypair()
        print(f"   Dummy Wallet: {wallet.get_public_key()}")

    # 2. Test Jupiter Quote
    print("\n2. Testing Jupiter Quote API...")
    jupiter = JupiterClient(wallet)
    
    # SOL -> USDC
    input_mint = "So11111111111111111111111111111111111111112" # SOL
    output_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v" # USDC
    amount = 10000000 # 0.01 SOL
    
    quote = jupiter.get_quote(input_mint, output_mint, amount)
    
    if quote:
        print("✅ Quote fetched successfully!")
        print(f"   Input: {int(quote['inAmount']) / 1e9} SOL")
        print(f"   Output: {int(quote['outAmount']) / 1e6} USDC")
        print(f"   Price Impact: {quote.get('priceImpactPct', 'N/A')}%")
    else:
        print("❌ Failed to fetch quote.")

if __name__ == "__main__":
    verify_integration()
