# Fixed API Usage - Now Gemini Works!

## Problem Solved ✅

I've fixed the issue where the `/api/analyze/simple` endpoint was ignoring the `ai_provider` parameter. Now you can properly use Gemini!

## How to Use Gemini:

### 1. Simple Request with Gemini:

```bash
curl -X POST "http://localhost:8000/api/analyze/simple" \
     -H "Content-Type: application/json" \
     -d '{"token": "SOL", "chain": "solana", "ai_provider": "gemini"}'
```

### 2. Full Signal Request with Gemini:

```bash
curl -X POST "http://localhost:8000/api/analyze/signal" \
     -H "Content-Type: application/json" \
     -d '{"token": "BTC", "chain": "ethereum", "mode": "signal", "ai_provider": "gemini"}'
```

### 3. Python Example:

```python
import requests

response = requests.post('http://localhost:8000/api/analyze/signal', json={
    'token': 'SOL',
    'chain': 'solana',
    'mode': 'signal',
    'ai_provider': 'gemini'  # This now works properly!
})

result = response.json()
print(f"Action: {result['action']}")
print(f"Conviction: {result['conviction_score']}%")
print(f"AI Provider Used: gemini")
```

## What Was Fixed:

### Before (❌ Broken):

The `/api/analyze/simple` endpoint had this hardcoded:

```python
args = {
    "ai_provider": "auto"  # Always ignored your parameter!
}
```

### After (✅ Fixed):

```python
args = {
    "ai_provider": request.ai_provider  # Now uses your parameter!
}
```

Also added the `ai_provider` field to the `SimpleAnalysisRequest` model so it accepts the parameter properly.

## Test It:

Restart your API server and try the Gemini request again:

```bash
# Stop the old server (Ctrl+C)
# Restart it
python3 start_api.py

# Now test with Gemini
curl -X POST "http://localhost:8000/api/analyze/simple" \
     -H "Content-Type: application/json" \
     -d '{"token": "SOL", "chain": "solana", "ai_provider": "gemini"}'
```

You should now see it actually uses Gemini instead of falling back to LM Studio!
