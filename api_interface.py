#!/usr/bin/env python3
"""
API Interface for trader-agent.py
Provides REST API endpoints to execute the trading agent and return data
"""

import os
import json
import subprocess
import asyncio
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn
import sys
import traceback

# Add the current directory to Python path to import trader-agent
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trader_agent_core import TraderAgent

app = FastAPI(
    title="Trader Agent API",
    description="REST API interface for the trading agent analysis script",
    version="1.0.0"
)

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request models
class TradingAnalysisRequest(BaseModel):
    token: str = Field(..., description="Token symbol (e.g., SOL, BTC, ETH)")
    chain: str = Field(default="solana", description="Blockchain network (e.g., solana, ethereum, bsc)")
    mode: str = Field(default="signal", description="Output mode: signal for trade signal, analysis for comprehensive market analysis")
    # Hardcoded to use Gemini API only
    # ai_provider: str = Field(default="gemini", description="AI provider: gemini (Google Gemini API)")
    # lmstudio_url: str = Field(default="http://127.0.0.1:1234", description="Custom LM Studio server URL")

class SimpleAnalysisRequest(BaseModel):
    token: str = Field(..., description="Token symbol (e.g., SOL, BTC, ETH)")
    chain: str = Field(default="solana", description="Blockchain network (e.g., solana, ethereum, bsc)")
    ai_provider: str = Field(default="gemini", description="AI provider: gemini (Google Gemini API)")

# Response models
class TradingSignalResponse(BaseModel):
    success: bool
    action: str
    entry_price: float
    stop_loss: float
    take_profit: float
    conviction_score: int
    strategy_type: str
    reasoning: str
    coin_symbol: str
    current_price: float
    market_data: Dict[str, Any]
    fabio_analysis: Optional[Dict[str, Any]] = None

class ComprehensiveAnalysisResponse(BaseModel):
    success: bool
    analysis: str
    coin_symbol: str
    market_data: Dict[str, Any]

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    traceback: Optional[str] = None

async def run_trader_agent_async(token: str, chain: str, mode: str, provider: str) -> Dict[str, Any]:
    """
    Execute the trader agent asynchronously using the core module.
    """
    try:
        agent = TraderAgent()
        market_data, ohlcv_data = await agent.fetch_data(token, chain)
        
        if "error" in market_data:
            return {"success": False, "error": market_data["error"]}
            
        analysis_result = agent.analyze_market(market_data, ohlcv_data)
        analysis_result["coin_symbol"] = token
        
        if mode == "analysis":
            # For comprehensive analysis, use the AI to generate a report
            analysis_report = await agent.generate_comprehensive_analysis(analysis_result, provider)
            
            if "error" in analysis_report:
                return {"success": False, "error": analysis_report["error"]}
                
            # Return the analysis text
            return {
                "success": True, 
                "output": analysis_report["analysis"],
                "fabio_analysis": analysis_result.get("fabio_analysis")
            }
        else:
            # Signal mode
            signal = await agent.generate_signal(analysis_result, provider)
            return {
                "success": True, 
                "output": json.dumps(signal),
                "fabio_analysis": analysis_result.get("fabio_analysis")
            }
            
    except Exception as e:
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}

def execute_trader_agent(args: Dict[str, str]) -> Dict[str, Any]:
    """
    Execute the trader-agent.py script with the given arguments
    DEPRECATED: Use run_trader_agent_async instead
    """
    try:
        # Build the command
        cmd = [sys.executable, "trader-agent.py"]
        
        # Add arguments
        for key, value in args.items():
            if value is not None:
                cmd.append(f"--{key.replace('_', '-')}")
                cmd.append(str(value))
        
        print(f"Executing command: {' '.join(cmd)}")
        
        # Execute the script
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": f"Script execution failed with return code {result.returncode}",
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        
        # Parse the output - the script prints JSON to stdout
        try:
            # The script outputs various formats, so we need to handle them
            lines = result.stdout.strip().split('\n')
            
            # Look for JSON output (usually at the end)
            for line in reversed(lines):
                line = line.strip()
                if line.startswith('{') and line.endswith('}'):
                    try:
                        return {
                            "success": True,
                            "output": json.loads(line),
                            "raw_output": result.stdout
                        }
                    except json.JSONDecodeError:
                        continue
            
            # If no JSON found, return the raw output
            return {
                "success": True,
                "output": result.stdout,
                "raw_output": result.stdout
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to parse script output: {str(e)}",
                "raw_output": result.stdout,
                "stderr": result.stderr
            }
    
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Script execution timed out after 5 minutes"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to execute script: {str(e)}",
            "traceback": traceback.format_exc()
        }

