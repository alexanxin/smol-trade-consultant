import os
from dotenv import load_dotenv
from drift_client_wrapper import DriftClientWrapper

load_dotenv()

def test_drift():
    print("🧪 Testing Drift Client Wrapper...")
    
    drift = DriftClientWrapper()
    
    if not drift.keypair:
        print("❌ No wallet configured")
        return

    print(f"✅ Wallet: {drift.keypair.pubkey()}")
    
    # Initialize (connects to RPC)
    # drift.initialize() # This prints success if works
    
    # Test market lookup
    idx = drift.get_perp_market_index("SOL")
    print(f"✅ SOL Market Index: {idx}")
    
    # Don't actually trade in this test unless user confirms
    # print("Attempting to open small position...")
    # drift.open_position("SOL", "LONG", 0.1)

if __name__ == "__main__":
    test_drift()
