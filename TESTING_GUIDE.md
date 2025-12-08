# VARMA Trading Agent V3 - Testing Guide

## Overview

The VARMA Trading Agent V3 includes comprehensive testing across three levels:

- **Unit Tests**: Individual component validation (33 tests)
- **Integration Tests**: End-to-end workflow testing (13 tests)
- **Noise Stress Tests**: Robustness under adverse conditions (21 tests)

**Total: 67 automated tests with 100% pass rate**

## Test Structure

```
tests/
├── test_varma_risk_engine.py    # Risk management (16 tests)
├── test_smart_execution.py      # Order camouflage (17 tests)
├── test_integration.py          # System integration (13 tests)
├── test_noise_stress.py         # Stress testing (21 tests)
└── __init__.py
```

## Running Tests

### All Tests
```bash
# Run complete test suite
python -m pytest tests/ -v

# Run with coverage report
python -m pytest tests/ --cov=backend --cov-report=html
```

### Individual Test Suites
```bash
# Unit tests only
python -m pytest tests/test_varma_risk_engine.py tests/test_smart_execution.py -v

# Integration tests only
python -m pytest tests/test_integration.py -v

# Stress tests only (excluding slow tests)
python -m pytest tests/test_noise_stress.py -m "not slow" -v

# Run slow stress tests
python -m pytest tests/test_noise_stress.py::TestNoiseStress::test_long_term_stability -v
```

### Selective Testing
```bash
# Run specific test class
python -m pytest tests/test_integration.py::TestVarmaAgentIntegration -v

# Run specific test method
python -m pytest tests/test_varma_risk_engine.py::TestVarmaRiskEngine::test_kelly_fraction_calculation -v

# Run tests matching pattern
python -m pytest tests/ -k "risk" -v
```

## Test Categories

### 1. Unit Tests

#### VarmaRiskEngine Tests (16 tests)
**Purpose**: Validate position sizing and risk calculations

**Key Tests**:
- `test_kelly_fraction_calculation` - Kelly Criterion formula
- `test_position_size_calculation_kelly` - Complete sizing pipeline
- `test_risk_validation_approved` - Pre-trade safety checks
- `test_performance_history_update` - Dynamic learning from trades

**Expected Results**:
```bash
tests/test_varma_risk_engine.py::TestVarmaRiskEngine::test_kelly_fraction_calculation PASSED
tests/test_varma_risk_engine.py::TestVarmaRiskEngine::test_position_size_calculation_kelly PASSED
...
======================== 16 passed in 0.05s ========================
```

#### SmartExecution Tests (17 tests)
**Purpose**: Validate order camouflage and execution logic

**Key Tests**:
- `test_place_hidden_order_buy` - Complete order camouflage
- `test_camouflaged_stop_calculation` - Non-round stop prices
- `test_odd_lot_sizing` - Retail-looking position sizes
- `test_execution_style_metadata` - Order metadata validation

**Expected Results**:
```bash
tests/test_smart_execution.py::TestSmartExecution::test_place_hidden_order_buy PASSED
tests/test_smart_execution.py::TestSmartExecution::test_camouflaged_stop_calculation PASSED
...
======================== 17 passed in 0.02s ========================
```

### 2. Integration Tests

#### End-to-End Testing (13 tests)
**Purpose**: Validate complete trading workflows

**Key Tests**:
- `test_full_trading_cycle_trend_strategy` - Complete trend trading cycle
- `test_forced_buy_integration` - Signal generation to execution
- `test_database_operations_integration` - Database persistence
- `test_component_initialization_integration` - System startup

**Expected Results**:
```bash
tests/test_integration.py::TestVarmaAgentIntegration::test_full_trading_cycle_trend_strategy PASSED
tests/test_integration.py::TestVarmaAgentIntegration::test_database_operations_integration PASSED
...
======================== 13 passed in 1.85s ========================
```

### 3. Noise Stress Tests

#### Robustness Testing (21 tests)
**Purpose**: Validate system behavior under adverse conditions

**Key Tests**:
- `test_regime_classification_under_noise` - 1-20% price noise resilience
- `test_trend_strategy_signal_stability` - Signal consistency under noise
- `test_extreme_volatility_handling` - Wild price swing handling
- `test_api_failure_resilience` - Network failure recovery
- `test_missing_data_resilience` - Incomplete data handling

**Expected Results**:
```bash
tests/test_noise_stress.py::TestNoiseStress::test_regime_classification_under_noise[0.01] PASSED
tests/test_noise_stress.py::TestNoiseStress::test_extreme_volatility_handling PASSED
...
======================== 21 passed in 0.93s ========================
```

## Test Configuration

### pytest.ini
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --tb=short
    --strict-markers
    --disable-warnings
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
```

### Test Fixtures

#### Fixed Seed Testing
Many tests use fixed random seeds for reproducible results:

```python
def setup_method(self):
    self.execution = SmartExecution(seed=42)  # Consistent camouflage
