    🧠 GEMINI HIGH-CONVICTION TRADE SIGNAL

COIN: ETH @ $4704.9954153050485
ACTION: BUY
ENTRY PRICE: $4705.0
STOP LOSS: $4690.0
TAKE PROFIT: $4735.0
CONVICTION: 85%

---

REASONING: Price has executed a strong impulsive move upwards, evidenced by the current price (4704.99) being significantly higher than the 'last_10_close_prices' (around 4677-4681). This suggests a break of market structure to the upside or a liquidity grab. Following this pump, the price has experienced a minor retracement in the last hour (-0.04% change). This retracement has brought the RSI into oversold territory (28.18), indicating a potential bounce or reversal of the short-term pullback. Concurrently, the MACD shows a 'Bullish Crossover', confirming nascent upward momentum. Despite the 'htf_trend' being Bearish, this setup presents a high-probability counter-trend trade for a liquidity grab or a retrace into a higher supply zone. We are buying the expected continuation of the impulsive move after a shallow retrace, targeting a 2:1 risk-to-reward ratio. The stop loss is placed below a logical short-term support level, while the take profit targets potential higher liquidity.

````

## Dependencies

The required dependencies are listed in the `requirements.txt` file:

- requests
- google-genai
- pandas
- ta (technical analysis library)
- python-dotenv
- argparse

To install all dependencies, run:

```bash
pip install -r requirements.txt
````

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

## Supported Networks

The trader agent supports the following blockchain networks:

- **Solana** - Supports SOL and other SPL tokens
- **Ethereum** - Supports ETH and ERC-20 tokens
- **Binance Smart Chain (BSC)** - Supports BNB and BEP-20 tokens
- **Polygon** - Supports MATIC and other Polygon tokens

## Installation

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd trader-agent
   ```

2. Install the required dependencies:
   ```bash
   pip install requests google-genai pandas ta python-dotenv
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

## Dependencies

The required dependencies are listed in the `requirements.txt` file:

- requests
- google-genai
- pandas
- ta (technical analysis library)
- python-dotenv
- argparse

To install all dependencies, run:

```bash
pip install -r requirements.txt
```
