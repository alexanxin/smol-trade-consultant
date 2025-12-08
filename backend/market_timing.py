"""
Market Timing System - Determines active market sessions and volatility windows.

For ORB strategy, identifies optimal times for opening range breakout detection
based on market sessions and volatility conditions.
"""

import logging
from datetime import datetime, timedelta, time
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger("MarketTiming")


@dataclass
class MarketSession:
    """Represents a market trading session."""
    name: str
    start_hour: int  # UTC hour (0-23)
    duration_hours: float
    description: str
    volatility_rating: str  # 'low', 'medium', 'high'


@dataclass
class MarketStatus:
    """Current market status information."""
    current_session: Optional[MarketSession]
    next_session: Optional[MarketSession]
    minutes_to_next: int
    is_active_period: bool
    volatility_level: str
    recommendation: str


class MarketTiming:
    """
    Market timing system for crypto trading.

    Defines market sessions and determines optimal trading windows
    based on volatility and session characteristics.
    """

    # Define crypto market sessions (approximating traditional market hours)
    CRYPTO_SESSIONS = [
        MarketSession("Asian Session", 0, 8.0, "Asia-Pacific crypto trading", "medium"),
        MarketSession("European Open", 8, 5.5, "European market overlap", "high"),
        MarketSession("US Session", 13, 6.0, "US market hours", "high"),
        MarketSession("Evening Volatility", 20, 4.0, "Global evening trading", "medium"),
    ]

    def __init__(
        self,
        volatility_threshold: float = 0.015,  # 1.5% threshold for "high volatility"
        min_session_overlap: int = 15  # Minutes before session start to activate
    ):
        """
        Initialize market timing system.

        Args:
            volatility_threshold: Price change % to consider "high volatility"
            min_session_overlap: Minutes before session to start monitoring
        """
        self.volatility_threshold = volatility_threshold
        self.min_session_overlap = min_session_overlap
        self.price_history = []  # Store recent prices for volatility calc
        self.max_history = 20  # Keep last 20 prices

        logger.info("MarketTiming initialized with volatility threshold: "
                   f"{volatility_threshold*100:.1f}%")

    def get_current_market_status(self, current_price: Optional[float] = None) -> MarketStatus:
        """
        Get comprehensive market status information.

        Args:
            current_price: Current asset price for volatility calculation

        Returns:
            MarketStatus with current session, next session, and recommendations
        """
        now = datetime.utcnow()
        current_hour = now.hour
        current_minute = now.minute

        # Find current and next sessions
        current_session = None
        next_session = None
        min_minutes_to_next = float('inf')

        for session in self.CRYPTO_SESSIONS:
            session_start = session.start_hour
            session_end = (session.start_hour + session.duration_hours) % 24

            # Check if current time is within this session
            if session_start <= session_end:
                # Normal case (e.g., 8-13)
                in_session = session_start <= current_hour < session_end
            else:
                # Wrap-around case (e.g., 20-4)
                in_session = current_hour >= session_start or current_hour < session_end

            if in_session:
                current_session = session

            # Calculate minutes to next session start
            if current_hour < session.start_hour:
                minutes_to_next = (session.start_hour - current_hour) * 60 - current_minute
            else:
                # Next day
                minutes_to_next = (24 - current_hour + session.start_hour) * 60 - current_minute

            if minutes_to_next < min_minutes_to_next:
                min_minutes_to_next = minutes_to_next
                next_session = session

        # Determine if we should be active
        is_active_period = False
        if current_session:
            is_active_period = True
        elif next_session and min_minutes_to_next <= self.min_session_overlap:
            is_active_period = True  # Approaching next session

        # Calculate volatility level
        volatility_level = self._calculate_volatility_level(current_price)

        # Generate recommendation
        recommendation = self._generate_recommendation(
            current_session, next_session, min_minutes_to_next,
            is_active_period, volatility_level
        )

        return MarketStatus(
            current_session=current_session,
            next_session=next_session,
            minutes_to_next=int(min_minutes_to_next),
            is_active_period=is_active_period,
            volatility_level=volatility_level,
            recommendation=recommendation
        )

    def should_run_orb_strategy(self, current_price: Optional[float] = None) -> Tuple[bool, str]:
        """
        Determine if ORB strategy should be active based on market conditions.

        Args:
            current_price: Current asset price

        Returns:
            Tuple of (should_run, reason)
        """
        status = self.get_current_market_status(current_price)

        # Always allow during active market sessions
        if status.is_active_period:
            return True, f"Active during {status.current_session.name if status.current_session else 'session transition'}"

        # Check volatility for off-hours trading
        if status.volatility_level == "high":
            return True, f"High volatility detected ({status.volatility_level}) despite off-hours"

        # Conservative: only run during market sessions
        return False, f"Outside market hours, low volatility ({status.volatility_level})"

    def update_price_history(self, price: float):
        """Update price history for volatility calculations."""
        self.price_history.append(price)
        if len(self.price_history) > self.max_history:
            self.price_history.pop(0)

    def _calculate_volatility_level(self, current_price: Optional[float]) -> str:
        """Calculate current volatility level."""
        if not current_price or len(self.price_history) < 5:
            return "unknown"

        # Calculate recent price changes
        recent_prices = self.price_history[-10:] + [current_price]  # Last 10 + current
        if len(recent_prices) < 5:
            return "low"

        # Calculate volatility as average absolute percentage change
        changes = []
        for i in range(1, len(recent_prices)):
            change = abs(recent_prices[i] - recent_prices[i-1]) / recent_prices[i-1]
            changes.append(change)

        avg_volatility = np.mean(changes) if changes else 0

        # Classify volatility
        if avg_volatility >= self.volatility_threshold * 2:  # 3%+ average change
            return "extreme"
        elif avg_volatility >= self.volatility_threshold:  # 1.5%+ average change
            return "high"
        elif avg_volatility >= self.volatility_threshold * 0.5:  # 0.75%+ average change
            return "medium"
        else:
            return "low"

    def _generate_recommendation(
        self,
        current_session: Optional[MarketSession],
        next_session: Optional[MarketSession],
        minutes_to_next: int,
        is_active_period: bool,
        volatility_level: str
    ) -> str:
        """Generate trading recommendation based on market conditions."""

        if current_session:
            if volatility_level in ["high", "extreme"]:
                return f"🚀 ACTIVE: {current_session.name} with {volatility_level} volatility - Ideal for ORB"
            else:
                return f"⚡ ACTIVE: {current_session.name} - Monitor for volatility spikes"

        if is_active_period and next_session:
            return f"🎯 APPROACHING: {next_session.name} starts in {minutes_to_next}min - Prepare ORB range"

        if volatility_level == "high":
            return f"⚡ HIGH VOLATILITY: {volatility_level} conditions detected - Consider ORB activation"

        if next_session:
            hours_to_next = minutes_to_next // 60
            mins_remainder = minutes_to_next % 60
            return f"⏰ NEXT: {next_session.name} in {hours_to_next}h {mins_remainder}m"

        return "😴 QUIET: Outside typical market hours"

    def get_session_schedule(self) -> List[Dict]:
        """Get formatted schedule of all market sessions."""
        schedule = []
        for session in self.CRYPTO_SESSIONS:
            schedule.append({
                "name": session.name,
                "utc_start": f"{session.start_hour:02d}:00 UTC",
                "duration": f"{session.duration_hours}h",
                "volatility": session.volatility_rating,
                "description": session.description
            })
        return schedule

    def get_next_session_info(self) -> Dict:
        """Get information about the next market session."""
        now = datetime.utcnow()
        current_hour = now.hour

        next_session = None
        min_minutes = float('inf')

        for session in self.CRYPTO_SESSIONS:
            if current_hour < session.start_hour:
                minutes = (session.start_hour - current_hour) * 60 - now.minute
            else:
                minutes = (24 - current_hour + session.start_hour) * 60 - now.minute

            if minutes < min_minutes:
                min_minutes = minutes
                next_session = session

        if next_session:
            next_time = now + timedelta(minutes=min_minutes)
            return {
                "session_name": next_session.name,
                "minutes_until": int(min_minutes),
                "next_time": next_time.strftime("%H:%M UTC"),
                "description": next_session.description
            }

        return {"error": "No next session found"}

    def format_market_status_display(self, status: MarketStatus) -> str:
        """Format market status for display."""
        lines = []

        # Current status
        if status.current_session:
            lines.append(f"📊 CURRENT: {status.current_session.name}")
            lines.append(f"   🕐 Active until ~{(status.current_session.start_hour + status.current_session.duration_hours) % 24:.0f}:00 UTC")
        else:
            lines.append("📊 CURRENT: Outside regular sessions")

        # Next session
        if status.next_session:
            hours = status.minutes_to_next // 60
            mins = status.minutes_to_next % 60
            next_time = (datetime.utcnow() + timedelta(minutes=status.minutes_to_next)).strftime("%H:%M UTC")
            lines.append(f"⏰ NEXT: {status.next_session.name} in {hours}h {mins}m ({next_time})")

        # Volatility & recommendation
        volatility_icon = {"low": "🟢", "medium": "🟡", "high": "🟠", "extreme": "🔴", "unknown": "⚪"}.get(status.volatility_level, "⚪")
        lines.append(f"{volatility_icon} VOLATILITY: {status.volatility_level.upper()}")
        lines.append(f"💡 {status.recommendation}")

        # ORB strategy status
        should_run, reason = self.should_run_orb_strategy()
        orb_status = "✅ ACTIVE" if should_run else "⏸️  INACTIVE"
        lines.append(f"🎯 ORB STRATEGY: {orb_status} - {reason}")

        return "\n".join(lines)