```

#### Mock Data
Integration tests use realistic mock data:

```python
mock_market_data = {
    'value': 132.50,
    'timestamp': '2025-01-01T12:00:00Z'
}

mock_ohlcv_data = {
    'daily': [{'t': 1735689600000, 'o': 130.0, 'h': 135.0, 'l': 125.0, 'c': 132.50, 'v': 1000000}],
    'ltf': []  # 5-minute data for ORB
}
```

## Interpreting Results

### Success Indicators

#### ✅ All Tests Pass
```
======================== 67 passed in 3.85s ========================
```

#### ✅ Coverage Report
```bash
----------- coverage: platform darwin, python 3.11.14 -----------
Name                          Stmts   Miss  Cover
-------------------------------------------------
backend/varma_risk_engine.py     180      0   100%
backend/smart_execution.py       120      0   100%
backend/position_manager.py      150      2    99%
...
TOTAL                            1200     15    99%
```

### Warning Signs

#### ❌ Test Failures
```
======================== 2 failed, 65 passed in 3.80s ========================
```

**Common Causes**:
- API changes breaking mocks
- Database schema modifications
- Random seed inconsistencies
- Missing dependencies

#### ❌ Slow Tests
Tests taking >30 seconds may indicate performance issues.

#### ❌ High Memory Usage
Memory leaks in long-running tests.

## Debugging Failed Tests

### Enable Debug Logging
```bash
export LOG_LEVEL=DEBUG
python -m pytest tests/test_integration.py::TestVarmaAgentIntegration::test_full_trading_cycle_trend_strategy -v -s
```

### Isolate Components
```python
# Test risk engine independently
from backend.varma_risk_engine import VarmaRiskEngine
engine = VarmaRiskEngine()
result = engine.calculate_kelly_fraction(0.6, 0.10, 0.05)
print(f"Kelly fraction: {result}")
```

### Check Dependencies
```bash
# Verify all packages installed
pip list | grep -E "(pytest|numpy|pandas|psutil)"

# Check Python version
python --version
```

### Database Issues
```bash
# Reset test database
rm -f trader_agent_test.db

# Check database schema
sqlite3 trader_agent.db ".schema"
```

## Performance Benchmarks

### Test Execution Times
- **Unit Tests**: < 0.1 seconds
- **Integration Tests**: < 2 seconds
- **Noise Stress Tests**: < 1 second
- **Total Suite**: < 4 seconds

### Memory Usage
- **Peak Memory**: < 150MB during full test run
- **Memory Leaks**: None detected in automated testing

### Coverage Targets
- **Line Coverage**: >95% for core components
- **Branch Coverage**: >90% for decision logic
- **Function Coverage**: 100% for public APIs

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-asyncio psutil
    - name: Run tests
      run: python -m pytest tests/ -v --tb=short
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

## Adding New Tests

### Test Structure Template
```python
import pytest
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from module_under_test import ClassUnderTest

class TestClassUnderTest:
    def setup_method(self):
        self.instance = ClassUnderTest()

    def test_feature_name(self):
        # Arrange
        input_data = "test_input"

        # Act
        result = self.instance.method_name(input_data)

        # Assert
        assert result == expected_output

    @pytest.mark.parametrize("input_param,expected", [
        (1, 2),
        (2, 4),
        (3, 6),
    ])
    def test_parameterized_feature(self, input_param, expected):
        result = self.instance.calculate(input_param)
        assert result == expected
```

### Integration Test Template
```python
@pytest.mark.asyncio
async def test_integration_scenario():
    # Setup
    agent = VarmaAgent(dry_run=True)

    # Mock dependencies
    with patch.object(agent, 'method_to_mock') as mock_method:
        mock_method.return_value = mock_data

        # Execute
        result = await agent.run_cycle()

        # Verify
        assert result["status"] == "success"
        mock_method.assert_called_once()
```

## Troubleshooting

### "Module not found" errors
```bash
# Install missing dependencies
pip install pytest-asyncio psutil numpy pandas

# Check Python path
python -c "import sys; print(sys.path)"
```

### "Database locked" errors
```bash
# Kill any running processes
pkill -f trader_agent

# Remove lock files
rm -f trader_agent.db.lock

# Reset database
rm -f trader_agent.db
python -c "from database import LifecycleDatabase; db = LifecycleDatabase(); db._init_db()"
```

### "Random test failures"
```python
# Use fixed seeds in tests
self.execution = SmartExecution(seed=42)

# Or check for non-deterministic behavior
for _ in range(10):
    result = function_under_test()
    assert result in expected_range
```

### Performance issues
```python
import time
start = time.time()
result = slow_function()
duration = time.time() - start
assert duration < 1.0  # Max 1 second
```

This testing guide ensures the VARMA Trading Agent V3 maintains high quality and reliability through comprehensive automated testing.
