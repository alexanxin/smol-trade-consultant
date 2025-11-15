#!/usr/bin/env python3
"""
Test script for the API interface
"""

import requests
import json
import time

API_BASE = "http://localhost:8000"

def test_health_check():
    """Test the health check endpoint"""
    print("🏥 Testing Health Check...")
    try:
        response = requests.get(f"{API_BASE}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data['status']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_supported_tokens():
    """Test the supported tokens endpoint"""
    print("\n🎯 Testing Supported Tokens...")
    try:
        response = requests.get(f"{API_BASE}/api/tokens/supported")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Supported tokens: {data['supported_tokens']}")
            print(f"✅ Supported chains: {data['supported_chains']}")
            return True
        else:
            print(f"❌ Supported tokens failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Supported tokens error: {e}")
        return False

def test_simple_analysis():
    """Test the simple analysis endpoint"""
    print("\n📊 Testing Simple Analysis...")
    try:
        payload = {
            "token": "SOL",
            "chain": "solana"
        }
        
        print(f"🔄 Making request for {payload['token']} on {payload['chain']}...")
        response = requests.post(f"{API_BASE}/api/analyze/simple", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Analysis successful!")
            print(f"   Action: {data.get('action', 'N/A')}")
            print(f"   Conviction: {data.get('conviction_score', 'N/A')}%")
            print(f"   Entry Price: {data.get('entry_price', 'N/A')}")
            return True
        else:
            print(f"❌ Analysis failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {error_data.get('error', 'Unknown error')}")
            except:
                print(f"   Raw response: {response.text[:200]}...")
            return False
    except Exception as e:
        print(f"❌ Analysis error: {e}")
        return False

def test_signal_analysis():
    """Test the full signal analysis endpoint"""
    print("\n🎯 Testing Signal Analysis...")
    try:
        payload = {
            "token": "BTC",
            "chain": "ethereum",
            "mode": "signal",
            "ai_provider": "auto"
        }
        
        print(f"🔄 Making request for {payload['token']} on {payload['chain']}...")
        print("⏳ This may take 30-60 seconds...")
        
        response = requests.post(f"{API_BASE}/api/analyze/signal", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Signal analysis successful!")
            print(f"   Action: {data.get('action', 'N/A')}")
            print(f"   Strategy: {data.get('strategy_type', 'N/A')}")
            print(f"   Conviction: {data.get('conviction_score', 'N/A')}%")
            print(f"   Entry: {data.get('entry_price', 'N/A')}")
            print(f"   Stop Loss: {data.get('stop_loss', 'N/A')}")
            print(f"   Take Profit: {data.get('take_profit', 'N/A')}")
            print(f"   Reasoning: {data.get('reasoning', 'N/A')[:100]}...")
            return True
        else:
            print(f"❌ Signal analysis failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {error_data.get('error', 'Unknown error')}")
            except:
                print(f"   Raw response: {response.text[:200]}...")
            return False
    except Exception as e:
        print(f"❌ Signal analysis error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 API Interface Test Suite")
    print("=" * 50)
    
    # Check if API is running
    print("🔍 Checking if API server is running...")
    try:
        response = requests.get(f"{API_BASE}/", timeout=5)
        if response.status_code != 200:
            print("❌ API server is not responding properly")
            print("Please start the API server using: python start_api.py")
            return
    except requests.exceptions.RequestException:
        print("❌ API server is not running")
        print("Please start the API server using: python start_api.py")
        return
    
    print("✅ API server is running!\n")
    
    # Run tests
    tests = [
        test_health_check,
        test_supported_tokens,
        test_simple_analysis,
        test_signal_analysis
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    main()