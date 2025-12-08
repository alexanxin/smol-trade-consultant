"""
Regime Classifier - Identifies risk regimes based on price position relative to trend.

Implements Samir Varma's principle:
- ~2/3 of returns occur above the trend line with ~1/3 of risk
- ~2/3 of risk occurs below the trend line with ~1/3 of returns
- Risk clusters (is not constant over time)
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from enum import Enum

logger = logging.getLogger("RegimeClassifier")


class RiskRegime(Enum):
    """Risk regime states."""
    RISK_ON = "RISK_ON"    # Above trend, favorable risk/return
    RISK_OFF = "RISK_OFF"  # Below trend, unfavorable risk/return
    UNKNOWN = "UNKNOWN"    # Insufficient data


class RegimeClassifier:
    """
    Classifies market risk regime based on position relative to long-term trend.
    
    Uses a simple but effective rule:
    - RISK_ON: Price is above the long-term moving average (e.g., 200-day MA)
    - RISK_OFF: Price is below the long-term moving average
    
    This classification drives position sizing adjustments.
    """
    
    def __init__(self, trend_period: int = 200, volatility_window: int = 20):
        """
        Initialize Regime Classifier.
        
        Args:
            trend_period: Period for long-term trend (200 for 200-day MA)
            volatility_window: Window for volatility clustering detection
        """
        self.trend_period = trend_period
        self.volatility_window = volatility_window
        logger.info(f"RegimeClassifier initialized: trend_period={trend_period}")
    
    def calculate_trend_line(self, prices: pd.Series) -> Optional[float]:
        """
        Calculate the long-term trend line (moving average).
        
        Args:
            prices: Series of historical prices
        
        Returns:
            Current trend line value (MA), or None if insufficient data
        """
        if len(prices) < self.trend_period:
            logger.warning(f"Insufficient data for trend calculation: {len(prices)} < {self.trend_period}")
            return None
        
        # Calculate simple moving average
        trend_line = prices.rolling(window=self.trend_period).mean().iloc[-1]
        
        logger.debug(f"Trend line ({self.trend_period}-period MA): {trend_line:.4f}")
        return trend_line
    
    def classify_regime(self, current_price: float, trend_line: float) -> RiskRegime:
        """
        Classify current risk regime based on price position relative to trend.
        
        Args:
            current_price: Current market price
            trend_line: Long-term trend line value (e.g., 200-day MA)
        
        Returns:
            RiskRegime enum (RISK_ON or RISK_OFF)
        """
        if trend_line is None or current_price is None:
            return RiskRegime.UNKNOWN
        
        if current_price > trend_line:
            regime = RiskRegime.RISK_ON
            distance_pct = ((current_price - trend_line) / trend_line) * 100
            logger.info(f"Regime: RISK-ON (price ${current_price:.4f} is {distance_pct:.2f}% above trend ${trend_line:.4f})")
        else:
            regime = RiskRegime.RISK_OFF
            distance_pct = ((trend_line - current_price) / trend_line) * 100
            logger.info(f"Regime: RISK-OFF (price ${current_price:.4f} is {distance_pct:.2f}% below trend ${trend_line:.4f})")
        
        return regime
    
    def calculate_regime_statistics(
        self,
        prices: pd.Series,
        returns: pd.Series
    ) -> Dict[str, float]:
        """
        Calculate historical statistics for each regime to validate Varma's principle.
        
        Expected results:
        - RISK_ON: ~67% of returns, ~33% of risk (volatility)
        - RISK_OFF: ~33% of returns, ~67% of risk
        
        Args:
            prices: Historical price series
            returns: Historical return series (same length as prices)
        
        Returns:
            Dict with regime statistics
        """
        if len(prices) < self.trend_period:
            logger.warning("Insufficient data for regime statistics")
            return {}
        
        # Calculate trend line for each period
        trend_line = prices.rolling(window=self.trend_period).mean()
        
        # Classify each period
        is_risk_on = prices > trend_line
        
        # Calculate statistics for each regime
        risk_on_returns = returns[is_risk_on]
        risk_off_returns = returns[~is_risk_on]
        
        stats = {
            "risk_on_pct_time": (is_risk_on.sum() / len(is_risk_on)) * 100,
            "risk_off_pct_time": ((~is_risk_on).sum() / len(is_risk_on)) * 100,
            "risk_on_avg_return": risk_on_returns.mean() if len(risk_on_returns) > 0 else 0,
            "risk_off_avg_return": risk_off_returns.mean() if len(risk_off_returns) > 0 else 0,
            "risk_on_volatility": risk_on_returns.std() if len(risk_on_returns) > 0 else 0,
            "risk_off_volatility": risk_off_returns.std() if len(risk_off_returns) > 0 else 0,
            "risk_on_total_return": risk_on_returns.sum() if len(risk_on_returns) > 0 else 0,
            "risk_off_total_return": risk_off_returns.sum() if len(risk_off_returns) > 0 else 0
        }
        
        # Calculate percentage of total returns in each regime
        total_return = stats["risk_on_total_return"] + stats["risk_off_total_return"]
        if total_return != 0:
            stats["risk_on_pct_returns"] = (stats["risk_on_total_return"] / total_return) * 100
            stats["risk_off_pct_returns"] = (stats["risk_off_total_return"] / total_return) * 100
        else:
            stats["risk_on_pct_returns"] = 0
            stats["risk_off_pct_returns"] = 0
        
        logger.info(f"Regime Statistics: RISK-ON={stats['risk_on_pct_time']:.1f}% time, "
                   f"{stats['risk_on_pct_returns']:.1f}% returns | "
                   f"RISK-OFF={stats['risk_off_pct_time']:.1f}% time, "
                   f"{stats['risk_off_pct_returns']:.1f}% returns")
        
        return stats
    
    def detect_risk_clustering(
        self,
        returns: pd.Series,
        regime_history: pd.Series
    ) -> Dict[str, any]:
        """
        Detect if risk is clustering (consecutive negative returns in RISK_OFF regime).
        
        Varma's principle: Risk clusters, it's not constant.
        
        Args:
            returns: Recent return series
            regime_history: Series of regime classifications (True=RISK_ON, False=RISK_OFF)
        
        Returns:
            Dict with clustering metrics
        """
        if len(returns) < self.volatility_window:
            return {"is_clustering": False, "consecutive_down_days": 0}
        
        # Focus on RISK_OFF periods
        risk_off_mask = ~regime_history
        risk_off_returns = returns[risk_off_mask]
        
        # Count consecutive down days
        consecutive_down = 0
        for ret in risk_off_returns.tail(self.volatility_window):
            if ret < 0:
                consecutive_down += 1
            else:
                consecutive_down = 0
        
        # Risk is clustering if we have 3+ consecutive down days in RISK_OFF
        is_clustering = consecutive_down >= 3
        
        clustering_info = {
            "is_clustering": is_clustering,
            "consecutive_down_days": consecutive_down,
            "recent_volatility": risk_off_returns.tail(self.volatility_window).std() if len(risk_off_returns) > 0 else 0
        }
        
        if is_clustering:
            logger.warning(f"⚠️  Risk clustering detected: {consecutive_down} consecutive down days in RISK-OFF regime")
        
        return clustering_info
    
    def get_regime_summary(
        self,
        current_price: float,
        prices: pd.Series,
        returns: Optional[pd.Series] = None
    ) -> Dict[str, any]:
        """
        Get comprehensive regime analysis.
        
        Args:
            current_price: Current market price
            prices: Historical price series
            returns: Optional historical return series
        
        Returns:
            Dict with regime classification, trend line, and statistics
        """
        trend_line = self.calculate_trend_line(prices)
        
        if trend_line is None:
            return {
                "regime": RiskRegime.UNKNOWN,
                "trend_line": None,
                "current_price": current_price,
                "distance_from_trend_pct": None
            }
        
        regime = self.classify_regime(current_price, trend_line)
        distance_pct = ((current_price - trend_line) / trend_line) * 100
        
        summary = {
            "regime": regime,
            "trend_line": trend_line,
            "current_price": current_price,
            "distance_from_trend_pct": distance_pct,
            "is_risk_on": regime == RiskRegime.RISK_ON
        }
        
        # Add statistics if returns provided
        if returns is not None and len(returns) >= self.trend_period:
            summary["statistics"] = self.calculate_regime_statistics(prices, returns)
        
        return summary
