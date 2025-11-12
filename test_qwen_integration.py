#!/usr/bin/env python3
"""
Test Qwen CLI integration in trading agent context
"""
import subprocess
import json
import sys

def test_generate_trade_signal():
    """Test the generate_trade_signal function with mock data"""
    
    print("=== Testing generate_trade_signal with Qwen CLI ===")
    
    # Mock analysis data
    mock_analysis_data = {
        "current_price": 160.30,
        "RSI_14": 61.1,
        "price_change_1h_pct": 0.24,
        "market_structure": {
            "momentum_direction": "neutral"
        }
    }
    
    analysis_json_string = json.dumps(mock_analysis_data)
    
    # Call Qwen CLI with system prompt for trading
    system_prompt = (
        "You are a professional Smart Money Concepts (SMC) trading agent. "
        "Analyze the provided JSON market data and generate a trade signal. "
        "Return ONLY a JSON object with keys: action (BUY/SELL/HOLD), entry_price, stop_loss, take_profit, conviction_score (1-100), and reasoning."
    )
    
    user_prompt = f"Analyze this market data and provide a trade signal: {analysis_json_string}"
    
    try:
        cmd = ['qwen', '--output-format', 'json']
        
        # Combine system and user prompts
        full_prompt = f"INSTRUCTION: {system_prompt}\n\nQUERY: {user_prompt}"
        cmd.append(full_prompt)
        
        print(f"Executing: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print(f"Raw output: {result.stdout[:500]}...")
            
            # Try to parse JSON response
            try:
                response_json = json.loads(result.stdout)
                if 'response' in response_json:
                    response_text = response_json['response']
                    print(f"Response text: {response_text}")
                    
                    # Try to parse the trading signal from response text
                    try:
                        signal_json = json.loads(response_text)
                        print("✅ Successfully generated trading signal:")
                        print(f"Action: {signal_json.get('action', 'N/A')}")
                        print(f"Entry: ${signal_json.get('entry_price', 'N/A')}")
                        print(f"Stop Loss: ${signal_json.get('stop_loss', 'N/A')}")
                        print(f"Take Profit: ${signal_json.get('take_profit', 'N/A')}")
                        print(f"Conviction: {signal_json.get('conviction_score', 'N/A')}%")
                        print(f"Reasoning: {signal_json.get('reasoning', 'N/A')}")
                    except json.JSONDecodeError:
                        print(f"✅ Response received but not valid JSON: {response_text}")
                else:
                    print(f"❌ No 'response' field in JSON: {response_json}")
            except json.JSONDecodeError:
                print(f"❌ Failed to parse JSON response: {result.stdout[:200]}")
        else:
            print(f"❌ Command failed with return code {result.returncode}")
            print(f"STDERR: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_generate_trade_signal()