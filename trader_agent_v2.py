#!/usr/bin/env python3
import asyncio
import os
import sys
import argparse
import time
import requests
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.event_bus import EventBus, Event
from backend.state_manager import StateManager
from backend.orchestrator import Orchestrator
from backend.position_monitor import PositionMonitor

# Load environment variables
load_dotenv()

class TraderAgentV2:
    def __init__(self, execution_mode: str = None, dry_run: bool = True, token: str = "SOL", 
                 monitor_interval: int = 30, trailing_stop: bool = False, trailing_distance: float = 2.0):
        print("Initializing Trader Agent V2 (TiMi Architecture)...")
        self.execution_mode = execution_mode
        self.dry_run = dry_run
        self.token = token
        self.monitor_interval = monitor_interval
        self.trailing_stop = trailing_stop
        self.trailing_distance = trailing_distance
        
        self.event_bus = EventBus()
        self.state_manager = StateManager()
        self.orchestrator = Orchestrator(
            self.state_manager,
            execution_mode=execution_mode,
            dry_run=dry_run,
            token=token
        )
        
        # Initialize Position Monitor if execution mode enabled
        self.position_monitor = None
        if execution_mode:
            self.position_monitor = PositionMonitor(
                execution_mode=execution_mode,
                dry_run=dry_run,
                token=token,
                monitor_interval=monitor_interval,
                trailing_stop=trailing_stop,
                trailing_distance=trailing_distance
            )
        
    async def start(self):
        print("Starting Event Loop...")
        # Start Event Bus
        bus_task = asyncio.create_task(self.event_bus.start())
        
        # Start Position Monitor if enabled
        monitor_task = None
        if self.position_monitor:
            print(f"Starting Position Monitor (interval={self.monitor_interval}s)...")
            monitor_task = asyncio.create_task(self.position_monitor.start())
        
        try:
            while True:
                print("\n" + "="*50)
                print(f"   STARTING ANALYSIS CYCLE: {self.token}")
                print("="*50)
                
                # Run the full analysis cycle
                final_state = await self.orchestrator.run_cycle()
                
                # Extract decision (final_state is a GlobalState Pydantic model)
                decision = final_state.decision or {}
                action = decision.get("action", "WAIT")
                plan = decision.get("plan", {})
                token_address = final_state.token_address
                
                print(f"\nCycle Complete. Decision: {action}")
                
                # Smart Watch Logic
                if action == "WAIT" or (action == "SELL" and not self.position_monitor.get_all_positions()):
                    print("\n--- Entering Smart Watch Mode ---")
                    print("Monitoring price for opportunities (saving API calls)...")
                    
                    target_entry = plan.get("entry_price")
                    if target_entry:
                        print(f"Target Entry: ${target_entry:.4f}")
                    
                    # Watch loop configuration
                    watch_duration = 900  # 15 minutes max wait
                    check_interval = 30   # Check price every 30 seconds
                    start_time = time.time()
                    
                    while (time.time() - start_time) < watch_duration:
                        # 1. Fetch current price cheaply
                        current_price = self._fetch_price_cheaply(token_address)
                        
                        if current_price:
                            timestamp = time.strftime("%H:%M:%S")
                            print(f"[{timestamp}] Price: ${current_price:.4f}", end="\r")
                            
                            # 2. Check triggers
                            if target_entry:
                                # If price is within 0.5% of target, wake up
                                if abs(current_price - target_entry) / target_entry < 0.005:
                                    print(f"\n🎯 Price near target (${target_entry})! Triggering analysis...")
                                    break
                                    
                                # If price dips significantly (e.g. 2% drop), wake up
                                # (Requires tracking last price, omitted for simplicity)
                        
                        await asyncio.sleep(check_interval)
                    
                    print("\nWatch cycle ended. Refreshing analysis...")
                    
                else:
                    # If we took action (BUY/SELL), wait 1 minute before re-checking
                    print(f"\nAction taken. Waiting 60s before next cycle...")
                    await asyncio.sleep(60)
            
        except KeyboardInterrupt:
            print("\nShutting down...")
        except Exception as e:
            print(f"\n❌ CRITICAL ERROR in Main Loop: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.event_bus.stop()
            if self.position_monitor:
                self.position_monitor.stop()
            
            # Wait for tasks to complete
            if monitor_task:
                monitor_task.cancel()
                try:
                    await monitor_task
                except asyncio.CancelledError:
                    pass
            
            await bus_task

    def _fetch_price_cheaply(self, token_address):
        """Fetches current price using Birdeye API (lightweight)."""
        if not token_address:
            return None
            
        api_key = os.getenv("BIRDEYE_API_KEY")
        if not api_key:
            return None
            
        url = f"https://public-api.birdeye.so/defi/price?address={token_address}"
        headers = {"X-API-KEY": api_key}
        
        try:
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                return response.json().get('data', {}).get('value')
        except Exception:
            pass
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Trader Agent V2 - TiMi Architecture')
    parser.add_argument('--token', type=str, default='SOL', help='Token symbol to analyze (e.g., SOL, BONK, JUP)')
    parser.add_argument('--spot', action='store_true', help='Enable spot trading via Jupiter')
    parser.add_argument('--leverage', action='store_true', help='Enable leverage trading via Drift')
    parser.add_argument('--dry-run', dest='dry_run', action='store_true', default=True,
                        help='Simulate execution without actual trades (default: True)')
    parser.add_argument('--live', dest='dry_run', action='store_false',
                        help='Execute real trades (disables dry-run)')
    parser.add_argument('--monitor-interval', type=int, default=30,
                        help='Position monitoring interval in seconds (default: 30)')
    parser.add_argument('--trailing-stop', action='store_true',
                        help='Enable trailing stop-loss for positions')
    parser.add_argument('--trailing-distance', type=float, default=2.0,
                        help='Trailing stop distance as percentage (default: 2.0)')
    
    args = parser.parse_args()
    
    # Determine execution mode
    execution_mode = None
    if args.spot and args.leverage:
        print("ERROR: Cannot enable both --spot and --leverage. Choose one.")
        sys.exit(1)
    elif args.spot:
        execution_mode = "spot"
    elif args.leverage:
        execution_mode = "leverage"
    
    if execution_mode:
        mode_str = execution_mode.upper()
        run_mode = "DRY RUN" if args.dry_run else "LIVE"
        print(f"🎯 Execution Mode: {mode_str} ({run_mode})")
    else:
        print("ℹ️  No execution mode specified. Running in analysis-only mode.")
    
    agent = TraderAgentV2(
        execution_mode=execution_mode, 
        dry_run=args.dry_run, 
        token=args.token,
        monitor_interval=args.monitor_interval,
        trailing_stop=args.trailing_stop,
        trailing_distance=args.trailing_distance
    )
    asyncio.run(agent.start())
