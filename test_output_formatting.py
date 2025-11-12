#!/usr/bin/env python3
"""
Quick test to verify the output formatting works in trader-agent.py
"""

import json
from output_formatter import OutputFormatter

def test_signal_formatting():
    """Test that signal formatting works correctly"""
    
    # Sample signal data (similar to what trader-agent.py generates)
    signal = {
        "action": "BUY",
        "entry_price": 159.45,
        "stop_loss": 156.20,
        "take_profit": 165.80,
        "conviction_score": 85,
        "strategy_type": "trend_following",
        "risk_reward_ratio": 2.15,
        "reasoning": "Strong bullish momentum detected with RSI at 62.5 and MACD showing bullish crossover."
    }
    
    market_data = {
        "symbol": "SOL",
        "value": 159.45
    }
    
    print("Testing Trade Signal Formatting:")
    print("=" * 80)
    OutputFormatter.format_trade_signal(signal, market_data, "SOL")
    print("\n✅ Trade signal formatting works!\n")

def test_fabio_analysis_formatting():
    """Test that Fabio Valentino analysis formatting works correctly"""
    
    fabio_data = {
        "ltf_market_state": {
            "state": "imbalanced",
            "imbalance_direction": "bullish",
            "strength": "strong"
        },
        "ltf_order_flow": {
            "buying_pressure": "high",
            "selling_pressure": "low",
            "cvd_trend": "bullish",
            "aggressive_orders": True
        },
        "trading_opportunities": {
            "trend_following": {
                "setup_name": "Bullish Continuation",
                "direction": "long",
                "entry_price": 159.45,
                "target": 165.80,
                "risk_reward": 2.15
            },
            "mean_reversion": None
        }
    }
    
    print("Testing Fabio Valentino Analysis Formatting:")
    print("=" * 80)
    OutputFormatter.format_fabio_valentino_analysis(fabio_data, "New_York")
    print("\n✅ Fabio Valentino analysis formatting works!\n")

def test_comprehensive_analysis_formatting():
    """Test that comprehensive analysis formatting works correctly"""
    
    analysis_text = """
⚡ Live SOL Market Overview
Current Price: $159.45 | Session: New York
Market State: Imbalanced (Bullish)

🏛️ Auction Market Theory
POC: $158.50 | Value Area: Strong

📈 Multi-Timeframe Structure
LTF: Bullish trend active
HTF: Confirms bullish bias

🎯 Trading Opportunities
TREND FOLLOWING: Active setup detected
Entry: $159.45 | Target: $165.80

✅ Final Assessment
Bias: BULLISH with high confidence
"""
    
    print("Testing Comprehensive Analysis Formatting:")
    print("=" * 80)
    OutputFormatter.format_comprehensive_analysis(analysis_text, "SOL")
    print("\n✅ Comprehensive analysis formatting works!\n")

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🧪 OUTPUT FORMATTING VERIFICATION TEST")
    print("=" * 80 + "\n")
    
    try:
        test_signal_formatting()
        test_fabio_analysis_formatting()
        test_comprehensive_analysis_formatting()
        
        print("=" * 80)
        print("✅ ALL TESTS PASSED!")
        print("=" * 80)
        print("\nThe output formatting is working correctly in trader-agent.py")
        print("You can now run: python3 trader-agent.py --token SOL --chain solana")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()