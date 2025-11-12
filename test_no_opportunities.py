ew#!/usr/bin/env python3
"""
Test output formatting when no trading opportunities are detected
"""

from output_formatter import OutputFormatter

def test_no_opportunities_balanced():
    """Test output when market is balanced with no opportunities"""
    
    fabio_data = {
        "ltf_market_state": {
            "state": "balanced",
            "imbalance_direction": None,
            "strength": "medium"
        },
        "ltf_order_flow": {
            "buying_pressure": "neutral",
            "selling_pressure": "neutral",
            "cvd_trend": "neutral"
        },
        "trading_opportunities": {
            "trend_following": None,
            "mean_reversion": None
        }
    }
    
    print("Test 1: Balanced Market - No Opportunities")
    print("=" * 80)
    OutputFormatter.format_fabio_valentino_analysis(fabio_data, "London")
    print()

def test_no_opportunities_imbalanced():
    """Test output when market is imbalanced but no valid setup"""
    
    fabio_data = {
        "ltf_market_state": {
            "state": "imbalanced",
            "imbalance_direction": "bearish",
            "strength": "strong"
        },
        "ltf_order_flow": {
            "buying_pressure": "low",
            "selling_pressure": "high",
            "cvd_trend": "bearish"
        },
        "trading_opportunities": {
            "trend_following": None,
            "mean_reversion": None
        }
    }
    
    print("Test 2: Imbalanced Bearish Market - No Valid Setup")
    print("=" * 80)
    OutputFormatter.format_fabio_valentino_analysis(fabio_data, "Asian")
    print()

def test_with_opportunities():
    """Test output when opportunities ARE detected"""
    
    fabio_data = {
        "ltf_market_state": {
            "state": "imbalanced",
            "imbalance_direction": "bullish",
            "strength": "strong"
        },
        "ltf_order_flow": {
            "buying_pressure": "high",
            "selling_pressure": "low",
            "cvd_trend": "bullish"
        },
        "trading_opportunities": {
            "trend_following": {
                "setup_name": "Bullish Continuation",
                "direction": "long",
                "entry_price": 159.45,
                "target": 165.80,
                "risk_reward": 2.15,
                "confidence": 70
            },
            "mean_reversion": None
        }
    }
    
    print("Test 3: Imbalanced Bullish Market - WITH Opportunity")
    print("=" * 80)
    OutputFormatter.format_fabio_valentino_analysis(fabio_data, "New_York")
    print()

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🧪 TESTING OUTPUT WITH NO OPPORTUNITIES")
    print("=" * 80 + "\n")
    
    test_no_opportunities_balanced()
    test_no_opportunities_imbalanced()
    test_with_opportunities()
    
    print("=" * 80)
    print("✅ ALL SCENARIOS TESTED")
    print("=" * 80)
    print("\nNow the output provides helpful context even when no opportunities exist!")