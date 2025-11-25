# Trader Agent

A Python-based trading agent that uses AI to analyze cryptocurrency market data and generate trade signals. The agent fetches real-time market data, calculates advanced technical indicators, and uses Google's Gemini AI to generate high-conviction trading signals based on Smart Money Concepts (SMC).

## Features

- Real-time market data fetching from Birdeye and CoinGecko APIs
- Advanced technical analysis including RSI, MACD, Fair Value Gaps (FVG), and price change calculations
- Multi-timeframe analysis (5-minute for execution, 1-hour for bias)
- AI-powered trade signal generation using Google's Gemini
- Support for multiple blockchain networks
- Dual-mode operation: Trade signals or comprehensive market analysis
- Smart Money Concepts (SMC) based analysis including liquidity analysis, order flow, and market structure
- Command-line interface for easy execution
- **Multi-Agent System**:
    - **News Agent**: Fetches real-time news from Google News RSS for sentiment analysis
    - **Risk Manager Agent**: Critiques and validates trade signals to reduce false positives

## Enhanced Capabilities

### Advanced Technical Analysis

- **Fair Value Gap (FVG) Detection**: Identifies bullish and bearish FVGs on multiple timeframes
- **Liquidity Level Analysis**: Calculates significant support/resistance levels based on volume and price action
- **Volume Profile Metrics**: Analyzes volume distribution and identifies high/low volume thresholds
- **Market Structure Analysis**: Detects swing highs/lows and recent market structure changes
- **Volume Analytics**: Tracks volume trends, spikes, and compares current volume to averages

### Comprehensive Market Analysis

- **Market Overview**: Live price, 24h change, volume, and liquidity analysis
- **Price & Momentum Read**: Multi-timeframe analysis with detailed momentum assessment
- **Liquidity & Order Flow**: Detailed buy/sell side liquidity analysis with liquidity imbalance identification
- **Fair Value Gaps (FVGs)**: Automatic FVG detection with zone, type, and impact analysis
- **Trading Plan Generation**: Entry/exit levels with risk-to-reward ratio calculations
- **Analyst's Take**: Professional market interpretation with clear trading bias
- **Analyst's Take**: Professional market interpretation with clear trading bias

### Multi-Agent Architecture

The system now employs a collaborative multi-agent approach:

1.  **News Agent**: Scours Google News RSS for the latest headlines related to the specific token to provide qualitative context (sentiment, major events).
2.  **Strategy Agent**: The core analyst that processes technical data and news to generate the initial trade signal.
3.  **Risk Manager Agent**: A "Devil's Advocate" agent that critiques the Strategy Agent's signal. It checks for weak reasoning, conflicting data, or high risk, and has the authority to **reject** or **downgrade** the signal.
### Optimal Trading Timeframes & Styles

The trader agent is **optimally designed for scalping and short-term day trading** with institutional-grade precision through Auction Market Theory (AMT) integration.

#### 📊 Multi-Timeframe Analysis

- **LTF (Lower TimeFrame)**: **5-minute data** - For execution and entry precision
- **HTF (Higher TimeFrame)**: **1-hour data** - For bias/trend direction confirmation
- **Daily**: **1-day data** - For broader market context and risk management

#### 🎯 Primary Trading Styles

**Scalping (1-15 minutes):**

- ✅ Ultra-precise LVN (Low Volume Node) targeting
- ✅ POC (Point of Control) retest entries
- ✅ Volume spike breakout detection
- ✅ Quick in/out trades with minimal risk

**Day Trading (15 minutes - 4 hours):**

- ✅ AMT Model 1: Trend Following during high volatility sessions
- ✅ AMT Model 2: Mean Reversion during range-bound periods
- ✅ Session-aware bias direction and strategy selection

#### ⚡ AMT-Enhanced Performance by Timeframe

| **Trading Style**     | **Primary Timeframe** | **Typical Hold Time** | **AMT Advantage**                                |
| --------------------- | --------------------- | --------------------- | ------------------------------------------------ |
| **Scalping**          | 5-minute              | 1-15 minutes          | LVN precision, volume spikes, aggression scoring |
| **Quick Day Trading** | 5-minute              | 15-120 minutes        | Model 1+2 flexibility, session optimization      |
| **Swing Day Trading** | 1-hour                | 2-4 hours             | Market state clarity, trend confirmation         |

#### 🌍 Session-Specific Optimizations

The AMT integration provides intelligent session-aware recommendations:

- **London-NY Overlap (9-14 UTC)**: Model 1 (Trend Following) - High volatility scalping
- **London Session (6-9 UTC)**: Model 2 (Mean Reversion) - Range trading and scalping
- **New York Session (14-18 UTC)**: Model 1 (Trend Following) - Momentum capture
- **Asian Session (0-6 UTC)**: Model 2 (Mean Reversion) - Consolidation trades

#### 💡 Key Benefits for Scalping/Day Trading

