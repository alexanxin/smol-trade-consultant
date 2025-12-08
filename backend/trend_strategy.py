"""
Trend Following Strategy - Samir Varma's long-term approach.

Logic: Focus on risk classification rather than alpha generation.
- Adjust position size based on risk regime (above/below 200-day MA)
- Never exit completely on trend break, just reduce size
- Maintain constant expected drawdown across regimes

Strategy:
1. Calculate long-term trend (200-day MA)
2. Classify regime (RISK-ON if above, RISK-OFF if below)
3. Size up in RISK-ON, size down in RISK-OFF
4. Hold for long periods (1+ year typical)
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Optional
from backend.regime_classifier import RegimeClassifier, RiskRegime

logger = logging.getLogger("TrendStrategy")


class TrendStrategy:
    """
    Long-term trend following strategy based on risk regime classification.
    
    Varma's principle: ~2/3 of returns occur above the trend with ~1/3 of risk.
    Therefore, we should be more aggressive when above trend and defensive when below.
    """
    
    def __init__(
        self,
        trend_period: int = 200,
        entry_threshold: float = 0.02,  # Enter when 2% above trend
        regime_classifier: Optional[RegimeClassifier] = None
    ):
        """
        Initialize Trend Following Strategy.
        
        Args:
            trend_period: Period for trend calculation (200 for 200-day MA)
            entry_threshold: Minimum distance above trend to enter (as decimal)
            regime_classifier: Optional RegimeClassifier instance (creates new if None)
        """
        self.trend_period = trend_period
        self.entry_threshold = entry_threshold
        
        # Use provided classifier or create new one
        self.regime_classifier = regime_classifier or RegimeClassifier(trend_period=trend_period)
        
        logger.info(f"TrendStrategy initialized: trend_period={trend_period}, "
                   f"entry_threshold={entry_threshold*100}%")
    
    def calculate_trend_line(self, prices: pd.Series) -> Optional[float]:
        """
        Calculate the long-term trend line.
        
        Args:
            prices: Historical price series
        
        Returns:
            Current trend line value or None if insufficient data
        """
        return self.regime_classifier.calculate_trend_line(prices)
    
    def determine_position_multiplier(self, regime: RiskRegime) -> float:
        """
        Determine position size multiplier based on regime.
        
        This is handled by VarmaRiskEngine, but we provide the regime classification.
        
        Args:
            regime: Current risk regime
        
        Returns:
            Multiplier (1.5 for RISK-ON, 0.5 for RISK-OFF)
        """
        if regime == RiskRegime.RISK_ON:
            return 1.5  # Increase position by 50%
        elif regime == RiskRegime.RISK_OFF:
            return 0.5  # Decrease position by 50%
        else:
            return 1.0  # Neutral if unknown
    
    def generate_trend_signal(
        self,
        current_price: float,
        prices: pd.Series,
        returns: Optional[pd.Series] = None
    ) -> Dict[str, any]:
        """
        Generate trend following signal.
        
        Args:
            current_price: Current market price
            prices: Historical price series
            returns: Optional historical returns for statistics
        
        Returns:
            Dict with signal, regime, trend_line, and metadata
        """
        # Get regime summary
        regime_summary = self.regime_classifier.get_regime_summary(
            current_price, prices, returns
        )
        
        regime = regime_summary["regime"]
        trend_line = regime_summary["trend_line"]
        distance_pct = regime_summary.get("distance_from_trend_pct", 0)
        
        if regime == RiskRegime.UNKNOWN:
            return {
                "action": "WAIT",
                "reason": "Insufficient data for trend calculation",
                "regime": regime.value,
                "trend_line": None,
                "current_price": current_price
            }
        
        # Determine action based on regime and distance from trend
        if regime == RiskRegime.RISK_ON:
            # We're above trend - favorable risk/return
            if distance_pct >= self.entry_threshold * 100:
                action = "BUY"
                reason = f"RISK-ON regime: {distance_pct:.2f}% above trend (favorable risk/return)"
            else:
                action = "HOLD"
                reason = f"RISK-ON but close to trend ({distance_pct:.2f}%), waiting for better entry"
        
        else:  # RISK_OFF
            # We're below trend - unfavorable risk/return
            # Don't exit, but signal to reduce position size
            action = "HOLD"
            reason = f"RISK-OFF regime: {distance_pct:.2f}% below trend (reduce position size, don't exit)"
        
        # Calculate stop loss (wider for long-term strategy)
        # Use trend line as dynamic stop
        stop_loss = trend_line * 0.95  # 5% below trend line
        stop_loss_pct = (current_price - stop_loss) / current_price if current_price > 0 else 0
        
        signal = {
            "action": action,
            "strategy": "TREND",
            "regime": regime.value,
            "is_risk_on": regime == RiskRegime.RISK_ON,
            "current_price": current_price,
            "trend_line": trend_line,
            "distance_from_trend_pct": distance_pct,
            "stop_loss": stop_loss,
            "stop_loss_pct": stop_loss_pct,
            "position_multiplier": self.determine_position_multiplier(regime),
            "reason": reason
        }
        
        # Add statistics if available
        if "statistics" in regime_summary:
            signal["regime_statistics"] = regime_summary["statistics"]
        
        logger.info(f"Trend Signal: {action} | Regime: {regime.value} | "
                   f"Price: ${current_price:.4f} | Trend: ${trend_line:.4f} | "
                   f"Distance: {distance_pct:+.2f}%")
        
        return signal
    
    def should_exit_position(
        self,
        entry_price: float,
        current_price: float,
        trend_line: float,
        regime: RiskRegime
    ) -> Dict[str, any]:
        """
        Determine if we should exit a position.
        
        Varma's principle: Don't exit on trend break, just reduce size.
        Only exit on significant adverse movement.
        
        Args:
            entry_price: Original entry price
            current_price: Current market price
            trend_line: Current trend line value
            regime: Current risk regime
        
        Returns:
            Dict with should_exit, reason, and suggested_action
        """
        # Calculate current P&L
        pnl_pct = (current_price - entry_price) / entry_price
        
        # Exit conditions (very conservative for long-term strategy)
        # 1. Price falls significantly below trend (>10%)
        distance_below_trend = (trend_line - current_price) / trend_line
        if distance_below_trend > 0.10:
            return {
                "should_exit": True,
                "reason": f"Price {distance_below_trend*100:.1f}% below trend (risk too high)",
                "suggested_action": "SELL"
            }
        
        # 2. Large drawdown from entry (>20% for long-term)
        if pnl_pct < -0.20:
            return {
                "should_exit": True,
                "reason": f"Large drawdown: {pnl_pct*100:.1f}% from entry",
                "suggested_action": "SELL"
            }
        
        # Otherwise, hold and adjust size based on regime
        if regime == RiskRegime.RISK_OFF:
            return {
                "should_exit": False,
                "reason": "RISK-OFF regime: reduce position size but don't exit",
                "suggested_action": "REDUCE"
            }
        else:
            return {
                "should_exit": False,
                "reason": "RISK-ON regime: maintain or increase position",
                "suggested_action": "HOLD"
            }
    
    def get_strategy_info(self) -> Dict[str, any]:
        """Get current strategy configuration."""
        return {
            "strategy": "TREND",
            "trend_period": self.trend_period,
            "entry_threshold": self.entry_threshold,
            "time_horizon": "long-term (1+ year)"
        }
