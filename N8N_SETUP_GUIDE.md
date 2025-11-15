# N8N Integration Setup Guide

## Overview

This guide will help you set up n8n on your server to run the trading agent script and expose it via a webhook for your browser-based frontend.

## Prerequisites

1. **Server with n8n installed**

   ```bash
   npm install -g n8n
   n8n start
   # Access at: http://your-server:5678
   ```

2. **Python environment on the server**

   - Copy `trader-agent.py` and dependencies
   - Install Python requirements: `pip install -r requirements.txt`
   - Copy `.env` file with API keys

3. **Project files accessible**
   - `frontend/src/lib/trader-agent-clean.py`
   - `.env` file with required API keys

## Step 1: Import the Workflow Template

1. Open n8n in your browser (http://your-server:5678)
2. Click "Import from File"
3. Select `n8n-workflow-template.json` from your project root
4. The workflow will be imported with the following nodes:

## Step 2: Workflow Configuration

### Webhook Node

- **HTTP Method**: POST
- **Path**: `trading-analysis`
- **Response Mode**: "Last node"
- **Authentication**: None (add if needed for production)

### Extract Parameters Function Node

- Extracts `token` and `chain` from request body
- Defaults to `"SOL"` token and `"solana"` chain

### Execute Script Command Node

- **Command**:
  ```bash
  cd /path/to/your/project && python3 frontend/src/lib/trader-agent-clean.py {{ $node["Extract Parameters"].json.token }} {{ $node["Extract Parameters"].json.chain }}
  ```
- **Replace `/path/to/your/project`** with your actual project directory path
- **Working Directory**: `/path/to/your/project`

### Parse JSON Response Function Node

- Parses the Python script JSON output
- Provides fallback error response if parsing fails

### Return Response Function Node

- Returns the parsed data to the client

## Step 3: Environment Setup on Server

1. **Copy project files to server**:

   ```bash
   # Upload these files to your server
   - trader-agent.py
   - requirements.txt
   - .env (with API keys)
   - frontend/src/lib/trader-agent-clean.py
   ```

2. **Install Python dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   ```bash
   # Make sure .env file is accessible and contains:
   BIRDEYE_API_KEY=your_birdeye_key
   COINGECKO_API_KEY=your_coingecko_key
   GEMINI_API_KEY=your_gemini_key
   ```

## Step 4: Test the Workflow

1. **Activate the workflow** in n8n
2. **Test with curl**:
   ```bash
   curl -X POST http://your-server:5678/webhook/trading-analysis \
        -H "Content-Type: application/json" \
        -d '{"token": "SOL", "chain": "solana"}'
   ```
3. **Expected response**: JSON with trading analysis data

## Step 5: Webhook URL

After setting up, your webhook URL will be:

```
http://your-server:5678/webhook/trading-analysis
```

Copy this URL for use in your frontend configuration.

## Step 6: Security Considerations (Production)

1. **Add authentication** to webhook
2. **Use HTTPS** (set up SSL)
3. **Rate limiting** for API protection
4. **Monitor execution logs**
5. **Set up environment variable management**

## Step 7: Frontend Update

Update your frontend to use the new webhook URL instead of `/api/analyze`.

See the `FRONTEND_UPDATE.md` file for implementation details.

## Troubleshooting

1. **"Command not found" errors**: Check Python path and working directory
2. **API key errors**: Verify .env file accessibility
3. **Timeout errors**: Script execution might take longer than expected
4. **JSON parsing errors**: Check Python script output format

## Alternative: Docker Deployment

For easier deployment, consider running n8n in Docker with your project volume mounted.

```bash
docker run -d \
  -p 5678:5678 \
  -v /path/to/project:/data \
  -e N8N_PORT=5678 \
  --name n8n-trading \
  n8nio/n8n:latest
```
