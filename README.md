# Trader Agent

A Python-based trading agent that uses AI to analyze cryptocurrency market data and generate trade signals. The agent fetches real-time market data, calculates technical indicators, and uses Google's Gemini AI to generate high-conviction trading signals.

## Features

- Real-time market data fetching from Birdeye and CoinGecko APIs
- Technical analysis including RSI, MACD, and price change calculations
- Multi-timeframe analysis (5-minute for execution, 1-hour for bias)
- AI-powered trade signal generation using Google's Gemini
- Support for multiple blockchain networks
- Command-line interface for easy execution

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

Run the trader agent with default settings (SOL on Solana):

```bash
python trader-agent.py
```

Or specify a token and chain:

```bash
python trader-agent.py --token ETH --chain ethereum
```

### Command Line Arguments

- `--token` - Token symbol (e.g., SOL, BTC, ETH) - Default: SOL
- `--chain` - Blockchain network (e.g., solana, ethereum, bsc) - Default: solana

## How It Works

1. **Data Retrieval**: Fetches market data from Birdeye and OHLCV data from CoinGecko
2. **Technical Analysis**: Calculates RSI, MACD, and other indicators
3. **AI Analysis**: Sends structured data to Gemini for trade signal generation
4. **Signal Output**: Generates BUY/SELL/HOLD signals with entry price, stop loss, take profit, and conviction score

## Output

The agent outputs a trade signal with the following information:

- Coin symbol and current price
- Action (BUY/SELL/HOLD)
- Entry price
- Stop loss
- Take profit
- Conviction score (1-100)
- Reasoning from the AI

## Example Output

```
==================================================
    🧠 GEMINI HIGH-CONVICTION TRADE SIGNAL
==================================================
   COIN: ETH @ $4704.9954153050485
   ACTION: BUY
   ENTRY PRICE: $4705.0
   STOP LOSS: $4690.0
   TAKE PROFIT: $4735.0
   CONVICTION: 85%
--------------------------------------------------
   REASONING: Price has executed a strong impulsive move upwards, evidenced by the current price (4704.99) being significantly higher than the 'last_10_close_prices' (around 4677-4681). This suggests a break of market structure to the upside or a liquidity grab. Following this pump, the price has experienced a minor retracement in the last hour (-0.04% change). This retracement has brought the RSI into oversold territory (28.18), indicating a potential bounce or reversal of the short-term pullback. Concurrently, the MACD shows a 'Bullish Crossover', confirming nascent upward momentum. Despite the 'htf_trend' being Bearish, this setup presents a high-probability counter-trend trade for a liquidity grab or a retrace into a higher supply zone. We are buying the expected continuation of the impulsive move after a shallow retrace, targeting a 2:1 risk-to-reward ratio. The stop loss is placed below a logical short-term support level, while the take profit targets potential higher liquidity.
==================================================
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
