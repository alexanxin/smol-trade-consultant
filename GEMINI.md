# Trader Agent

## Project Overview

This is a Python-based cryptocurrency trading agent that uses AI to analyze market data and generate trade signals. The agent fetches real-time market data from Birdeye and CoinGecko APIs, calculates a wide range of technical indicators, and uses an AI model (either Google's Gemini or a local LM Studio instance) to generate high-conviction trading signals based on Smart Money Concepts (SMC) and a proprietary "Fabio Valentino Strategy".

The project is architected with a clear separation of concerns:
- `trader-agent.py`: The core application logic.
- `api_interface.py`: A FastAPI-based REST API to interact with the agent.
- `output_formatter.py`: A utility for creating a rich, user-friendly command-line output.
- `requirements.txt`: A list of the core Python dependencies.
- `api_requirements.txt`: A list of the Python dependencies for the API.

## Building and Running

### Dependencies

Install the core dependencies using pip:

```bash
pip install -r requirements.txt
```

To run the API, install the API-specific dependencies:

```bash
pip install -r api_requirements.txt
```

### Configuration

The agent requires API keys for Birdeye, Google Gemini, and CoinGecko.

1.  Copy the example `.env.example` file to a new `.env` file:

    ```bash
    cp .env.example .env
    ```

2.  Edit the `.env` file and add your API keys:

    ```env
    BIRDEYE_API_KEY=your-birdeye-api-key
    GEMINI_API_KEY=your-gemini-api-key
    COINGECKO_API_KEY=your-coingecko-api-key
    ```

### Running the Agent

You can run the trading agent directly from the command line:

```bash
python trader-agent.py --token <TOKEN_SYMBOL> --chain <BLOCKCHAIN> --mode <MODE>
```

-   `--token`: The token symbol (e.g., `SOL`, `BTC`, `ETH`). Defaults to `SOL`.
-   `--chain`: The blockchain network (e.g., `solana`, `ethereum`, `bsc`). Defaults to `solana`.
-   `--mode`: The output mode. `signal` for a trade signal, `analysis` for a comprehensive market analysis. Defaults to `signal`.
-   `--ai-provider`: The AI provider to use. `auto` (default), `gemini`, or `lmstudio`.

### Running the API

To start the FastAPI server, run:

```bash
python api_interface.py
```

The API will be available at `http://localhost:8000`. You can find the API documentation at `http://localhost:8000/docs`.

## Development Conventions

-   **Code Style:** The code is generally well-structured and follows common Python conventions.
-   **Configuration:** Application configuration is managed through environment variables loaded from a `.env` file, which is a good security practice.
-   **Testing:** The presence of numerous `test_*.py` files suggests that the project uses a testing framework, likely `pytest`. To run the tests, you would typically run `pytest` from the root of the project.
-   **User Interface:** The project has a focus on user experience, with a dedicated `output_formatter.py` for creating a visually appealing and informative command-line interface.
