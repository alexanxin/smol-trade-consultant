"""
Varma Risk Engine - Position sizing based on Samir Varma's methodology.

Implements:
- Kelly Criterion with fractional dampener
- Target drawdown-based position sizing
- Regime-based position adjustments
- Non-standard risk parameters (45-55% max drawdown vs traditional 3%)
"""

import logging
from typing import Dict, Optional, List, Any

logger = logging.getLogger("VarmaRiskEngine")


class VarmaRiskEngine:
    """
    Risk management engine based on Samir Varma's principles:
    - Use fractional Kelly Criterion (e.g., 0.25x Kelly) to reduce volatility
    - Target specific drawdown levels (45-55%) rather than avoiding drawdowns
    - Adjust position size based on risk regime (above/below trend)
    - Focus on keeping expected drawdowns constant across regimes
    """
    
    def __init__(
        self,
        kelly_dampener: float = 0.25,
        max_drawdown_target: float = 0.45,
        risk_on_multiplier: float = 1.5,
        risk_off_multiplier: float = 0.5,
        min_position_size: float = 0.05,
        max_position_size: float = 0.25
    ):
        """
        Initialize Varma Risk Engine.
        
        Args:
            kelly_dampener: Fraction of Kelly to use (0.25 = quarter Kelly)
            max_drawdown_target: Maximum acceptable drawdown (0.45 = 45%)
            risk_on_multiplier: Position size multiplier when above trend
            risk_off_multiplier: Position size multiplier when below trend
            min_position_size: Minimum position size as fraction of capital
            max_position_size: Maximum position size as fraction of capital
        """
        self.kelly_dampener = kelly_dampener
        self.max_drawdown_target = max_drawdown_target
        self.risk_on_multiplier = risk_on_multiplier
        self.risk_off_multiplier = risk_off_multiplier
        self.min_position_size = min_position_size
        self.max_position_size = max_position_size
        
        logger.info(f"VarmaRiskEngine initialized: Kelly={kelly_dampener}x, MaxDD={max_drawdown_target*100}%")
    
    def calculate_kelly_fraction(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float
    ) -> float:
        """
        Calculate Kelly Criterion position size.
        
        Formula: K = W - (1-W)/R
        Where:
            W = win rate (probability of winning)
            R = risk/reward ratio (avg_win / avg_loss)
        
        Args:
            win_rate: Historical win rate (0.0 to 1.0)
            avg_win: Average winning trade size (absolute value)
            avg_loss: Average losing trade size (absolute value)
        
        Returns:
            Kelly fraction (0.0 to 1.0)
        """
        if avg_loss <= 0 or avg_win <= 0:
            logger.warning("Invalid avg_win or avg_loss for Kelly calculation")
            return 0.0
        
        risk_reward_ratio = avg_win / avg_loss
        
        if risk_reward_ratio <= 0:
            return 0.0
        
        # Kelly formula: K = W - (1-W)/R
        kelly = win_rate - ((1 - win_rate) / risk_reward_ratio)
        
        # Apply fractional Kelly dampener
        fractional_kelly = max(0.0, kelly) * self.kelly_dampener
        
        logger.debug(f"Kelly: win_rate={win_rate:.2f}, R:R={risk_reward_ratio:.2f}, "
                    f"raw_kelly={kelly:.3f}, fractional={fractional_kelly:.3f}")
        
        return fractional_kelly
    
    def calculate_position_from_drawdown(
        self,
        stop_loss_pct: float,
        capital: float
    ) -> float:
        """
        Calculate position size based on target maximum drawdown.
        
        Logic: If we can tolerate a 45% drawdown and our stop-loss is 3%,
        we can risk 45% / 3% = 15 units, but we cap this for safety.
        
        Args:
            stop_loss_pct: Stop loss as decimal (0.03 = 3%)
            capital: Total capital available
        
        Returns:
            Position size in USD
        """
        if stop_loss_pct <= 0:
            logger.warning("Invalid stop_loss_pct for drawdown calculation")
            return 0.0
        
        # Calculate how many "units" we can risk
        # If max drawdown is 45% and stop is 3%, we can risk 15 units
        max_units = self.max_drawdown_target / stop_loss_pct
        
        # Convert to position size as fraction of capital
        # But cap it at max_position_size for safety
        position_fraction = min(max_units * stop_loss_pct, self.max_position_size)
        position_fraction = max(position_fraction, self.min_position_size)
        
        position_size_usd = capital * position_fraction
        
        logger.debug(f"Drawdown sizing: SL={stop_loss_pct*100}%, max_units={max_units:.1f}, "
                    f"position_fraction={position_fraction:.3f}, size=${position_size_usd:.2f}")
        
        return position_size_usd
    
    def adjust_for_regime(
        self,
        base_position_size: float,
        is_risk_on: bool
    ) -> float:
        """
        Adjust position size based on risk regime.
        
        Varma's principle: ~2/3 of returns occur above trend with ~1/3 of risk.
        Therefore, we should size up when above trend and size down when below.
        
        Args:
            base_position_size: Base position size before regime adjustment
            is_risk_on: True if above trend (risk-on), False if below (risk-off)
        
        Returns:
            Adjusted position size
        """
        multiplier = self.risk_on_multiplier if is_risk_on else self.risk_off_multiplier
        adjusted_size = base_position_size * multiplier
        
        regime_label = "RISK-ON" if is_risk_on else "RISK-OFF"
        logger.info(f"Regime adjustment: {regime_label}, multiplier={multiplier}x, "
                   f"base=${base_position_size:.2f} → adjusted=${adjusted_size:.2f}")
        
        return adjusted_size
    
    def calculate_position_size(
        self,
        capital: float,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        stop_loss_pct: float,
        is_risk_on: bool,
        method: str = "kelly"
    ) -> Dict[str, float]:
        """
        Calculate final position size using specified method and regime adjustment.
        
        Args:
            capital: Total capital available
            win_rate: Historical win rate (0.0 to 1.0)
            avg_win: Average winning trade size
            avg_loss: Average losing trade size
            stop_loss_pct: Stop loss as decimal (0.03 = 3%)
            is_risk_on: True if above trend (risk-on regime)
            method: "kelly" or "drawdown"
        
        Returns:
            Dict with position_size_usd, position_fraction, method, regime
        """
        # Calculate base position size
        if method == "kelly":
            kelly_fraction = self.calculate_kelly_fraction(win_rate, avg_win, avg_loss)
            base_position_size = capital * kelly_fraction
        elif method == "drawdown":
            base_position_size = self.calculate_position_from_drawdown(stop_loss_pct, capital)
        else:
            logger.error(f"Unknown method: {method}")
            return {
                "position_size_usd": 0.0,
                "position_fraction": 0.0,
                "method": method,
                "regime": "UNKNOWN"
            }
        
        # Apply regime adjustment
        final_position_size = self.adjust_for_regime(base_position_size, is_risk_on)
        
        # Ensure within bounds
        min_size = capital * self.min_position_size
        max_size = capital * self.max_position_size
        final_position_size = max(min_size, min(final_position_size, max_size))
        
        position_fraction = final_position_size / capital if capital > 0 else 0.0
        
        return {
            "position_size_usd": final_position_size,
            "position_fraction": position_fraction,
            "method": method,
            "regime": "RISK-ON" if is_risk_on else "RISK-OFF"
        }
    
    def get_risk_parameters(self) -> Dict[str, float]:
        """Get current risk parameters for logging/debugging."""
        return {
            "kelly_dampener": self.kelly_dampener,
            "max_drawdown_target": self.max_drawdown_target,
            "risk_on_multiplier": self.risk_on_multiplier,
            "risk_off_multiplier": self.risk_off_multiplier,
            "min_position_size": self.min_position_size,
            "max_position_size": self.max_position_size
        }

    def update_from_performance_history(self, closed_trades: List[Dict]) -> Dict[str, float]:
        """
        Update Kelly inputs based on actual trading performance.

        Args:
            closed_trades: List of closed trade dictionaries with entry_price, exit_price, etc.

        Returns:
            Updated performance metrics
        """
        if not closed_trades:
            logger.warning("No closed trades available for performance analysis")
            return {
                "win_rate": 0.55,  # Default
                "avg_win_pct": 0.05,
                "avg_loss_pct": 0.03,
                "total_trades": 0,
                "sharpe_ratio": 0.0
            }

        # Calculate performance metrics
        wins = []
        losses = []

        for trade in closed_trades:
            entry_price = trade.get('entry_price', 0)
            exit_price = trade.get('exit_price', 0)
            if entry_price == 0:
                continue

            pnl_pct = ((exit_price - entry_price) / entry_price) * 100

            if pnl_pct > 0:
                wins.append(pnl_pct)
            else:
                losses.append(pnl_pct)

        # Calculate metrics
        total_trades = len(closed_trades)
        win_rate = len(wins) / total_trades if total_trades > 0 else 0.55
        avg_win_pct = sum(wins) / len(wins) / 100 if wins else 0.05  # Convert to decimal
        avg_loss_pct = abs(sum(losses) / len(losses)) / 100 if losses else 0.03  # Convert to decimal

        # Calculate Sharpe-like ratio (simplified)
        if wins and losses:
            avg_win = sum(wins) / len(wins)
            avg_loss = abs(sum(losses) / len(losses))
            sharpe_ratio = (win_rate * avg_win - (1 - win_rate) * avg_loss) / (avg_loss if avg_loss > 0 else 1)
        else:
            sharpe_ratio = 0.0

        performance_metrics = {
            "win_rate": win_rate,
            "avg_win_pct": avg_win_pct,
            "avg_loss_pct": avg_loss_pct,
            "total_trades": total_trades,
            "sharpe_ratio": sharpe_ratio,
            "wins_count": len(wins),
            "losses_count": len(losses)
        }

        logger.info(f"Updated performance metrics from {total_trades} trades: "
                   f"Win Rate={win_rate:.1%}, Avg Win={avg_win_pct:.1%}, "
                   f"Avg Loss={avg_loss_pct:.1%}")

        return performance_metrics

    def validate_trade_risk(
        self,
        position_size_usd: float,
        capital: float,
        stop_loss_price: float,
        entry_price: float,
        regime: str,
        existing_positions: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Validate a trade against risk limits before execution.

        Args:
            position_size_usd: Proposed position size in USD
            capital: Total available capital
            stop_loss_price: Stop loss price level
            entry_price: Entry price
            regime: Current risk regime ("RISK_ON" or "RISK_OFF")
            existing_positions: List of current open positions

        Returns:
            Dict with validation result and any adjustments needed
        """
        validation_result = {
            "approved": True,
            "warnings": [],
            "adjustments": {},
            "risk_metrics": {}
        }

        existing_positions = existing_positions or []

        # 1. Position Size Bounds Check
        position_fraction = position_size_usd / capital if capital > 0 else 0
        if position_fraction < self.min_position_size:
            validation_result["approved"] = False
            validation_result["warnings"].append(
                f"Position size ${position_size_usd:.2f} ({position_fraction:.1%}) below minimum {self.min_position_size:.1%}"
            )
        elif position_fraction > self.max_position_size:
            # Allow adjustment instead of rejection
            adjusted_size = capital * self.max_position_size
            validation_result["adjustments"]["position_size_usd"] = adjusted_size
            validation_result["warnings"].append(
                f"Position size reduced from ${position_size_usd:.2f} to ${adjusted_size:.2f} (max {self.max_position_size:.1%})"
            )

        # 2. Stop Loss Validation
        if entry_price > 0:
            stop_loss_pct = abs(stop_loss_price - entry_price) / entry_price
            if stop_loss_pct > 0.10:  # Max 10% stop loss
                validation_result["approved"] = False
                validation_result["warnings"].append(
                    f"Stop loss too wide: {stop_loss_pct:.1%} > 10%"
                )
            elif stop_loss_pct < 0.005:  # Min 0.5% stop loss
                validation_result["approved"] = False
                validation_result["warnings"].append(
                    f"Stop loss too tight: {stop_loss_pct:.1%} < 0.5%"
                )

        # 3. Portfolio Concentration Check
        total_exposure = sum(pos.get('position_size_usd', 0) for pos in existing_positions)
        total_exposure += position_size_usd

        max_portfolio_exposure = capital * 2.0  # Max 2x leverage across all positions
        if total_exposure > max_portfolio_exposure:
            validation_result["approved"] = False
            validation_result["warnings"].append(
                f"Portfolio exposure ${total_exposure:.2f} exceeds max ${max_portfolio_exposure:.2f}"
            )

        # 4. Drawdown Risk Check
        if entry_price > 0 and stop_loss_price > 0:
            potential_loss = abs(entry_price - stop_loss_price) / entry_price * position_size_usd
            potential_drawdown = potential_loss / capital

            if potential_drawdown > self.max_drawdown_target:
                validation_result["approved"] = False
                validation_result["warnings"].append(
                    f"Potential drawdown {potential_drawdown:.1%} exceeds target {self.max_drawdown_target:.1%}"
                )

        # 5. Regime-Appropriate Sizing (informational only, not blocking)
        expected_regime_multiplier = 1.5 if regime == "RISK_ON" else 0.5
        current_multiplier = position_fraction / (self.min_position_size * 2)  # Rough estimate

        if abs(current_multiplier - expected_regime_multiplier) > 0.5:  # Allow some tolerance
            # Log as informational, but don't block the trade
            logger.info(f"Position size {position_fraction:.1%} may not be optimal for {regime} regime "
                       f"(expected ~{expected_regime_multiplier}x multiplier)")

        # 6. Calculate Risk Metrics
        validation_result["risk_metrics"] = {
            "position_fraction": position_fraction,
            "stop_loss_pct": stop_loss_pct if 'stop_loss_pct' in locals() else 0,
            "portfolio_exposure": total_exposure,
            "potential_drawdown": potential_drawdown if 'potential_drawdown' in locals() else 0,
            "regime": regime
        }

        # Final approval decision
        if validation_result["warnings"] and not validation_result["adjustments"]:
            # Only reject if there are warnings and no adjustments made
            validation_result["approved"] = False

        logger.info(f"Risk validation {'APPROVED' if validation_result['approved'] else 'REJECTED'}: "
                   f"size=${position_size_usd:.2f}, fraction={position_fraction:.1%}")

        if validation_result["warnings"]:
            for warning in validation_result["warnings"]:
                logger.warning(f"Risk warning: {warning}")

        return validation_result
