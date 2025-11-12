#!/usr/bin/env python3
"""
Test script to demonstrate candlestick pattern display in output
"""

from output_formatter import OutputFormatter

# Sample data with candlestick patterns
sample_fabio_data = {
    'ltf_market_state': {
        'state': 'imbalanced',
        'imbalance_direction': 'bullish',
        'strength': 'strong'
    },
    'ltf_order_flow': {
        'buying_pressure': 'high',
        'selling_pressure': 'low',
        'cvd_trend': 'bullish'
    },
    'trading_opportunities': {
        'trend_following': {
            'setup_name': 'Bullish Continuation',
            'entry_price': 150.25,
            'target': 155.50,
            'risk_reward': 2.5,
            'confidence': 75
        }
    }
}

sample_analysis_data = {
    'ltf_candlestick_patterns': [
        {
            'pattern_type': 'bullish_engulfing',
            'candle_index': 45,
            'timeframe': 'current',
            'strength': 'high',
            'price': 149.85,
            'description': 'Bullish engulfing pattern detected'
        },
        {
            'pattern_type': 'outside_bar',
            'candle_index': 48,
            'timeframe': 'current',
            'strength': 'medium',
            'price': 150.10,
            'description': 'Outside bar pattern detected'
        }
    ],
    'htf_candlestick_patterns': [
        {
            'pattern_type': 'bearish_engulfing',
            'candle_index': 12,
            'timeframe': 'current',
            'strength': 'high',
            'price': 152.30,
            'description': 'Bearish engulfing pattern detected'
        }
    ],
    'daily_candlestick_patterns': [
        {
            'pattern_type': 'evening_star',
            'candle_index': 5,
            'timeframe': 'current',
            'strength': 'high',
            'price': 153.75,
            'description': 'Evening star pattern detected - potential bearish reversal'
        },
        {
            'pattern_type': 'gravestone_doji',
            'candle_index': 7,
            'timeframe': 'current',
            'strength': 'high',
            'price': 154.20,
            'description': 'Gravestone doji detected - potential reversal signal'
        }
    ]
}

def main():
    print("\n" + "="*80)
    print("🕯️  CANDLESTICK PATTERN DISPLAY TEST")
    print("="*80 + "\n")
    
    print("This test demonstrates how candlestick patterns are displayed")
    print("in the Fabio Valentino analysis section.\n")
    
    # Display the formatted output
    OutputFormatter.format_fabio_valentino_analysis(
        sample_fabio_data, 
        'New_York',
        sample_analysis_data
    )
    
    print("\n" + "="*80)
    print("📋 PATTERN LEGEND")
    print("="*80)
    print("\n  Pattern Icons:")
    print("  🟢 Bullish Engulfing - Bullish reversal pattern")
    print("  🔴 Bearish Engulfing - Bearish reversal pattern")
    print("  ⚫ Outside Bar - Volatility expansion pattern")
    print("  🌙 Evening Star - Three-candle bearish reversal")
    print("  ⚰️  Gravestone Doji - Rejection of higher prices")
    print("\n  Strength Indicators:")
    print("  🔥 High strength pattern")
    print("  ⭐ Medium strength pattern")
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main()