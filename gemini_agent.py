"""
=== GEMINI API TRADING AGENT ===

This module contains Gemini API-specific functionality for trading analysis.
No fallback to other AI providers - pure Gemini integration.

Requirements:
- pip install google-generativeai

Usage:
python gemini_agent.py --token SOL --chain solana
"""
import os
import json
import argparse
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import required libraries - try multiple import methods for Google AI
try:
    # Newer Google AI SDK
    import google.ai.generativelanguage as genai
    print("✅ Using google.ai.generativelanguage")
    USING_NEW_SDK = True
except ImportError:
    try:
        # Legacy Google Generative AI SDK
        import google.generativeai as genai
        print("✅ Using google.generativeai")
        USING_NEW_SDK = False
    except ImportError:
        print("Error: Google AI library not installed.")
        print("Install with: pip install google-generativeai")
        exit(1)

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def check_gemini_setup():
    """Check if Gemini API is properly configured."""
    if not GEMINI_API_KEY or GEMINI_API_KEY == "REPLACE_WITH_YOUR_GEMINI_KEY":
        print("❌ ERROR: Gemini API key is missing or not set properly.")
        print("💡 Please set GEMINI_API_KEY in your .env file")
        return False
    return True

def configure_gemini():
    """Configure Gemini API with the provided key."""
    try:
        if USING_NEW_SDK:
            # Configure using the newer SDK
            genai.configure(api_key=GEMINI_API_KEY)
        else:
            # Configure using the legacy SDK
            genai.configure(api_key=GEMINI_API_KEY)
        return True
    except Exception as e:
        print(f"❌ Error configuring Gemini API: {e}")
        return False

def call_gemini_analysis(prompt: str, system_prompt: str = None) -> str:
    """Call Gemini API for trading analysis."""
    try:
        # Combine system and user prompts
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        
        if USING_NEW_SDK:
            # Use newer SDK structure
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(full_prompt)
        else:
            # Use legacy SDK structure
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(full_prompt)
        
        return response.text
        
    except Exception as e:
        print(f"❌ Error calling Gemini API: {e}")
        return f"Error: {e}"

