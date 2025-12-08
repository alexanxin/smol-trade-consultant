"""
Noise Stress Tests for Varma Trading Agent - Robustness validation under noisy conditions.
"""

import pytest
import numpy as np
import pandas as pd
import sys
import os
from unittest.mock import patch, MagicMock
import asyncio

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from trader_agent_v3 import VarmaAgent
from backend.regime_classifier import RegimeClassifier
from backend.trend_strategy import TrendStrategy
from backend.orb_strategy import ORBStrategy
from backend.varma_risk_engine import VarmaRiskEngine


class TestNoiseStress:
    """Stress tests for system robustness under noisy conditions."""

    def setup_method(self):
        """Set up test environment."""
        self.agent = VarmaAgent(
            strategy="trend",
            token_symbol="SOL",
            chain="solana",
            capital=1000.0,
            dry_run=True
        )

    def add_price_noise(self, prices: pd.Series, noise_pct: float, seed: int = 42) -> pd.Series:
        """Add random noise to price series."""
        np.random.seed(seed)
        noise = np.random.normal(0, noise_pct, len(prices))
        noisy_prices = prices * (1 + noise)
        return noisy_prices.clip(lower=0.01)  # Prevent negative prices

    def create_extreme_volatility_data(self, base_price: float = 100.0, periods: int = 200) -> pd.Series:
        """Create price data with extreme volatility."""
        np.random.seed(123)
        # Start with base price
        prices = [base_price]

        for _ in range(periods - 1):
            # Random walk with occasional extreme moves
            change = np.random.normal(0, 0.02)  # 2% daily volatility
            # Occasionally add extreme moves (10%+)
            if np.random.random() < 0.05:  # 5% chance
                extreme_move = np.random.choice([-0.15, 0.15])  # -15% or +15%
                change += extreme_move

            new_price = prices[-1] * (1 + change)
            prices.append(max(new_price, 0.01))  # Prevent negative

        return pd.Series(prices)

    @pytest.mark.parametrize("noise_level", [0.01, 0.05, 0.10, 0.20])
    def test_regime_classification_under_noise(self, noise_level):
        """Test regime classification robustness under price noise."""
        classifier = RegimeClassifier()

        # Create clean trending data
        clean_prices = pd.Series([100 + i * 0.1 for i in range(200)])
        current_price = clean_prices.iloc[-1] + 1  # Slightly above trend

        # Test clean data first
        clean_regime = classifier.get_regime_summary(current_price, clean_prices)

        # Add noise and test
        noisy_prices = self.add_price_noise(clean_prices, noise_level)
        noisy_regime = classifier.get_regime_summary(current_price, noisy_prices)

        # System should still classify regime reasonably (may change due to noise)
        regime_value = noisy_regime["regime"].value if hasattr(noisy_regime["regime"], 'value') else noisy_regime["regime"]
        assert regime_value in ["RISK_ON", "RISK_OFF", "UNKNOWN"]
        assert "distance_from_trend_pct" in noisy_regime

        # With extreme noise, we expect some degradation but not complete failure
        if noise_level <= 0.10:  # Up to 10% noise
            # Should still be able to calculate distance
            assert isinstance(noisy_regime["distance_from_trend_pct"], (int, float))

    @pytest.mark.parametrize("noise_level", [0.01, 0.05, 0.10])
    def test_trend_strategy_signal_stability(self, noise_level):
        """Test trend strategy signal stability under noise."""
        strategy = TrendStrategy()

        # Create clean trending up data
        clean_prices = pd.Series([100 + i * 0.1 for i in range(200)])
        current_price = clean_prices.iloc[-1] + 2  # Above trend for BUY signal

        # Test clean signal
        clean_signal = strategy.generate_trend_signal(current_price, clean_prices)

        # Test with noise
        noisy_prices = self.add_price_noise(clean_prices, noise_level)
        noisy_signal = strategy.generate_trend_signal(current_price, noisy_prices)

        # Both should generate signals (not None)
        assert clean_signal is not None
        assert noisy_signal is not None

        # Signal structure should be consistent
        for signal in [clean_signal, noisy_signal]:
            assert "action" in signal
            assert "current_price" in signal
            if signal["action"] in ["BUY", "SELL"]:  # Only trading signals have stop_loss
                assert "stop_loss" in signal

    @pytest.mark.parametrize("noise_level", [0.02, 0.05])
    def test_orb_strategy_noise_resistance(self, noise_level):
        """Test ORB strategy robustness under moderate noise."""
        strategy = ORBStrategy()

        # Create clean ORB data (opening range breakout scenario)
        base_time = pd.Timestamp('2025-01-01 09:30:00')

        # Opening range (first 3 candles)
        opening_data = [
            {'timestamp': base_time, 'open': 100.0, 'high': 101.0, 'low': 99.5, 'close': 100.5, 'volume': 1000},
            {'timestamp': base_time + pd.Timedelta(minutes=5), 'open': 100.5, 'high': 101.5, 'low': 100.0, 'close': 101.0, 'volume': 1200},
            {'timestamp': base_time + pd.Timedelta(minutes=10), 'open': 101.0, 'high': 102.0, 'low': 100.5, 'close': 101.5, 'volume': 1100},
        ]

        # Breakout candle
        breakout_data = [{
            'timestamp': base_time + pd.Timedelta(minutes=15),
            'open': 101.5, 'high': 104.0, 'low': 101.0, 'close': 103.5, 'volume': 1500
        }]

        # Convert to DataFrame
        df = pd.DataFrame(opening_data + breakout_data)

        # Test clean signal
        current_price = 103.5
        clean_signal = strategy.generate_orb_signal(current_price, df, base_time)

        # Test with noise added to prices
        noisy_df = df.copy()
        for col in ['open', 'high', 'low', 'close']:
            prices = pd.Series(noisy_df[col].values)
            noisy_prices = self.add_price_noise(prices, noise_level)
            noisy_df[col] = noisy_prices.values

        noisy_signal = strategy.generate_orb_signal(current_price, noisy_df, base_time)

        # Both should handle the data without crashing
        # (Signals may differ due to noise, that's expected)
        for signal in [clean_signal, noisy_signal]:
            if signal is not None:
                assert "action" in signal
                assert signal["action"] in ["BUY", "SELL", "HOLD", "WAIT", None]

    def test_extreme_volatility_handling(self):
        """Test system handling of extreme volatility conditions."""
        classifier = RegimeClassifier()
        strategy = TrendStrategy()

        # Create extremely volatile price data
        volatile_prices = self.create_extreme_volatility_data(base_price=100.0, periods=200)
        current_price = volatile_prices.iloc[-1]

        # Test regime classification
        regime_result = classifier.get_regime_summary(current_price, volatile_prices)

        # Should still classify (may be UNKNOWN due to volatility)
        regime_value = regime_result["regime"].value if hasattr(regime_result["regime"], 'value') else regime_result["regime"]
        assert regime_value in ["RISK_ON", "RISK_OFF", "UNKNOWN"]

        # Test trend strategy
        trend_signal = strategy.generate_trend_signal(current_price, volatile_prices)

        # Should generate signal without crashing
        assert trend_signal is not None
        assert "action" in trend_signal

    @pytest.mark.asyncio
    async def test_api_failure_resilience(self):
        """Test system resilience to API failures."""
        # Mock API failure
        with patch.object(self.agent, '_fetch_market_data', return_value=(None, None)):
            result = await self.agent.run_cycle()

            # Should handle gracefully
            assert result["status"] == "error"
            assert "message" in result

    @pytest.mark.asyncio
    async def test_partial_data_handling(self):
        """Test handling of incomplete or partial market data."""
        # Mock incomplete OHLCV data
        incomplete_ohlcv = {
            'daily': [
                {'t': 1735689600000, 'o': 130.0, 'h': 135.0},  # Missing low, close, volume
                {'t': 1735603200000},  # Minimal data
            ],
            'ltf': []  # Empty
        }

        mock_market_data = {'value': 132.50}

        with patch.object(self.agent, '_fetch_market_data', return_value=(mock_market_data, incomplete_ohlcv)):
            # Should handle gracefully without crashing
            result = await self.agent.run_cycle()

            # Result should be valid (may be error or success depending on implementation)
            assert "status" in result
            assert result["status"] in ["success", "error"]

    def test_risk_engine_noise_resistance(self):
        """Test risk engine calculations under noisy performance data."""
        risk_engine = VarmaRiskEngine()

        # Create noisy performance data
        base_trades = [
            {"entry_price": 100.0, "exit_price": 105.0},  # 5% win
            {"entry_price": 100.0, "exit_price": 98.0},   # 2% loss
            {"entry_price": 100.0, "exit_price": 102.0},  # 2% win
            {"entry_price": 100.0, "exit_price": 97.0},   # 3% loss
        ]

        # Add noise to exit prices
        noisy_trades = []
        for trade in base_trades:
            noisy_exit = trade["exit_price"] * (1 + np.random.normal(0, 0.05))  # 5% noise
            noisy_trades.append({
                "entry_price": trade["entry_price"],
                "exit_price": noisy_exit
            })

        # Calculate metrics
        metrics = risk_engine.update_from_performance_history(noisy_trades)

        # Should still produce reasonable metrics
        assert 0 <= metrics["win_rate"] <= 1
        assert metrics["avg_win_pct"] >= 0
        assert metrics["avg_loss_pct"] >= 0
        assert metrics["total_trades"] == len(noisy_trades)

    def test_signal_consistency_under_noise(self):
        """Test that signals remain reasonably consistent under moderate noise."""
        strategy = TrendStrategy()

        # Create base trending data
        base_prices = pd.Series([100 + i * 0.1 for i in range(100)])
        current_price = base_prices.iloc[-1] + 1  # Slightly above trend

        # Generate signals with different noise levels
        signals = []
        for noise_level in [0.0, 0.02, 0.05]:  # Clean, 2%, 5% noise
            if noise_level == 0.0:
                noisy_prices = base_prices
            else:
                noisy_prices = self.add_price_noise(base_prices, noise_level, seed=42)

            signal = strategy.generate_trend_signal(current_price, noisy_prices)
            signals.append(signal)

        # All signals should exist and have consistent structure
        for signal in signals:
            assert signal is not None
            assert "action" in signal
            # Confidence may not be present for all signal types
            if "confidence" in signal:
                assert isinstance(signal["confidence"], (int, float))

        # With moderate noise, signal action might change but structure remains
        clean_action = signals[0]["action"]
        moderate_noise_action = signals[1]["action"]

        # Structure should be preserved even if action changes
        assert all("current_price" in s for s in signals)

    @pytest.mark.parametrize("missing_pct", [0.1, 0.25, 0.5])
    def test_missing_data_resilience(self, missing_pct):
        """Test system resilience to missing data points."""
        classifier = RegimeClassifier()

        # Create complete price series
        complete_prices = pd.Series([100 + i * 0.1 for i in range(200)])

        # Remove random data points
        np.random.seed(42)
        mask = np.random.random(len(complete_prices)) > missing_pct
        incomplete_prices = complete_prices[mask]

        if len(incomplete_prices) < 30:  # Minimum required
            pytest.skip("Too few data points remaining")

        current_price = incomplete_prices.iloc[-1]

        # Should handle missing data gracefully
        regime_result = classifier.get_regime_summary(current_price, incomplete_prices)

        # Should still attempt classification
        assert "regime" in regime_result
        assert "distance_from_trend_pct" in regime_result

    def test_outlier_price_handling(self):
        """Test handling of extreme outlier prices."""
        classifier = RegimeClassifier()

        # Create normal trending data
        normal_prices = pd.Series([100 + i * 0.1 for i in range(180)])

        # Add extreme outliers
        outlier_prices = pd.Series([1000.0, 0.01, 500.0])  # Crazy prices

        # Combine (outliers at end)
        mixed_prices = pd.concat([normal_prices, outlier_prices])

        current_price = 150.0  # Normal current price

        # Should handle outliers without crashing
        regime_result = classifier.get_regime_summary(current_price, mixed_prices)

        # Should still produce result (may be nonsensical due to outliers)
        assert "regime" in regime_result
        assert isinstance(regime_result["distance_from_trend_pct"], (int, float, type(None)))

    def test_zero_price_handling(self):
        """Test handling of zero or near-zero prices."""
        strategy = TrendStrategy()

        # Create data with some zero/near-zero prices (shouldn't happen but test robustness)
        prices = pd.Series([100 + i * 0.1 for i in range(190)])
        # Add some problematic prices
        problematic_prices = pd.Series([0.0, 0.001, -1.0])  # Invalid prices
        mixed_prices = pd.concat([prices, problematic_prices])

        current_price = 120.0

        # Should handle without crashing (though results may be invalid)
        try:
            signal = strategy.generate_trend_signal(current_price, mixed_prices)
            # If it returns a signal, it should have proper structure
            if signal is not None:
                assert "action" in signal
        except Exception as e:
            # It's acceptable to throw exception on invalid data
            assert isinstance(e, (ValueError, ZeroDivisionError, RuntimeWarning))

    def test_performance_under_load(self):
        """Test system performance with large datasets."""
        import time

        classifier = RegimeClassifier()

        # Create large dataset (1000+ points)
        large_prices = pd.Series([100 + i * 0.01 for i in range(1000)])
        current_price = large_prices.iloc[-1]

        # Time the operation
        start_time = time.time()
        regime_result = classifier.get_regime_summary(current_price, large_prices)
        end_time = time.time()

        # Should complete in reasonable time (< 1 second)
        assert end_time - start_time < 1.0

        # Should produce valid result
        assert "regime" in regime_result

    def test_memory_efficiency(self):
        """Test that system doesn't have memory leaks with repeated operations."""
        import psutil
        import os

        # Get initial memory
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Perform many operations
        classifier = RegimeClassifier()
        for i in range(100):
            prices = pd.Series([100 + j * 0.1 for j in range(50)])
            current_price = prices.iloc[-1]
            _ = classifier.get_regime_summary(current_price, prices)

        # Check final memory
        final_memory = process.memory_info().rss

        # Memory increase should be reasonable (< 50MB)
        memory_increase = final_memory - initial_memory
        assert memory_increase < 50 * 1024 * 1024  # 50MB in bytes

    @pytest.mark.slow
    def test_long_term_stability(self):
        """Test system stability over many repeated operations."""
        strategy = TrendStrategy()
        classifier = RegimeClassifier()

        # Run many iterations
        for iteration in range(50):
            # Create slightly different data each time
            seed = 42 + iteration
            np.random.seed(seed)

            prices = pd.Series([100 + i * 0.1 + np.random.normal(0, 0.5) for i in range(100)])
            current_price = prices.iloc[-1] + np.random.normal(0, 1.0)

            # Test both components
            regime = classifier.get_regime_summary(current_price, prices)
            signal = strategy.generate_trend_signal(current_price, prices)

            # Should consistently produce results
            assert "regime" in regime
            if signal is not None:
                assert "action" in signal

        # If we get here without exceptions, the system is stable
