#!/usr/bin/env python3
"""
Enhanced Output Formatter for Trading Agent
Provides beautiful, structured console output with icons, colors, and formatting
"""

class OutputFormatter:
    """Handles all formatted output for the trading agent"""
    
    # Color codes for terminal output
    COLORS = {
        'reset': '\033[0m',
        'bold': '\033[1m',
        'green': '\033[92m',
        'red': '\033[91m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'cyan': '\033[96m',
        'magenta': '\033[95m',
        'white': '\033[97m',
        'gray': '\033[90m'
    }
    
    # Icons for different sections
    ICONS = {
        'rocket': '🚀',
        'chart': '📊',
        'money': '💰',
        'up': '📈',
        'down': '📉',
        'warning': '⚠️',
        'check': '✅',
        'cross': '❌',
        'info': 'ℹ️',
        'target': '🎯',
        'shield': '🛡️',
        'lightning': '⚡',
        'fire': '🔥',
        'brain': '🧠',
        'crystal': '🔮',
        'compass': '🧭',
        'scales': '⚖️',
        'building': '🏛️',
        'droplet': '💧',
        'clock': '🕐',
        'globe': '🌍',
        'star': '⭐',
        'trophy': '🏆',
        'key': '🔑',
        'lock': '🔒',
        'unlock': '🔓',
        'bell': '🔔',
        'magnify': '🔍',
        'wrench': '🔧',
        'gear': '⚙️',
        'package': '📦',
        'folder': '📁',
        'file': '📄',
        'link': '🔗',
        'signal': '📡'
    }
    
    @staticmethod
    def color(text, color_name):
        """Apply color to text"""
        color_code = OutputFormatter.COLORS.get(color_name, '')
        reset = OutputFormatter.COLORS['reset']
        return f"{color_code}{text}{reset}"
    
    @staticmethod
    def bold(text):
        """Make text bold"""
        return OutputFormatter.color(text, 'bold')
    
    @staticmethod
    def section_header(title, icon='star', width=80):
        """Create a formatted section header"""
        icon_char = OutputFormatter.ICONS.get(icon, '•')
        line = "=" * width
        print(f"\n{line}")
        print(f"{icon_char}  {OutputFormatter.bold(title)}")
        print(line)
    
    @staticmethod
    def subsection_header(title, icon='info'):
        """Create a formatted subsection header"""
        icon_char = OutputFormatter.ICONS.get(icon, '•')
        print(f"\n{icon_char} {OutputFormatter.bold(title)}")
        print("-" * 60)
    
    @staticmethod
    def bullet_point(text, level=0, icon='•'):
        """Create a bullet point with optional indentation"""
        indent = "  " * level
        if isinstance(icon, str) and len(icon) == 1:
            bullet = icon
        else:
            bullet = OutputFormatter.ICONS.get(icon, '•')
        print(f"{indent}{bullet} {text}")
    
    @staticmethod
    def key_value(key, value, icon=None, color=None):
        """Display a key-value pair with optional icon and color"""
        icon_str = f"{OutputFormatter.ICONS.get(icon, '')} " if icon else ""
        value_str = str(value)
        if color:
            value_str = OutputFormatter.color(value_str, color)
        print(f"  {icon_str}{OutputFormatter.bold(key)}: {value_str}")
    
    @staticmethod
    def price_change(value, label="Change"):
        """Format price change with color based on direction"""
        if value > 0:
            color_val = OutputFormatter.color(f"+{value:.2f}%", 'green')
            icon = OutputFormatter.ICONS['up']
        elif value < 0:
            color_val = OutputFormatter.color(f"{value:.2f}%", 'red')
            icon = OutputFormatter.ICONS['down']
        else:
            color_val = f"{value:.2f}%"
            icon = "→"
        print(f"  {icon} {OutputFormatter.bold(label)}: {color_val}")
    
    @staticmethod
    def action_signal(action):
        """Format trading action with appropriate color and icon"""
        action_upper = action.upper()
        if action_upper == "BUY":
            icon = OutputFormatter.ICONS['up']
            colored = OutputFormatter.color(action_upper, 'green')
        elif action_upper == "SELL":
            icon = OutputFormatter.ICONS['down']
            colored = OutputFormatter.color(action_upper, 'red')
        else:  # HOLD
            icon = OutputFormatter.ICONS['warning']
            colored = OutputFormatter.color(action_upper, 'yellow')
        return f"{icon} {OutputFormatter.bold(colored)}"
    
    @staticmethod
    def conviction_bar(score, width=20):
        """Create a visual conviction score bar"""
        filled = int((score / 100) * width)
        empty = width - filled
        bar = "█" * filled + "░" * empty
        
        if score >= 80:
            color = 'green'
            icon = OutputFormatter.ICONS['fire']
        elif score >= 60:
            color = 'yellow'
            icon = OutputFormatter.ICONS['star']
        else:
            color = 'red'
            icon = OutputFormatter.ICONS['warning']
        
        colored_bar = OutputFormatter.color(bar, color)
        return f"{icon} {colored_bar} {score}%"
    
    @staticmethod
    def market_state(state, direction=None):
        """Format market state with appropriate styling"""
        if state.lower() == "balanced":
            icon = OutputFormatter.ICONS['scales']
            color = 'cyan'
        else:  # imbalanced
            icon = OutputFormatter.ICONS['lightning']
            color = 'yellow'
        
        state_str = OutputFormatter.color(state.upper(), color)
        result = f"{icon} {state_str}"
        
        if direction:
            if direction.lower() == "bullish":
                dir_icon = OutputFormatter.ICONS['up']
                dir_color = 'green'
            else:
                dir_icon = OutputFormatter.ICONS['down']
                dir_color = 'red'
            result += f" {dir_icon} {OutputFormatter.color(direction.upper(), dir_color)}"
        
        return result
    
    @staticmethod
    def risk_reward_ratio(ratio):
        """Format risk/reward ratio with visual indicator"""
        if ratio >= 2.0:
            icon = OutputFormatter.ICONS['trophy']
            color = 'green'
        elif ratio >= 1.5:
            icon = OutputFormatter.ICONS['check']
            color = 'yellow'
        else:
            icon = OutputFormatter.ICONS['warning']
            color = 'red'
        
        colored_ratio = OutputFormatter.color(f"{ratio:.2f}:1", color)
        return f"{icon} {colored_ratio}"
    
    @staticmethod
    def session_indicator(session):
        """Format trading session with appropriate icon"""
        session_map = {
            'New_York': ('🗽', 'NY Session', 'green'),
            'London': ('🇬🇧', 'London Session', 'blue'),
            'Asian': ('🌏', 'Asian Session', 'yellow'),
            'Low_Volume': ('🌙', 'Low Volume', 'gray')
        }
        
        icon, label, color = session_map.get(session, ('🌍', session, 'white'))
        colored_label = OutputFormatter.color(label, color)
        return f"{icon} {colored_label}"
    
    @staticmethod
    def divider(char="-", width=80):
        """Print a divider line"""
        print(char * width)
    
    @staticmethod
    def blank_line():
        """Print a blank line"""
        print()
    
    @staticmethod
    def format_trade_signal(signal, market_data, coin_symbol):
        """Format complete trade signal output"""
        fmt = OutputFormatter
        
        # Header
        fmt.section_header(f"TRADE SIGNAL - {coin_symbol}", icon='brain', width=80)
        
        # Current Market Info
        fmt.subsection_header("Current Market", icon='chart')
        fmt.key_value("Token", coin_symbol, icon='money')
        fmt.key_value("Price", f"${market_data.get('value', 'N/A')}", icon='chart', color='cyan')
        
        # News Summary
        if 'news_summary' in signal:
             fmt.blank_line()
             fmt.subsection_header("News Analysis", icon='globe')
             news_lines = signal['news_summary'].split('\n')
             for line in news_lines:
                 if line.startswith('-'):
                     print(f"  {line}")
                 elif line.startswith('---'):
                     continue
                 else:
                     print(f"  {line}")

        # Risk Assessment
        if 'risk_assessment' in signal:
            risk = signal['risk_assessment']
            fmt.blank_line()
            fmt.subsection_header("Risk Manager Assessment", icon='shield')
            
            approved = risk.get('approved', True)
            status_color = 'green' if approved else 'red'
            status_icon = 'check' if approved else 'cross'
            fmt.key_value("Status", "APPROVED" if approved else "REJECTED", icon=status_icon, color=status_color)
            
            risk_score = risk.get('risk_score', 0)
            score_color = 'green' if risk_score <= 3 else 'yellow' if risk_score <= 7 else 'red'
            fmt.key_value("Risk Score", f"{risk_score}/10", icon='warning', color=score_color)
            
            critique = risk.get('critique', 'No critique provided.')
            print(f"  {fmt.bold('Critique')}: {critique}")
        
        # Trading Action
        fmt.blank_line()
        fmt.subsection_header("Trading Recommendation", icon='target')
        print(f"  {fmt.action_signal(signal.get('action', 'HOLD'))}")
        
        # Entry & Targets
        fmt.blank_line()
        fmt.subsection_header("Entry & Targets", icon='compass')
        fmt.key_value("Entry Price", f"${signal.get('entry_price', 0):.4f}", icon='unlock')
        fmt.key_value("Stop Loss", f"${signal.get('stop_loss', 0):.4f}", icon='shield', color='red')
        fmt.key_value("Take Profit", f"${signal.get('take_profit', 0):.4f}", icon='target', color='green')
        
        # Risk Management
        if 'risk_reward_ratio' in signal:
            fmt.blank_line()
            fmt.subsection_header("Risk Management", icon='scales')
            print(f"  {fmt.bold('Risk/Reward')}: {fmt.risk_reward_ratio(signal['risk_reward_ratio'])}")
        
        # Conviction
        fmt.blank_line()
        fmt.subsection_header("Conviction Score", icon='fire')
        print(f"  {fmt.conviction_bar(signal.get('conviction_score', 50))}")
        
        # Strategy Type
        if 'strategy_type' in signal:
            fmt.blank_line()
            strategy = signal['strategy_type'].replace('_', ' ').title()
            fmt.key_value("Strategy", strategy, icon='crystal')
        
        # Reasoning
        fmt.blank_line()
        fmt.subsection_header("Analysis", icon='magnify')
        reasoning = signal.get('reasoning', 'N/A')
        # Wrap long text
        max_width = 76
        words = reasoning.split()
        line = "  "
        for word in words:
            if len(line) + len(word) + 1 > max_width:
                print(line)
                line = "  " + word
            else:
                line += " " + word if line != "  " else word
        if line.strip():
            print(line)
        
        # Footer
        fmt.blank_line()
        fmt.divider("=", 80)
        fmt.blank_line()
    
    @staticmethod
    def format_comprehensive_analysis(analysis_text, coin_symbol):
        """Format comprehensive market analysis output"""
        fmt = OutputFormatter
        
        # Header
        fmt.section_header(f"COMPREHENSIVE MARKET ANALYSIS - {coin_symbol}", icon='crystal', width=80)
        
        # Split analysis into sections if possible
        lines = analysis_text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                fmt.blank_line()
                continue
            
            # Detect section headers (lines with emojis or all caps)
            if any(icon in line for icon in ['⚡', '🏛️', '📈', '💧', '🎯', '📊', '🧭', '✅']):
                fmt.blank_line()
                print(f"{fmt.bold(line)}")
                fmt.divider("-", 60)
            else:
                print(f"  {line}")
        
        # Footer
        fmt.blank_line()
        fmt.divider("=", 80)
        fmt.blank_line()
    
    @staticmethod
    def format_fabio_valentino_analysis(fabio_data, session, analysis_data=None):
        """Format Fabio Valentino specific analysis with candlestick patterns"""
        fmt = OutputFormatter
        
        fmt.subsection_header("Fabio Valentino Framework", icon='building')
        
        # Session
        print(f"  {fmt.bold('Session')}: {fmt.session_indicator(session)}")
        
        # Market State
        ltf_state = fabio_data.get('ltf_market_state', {})
        if ltf_state:
            state = ltf_state.get('state', 'unknown')
            direction = ltf_state.get('imbalance_direction')
            print(f"  {fmt.bold('Market State')}: {fmt.market_state(state, direction)}")
        
        # Candlestick Patterns Section
        if analysis_data:
            ltf_patterns = analysis_data.get('ltf_candlestick_patterns', [])
            htf_patterns = analysis_data.get('htf_candlestick_patterns', [])
            daily_patterns = analysis_data.get('daily_candlestick_patterns', [])
            
            if ltf_patterns or htf_patterns or daily_patterns:
                fmt.blank_line()
                fmt.bullet_point("Candlestick Patterns:", level=1, icon='📊')
                
                if ltf_patterns:
                    fmt.bullet_point("LTF (5m):", level=2, icon='chart')
                    for pattern in ltf_patterns[-3:]:  # Show last 3 patterns
                        pattern_type = pattern.get('pattern_type', 'unknown')
                        strength = pattern.get('strength', 'medium')
                        price = pattern.get('price', 0)
                        
                        # Pattern icons and colors
                        pattern_icons = {
                            'bullish_engulfing': '🟢',
                            'bearish_engulfing': '🔴',
                            'outside_bar': '⚫',
                            'evening_star': '🌙',
                            'gravestone_doji': '⚰️'
                        }
                        icon = pattern_icons.get(pattern_type, '•')
                        pattern_name = pattern_type.replace('_', ' ').title()
                        strength_indicator = "🔥" if strength == 'high' else "⭐"
                        
                        fmt.bullet_point(f"{icon} {pattern_name} @ ${price:.6f} {strength_indicator}", level=3)
                
                if htf_patterns:
                    fmt.bullet_point("HTF (1h):", level=2, icon='chart')
                    for pattern in htf_patterns[-3:]:
                        pattern_type = pattern.get('pattern_type', 'unknown')
                        strength = pattern.get('strength', 'medium')
                        price = pattern.get('price', 0)
                        
                        pattern_icons = {
                            'bullish_engulfing': '🟢',
                            'bearish_engulfing': '🔴',
                            'outside_bar': '⚫',
                            'evening_star': '🌙',
                            'gravestone_doji': '⚰️'
                        }
                        icon = pattern_icons.get(pattern_type, '•')
                        pattern_name = pattern_type.replace('_', ' ').title()
                        strength_indicator = "🔥" if strength == 'high' else "⭐"
                        
                        fmt.bullet_point(f"{icon} {pattern_name} @ ${price:.6f} {strength_indicator}", level=3)
                
                if daily_patterns:
                    fmt.bullet_point("Daily:", level=2, icon='chart')
                    for pattern in daily_patterns[-3:]:
                        pattern_type = pattern.get('pattern_type', 'unknown')
                        strength = pattern.get('strength', 'medium')
                        price = pattern.get('price', 0)
                        
                        pattern_icons = {
                            'bullish_engulfing': '🟢',
                            'bearish_engulfing': '🔴',
                            'outside_bar': '⚫',
                            'evening_star': '🌙',
                            'gravestone_doji': '⚰️'
                        }
                        icon = pattern_icons.get(pattern_type, '•')
                        pattern_name = pattern_type.replace('_', ' ').title()
                        strength_indicator = "🔥" if strength == 'high' else "⭐"
                        
                        fmt.bullet_point(f"{icon} {pattern_name} @ ${price:.6f} {strength_indicator}", level=3)
        
        # Order Flow
        ltf_flow = fabio_data.get('ltf_order_flow', {})
        if ltf_flow:
            fmt.blank_line()
            fmt.bullet_point(f"Buying Pressure: {ltf_flow.get('buying_pressure', 'N/A')}", level=1, icon='up')
            fmt.bullet_point(f"Selling Pressure: {ltf_flow.get('selling_pressure', 'N/A')}", level=1, icon='down')
            fmt.bullet_point(f"CVD Trend: {ltf_flow.get('cvd_trend', 'N/A')}", level=1, icon='chart')
        
        # Trading Opportunities
        opportunities = fabio_data.get('trading_opportunities', {})
        fmt.blank_line()
        fmt.bullet_point("Trading Opportunities:", level=1, icon='target')
        
        has_opportunities = False
        
        if opportunities:
            trend_setup = opportunities.get('trend_following')
            if trend_setup:
                has_opportunities = True
                fmt.bullet_point(f"Trend Following: {trend_setup.get('setup_name', 'Available')}", level=2, icon='lightning')
                if 'entry_price' in trend_setup:
                    fmt.bullet_point(f"Entry: ${trend_setup.get('entry_price', 0):.4f}", level=3)
                    fmt.bullet_point(f"Target: ${trend_setup.get('target', 0):.4f}", level=3)
                    fmt.bullet_point(f"R:R: {trend_setup.get('risk_reward', 0):.2f}:1", level=3)
                    if 'confidence' in trend_setup:
                        fmt.bullet_point(f"Confidence: {trend_setup.get('confidence', 0)}%", level=3)
            
            mean_setup = opportunities.get('mean_reversion')
            if mean_setup:
                has_opportunities = True
                fmt.bullet_point(f"Mean Reversion: {mean_setup.get('setup_name', 'Available')}", level=2, icon='scales')
                if 'entry_price' in mean_setup:
                    fmt.bullet_point(f"Entry: ${mean_setup.get('entry_price', 0):.4f}", level=3)
                    fmt.bullet_point(f"Target: ${mean_setup.get('target', 0):.4f}", level=3)
                    fmt.bullet_point(f"R:R: {mean_setup.get('risk_reward', 0):.2f}:1", level=3)
                    if 'confidence' in mean_setup:
                        fmt.bullet_point(f"Confidence: {mean_setup.get('confidence', 0)}%", level=3)
        
        if not has_opportunities:
            # Provide helpful context when no opportunities are detected
            market_state = fabio_data.get('ltf_market_state', {})
            state = market_state.get('state', 'unknown')
            direction = market_state.get('imbalance_direction')
            
            if state == 'balanced':
                fmt.bullet_point("⏳ Waiting for breakout confirmation", level=2, icon='clock')
                fmt.bullet_point("Market in consolidation - avoid first swing", level=3)
                fmt.bullet_point("Monitor for: Clear breakout + retracement pattern", level=3)
            elif state == 'imbalanced':
                if direction:
                    fmt.bullet_point(f"⏳ No valid setup in current {direction} imbalance", level=2, icon='clock')
                else:
                    fmt.bullet_point("⏳ Market imbalanced but direction unclear", level=2, icon='clock')
                fmt.bullet_point("Waiting for optimal entry conditions", level=3)
                fmt.bullet_point("Monitor for: LVN reaction, POC proximity, session alignment", level=3)
            else:
                fmt.bullet_point("⏳ No setups detected - conditions not met", level=2, icon='clock')
                fmt.bullet_point("Monitor for: POC proximity, LVN reaction, session timing", level=3)
        
        fmt.blank_line()
        fmt.divider("-", 60)
        print(f"  💡 {fmt.bold('Tip')}: Fabio Valentino strategy requires patience - wait for high-probability setups")
        fmt.blank_line()