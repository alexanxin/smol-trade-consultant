#!/usr/bin/env python3
"""
Trader Agent V3 (Varma) - Reactive, risk-focused trading agent.

Based on Samir Varma's methodologies:
- Regime Classification over prediction
- Kelly Criterion for position sizing
- Noise-resistant strategies (ORB + Trend Following)
- Smart execution to avoid predatory algorithms
"""

import os
import sys
import logging
import argparse
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.varma_risk_engine import VarmaRiskEngine
from backend.regime_classifier import RegimeClassifier
from backend.trend_strategy import TrendStrategy
from backend.orb_strategy import ORBStrategy
from backend.smart_execution import SmartExecution
from backend.position_monitor import PositionMonitor
from backend.market_timing import MarketTiming
from backend.config import Config

# Extract Varma config parameters
VARMA_CONFIG = {
    'VARMA_KELLY_DAMPENER': Config.VARMA_KELLY_DAMPENER,
    'VARMA_MAX_DRAWDOWN': Config.VARMA_MAX_DRAWDOWN,
    'VARMA_TREND_PERIOD': Config.VARMA_TREND_PERIOD,
    'VARMA_ORB_RANGE_MINUTES': Config.VARMA_ORB_RANGE_MINUTES,
    'VARMA_RISK_ON_MULTIPLIER': Config.VARMA_RISK_ON_MULTIPLIER,
    'VARMA_RISK_OFF_MULTIPLIER': Config.VARMA_RISK_OFF_MULTIPLIER,
    'VARMA_MIN_POSITION_SIZE': Config.VARMA_MIN_POSITION_SIZE,
    'VARMA_MAX_POSITION_SIZE': Config.VARMA_MAX_POSITION_SIZE
}
from trader_agent_core import TraderAgent as TraderAgentCore

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('varma_agent.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("VarmaAgent")


class VarmaAgent:
    """
    Reactive trading agent based on Samir Varma's methodologies.

    Core principles:
    - Purely reactive and rule-based (no AI predictions)
    - Regime classification over prediction
    - Kelly Criterion with fractional dampener
    - Target 45% max drawdown vs traditional 3%
    - Noise-resistant strategies (ORB + Trend)
    """

    def __init__(
        self,
        strategy: str = "trend",
        token_symbol: str = "SOL",
        chain: str = "solana",
        capital: float = 1000.0,
        dry_run: bool = True,
        force_buy: bool = False,
        trailing_stop_enabled: bool = False,
        trailing_stop_distance: float = 2.0,
        market_timing_enabled: bool = True
    ):
        """
        Initialize VarmaAgent.

        Args:
            strategy: "trend" or "orb"
            token_symbol: Token to trade (e.g., "SOL")
            chain: Blockchain network
            capital: Total capital available
            dry_run: If True, no real trades executed
            force_buy: If True, force a BUY signal for testing
        """
        self.strategy = strategy
        self.token_symbol = token_symbol
        self.chain = chain
        self.capital = capital
        self.dry_run = dry_run
        self.force_buy = force_buy
        self.trailing_stop_enabled = trailing_stop_enabled
        self.trailing_stop_distance = trailing_stop_distance

        logger.info(f"Initializing VarmaAgent: strategy={strategy}, token={token_symbol}, "
                   f"chain={chain}, capital=${capital}, dry_run={dry_run}, force_buy={force_buy}, "
                   f"trailing_stop={trailing_stop_enabled} ({trailing_stop_distance}%)")

        # Initialize core components
        self._init_components()

        # Trading state
        self.active_position = None
        self.last_signal = None

        logger.info("VarmaAgent initialized successfully")

    def _init_components(self):
        """Initialize all core components."""
        try:
            # Data fetcher (reuse existing core)
            self.data_fetcher = TraderAgentCore()

            # Risk engine (already implemented)
            self.risk_engine = VarmaRiskEngine(
                kelly_dampener=VARMA_CONFIG['VARMA_KELLY_DAMPENER'],
                max_drawdown_target=VARMA_CONFIG['VARMA_MAX_DRAWDOWN'],
                risk_on_multiplier=VARMA_CONFIG['VARMA_RISK_ON_MULTIPLIER'],
                risk_off_multiplier=VARMA_CONFIG['VARMA_RISK_OFF_MULTIPLIER'],
                min_position_size=VARMA_CONFIG['VARMA_MIN_POSITION_SIZE'],
                max_position_size=VARMA_CONFIG['VARMA_MAX_POSITION_SIZE']
            )

            # Regime classifier
            self.regime_classifier = RegimeClassifier()

            # Strategy components
            if self.strategy == "trend":
                self.strategy_engine = TrendStrategy()
            elif self.strategy == "orb":
                self.strategy_engine = ORBStrategy()
            else:
                raise ValueError(f"Unknown strategy: {self.strategy}")

            # Smart execution
            self.execution_engine = SmartExecution()

            # Market timing (for ORB strategy optimization) - initialize before position monitor
            self.market_timing = MarketTiming()

            # Position monitor (share market timing instance for consistent volatility tracking)
            self.position_monitor = PositionMonitor(
                execution_mode="spot",
                dry_run=self.dry_run,
                token=self.token_symbol,
                trailing_stop=self.trailing_stop_enabled,
                trailing_distance=self.trailing_stop_distance,
                market_timing=self.market_timing
            )

            logger.info("All components initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise

    async def run_cycle(self) -> Dict[str, Any]:
        """
        Run one complete trading cycle.

        Returns:
            Dict with cycle results
        """
        try:
            logger.info(f"Starting trading cycle for {self.token_symbol}")

            # 1. Fetch market data
            market_data, ohlcv_data = await self._fetch_market_data()
            if not market_data:
                return {"status": "error", "message": "Failed to fetch market data"}

            current_price = market_data.get('value', 0)
            logger.info(f"Current price: ${current_price:.4f}")

            # 2. Classify risk regime
            print(f"[STRATEGY] 📊 Analyzing risk regime...")
            regime = self._classify_regime(ohlcv_data)
            print(f"[STRATEGY] 🎯 Risk regime: {regime}")
            logger.info(f"Risk regime: {regime}")

            # 3. Generate strategy signal
            print(f"[STRATEGY] 🎲 Generating {self.strategy} strategy signal...")
            signal = self._generate_signal(market_data, ohlcv_data, regime)
            if signal:
                signal_action = signal.get('action', 'HOLD')
                signal_price = signal.get('entry_price', 0)
                signal_confidence = signal.get('confidence', 0)
                print(f"[STRATEGY] 📈 Signal: {signal_action} at ${signal_price:.4f} (confidence: {signal_confidence}%)")
                logger.info(f"Signal generated: {signal_action} at ${signal_price:.4f}")
            else:
                print(f"[STRATEGY] ⏸️  No signal generated")
                logger.info("No signal generated")

            # 4. Calculate position size (if signal exists)
            if signal and signal['action'] in ['BUY', 'SELL']:
                position_size = self._calculate_position_size(signal, regime)
                signal['position_size'] = position_size
                logger.info(f"Position size: ${position_size:.2f}")

                # 4.5. Validate trade risk before execution
                risk_validation = self._validate_trade_risk(signal, regime)
                if not risk_validation['approved']:
                    logger.warning(f"Trade rejected by risk validation: {risk_validation['warnings']}")
                    signal['risk_validation'] = risk_validation
                    signal['execution_result'] = {"status": "rejected", "reason": "Risk validation failed"}
                else:
                    # Apply any risk adjustments
                    if 'position_size_usd' in risk_validation.get('adjustments', {}):
                        adjusted_size = risk_validation['adjustments']['position_size_usd']
                        signal['position_size'] = adjusted_size
                        logger.info(f"Position size adjusted by risk validation: ${adjusted_size:.2f}")

                    # 5. Execute trade (generate camouflaged orders even in dry-run)
                    execution_result = self._execute_trade(signal)
                    signal['execution_result'] = execution_result

                    # 6. Record position for monitoring (only if trade was executed)
                    if execution_result.get('status') in ['simulated', 'executed']:
                        self._record_position(signal)

                signal['risk_validation'] = risk_validation

            # Store last signal
            self.last_signal = signal

            return {
                "status": "success",
                "current_price": current_price,
                "regime": regime,
                "signal": signal,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")
            return {"status": "error", "message": str(e)}

    async def _fetch_market_data(self):
        """Fetch market data using existing core."""
        try:
            print(f"[API] 📡 Fetching market data for {self.token_symbol} on {self.chain}...")

            # Use TraderAgentCore to fetch data
            market_data, ohlcv_data = await self.data_fetcher.fetch_data(self.token_symbol, self.chain)

            if 'error' in market_data:
                print(f"[API] ❌ Failed to fetch market data: {market_data['error']}")
                logger.error(f"Failed to fetch market data: {market_data['error']}")
                return None, None

            # Show successful data fetch
            price = market_data.get('value', 'N/A')
            liquidity = market_data.get('liquidity', 'N/A')
            volume = market_data.get('volume') or market_data.get('v24h', 'N/A')

            print(f"[API] ✅ Market data received:")
            print(f"[API]    💰 Price: ${price}")
            print(f"[API]    💧 Liquidity: {liquidity}")
            print(f"[API]    📊 24h Volume: {volume}")

            # Show OHLCV data summary
            if ohlcv_data:
                for timeframe, data in ohlcv_data.items():
                    if data and len(data) > 0:
                        latest = data[-1]  # Most recent candle
                        print(f"[API]    📈 {timeframe.upper()}: {len(data)} candles, Latest: O:{latest.get('o', 'N/A')} H:{latest.get('h', 'N/A')} L:{latest.get('l', 'N/A')} C:{latest.get('c', 'N/A')}")

            return market_data, ohlcv_data

        except Exception as e:
            print(f"[API] ❌ Error fetching market data: {e}")
            logger.error(f"Failed to fetch market data: {e}")
            return None, None

    def _classify_regime(self, ohlcv_data: Dict) -> str:
        """Classify risk regime (RISK_ON vs RISK_OFF)."""
        try:
            # Extract daily OHLCV data for trend calculation
            daily_data = ohlcv_data.get('daily', [])
            if not daily_data:
                logger.warning("No daily data available for regime classification")
                return "UNKNOWN"

            # Convert to pandas Series for analysis
            import pandas as pd
            prices = pd.DataFrame(daily_data)['c'] if daily_data else pd.Series()

            # Gracefully degrade to shorter MA if insufficient data (as per implementation plan)
            min_period = min(len(prices), 200)
            if min_period < 30:  # Need at least 30 days for meaningful analysis
                logger.warning(f"Insufficient data for trend calculation: {len(prices)} < 30")
                return "UNKNOWN"

            # Use available data length for trend period (degrade gracefully)
            trend_period = min(min_period, 200)
            logger.info(f"Using {trend_period}-day moving average for regime classification (available: {len(prices)} days)")

            # Create temporary regime classifier with appropriate period
            temp_regime_classifier = RegimeClassifier(trend_period=trend_period)

            # Get current price (from market data, but for daily regime we use last daily close)
            current_daily_price = prices.iloc[-1]

            # Classify regime using the regime classifier
            regime_summary = temp_regime_classifier.get_regime_summary(
                current_price=current_daily_price,
                prices=prices
            )

            regime = regime_summary["regime"].value
            logger.info(f"Regime classified: {regime}")

            return regime

        except Exception as e:
            logger.error(f"Failed to classify regime: {e}")
            return "UNKNOWN"

    def _generate_signal(self, market_data: Dict, ohlcv_data: Dict, regime: str):
        """Generate trading signal using selected strategy."""
        try:
            # Force BUY signal for testing if requested
            if self.force_buy:
                current_price = market_data.get('value', 0)
                logger.info("FORCING BUY SIGNAL for testing execution")
                return {
                    "action": "BUY",
                    "entry_price": current_price,
                    "stop_loss": current_price * 0.97,  # 3% stop loss
                    "take_profit": 0,
                    "confidence": 90,
                    "strategy": "forced_test",
                    "regime": regime,
                    "reason": "Forced BUY signal for testing smart execution"
                }

            # Normal strategy logic
            if self.strategy == "trend":
                return self._generate_trend_signal(market_data, ohlcv_data, regime)
            elif self.strategy == "orb":
                return self._generate_orb_signal(market_data, ohlcv_data, regime)
            else:
                return None
        except Exception as e:
            logger.error(f"Failed to generate signal: {e}")
            return None

    def _generate_trend_signal(self, market_data: Dict, ohlcv_data: Dict, regime: str):
        """Generate trend-following signal using TrendStrategy."""
        try:
            # Extract daily data for trend analysis
            daily_data = ohlcv_data.get('daily', [])
            if not daily_data:
                logger.warning("No daily data available for trend signal generation")
                return None

            import pandas as pd
            prices = pd.DataFrame(daily_data)['c'] if daily_data else pd.Series()

            # Gracefully degrade to shorter period if insufficient data
            available_days = len(prices)
            if available_days < 30:  # Need at least 30 days for meaningful analysis
                logger.warning(f"Insufficient data for trend analysis: {available_days} < 30")
                return None

            # Use available data length for trend period
            trend_period = min(available_days, 200)
            logger.info(f"Using {trend_period}-day trend period for signal generation (available: {available_days} days)")

            current_price = market_data.get('value', 0)

            # Create temporary trend strategy with appropriate period
            temp_trend_strategy = TrendStrategy(trend_period=trend_period)

            # Generate signal using TrendStrategy
            signal = temp_trend_strategy.generate_trend_signal(
                current_price=current_price,
                prices=prices
            )

            # Convert to our unified signal format
            unified_signal = {
                "action": signal.get("action", "HOLD"),
                "entry_price": current_price,
                "stop_loss": signal.get("stop_loss", 0),
                "take_profit": 0,  # Trend strategy doesn't use take profit, just stops
                "confidence": 80 if signal.get("is_risk_on") else 60,  # Higher confidence in RISK_ON
                "strategy": "trend",
                "regime": regime,
                "trend_line": signal.get("trend_line"),
                "distance_from_trend_pct": signal.get("distance_from_trend_pct"),
                "position_multiplier": signal.get("position_multiplier", 1.0),
                "reason": signal.get("reason", "")
            }

            return unified_signal

        except Exception as e:
            logger.error(f"Failed to generate trend signal: {e}")
            return None

    def _generate_orb_signal(self, market_data: Dict, ohlcv_data: Dict, regime: str):
        """Generate ORB signal using ORBStrategy with market timing."""
        try:
            current_price = market_data.get('value', 0)

            # Update price history for volatility tracking
            self.market_timing.update_price_history(current_price)

            # Check if market conditions are suitable for ORB strategy
            should_run, reason = self.market_timing.should_run_orb_strategy(current_price)
            if not should_run:
                logger.info(f"ORB strategy inactive: {reason}")
                return {
                    "action": "WAIT",
                    "entry_price": current_price,
                    "stop_loss": 0,
                    "take_profit": 0,
                    "confidence": 0,
                    "strategy": "orb",
                    "regime": regime,
                    "reason": f"Market timing: {reason}"
                }

            # Extract 5-minute data for ORB analysis (opening range is typically 10-20 minutes)
            ltf_data = ohlcv_data.get('ltf', [])
            if not ltf_data:
                logger.warning("No 5-minute data available for ORB signal generation")
                return None

            import pandas as pd
            # Convert to DataFrame with proper column names
            df = pd.DataFrame(ltf_data)
            if not df.empty:
                # Rename columns to match expected format
                df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                # Convert timestamp if it's in seconds
                if 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s' if df['timestamp'].iloc[0] > 1e10 else 'ms')

            if len(df) < 10:  # Need at least 10 5-minute candles for meaningful ORB
                logger.warning(f"Insufficient 5-minute data for ORB: {len(df)} < 10")
                return None

            # For crypto, we don't have traditional market hours, so we'll use the first few candles
            # Define opening range as first 15 minutes (3 x 5-minute candles)
            market_open_time = df['timestamp'].iloc[0] if not df.empty else None

            # Generate signal using ORBStrategy
            signal = self.strategy_engine.generate_orb_signal(
                current_price=current_price,
                ohlcv_data=df,
                market_open_time=market_open_time
            )

            # Convert to our unified signal format
            unified_signal = {
                "action": signal.get("action", "HOLD"),
                "entry_price": current_price,
                "stop_loss": signal.get("stop_loss", 0),
                "take_profit": 0,  # ORB strategy doesn't use take profit, just stops
                "confidence": 75 if signal.get("action") in ["BUY", "SELL"] else 50,  # High confidence for ORB breakouts
                "strategy": "orb",
                "regime": regime,
                "opening_range_high": signal.get("opening_range_high"),
                "opening_range_low": signal.get("opening_range_low"),
                "breakout_direction": signal.get("breakout_direction"),
                "reason": signal.get("reason", "")
            }

            return unified_signal

        except Exception as e:
            logger.error(f"Failed to generate ORB signal: {e}")
            return None

    def _calculate_position_size(self, signal: Dict, regime: str) -> float:
        """Calculate position size using Varma risk engine with historical performance."""
        try:
            # Get historical performance from closed trades
            performance_metrics = self._get_performance_metrics()

            # Extract metrics for Kelly calculation
            win_rate = performance_metrics.get('win_rate', 0.55)
            avg_win = performance_metrics.get('avg_win_pct', 0.05)  # Already in decimal
            avg_loss = performance_metrics.get('avg_loss_pct', 0.03)  # Already in decimal
            stop_loss_pct = 0.03  # 3% stop loss (could be made configurable)
            is_risk_on = regime == "RISK_ON"

            logger.info(f"Using performance metrics: win_rate={win_rate:.1%}, "
                       f"avg_win={avg_win:.1%}, avg_loss={avg_loss:.1%}, "
                       f"total_trades={performance_metrics.get('total_trades', 0)}")

            sizing_result = self.risk_engine.calculate_position_size(
                capital=self.capital,
                win_rate=win_rate,
                avg_win=avg_win,
                avg_loss=avg_loss,
                stop_loss_pct=stop_loss_pct,
                is_risk_on=is_risk_on,
                method="kelly"
            )

            return sizing_result['position_size_usd']

        except Exception as e:
            logger.error(f"Failed to calculate position size: {e}")
            return 0.0

    def _get_performance_metrics(self) -> Dict[str, float]:
        """Get performance metrics from closed trades for Kelly calculations."""
        try:
            from database import LifecycleDatabase
            db = LifecycleDatabase()

            # Get all closed trades
            closed_trades = db.get_positions_by_status("CLOSED")

            # Update risk engine with performance data
            performance_metrics = self.risk_engine.update_from_performance_history(closed_trades)

            return performance_metrics

        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            # Return conservative defaults
            return {
                "win_rate": 0.55,
                "avg_win_pct": 0.05,
                "avg_loss_pct": 0.03,
                "total_trades": 0,
                "sharpe_ratio": 0.0
            }

    def _validate_trade_risk(self, signal: Dict, regime: str) -> Dict[str, Any]:
        """Validate trade against risk limits before execution."""
        try:
            # Get current open positions
            from backend.position_manager import PositionManager
            position_manager = PositionManager()
            existing_positions = position_manager.get_all_positions()

            # Convert positions to format expected by risk engine
            existing_positions_data = []
            for pos in existing_positions:
                existing_positions_data.append({
                    'position_size_usd': pos.entry_amount * pos.entry_price if hasattr(pos, 'entry_amount') else 0,
                    'entry_price': pos.entry_price,
                    'stop_loss': pos.stop_loss
                })

            # Validate the trade
            validation_result = self.risk_engine.validate_trade_risk(
                position_size_usd=signal.get('position_size', 0),
                capital=self.capital,
                stop_loss_price=signal.get('stop_loss', 0),
                entry_price=signal.get('entry_price', 0),
                regime=regime,
                existing_positions=existing_positions_data
            )

            return validation_result

        except Exception as e:
            logger.error(f"Failed to validate trade risk: {e}")
            return {
                "approved": False,
                "warnings": [f"Risk validation error: {str(e)}"],
                "adjustments": {},
                "risk_metrics": {}
            }

    def _execute_trade(self, signal: Dict) -> Dict[str, Any]:
        """Execute trade using smart execution and Jupiter/Drift."""
        try:
            action = signal.get("action", "HOLD")
            if action not in ["BUY", "SELL"]:
                return {"status": "skipped", "reason": "No trade action"}

            entry_price = signal.get("entry_price", 0)
            position_size_usd = signal.get("position_size", 0)

            # Generate camouflaged order using SmartExecution
            camouflaged_order = self.execution_engine.place_hidden_order(
                order_type=action,
                entry_price=entry_price,
                position_size_usd=position_size_usd,
                stop_loss_pct=0.03,  # 3% stop loss
                take_profit_pct=None  # Trend/ORBs don't use take profit
            )

            # For now, in dry-run mode, just return the camouflaged order details
            if self.dry_run:
                return {
                    "status": "simulated",
                    "order_details": camouflaged_order,
                    "message": f"Would execute {camouflaged_order['order_type']} {camouflaged_order['asset_quantity']:.4f} units"
                }

            # LIVE EXECUTION: Use Jupiter client directly for spot trades
            logger.info(f"Live execution: {camouflaged_order}")

            # Import JupiterClient here to avoid circular imports
            from jupiter_client import JupiterClient
            from wallet_manager import SolanaWallet

            # Initialize wallet and Jupiter client
            wallet = SolanaWallet()
            jupiter = JupiterClient(wallet)

            # Get token addresses
            input_mint = "So11111111111111111111111111111111111111112"  # SOL (assuming we're buying with SOL)
            output_mint = self._get_token_address()

            if not output_mint:
                return {"status": "failed", "error": f"Could not find token address for {self.token_symbol}"}

            # Convert USD position size to token amount
            token_amount = camouflaged_order['asset_quantity']

            # Convert to lamports/atomic units (SOL has 9 decimals)
            if action == "BUY":
                # Buying tokens with SOL - amount is SOL amount in lamports
                amount_lamports = int(token_amount * (10 ** 9))  # SOL has 9 decimals
                input_mint, output_mint = input_mint, output_mint
            else:  # SELL
                # Selling tokens for SOL - amount is token amount in appropriate decimals
                # For simplicity, assuming 9 decimals for the token (like SOL)
                amount_lamports = int(token_amount * (10 ** 9))
                input_mint, output_mint = output_mint, input_mint

            # Execute the swap
            execution_result = jupiter.execute_swap(
                input_mint=input_mint,
                output_mint=output_mint,
                amount=amount_lamports,
                slippage_bps=100  # 1% slippage
            )

            # Merge camouflaged order details with execution result
            if "error" not in execution_result:
                execution_result["order_details"] = camouflaged_order
                execution_result["message"] = f"Executed {camouflaged_order['order_type']} {camouflaged_order['asset_quantity']:.4f} units via Jupiter"
                logger.info(f"Trade executed successfully: {execution_result}")
            else:
                logger.error(f"Trade execution failed: {execution_result}")

            return execution_result

        except Exception as e:
            logger.error(f"Failed to execute trade: {e}")
            return {"status": "failed", "error": str(e)}

    def _record_position(self, signal: Dict):
        """Record position for monitoring using PositionManager."""
        try:
            # Get token address
            token_address = self._get_token_address()

            # Get execution result
            execution_result = signal.get('execution_result', {})

            # Prepare trade data in the format PositionManager expects
            trade_data = {
                'plan': {
                    'entry': signal.get('entry_price', 0),
                    'stop_loss': signal.get('stop_loss', 0),
                    'take_profit': signal.get('take_profit', 0)
                }
            }

            # Add position to database via PositionManager
            from backend.position_manager import PositionManager
            position_manager = PositionManager()

            # Create execution result format
            exec_result = {
                'amount': signal.get('position_size', 0) / signal.get('entry_price', 1),  # Convert USD to token amount
                'mode': 'spot'
            }

            position = position_manager.add_position(
                trade_data=trade_data,
                execution_result=exec_result,
                token=self.token_symbol,
                token_address=token_address
            )

            self.active_position = position
            logger.info(f"Position recorded: {position.trade_id} for {self.token_symbol}")

        except Exception as e:
            logger.error(f"Failed to record position: {e}")

    def _get_token_address(self) -> Optional[str]:
        """Get token address for trading."""
        try:
            # Placeholder - will implement token address resolution
            return "So11111111111111111111111111111111111111112"  # SOL
        except Exception as e:
            logger.error(f"Failed to get token address: {e}")
            return None

    def get_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        return {
            "strategy": self.strategy,
            "token": self.token_symbol,
            "chain": self.chain,
            "capital": self.capital,
            "dry_run": self.dry_run,
            "active_position": self.active_position,
            "last_signal": self.last_signal,
            "timestamp": datetime.now().isoformat()
        }


async def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(description='Varma Trading Agent V3')
    parser.add_argument('--strategy', choices=['trend', 'orb'], default='trend',
                       help='Trading strategy (default: trend)')
    parser.add_argument('--token', type=str, default='SOL',
                       help='Token symbol to trade (default: SOL)')
    parser.add_argument('--chain', type=str, default='solana',
                       help='Blockchain network (default: solana)')
    parser.add_argument('--capital', type=float, default=1000.0,
                       help='Total capital available (default: 1000)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Run in simulation mode (no real trades)')
    parser.add_argument('--force-buy', action='store_true',
                       help='Force a BUY signal for testing execution')
    parser.add_argument('--trailing-stop', action='store_true',
                       help='Enable trailing stop-loss for positions')
    parser.add_argument('--trailing-distance', type=float, default=2.0,
                       help='Trailing stop distance as percentage (default: 2.0)')
    parser.add_argument('--continuous', '--daemon', action='store_true',
                       help='Run continuously with periodic checks (default: single cycle)')
    parser.add_argument('--check-interval', type=int, default=10,
                       help='Minutes between checks when running continuously (default: 10)')
    parser.add_argument('--max-cycles', type=int, default=None,
                       help='Maximum number of cycles to run (default: unlimited)')
    parser.add_argument('--show-market-status', action='store_true',
                       help='Show current market status and session information')

    args = parser.parse_args()

    # Handle market status display
    if args.show_market_status:
        try:
            # Initialize market timing only for status display
            from backend.market_timing import MarketTiming
            from trader_agent_core import TraderAgent as TraderAgentCore

            market_timing = MarketTiming()
            data_fetcher = TraderAgentCore()

            # Fetch current price for volatility calculation
            market_data, _ = await data_fetcher.fetch_data(args.token, args.chain)
            current_price = market_data.get('value', 0) if market_data else None

            # Get market status
            status = market_timing.get_current_market_status(current_price)

            # Display formatted market status
            print("🌍 MARKET STATUS OVERVIEW")
            print("=" * 50)
            print(market_timing.format_market_status_display(status))

            # Show session schedule
            print("\n📅 CRYPTO MARKET SESSIONS (UTC)")
            print("-" * 35)
            schedule = market_timing.get_session_schedule()
            for session in schedule:
                print(f"{session['name']:15} {session['utc_start']:8} {session['duration']:6} {session['volatility']:8} {session['description']}")
            print()
            return  # Exit after showing status

        except Exception as e:
            print(f"❌ Failed to get market status: {e}")
            return

    try:
        # Initialize agent
        agent = VarmaAgent(
            strategy=args.strategy,
            token_symbol=args.token,
            chain=args.chain,
            capital=args.capital,
            dry_run=args.dry_run,
            force_buy=args.force_buy,
            trailing_stop_enabled=args.trailing_stop,
            trailing_stop_distance=args.trailing_distance
        )

        # Display market status at startup (always, not just with --show-market-status)
        print("🌍 CHECKING MARKET STATUS...")
        print("-" * 40)
        try:
            # Get current price for volatility calculation
            market_data, _ = await agent.data_fetcher.fetch_data(args.token, args.chain)
            current_price = market_data.get('value', 0) if market_data else None

            # Get market status
            status = agent.market_timing.get_current_market_status(current_price)

            # Display market status
            print(agent.market_timing.format_market_status_display(status))

            # Special notification for ORB strategy
            if args.strategy == "orb":
                should_run, reason = agent.market_timing.should_run_orb_strategy(current_price)
                if should_run:
                    print(f"\n🎯 ORB STRATEGY: ✅ WILL RUN - {reason}")
                else:
                    print(f"\n🎯 ORB STRATEGY: ⏸️  WILL WAIT - {reason}")
                    if not args.force_buy:  # Don't show if forcing buy for testing
                        print("💡 Tip: Use --force-buy to test execution or wait for better market conditions")

            print("=" * 60)

        except Exception as e:
            print(f"⚠️  Could not check market status: {e}")
            print("   Proceeding without market timing information...")
            print("=" * 60)

        # Check if position monitor should run (for continuous operation)
        if args.continuous or args.max_cycles:
            # Start position monitor for continuous operation
            await agent.position_monitor.start()

        cycle_count = 0
        max_cycles = args.max_cycles

        if args.continuous:
            print("🔄 Starting VARMA Agent in CONTINUOUS mode")
            print(f"   Strategy: {args.strategy}")
            print(f"   Check Interval: {args.check_interval} minutes")
            print(f"   Max Cycles: {max_cycles if max_cycles else 'unlimited'}")
            print("=" * 60)

        while True:
            cycle_count += 1

            # Show updated market status on each cycle (if continuous)
            if args.continuous and cycle_count > 1:
                try:
                    # Get updated market status
                    market_data, _ = await agent.data_fetcher.fetch_data(args.token, args.chain)
                    current_price = market_data.get('value', 0) if market_data else None

                    status = agent.market_timing.get_current_market_status(current_price)

                    # Display compact market update
                    volatility_icon = {"low": "🟢", "medium": "🟡", "high": "🟠", "extreme": "🔴", "unknown": "⚪"}.get(status.volatility_level, "⚪")
                    session_name = status.current_session.name if status.current_session else "Outside sessions"

                    print(f"\n🔄 CYCLE #{cycle_count} - {datetime.now().strftime('%H:%M:%S')} UTC")
                    print(f"   📊 Session: {session_name}")
                    print(f"   💰 Price: ${current_price:.4f}" if current_price else "   💰 Price: N/A")
                    print(f"   {volatility_icon} Volatility: {status.volatility_level.upper()}")

                    # ORB strategy status for this cycle
                    if args.strategy == "orb":
                        should_run, reason = agent.market_timing.should_run_orb_strategy(current_price)
                        orb_status = "✅ ACTIVE" if should_run else "⏸️  INACTIVE"
                        print(f"   🎯 ORB: {orb_status}")

                    print("-" * 50)

                except Exception as e:
                    print(f"⚠️  Market status update failed: {e}")

            # Run one trading cycle
            result = await agent.run_cycle()

            # Print results
            print(f"{'='*60}")
            print(f"VARMA AGENT V3 - CYCLE #{cycle_count} RESULTS")
            print(f"{'='*60}")
            print(f"Status: {result['status']}")
            if result['status'] == 'success':
                print(f"Current Price: ${result['current_price']:.4f}")
                print(f"Risk Regime: {result['regime']}")
                if result.get('signal'):
                    signal = result['signal']
                    print(f"Signal: {signal.get('action', 'HOLD')}")
                    if signal.get('action') in ['BUY', 'SELL']:
                        print(f"Entry Price: ${signal.get('entry_price', 0):.4f}")
                        print(f"Position Size: ${signal.get('position_size', 0):.2f}")
                        print(f"Stop Loss: ${signal.get('stop_loss', 0):.4f}")
                        print(f"Take Profit: ${signal.get('take_profit', 0):.4f}")
                        print(f"Confidence: {signal.get('confidence', 0)}%")

                        # Show execution details in dry-run mode
                        exec_result = result.get('signal', {}).get('execution_result', {})
                        if exec_result.get('status') == 'simulated':
                            order_details = exec_result.get('order_details', {})
                            if order_details:
                                asset_qty = order_details.get('asset_quantity', 0)
                                pos_size = order_details.get('position_size_usd', 0)
                                stop_price = order_details.get('stop_loss', 0)
                                print(f"\n🛡️  CAMOUFLAGED ORDER DETAILS:")
                                print(f"   Asset Quantity: {asset_qty:.4f} units")
                                print(f"   Actual Position Size: ${pos_size:.2f}")
                                print(f"   Camouflaged Stop: ${stop_price:.4f}")
                                print(f"   Order Style: {order_details.get('execution_style', 'standard')}")
                                print(f"   Notes: {order_details.get('notes', 'None')}")
            else:
                print(f"Error: {result.get('message', 'Unknown error')}")
            print(f"{'='*60}")

            # Check if we should exit
            if not args.continuous and not max_cycles:
                break  # Single cycle mode

            if max_cycles and cycle_count >= max_cycles:
                print(f"\n🎯 Reached maximum cycles ({max_cycles}). Exiting.")
                break

            # Wait for next cycle (if continuous)
            if args.continuous:
                wait_seconds = args.check_interval * 60
                print(f"\n⏱️  Next check in {args.check_interval} minutes...")
                await asyncio.sleep(wait_seconds)

        # Cleanup
        if args.continuous or args.max_cycles:
            agent.position_monitor.stop()

        print("\n✅ VARMA Agent completed successfully.")
        if cycle_count > 1:
            print(f"   Total cycles: {cycle_count}")
            print(f"   Average interval: {args.check_interval} minutes")

    except KeyboardInterrupt:
        print("\n🛑 Received interrupt signal. Shutting down gracefully...")

        # Stop position monitor if it was started
        if args.continuous or args.max_cycles:
            try:
                agent.position_monitor.stop()
            except Exception as e:
                print(f"⚠️  Warning during position monitor cleanup: {e}")

        # Give async operations a moment to clean up
        try:
            # Create a new event loop for cleanup if needed
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is still running, give it a moment
                import time
                time.sleep(0.1)
        except Exception:
            pass

        print("✅ VARMA Agent stopped.")
    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        print(f"❌ Agent execution failed: {e}")

        # Cleanup on error
        if args.continuous or args.max_cycles:
            agent.position_monitor.stop()

        sys.exit(1)


def sync_main():
    """Synchronous wrapper for main."""
    import asyncio
    asyncio.run(main())


if __name__ == "__main__":
    sync_main()
