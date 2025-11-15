# Quick Installation Guide

## 1. Install API Dependencies

```bash
pip install -r api_requirements.txt
```

## 2. Start the API Server

```bash
python start_api.py
```

The API will be available at:

- **API**: http://localhost:8000
- **Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 3. Test the API

```bash
# Run the test suite
python test_api.py

# Or run the interactive demo
python demo_api.py
```

## 4. Use the API

### Simple Example (curl):

```bash
curl -X POST "http://localhost:8000/api/analyze/simple" \
     -H "Content-Type: application/json" \
     -d '{"token": "SOL", "chain": "solana"}'
```

### Full Example (Python):

```python
import requests

response = requests.post('http://localhost:8000/api/analyze/signal', json={
    'token': 'SOL',
    'chain': 'solana',
    'mode': 'signal',
    'ai_provider': 'auto'
})

result = response.json()
print(f"Action: {result['action']}")
print(f"Conviction: {result['conviction_score']}%")
```

## Environment Variables

Make sure you have the required API keys in your `.env` file:

- `BIRDEYE_API_KEY`
- `GEMINI_API_KEY` (optional, for Gemini AI)
- `COINGECKO_API_KEY`

## Troubleshooting

- **Import errors**: Install missing dependencies with `pip install -r api_requirements.txt`
- **API not responding**: Check that the API server is running with `python start_api.py`
- **Trader agent errors**: Ensure your `.env` file has the required API keys
- **Timeout errors**: The script may take 30-120 seconds depending on AI provider and analysis type

## Available Endpoints

- `POST /api/analyze/signal` - Get trading signal
- `POST /api/analyze/comprehensive` - Get comprehensive analysis
- `POST /api/analyze/simple` - Simple analysis with defaults
- `GET /api/tokens/supported` - Get supported tokens
- `GET /api/health` - Health check
- `GET /` - API information

For detailed API documentation, visit http://localhost:8000/docs when the server is running.
