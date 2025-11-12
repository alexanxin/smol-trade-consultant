#!/usr/bin/env python3
"""
Test simple Qwen CLI call to debug the hang issue
"""
import subprocess
import sys

def test_simple_qwen():
    """Test simple Qwen CLI call"""
    
    print("Testing simple Qwen CLI call...")
    
    # Very simple prompt
    prompt = "SOL price: $160, RSI: 60. Recommend: BUY, SELL, or HOLD?"
    
    cmd = ['qwen', '--output-format', 'text', prompt]
    
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)  # 30 second timeout
        
        print(f"Return code: {result.returncode}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        
    except subprocess.TimeoutExpired:
        print("❌ Command timed out after 30 seconds")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_simple_qwen()