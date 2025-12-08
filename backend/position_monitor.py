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
                 trailing_stop: bool = False, trailing_distance: float = 2.0,
                 market_timing=None):
        """
        Initialize Position Monitor.

        Args:
            execution_mode: 'spot' or 'leverage'
            dry_run: If True, simulate exits without actual trades
            token: Default token symbol
            monitor_interval: Seconds between monitoring checks
            trailing_stop: Enable trailing stop-loss
            trailing_distance: Trailing stop distance as percentage (e.g., 2.0 for 2%)
            market_timing: Optional MarketTiming instance to share price history
        """
        self.execution_mode = execution_mode
        self.dry_run = dry_run
        self.token = token
        self.monitor_interval = monitor_interval
        self.trailing_stop = trailing_stop
        self.trailing_distance = trailing_distance / 100.0  # Convert percentage to decimal
        self.running = False
        self.market_timing = market_timing  # Shared MarketTiming instance

        # Initialize components
        self.position_manager = PositionManager()
        self.execution_engine = ExecutionEngine(mode=execution_mode, dry_run=dry_run)
        self.trader_agent = TraderAgent()

        trailing_info = f", trailing_stop={trailing_stop}" if trailing_stop else ""
        print(f"[PositionMonitor] Initialized (mode={execution_mode}, dry_run={dry_run}, interval={monitor_interval}s{trailing_info})")
    
    async def start(self):
        """Start the monitoring loop."""
        self.running = True
        positions = self.position_manager.get_all_positions()
        position_count = len(positions)
        print(f"[PositionMonitor] Starting monitoring loop... ({position_count} positions to monitor)")

        if position_count == 0:
            print("[PositionMonitor] ℹ️  No active positions - monitoring paused until positions exist")

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
        check_count = 0
        while self.running:
            try:
                check_count += 1
                positions = self.position_manager.get_all_positions()

                if positions:
                    print(f"\n[PositionMonitor] 🔍 Check #{check_count} - Monitoring {len(positions)} position(s) at {self.monitor_interval}s intervals")

                    # Check each position
                    for position in positions:
                        await self.check_position(position)
                else:
                    # Show market status information even with no positions
                    await self.show_market_status(check_count)

                # Sleep for interval
                await asyncio.sleep(self.monitor_interval)

            except Exception as e:
                print(f"[PositionMonitor] ❌ Error in check #{check_count}: {e}")
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
        Fetch current price using TraderAgent's robust fetching logic (Birdeye -> Jupiter -> CoinGecko OHLCV).
        """
        try:
            # Use TraderAgent to fetch data
            # We assume chain is 'solana' for now as per current scope
            # Note: fetch_data resolves address from symbol. If we want to use address directly,
            # we might need to update TraderAgent, but for now symbol resolution should work
            # as we likely found the token via TraderAgent initially.
            market_data, _ = await self.trader_agent.fetch_data(symbol, "solana")
            
            price = market_data.get('value')
            if price:
                return float(price)
                
            print(f"[PositionMonitor] ❌ All price sources failed for {symbol}")
            return None
            
        except Exception as e:
            print(f"[PositionMonitor] Error fetching price via TraderAgent: {e}")
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

    async def show_market_status(self, check_count: int):
        """
        Show market status information even when no positions exist.

        Args:
            check_count: Current check number for display
        """
        try:
            # Fetch current market data on EVERY check to build price history
            market_data, _ = await self.trader_agent.fetch_data(self.token, "solana")
            current_price = market_data.get('value', 0) if market_data else None

            if current_price and self.market_timing:
                # ALWAYS update price history for volatility tracking (even if not displaying)
                self.market_timing.update_price_history(current_price)

            # Display status less frequently to avoid spam
            if check_count % 5 == 1:  # Every 5th check (every 2.5 minutes at 30s intervals)
                if current_price and self.market_timing:
                    # Use shared market timing instance with updated price history
                    status = self.market_timing.get_current_market_status(current_price)

                    # Display market status
                    volatility_icon = {"low": "🟢", "medium": "🟡", "high": "🟠", "extreme": "🔴", "unknown": "⚪"}.get(status.volatility_level, "⚪")

                    print(f"\n[PositionMonitor] 📊 Market Status (Check #{check_count})")
                    print(f"[PositionMonitor]    💰 Price: ${current_price:.4f}")
                    print(f"[PositionMonitor]    {volatility_icon} Volatility: {status.volatility_level.upper()}")

                    # Show volume if available
                    volume = market_data.get('volume') or market_data.get('v24h')
                    if volume:
                        print(f"[PositionMonitor]    📊 24h Volume: {volume:,.0f}")

                    # Show liquidity if available
                    liquidity = market_data.get('liquidity')
                    if liquidity:
                        print(f"[PositionMonitor]    💧 Liquidity: {liquidity:,.0f}")

                    # Show current session
                    session_name = status.current_session.name if status.current_session else "Outside sessions"
                    print(f"[PositionMonitor]    📅 Session: {session_name}")

                    # Show ORB strategy readiness
                    should_run_orb, orb_reason = self.market_timing.should_run_orb_strategy(current_price)
                    orb_status = "✅ READY" if should_run_orb else "⏸️  WAITING"
                    print(f"[PositionMonitor]    🎯 ORB Strategy: {orb_status} - {orb_reason}")

                    # Show recommendation
                    print(f"[PositionMonitor]    💡 {status.recommendation}")

        except Exception as e:
            # Don't spam with errors, just log occasionally
            if check_count % 10 == 1:  # Every 10th check
                print(f"[PositionMonitor] ⚠️  Market status check failed: {e}")