def generate_gemini_trade_signal(analysis_data: dict) -> dict:
    """Generate trade signal using Gemini API."""
    
    # Extract essential data
    current_price = analysis_data.get("current_price", 0)
    rsi = analysis_data.get("RSI_14", 50)
    price_change_1h = analysis_data.get("price_change_1h_pct", 0)
    macd_signal = analysis_data.get("MACD_signal_cross", "Neutral")
    htf_trend = analysis_data.get("htf_trend", "Unknown")
    coin_symbol = analysis_data.get("coin_symbol", "SOL")
    
    # Create system prompt for Gemini
    system_prompt = f"""
    You are a professional cryptocurrency trading analyst using Google Gemini AI.
    
    Analyze the provided market data for {coin_symbol} and provide a high-quality trading signal.
    
    Focus on:
    - Technical analysis using RSI, MACD, and price action
    - Market structure and trend analysis
    - Volume and momentum indicators
    - Risk management and position sizing
    
    Provide your response in the following format:
    ACTION: [BUY/SELL/HOLD]
    ENTRY: [price]
    STOP_LOSS: [price]
    TAKE_PROFIT: [price]
    CONVICTION: [score from 1-100]
    REASONING: [detailed explanation]
    """
    
    # Create user prompt with market data
    user_prompt = f"""
    Current Market Data for {coin_symbol}:
    - Current Price: ${current_price}
    - 1H Price Change: {price_change_1h}%
    - RSI (14): {rsi}
    - MACD Signal: {macd_signal}
    - HTF Trend: {htf_trend}
    
    Please analyze this data and provide a trading signal with entry, stop loss, take profit, and conviction level.
    """
    
    # Call Gemini API
    print("🤖 Using Gemini API for analysis...")
    response = call_gemini_analysis(user_prompt, system_prompt)
    
    if response.startswith("Error:"):
        return {
            "action": "HOLD",
            "entry_price": round(current_price, 4),
            "stop_loss": round(current_price * 0.98, 4),
            "take_profit": round(current_price * 1.03, 4),
            "conviction_score": 50,
            "reasoning": f"Gemini API Error: {response}"
        }
    
    # Parse response
    try:
        lines = response.split('\n')
        action = "HOLD"
        entry_price = current_price
        stop_loss = current_price * 0.98
        take_profit = current_price * 1.03
        conviction_score = 70
        reasoning = response
        
        for line in lines:
            line = line.strip().upper()
            if line.startswith("ACTION:"):
                action_text = line.split(":", 1)[1].strip()
                if "BUY" in action_text:
                    action = "BUY"
                elif "SELL" in action_text:
                    action = "SELL"
            elif line.startswith("ENTRY:"):
                try:
                    entry_price = float(line.split(":", 1)[1].strip().replace("$", ""))
                except:
                    pass
            elif line.startswith("STOP_LOSS:"):
                try:
                    stop_loss = float(line.split(":", 1)[1].strip().replace("$", ""))
                except:
                    pass
            elif line.startswith("TAKE_PROFIT:"):
                try:
                    take_profit = float(line.split(":", 1)[1].strip().replace("$", ""))
                except:
                    pass
            elif line.startswith("CONVICTION:"):
                try:
                    conviction_score = int(line.split(":", 1)[1].strip().replace("%", ""))
                except:
                    pass
        
        return {
            "action": action,
            "entry_price": round(entry_price, 4),
            "stop_loss": round(stop_loss, 4),
            "take_profit": round(take_profit, 4),
            "conviction_score": conviction_score,
            "reasoning": f"Gemini Analysis: {reasoning}"
        }
        
    except Exception as e:
        print(f"⚠️  Error parsing Gemini response: {e}")
        return {
            "action": "HOLD",
            "entry_price": round(current_price, 4),
            "stop_loss": round(current_price * 0.98, 4),
            "take_profit": round(current_price * 1.03, 4),
            "conviction_score": 50,
            "reasoning": f"Parsing Error: {response}"
        }

def main():
    """Main execution function for Gemini trading agent."""
    parser = argparse.ArgumentParser(description='Run Gemini Trading Agent')
    parser.add_argument('--token', type=str, default='SOL', help='Token symbol (e.g., SOL, BTC, ETH)')
    parser.add_argument('--chain', type=str, default='solana', help='Blockchain network (e.g., solana, ethereum, bsc)')
    
    args = parser.parse_args()
    
    # Check Gemini setup
    if not check_gemini_setup():
        return
    
    # Configure Gemini
    if not configure_gemini():
        return
    
    print(f"🚀 Starting Gemini Trading Agent for {args.token} on {args.chain}...")
    print(f"🔑 Using Gemini API: {GEMINI_API_KEY[:10]}...")
    
    # For demo purposes, create sample market data
    # In a real implementation, you would fetch this from APIs
    sample_data = {
        "coin_symbol": args.token,
        "current_price": 159.45,
        "RSI_14": 55.2,
        "price_change_1h_pct": 1.2,
        "MACD_signal_cross": "Bullish Crossover",
        "htf_trend": "Bullish"
    }
    
    # Generate signal
    signal = generate_gemini_trade_signal(sample_data)
    
    # Output result
    print("\n" + "="*60)
    print("    🤖 GEMINI AI TRADING SIGNAL")
    print("="*60)
    print(f"   COIN: {args.token}")
    print(f"   ACTION: {signal['action']}")
    print(f"   ENTRY PRICE: ${signal['entry_price']}")
    print(f"   STOP LOSS: ${signal['stop_loss']}")
    print(f"   TAKE PROFIT: ${signal['take_profit']}")
    print(f"   CONVICTION: {signal['conviction_score']}%")
    print("-" * 60)
    print(f"   REASONING: {signal['reasoning']}")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()