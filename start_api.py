#!/usr/bin/env python3
"""
Simple startup script for the Trader Agent API
"""

import os
import sys
import subprocess
import importlib.util

def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = [
        'fastapi',
        'uvicorn',
        'pydantic'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        if importlib.util.find_spec(package) is None:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing required packages: {', '.join(missing_packages)}")
        print("Please install them using:")
        print(f"pip install -r api_requirements.txt")
        return False
    
    print("✅ All required dependencies are installed")
    return True

def check_trader_agent():
    """Check if trader-agent.py exists"""
    if not os.path.exists("trader-agent.py"):
        print("❌ trader-agent.py not found in the current directory")
        print("Please ensure you're running this script from the correct directory")
        return False
    
    print("✅ trader-agent.py found")
    return True

def main():
    print("🚀 Trader Agent API Startup Check")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Check trader agent
    if not check_trader_agent():
        sys.exit(1)
    
    print("\n✅ All checks passed!")
    print("🚀 Starting API server...")
    print("\n📊 API will be available at:")
    print("   • http://localhost:8000 (API)")
    print("   • http://localhost:8000/docs (Interactive Documentation)")
    print("   • http://localhost:8000/health (Health Check)")
    print("\n🛑 Press Ctrl+C to stop the server")
    
    # Start the API
    try:
        from api_interface import app
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
    except ImportError as e:
        print(f"❌ Error importing API module: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 API server stopped")

if __name__ == "__main__":
    main()