async def parse_signal_output(output: str, market_data: Dict[str, Any], coin_symbol: str) -> Dict[str, Any]:
    """
    Parse the signal output from the trader agent
    """
    try:
        lines = output.split('\n')
        signal_data = None
        fabio_data = None
        
        # Method 1: Look for JSON data in the output
        for line in lines:
            line = line.strip()
            if line.startswith('{') and line.endswith('}'):
                try:
                    parsed = json.loads(line)
                    if isinstance(parsed, dict):
                        if 'action' in parsed and 'entry_price' in parsed:
                            signal_data = parsed
                        elif 'fabio_valentino_analysis' in parsed:
                            fabio_data = parsed['fabio_valentino_analysis']
                except json.JSONDecodeError:
                    continue
        
        # Method 2: If no JSON found, try to extract from formatted output
        if not signal_data:
            # Look for signal patterns in the text output
            action = None
            entry_price = 0
            stop_loss = 0
            take_profit = 0
            conviction_score = 50
            reasoning = "Extracted from formatted output"
            strategy_type = "extracted"
            
            for line in lines:
                line_lower = line.lower()
                # Look for action keywords
                if 'action:' in line_lower:
                    if 'buy' in line_lower:
                        action = "BUY"
                    elif 'sell' in line_lower:
                        action = "SELL"
                    elif 'hold' in line_lower:
                        action = "HOLD"
                
                # Look for numerical values
                import re
                
                # Extract conviction score
                conviction_match = re.search(r'conviction[:\s]*(\d+)', line_lower)
                if conviction_match:
                    conviction_score = int(conviction_match.group(1))
                
                # Extract price values
                price_matches = re.findall(r'(\d+\.?\d*)', line)
                if len(price_matches) >= 1:
                    if entry_price == 0:
                        entry_price = float(price_matches[0])
                    elif stop_loss == 0 and action == "BUY":
                        stop_loss = float(price_matches[0]) * 0.98  # Estimate 2% stop
                    elif take_profit == 0 and action == "BUY":
                        take_profit = float(price_matches[0]) * 1.02  # Estimate 2% target
            
            if action:
                signal_data = {
                    "action": action,
                    "entry_price": entry_price,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "conviction_score": conviction_score,
                    "strategy_type": strategy_type,
                    "reasoning": reasoning
                }
        
        # If we found signal data, return it
        if signal_data:
            return {
                "success": True,
                "action": signal_data.get("action", "HOLD"),
                "entry_price": float(signal_data.get("entry_price") or 0),
                "stop_loss": float(signal_data.get("stop_loss") or 0),
                "take_profit": float(signal_data.get("take_profit") or 0),
                "conviction_score": int(signal_data.get("conviction_score") or 50),
                "strategy_type": signal_data.get("strategy_type", "extracted"),
                "reasoning": signal_data.get("reasoning", "Data extracted from output"),
                "coin_symbol": coin_symbol,
                "current_price": float(signal_data.get("entry_price") or 0),
                "market_data": market_data,
                "fabio_analysis": fabio_data
            }
        else:
            # No signal data found, return analysis data if available
            if fabio_data:
                return {
                    "success": True,
                    "action": "HOLD",
                    "entry_price": 0,
                    "stop_loss": 0,
                    "take_profit": 0,
                    "conviction_score": 50,
                    "strategy_type": "analysis_only",
                    "reasoning": "Comprehensive analysis completed, no specific signal generated",
                    "coin_symbol": coin_symbol,
                    "current_price": 0,
                    "market_data": market_data,
                    "fabio_analysis": fabio_data
                }
            else:
                # Complete fallback
                return {
                    "success": True,
                    "action": "HOLD",
                    "entry_price": 0,
                    "stop_loss": 0,
                    "take_profit": 0,
                    "conviction_score": 50,
                    "strategy_type": "unknown",
                    "reasoning": "Signal parsing failed, raw output available",
                    "coin_symbol": coin_symbol,
                    "current_price": 0,
                    "market_data": market_data,
                    "fabio_analysis": None,
                    "raw_output": output[:500] + "..." if len(output) > 500 else output  # Include preview of raw output
                }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to parse signal output: {str(e)}",
            "action": "HOLD",
            "entry_price": 0,
            "stop_loss": 0,
            "take_profit": 0,
            "conviction_score": 50,
            "strategy_type": "error",
            "reasoning": f"Parse error: {str(e)}",
            "coin_symbol": coin_symbol,
            "current_price": 0,
            "market_data": market_data
        }

