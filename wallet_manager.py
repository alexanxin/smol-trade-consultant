import os
import base58
from solana.rpc.api import Client
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction

class SolanaWallet:
    def __init__(self):
        self.private_key = os.getenv("SOLANA_PRIVATE_KEY")
        # Correct Helius RPC endpoint (not the transactions API)
        self.rpc_url = os.getenv("RPC_URL", "https://mainnet.helius-rpc.com/?api-key=d44985e5-048b-42ed-885f-e3f4ba38d5fc")
        self.client = Client(self.rpc_url)
        self.keypair = None
        
        if self.private_key:
            try:
                # Try decoding as base58 (Phantom export format)
                decoded_key = base58.b58decode(self.private_key)
                self.keypair = Keypair.from_bytes(decoded_key)
            except Exception:
                try:
                    # Try as raw bytes or list of integers (Solana CLI format)
                    import json
                    key_data = json.loads(self.private_key)
                    self.keypair = Keypair.from_bytes(bytes(key_data))
                except Exception as e:
                    print(f"❌ Error loading private key: {e}")
                    self.keypair = None
        
        if self.keypair:
            print(f"✅ Wallet loaded: {self.keypair.pubkey()}")
        else:
            print("⚠️  No valid wallet loaded. Trading will be simulated.")

    def get_public_key(self):
        return self.keypair.pubkey() if self.keypair else None

    def get_balance(self):
        if not self.keypair:
            return 0.0
        try:
            response = self.client.get_balance(self.keypair.pubkey())
            if hasattr(response, 'value'):
                return response.value / 1e9  # Convert lamports to SOL
            else:
                # Try alternative response format
                return float(response) / 1e9 if response else 0.0
        except Exception as e:
            print(f"⚠️  Warning: Could not fetch balance: {e}")
            print(f"   This won't prevent trading, continuing...")
            return 0.0

    def sign_and_send_transaction(self, transaction_bytes):
        """
        Signs and sends a versioned transaction (required for Jupiter).
        """
        if not self.keypair:
            return {"error": "No wallet loaded"}

        try:
            # Deserialize the transaction from bytes
            if isinstance(transaction_bytes, bytes):
                tx = VersionedTransaction.from_bytes(transaction_bytes)
            else:
                tx = transaction_bytes

            # Sign the transaction using the keypair directly
            # Create a new signed transaction
            from solders.transaction import VersionedTransaction as VT
            signed_tx = VT(tx.message, [self.keypair])

            # Send the transaction with skip_preflight to avoid blockhash expiration
            print(f"   Sending transaction to RPC...")
            from solana.rpc.types import TxOpts
            opts = TxOpts(skip_preflight=True, preflight_commitment="confirmed")
            result = self.client.send_raw_transaction(bytes(signed_tx), opts=opts)
            
            if hasattr(result, 'value'):
                return {"signature": str(result.value)}
            else:
                return {"error": f"Unexpected response format: {result}"}
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"❌ Transaction failed: {e}")
            print(f"   Details: {error_details}")
            return {"error": str(e), "details": error_details}
