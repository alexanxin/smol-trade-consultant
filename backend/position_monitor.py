import asyncio
import sys
import os
import logging
from typing import Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aiohttp
from backend.position_manager import PositionManager, Position
from backend.execution import ExecutionEngine
from backend.config import Config
from trader_agent_core import TraderAgent

# Create logger
logger = logging.getLogger("PositionMonitor")


class PositionMonitor:
    """Continuously monitors positions and triggers exits when conditions are met."""
    
    def __init__(self, execution_mode: str = "spot", dry_run: bool = True, 
                 token: str = "SOL", monitor_interval: int = 30,
                 trailing_stop: bool = False, trailing_distance: float = 2.0):
        """
        Initialize Position Monitor.
        
        Args:
            execution_mode: 'spot' or 'leverage'
            dry_run: If True, simulate exits without actual trades
            token: Default token symbol
            monitor_interval: Seconds between monitoring checks
            trailing_stop: Enable trailing stop-loss
            trailing_distance: Trailing stop distance as percentage (e.g., 2.0 for 2%)
        """
        self.execution_mode = execution_mode
        self.dry_run = dry_run
        self.token = token
        self.monitor_interval = monitor_interval
        self.trailing_stop = trailing_stop
        self.trailing_distance = trailing_distance / 100.0  # Convert percentage to decimal
        self.running = False
        
        # Initialize components
        self.position_manager = PositionManager()
        self.execution_engine = ExecutionEngine(mode=execution_mode, dry_run=dry_run)
        self.trader_agent = TraderAgent()
        
        trailing_info = f", trailing_stop={trailing_stop}" if trailing_stop else ""
        print(f"[PositionMonitor] Initialized (mode={execution_mode}, dry_run={dry_run}, interval={monitor_interval}s{trailing_info})")
    
    async def start(self):
        """Start the monitoring loop."""
        self.running = True
        print("[PositionMonitor] Starting monitoring loop...")
        
        try:
            await self.monitor_loop()
        except asyncio.CancelledError:
            print("[PositionMonitor] Monitoring cancelled")
            self.running = False
        except Exception as e:
            print(f"[PositionMonitor] Error in monitoring loop: {e}")
            self.running = False
            raise
    
    def stop(self):
        """Stop the monitoring loop."""
        self.running = False
        print("[PositionMonitor] Stopping monitoring loop...")
    
    async def monitor_loop(self):
        """Main monitoring loop - continuously checks all positions."""
        while self.running:
            try:
                positions = self.position_manager.get_all_positions()
                
                if positions:
                    print(f"\n[PositionMonitor] Checking {len(positions)} position(s)...")
                    
                    # Check each position
                    for position in positions:
                        await self.check_position(position)
                
                # Sleep for interval
                await asyncio.sleep(self.monitor_interval)
                
            except Exception as e:
                print(f"[PositionMonitor] Error in monitor loop: {e}")
                await asyncio.sleep(self.monitor_interval)
    
    async def check_position(self, position: Position):
        """
        Check a single position for exit conditions.
        
        Args:
            position: Position to check
        """
        try:
            # Enable trailing stop if configured
            if self.trailing_stop and not position.trailing_stop_enabled:
                position.trailing_stop_enabled = True
                position.trailing_stop_distance = self.trailing_distance
                print(f"[PositionMonitor] Enabled trailing stop for position {position.trade_id} ({self.trailing_distance*100:.1f}%)")
            
            # Fetch current price
            current_price = await self.fetch_current_price(position.token_address, position.symbol)
            
            if not current_price:
                print(f"[PositionMonitor] Could not fetch price for {position.symbol}")
                return
            
            # Update position with current price (this also updates trailing stop if enabled)
            self.position_manager.update_position_price(position.trade_id, current_price)
            
            # Calculate P&L
            pnl = position.calculate_pnl(current_price)
            pnl_pct = position.calculate_pnl_percentage(current_price)
            
            print(f"[PositionMonitor] Position {position.trade_id} ({position.symbol}):")
            print(f"   Entry: ${position.entry_price:.4f}, Current: ${current_price:.4f}")
            print(f"   P&L: ${pnl:.2f} ({pnl_pct:+.2f}%)")
            print(f"   SL: ${position.stop_loss:.4f}, TP: ${position.take_profit:.4f}")
            if position.trailing_stop_enabled and position.trailing_stop_price:
                print(f"   Trailing Stop: ${position.trailing_stop_price:.4f}")
            
            # Check exit conditions
            exit_reason = self.position_manager.check_exit_conditions(position)
            
            if exit_reason:
                print(f"[PositionMonitor] Exit condition met: {exit_reason}")
                await self.execute_exit(position, current_price, exit_reason)
            
        except Exception as e:
            print(f"[PositionMonitor] Error checking position {position.trade_id}: {e}")
    
    async def fetch_current_price(self, token_address: str, symbol: str) -> Optional[float]:
        """
        Fetch current price for a token using Birdeye API with CoinGecko fallback.
        """
        if not token_address:
            print(f"[PositionMonitor] Cannot fetch price for {symbol}: No token address provided")
            return None
        
        # Try Birdeye first
        price = await self._fetch_price_birdeye(token_address, symbol)
        if price:
            return price
        
        # Fallback to CoinGecko
        print(f"[PositionMonitor] Falling back to CoinGecko for {symbol} price...")
        price = await self._fetch_price_coingecko(token_address, symbol)
        if price:
            print(f"[PositionMonitor] ✓ Got price from CoinGecko: ${price:.4f}")
            return price
        
        print(f"[PositionMonitor] ❌ All price sources failed for {symbol}")
        return None
    
    async def _fetch_price_birdeye(self, token_address: str, symbol: str) -> Optional[float]:
        """Fetch price from Birdeye API."""
        api_key = Config.BIRDEYE_API_KEY
        if not api_key:
            print(f"[PositionMonitor] Birdeye API key not configured")
            return None
            
        url = f"https://public-api.birdeye.so/defi/price?address={token_address}"
        headers = {"X-API-KEY": api_key}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        price = data.get('data', {}).get('value')
                        if price:
                            return price
                        else:
                            print(f"[PositionMonitor] Price not found in Birdeye response for {symbol}")
                    else:
                        error_text = await response.text()
                        print(f"[PositionMonitor] Birdeye API error for {symbol}: HTTP {response.status}")
                        if response.status == 400 and "limit exceeded" in error_text.lower():
                            print(f"[PositionMonitor] Birdeye rate limit exceeded")
                        else:
                            print(f"[PositionMonitor] Error response: {error_text}")
        except asyncio.TimeoutError:
            print(f"[PositionMonitor] Timeout fetching price from Birdeye API")
        except Exception as e:
            print(f"[PositionMonitor] Birdeye error: {type(e).__name__}: {e}")
            
        return None
    
    async def _fetch_price_coingecko(self, token_address: str, symbol: str) -> Optional[float]:
        """Fetch price from CoinGecko API."""
        api_key = Config.COINGECKO_API_KEY
        
        # Map token addresses to CoinGecko IDs
        # For Solana tokens, we need to use the contract address
        token_id_map = {
            "So11111111111111111111111111111111111111111": "solana",  # Wrapped SOL
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "usd-coin",  # USDC
        }
        
        # Try to get CoinGecko ID from map, otherwise use the address
        coingecko_id = token_id_map.get(token_address)
        
        if coingecko_id:
            # Use simple price API for known tokens
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={coingecko_id}&vs_currencies=usd"
        else:
            # For unknown tokens, try the token price by contract address
            # Note: This requires the token to be listed on CoinGecko
            url = f"https://api.coingecko.com/api/v3/simple/token_price/solana?contract_addresses={token_address}&vs_currencies=usd"
        
        headers = {}
        if api_key:
            headers["x-cg-demo-api-key"] = api_key
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Extract price based on which endpoint we used
                        if coingecko_id:
                            price = data.get(coingecko_id, {}).get('usd')
                        else:
                            price = data.get(token_address.lower(), {}).get('usd')
                        
                        if price:
                            return float(price)
                        else:
                            print(f"[PositionMonitor] Price not found in CoinGecko response")
                    else:
                        error_text = await response.text()
                        print(f"[PositionMonitor] CoinGecko API error: HTTP {response.status}")
                        if response.status == 429:
                            print(f"[PositionMonitor] CoinGecko rate limit exceeded")
        except asyncio.TimeoutError:
            print(f"[PositionMonitor] Timeout fetching price from CoinGecko API")
        except Exception as e:
            print(f"[PositionMonitor] CoinGecko error: {type(e).__name__}: {e}")
            
        return None
    
    async def execute_exit(self, position: Position, exit_price: float, exit_reason: str):
        """
        Execute exit for a position.
        
        Args:
            position: Position to exit
            exit_price: Current market price
            exit_reason: Reason for exit (STOP_LOSS, TAKE_PROFIT, etc.)
        """
        print(f"\n[PositionMonitor] ========================================")
        print(f"[PositionMonitor]   EXECUTING EXIT")
        print(f"[PositionMonitor] ========================================")
        print(f"[PositionMonitor] Position: {position.trade_id} ({position.symbol})")
        print(f"[PositionMonitor] Reason: {exit_reason}")
        print(f"[PositionMonitor] Exit Price: ${exit_price:.4f}")
        
        if self.dry_run:
            print(f"[PositionMonitor] DRY RUN - Simulating exit")
            result = {
                "status": "simulated",
                "action": "SELL",
                "token": position.symbol,
                "price": exit_price
            }
        else:
            # Execute actual sell order
            print(f"[PositionMonitor] Executing SELL order via ExecutionEngine...")
            
            # Create a decision-like structure for execution engine
            decision = {
                "action": "SELL",
                "plan": {
                    "entry": exit_price,
                    "position_size_pct": 1.0  # Sell 100% of position
                }
            }
            
            try:
                result = await self.execution_engine.execute_decision(decision, position.symbol)
            except Exception as e:
                print(f"[PositionMonitor] Error executing sell: {e}")
                result = {"error": str(e)}
        
        # Close position in database
        self.position_manager.close_position(position.trade_id, exit_price, exit_reason)
        
        print(f"[PositionMonitor] ========================================")
        if "signature" in result:
            print(f"[PositionMonitor] ✅ EXIT SUCCESS: {result['signature']}")
        elif "error" in result:
            print(f"[PositionMonitor] ❌ EXIT ERROR: {result['error']}")
        else:
            print(f"[PositionMonitor] ℹ️  EXIT SIMULATED")
        print(f"[PositionMonitor] ========================================\n")