async def parse_analysis_output(output: str, coin_symbol: str) -> Dict[str, Any]:
    """
    Parse the analysis output from the trader agent
    """
    try:
        return {
            "success": True,
            "analysis": output,
            "coin_symbol": coin_symbol,
            "market_data": {}
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to parse analysis output: {str(e)}",
            "analysis": output,
            "coin_symbol": coin_symbol,
            "market_data": {}
        }

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Trader Agent API is running",
        "status": "healthy",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "api_version": "1.0.0",
        "trader_agent_available": os.path.exists("trader-agent.py"),
        "current_directory": os.getcwd()
    }

@app.post("/api/analyze/signal", response_model=TradingSignalResponse)
async def get_trading_signal(request: TradingAnalysisRequest):
    """
    Get a trading signal for a specific token
    """
    try:
        # Prepare arguments for the trader agent (hardcoded to Gemini)
        # args = {
        #     "token": request.token,
        #     "chain": request.chain,
        #     "mode": "signal",
        #     "ai_provider": "gemini"
        # }

        # Execute the trader agent
        # result = execute_trader_agent(args)
        result = await run_trader_agent_async(request.token, request.chain, "signal", "gemini")
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        # Get market data (simplified - you might want to extract this from the output)
        market_data = {"symbol": request.token}
        
        # Parse the output
        parsed_signal = await parse_signal_output(result["output"], market_data, request.token)
        
        if parsed_signal["success"]:
            return parsed_signal
        else:
            raise HTTPException(status_code=500, detail=parsed_signal["error"])
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.post("/api/analyze/comprehensive", response_model=ComprehensiveAnalysisResponse)
async def get_comprehensive_analysis(request: TradingAnalysisRequest):
    """
    Get comprehensive market analysis for a specific token
    """
    try:
        # Prepare arguments for the trader agent (hardcoded to Gemini)
        # args = {
        #     "token": request.token,
        #     "chain": request.chain,
        #     "mode": "analysis",
        #     "ai_provider": "gemini"
        # }

        # Execute the trader agent
        # result = execute_trader_agent(args)
        result = await run_trader_agent_async(request.token, request.chain, "analysis", "gemini")
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        # Parse the analysis output
        parsed_analysis = await parse_analysis_output(result["output"], request.token)
        
        if parsed_analysis["success"]:
            return parsed_analysis
        else:
            raise HTTPException(status_code=500, detail=parsed_analysis["error"])
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
@app.post("/api/analyze/simple")
async def simple_analysis(request: SimpleAnalysisRequest):
    """
    Simple analysis with default parameters (can specify AI provider, signal mode)
    """
    try:
        # Prepare arguments for the trader agent with user-specified or default AI provider
        # args = {
        #     "token": request.token,
        #     "chain": request.chain,
        #     "mode": "signal",
        #     "ai_provider": request.ai_provider
        # }

        
        # Execute the trader agent
        # result = execute_trader_agent(args)
        result = await run_trader_agent_async(request.token, request.chain, "signal", request.ai_provider)
        
        if not result["success"]:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": result["error"]}
            )
        
        # Parse the output
        market_data = {"symbol": request.token}
        parsed_result = await parse_signal_output(result["output"], market_data, request.token)
        
        return JSONResponse(content=parsed_result)
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Unexpected error: {str(e)}"}
        )

@app.get("/api/tokens/supported")
async def get_supported_tokens():
    """
    Get list of supported tokens and networks
    """
    return {
        "supported_tokens": ["SOL", "BTC", "ETH", "BNB", "ADA", "DOT", "MATIC"],
        "supported_chains": ["solana", "ethereum", "bsc", "polygon"],
        "supported_modes": ["signal", "analysis"],
        "supported_ai_providers": ["gemini"],  # LM Studio commented out
        "default_settings": {
            "chain": "solana",
            "mode": "signal",
            "ai_provider": "gemini"  # Hardcoded to Gemini
        },
        "note": "This API now uses Google Gemini API only for AI analysis"
    }

@app.get("/api/example/{token}")
async def get_example_analysis(token: str):
    """
    Get example analysis for a token (demonstration endpoint)
    """
    example_request = TradingAnalysisRequest(
        token=token,
        chain="solana",
        mode="signal",
        ai_provider="auto"
    )
    
    return await get_trading_signal(example_request)

if __name__ == "__main__":
    print("🚀 Starting Trader Agent API Server...")
    print("📊 API Documentation available at: http://localhost:8000/docs")
    uvicorn.run(
        "api_interface:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )