"""
Unit tests for SmartExecution - Order camouflage and hidden execution.
"""

import pytest
import sys
import os
import random

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from smart_execution import SmartExecution


class TestSmartExecution:
    """Test SmartExecution functionality."""

    def setup_method(self):
        """Set up test fixtures with fixed seed for reproducible tests."""
        self.execution = SmartExecution(seed=42)  # Fixed seed for consistent results

    def test_initialization(self):
        """Test SmartExecution initialization."""
        assert self.execution is not None

    def test_odd_lot_sizing(self):
        """Test odd-lot size generation."""
        # Test normal case
        size = self.execution.generate_odd_lot_size(
            target_usd_amount=100.0,
            price=50.0
        )

        # Should be close to target (2 units) but with odd-lot adjustment
        expected_base = 100.0 / 50.0  # 2.0 units
        assert 1.8 <= size <= 2.2  # Should be reasonably close

        # Test minimum size enforcement
        tiny_size = self.execution.generate_odd_lot_size(
            target_usd_amount=0.001,  # Very small amount
            price=100.0,
            min_size=0.01
        )
        assert tiny_size >= 0.01  # Should respect minimum

    def test_odd_lot_consistency(self):
        """Test that odd-lot sizing produces different results (not round numbers)."""
        sizes = []
        for _ in range(10):
            size = self.execution.generate_odd_lot_size(
                target_usd_amount=100.0,
                price=50.0
            )
            sizes.append(size)

        # Should have some variation (not all exactly 2.0)
        unique_sizes = len(set(sizes))
        assert unique_sizes > 1  # Should have variation

    def test_camouflaged_stop_calculation(self):
        """Test camouflaged stop-loss price calculation."""
        entry_price = 100.0
        stop_pct = 0.03  # 3% stop

        # Long position stop
        stop_price_long = self.execution.calculate_camouflaged_stop(
            entry_price=entry_price,
            stop_loss_pct=stop_pct,
            direction="long"
        )

        expected_base_stop = entry_price * (1 - stop_pct)  # 97.0
        assert 96.5 <= stop_price_long <= 97.5  # Should be close but camouflaged

        # Short position stop
        stop_price_short = self.execution.calculate_camouflaged_stop(
            entry_price=entry_price,
            stop_loss_pct=stop_pct,
            direction="short"
        )

        expected_base_stop_short = entry_price * (1 + stop_pct)  # 103.0
        assert 102.5 <= stop_price_short <= 103.5  # Should be close but camouflaged

    def test_camouflaged_stop_non_round(self):
        """Test that camouflaged stops avoid round numbers."""
        entry_price = 100.0
        stop_pct = 0.03

        stop_price = self.execution.calculate_camouflaged_stop(
            entry_price=entry_price,
            stop_loss_pct=stop_pct,
            direction="long"
        )

        # Extract decimal part
        decimal_part = stop_price - int(stop_price)

        # Should avoid common round endings (0.00, 0.25, 0.50, 0.75)
        common_roundings = [0.00, 0.25, 0.50, 0.75]
        assert decimal_part not in common_roundings

    def test_prime_like_number_generation(self):
        """Test prime-like number generation."""
        target = 100.0

        result = self.execution.generate_prime_like_number(target)

        # Should be reasonably close to target
        assert 95.0 <= result <= 105.0

        # Should be different from target (with high probability)
        assert abs(result - target) > 0.1

    def test_place_hidden_order_buy(self):
        """Test placing a camouflaged buy order."""
        order = self.execution.place_hidden_order(
            order_type="BUY",
            entry_price=100.0,
            position_size_usd=1000.0,
            stop_loss_pct=0.03,
            take_profit_pct=None
        )

        assert order["order_type"] == "BUY"
        assert order["entry_price"] == 100.0
        assert order["asset_quantity"] > 0
        assert order["position_size_usd"] > 0
        assert order["stop_loss"] < 100.0  # Stop below entry for buy
        assert order["take_profit"] is None  # No take profit set
        assert order["execution_style"] == "camouflaged"
        assert "Odd-lot sizing" in order["notes"]

    def test_place_hidden_order_sell(self):
        """Test placing a camouflaged sell order."""
        order = self.execution.place_hidden_order(
            order_type="SELL",
            entry_price=100.0,
            position_size_usd=1000.0,
            stop_loss_pct=0.03,
            take_profit_pct=None
        )

        assert order["order_type"] == "SELL"
        assert order["entry_price"] == 100.0
        assert order["asset_quantity"] > 0
        assert order["position_size_usd"] > 0
        assert order["stop_loss"] > 100.0  # Stop above entry for sell
        assert order["take_profit"] is None

    def test_place_hidden_order_with_take_profit(self):
        """Test placing order with take profit."""
        order = self.execution.place_hidden_order(
            order_type="BUY",
            entry_price=100.0,
            position_size_usd=1000.0,
            stop_loss_pct=0.03,
            take_profit_pct=0.05  # 5% take profit
        )

        assert order["order_type"] == "BUY"
        assert order["take_profit"] is not None
        assert order["take_profit"] > 100.0  # Take profit above entry for buy

        # Take profit should be close to expected but camouflaged
        expected_tp = 100.0 * 1.05  # 105.0
        assert 104.5 <= order["take_profit"] <= 105.5

    def test_asset_quantity_calculation(self):
        """Test that asset quantity matches position size calculation."""
        target_usd = 1000.0
        price = 50.0
        expected_qty = target_usd / price  # 20.0

        order = self.execution.place_hidden_order(
            order_type="BUY",
            entry_price=price,
            position_size_usd=target_usd,
            stop_loss_pct=0.03
        )

        # Asset quantity should be close to expected but odd-lot adjusted
        assert 18.0 <= order["asset_quantity"] <= 22.0

        # Position size should be quantity * price (approximately target)
        calculated_usd = order["asset_quantity"] * price
        assert 900 <= calculated_usd <= 1100  # Close to target

    def test_stop_loss_placement_buy(self):
        """Test stop loss placement for buy orders."""
        entry_price = 100.0
        stop_pct = 0.03  # 3%

        order = self.execution.place_hidden_order(
            order_type="BUY",
            entry_price=entry_price,
            position_size_usd=1000.0,
            stop_loss_pct=stop_pct
        )

        stop_price = order["stop_loss"]

        # Stop should be below entry for buys
        assert stop_price < entry_price

        # Stop should be close to expected stop level (97.0) but camouflaged
        expected_stop = entry_price * (1 - stop_pct)
        assert abs(stop_price - expected_stop) < 0.5  # Within 0.5 of expected

    def test_stop_loss_placement_sell(self):
        """Test stop loss placement for sell orders."""
        entry_price = 100.0
        stop_pct = 0.03  # 3%

        order = self.execution.place_hidden_order(
            order_type="SELL",
            entry_price=entry_price,
            position_size_usd=1000.0,
            stop_loss_pct=stop_pct
        )

        stop_price = order["stop_loss"]

        # Stop should be above entry for sells
        assert stop_price > entry_price

        # Stop should be close to expected stop level (103.0) but camouflaged
        expected_stop = entry_price * (1 + stop_pct)
        assert abs(stop_price - expected_stop) < 0.5  # Within 0.5 of expected

    def test_order_consistency_with_seed(self):
        """Test that results are consistent with fixed seed."""
        # Create a single execution instance with fixed seed
        exec_instance = SmartExecution(seed=123)

        # Generate order multiple times with same instance
        order1 = exec_instance.place_hidden_order(
            order_type="BUY",
            entry_price=100.0,
            position_size_usd=1000.0,
            stop_loss_pct=0.03
        )

        # Reset random state and try again
        exec_instance2 = SmartExecution(seed=123)
        order2 = exec_instance2.place_hidden_order(
            order_type="BUY",
            entry_price=100.0,
            position_size_usd=1000.0,
            stop_loss_pct=0.03
        )

        # Should be identical due to same seed
        assert order1["asset_quantity"] == order2["asset_quantity"]
        assert order1["stop_loss"] == order2["stop_loss"]

    def test_order_variation_without_seed(self):
        """Test that orders vary when no seed is provided."""
        exec1 = SmartExecution()  # No seed
        exec2 = SmartExecution()  # No seed

        orders1 = []
        orders2 = []

        # Generate multiple orders
        for _ in range(5):
            order1 = exec1.place_hidden_order(
                order_type="BUY",
                entry_price=100.0,
                position_size_usd=1000.0,
                stop_loss_pct=0.03
            )
            order2 = exec2.place_hidden_order(
                order_type="BUY",
                entry_price=100.0,
                position_size_usd=1000.0,
                stop_loss_pct=0.03
            )

            orders1.append(order1["asset_quantity"])
            orders2.append(order2["asset_quantity"])

        # Should have some variation (different random seeds)
        assert len(set(orders1)) > 1 or len(set(orders2)) > 1

    def test_limit_order_decision(self):
        """Test limit order vs market order decision based on volatility."""
        # Low volatility should prefer market orders
        assert not self.execution.should_use_limit_order(0.01, 0.02)

        # High volatility should prefer limit orders
        assert self.execution.should_use_limit_order(0.05, 0.02)

        # At threshold should prefer market (uses > not >=)
        assert not self.execution.should_use_limit_order(0.02, 0.02)

        # Just above threshold should prefer limit
        assert self.execution.should_use_limit_order(0.0201, 0.02)

    def test_execution_style_metadata(self):
        """Test that orders include proper execution style metadata."""
        order = self.execution.place_hidden_order(
            order_type="BUY",
            entry_price=100.0,
            position_size_usd=1000.0,
            stop_loss_pct=0.03
        )

        assert order["execution_style"] == "camouflaged"
        assert "Odd-lot sizing" in order["notes"]
        assert "non-round stops" in order["notes"]

    def test_zero_position_size_handling(self):
        """Test handling of zero or very small position sizes."""
        order = self.execution.place_hidden_order(
            order_type="BUY",
            entry_price=100.0,
            position_size_usd=0.0,  # Zero size
            stop_loss_pct=0.03
        )

        # Should still generate an order (though very small)
        assert order["asset_quantity"] >= 0.01  # Minimum size enforced
        assert order["position_size_usd"] >= 0.0
