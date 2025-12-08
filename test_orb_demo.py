#!/usr/bin/env python3
"""
Demo script showing ORB strategy range checking functionality.
"""

from backend.orb_strategy import ORBStrategy
import pandas as pd

def main():
    print("🔍 ORB Strategy Range Checking Demo")
    print("=" * 50)

    # Create ORB strategy
    orb = ORBStrategy(range_minutes=15, min_range_size=0.005)  # 0.5% minimum range

    # Create sample 5-minute data for a 15-minute opening range
    base_time = pd.Timestamp('2025-01-01 09:30:00')
    data = [
        {'timestamp': base_time, 'open': 100.0, 'high': 101.0, 'low': 99.5, 'close': 100.5, 'volume': 1000},
        {'timestamp': base_time + pd.Timedelta(minutes=5), 'open': 100.5, 'high': 101.5, 'low': 100.0, 'close': 101.0, 'volume': 1200},
        {'timestamp': base_time + pd.Timedelta(minutes=10), 'open': 101.0, 'high': 102.0, 'low': 100.5, 'close': 101.5, 'volume': 1100},
        {'timestamp': base_time + pd.Timedelta(minutes=15), 'open': 101.5, 'high': 104.0, 'low': 101.0, 'close': 103.5, 'volume': 1500},
    ]

    df = pd.DataFrame(data)

    print("📊 Sample OHLCV Data (15-minute opening range):")
    print(df)
    print()

    # Test range definition
    print("1️⃣ Range Definition:")
    range_high, range_low = orb.define_opening_range(df, base_time)
    if range_high and range_low:
        range_size_pct = (range_high - range_low) / range_low * 100
        print(f"   ✅ Opening Range: High=${range_high:.2f}, Low=${range_low:.2f}")
        print(f"   📏 Range Size: {range_size_pct:.2f}% (minimum required: {orb.min_range_size*100:.1f}%)")
        print(f"   🎯 Valid Range: {'Yes' if range_size_pct >= orb.min_range_size * 100 else 'No'}")
    else:
        print("   ❌ Opening range not defined (insufficient data or range too small)")
    print()

    # Test breakout detection with different price levels
    print("2️⃣ Breakout Detection:")

    # Price above range (long breakout)
    current_price_high = 103.5  # Above range high
    breakout_high = orb.detect_breakout(current_price_high)
    print(f"   📈 Price ${current_price_high:.2f} (above range): {breakout_high.value}")

    # Price below range (short breakout)
    current_price_low = 98.0  # Below range low
    breakout_low = orb.detect_breakout(current_price_low)
    print(f"   📉 Price ${current_price_low:.2f} (below range): {breakout_low.value}")

    # Price inside range (no breakout)
    current_price_mid = 101.2  # Inside range
    breakout_mid = orb.detect_breakout(current_price_mid)
    print(f"   ➡️  Price ${current_price_mid:.2f} (inside range): {breakout_mid.value}")
    print()

    # Test signal generation
    print("3️⃣ Signal Generation:")

    # Generate signal for breakout price
    signal = orb.generate_orb_signal(current_price_high, df, base_time)
    print(f"   🚀 Signal for breakout price (${current_price_high:.2f}):")
    print(f"      Action: {signal['action']}")
    print(f"      Reason: {signal['reason']}")
    if signal['action'] in ['BUY', 'SELL']:
        print(f"      Entry: ${signal['entry_price']:.2f}")
        print(f"      Stop Loss: ${signal['stop_loss']:.2f}")
        print(f"      Range: ${signal['opening_range_low']:.2f} - ${signal['opening_range_high']:.2f}")
    print()

    # Test with price inside range
    signal_wait = orb.generate_orb_signal(current_price_mid, df, base_time)
    print(f"   ⏳ Signal for range-bound price (${current_price_mid:.2f}):")
    print(f"      Action: {signal_wait['action']}")
    print(f"      Reason: {signal_wait['reason']}")
    print()

    # Test range validation
    print("4️⃣ Range Validation Examples:")

    # Test with very small range (should fail)
    small_range_data = [
        {'timestamp': base_time, 'open': 100.0, 'high': 100.1, 'low': 99.9, 'close': 100.0, 'volume': 1000},
        {'timestamp': base_time + pd.Timedelta(minutes=5), 'open': 100.0, 'high': 100.2, 'low': 99.8, 'close': 100.1, 'volume': 1200},
    ]
    small_df = pd.DataFrame(small_range_data)

    orb_small = ORBStrategy(range_minutes=15, min_range_size=0.005)
    range_high_small, range_low_small = orb_small.define_opening_range(small_df, base_time)

    if range_high_small and range_low_small:
        small_range_size = (range_high_small - range_low_small) / range_low_small * 100
        print(f"   📏 Small range ({small_range_size:.2f}%) would be accepted")
    else:
        print("   ❌ Small range rejected (below minimum 0.5%)")
    print()

    print("✅ ORB Strategy Range Checking: COMPLETE")
    print("   - Defines opening ranges from first 15 minutes")
    print("   - Validates minimum range size (0.5%)")
    print("   - Detects breakouts above/below range")
    print("   - Generates BUY/SELL signals only on confirmed breakouts")

if __name__ == "__main__":
    main()
