import asyncio
import os
import base58
from driftpy.drift_client import DriftClient
from driftpy.account_subscription_config import AccountSubscriptionConfig
from driftpy.types import MarketType, PositionDirection, OrderType, OrderParams
from driftpy.constants.numeric_constants import BASE_PRECISION, QUOTE_PRECISION
from anchorpy import Provider, Wallet
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solders.pubkey import Pubkey

class DriftClientWrapper:
    def __init__(self):
        self.env = "mainnet" 
        self.private_key = os.getenv("SOLANA_PRIVATE_KEY")
        # Use Helius RPC for Drift as well
        self.rpc_url = os.getenv("RPC_URL", "https://mainnet.helius-rpc.com/?api-key=d44985e5-048b-42ed-885f-e3f4ba38d5fc")
        self.keypair = None
        
        if self.private_key:
            try:
                decoded_key = base58.b58decode(self.private_key)
                self.keypair = Keypair.from_bytes(decoded_key)
            except Exception as e:
                print(f"❌ Error loading private key for Drift: {e}")

    async def _get_client(self):
        if not self.keypair:
            return None
            
        connection = AsyncClient(self.rpc_url)
        wallet = Wallet(self.keypair)
        provider = Provider(connection, wallet)
        
        client = DriftClient(
            provider.connection,
            provider.wallet,
            self.env,
            account_subscription=AccountSubscriptionConfig("cached")
        )
        await client.subscribe()
        return client

    def get_perp_market_index(self, symbol):
        # Map symbol to Drift Perp Market Index
        # This is a simplified map, in production you'd query the markets
        symbol_map = {
            "SOL": 0,
            "BTC": 1,
            "ETH": 2,
            # Add more as needed
        }
        return symbol_map.get(symbol.upper())

    def open_position(self, symbol, direction, amount_sol, leverage=1):
        """
        Open a perpetual position.
        direction: 'LONG' or 'SHORT'
        amount_sol: Size of position in SOL (not collateral, but notional value?) 
                   Or collateral amount? 
                   Drift takes base_asset_amount usually.
        """
        async def _action():
            client = await self._get_client()
            if not client:
                return {"error": "No wallet"}
            
            try:
                market_index = self.get_perp_market_index(symbol)
                if market_index is None:
                    return {"error": f"Market {symbol} not supported on Drift"}

                # Convert amount to base precision
                # amount_sol is the amount of token to buy/sell
                base_asset_amount = int(amount_sol * BASE_PRECISION)
                
                drift_direction = PositionDirection.Long() if direction == 'LONG' else PositionDirection.Short()
                
                order_params = OrderParams(
                    order_type=OrderType.Market(),
                    market_type=MarketType.Perp(),
                    market_index=market_index,
                    user_order_id=0,
                    direction=drift_direction,
                    base_asset_amount=base_asset_amount,
                    price=0, # Market order
                    reduce_only=False
                )

                print(f"🔄 Placing Drift {direction} order for {amount_sol} {symbol}...")
                tx_sig = await client.place_perp_order(order_params)
                print(f"✅ Drift Order Placed: {tx_sig}")
                return {"signature": str(tx_sig)}
                
            except Exception as e:
                print(f"❌ Drift Order Failed: {e}")
                return {"error": str(e)}
            finally:
                await client.unsubscribe()
                await client.program.provider.connection.close()

        return asyncio.run(_action())

    def close_position(self, symbol):
        """
        Close all positions for a symbol.
        """
        async def _action():
            client = await self._get_client()
            if not client:
                return {"error": "No wallet"}
            
            try:
                market_index = self.get_perp_market_index(symbol)
                if market_index is None:
                    return {"error": f"Market {symbol} not supported"}

                # Get user position
                user = client.get_user()
                position = user.get_perp_position(market_index)
                
                if not position or position.base_asset_amount == 0:
                    return {"error": "No open position to close"}

                # Determine direction to close (opposite of current)
                direction = PositionDirection.Short() if position.base_asset_amount > 0 else PositionDirection.Long()
                base_amount = abs(position.base_asset_amount)

                order_params = OrderParams(
                    order_type=OrderType.Market(),
                    market_type=MarketType.Perp(),
                    market_index=market_index,
                    user_order_id=0,
                    direction=direction,
                    base_asset_amount=base_amount,
                    price=0,
                    reduce_only=True
                )

                print(f"🔄 Closing Drift position for {symbol}...")
                tx_sig = await client.place_perp_order(order_params)
                return {"signature": str(tx_sig)}
                
            except Exception as e:
                print(f"❌ Drift Close Failed: {e}")
                return {"error": str(e)}
            finally:
                await client.unsubscribe()
                await client.program.provider.connection.close()

        return asyncio.run(_action())
