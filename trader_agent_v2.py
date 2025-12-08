#!/usr/bin/env python3
import asyncio
import os
import sys
import argparse
import time
import aiohttp
import logging
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.event_bus import EventBus, Event
from backend.state_manager import StateManager
from backend.orchestrator import Orchestrator
from backend.position_monitor import PositionMonitor
from backend.config import Config

# Configure Logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("TraderAgentV2")

# Load environment variables
load_dotenv()

class TraderAgentV2:
    def __init__(self, execution_mode: str = None, dry_run: bool = True, token: str = Config.DEFAULT_TOKEN, 
                 monitor_interval: int = Config.DEFAULT_MONITOR_INTERVAL, trailing_stop: bool = False, trailing_distance: float = Config.DEFAULT_TRAILING_DISTANCE,
                 ai_provider: str = "auto"):
        logger.info("Initializing Trader Agent V2 (TiMi Architecture)...")
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
            token=token,
            ai_provider=ai_provider
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
        logger.info("Starting Event Loop...")
        # Start Event Bus
        bus_task = asyncio.create_task(self.event_bus.start())
        
        # Track last analysis time to prevent API quota exhaustion
        last_analysis_time = 0
        min_analysis_interval = 14400  # 4 hours minimum between full analysis cycles
        
        # Start Position Monitor if enabled
        monitor_task = None
        if self.position_monitor:
            logger.info(f"Starting Position Monitor (interval={self.monitor_interval}s)...")
            monitor_task = asyncio.create_task(self.position_monitor.start())
        
        try:
            while True:
                # 0. Check for existing open positions BEFORE starting analysis
                if self.position_monitor:
                    self.position_monitor.position_manager.refresh_positions()
                    existing_positions = self.position_monitor.position_manager.get_all_positions()
                    if existing_positions:
                        logger.info(f"Found {len(existing_positions)} existing open positions. Skipping analysis and entering monitoring mode.")
                        await self._monitor_positions_loop(self.token)
                        continue
                
                # Check if enough time has passed since last analysis
                time_since_last_analysis = time.time() - last_analysis_time
                if last_analysis_time > 0 and time_since_last_analysis < min_analysis_interval:
                    remaining_time = min_analysis_interval - time_since_last_analysis
                    logger.info(f"⏳ Cooldown active. Next analysis in {remaining_time/3600:.1f} hours to preserve API quota.")
                    logger.info(f"💡 Tip: You've used your daily Gemini API quota. The agent will wait before running another full analysis.")
                    await asyncio.sleep(remaining_time)

                print("\n" + "="*50)
                print(f"   STARTING ANALYSIS CYCLE: {self.token}")
                print("="*50)
                
                # Run the full analysis cycle
                try:
                    final_state = await self.orchestrator.run_cycle()
                except ValueError as e:
                    logger.error(f"\n⚠️  {e}")
                    logger.info("Waiting 5 minutes before retrying...")
                    await asyncio.sleep(300)
                    continue
                    
                last_analysis_time = time.time()  # Update last analysis time
                
                # Extract decision (final_state is a GlobalState Pydantic model)
                decision = final_state.decision or {}
                action = decision.get("action", "WAIT")
                plan = decision.get("plan", {})
                token_address = final_state.token_address
                
                logger.info(f"Cycle Complete. Decision: {action}")
                
                # Ensure we have a token_address for watch mode
                if not token_address:
                    logger.warning("⚠️  Token address not available. Fetching...")
                    from trader_agent_core import TraderAgent
                    agent = TraderAgent()
                    token_address = await agent._get_token_address(self.token, "solana")
                    if not token_address:
                        logger.error(f"❌ Could not fetch token address for {self.token}. Waiting 1 hour before retry...")
                        await asyncio.sleep(3600)
                        continue
                
                # Smart Watch Logic
                if action == "WAIT" or action is None or (action == "SELL" and not (self.position_monitor and self.position_monitor.position_manager.get_all_positions())):
                    logger.info("--- Entering Smart Watch Mode ---")
                    logger.info("Monitoring price for opportunities (saving API calls)...")
                    
                    target_entry = plan.get("entry_price")
                    if target_entry:
                        logger.info(f"Target Entry: ${target_entry:.4f}")
                    
                    # Watch loop configuration - increased to 6 hours to save API quota
                    watch_duration = 21600  # 6 hours (increased from 1 hour)
                    check_interval = 60   # Check price every 60 seconds (reduced frequency)
                    start_time = time.time()
                    
                    logger.info(f"⏰ Will watch for {watch_duration/3600:.0f} hours before re-analyzing...")
                    
                    while (time.time() - start_time) < watch_duration:
                        # 1. Fetch current price cheaply (Async)
                        current_price = await self._fetch_price_cheaply(token_address)
                        
                        if current_price:
                            timestamp = time.strftime("%H:%M:%S")
                            print(f"[{timestamp}] Price: ${current_price:.4f}", end="\r")
                            
                            # 2. Check triggers
                            if target_entry:
                                # If price is within 0.5% of target, wake up
                                if abs(current_price - target_entry) / target_entry < 0.005:
                                    logger.info(f"\n🎯 Price near target (${target_entry})! Triggering analysis...")
                                    break
                                    
                                # If price dips significantly (e.g. 2% drop), wake up
                                # (Requires tracking last price, omitted for simplicity)
                        else:
                            # If price fetch fails, still wait the interval to avoid tight loop
                            timestamp = time.strftime("%H:%M:%S")
                            print(f"[{timestamp}] Waiting... (price unavailable)", end="\r")
                        
                        await asyncio.sleep(check_interval)
                    
                    logger.info("\nWatch cycle ended. Refreshing analysis...")
                    
                else:
                    # If we took action (BUY/SELL), monitor position with PnL display
                    await self._monitor_positions_loop(token_address)
            
        except KeyboardInterrupt:
            logger.info("\nShutting down...")
        except Exception as e:
            logger.error(f"\n❌ CRITICAL ERROR in Main Loop: {e}", exc_info=True)
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

    async def _monitor_positions_loop(self, token_address):
        """Helper method to monitor positions indefinitely."""
        logger.info(f"--- Monitoring Position ---")
        
        # Indefinite monitoring loop as long as positions exist
        check_interval = self.monitor_interval  # Use configured interval
        
        while True:
            # Refresh positions from DB to ensure we have the latest state
            if self.position_monitor:
                self.position_monitor.position_manager.refresh_positions()
                open_positions = self.position_monitor.position_manager.get_all_positions()
            else:
                open_positions = []
            
            if not open_positions:
                logger.info(f"\nNo open positions. Returning to analysis cycle...")
                break
            
            # If token_address is not passed (e.g. on startup), try to fetch it from position or API
            if not token_address or token_address == self.token:
                 # Try to get address from the first position
                 if open_positions:
                     token_address = open_positions[0].token_address
            
            # Optimization: Do NOT fetch price here if PositionMonitor is running.
            # PositionMonitor already fetches price and updates the DB.
            # We just display the latest state from DB.
            
            timestamp = time.strftime("%H:%M:%S")
            
            # Calculate PnL for each position based on stored price (updated by PositionMonitor)
            for pos in open_positions:
                if pos.symbol == self.token:
                    current_price = pos.current_price
                    if current_price:
                        pnl_pct = pos.calculate_pnl_percentage(current_price)
                        pnl_usd = pos.calculate_pnl(current_price)
                        sl_price = pos.stop_loss
                        
                        print(f"[{timestamp}] Price: ${current_price:.4f} | PnL: {pnl_pct:+.2f}% (${pnl_usd:+.2f}) | SL: ${sl_price:.4f}", end="\r")
                    else:
                         print(f"[{timestamp}] Waiting for price update...", end="\r")
            
            await asyncio.sleep(check_interval)
    async def _fetch_price_cheaply(self, token_address):
        """Fetches current price using robust logic (Birdeye -> Jupiter -> CoinGecko OHLCV)."""
        try:
            # Use the core agent from the orchestrator's technical analyst
            # This ensures we reuse the robust fetching logic with fallbacks
            market_data, _ = await self.orchestrator.tech_analyst.core_agent.fetch_data(self.token, "solana")
            price = market_data.get('value')
            if price:
                return float(price)
        except Exception as e:
            logger.error(f"Error fetching price: {e}")
            
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Trader Agent V2 - TiMi Architecture')
    parser.add_argument("--ai-provider", type=str, default="auto", choices=["auto", "gemini", "lmstudio", "qwen"], help="AI Provider")
    parser.add_argument('--token', type=str, default=Config.DEFAULT_TOKEN, help='Token symbol to analyze (e.g., SOL, BONK, JUP)')
    parser.add_argument('--spot', action='store_true', help='Enable spot trading via Jupiter')
    parser.add_argument('--leverage', action='store_true', help='Enable leverage trading via Drift')
    parser.add_argument('--dry-run', dest='dry_run', action='store_true', default=True,
                        help='Simulate execution without actual trades (default: True)')
    parser.add_argument('--live', dest='dry_run', action='store_false',
                        help='Execute real trades (disables dry-run)')
    parser.add_argument('--monitor-interval', type=int, default=Config.DEFAULT_MONITOR_INTERVAL,
                        help=f'Position monitoring interval in seconds (default: {Config.DEFAULT_MONITOR_INTERVAL})')
    parser.add_argument('--trailing-stop', action='store_true',
                        help='Enable trailing stop-loss for positions')
    parser.add_argument('--trailing-distance', type=float, default=Config.DEFAULT_TRAILING_DISTANCE,
                        help=f'Trailing stop distance as percentage (default: {Config.DEFAULT_TRAILING_DISTANCE})')
    
    args = parser.parse_args()
    
    # Determine execution mode
    execution_mode = None
    if args.spot and args.leverage:
        logger.error("Cannot enable both --spot and --leverage. Choose one.")
        sys.exit(1)
    elif args.spot:
        execution_mode = "spot"
    elif args.leverage:
        execution_mode = "leverage"
    
    if execution_mode:
        mode_str = execution_mode.upper()
        run_mode = "DRY RUN" if args.dry_run else "LIVE"
        logger.info(f"🎯 Execution Mode: {mode_str} ({run_mode})")
    else:
        logger.info("ℹ️  No execution mode specified. Running in analysis-only mode.")
    
    agent = TraderAgentV2(
        execution_mode=execution_mode,
        dry_run=args.dry_run,
        token=args.token,
        monitor_interval=args.monitor_interval,
        trailing_stop=args.trailing_stop,
        trailing_distance=args.trailing_distance,
        ai_provider=args.ai_provider
    )
    asyncio.run(agent.start())
