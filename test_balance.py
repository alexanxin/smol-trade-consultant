#!/usr/bin/env python3
"""
Quick test to verify wallet balance using alternative method
"""
import os
from dotenv import load_dotenv
from solana.rpc.api import Client
from solders.keypair import Keypair
import base58

load_dotenv()

private_key = os.getenv("SOLANA_PRIVATE_KEY")
rpc_url = os.getenv("RPC_URL", "https://mainnet.helius-rpc.com/?api-key=d44985e5-048b-42ed-885f-e3f4ba38d5fc")

if private_key:
    try:
        decoded_key = base58.b58decode(private_key)
        keypair = Keypair.from_bytes(decoded_key)
        
        print(f"Wallet: {keypair.pubkey()}")
        
        client = Client(rpc_url)
        
        # Try to get balance
        try:
            result = client.get_balance(keypair.pubkey())
            print(f"Raw response: {result}")
            print(f"Response type: {type(result)}")
            
            if hasattr(result, 'value'):
                balance = result.value / 1e9
                print(f"✅ Balance: {balance} SOL")
            else:
                print(f"⚠️  Unexpected response format")
        except Exception as e:
            print(f"❌ Balance fetch error: {e}")
            
    except Exception as e:
        print(f"❌ Wallet error: {e}")
else:
    print("❌ No SOLANA_PRIVATE_KEY in .env")
