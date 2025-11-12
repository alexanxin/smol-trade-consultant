#!/usr/bin/env python3
"""
Simple test script to understand Qwen CLI command syntax
"""
import subprocess

def test_qwen_basic():
    """Test basic Qwen CLI functionality"""
    print("Testing basic Qwen CLI...")
    
    # Test 1: Simple query
    cmd = ['qwen', 'Hello world']
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        print(f"Test 1 - Basic query:")
        print(f"Command: {' '.join(cmd)}")
        print(f"Return code: {result.returncode}")
        print(f"STDOUT: {result.stdout[:200]}...")
        print(f"STDERR: {result.stderr[:200]}...")
        print("-" * 50)
    except Exception as e:
        print(f"Test 1 failed: {e}")
        print("-" * 50)

def test_qwen_with_prompt_flag():
    """Test Qwen CLI with --prompt flag"""
    print("Testing Qwen CLI with --prompt flag...")
    
    cmd = ['qwen', '--prompt', 'Hello world']
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        print(f"Test 2 - With --prompt flag:")
        print(f"Command: {' '.join(cmd)}")
        print(f"Return code: {result.returncode}")
        print(f"STDOUT: {result.stdout[:200]}...")
        print(f"STDERR: {result.stderr[:200]}...")
        print("-" * 50)
    except Exception as e:
        print(f"Test 2 failed: {e}")
        print("-" * 50)

def test_qwen_with_output_format():
    """Test Qwen CLI with different output formats"""
    print("Testing Qwen CLI with output formats...")
    
    # Test text output
    cmd = ['qwen', '--output-format', 'text', 'Hello']
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        print(f"Test 3a - Text output:")
        print(f"Command: {' '.join(cmd)}")
        print(f"Return code: {result.returncode}")
        print(f"STDOUT: {result.stdout[:200]}...")
        print(f"STDERR: {result.stderr[:200]}...")
        print("-" * 50)
    except Exception as e:
        print(f"Test 3a failed: {e}")
        print("-" * 50)
    
    # Test JSON output
    cmd = ['qwen', '--output-format', 'json', 'Hello']
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        print(f"Test 3b - JSON output:")
        print(f"Command: {' '.join(cmd)}")
        print(f"Return code: {result.returncode}")
        print(f"STDOUT: {result.stdout[:200]}...")
        print(f"STDERR: {result.stderr[:200]}...")
        print("-" * 50)
    except Exception as e:
        print(f"Test 3b failed: {e}")
        print("-" * 50)

def test_qwen_interactive_mode():
    """Test Qwen CLI interactive mode"""
    print("Testing Qwen CLI interactive mode...")
    
    cmd = ['qwen', '--prompt-interactive', 'Hello']
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        print(f"Test 4 - Interactive mode:")
        print(f"Command: {' '.join(cmd)}")
        print(f"Return code: {result.returncode}")
        print(f"STDOUT: {result.stdout[:200]}...")
        print(f"STDERR: {result.stderr[:200]}...")
        print("-" * 50)
    except Exception as e:
        print(f"Test 4 failed: {e}")
        print("-" * 50)

if __name__ == "__main__":
    print("=== Qwen CLI Testing ===")
    test_qwen_basic()
    test_qwen_with_prompt_flag()
    test_qwen_with_output_format()
    test_qwen_interactive_mode()
    print("=== End of Tests ===")