import json
from news_agent import NewsAgent
from risk_manager import RiskManager
from output_formatter import OutputFormatter

def mock_ai_callback(user_prompt, system_prompt):
    print("\n[MOCK AI] Received Prompt length:", len(user_prompt))
    # Return a dummy risk assessment
    return json.dumps({
        "approved": True,
        "risk_score": 3,
        "critique": "The signal seems valid given the positive news sentiment and strong technicals.",
        "modified_conviction": 85
    })

def test_flow():
    print("--- Testing Multi-Agent Flow ---")
    
    # 1. Test News Agent
    print("\n1. Testing News Agent...")
    news_agent = NewsAgent()
    # Mocking fetch_news to avoid network calls if needed, but let's try real first
    try:
        news_summary = news_agent.fetch_news("SOL")
        print("News fetched successfully.")
        print(news_summary[:100] + "...")
    except Exception as e:
        print(f"News fetch failed: {e}")
        news_summary = "Mock News: SOL is going up."

    # 2. Mock Strategy Signal
    print("\n2. Mocking Strategy Signal...")
    signal = {
        "action": "BUY",
        "entry_price": 100.0,
        "stop_loss": 95.0,
        "take_profit": 110.0,
        "conviction_score": 80,
        "reasoning": "Strong bullish momentum and breakout.",
        "news_summary": news_summary
    }
    
    market_data = {
        "value": 100.0,
        "liquidity": 1000000,
        "volume": 500000
    }

    # 3. Test Risk Manager
    print("\n3. Testing Risk Manager...")
    risk_manager = RiskManager()
    risk_assessment = risk_manager.assess_risk(signal, market_data, news_summary, mock_ai_callback)
    print("Risk Assessment:", risk_assessment)
    
    signal['risk_assessment'] = risk_assessment

    # 4. Test Output Formatter
    print("\n4. Testing Output Formatter...")
    OutputFormatter.format_trade_signal(signal, market_data, "SOL")

if __name__ == "__main__":
    test_flow()
