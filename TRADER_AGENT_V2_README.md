# Trader Agent V2 Documentation

## Overview

Trader Agent V2 is an AI-powered cryptocurrency trading agent built on the TiMi (Trading Intelligence and Market Insights) architecture. It uses advanced technical analysis, sentiment analysis, and AI debate systems to make trading decisions.

## Key Features

- **Multi-Agent Analysis**: Technical analyst, sentiment analyst, and master trader agents
- **Smart Money Concepts**: Implements Fabio Valentino's trading methodology
- **Debate Room**: AI agents debate trading decisions for better accuracy
- **Position Management**: Automatic position monitoring with stop-loss and take-profit
- **Multiple Execution Modes**: Spot trading via Jupiter and leverage trading via Drift
- **Risk Management**: Kelly Criterion position sizing and adaptive risk controls

## System Requirements

### Python Version

**Required**: Python 3.9 or higher (Python 3.11 recommended)

Check your Python version:
```bash
python3 --version
```

### Operating System

- **macOS**: Fully supported
- **Linux**: Fully supported
- **Windows**: Supported (use WSL2 recommended)

## Installation

### 1. Clone or Download the Project

```bash
cd /path/to/trader-agent
```

### 2. Create Virtual Environment

#### On macOS/Linux:

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Verify activation (you should see (.venv) in your prompt)
which python
```

#### On Windows (PowerShell):

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\Activate.ps1

# If you get execution policy error, run:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### On Windows (Command Prompt):

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\activate.bat
```

### 3. Install Dependencies

With the virtual environment activated:

```bash
# Upgrade pip first
pip install --upgrade pip

# Install all required packages
pip install -r requirements.txt
```

**Note**: If you encounter dependency conflicts, try:
```bash
pip install -r requirements.txt --no-deps
pip install langgraph autogen-agentchat[gemini] qdrant-client google-generativeai
```

### 4. Verify Installation

```bash
# Check if key packages are installed
python -c "import langgraph; import autogen; print('✅ Installation successful!')"
```

## Prerequisites

### Required Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# Solana RPC and Wallet
SOLANA_PRIVATE_KEY=your_base58_encoded_private_key_here
RPC_URL=https://mainnet.helius-rpc.com/?api-key=your_helius_api_key

# API Keys
BIRDEYE_API_KEY=your_birdeye_api_key
GEMINI_API_KEY=your_gemini_api_key
COINGECKO_API_KEY=your_coingecko_api_key
```

### API Requirements

- **Birdeye API**: For market data and token information
- **CoinGecko API**: For historical OHLCV data
- **Gemini API**: For AI-powered trading decisions
- **Helius RPC**: For Solana blockchain interaction

### Python Dependencies

Install required packages:
```bash
pip install -r requirements.txt
```

### 5. Deactivate Virtual Environment (When Done)

When you're finished working with the agent:

```bash
# Simply run
deactivate
```

To reactivate later:
```bash
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate     # Windows
```

## Quick Start Guide

### First Time Setup (Complete Walkthrough)

```bash
# 1. Navigate to project directory
cd /Users/aleksandar/Desktop/Raboten/trader-agent

# 2. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # You should see (.venv) in your prompt

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
nano .env  # Edit with your API keys

# 5. Test the installation (dry-run mode)
python trader_agent_v2.py --spot --dry-run --token SOL

# 6. When done
deactivate
```

### Daily Usage

```bash
# Activate environment
source .venv/bin/activate

# Run the agent
python trader_agent_v2.py --spot --dry-run --token SOL

