#!/usr/bin/env python3
"""
Test script to verify Gemini Web API integration
"""
import os
import asyncio
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("❌ GEMINI_API_KEY not found")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)

def test_sync_call():
    """Test synchronous Gemini API call"""
    print("🧪 Testing synchronous Gemini Web API call...")
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content("Generate a JSON object with keys: action (BUY/SELL/HOLD), conviction_score (0-100), reasoning (brief). Make it a trading signal for Bitcoin.")
        
        if response and response.text:
            print("✅ Synchronous call successful!")
            print(f"Response length: {len(response.text)} characters")
            print(f"Response preview: {response.text[:200]}...")
            return True
        else:
            print("❌ Empty response")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def test_async_call():
    """Test asynchronous Gemini API call using asyncio.to_thread"""
    print("\n🧪 Testing asynchronous Gemini Web API call...")
    try:
        def _generate():
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content("Generate a JSON object with keys: action, conviction_score, reasoning. Trading signal for Ethereum.")
            return response.text if response and response.text else None
        
        response_text = await asyncio.to_thread(_generate)
        
        if response_text:
            print("✅ Asynchronous call successful!")
            print(f"Response length: {len(response_text)} characters")
            print(f"Response preview: {response_text[:200]}...")
            return True
        else:
            print("❌ Empty response")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def main():
    print("=" * 60)
    print("Gemini Web API Integration Test")
    print("=" * 60)
    
    # Test 1: Synchronous call
    sync_result = test_sync_call()
    
    # Test 2: Asynchronous call
    async_result = await test_async_call()
    
    print("\n" + "=" * 60)
    print("Test Results:")
    print(f"  Synchronous call: {'✅ PASS' if sync_result else '❌ FAIL'}")
    print(f"  Asynchronous call: {'✅ PASS' if async_result else '❌ FAIL'}")
    print("=" * 60)
    
    if sync_result and async_result:
        print("\n🎉 All tests passed! Gemini Web API is working correctly.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
