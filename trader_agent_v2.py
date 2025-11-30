#!/usr/bin/env python3
import asyncio
import os
import sys
import argparse
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.event_bus import EventBus, Event
from backend.state_manager import StateManager
from backend.orchestrator import Orchestrator

# Load environment variables
load_dotenv()

class TraderAgentV2:
    def __init__(self, execution_mode: str = None, dry_run: bool = True, token: str = "SOL"):
        print("Initializing Trader Agent V2 (TiMi Architecture)...")
        self.event_bus = EventBus()
        self.state_manager = StateManager()
        self.orchestrator = Orchestrator(
            self.state_manager,
            execution_mode=execution_mode,
            dry_run=dry_run,
            token=token
        )
        
    async def start(self):
        print("Starting Event Loop...")
        # Start Event Bus
        bus_task = asyncio.create_task(self.event_bus.start())
        
        try:
            # Simulate a cycle for testing
            print("\n--- Starting Test Cycle ---")
            await self.orchestrator.run_cycle()
            
            # Keep running until interrupted
            # await asyncio.Future() 
            
        except KeyboardInterrupt:
            print("Shutting down...")
        finally:
            self.event_bus.stop()
            await bus_task

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Trader Agent V2 - TiMi Architecture')
    parser.add_argument('--token', type=str, default='SOL', help='Token symbol to analyze (e.g., SOL, BONK, JUP)')
    parser.add_argument('--spot', action='store_true', help='Enable spot trading via Jupiter')
    parser.add_argument('--leverage', action='store_true', help='Enable leverage trading via Drift')
    parser.add_argument('--dry-run', dest='dry_run', action='store_true', default=True,
                        help='Simulate execution without actual trades (default: True)')
    parser.add_argument('--live', dest='dry_run', action='store_false',
                        help='Execute real trades (disables dry-run)')
    
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
    
    agent = TraderAgentV2(execution_mode=execution_mode, dry_run=args.dry_run, token=args.token)
    asyncio.run(agent.start())
