# VARMA Trading Agent V3 🚀

**Samir Varma's Quantitative Trading System - Production-Ready Implementation**

[![Tests](https://img.shields.io/badge/tests-59%20passing-brightgreen)](https://github.com/alexanxin/smol-trade-consultant)
[![Python](https://img.shields.io/badge/python-3.11+-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A sophisticated algorithmic trading agent implementing Samir Varma's methodologies for regime-based trend following and risk management on Solana.

## 📈 Key Features

### 🎯 **Core Trading Strategies**
- **Trend Following**: 183-day regime classification with RISK_ON/OFF positioning
- **ORB Strategy**: Opening Range Breakout detection for intraday moves
- **Dual Strategy Support**: Switch between strategies via command line

### 🛡️ **Advanced Risk Management**
- **Kelly Criterion**: Fractional Kelly with 0.25x dampener for optimal sizing
- **Regime-Based Sizing**: 1.5x RISK_ON, 0.5x RISK_OFF multipliers
- **45% Max Drawdown Target**: Conservative risk limits vs traditional 3%
- **Pre-Trade Validation**: Comprehensive safety checks before execution

### 🎪 **Smart Execution**
- **Order Camouflage**: Odd-lot sizing and non-round stops to avoid front-running
- **Jupiter DEX Integration**: Live spot trading on Solana
- **Slippage Protection**: 1% slippage tolerance for reliable execution
- **Trailing Stops**: Optional automated profit protection

### 📊 **Performance & Monitoring**
- **Real-Time P&L**: Live position tracking and unrealized gains/losses
- **Historical Performance**: Dynamic Kelly updates from trade history
- **Database Integration**: Complete trade audit trail and analytics
- **Position Monitoring**: Automated stop loss management

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   VarmaAgent    │───▶│  Risk Engine     │───▶│   Strategies    │
│   (Async Core)  │    │  (Kelly + Regime)│    │ (Trend + ORB)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Smart Execution │───▶│  Jupiter Client  │───▶│   Database      │
│  (Camouflage)   │    │  (Live Trading)  │    │ (Positions)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Solana wallet with SOL
- USDC for trading (optional)

### Installation

```bash
# Clone repository
git clone https://github.com/alexanxin/smol-trade-consultant.git
cd smol-trade-consultant

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your SOLANA_PRIVATE_KEY
```

### Basic Usage

```bash
# Dry-run trend following (safe testing)
python trader_agent_v3.py --strategy trend --dry-run

# Live trading with trend strategy
python trader_agent_v3.py --strategy trend

# ORB strategy with trailing stops
python trader_agent_v3.py --strategy orb --trailing-stop --trailing-distance 2.0

# Custom capital allocation
python trader_agent_v3.py --capital 5000 --token SOL
```

## 📋 Command Line Options

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
  --token TOKEN         Token symbol to trade (default: SOL)
  --chain CHAIN         Blockchain network (default: solana)
  --capital CAPITAL     Total capital available (default: 1000)
  --dry-run             Run in simulation mode (no real trades)
  --force-buy           Force a BUY signal for testing execution
  --trailing-stop       Enable trailing stop-loss for positions
  --trailing-distance DISTANCE
                        Trailing stop distance as percentage (default: 2.0)
```

## 📊 Strategy Explanations

### Trend Following Strategy
**Philosophy**: "Let winners run until stopped out or regime changes"

- **Regime Classification**: 183-day MA position determines RISK_ON/OFF
- **Entry**: Above trend in RISK_ON regime
- **Exit**: Stop loss only (no profit targets)
- **Holding Period**: Days to years (long-term)

**Risk Multipliers**:
- RISK_ON (above trend): 1.5x position size
- RISK_OFF (below trend): 0.5x position size

### ORB Strategy (Opening Range Breakout)
**Philosophy**: "Ride institutional flow from opening range"

- **Range Detection**: First 15 minutes of trading establishes range
- **Breakout Logic**: Trade above/below range with momentum
- **Intraday Focus**: Positions closed by session end
- **Volume Confirmation**: Higher volume breakouts preferred

## 🛡️ Risk Management

### Kelly Criterion Implementation
```python
# Fractional Kelly with dampener
kelly_fraction = win_rate - ((1 - win_rate) / risk_reward_ratio)
fractional_kelly = max(0.0, kelly_fraction) * 0.25  # 0.25x dampener
```

### Position Sizing Example
```
Capital: $10,000
Win Rate: 55%
Avg Win: 8%, Avg Loss: 4%
Stop Loss: 3%

Kelly Size: $275 (2.75% of capital)
RISK_ON Multiplier: $413 (4.13% final size)
```

### Safety Features
- **Max Drawdown**: 45% portfolio limit (vs traditional 3%)
- **Position Bounds**: 5-25% individual position limits
- **Stop Loss Validation**: 0.5-10% range enforcement
- **Portfolio Exposure**: 2x leverage maximum across all positions

## 🎪 Order Camouflage

### Why Camouflage?
> *"Liquidity is scarce, and predatory algorithms hunt for obvious orders."*
>
> — Samir Varma

### Camouflage Techniques
- **Odd-Lot Sizing**: 0.3870 instead of 0.5 or 1.0 units
- **Non-Round Stops**: $127.83 instead of $128.00
- **Retail Appearance**: Orders designed to blend with retail traders
- **Variable Timing**: Avoids predictable execution patterns

### Example Camouflaged Order
```
Asset Quantity: 0.3930 (odd-lot)
Position Size: $51.04
Stop Loss: $128.0380 (non-round)
Execution Style: camouflaged
```

## 📈 Performance Monitoring

### Real-Time Dashboard
```
VARMA AGENT V3 - TRADING CYCLE RESULT
==================================================
Status: success
Current Price: $132.2354
Risk Regime: RISK_OFF
Signal: BUY
Entry Price: $132.2354
Position Size: $50.00
Stop Loss: $128.2683
Confidence: 90%

🛡️ CAMOUFLAGED ORDER DETAILS:
   Asset Quantity: 0.3630 units
   Position Size: $48.06
   Stop: $128.1770
```

### Database Schema
- **Trades**: Entry/exit prices, P&L, timestamps
- **Signals**: Strategy decisions with confidence scores
- **Portfolio Snapshots**: Equity curves and exposure tracking

## 🔧 Configuration

### Environment Variables (.env)
```bash
# Required
SOLANA_PRIVATE_KEY=your_private_key_here

# Optional
RPC_URL=https://mainnet.helius-rpc.com/?api-key=your_key
LOG_LEVEL=INFO
```

### Strategy Parameters
```python
VARMA_CONFIG = {
    'VARMA_KELLY_DAMPENER': 0.25,      # Fractional Kelly multiplier
    'VARMA_MAX_DRAWDOWN': 0.45,        # 45% max drawdown target
    'VARMA_TREND_PERIOD': 200,         # Days for trend calculation
    'VARMA_ORB_RANGE_MINUTES': 15,     # Opening range duration
    'VARMA_RISK_ON_MULTIPLIER': 1.5,   # Above-trend sizing
    'VARMA_RISK_OFF_MULTIPLIER': 0.5,  # Below-trend sizing
}
```

## 🧪 Testing

### Run All Tests
```bash
# Unit tests
python -m pytest tests/test_varma_risk_engine.py -v
python -m pytest tests/test_smart_execution.py -v

# Integration tests
python -m pytest tests/test_integration.py -v

# Noise stress tests
python -m pytest tests/test_noise_stress.py -v

# All tests
python -m pytest tests/ -v
```

### Test Coverage: 59 Tests Passing
- **Unit Tests**: 33 tests (individual components)
- **Integration Tests**: 13 tests (end-to-end workflows)
- **Noise Stress Tests**: 21 tests (robustness validation)

## 🚨 Risk Warnings

### Important Disclaimers
- **Live Trading Risk**: This system trades with real money
- **Volatility**: Crypto markets can be extremely volatile
- **No Guarantees**: Past performance ≠ future results
- **Education Required**: Understand Varma's methodologies before use

### Safety Recommendations
- Start with small capital amounts
- Use dry-run mode extensively for testing
- Monitor positions actively
- Have emergency stop procedures

## 🐛 Troubleshooting

### Common Issues

**"Insufficient data for trend calculation"**
- Need at least 30 days of price history
- Check data source connectivity

**"Risk validation failed"**
- Position size may exceed limits
- Check capital allocation settings

**"Jupiter API error"**
- Check Solana RPC connectivity
- Verify wallet has sufficient SOL for fees

### Debug Mode
```bash
# Enable detailed logging
export LOG_LEVEL=DEBUG
python trader_agent_v3.py --dry-run
```

## 📚 References

- **Samir Varma's Books**:
  - "Trading Systems and Money Management"
  - "Forex Made Simple"

- **Key Concepts**:
  - Kelly Criterion for position sizing
  - Regime classification for market timing
  - Order camouflage for execution efficiency

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add comprehensive tests
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## ⚠️ Legal Notice

This software is for educational and research purposes. Trading cryptocurrencies involves substantial risk of loss and is not suitable for every investor. The user of this software assumes all responsibility for its use and any losses incurred.

---

**Built with ❤️ for quantitative trading excellence**
