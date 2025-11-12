#!/usr/bin/env python3
"""
Test the corrected Qwen CLI integration for trading analysis
"""
import subprocess
import json

def call_qwen_cli(prompt: str, system_prompt: str = None) -> str:
    """Call Qwen CLI with the given prompt and return the response."""
    
    try:
        # Build the command for Qwen Code CLI
        cmd = ['qwen', '--output-format', 'json']
        
        # Handle system prompt by prepending it to the prompt
        if system_prompt:
            full_prompt = f"INSTRUCTION: {system_prompt}\n\nQUERY: {prompt}"
        else:
            full_prompt = prompt
        
        # Add the prompt as positional argument
        cmd.append(full_prompt)
        
        # Run the command
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            # Parse JSON response
            try:
                response_json = json.loads(result.stdout)
                if 'response' in response_json:
                    return response_json['response']
                else:
                    return result.stdout.strip()
            except json.JSONDecodeError:
                # If JSON parsing fails, return raw output
                return result.stdout.strip()
        else:
            print(f"❌ Qwen CLI error: {result.stderr}")
            return f"Error: {result.stderr}"
            
    except subprocess.TimeoutExpired:
        print("❌ Qwen CLI timeout")
        return "Error: Request timeout"
    except Exception as e:
        print(f"❌ Error calling Qwen CLI: {e}")
        return f"Error: {e}"

def test_trading_analysis():
    """Test trading analysis with Qwen CLI"""
    
    print("=== Testing Trading Analysis with Qwen CLI ===")
    
    # Test simple trading query
    system_prompt = "You are a professional trading analyst. Provide clear, concise analysis."
    user_prompt = "SOL price at $150, RSI at 65, Volume 50% above average. What's your analysis?"
    
    print(f"System: {system_prompt}")
    print(f"Query: {user_prompt}")
    print("-" * 60)
    
    response = call_qwen_cli(user_prompt, system_prompt)
    print(f"Response: {response}")
    print("-" * 60)

if __name__ == "__main__":
    test_trading_analysis()