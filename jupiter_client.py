import requests
import base64
import json
import time

class JupiterClient:
    def __init__(self, wallet=None):
        # Using Lite API instead of regular API (more reliable)
        self.base_url = "https://lite-api.jup.ag/swap/v1"
        self.wallet = wallet
        # Common token mints
        self.SOL_MINT = "So11111111111111111111111111111111111111112"
        self.USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

    def get_quote(self, input_mint, output_mint, amount, slippage_bps=50):
        """
        Get a quote for a swap using Jupiter Lite API.
        amount: integer (lamports/atomic units)
        slippage_bps: basis points (50 = 0.5%)
        """
        url = f"{self.base_url}/quote"
        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": amount,
            "slippageBps": slippage_bps,
            "restrictIntermediateTokens": "true"  # Lite API parameter
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Error fetching Jupiter quote: {e}")
            return None

    def execute_swap(self, input_mint, output_mint, amount, slippage_bps=50):
        """
        Orchestrates the full swap process: Quote -> Swap Instructions -> Sign -> Send
        """
        if not self.wallet:
            return {"error": "No wallet configured"}

        print(f"🔄 Fetching quote for {amount} units...")
        quote_response = self.get_quote(input_mint, output_mint, amount, slippage_bps)
        
        if not quote_response:
            return {"error": "Failed to get quote"}

        print(f"   Quote received: {quote_response.get('outAmount')} output units")

        # Get serialized transaction
        swap_url = f"{self.base_url}/swap"
        payload = {
            "quoteResponse": quote_response,
            "userPublicKey": str(self.wallet.get_public_key()),
            "wrapAndUnwrapSol": True
        }
        
        try:
            print("🔄 Requesting swap transaction...")
            response = requests.post(swap_url, json=payload)
            response.raise_for_status()
            swap_data = response.json()
            
            # The transaction is returned as base64 encoded string
            swap_transaction_b64 = swap_data.get("swapTransaction")
            if not swap_transaction_b64:
                return {"error": "No swap transaction returned"}
                
            # Decode base64 to bytes
            transaction_bytes = base64.b64decode(swap_transaction_b64)
            
            # Sign and send
            print("✍️  Signing and sending transaction...")
            result = self.wallet.sign_and_send_transaction(transaction_bytes)
            return result
            
        except Exception as e:
            print(f"❌ Error executing swap: {e}")
            return {"error": str(e)}
