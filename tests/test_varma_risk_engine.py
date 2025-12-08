"""
Unit tests for VarmaRiskEngine - Position sizing and risk management.
"""

import pytest
import sys
import os
from unittest.mock import MagicMock

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from varma_risk_engine import VarmaRiskEngine


class TestVarmaRiskEngine:
    """Test VarmaRiskEngine functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = VarmaRiskEngine(
            kelly_dampener=0.25,
            max_drawdown_target=0.45,
            risk_on_multiplier=1.5,
            risk_off_multiplier=0.5,
            min_position_size=0.05,
            max_position_size=0.25
        )

    def test_initialization(self):
        """Test engine initialization with correct parameters."""
        assert self.engine.kelly_dampener == 0.25
        assert self.engine.max_drawdown_target == 0.45
        assert self.engine.risk_on_multiplier == 1.5
        assert self.engine.risk_off_multiplier == 0.5
        assert self.engine.min_position_size == 0.05
        assert self.engine.max_position_size == 0.25

    def test_kelly_fraction_calculation(self):
        """Test Kelly Criterion fraction calculation."""
        # Test winning scenario
        kelly = self.engine.calculate_kelly_fraction(0.6, 0.10, 0.05)  # 60% win rate, 10% wins, 5% losses
        assert kelly > 0  # Should be positive

        # Test losing scenario
        kelly = self.engine.calculate_kelly_fraction(0.4, 0.05, 0.10)  # 40% win rate, 5% wins, 10% losses
        assert kelly == 0.0  # Should be 0 (max(0, negative_kelly))

        # Test edge cases
        kelly = self.engine.calculate_kelly_fraction(0.5, 0.05, 0.05)  # Break-even
        assert abs(kelly) < 0.01  # Should be close to zero

    def test_kelly_fraction_with_invalid_inputs(self):
        """Test Kelly calculation with invalid inputs."""
        # Zero or negative loss
        kelly = self.engine.calculate_kelly_fraction(0.6, 0.10, 0.0)
        assert kelly == 0.0

        # Zero or negative win
        kelly = self.engine.calculate_kelly_fraction(0.6, 0.0, 0.05)
        assert kelly == 0.0

    def test_drawdown_position_sizing(self):
        """Test position sizing based on drawdown limits."""
        # Test with 3% stop loss and $1000 capital
        size = self.engine.calculate_position_from_drawdown(0.03, 1000.0)
        expected_max = 1000.0 * self.engine.max_position_size
        expected_min = 1000.0 * self.engine.min_position_size

        assert expected_min <= size <= expected_max

        # Test with very tight stop (0.5%)
        size_tight = self.engine.calculate_position_from_drawdown(0.005, 1000.0)
        assert size_tight <= expected_max

    def test_regime_adjustment(self):
        """Test position size adjustment based on risk regime."""
        base_size = 100.0

        # Risk-on regime should increase size
        adjusted_on = self.engine.adjust_for_regime(base_size, True)  # is_risk_on=True
        assert adjusted_on == base_size * 1.5

        # Risk-off regime should decrease size
        adjusted_off = self.engine.adjust_for_regime(base_size, False)  # is_risk_on=False
        assert adjusted_off == base_size * 0.5

    def test_position_size_calculation_kelly(self):
        """Test complete position sizing with Kelly method."""
        result = self.engine.calculate_position_size(
            capital=1000.0,
            win_rate=0.55,
            avg_win=0.08,
            avg_loss=0.04,
            stop_loss_pct=0.03,
            is_risk_on=True,
            method="kelly"
        )

        assert "position_size_usd" in result
        assert "position_fraction" in result
        assert "method" in result
        assert "regime" in result
        assert result["method"] == "kelly"
        assert result["regime"] == "RISK-ON"
        assert result["position_size_usd"] > 0
        assert 0.05 <= result["position_fraction"] <= 0.25  # Within bounds

    def test_position_size_calculation_drawdown(self):
        """Test complete position sizing with drawdown method."""
        result = self.engine.calculate_position_size(
            capital=1000.0,
            win_rate=0.55,
            avg_win=0.08,
            avg_loss=0.04,
            stop_loss_pct=0.03,
            is_risk_on=False,
            method="drawdown"
        )

        assert result["method"] == "drawdown"
        assert result["regime"] == "RISK-OFF"
        assert result["position_size_usd"] > 0

    def test_position_size_bounds_enforcement(self):
        """Test that position sizes are enforced within bounds."""
        # Force a very large Kelly result
        result = self.engine.calculate_position_size(
            capital=1000.0,
            win_rate=0.9,  # Very high win rate
            avg_win=0.50,  # Large wins
            avg_loss=0.01,  # Small losses
            stop_loss_pct=0.03,
            is_risk_on=True,
            method="kelly"
        )

        # Should be capped at max_position_size
        assert result["position_fraction"] <= self.engine.max_position_size

    def test_performance_history_update(self):
        """Test updating Kelly inputs from trade history."""
        # Mock closed trades data
        closed_trades = [
            {"entry_price": 100.0, "exit_price": 105.0},  # 5% win
            {"entry_price": 100.0, "exit_price": 98.0},   # 2% loss
            {"entry_price": 100.0, "exit_price": 102.0},  # 2% win
            {"entry_price": 100.0, "exit_price": 97.0},   # 3% loss
        ]

        metrics = self.engine.update_from_performance_history(closed_trades)

        assert "win_rate" in metrics
        assert "avg_win_pct" in metrics
        assert "avg_loss_pct" in metrics
        assert "total_trades" in metrics
        assert metrics["total_trades"] == 4
        assert metrics["wins_count"] == 2
        assert metrics["losses_count"] == 2
        assert 0.4 <= metrics["win_rate"] <= 0.6  # Should be around 50%

    def test_performance_history_empty(self):
        """Test performance update with no trades."""
        metrics = self.engine.update_from_performance_history([])

        assert metrics["win_rate"] == 0.55  # Default
        assert metrics["avg_win_pct"] == 0.05  # Default
        assert metrics["avg_loss_pct"] == 0.03  # Default
        assert metrics["total_trades"] == 0

    def test_risk_validation_approved(self):
        """Test risk validation with valid trade."""
        validation = self.engine.validate_trade_risk(
            position_size_usd=50.0,
            capital=1000.0,
            stop_loss_price=97.0,
            entry_price=100.0,
            regime="RISK_OFF",
            existing_positions=[]
        )

        assert validation["approved"] == True
        assert "warnings" in validation
        assert "risk_metrics" in validation

    def test_risk_validation_adjusted_size_too_large(self):
        """Test risk validation adjusts oversized position instead of rejecting."""
        validation = self.engine.validate_trade_risk(
            position_size_usd=400.0,  # 40% of capital (above max 25%)
            capital=1000.0,
            stop_loss_price=97.0,
            entry_price=100.0,
            regime="RISK_OFF",
            existing_positions=[]
        )

        # Should be approved but with size adjustment
        assert validation["approved"] == True
        assert "adjustments" in validation
        assert "position_size_usd" in validation["adjustments"]
        assert validation["adjustments"]["position_size_usd"] == 250.0  # Max 25% of 1000
        assert len(validation["warnings"]) > 0

    def test_risk_validation_rejected_stop_too_wide(self):
        """Test risk validation rejects stop loss too wide."""
        validation = self.engine.validate_trade_risk(
            position_size_usd=50.0,
            capital=1000.0,
            stop_loss_price=85.0,  # 15% stop (above max 10%)
            entry_price=100.0,
            regime="RISK_OFF",
            existing_positions=[]
        )

        assert validation["approved"] == False
        assert len(validation["warnings"]) > 0

    def test_risk_validation_adjustment(self):
        """Test risk validation with automatic adjustment."""
        validation = self.engine.validate_trade_risk(
            position_size_usd=300.0,  # 30% of capital (above max 25%)
            capital=1000.0,
            stop_loss_price=98.0,
            entry_price=100.0,
            regime="RISK_OFF",
            existing_positions=[]
        )

        # Should be approved but with adjustment
        assert validation["approved"] == True  # Approved with adjustment
        assert "adjustments" in validation
        assert "position_size_usd" in validation["adjustments"]
        assert validation["adjustments"]["position_size_usd"] <= 250.0  # Max 25%

    def test_risk_validation_portfolio_limits(self):
        """Test risk validation with portfolio concentration limits."""
        existing_positions = [
            {"position_size_usd": 150.0},  # Large existing position
        ]

        validation = self.engine.validate_trade_risk(
            position_size_usd=150.0,  # New position
            capital=1000.0,
            stop_loss_price=98.0,
            entry_price=100.0,
            regime="RISK_OFF",
            existing_positions=existing_positions
        )

        # Combined exposure would be 300/1000 = 30%, which is within 2x limit
        assert validation["approved"] == True

    def test_get_risk_parameters(self):
        """Test getting risk parameters for debugging."""
        params = self.engine.get_risk_parameters()

        assert "kelly_dampener" in params
        assert "max_drawdown_target" in params
        assert "risk_on_multiplier" in params
        assert "risk_off_multiplier" in params
        assert "min_position_size" in params
        assert "max_position_size" in params

        assert params["kelly_dampener"] == 0.25
        assert params["max_drawdown_target"] == 0.45
