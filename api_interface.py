#!/usr/bin/env python3
"""
API Interface for trader-agent.py
Provides REST API endpoints to execute the trading agent and return data
"""

import os
import json
import asyncio
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn
import sys
import traceback
import logging

# Add the current directory to Python path to import trader-agent
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trader_agent_core import TraderAgent
from backend.config import Config

# Configure logging
logging.basicConfig(level=getattr(logging, Config.LOG_LEVEL))
logger = logging.getLogger("API")

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
            if "error" in signal:
                 return {"success": False, "error": signal["error"]}

            return {
                "success": True, 
                "output": json.dumps(signal),
                "fabio_analysis": analysis_result.get("fabio_analysis")
            }
            
    except Exception as e:
        logger.error(f"Error in run_trader_agent_async: {e}", exc_info=True)
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}

async def parse_signal_output(output: str, market_data: Dict[str, Any], coin_symbol: str) -> Dict[str, Any]:
    """
    Parse the signal output from the trader agent
    """
    try:
        # The output is already a JSON string from run_trader_agent_async
        if isinstance(output, str):
            try:
                signal_data = json.loads(output)
            except json.JSONDecodeError:
                # If it's not JSON, it might be an error message or raw text
                return {
                    "success": False,
                    "error": "Failed to parse signal JSON",
                    "raw_output": output
                }
        else:
            signal_data = output

        return {
            "success": True,
            "action": signal_data.get("action", "HOLD"),
            "entry_price": float(signal_data.get("entry_price") or 0),
            "stop_loss": float(signal_data.get("stop_loss") or 0),
            "take_profit": float(signal_data.get("take_profit") or 0),
            "conviction_score": int(signal_data.get("conviction_score") or 50),
            "strategy_type": signal_data.get("strategy_type", "ai_generated"),
            "reasoning": signal_data.get("reasoning", "No reasoning provided"),
            "coin_symbol": coin_symbol,
            "current_price": float(signal_data.get("entry_price") or 0), # Approximation
            "market_data": market_data,
            "fabio_analysis": signal_data.get("fabio_analysis") # Might be nested
        }
    
    except Exception as e:
        logger.error(f"Error parsing signal output: {e}")
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
        "trader_agent_available": True,
        "current_directory": os.getcwd()
    }

@app.post("/api/analyze/signal", response_model=TradingSignalResponse)
async def get_trading_signal(request: TradingAnalysisRequest):
    """
    Get a trading signal for a specific token
    """
    try:
        result = await run_trader_agent_async(request.token, request.chain, "signal", "gemini")
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        market_data = {"symbol": request.token}
        
        # Parse the output
        parsed_signal = await parse_signal_output(result["output"], market_data, request.token)
        
        # Inject fabio analysis if available separately
        if result.get("fabio_analysis"):
            parsed_signal["fabio_analysis"] = result["fabio_analysis"]

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
        result = await run_trader_agent_async(request.token, request.chain, "signal", request.ai_provider)
        
        if not result["success"]:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": result["error"]}
            )
        
        market_data = {"symbol": request.token}
        parsed_result = await parse_signal_output(result["output"], market_data, request.token)
        
        if result.get("fabio_analysis"):
            parsed_result["fabio_analysis"] = result["fabio_analysis"]
            
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
        "supported_ai_providers": ["gemini"],
        "default_settings": {
            "chain": "solana",
            "mode": "signal",
            "ai_provider": "gemini"
        },
        "note": "This API now uses Google Gemini API only for AI analysis"
    }

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