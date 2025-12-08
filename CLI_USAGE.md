# VARMA Trading Agent V3 - Command Line Usage Guide

## Table of Contents
- [Quick Start](#quick-start)
- [Command Line Options](#command-line-options)
- [Usage Examples](#usage-examples)
- [Strategy Selection](#strategy-selection)
- [Risk Management](#risk-management)
- [Output Interpretation](#output-interpretation)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

## Quick Start

### Prerequisites
- Python 3.11+
- Solana wallet with SOL
- Environment configured (see README.md)

### Basic Commands

```bash
# Show help
python trader_agent_v3.py --help

# Safe testing (recommended first!)
python trader_agent_v3.py --dry-run

# Test execution pipeline
python trader_agent_v3.py --dry-run --force-buy

# Live trading (use with caution!)
python trader_agent_v3.py --strategy trend
```

## Command Line Options

```
usage: trader_agent_v3.py [-h] [--strategy {trend,orb}] [--token TOKEN]
                         [--chain CHAIN] [--capital CAPITAL]
                         [--dry-run] [--force-buy]
                         [--trailing-stop] [--trailing-distance DISTANCE]

VARMA Trading Agent V3

options:
  -h, --help            show this help message and exit
  --strategy {trend,orb}
                        Trading strategy (default: trend)
                        - trend: Trend following based on 183-day MA
                        - orb: Opening Range Breakout (15-minute ranges)
  --token TOKEN         Token symbol to trade (default: SOL)
                        - SOL: Solana
                        - Other tokens supported via Jupiter
  --chain CHAIN         Blockchain network (default: solana)
  --capital CAPITAL     Total capital available in USD (default: 1000)
                        - Determines position sizes via Kelly Criterion
  --dry-run             Run in simulation mode (no real trades)
                        - Essential for testing and validation
                        - Shows camouflaged order details
  --force-buy           Force a BUY signal for testing execution
                        - Overrides strategy logic
                        - Useful for testing trade pipeline
  --trailing-stop       Enable trailing stop-loss for positions
                        - Locks in profits as price moves favorably
                        - Default distance: 2.0%
  --trailing-distance DISTANCE
                        Trailing stop distance as percentage (default: 2.0)
                        - Range: 0.5% to 10%
                        - Lower = tighter stops, higher = looser stops
```

## Usage Examples

### Testing & Development

#### Safe Testing
```bash
# Basic dry-run with defaults
python trader_agent_v3.py --dry-run

# Test both strategies
python trader_agent_v3.py --dry-run --strategy trend
python trader_agent_v3.py --dry-run --strategy orb

# Force execution to test pipeline
python trader_agent_v3.py --dry-run --force-buy

# Test with different capital amounts
python trader_agent_v3.py --dry-run --capital 100   # Small test
python trader_agent_v3.py --dry-run --capital 10000 # Larger position
```

#### Strategy Comparison
```bash
# Compare strategies with same conditions
python trader_agent_v3.py --dry-run --strategy trend --capital 1000
python trader_agent_v3.py --dry-run --strategy orb --capital 1000
```

### Live Trading

#### Conservative Deployment
```bash
# Start with small amounts and monitoring
python trader_agent_v3.py --capital 100 --strategy trend --dry-run

# If testing successful, go live small
python trader_agent_v3.py --capital 500 --strategy trend

# Add trailing stops for risk management
python trader_agent_v3.py --capital 1000 --strategy trend --trailing-stop
```

#### Advanced Configurations
```bash
# Trend following with custom trailing distance
python trader_agent_v3.py --strategy trend --trailing-stop --trailing-distance 1.5

# ORB strategy with larger capital
python trader_agent_v3.py --strategy orb --capital 5000

# Different token (if supported)
python trader_agent_v3.py --token SOL --capital 2000 --strategy trend
```

### Parameter Combinations

#### Risk Management Focused
```bash
# Conservative: small capital, tight stops
python trader_agent_v3.py --dry-run --capital 500 --trailing-stop --trailing-distance 1.0

# Balanced: medium capital, standard stops
python trader_agent_v3.py --dry-run --capital 2000 --trailing-stop --trailing-distance 2.0

# Aggressive: larger capital, wider stops
python trader_agent_v3.py --dry-run --capital 5000 --trailing-stop --trailing-distance 3.0
```

#### Strategy Testing Matrix
```bash
# Test all combinations systematically
python trader_agent_v3.py --dry-run --strategy trend --capital 1000 --force-buy
python trader_agent_v3.py --dry-run --strategy orb --capital 1000 --force-buy
python trader_agent_v3.py --dry-run --strategy trend --capital 1000 --trailing-stop
python trader_agent_v3.py --dry-run --strategy orb --capital 1000 --trailing-stop
```

## Strategy Selection

### Trend Strategy (--strategy trend)
**Best for**: Long-term position trading, trending markets

**Characteristics**:
- Uses 183-day moving average for regime classification
- RISK_ON: 1.5x position size (above trend)
- RISK_OFF: 0.5x position size (below trend)
- No profit targets (let winners run)
- Stop loss only exits

**When to use**:
- Bull markets with clear trends
- Long-term investment horizon
- Prefer holding through volatility

**Example output**:
```
Risk Regime: RISK_ON
Signal: BUY
Position Size: $150.00 (1.5x multiplier)
```

### ORB Strategy (--strategy orb)
**Best for**: Intraday breakout trading, ranging markets

**Characteristics**:
- 15-minute opening range detection
- Breaks above/below range trigger signals
- Intraday holding period
- Volume confirmation preferred

**When to use**:
- Volatile sessions with clear ranges
- Shorter timeframes
- Breakout-style market conditions

**Example output**:
```
Risk Regime: RISK_OFF
Signal: WAIT (range too small)
```

## Risk Management

### Capital Allocation (--capital)
**Impact**: Directly affects position sizes via Kelly Criterion

**Examples**:
- `--capital 100`: Small test positions (~$5-25)
- `--capital 1000`: Standard positions (~$50-250)
- `--capital 10000`: Large positions (~$500-2500)

**Kelly Formula**: Position = Capital × WinRate - ((1-WinRate)/RiskRatio)) × 0.25

### Trailing Stops (--trailing-stop --trailing-distance)
**Purpose**: Lock in profits while allowing winners to run

**Distance Guidelines**:
- `1.0`: Tight protection, frequent exits
- `2.0`: Balanced (default), moderate protection
- `3.0`: Loose protection, fewer exits

**How it works**:
1. Initial stop placed at entry - distance%
2. As price moves up, stop follows at distance%
3. If price drops to trailing stop, position exits

**Example**:
```
Entry: $100
Trailing Distance: 2%
Initial Stop: $98
Price moves to $110 → Stop moves to $107.80
Price moves to $115 → Stop moves to $112.70
```

## Output Interpretation

### Successful Execution

#### Trend Strategy BUY
```
VARMA AGENT V3 - TRADING CYCLE RESULT
==================================================
Status: success
Current Price: $136.0604
Risk Regime: RISK_OFF
Signal: BUY
Entry Price: $136.0604
Position Size: $50.00
Stop Loss: $131.9786
Take Profit: $0.0000
Confidence: 90%

🛡️ CAMOUFLAGED ORDER DETAILS:
   Asset Quantity: 0.3710 units
   Actual Position Size: $50.48
   Camouflaged Stop: $131.5975
   Order Style: camouflaged
   Notes: Odd-lot sizing and non-round stops to avoid detection
==================================================
```

#### ORB Strategy WAIT
```
VARMA AGENT V3 - TRADING CYCLE RESULT
==================================================
Status: success
Current Price: $136.0591
Risk Regime: RISK_OFF
Signal: WAIT
==================================================
```

### Key Fields Explained

| Field | Description |
|-------|-------------|
| Status | `success` or `error` |
| Current Price | Live market price fetched |
| Risk Regime | `RISK_ON` (above trend) or `RISK_OFF` (below trend) |
| Signal | `BUY`, `SELL`, `HOLD`, or `WAIT` |
| Position Size | USD amount allocated (Kelly + regime adjusted) |
| Stop Loss | Camouflaged exit price (non-round) |
| Asset Quantity | Odd-lot token amount (retail appearance) |
| Confidence | Signal strength (0-100%) |

### Camouflage Details
- **Odd-lot sizing**: Avoids round numbers (0.3710 vs 0.37)
- **Non-round stops**: Prevents obvious technical levels
- **Retail appearance**: Designed to blend with individual traders

## Troubleshooting

### Common Issues

#### "No signal generated"
```
# Check market conditions
python trader_agent_v3.py --dry-run --force-buy
```

#### "Risk validation failed"
```
# Check capital amount and position sizes
python trader_agent_v3.py --dry-run --capital 1000 --force-buy
```

#### "API connection error"
```
# Check internet and RPC endpoints
# Try different RPC if needed
export RPC_URL=https://api.mainnet-beta.solana.com
```

#### "Database locked"
```
# Kill any running processes
pkill -f trader_agent

# Reset database
rm trader_agent.db
python trader_agent_v3.py --dry-run
```

### Debug Mode
```bash
# Enable detailed logging
export LOG_LEVEL=DEBUG
python trader_agent_v3.py --dry-run
```

### Environment Check
```bash
# Verify Python version
python --version

# Check dependencies
pip list | grep -E "(numpy|pandas|pytest)"

# Verify wallet
python -c "from wallet_manager import SolanaWallet; print('Wallet OK')"
```

## Best Practices

### Development Workflow
1. **Always start with `--dry-run`**
2. **Test execution pipeline with `--force-buy`**
3. **Compare strategies under same conditions**
4. **Start live trading with small capital**

### Risk Management
1. **Use trailing stops for live trading**
2. **Start with conservative capital amounts**
3. **Monitor positions actively**
4. **Have emergency stop procedures**

### Performance Monitoring
1. **Log all runs with timestamps**
2. **Track win/loss ratios**
3. **Monitor drawdown levels**
4. **Review strategy performance regularly**

### Maintenance
1. **Keep dependencies updated**
2. **Monitor for API changes**
3. **Regular database cleanup**
4. **Backup configuration files**

## Command Reference

### Most Common Commands
```bash
# Testing
python trader_agent_v3.py --dry-run
python trader_agent_v3.py --dry-run --force-buy
python trader_agent_v3.py --dry-run --strategy orb

# Live Trading
python trader_agent_v3.py --strategy trend --capital 1000
python trader_agent_v3.py --strategy trend --trailing-stop
python trader_agent_v3.py --strategy orb --capital 2000
```

### Advanced Combinations
```bash
# Full test suite
python trader_agent_v3.py --dry-run --strategy trend --capital 1000 --force-buy --trailing-stop --trailing-distance 2.0

# Minimal live test
python trader_agent_v3.py --capital 50 --strategy trend --trailing-stop --trailing-distance 1.0

# Maximum safety
python trader_agent_v3.py --dry-run --capital 100 --strategy trend --trailing-stop --trailing-distance 1.0
```

---

**⚠️ Remember**: Always test thoroughly with `--dry-run` before live trading. Crypto markets can be extremely volatile, and this system trades with real money.
