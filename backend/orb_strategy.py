"""
Opening Range Breakout (ORB) Strategy - Samir Varma's intraday approach.

Logic: "Like a leech on a whale" - ride institutional flow by detecting
when large orders are moving the market during the opening period.

Strategy:
1. Define opening range (first 10-20 minutes of trading)
2. Wait for breakout above/below this range
3. Enter in direction of breakout
4. Exit by end of day (intraday only)
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger("ORBStrategy")


class BreakoutDirection(Enum):
    """Breakout direction."""
    LONG = "LONG"    # Price broke above opening range
    SHORT = "SHORT"  # Price broke below opening range
    NONE = "NONE"    # No breakout yet


class ORBStrategy:
    """
    Opening Range Breakout strategy for intraday trading.
    
    Varma's principle: Institutional algorithms (like VWAP) execute large orders
    over time. If price breaks out of the opening range, it suggests a large
    buyer or seller is active, and we can "draft" behind them.
    """
    
    def __init__(
        self,
        range_minutes: int = 15,
        breakout_threshold: float = 0.001,  # 0.1% beyond range to confirm
        min_range_size: float = 0.005  # Minimum 0.5% range to be valid
    ):
        """
        Initialize ORB Strategy.
        
        Args:
            range_minutes: Duration of opening range (10, 15, or 20 minutes typical)
            breakout_threshold: Additional % beyond range to confirm breakout
            min_range_size: Minimum range size as % to avoid false signals
        """
        self.range_minutes = range_minutes
        self.breakout_threshold = breakout_threshold
        self.min_range_size = min_range_size
        
        self.opening_range_high = None
        self.opening_range_low = None
        self.range_defined = False
        
        logger.info(f"ORBStrategy initialized: range={range_minutes}min, "
                   f"threshold={breakout_threshold*100}%")
    
    def define_opening_range(
        self,
        ohlcv_data: pd.DataFrame,
        market_open_time: Optional[datetime] = None
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Define the opening range from OHLCV data.
        
        Args:
            ohlcv_data: DataFrame with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            market_open_time: Optional market open time (if None, uses first candle)
        
        Returns:
            Tuple of (range_high, range_low) or (None, None) if insufficient data
        """
        if ohlcv_data is None or len(ohlcv_data) == 0:
            logger.warning("No OHLCV data provided for opening range")
            return None, None
        
        # Ensure timestamp column exists and is datetime
        if 'timestamp' not in ohlcv_data.columns:
            logger.error("OHLCV data missing 'timestamp' column")
            return None, None
        
        df = ohlcv_data.copy()
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # If market_open_time not specified, use first candle time
        if market_open_time is None:
            market_open_time = df['timestamp'].iloc[0]
        
        # Calculate range end time
        range_end_time = market_open_time + timedelta(minutes=self.range_minutes)
        
        # Filter data within opening range
        opening_data = df[
            (df['timestamp'] >= market_open_time) &
            (df['timestamp'] <= range_end_time)
        ]
        
        if len(opening_data) == 0:
            logger.warning(f"No data found in opening range ({market_open_time} to {range_end_time})")
            return None, None
        
        # Define range as highest high and lowest low during opening period
        range_high = opening_data['high'].max()
        range_low = opening_data['low'].min()
        
        # Validate range size
        range_size_pct = (range_high - range_low) / range_low
        if range_size_pct < self.min_range_size:
            logger.warning(f"Opening range too small: {range_size_pct*100:.2f}% < {self.min_range_size*100}%")
            return None, None
        
        self.opening_range_high = range_high
        self.opening_range_low = range_low
        self.range_defined = True
        
        logger.info(f"Opening range defined: HIGH=${range_high:.4f}, LOW=${range_low:.4f}, "
                   f"size={range_size_pct*100:.2f}%")
        
        return range_high, range_low
    
    def detect_breakout(
        self,
        current_price: float,
        current_volume: Optional[float] = None
    ) -> BreakoutDirection:
        """
        Detect if price has broken out of the opening range.
        
        Args:
            current_price: Current market price
            current_volume: Optional current volume (for confirmation)
        
        Returns:
            BreakoutDirection enum
        """
        if not self.range_defined or self.opening_range_high is None or self.opening_range_low is None:
            logger.warning("Opening range not defined, cannot detect breakout")
            return BreakoutDirection.NONE
        
        # Calculate breakout levels with threshold
        breakout_high = self.opening_range_high * (1 + self.breakout_threshold)
        breakout_low = self.opening_range_low * (1 - self.breakout_threshold)
        
        # Check for breakout
        if current_price > breakout_high:
            logger.info(f"🚀 LONG BREAKOUT: ${current_price:.4f} > ${breakout_high:.4f}")
            return BreakoutDirection.LONG
        elif current_price < breakout_low:
            logger.info(f"📉 SHORT BREAKOUT: ${current_price:.4f} < ${breakout_low:.4f}")
            return BreakoutDirection.SHORT
        else:
            logger.debug(f"No breakout: ${current_price:.4f} within range [${breakout_low:.4f}, ${breakout_high:.4f}]")
            return BreakoutDirection.NONE
    
    def generate_orb_signal(
        self,
        current_price: float,
        ohlcv_data: pd.DataFrame,
        market_open_time: Optional[datetime] = None
    ) -> Dict[str, any]:
        """
        Generate ORB trading signal.
        
        Args:
            current_price: Current market price
            ohlcv_data: Historical OHLCV data
            market_open_time: Optional market open time
        
        Returns:
            Dict with signal, direction, entry_price, stop_loss, and metadata
        """
        # Define opening range if not already done
        if not self.range_defined:
            range_high, range_low = self.define_opening_range(ohlcv_data, market_open_time)
            if range_high is None or range_low is None:
                return {
                    "action": "WAIT",
                    "reason": "Opening range not defined (insufficient data or range too small)",
                    "opening_range_high": None,
                    "opening_range_low": None
                }
        
        # Detect breakout
        breakout = self.detect_breakout(current_price)
        
        if breakout == BreakoutDirection.NONE:
            return {
                "action": "WAIT",
                "reason": "No breakout detected",
                "opening_range_high": self.opening_range_high,
                "opening_range_low": self.opening_range_low,
                "current_price": current_price
            }
        
        # Generate signal based on breakout direction
        if breakout == BreakoutDirection.LONG:
            action = "BUY"
            entry_price = current_price
            # Stop loss just below opening range low
            stop_loss = self.opening_range_low * 0.995  # 0.5% below range low
            stop_loss_pct = (entry_price - stop_loss) / entry_price
            
        else:  # SHORT
            action = "SELL"  # For crypto spot, this would be exit or short if supported
            entry_price = current_price
            # Stop loss just above opening range high
            stop_loss = self.opening_range_high * 1.005  # 0.5% above range high
            stop_loss_pct = (stop_loss - entry_price) / entry_price
        
        signal = {
            "action": action,
            "strategy": "ORB",
            "breakout_direction": breakout.value,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "stop_loss_pct": stop_loss_pct,
            "opening_range_high": self.opening_range_high,
            "opening_range_low": self.opening_range_low,
            "range_size_pct": (self.opening_range_high - self.opening_range_low) / self.opening_range_low,
            "reason": f"{breakout.value} breakout detected - riding institutional flow"
        }
        
        logger.info(f"ORB Signal: {action} at ${entry_price:.4f}, SL=${stop_loss:.4f} ({stop_loss_pct*100:.2f}%)")
        
        return signal
    
    def reset_range(self):
        """Reset opening range for new trading day."""
        self.opening_range_high = None
        self.opening_range_low = None
        self.range_defined = False
        logger.info("Opening range reset for new session")
    
    def get_range_info(self) -> Dict[str, any]:
        """Get current opening range information."""
        return {
            "range_defined": self.range_defined,
            "opening_range_high": self.opening_range_high,
            "opening_range_low": self.opening_range_low,
            "range_minutes": self.range_minutes,
            "breakout_threshold": self.breakout_threshold
        }