- **Objective Level Identification**: POC and LVN-based entries reduce guesswork
- **Market State Awareness**: Automatic balance vs imbalance detection
- **Aggression Confirmation**: Volume-based trade validation system
- **Session Intelligence**: Time-of-day strategy optimization
- **Location-Based Risk Management**: Stops placed at volume profile levels

#### 📈 Performance Expectations

**5-Minute LTF Advantages:**

- High frequency signal generation
- Precise entry/exit point identification
- Multiple daily trading opportunities
- Lower capital requirements for position sizing
- Quick feedback on strategy effectiveness

**Optimal Hold Times by Strategy:**

- **Scalping**: 5-30 minutes
- **Day Trading**: 30 minutes - 4 hours
- **Swing components**: 4+ hours (using HTF bias confirmation)

## Supported Networks

The trader agent supports the following blockchain networks:

- **Solana** - Supports SOL and other SPL tokens
- **Ethereum** - Supports ETH and ERC-20 tokens
- **Binance Smart Chain (BSC)** - Supports BNB and BEP-20 tokens

### Minimal Cost-Optimized Mode

For high-frequency monitoring without AI costs:

```bash
python trader-agent.py --token SOL --mode minimal
```

This mode provides basic signals using simple logic (RSI + price change) without calling Gemini API, making it completely free to run and perfect for frequent monitoring.

- **Polygon** - Supports MATIC and other Polygon tokens

## Installation

### Command Line Arguments

- `--token` - Token symbol (e.g., SOL, BTC, ETH) - Default: SOL
- `--chain` - Blockchain network (e.g., solana, ethereum, bsc) - Default: solana
- `--mode` - Output mode: `signal` for trade signal, `analysis` for comprehensive market analysis, `minimal` for bare minimum data and signals (no AI, cost-optimized)

## Cost Optimization Strategies

### Token Cost Management

Since Gemini API calls consume tokens and incur costs, the trader agent provides multiple modes and strategies to optimize usage:

#### 🆓 **Minimal Mode (Zero AI Cost)**

For frequent monitoring without AI costs, use minimal mode:

```bash
python trader-agent.py --token SOL --mode minimal
```

**Benefits:**

- **Zero Gemini API calls** - Completely free to run
- **Quick signals** - Based on simple RSI and price change logic
- **Frequent monitoring** - Can be called every 1-5 minutes without cost concerns
- **Essential data only** - Price, 1H change, RSI, and basic momentum

**Best for:**

- High-frequency monitoring during active trading sessions
- Market overview checks
- Backup signals when AI is unavailable
- Cost-conscious traders

#### 💰 **Cost-Effective Frequency Strategy**

| **Trading Session (UTC)**    | **Recommended Frequency** | **Mode**              | **Daily Cost** |
| ---------------------------- | ------------------------- | --------------------- | -------------- |
| **London-NY Overlap (9-14)** | Every 15-30 min           | `signal` or `minimal` | Low            |
| **New York (14-18)**         | Every 20-30 min           | `signal` or `minimal` | Low            |
| **London (6-9)**             | Every 30-45 min           | `minimal`             | Very Low       |
| **Asian (0-6)**              | Every 1-2 hours           | `minimal`             | Minimal        |
| **Weekend**                  | Every 3-4 hours           | `minimal`             | Minimal        |

#### 🎯 **Hybrid Approach (Recommended)**

1. **Use `minimal` mode** for frequent monitoring (every 15-30 minutes)
2. **Use `signal` mode** for detailed analysis when `minimal` shows interesting signals
3. **Use `analysis` mode** once per day for comprehensive market overview

**Example Workflow:**

```bash
# Frequent monitoring during active hours
python trader-agent.py --token SOL --mode minimal

# Detailed analysis when minimal shows BUY signal
python trader-agent.py --token SOL --mode signal

# Comprehensive overview once daily
python trader-agent.py --token SOL --mode analysis
```

#### 📊 **Token Usage Comparison**

| **Mode**       | **Gemini Calls** | **Tokens per Call** | **Daily Cost** | **Use Case**              |
| -------------- | ---------------- | ------------------- | -------------- | ------------------------- |
| **`minimal`**  | 0                | 0                   | Free           | High-frequency monitoring |
| **`signal`**   | 1 per call       | ~2,000 tokens       | Low            | Detailed signals          |
| **`analysis`** | 1 per call       | ~4,000 tokens       | Medium         | Comprehensive analysis    |

#### ⚡ **Session-Aware Cost Optimization**

The agent automatically detects trading sessions and can be scheduled accordingly:

- **High Volatility** (London-NY overlap): More frequent `minimal` calls
- **Low Volatility** (Asian session): Less frequent calls
- **Weekend**: Very infrequent calls or disable monitoring

