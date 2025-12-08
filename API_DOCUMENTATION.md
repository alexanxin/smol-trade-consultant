# VARMA Trading Agent V3 - API Documentation

## Table of Contents
- [Core Classes](#core-classes)
- [Trading Strategies](#trading-strategies)
- [Risk Management](#risk-management)
- [Execution Engine](#execution-engine)
- [Database Schema](#database-schema)
- [Configuration](#configuration)
- [Extension Guide](#extension-guide)

## Core Classes

### VarmaAgent

**Main trading agent orchestrating all components.**

```python
class VarmaAgent:
    def __init__(
        self,
        strategy: str = "trend",
        token_symbol: str = "SOL",
        chain: str = "solana",
        capital: float = 1000.0,
        dry_run: bool = True,
        force_buy: bool = False,
        trailing_stop_enabled: bool = False,
        trailing_stop_distance: float = 2.0
    )
```

#### Key Methods:
- `run_cycle()` - Execute one complete trading cycle
- `_fetch_market_data()` - Get price and OHLCV data
- `_classify_regime()` - Determine RISK_ON/OFF regime
- `_generate_signal()` - Create trading signals
- `_calculate_position_size()` - Apply Kelly + regime sizing
- `_validate_trade_risk()` - Pre-trade safety checks
- `_execute_trade()` - Execute camouflaged orders
- `_record_position()` - Store positions in database

#### Example Usage:
```python
agent = VarmaAgent(strategy="trend", capital=5000.0, dry_run=True)
result = await agent.run_cycle()
```

### VarmaRiskEngine

**Implements Kelly Criterion and risk management.**

```python
class VarmaRiskEngine:
    def __init__(
        self,
        kelly_dampener: float = 0.25,
        max_drawdown_target: float = 0.45,
        risk_on_multiplier: float = 1.5,
        risk_off_multiplier: float = 0.5,
        min_position_size: float = 0.05,
        max_position_size: float = 0.25
    )
```

#### Key Methods:
- `calculate_kelly_fraction(win_rate, avg_win, avg_loss)` - Kelly formula
- `calculate_position_from_drawdown(stop_pct, capital)` - Drawdown-based sizing
- `adjust_for_regime(base_size, is_risk_on)` - Regime multipliers
- `calculate_position_size(...)` - Complete position sizing pipeline
- `validate_trade_risk(...)` - Pre-trade risk validation
- `update_from_performance_history(trades)` - Dynamic Kelly updates

#### Example Usage:
```python
engine = VarmaRiskEngine()
size_result = engine.calculate_position_size(
    capital=10000.0,
    win_rate=0.55,
    avg_win=0.08,
    avg_loss=0.04,
    stop_loss_pct=0.03,
    is_risk_on=True
)
print(f"Position size: ${size_result['position_size_usd']:.2f}")
```

### SmartExecution

**Handles order camouflage and execution.**

```python
class SmartExecution:
    def __init__(self, seed: Optional[int] = None)
```

#### Key Methods:
- `generate_odd_lot_size(target_usd, price)` - Create retail-looking sizes
- `calculate_camouflaged_stop(entry_price, stop_pct, direction)` - Non-round stops
- `generate_prime_like_number(target)` - Weird number generation
- `place_hidden_order(...)` - Complete camouflaged order creation

#### Example Usage:
```python
execution = SmartExecution(seed=42)
order = execution.place_hidden_order(
    order_type="BUY",
    entry_price=100.0,
    position_size_usd=1000.0,
    stop_loss_pct=0.03
)
print(f"Camouflaged quantity: {order['asset_quantity']}")
print(f"Hidden stop: ${order['stop_loss']}")
```

## Trading Strategies

### TrendStrategy

**Implements Varma's trend-following methodology.**

```python
class TrendStrategy:
    def __init__(self, trend_period: int = 200, entry_threshold: float = 2.0)
```

#### Key Methods:
- `generate_trend_signal(current_price, prices)` - Main signal generation

#### Signal Structure:
```python
{
    "action": "BUY",  # or "SELL" or "HOLD"
    "entry_price": 132.50,
    "stop_loss": 128.27,
    "take_profit": 0,  # Trend strategy doesn't use profit targets
    "confidence": 80,
    "strategy": "trend",
    "regime": "RISK_ON",
    "trend_line": 130.25,
    "distance_from_trend_pct": 1.73,
    "position_multiplier": 1.5
}
```

### ORBStrategy

**Opening Range Breakout strategy for intraday moves.**

```python
class ORBStrategy:
    def __init__(self, range_minutes: int = 15)
```

#### Key Methods:
- `generate_orb_signal(current_price, ohlcv_data, market_open_time)`

#### Signal Structure:
```python
{
    "action": "BUY",
    "entry_price": 132.50,
    "stop_loss": 128.27,
    "take_profit": 0,
    "confidence": 75,
    "strategy": "orb",
    "regime": "RISK_ON",
    "opening_range_high": 131.50,
    "opening_range_low": 129.50,
    "breakout_direction": "up"
}
```

## Risk Management

### Kelly Criterion Implementation

The system uses fractional Kelly with regime adjustments:

```python
# Raw Kelly formula
kelly = win_rate - ((1 - win_rate) / risk_reward_ratio)

# Apply fractional dampener (0.25x)
fractional_kelly = max(0.0, kelly) * 0.25

# Apply regime multiplier
if is_risk_on:
    final_fraction = fractional_kelly * 1.5
else:
    final_fraction = fractional_kelly * 0.5

# Convert to dollar amount
position_size_usd = capital * final_fraction
```

### Risk Validation Checks

Pre-trade validation includes:

1. **Position Size Bounds**: Min 5%, Max 25% of capital
2. **Stop Loss Range**: 0.5% to 10% from entry
3. **Portfolio Exposure**: Max 2x leverage across positions
4. **Drawdown Limits**: Prevent >45% potential drawdown
5. **Regime Appropriateness**: Size matches risk regime

### Performance History Updates

The system learns from trade history:

```python
# Analyze closed trades
wins = [trade for trade in closed_trades if trade['exit_price'] > trade['entry_price']]
losses = [trade for trade in closed_trades if trade['exit_price'] <= trade['entry_price']]

win_rate = len(wins) / len(closed_trades)
avg_win_pct = sum((w['exit_price']-w['entry_price'])/w['entry_price'] for w in wins) / len(wins)
avg_loss_pct = abs(sum((l['exit_price']-l['entry_price'])/l['entry_price'] for l in losses) / len(losses))

# Update Kelly calculations with real performance
risk_engine.update_from_performance_history(closed_trades)
```

## Execution Engine

### JupiterClient

**Handles Solana DEX interactions.**

```python
class JupiterClient:
    def __init__(self, wallet=None)
```

#### Key Methods:
- `get_quote(input_mint, output_mint, amount, slippage_bps)` - Price quotes
- `execute_swap(input_mint, output_mint, amount, slippage_bps)` - Execute trades

#### Token Addresses:
```python
SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
```

### PositionManager

**Manages active trading positions.**

```python
class PositionManager:
    def __init__(self, db_path: str = "trader_agent.db")
```

#### Key Methods:
- `add_position(trade_data, execution_result, token, token_address)`
- `get_all_positions()` - Active positions list
- `update_position_price(trade_id, current_price, unrealized_pnl)`
- `check_exit_conditions(position)` - Stop loss checks
- `close_position(trade_id, exit_price, exit_reason)`

### PositionMonitor

**Real-time position monitoring and automated exits.**

```python
class PositionMonitor:
    def __init__(
        self,
        execution_mode: str = "spot",
        dry_run: bool = True,
        token: str = "SOL",
        trailing_stop: bool = False,
        trailing_distance: float = 2.0
    )
```

#### Key Methods:
- `start()` - Begin monitoring loop
- `stop()` - End monitoring
- `check_position(position)` - Evaluate single position
- `execute_exit(position, exit_price, exit_reason)` - Close positions

## Database Schema

### Trades Table
```sql
CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    entry_price REAL,
    stop_loss REAL,
    take_profit REAL,
    status TEXT NOT NULL, -- 'OPEN', 'CLOSED'
    timestamp TEXT NOT NULL,
    strategy_output TEXT, -- JSON string
    risk_assessment TEXT, -- JSON string
    exit_price REAL,
    exit_reason TEXT,
    exit_timestamp TEXT,
    -- Position tracking fields
    token_address TEXT,
    entry_amount REAL,
    current_price REAL,
    unrealized_pnl REAL,
    last_check_timestamp TEXT,
    trailing_stop_price REAL,
    execution_mode TEXT -- 'spot' or 'leverage'
)
```

### Signals Table
```sql
CREATE TABLE signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    symbol TEXT NOT NULL,
    action TEXT,
    entry_price REAL,
    stop_loss REAL,
    take_profit REAL,
    confidence REAL,
    reasoning TEXT,
    strategy_output TEXT, -- JSON string
    risk_assessment TEXT, -- JSON string
    status TEXT -- 'PENDING', 'EXECUTED', 'REJECTED', 'SKIPPED'
)
```

### Portfolio Snapshots Table
```sql
CREATE TABLE portfolio_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    total_equity REAL,
    cash_balance REAL,
    unrealized_pnl REAL,
    open_positions_count INTEGER,
    risk_exposure REAL
)
```

## Configuration

### Environment Variables
```bash
# Required
SOLANA_PRIVATE_KEY=your_private_key_here

# Optional
RPC_URL=https://mainnet.helius-rpc.com/?api-key=your_key
LOG_LEVEL=INFO
DATABASE_PATH=trader_agent.db
```

### Strategy Configuration
Located in `backend/config.py`:

```python
VARMA_CONFIG = {
    'VARMA_KELLY_DAMPENER': 0.25,
    'VARMA_MAX_DRAWDOWN': 0.45,
    'VARMA_TREND_PERIOD': 200,
    'VARMA_ORB_RANGE_MINUTES': 15,
    'VARMA_RISK_ON_MULTIPLIER': 1.5,
    'VARMA_RISK_OFF_MULTIPLIER': 0.5,
    'VARMA_MIN_POSITION_SIZE': 0.05,
    'VARMA_MAX_POSITION_SIZE': 0.25
}
```

## Extension Guide

### Adding a New Strategy

1. **Create Strategy Class**:
```python
from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    @abstractmethod
    def generate_signal(self, market_data, ohlcv_data, regime):
        pass

class NewStrategy(BaseStrategy):
    def generate_signal(self, market_data, ohlcv_data, regime):
        # Implement your strategy logic
        return {
            "action": "BUY",
            "entry_price": market_data['value'],
            "stop_loss": market_data['value'] * 0.97,
            "take_profit": 0,
            "confidence": 75,
            "strategy": "new_strategy"
        }
```

2. **Register in VarmaAgent**:
```python
# In VarmaAgent.__init__
elif self.strategy == "new":
    self.strategy_engine = NewStrategy()
```

3. **Add CLI Support**:
```python
# In argument parser
parser.add_argument('--strategy', choices=['trend', 'orb', 'new'], default='trend')
```

### Adding Risk Metrics

1. **Extend RiskEngine**:
```python
def calculate_new_metric(self, trades):
    # Implement new risk calculation
    return custom_risk_score
```

2. **Update Validation**:
```python
def validate_trade_risk(self, ...):
    # Add new validation checks
    if not self.check_new_metric(...):
        validation_result["warnings"].append("New metric violation")
```

### Custom Execution Methods

1. **Extend SmartExecution**:
```python
def custom_execution_style(self, order_params):
    # Implement custom camouflage
    return modified_order
```

2. **Add to JupiterClient**:
```python
def execute_custom_swap(self, custom_params):
    # Custom execution logic
    return result
```

### Database Extensions

1. **Add Migration**:
```python
# In database.py _init_db
cursor.execute('''
    ALTER TABLE trades ADD COLUMN custom_field REAL
''')
```

2. **Update Models**:
```python
@dataclass
class Position:
    custom_field: Optional[float] = None
```

### Testing Extensions

1. **Add Test Cases**:
```python
def test_new_strategy():
    strategy = NewStrategy()
    signal = strategy.generate_signal(market_data, ohlcv_data, regime)
    assert signal["action"] in ["BUY", "SELL", "HOLD"]
```

2. **Integration Tests**:
```python
@pytest.mark.asyncio
async def test_new_strategy_integration():
    agent = VarmaAgent(strategy="new", dry_run=True)
    result = await agent.run_cycle()
    assert result["status"] == "success"
```

This API documentation provides the foundation for extending and customizing the VARMA Trading Agent V3 system.
