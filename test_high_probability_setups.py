#!/usr/bin/env python3
"""
Test script to demonstrate high-probability setup detection
"""

import json
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the function from trader-agent.py
exec(open('trader-agent.py').read())
detect_high_probability_setups = locals()['detect_high_probability_setups']

# Sample data representing different market conditions
sample_market_data = {
    "fabio_valentino_analysis": {
        "ltf_market_state": {
            "state": "imbalanced",
            "imbalance_direction": "bullish",
            "strength": "strong",
            "balance_center": 150.0,
            "balance_high": 155.0,
            "balance_low": 145.0
        },
        "htf_market_state": {
            "imbalance_direction": "bullish"
        },
        "ltf_order_flow": {
            "aggressive_orders": True,
            "cvd_trend": "bullish",
            "buying_pressure": "high",
            "selling_pressure": "low"
        }
    },
    "current_trading_session": "New_York",
    "current_price": 153.0,
    "RSI_14": 45.0,
    "MACD_signal_cross": "Bullish Crossover",
    "ltf_candlestick_patterns": [
        {
            "pattern_type": "bullish_engulfing",
            "strength": "high",
            "price": 152.5
        },
        {
            "pattern_type": "outside_bar", 
            "strength": "high",
            "price": 152.8
        }
    ],
    "ltf_volume_profile": {
        "poc_price": 152.5,
        "low_volume_nodes": [
            {"price": 151.0, "volume": 1000, "strength": "low"},
            {"price": 154.0, "volume": 1200, "strength": "low"}
        ]
    },
    "ltf_fair_value_gaps": [
        {
            "type": "bullish",
            "zone": [151.5, 152.0]
        }
    ],
    "ltf_volume_analytics": {
        "volume_spike_detected": True
    }
}

def test_high_probability_setup_detection():
    """Test the high-probability setup detection system"""
    
    print("🔍 TESTING HIGH-PROBABILITY SETUP DETECTION")
    print("=" * 80)
    
    # Test different scenarios
    scenarios = [
        {
            "name": "🚀 TREND FOLLOWING SCENARIO",
            "description": "Imbalanced bullish market with aggressive orders",
            "data": sample_market_data
        },
        {
            "name": "⚖️ MEAN REVERSION SCENARIO", 
            "description": "Balanced market with deep discount",
            "data": {
                **sample_market_data,
                "fabio_valentino_analysis": {
                    **sample_market_data["fabio_valentino_analysis"],
                    "ltf_market_state": {
                        **sample_market_data["fabio_valentino_analysis"]["ltf_market_state"],
                        "state": "balanced",
                        "imbalance_direction": None
                    }
                },
                "current_price": 147.0,  # Deep discount
                "RSI_14": 28.0,  # Oversold
                "current_trading_session": "London"
            }
        }
    ]
    
    for scenario in scenarios:
        print(f"\n{scenario['name']}")
        print(f"📝 {scenario['description']}")
        print("-" * 60)
        
        # Detect high-probability setups
        setups = detect_high_probability_setups(scenario['data'])
        
        if setups:
            print(f"✅ {len(setups)} HIGH-PROBABILITY SETUP(S) DETECTED:")
            print()
            
            for i, setup in enumerate(setups, 1):
                probability_icon = "🔥" if setup.get("probability", 0) >= 80 else "⭐" if setup.get("probability", 0) >= 60 else "⚡"
                direction_icon = "📈" if setup.get("direction") in ["bullish", "long"] else "📉" if setup.get("direction") in ["bearish", "short"] else "⚖️"
                
                print(f"{i}. {probability_icon} {setup.get('setup_type', 'Unknown')} - {setup.get('confidence_level', 'MEDIUM')} PROBABILITY")
                print(f"   {direction_icon} Direction: {setup.get('direction', 'N/A').title()}")
                print(f"   📊 Probability: {setup.get('probability', 0)}%")
                print(f"   🎯 Entry: {setup.get('entry_criteria', 'N/A')}")
                print(f"   🏆 Target: {setup.get('target', 'N/A')}")
                print(f"   ⚙️ Session: {setup.get('session_optimization', 'N/A')}")
                print(f"   🛡️ Risk Mgmt: {setup.get('risk_management', 'N/A')}")
                
                confluence_factors = setup.get('confluence_factors', [])
                if confluence_factors:
                    print(f"   ✅ Confluence Factors:")
                    for factor in confluence_factors:
                        print(f"      • {factor}")
                print()
        else:
            print("❌ No high-probability setups detected for this scenario")
    
    print("=" * 80)
    print("✅ HIGH-PROBABILITY SETUP DETECTION TEST COMPLETED")

if __name__ == "__main__":
    test_high_probability_setup_detection()