This approach can reduce costs by **80-90%** while maintaining effective market awareness.

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd trader-agent
   ```

2. Install the required dependencies:
   ```bash
   pip install requests google-genai pandas ta python-dotenv feedparser
   ```

Or install all dependencies from the requirements.txt file:

```bash
pip install -r requirements.txt
```

## Configuration

The script requires API keys for the following services:

1. **Birdeye API Key** - For market data
2. **Google Gemini API Key** - For AI analysis
3. **CoinGecko API Key** - For additional market data

After downloading the script, copy the `.env.example` file to create a new `.env` file:

```bash
cp .env.example .env
```

Then edit the `.env` file to add your API keys:

```env
BIRDEYE_API_KEY=your-birdeye-api-key
GEMINI_API_KEY=your-gemini-api-key
COINGECKO_API_KEY=your-coingecko-api-key
```

The script will automatically load these values from the `.env` file.

## Usage

### Basic Usage

Run the trader agent with default settings (SOL on Solana) in signal mode:

```bash
python trader-agent.py
```

Or specify a token and chain:

```bash
python trader-agent.py --token ETH --chain ethereum
```

### Comprehensive Market Analysis Mode

Run the trader agent in comprehensive market analysis mode:

```bash
python trader-agent.py --token SOL --chain solana --mode analysis
```

### Command Line Arguments

- `--token` - Token symbol (e.g., SOL, BTC, ETH) - Default: SOL
- `--chain` - Blockchain network (e.g., solana, ethereum, bsc) - Default: solana
- `--mode` - Output mode: `signal` for trade signal, `analysis` for comprehensive market analysis - Default: signal

## How It Works

1. **Data Retrieval**: Fetches market data from Birdeye and OHLCV data from CoinGecko
2. **Advanced Technical Analysis**: Calculates RSI, MACD, FVGs, liquidity levels, volume profiles, and market structure
3. **AI Analysis**: Sends structured data to Gemini for trade signal or market analysis generation
4. **Output**: Generates either BUY/SELL/HOLD signals or comprehensive market analysis

## Output Modes

### Signal Mode (Default)

Generates concise trade signals with:

- Coin symbol and current price
- Action (BUY/SELL/HOLD)
- Entry price
- Stop loss
- Take profit
- Conviction score (1-100)
- Reasoning from the AI

### Analysis Mode

Generates comprehensive market analysis including:

- ⚡ Live Market Overview with price, volume, and liquidity
- 🔍 Price & Momentum Read across multiple timeframes
- 💧 Liquidity & Order Flow analysis
- 📊 Fair Value Gaps (FVGs) detection
- 🧭 Trading Plan with entry/exit levels and risk-to-reward ratios
- ✅ Analyst's Take with detailed market interpretation

## Example Output

### Signal Mode Output

```
    🧠 GEMINI HIGH-CONVICTION TRADE SIGNAL
   COIN: SOL @ $222.66
   ACTION: BUY
   ENTRY PRICE: $222.00
   STOP LOSS: $220.90
   TAKE PROFIT: $231.30
   CONVICTION: 85%
--------------------------------------------------
   REASONING: The higher timeframe (HTF) trend for SOL remains Bullish, supported by an HTF RSI of 68.67. The current price has experienced a significant retracement from recent highs (last 10 close prices around 230-231), landing precisely on strong HTF and LTF liquidity support levels identified around 221.85 - 223.96. This aggressive move down is interpreted as a potential liquidity sweep below previous LTF lows, entering a key demand zone. Further reinforcing the bullish bias is a clear 'Bullish Crossover' on the MACD, indicating a shift in momentum, and increasing HTF volume, which adds conviction to a potential bounce. We anticipate a rebound from this demand zone to target previous resistance and liquidity levels.
```

### Analysis Mode Output

```
⚡ Live SOL Market Overview
Current Price: $222.66 (Birdeye live)
24h Change: 0.0%
Volume (24h): ~$0.00 (0.0%)
Liquidity: ~$21.48 Billion — High liquidity, indicating a healthy and actively traded market.

🔍 Price & Momentum Read
Timeframe | Change | Structure | Momentum
1H | 0.71% | Broken Bearish / Retesting | Bullish (RSI 61.83)
4H | 0.05% | Broken Bearish / Retesting | Bullish (RSI 68.67)
12H | 0.0% | Broken Bearish / Retesting | Bullish (RSI 68.67)
24H | 0.0% | Broken Bearish / Retesting | Bullish (RSI 68.67)

Short-term: SOL has seen a slight positive movement of 0.71% in the last hour and 0.05% over the past 4 hours, indicating a minor rebound from a recent significant downturn. Despite these slight upticks, the current price ($222.66) is notably below all recent short-term (LTF) swing lows ($228.47) and highs ($231.56). This suggests a break of short-term market structure to the downside. However, both the 14-period RSI (61.83) and a bullish MACD crossover signal strong underlying bullish momentum.

[...] (Full analysis continues with all sections from the example)
```
