"""
Integration tests for Varma Trading Agent - End-to-end system testing.
"""

import pytest
import asyncio
import sys
import os
from unittest.mock import patch, MagicMock
import tempfile
import sqlite3

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from trader_agent_v3 import VarmaAgent
from backend.varma_risk_engine import VarmaRiskEngine
from backend.smart_execution import SmartExecution
from backend.position_manager import PositionManager
from database import LifecycleDatabase


class TestVarmaAgentIntegration:
    """Integration tests for complete VarmaAgent functionality."""

    def setup_method(self):
        """Set up test environment with temporary database."""
        # Create temporary database for testing
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp()
        self.original_db_path = None

        # Patch the database path in the lifecycle database
        with patch('backend.position_manager.LifecycleDatabase') as mock_db_class:
            mock_db_instance = MagicMock()
            mock_db_class.return_value = mock_db_instance
            self.mock_db = mock_db_instance

            # Create agent with mocked dependencies
            self.agent = VarmaAgent(
                strategy="trend",
                token_symbol="SOL",
                chain="solana",
                capital=1000.0,
                dry_run=True,
                force_buy=False
            )

    def teardown_method(self):
        """Clean up test environment."""
        if hasattr(self, 'temp_db_fd'):
            os.close(self.temp_db_fd)
            os.unlink(self.temp_db_path)

    @pytest.mark.asyncio
    async def test_full_trading_cycle_trend_strategy(self):
        """Test complete trading cycle with trend strategy."""
        # Mock market data
        mock_market_data = {
            'value': 132.50,
            'timestamp': '2025-01-01T12:00:00Z'
        }

        mock_ohlcv_data = {
            'daily': [
                {'t': 1735689600000, 'o': 130.0, 'h': 135.0, 'l': 125.0, 'c': 132.50, 'v': 1000000},
                {'t': 1735603200000, 'o': 128.0, 'h': 133.0, 'l': 126.0, 'c': 131.00, 'v': 950000},
                {'t': 1735516800000, 'o': 125.0, 'h': 130.0, 'l': 123.0, 'c': 128.50, 'v': 900000},
            ],
            'ltf': []  # Not needed for trend strategy
        }

        # Mock the data fetching
        with patch.object(self.agent, '_fetch_market_data', return_value=(mock_market_data, mock_ohlcv_data)):
            # Mock position recording
            with patch.object(self.agent, '_record_position'):
                # Mock risk validation
                with patch.object(self.agent, '_validate_trade_risk') as mock_validation:
                    mock_validation.return_value = {"approved": True, "warnings": [], "adjustments": {}}

                    # Run trading cycle
                    result = await self.agent.run_cycle()

                    # Verify result structure
                    assert result["status"] == "success"
                    assert "current_price" in result
                    assert "regime" in result
                    assert "signal" in result

                    # Verify regime classification worked
                    assert result["regime"] in ["RISK_ON", "RISK_OFF", "UNKNOWN"]

                    # Verify signal generation (may or may not produce signal)
                    signal = result.get("signal")
                    if signal:
                        assert "action" in signal
                        assert signal["action"] in ["BUY", "SELL", "HOLD", None]

    @pytest.mark.asyncio
    async def test_full_trading_cycle_orb_strategy(self):
        """Test complete trading cycle with ORB strategy."""
        # Create agent with ORB strategy
        agent = VarmaAgent(
            strategy="orb",
            token_symbol="SOL",
            chain="solana",
            capital=1000.0,
            dry_run=True,
            force_buy=False
        )

        # Mock market data
        mock_market_data = {
            'value': 132.50,
            'timestamp': '2025-01-01T12:00:00Z'
        }

        # Mock 5-minute OHLCV data for ORB
        mock_ohlcv_data = {
            'daily': [],  # Not needed for ORB
            'ltf': [
                # Opening range (first 3 candles)
                {'timestamp': '2025-01-01T09:30:00Z', 'open': 130.0, 'high': 131.0, 'low': 129.5, 'close': 130.5, 'volume': 10000},
                {'timestamp': '2025-01-01T09:35:00Z', 'open': 130.5, 'high': 131.5, 'low': 130.0, 'close': 131.0, 'volume': 12000},
                {'timestamp': '2025-01-01T09:40:00Z', 'open': 131.0, 'high': 132.0, 'low': 130.5, 'close': 131.5, 'volume': 11000},
                # Breakout candle
                {'timestamp': '2025-01-01T09:45:00Z', 'open': 131.5, 'high': 134.0, 'low': 131.0, 'close': 133.5, 'volume': 15000},
            ]
        }

        # Mock the data fetching
        with patch.object(agent, '_fetch_market_data', return_value=(mock_market_data, mock_ohlcv_data)):
            # Mock position recording
            with patch.object(agent, '_record_position'):
                # Mock risk validation
                with patch.object(agent, '_validate_trade_risk') as mock_validation:
                    mock_validation.return_value = {"approved": True, "warnings": [], "adjustments": {}}

                    # Run trading cycle
                    result = await agent.run_cycle()

                    # Verify result structure
                    assert result["status"] == "success"
                    assert result["regime"] in ["RISK_ON", "RISK_OFF", "UNKNOWN"]

    @pytest.mark.asyncio
    async def test_forced_buy_integration(self):
        """Test forced buy signal integration."""
        # Create agent with forced buy
        agent = VarmaAgent(
            strategy="trend",
            token_symbol="SOL",
            chain="solana",
            capital=1000.0,
            dry_run=True,
            force_buy=True  # Force buy signal
        )

        # Mock market data
        mock_market_data = {'value': 132.50}
        mock_ohlcv_data = {'daily': [], 'ltf': []}

        with patch.object(agent, '_fetch_market_data', return_value=(mock_market_data, mock_ohlcv_data)):
            with patch.object(agent, '_record_position'):
                with patch.object(agent, '_validate_trade_risk') as mock_validation:
                    mock_validation.return_value = {"approved": True, "warnings": [], "adjustments": {}}

                    result = await agent.run_cycle()

                    # Verify forced buy signal was generated
                    signal = result.get("signal")
                    assert signal is not None
                    assert signal["action"] == "BUY"
                    assert signal["entry_price"] == 132.50
                    assert signal["strategy"] == "forced_test"

    def test_risk_engine_position_sizing_integration(self):
        """Test risk engine integration with position sizing."""
        # Create risk engine
        risk_engine = VarmaRiskEngine()

        # Test position sizing calculation
        result = risk_engine.calculate_position_size(
            capital=1000.0,
            win_rate=0.55,
            avg_win=0.08,
            avg_loss=0.04,
            stop_loss_pct=0.03,
            is_risk_on=True,
            method="kelly"
        )

        # Verify result structure
        assert "position_size_usd" in result
        assert "position_fraction" in result
        assert "method" in result
        assert "regime" in result

        # Verify reasonable bounds
        assert result["position_size_usd"] > 0
        assert 0.05 <= result["position_fraction"] <= 0.25  # Within configured bounds

    def test_smart_execution_integration(self):
        """Test smart execution order generation."""
        execution = SmartExecution(seed=42)

        # Generate camouflaged order
        order = execution.place_hidden_order(
            order_type="BUY",
            entry_price=100.0,
            position_size_usd=1000.0,
            stop_loss_pct=0.03
        )

        # Verify order structure
        assert order["order_type"] == "BUY"
        assert order["entry_price"] == 100.0
        assert order["asset_quantity"] > 0
        assert order["position_size_usd"] > 0
        assert order["stop_loss"] < 100.0  # Stop below entry for buy
        assert order["execution_style"] == "camouflaged"

        # Verify camouflaged properties
        assert order["asset_quantity"] != 10.0  # Not round number
        stop_decimals = str(order["stop_loss"]).split('.')[-1]
        assert len(stop_decimals) >= 3  # Non-round decimals

    def test_position_manager_database_integration(self):
        """Test position manager database operations."""
        # Create temporary database for testing
        db_fd, db_path = tempfile.mkstemp()

        try:
            # Create database and add a test trade
            db = LifecycleDatabase(db_path)
            trade_id = db.add_trade(
                symbol="SOL",
                entry_price=130.0,
                stop_loss=126.0,
                take_profit=0.0,
                strategy_output={"strategy": "test"},
                risk_assessment={"test": True}
            )

            # Create position manager with the test database
            position_manager = PositionManager(db_path)

            # Test loading positions
            positions = position_manager.get_all_positions()
            assert len(positions) == 1
            assert positions[0].symbol == "SOL"
            assert positions[0].entry_price == 130.0
            assert positions[0].stop_loss == 126.0

        finally:
            os.close(db_fd)
            os.unlink(db_path)

    def test_trailing_stop_integration(self):
        """Test trailing stop functionality integration."""
        # Create agent with trailing stops enabled
        agent = VarmaAgent(
            strategy="trend",
            token_symbol="SOL",
            chain="solana",
            capital=1000.0,
            dry_run=True,
            trailing_stop_enabled=True,
            trailing_stop_distance=2.0
        )

        # Verify trailing stop parameters are set
        assert agent.trailing_stop_enabled == True
        assert agent.trailing_stop_distance == 2.0

        # Verify position monitor has trailing stop configured
        assert agent.position_monitor.trailing_stop == True
        assert agent.position_monitor.trailing_distance == 0.02  # Converted to decimal

    @pytest.mark.asyncio
    async def test_error_handling_integration(self):
        """Test error handling in integration scenarios."""
        # Test with invalid market data
        with patch.object(self.agent, '_fetch_market_data', return_value=(None, None)):
            result = await self.agent.run_cycle()

            # Should handle gracefully
            assert result["status"] == "error"
            assert "message" in result

    def test_regime_classification_integration(self):
        """Test regime classification with real price data."""
        from backend.regime_classifier import RegimeClassifier

        # Create regime classifier
        classifier = RegimeClassifier()

        # Test with sufficient trending up data (need at least 200 days for full classification)
        import pandas as pd
        # Create 200+ data points trending up
        base_price = 100.0
        trending_prices = pd.Series([base_price + i * 0.1 for i in range(200)])
        current_price = base_price + 200 * 0.1  # Above trend

        regime_summary = classifier.get_regime_summary(current_price, trending_prices)

        # Should classify as RISK_ON (above trend) - check the enum value
        assert regime_summary["regime"].value == "RISK_ON"
        assert "distance_from_trend_pct" in regime_summary

    def test_database_operations_integration(self):
        """Test database operations work correctly."""
        # Create temporary database
        db_fd, db_path = tempfile.mkstemp()

        try:
            # Create database instance
            db = LifecycleDatabase(db_path)

            # Test trade insertion
            trade_id = db.add_trade(
                symbol="SOL",
                entry_price=130.0,
                stop_loss=126.0,
                take_profit=0.0,
                strategy_output={"strategy": "trend"},
                risk_assessment={"risk_level": "medium"}
            )

            assert trade_id is not None
            assert trade_id > 0

            # Test trade retrieval
            open_positions = db.get_open_positions()
            assert len(open_positions) == 1
            assert open_positions[0]["symbol"] == "SOL"

            # Test trade closure
            db.close_trade(trade_id, exit_price=135.0, exit_reason="TAKE_PROFIT")

            # Verify closed
            open_positions = db.get_open_positions()
            assert len(open_positions) == 0

            closed_trades = db.get_positions_by_status("CLOSED")
            assert len(closed_trades) == 1
            assert closed_trades[0]["exit_price"] == 135.0

        finally:
            os.close(db_fd)
            os.unlink(db_path)

    def test_component_initialization_integration(self):
        """Test that all components initialize correctly."""
        agent = self.agent

        # Verify all components exist
        assert hasattr(agent, 'data_fetcher')
        assert hasattr(agent, 'risk_engine')
        assert hasattr(agent, 'regime_classifier')
        assert hasattr(agent, 'strategy_engine')
        assert hasattr(agent, 'execution_engine')
        assert hasattr(agent, 'position_monitor')

        # Verify component types
        assert isinstance(agent.risk_engine, VarmaRiskEngine)
        assert isinstance(agent.execution_engine, SmartExecution)

        # Verify configuration
        assert agent.strategy == "trend"
        assert agent.token_symbol == "SOL"
        assert agent.capital == 1000.0
        assert agent.dry_run == True

    def test_performance_metrics_integration(self):
        """Test performance metrics calculation from trade history."""
        # Mock closed trades
        closed_trades = [
            {"entry_price": 100.0, "exit_price": 105.0},  # 5% win
            {"entry_price": 100.0, "exit_price": 98.0},   # 2% loss
            {"entry_price": 100.0, "exit_price": 102.0},  # 2% win
            {"entry_price": 100.0, "exit_price": 97.0},   # 3% loss
        ]

        # Test performance calculation
        metrics = self.agent._get_performance_metrics()

        # Should have calculated metrics
        assert "win_rate" in metrics
        assert "avg_win_pct" in metrics
        assert "avg_loss_pct" in metrics
        assert "total_trades" in metrics

        # Verify reasonable values
        assert 0 <= metrics["win_rate"] <= 1
        assert metrics["total_trades"] >= 0

    def test_risk_validation_integration(self):
        """Test risk validation integration."""
        # Test valid trade
        validation = self.agent._validate_trade_risk(
            signal={
                "position_size": 50.0,
                "entry_price": 100.0,
                "stop_loss": 97.0
            },
            regime="RISK_OFF"
        )

        assert "approved" in validation
        assert "warnings" in validation
        assert "risk_metrics" in validation

        # Valid trade should be approved
        assert validation["approved"] == True
