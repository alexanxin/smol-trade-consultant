# Trader Agent API Interface

A REST API wrapper around the `trader-agent.py` script that allows you to execute the trading analysis through HTTP endpoints and receive structured JSON responses.

## Features

- **REST API Interface**: Execute trader-agent.py through HTTP endpoints
- **Multiple Output Modes**: Get either trading signals or comprehensive market analysis
- **Flexible AI Providers**: Support for auto-detection, Gemini API, and LM Studio
- **Structured Responses**: Clean JSON responses with proper error handling
- **CORS Enabled**: Easy integration with web frontends
- **Interactive Documentation**: Auto-generated API docs with Swagger UI

## Quick Start

### 1. Install Dependencies

```bash
pip install -r api_requirements.txt
```

### 2. Start the API Server

```bash
python start_api.py
```

Or directly:

```bash
uvicorn api_interface:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Access the API

- **API Base URL**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## API Endpoints

### Core Endpoints

#### POST /api/analyze/signal

Get a trading signal for a specific token.

**Request Body:**

```json
{
  "token": "SOL",
  "chain": "solana",
  "mode": "signal",
  "ai_provider": "auto",
  "lmstudio_url": "http://127.0.0.1:1234"
}
```

**Response:**

```json
{
  "success": true,
  "action": "BUY",
  "entry_price": 145.67,
  "stop_loss": 142.33,
  "take_profit": 148.92,
  "conviction_score": 78,
  "strategy_type": "trend_following",
  "reasoning": "Strong bullish momentum detected...",
  "coin_symbol": "SOL",
  "current_price": 145.67,
  "market_data": {
    "symbol": "SOL",
    "value": 145.67,
    "liquidity": 1000000,
    "volume": 500000
  },
  "fabio_analysis": {
    "ltf_market_state": {...},
    "trading_opportunities": {...}
  }
}
```

#### POST /api/analyze/comprehensive

Get comprehensive market analysis for a specific token.

**Request Body:**

```json
{
  "token": "BTC",
  "chain": "ethereum",
  "mode": "analysis",
  "ai_provider": "gemini"
}
```

**Response:**

```json
{
  "success": true,
  "analysis": "⚡ Live BTC Market Overview (Fabio Valentino Framework)\nCurrent Price: $43,250 | Trading Session: New_York\nMarket State: imbalanced | Volume Profile: High volume at $43,000 POC\n...",
  "coin_symbol": "BTC",
  "market_data": {}
}
```

#### POST /api/analyze/simple

Simple analysis with default parameters (auto AI provider, signal mode).

**Request Body:**

```json
{
  "token": "ETH",
  "chain": "ethereum"
}
```

### Utility Endpoints

#### GET /api/tokens/supported

Get list of supported tokens and networks.

**Response:**

```json
{
  "supported_tokens": ["SOL", "BTC", "ETH", "BNB", "ADA", "DOT", "MATIC"],
  "supported_chains": ["solana", "ethereum", "bsc", "polygon"],
  "supported_modes": ["signal", "analysis"],
  "supported_ai_providers": ["auto", "gemini", "lmstudio"],
  "default_settings": {
    "chain": "solana",
    "mode": "signal",
    "ai_provider": "auto",
    "lmstudio_url": "http://127.0.0.1:1234"
  }
}
```

#### GET /api/example/{token}

Get example analysis for a token (demonstration endpoint).

#### GET /health

Health check endpoint.

#### GET /

Root endpoint with basic API information.

## Usage Examples

### Using curl

```bash
# Get a trading signal for SOL
curl -X POST "http://localhost:8000/api/analyze/signal" \
     -H "Content-Type: application/json" \
     -d '{
       "token": "SOL",
       "chain": "solana",
       "mode": "signal",
       "ai_provider": "auto"
     }'

# Get comprehensive analysis for BTC
curl -X POST "http://localhost:8000/api/analyze/comprehensive" \
     -H "Content-Type: application/json" \
     -d '{
       "token": "BTC",
       "chain": "ethereum",
       "mode": "analysis",
       "ai_provider": "gemini"
     }'
```

### Using Python requests

```python
import requests

# Get trading signal
response = requests.post('http://localhost:8000/api/analyze/signal', json={
    'token': 'SOL',
    'chain': 'solana',
    'mode': 'signal',
    'ai_provider': 'auto'
})

if response.status_code == 200:
    result = response.json()
    print(f"Action: {result['action']}")
    print(f"Conviction: {result['conviction_score']}%")
    print(f"Entry: {result['entry_price']}")
else:
    print(f"Error: {response.text}")
```

### Using JavaScript fetch

```javascript
// Get trading signal
const response = await fetch("http://localhost:8000/api/analyze/signal", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    token: "SOL",
    chain: "solana",
    mode: "signal",
    ai_provider: "auto",
  }),
});

const result = await response.json();
console.log("Trading Signal:", result);
```

## Configuration

### Environment Variables

The API respects the same environment variables as the underlying trader-agent.py:

- `BIRDEYE_API_KEY`: Birdeye API key for market data
- `GEMINI_API_KEY`: Google Gemini API key for AI analysis
- `COINGECKO_API_KEY`: CoinGecko API key for OHLCV data
- `GOOGLE_CLOUD_PROJECT`: Google Cloud Project ID (optional)

### AI Provider Configuration

- **auto**: Automatically detects the best available provider
- **gemini**: Uses Google Gemini API (requires `GEMINI_API_KEY`)
- **lmstudio**: Uses local LM Studio instance (default: http://127.0.0.1:1234)

## Error Handling

All endpoints return structured error responses:

```json
{
  "success": false,
  "error": "Detailed error message",
  "traceback": "Optional traceback for debugging"
}
```

Common error codes:

- **500**: Internal server error or script execution failure
- **422**: Validation error (missing or invalid parameters)
- **400**: Bad request format

## Integration with Frontends

The API includes CORS headers, making it easy to integrate with web applications:

```javascript
// React example
const fetchTradingSignal = async (token) => {
  const response = await fetch("http://localhost:8000/api/analyze/signal", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      token: token,
      chain: "solana",
      mode: "signal",
    }),
  });

  return await response.json();
};
```

## Performance Considerations

- **Timeout**: Each request has a 5-minute timeout
- **Caching**: Consider implementing caching for repeated analysis of the same token
- **Rate Limiting**: The underlying APIs (Birdeye, CoinGecko) have rate limits
- **Background Tasks**: For high-volume usage, consider implementing background job processing

## Development

### Running in Development Mode

```bash
# With auto-reload
uvicorn api_interface:app --host 0.0.0.0 --port 8000 --reload

# With detailed logging
uvicorn api_interface:app --host 0.0.0.0 --port 8000 --log-level debug
```

### Testing Endpoints

Visit http://localhost:8000/docs for interactive API testing using Swagger UI.

## Architecture

The API wrapper works by:

1. **Receiving HTTP Requests** with trading analysis parameters
2. **Executing trader-agent.py** as a subprocess with the appropriate arguments
3. **Parsing the Output** from the trading agent (both structured and formatted output)
4. **Returning Structured JSON** responses with proper error handling

## Limitations

- Each request executes the full trader-agent.py script (may take 10-30 seconds)
- No persistent caching between requests
- Requires the same environment setup as the original trader-agent.py
- Large responses for comprehensive analysis mode

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all trader-agent.py dependencies are installed
2. **API Key Errors**: Check that required API keys are set in environment variables
3. **Timeout Errors**: The script may take longer than expected, increase timeout if needed
4. **Permission Errors**: Ensure the script has execute permissions

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## License

This API interface is provided as-is to work with the existing trader-agent.py script.
