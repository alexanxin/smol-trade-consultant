#!/usr/bin/env python3
"""
Demo script to showcase the enhanced output formatting
"""

from output_formatter import OutputFormatter

def demo_trade_signal():
    """Demonstrate trade signal formatting"""
    
    # Sample signal data
    signal = {
        "action": "BUY",
        "entry_price": 159.45,
        "stop_loss": 156.20,
        "take_profit": 165.80,
        "conviction_score": 85,
        "strategy_type": "trend_following",
        "risk_reward_ratio": 2.15,
        "reasoning": "Strong bullish momentum detected with RSI at 62.5 and MACD showing bullish crossover. Volume profile indicates POC at $158.50 with price breaking through key resistance. Order flow shows aggressive buying pressure with CVD trending upward. Market state is imbalanced with bullish direction, optimal for trend following setup during NY session."
    }
    
    market_data = {
        "symbol": "SOL",
        "value": 159.45,
        "liquidity": 2500000,
        "volume": 1850000
    }
    
    # Format and display
    OutputFormatter.format_trade_signal(signal, market_data, "SOL")
    
    # Add Fabio Valentino analysis
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
                "direction": "long"
            }
        }
    }
    
    OutputFormatter.format_fabio_valentino_analysis(fabio_data, "New_York")

def demo_comprehensive_analysis():
    """Demonstrate comprehensive analysis formatting"""
    
    analysis_text = """
⚡ Live SOL Market Overview (Fabio Valentino Framework)
Current Price: $159.45 | Trading Session: New York
Market State: Imbalanced (Bullish) | Volume Profile: Strong POC at $158.50
24h Change: +5.2% | Volume: $1.85M | Liquidity: $2.5M

🏛️ Auction Market Theory Analysis
Balance Area: $155.20 - $162.80 | POC: $158.50 | Value Area: Strong concentration
Market State: Imbalanced | Direction: Bullish | Strength: High
Liquidity Grabs: Multiple sweeps above $160 | Order Flow: Aggressive buying detected

📈 Multi-Timeframe Structure
Timeframe | Market State | Order Flow | Opportunity
LTF (5m): Imbalanced | Bullish CVD | Trend Following Setup Active
HTF (1h): Bullish Bias | Strong Buying | Confirms LTF direction
Daily: Uptrend | Accumulation | Long-term bullish context

💧 Volume Profile & Liquidity
POC: $158.50 (70% reversal probability)
LVN Levels: $156.20, $161.50 | HVN Levels: $158.50, $159.80
Value Area: $157.00 - $160.50 | Imbalance Zones: Multiple bullish gaps

🎯 Fabio Valentino Trading Opportunities
TREND FOLLOWING: Active Setup Detected
- Entry: $159.45 | Target: $165.80 (POC) | R:R: 2.15:1
MEAN REVERSION: Not applicable in current imbalanced state

📊 Traditional SMC Analysis
FVGs: 3 bullish gaps identified | Order Blocks: Strong demand zone at $157.50
Patterns: Bullish engulfing on 1H timeframe

🧭 Integrated Trading Plan
Preferred Setup: Trend Following with SMC confluence
Entry: $159.45 | Stop: $156.20 (aggressive) | TP: $165.80 (POC target)
Risk Management: 0.25% account risk, NY session optimal | Conviction: 85%

✅ Final Assessment
Market Context: Strong bullish momentum in imbalanced state with institutional participation
Bias: BULLISH with HIGH confidence
Action Plan: Execute trend following model, target POC reversion at $165.80
"""
    
    OutputFormatter.format_comprehensive_analysis(analysis_text, "SOL")

def demo_all_features():
    """Demonstrate all formatting features"""
    
    fmt = OutputFormatter
    
    # Section headers
    fmt.section_header("FORMATTING FEATURES DEMO", icon='rocket')
    
    # Subsections
    fmt.subsection_header("Price Changes", icon='chart')
    fmt.price_change(5.2, "1H Change")
    fmt.price_change(-2.1, "4H Change")
    fmt.price_change(0.0, "Neutral")
    
    # Key-value pairs
    fmt.blank_line()
    fmt.subsection_header("Market Data", icon='money')
    fmt.key_value("Current Price", "$159.45", icon='chart', color='cyan')
    fmt.key_value("Volume 24H", "$1.85M", icon='droplet', color='blue')
    fmt.key_value("Liquidity", "$2.5M", icon='lock', color='green')
    
    # Action signals
    fmt.blank_line()
    fmt.subsection_header("Trading Actions", icon='target')
    print(f"  {fmt.action_signal('BUY')}")
    print(f"  {fmt.action_signal('SELL')}")
    print(f"  {fmt.action_signal('HOLD')}")
    
    # Conviction bars
    fmt.blank_line()
    fmt.subsection_header("Conviction Scores", icon='fire')
    print(f"  High: {fmt.conviction_bar(85)}")
    print(f"  Medium: {fmt.conviction_bar(65)}")
    print(f"  Low: {fmt.conviction_bar(45)}")
    
    # Market states
    fmt.blank_line()
    fmt.subsection_header("Market States", icon='building')
    print(f"  {fmt.market_state('balanced')}")
    print(f"  {fmt.market_state('imbalanced', 'bullish')}")
    print(f"  {fmt.market_state('imbalanced', 'bearish')}")
    
    # Risk/Reward ratios
    fmt.blank_line()
    fmt.subsection_header("Risk/Reward Ratios", icon='scales')
    print(f"  Excellent: {fmt.risk_reward_ratio(3.5)}")
    print(f"  Good: {fmt.risk_reward_ratio(2.0)}")
    print(f"  Acceptable: {fmt.risk_reward_ratio(1.5)}")
    print(f"  Poor: {fmt.risk_reward_ratio(0.8)}")
    
    # Sessions
    fmt.blank_line()
    fmt.subsection_header("Trading Sessions", icon='globe')
    print(f"  {fmt.session_indicator('New_York')}")
    print(f"  {fmt.session_indicator('London')}")
    print(f"  {fmt.session_indicator('Asian')}")
    print(f"  {fmt.session_indicator('Low_Volume')}")
    
    # Bullet points
    fmt.blank_line()
    fmt.subsection_header("Bullet Points", icon='file')
    fmt.bullet_point("Level 0 bullet point", level=0, icon='star')
    fmt.bullet_point("Level 1 bullet point", level=1, icon='check')
    fmt.bullet_point("Level 2 bullet point", level=2, icon='info')
    
    # Footer
    fmt.blank_line()
    fmt.divider("=", 80)
    fmt.blank_line()

if __name__ == "__main__":
    print("\n" + "="*80)
    print("🎨 ENHANCED OUTPUT FORMATTING DEMO")
    print("="*80)
    
    print("\n\n1️⃣  TRADE SIGNAL FORMATTING")
    print("-" * 80)
    demo_trade_signal()
    
    print("\n\n2️⃣  COMPREHENSIVE ANALYSIS FORMATTING")
    print("-" * 80)
    demo_comprehensive_analysis()
    
    print("\n\n3️⃣  ALL FORMATTING FEATURES")
    print("-" * 80)
    demo_all_features()
    
    print("\n✅ Demo complete! The output is now much more readable and structured.")