# Stop with Ctrl+C when done
# Deactivate environment
deactivate
```

## Command Line Usage

### Basic Syntax

```bash
python trader_agent_v2.py [OPTIONS]
```

### Command Line Switches

#### Trading Configuration

- `--token SYMBOL`
  - **Default**: `SOL`
  - **Description**: Token symbol to analyze and trade
  - **Examples**: `--token SOL`, `--token BONK`, `--token JUP`

#### Execution Modes

- `--spot`
  - **Description**: Enable spot trading via Jupiter DEX
  - **Notes**: Cannot be used with `--leverage`

- `--leverage`
  - **Description**: Enable leverage trading via Drift Protocol
  - **Notes**: Cannot be used with `--spot`. Currently disabled.

#### Risk and Safety

- `--dry-run`
  - **Default**: `True` (enabled)
  - **Description**: Simulate execution without actual trades
  - **Notes**: This is the default mode for safety

- `--live`
  - **Description**: Execute real trades (disables dry-run)
  - **Warning**: Only use with real money when confident in the system

#### Position Monitoring

- `--monitor-interval SECONDS`
  - **Default**: `30`
  - **Description**: Position monitoring interval in seconds
  - **Notes**: How often to check position P&L and trigger stops

- `--trailing-stop`
  - **Description**: Enable trailing stop-loss for positions
  - **Notes**: Automatically adjusts stop-loss as price moves favorably

- `--trailing-distance PERCENTAGE`
  - **Default**: `2.0`
  - **Description**: Trailing stop distance as percentage
  - **Example**: `--trailing-distance 3.5`

## Usage Examples

### Analysis Only (Safe)

Run analysis without any trading execution:

```bash
python trader_agent_v2.py
```

### Spot Trading Simulation

Test spot trading with SOL in dry-run mode:

```bash
python trader_agent_v2.py --spot --dry-run --token SOL
```

### Live Spot Trading (⚠️ Use with Caution)

Execute real spot trades:

```bash
python trader_agent_v2.py --spot --live --token SOL
```

### Custom Monitoring and Stops

Configure position monitoring with trailing stops:

```bash
python trader_agent_v2.py --spot --dry-run --token BONK \
  --monitor-interval 15 \
  --trailing-stop \
  --trailing-distance 1.5
```

### Different Token Analysis

Analyze and trade different tokens:

```bash
python trader_agent_v2.py --spot --dry-run --token JUP
```

## How It Works

### Execution Flow

1. **Market Scan**: Technical and sentiment analysis agents gather data
2. **Debate Room**: AI agents debate the trading decision
3. **Decision Making**: Master trader agent makes final BUY/SELL/HOLD decision
4. **Risk Assessment**: Kelly Criterion calculates position size
5. **Execution**: If enabled, executes trades via Jupiter or Drift
6. **Monitoring**: Continuously monitors positions and manages stops

### Trading Logic

- **BUY SOL**: Uses USDC to buy SOL via Jupiter
- **BUY Other Tokens**: Uses SOL to buy target token
- **SELL SOL**: Sells SOL for USDC
- **SELL Other Tokens**: Sells token for SOL

### Position Management

- **Entry**: Records trade details in SQLite database
- **Monitoring**: Checks P&L every `--monitor-interval` seconds
- **Stop Loss**: Automatic loss protection
- **Take Profit**: Automatic profit taking
- **Trailing Stops**: Optional dynamic stop-loss adjustment

## Output and Logging

### Console Output

The agent provides detailed console output including:

- Market data and analysis results
- Debate transcripts
- Trading decisions and confidence levels
- Execution results (simulated or real)
- Position monitoring updates

### Database Storage

Trades and positions are stored in `trader_agent.db`:

- **positions** table: Active positions
- **trades** table: Completed trades
- **market_experiences** collection: AI learning data

## Safety Features

- **Dry-run mode** by default
- **Wallet balance checks** before trading
- **API quota monitoring**
- **Error handling** with graceful failures
- **Position size limits** via Kelly Criterion

## Troubleshooting

### Common Issues

1. **"No wallet configured"**
   - Ensure `SOLANA_PRIVATE_KEY` is set in `.env`
   - Verify private key format (base58 encoded)

2. **"Insufficient balance"**
   - For SOL buys: Ensure USDC balance > $1
   - For other token buys: Ensure SOL balance > 0.01
   - For sells: Ensure token balance > 0

3. **"API quota exceeded"**
   - Gemini API has daily limits
   - Wait or upgrade API plan
   - Use dry-run mode for testing

4. **"Token address not found"**
   - Verify token symbol is correct
   - Check if token is supported on Solana

### Debug Mode

Add debug prints by modifying the logging level in the source code.

## Architecture

### Core Components

- **Event Bus**: Asynchronous communication between components
- **State Manager**: Global state management
- **Orchestrator**: Coordinates the analysis and execution pipeline
- **Position Monitor**: Real-time position management

### AI Components

- **Technical Analyst**: Price action and technical analysis
- **Sentiment Analyst**: News and social sentiment analysis
- **Master Trader**: Final decision making with risk assessment
- **Debate Room**: Multi-agent decision validation

## Contributing

When modifying the codebase:

1. Test changes in dry-run mode first
2. Update this documentation for new features
3. Follow the existing code patterns
4. Add appropriate error handling

## License

This project is for educational and research purposes. Use at your own risk.
