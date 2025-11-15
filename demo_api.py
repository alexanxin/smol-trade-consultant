#!/usr/bin/env python3
"""
Demo script showing how to use the Trader Agent API
"""

import requests
import json
import time

API_BASE = "http://localhost:8000"

def demo_simple_analysis():
    """Demo: Get a simple trading signal"""
    print("📊 Demo: Simple Trading Signal")
    print("-" * 40)
    
    payload = {
        "token": "SOL",
        "chain": "solana"
    }
    
    print(f"Token: {payload['token']}")
    print(f"Chain: {payload['chain']}")
    print("Mode: signal (default)")
    print("AI Provider: auto (default)")
    print("\n🔄 Making request...")
    
    try:
        response = requests.post(f"{API_BASE}/api/analyze/simple", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ Response received:")
            print(json.dumps(data, indent=2))
        else:
            print(f"\n❌ Request failed: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")

def demo_custom_analysis():
    """Demo: Get a custom trading signal with specific parameters"""
    print("\n\n🎯 Demo: Custom Trading Signal")
    print("-" * 40)
    
    payload = {
        "token": "BTC",
        "chain": "ethereum",
        "mode": "signal",
        "ai_provider": "auto"
    }
    
    print(f"Token: {payload['token']}")
    print(f"Chain: {payload['chain']}")
    print("Mode: signal")
    print("AI Provider: auto")
    print("⚠️  This will take 30-60 seconds...")
    
    try:
        response = requests.post(f"{API_BASE}/api/analyze/signal", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ Response received:")
            
            # Pretty print key fields
            print(f"Action: {data.get('action', 'N/A')}")
            print(f"Strategy: {data.get('strategy_type', 'N/A')}")
            print(f"Conviction: {data.get('conviction_score', 'N/A')}%")
            print(f"Entry Price: ${data.get('entry_price', 'N/A')}")
            print(f"Stop Loss: ${data.get('stop_loss', 'N/A')}")
            print(f"Take Profit: ${data.get('take_profit', 'N/A')}")
            print(f"Reasoning: {data.get('reasoning', 'N/A')[:100]}...")
            
            if 'fabio_analysis' in data and data['fabio_analysis']:
                print("✅ Fabio Valentino analysis included!")
            
        else:
            print(f"\n❌ Request failed: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")

def demo_comprehensive_analysis():
    """Demo: Get comprehensive market analysis"""
    print("\n\n📈 Demo: Comprehensive Market Analysis")
    print("-" * 40)
    
    payload = {
        "token": "ETH",
        "chain": "ethereum",
        "mode": "analysis",
        "ai_provider": "auto"
    }
    
    print(f"Token: {payload['token']}")
    print(f"Chain: {payload['chain']}")
    print("Mode: analysis (comprehensive)")
    print("AI Provider: auto")
    print("⚠️  This will take 60-120 seconds...")
    
    try:
        response = requests.post(f"{API_BASE}/api/analyze/comprehensive", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ Response received:")
            print(f"Coin: {data.get('coin_symbol', 'N/A')}")
            print(f"Analysis length: {len(data.get('analysis', ''))} characters")
            
            # Show first 200 characters of analysis
            analysis = data.get('analysis', '')
            if analysis:
                print(f"\nFirst 200 characters of analysis:")
                print("-" * 40)
                print(analysis[:200] + "..." if len(analysis) > 200 else analysis)
            
        else:
            print(f"\n❌ Request failed: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")

def demo_supported_info():
    """Demo: Get supported tokens and configurations"""
    print("\n\nℹ️  Demo: Supported Tokens & Configurations")
    print("-" * 40)
    
    try:
        response = requests.get(f"{API_BASE}/api/tokens/supported")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Supported information:")
            print(json.dumps(data, indent=2))
        else:
            print(f"❌ Request failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    """Run all demos"""
    print("🚀 Trader Agent API Demo")
    print("=" * 50)
    print("This demo shows how to use the API interface.")
    print("Make sure the API server is running first!")
    print("Start it with: python start_api.py")
    print("=" * 50)
    
    # Check if API is running
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        if response.status_code != 200:
            print("❌ API server is not responding")
            print("Please start the API server first!")
            return
    except requests.exceptions.RequestException:
        print("❌ API server is not running")
        print("Please start the API server with: python start_api.py")
        return
    
    print("✅ API server is running!\n")
    
    # Run demos
    demos = [
        demo_supported_info,
        demo_simple_analysis,
        demo_custom_analysis,
        demo_comprehensive_analysis
    ]
    
    for demo in demos:
        try:
            demo()
            input("\nPress Enter to continue to next demo...")
        except KeyboardInterrupt:
            print("\n👋 Demo interrupted by user")
            break
        except Exception as e:
            print(f"\n❌ Demo failed: {e}")
            continue
    
    print("\n🎉 Demo completed!")

if __name__ == "__main__":
    main()