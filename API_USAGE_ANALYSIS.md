# API Usage Analysis - Management Mode

## Management Mode API Calls

When an active trade is found, the agent enters **Management Mode** and makes the following API calls **every 60 seconds**:

### Per Cycle (Every 60s):
1. **Birdeye API** - 1 call
   - Endpoint: `/defi/price`
   - Purpose: Get current price of the active trade's token
   - Rate Limit: **Free tier = 150 requests/minute**

### Total: 1 API call per 60 seconds = **60 calls/hour**

---

## Scanning Mode API Calls

When NO active trade exists, the agent runs a full analysis cycle:

### Per Cycle (Every 5 minutes = 300s):
1. **Birdeye API** - 1 call
   - Get token address lookup
   
2. **Birdeye API** - 1 call  
   - Get current market data (price + liquidity)
   
3. **CoinGecko API** - 1 call
   - Get top pool for the token
   
4. **CoinGecko API** - 3 calls
   - OHLCV data for 3 timeframes (5m, 1h, daily)
   
5. **News API** - 1 call (via feedparser)
   - Fetch recent news for the token
   
6. **Gemini AI** - 2-3 calls
   - Strategy agent (signal generation)
   - Risk manager (signal validation)
   - Potentially 1-2 more if debate loop triggers

### Total: ~9-12 API calls per 5 minutes = **108-144 calls/hour**

---

## Rate Limits

### Birdeye (Free Tier)
- **Limit**: 150 requests/minute
- **Management Mode**: 1 req/min ✅ Safe
- **Scanning Mode**: ~2 req/5min ✅ Safe
- **Risk**: Very Low

### CoinGecko (Free Tier)  
- **Limit**: 10-30 calls/minute (varies)
- **Management Mode**: 0 req/min ✅ Safe
- **Scanning Mode**: ~4 req/5min ✅ Safe
- **Risk**: Low

### Gemini AI
- **Limit**: Depends on your plan
- **Free tier**: 15 RPM (requests per minute)
- **Management Mode**: 0 req/min ✅ Safe
- **Scanning Mode**: ~2-3 req/5min ✅ Safe
- **Risk**: Low (well within limits)

### Jupiter API (Lite)
- **Limit**: No official limit published, but generous
- **Usage**: Only when executing trades (not in loops)
- **Risk**: Very Low

### Helius RPC
- **Limit**: Free tier = 100 requests/second
- **Usage**: Only when sending transactions
- **Risk**: Very Low

---

## Recommendations

### ✅ Current Configuration is Safe
Your current setup with:
- **Management Mode**: 60s interval
- **Scanning Mode**: 300s (5min) interval

Is well within all API limits.

### 🔧 If You Want to Be Extra Conservative

You can increase the intervals:

```python
# In trader-agent.py, around line 2196
if args.loop:
    print(f"💤 Sleeping for 60s (Management Mode)...")
    time.sleep(60)  # Change to 120 or 180 for less frequent checks
```

```python
# Around line 2449
if args.loop:
    print(f"💤 Sleeping for {args.interval}s...")
    time.sleep(args.interval)  # Default is 300s, can increase to 600s
```

### 📊 Estimated Monthly Usage

**Scenario: 1 active trade per day, running 24/7**

- Management mode (1 hour/day): 60 calls
- Scanning mode (23 hours/day): ~2,760 calls
- **Total per day**: ~2,820 API calls
- **Total per month**: ~84,600 API calls

All well within free tier limits!

### ⚠️ Only Risk: Gemini AI

If you're on Gemini's free tier (15 RPM), the debate loop could potentially trigger multiple rapid calls. To mitigate:

1. The agent already has a 5-minute interval between scans
2. Debate loop is limited to 3 retries max
3. Each retry happens sequentially, not in parallel

**Verdict**: You're safe! The current configuration is well-optimized for free-tier API limits.
