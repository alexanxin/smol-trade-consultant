import os
import json
import requests
import pandas as pd
import google.genai as genai
import time
import sys
import argparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- External Libraries for Technical Analysis ---
# NOTE: You will need to install the following libraries:
# pip install requests google-genai pandas ta python-dotenv
# The 'ta' library is used for indicator calculations.
try:
    import ta 
except ImportError:
    print("Error: The 'ta' library is not installed. Please run: pip install ta")
    exit()

# --- CONFIGURATION (UPDATE THESE OR USE ENVIRONMENT VARIABLES) ---

# It is highly recommended to set these as environment variables for security:
# export BIRDEYE_API_KEY="your-birdeye-key"
# export GEMINI_API_KEY="your-gemini-key"

BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY", "REPLACE_WITH_YOUR_BIRDEYE_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "REPLACE_WITH_YOUR_GEMINI_KEY")
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "REPLACE_WITH_YOUR_COINGECKO_KEY")

# Initialize the Gemini Client
try:
    if not GEMINI_API_KEY or GEMINI_API_KEY == "REPLACE_WITH_YOUR_GEMINI_KEY":
        raise ValueError("GEMINI_API_KEY not set.")
    client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"Error initializing Gemini client: {e}")
    # We will let the script proceed to check API keys inside main()

# ----------------------------------------------------------------------
# 1. DATA RETRIEVAL FUNCTION
# ----------------------------------------------------------------------

def get_top_pool_coingecko(token_address: str, network: str = "solana"):
    """Fetches the top pool for a token from CoinGecko."""
    # Map network names to CoinGecko's expected identifiers for pools API
    # Note: Different CoinGecko API endpoints may use different identifiers
    # Based on user's information, CoinGecko uses 'eth' for Ethereum pools API
    network_map = {
        'solana': 'solana',
        'ethereum': 'eth',        # CoinGecko uses 'eth' for Ethereum pools API
        'bsc': 'bsc-mainnet',     # CoinGecko uses 'bsc-mainnet' for BSC pools
        'polygon': 'polygon-pos-mainnet'  # CoinGecko uses 'polygon-pos-mainnet' for Polygon pools
    }
    
    # Use the mapped network name or fall back to the original if not in map
    mapped_network = network_map.get(network, network)
    
    pools_url = f"https://api.coingecko.com/api/v3/onchain/networks/{mapped_network}/tokens/{token_address}/pools"
    headers = {"x-cg-demo-api-key": COINGECKO_API_KEY}
    try:
        response = requests.get(pools_url, headers=headers, timeout=10)
        response.raise_for_status()
        response_data = response.json()
        # Check if response has the expected structure
        if 'data' in response_data and isinstance(response_data['data'], list) and len(response_data['data']) > 0:
            # Get the first pool (top pool) from the list
            top_pool = response_data['data'][0]  # Get the first item in the list
            if 'attributes' in top_pool and 'address' in top_pool['attributes']:
                 return top_pool['attributes']['address']
            elif 'id' in top_pool:
                 return top_pool['id']
        print("❌ No pools found for token.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR fetching pools from CoinGecko: {e}")
        return None

def fetch_ohlcv_coingecko(pool_address: str, network: str = "solana", timeframe: str = "minute", aggregate: int = 5, limit: int = 100):
    """Fetches OHLCV data from CoinGecko for a pool."""
    # Map network names to CoinGecko's expected identifiers for pools API
    # Note: Different CoinGecko API endpoints may use different identifiers
    # Based on user's information, CoinGecko uses 'eth' for Ethereum pools API
    network_map = {
        'solana': 'solana',
        'ethereum': 'eth',        # CoinGecko uses 'eth' for Ethereum pools API
        'bsc': 'bsc-mainnet',     # CoinGecko uses 'bsc-mainnet' for BSC pools
        'polygon': 'polygon-pos-mainnet'  # CoinGecko uses 'polygon-pos-mainnet' for Polygon pools
    }
    
    # Use the mapped network name or fall back to the original if not in map
    mapped_network = network_map.get(network, network)
    
    # Remove network prefix from pool address if present (e.g., "solana_...")
    if '_' in pool_address:
        clean_pool_address = pool_address.split('_', 1)[1]  # Split only on first underscore
    else:
        clean_pool_address = pool_address
        
    ohlcv_url = f"https://api.coingecko.com/api/v3/onchain/networks/{mapped_network}/pools/{clean_pool_address}/ohlcv/{timeframe}?aggregate={aggregate}&limit={limit}"
    headers = {"x-cg-demo-api-key": COINGECKO_API_KEY}

    try:
        response = requests.get(ohlcv_url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json().get('data', {}).get('attributes', {}).get('ohlcv_list', [])
        # Transform to match Birdeye format: [t, o, h, l, c, v]
        ohlcv_data = []
        for item in data:
            # item is [timestamp, open, high, low, close, volume]
            if len(item) >= 6:
                ohlcv_data.append({
                    't': int(item[0]),  # timestamp in seconds
                    'o': float(item[1]),  # open price
                    'h': float(item[2]),  # high price
                    'l': float(item[3]),  # low price
                    'c': float(item[4]),  # close price
                    'v': float(item[5])   # volume
                })
        return ohlcv_data
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR fetching OHLCV from CoinGecko: {e}")
        return []

def fetch_multiple_timeframes_coingecko(pool_address: str, network: str = "solana"):
    """Fetches OHLCV data from CoinGecko for multiple timeframes."""
    # Fetch 5-minute data (LTF - Execution timeframe)
    ltf_data = fetch_ohlcv_coingecko(pool_address, network, "minute", 5, 100)
    
    # Fetch 1-hour data (HTF - Bias timeframe)
    htf_data = fetch_ohlcv_coingecko(pool_address, network, "hour", 1, 25)  # 25 hours to get 12+ data points for RSI
    
    return {
        "ltf": ltf_data, # Lower timeframe for execution
        "htf": htf_data   # Higher timeframe for bias
    }

def fetch_birdeye_data(token_address: str, chain: str):
    """Fetches current market data from Birdeye and OHLCV from CoinGecko."""

    if not BIRDEYE_API_KEY or BIRDEYE_API_KEY == "REPLACE_WITH_YOUR_BIRDEYE_KEY":
        print("❌ ERROR: Birdeye API Key is missing or default. Please set BIRDEYE_API_KEY.")
        return {"error": "API Key Missing"}, {}

    headers = {"X-API-KEY": BIRDEYE_API_KEY, "X-CHAIN": chain}

    # Check if this is a native token that requires special handling
    if chain == "solana" and token_address == "So111111112":  # SOL native token
        # Use the correct address for SOL in Birdeye API
        market_url = f"https://public-api.birdeye.so/defi/price?address=So11111111111111111111111111111111111111112&include_liquidity=true&ui_amount_mode=raw"
    else:
        # Use the standard endpoint for all other tokens
        market_url = f"https://public-api.birdeye.so/defi/price?address={token_address}&include_liquidity=true&ui_amount_mode=raw"
    
    try:
        market_response = requests.get(market_url, headers=headers, timeout=10)
        market_response.raise_for_status() # Raise exception for bad status codes
        market_data = market_response.json().get('data', {})
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR fetching market data: {e}")
        # If the standard call fails for SOL, try using just "SOL" as the address
        if chain == "solana" and token_address == "So11111111111111111111111111111111111111112":
            try:
                # Wait a bit more to avoid rate limiting before trying alternative
                time.sleep(5)
                market_url_alt = f"https://public-api.birdeye.so/defi/price?address=SOL&include_liquidity=true&ui_amount_mode=raw"
                market_response_alt = requests.get(market_url_alt, headers=headers, timeout=10)
                market_response_alt.raise_for_status()
                market_data = market_response_alt.json().get('data', {})
            except requests.exceptions.RequestException as e_alt:
                print(f"❌ ERROR fetching market data with alternative SOL endpoint: {e_alt}")
                return {"error": f"Market Data Error: {e_alt}"}, {}
        else:
            return {"error": f"Market Data Error: {e}"}, {}

    # Add delay to avoid rate limiting
    time.sleep(2)

    # 2. Fetch OHLCV from CoinGecko
    pool_address = get_top_pool_coingecko(token_address, chain)
    if pool_address:
        time.sleep(1)  # Delay between calls
        ohlcv_data = fetch_multiple_timeframes_coingecko(pool_address, chain)
    else:
        ohlcv_data = {"ltf": [], "htf": []}

    return market_data, ohlcv_data

# ----------------------------------------------------------------------
# 2. DATA PROCESSING AND ANALYSIS FUNCTION
# ----------------------------------------------------------------------

def process_data(market_data: dict, ohlcv_data: dict) -> str:
    """Calculates technical indicators and formats the payload for Gemini. Uses defaults if no OHLCV data."""

    current_price = market_data.get('value', 0)

    # Get LTF (Lower TimeFrame) and HTF (Higher TimeFrame) data
    ltf_data = ohlcv_data.get("ltf", [])
    htf_data = ohlcv_data.get("htf", [])

    if ltf_data:
        # Convert LTF OHLCV data to a Pandas DataFrame for technical analysis
        df_ltf = pd.DataFrame(ltf_data)
        # Rename columns to standard OHLCV format for 'ta' library
        df_ltf.columns = ['t', 'o', 'h', 'l', 'c', 'v']
        df_ltf['c'] = df_ltf['c'].astype(float) # Ensure close price is float

        # --- Technical Indicator Calculation (LTF) ---

        # Relative Strength Index (RSI)
        df_ltf['RSI'] = ta.momentum.rsi(df_ltf['c'], window=14)
        current_rsi = df_ltf['RSI'].iloc[-1]

        # Moving Average Convergence Divergence (MACD)
        macd_instance = ta.trend.MACD(df_ltf['c'])
        current_macd_signal = macd_instance.macd_signal().iloc[-1]
        current_macd_line = macd_instance.macd().iloc[-1]

        # Simple Price Change (LTF)
        price_change_1hr = ((df_ltf['c'].iloc[-1] - df_ltf['c'].iloc[-12]) / df_ltf['c'].iloc[-12]) * 100 if len(df_ltf) >= 12 else 0

        last_10_close_prices = df_ltf['c'].tail(10).tolist()
        macd_signal = "Bullish Crossover" if current_macd_line > current_macd_signal and current_macd_line is not None else "Bearish Crossover"
    else:
        # Defaults when no LTF OHLCV data
        current_rsi = 50 # Neutral
        current_macd_line = 0
        current_macd_signal = 0
        price_change_1hr = 0
        last_10_close_prices = [current_price] * 10  # Repeat current price
        macd_signal = "Neutral"

    # Calculate HTF indicators if HTF data is available
    if htf_data:
        df_htf = pd.DataFrame(htf_data)
        df_htf.columns = ['t', 'o', 'h', 'l', 'c', 'v']
        df_htf['c'] = df_htf['c'].astype(float)

        # HTF RSI for trend bias
        df_htf['RSI'] = ta.momentum.rsi(df_htf['c'], window=14)
        htf_rsi = df_htf['RSI'].iloc[-1]
        htf_trend = "Bullish" if htf_rsi > 50 else "Bearish" if htf_rsi < 50 else "Neutral"
    else:
        htf_trend = "Unknown"

    # --- Create the Structured Payload for Gemini ---

    analysis_payload = {
        "coin_symbol": market_data.get('symbol', 'N/A'),
        "current_price": current_price,
        "liquidity_usd": market_data.get('liquidity'),
        "volume_24hr": market_data.get('v24h'),
        "price_change_1hr_pct": round(price_change_1hr, 2),
        "RSI_14": round(current_rsi, 2) if current_rsi is not None else "N/A",
        "MACD_signal_cross": macd_signal,
        "last_10_close_prices": last_10_close_prices,
        "htf_trend": htf_trend,  # Higher time frame trend for bias

        # Placeholder for complex analysis that Gemini can interpret
        "FVG_analysis_hint": "No historical data available; focus on current price and market conditions.",
        "onchain_flow_hint": "Assume a large inflow/outflow if liquidity and volume show extreme divergence from price action."
    }

    return json.dumps(analysis_payload)

# ----------------------------------------------------------------------
# 3. GEMINI AGENT ANALYSIS FUNCTION
# ----------------------------------------------------------------------

def generate_trade_signal(analysis_json_string: str) -> dict:
    """Uses the Gemini API to analyze data and output a trade signal."""
    
    if analysis_json_string.startswith('{"error"'):
         return json.loads(analysis_json_string)

    system_prompt = (
        "You are a professional, high-conviction Smart Money Concepts (SMC) trading agent. "
        "Analyze the provided JSON market data, focusing on liquidity, volume, and momentum (RSI/MACD). "
        "Use the last 10 close prices to infer potential market structure shifts, liquidity grabs, or Fair Value Gaps (FVG). "
        "Generate a high-probability trade recommendation for longing (BUY) or shorting (SELL). "
        "Your output MUST be a single JSON object with the keys 'action' (BUY/SELL/HOLD), 'entry_price', 'stop_loss', 'take_profit', 'conviction_score' (1-100), and 'reasoning'."
    )

    user_prompt = f"Analyze the following data and provide a trade signal: {analysis_json_string}"

    try:
        response = client.models.generate_content(
            model='models/gemini-2.5-flash',  # Changed to stable model
            contents=[user_prompt],
            config=genai.types.GenerateContentConfig(
                system_instruction=system_prompt
            )
        )
        # Attempt to parse the expected JSON output
        # The model's response may be wrapped in markdown code blocks
        response_text = response.text.strip()
        if response_text.startswith('```json') and response_text.endswith('```'):
            json_str = response_text[7:-3].strip() # Remove ```json and ```
        else:
            json_str = response_text
        return json.loads(json_str)
    except Exception as e:
        print(f"❌ Error during Gemini API call or JSON parsing: {e}")
        return {"error": f"AI signal generation failed: {e}"}

# ----------------------------------------------------------------------
# 4. MAIN EXECUTION BLOCK
# ----------------------------------------------------------------------
def get_token_address_from_birdeye(token_symbol: str, chain: str = "solana"):
    """Fetches token address from Birdeye using the token symbol."""
    headers = {"X-API-KEY": BIRDEYE_API_KEY}
    
    # Birdeye token search endpoint
    search_url = f"https://public-api.birdeye.so/public/tokenlist?includeNFT=false&chain={chain}"
    
    try:
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        token_list = response.json().get('data', [])
        
        if not token_list:
            print(f"❌ No tokens found in Birdeye tokenlist for chain: {chain}")
            return None
        
        # Find the token that matches the symbol
        for token in token_list:
            if token.get('symbol', '').upper() == token_symbol.upper():
                contract_address = token.get('address')
                if contract_address:
                    return contract_address
        
        print(f"❌ No token found for symbol: {token_symbol} on chain: {chain}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR fetching token address from Birdeye: {e}")
        return None

def get_token_address_from_symbol(token_symbol: str, network: str = "solana"):
    """Fetches token address from CoinGecko using the token symbol, with Birdeye as fallback."""
    # Handle native tokens that don't have contract addresses
    if network == "solana" and token_symbol.upper() == "SOL":
        # SOL is the native token of Solana, use the official placeholder address
        return "So11111111111111111111111111111111111111112"
    elif network == "ethereum" and token_symbol.upper() == "ETH":
        # ETH is the native token of Ethereum
        return "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
    elif network == "bsc" and token_symbol.upper() == "BNB":
        # BNB is the native token of Binance Smart Chain
        return "0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c"
    
    # First, try to get the address from CoinGecko
    contract_address = get_token_address_from_coingecko(token_symbol, network)
    
    # If CoinGecko fails, try Birdeye as fallback
    if not contract_address:
        print(f"⚠️  CoinGecko lookup failed for {token_symbol}, trying Birdeye...")
        contract_address = get_token_address_from_birdeye(token_symbol, network)
    
    return contract_address

def get_token_address_from_coingecko(token_symbol: str, network: str = "solana"):
    """Fetches token address from CoinGecko using the token symbol."""
    # First, try to get the CoinGecko coin ID for the token symbol
    search_url = f"https://api.coingecko.com/api/v3/search?query={token_symbol}"
    headers = {"x-cg-demo-api-key": COINGECKO_API_KEY}
    
    try:
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        search_results = response.json().get('coins', [])
        
        if not search_results:
            print(f"❌ No token found for symbol: {token_symbol} on CoinGecko")
            return None
            
        # Find the coin that matches the symbol
        matching_coin = None
        for coin in search_results:
            if coin.get('symbol', '').upper() == token_symbol.upper():
                matching_coin = coin
                break
        
        if not matching_coin:
            print(f"❌ No exact symbol match found for: {token_symbol} on CoinGecko")
            return None
            
        coin_id = matching_coin['id']
        
        # Now get the contract address for the specific network
        token_url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
        response = requests.get(token_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        token_data = response.json()
        platforms = token_data.get('platforms', {})
        
        # Get the contract address for the specified network
        network_platform_map = {
            'solana': 'solana',
            'ethereum': 'ethereum',
            'bsc': 'binance-smart-chain',
            'polygon': 'polygon-pos'
        }
        
        platform_key = network_platform_map.get(network)
        if not platform_key:
            print(f"❌ Network {network} not supported in CoinGecko mapping")
            return None
            
        contract_address = platforms.get(platform_key)
        if not contract_address:
            print(f"❌ No contract address found for {token_symbol} on {network} via CoinGecko")
            return None
            
        return contract_address
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR fetching token address from CoinGecko: {e}")
        return None

def main():
    """Executes the trading agent's workflow."""
    parser = argparse.ArgumentParser(description='Run the Gemini Trading Agent')
    parser.add_argument('--token', type=str, default='SOL', help='Token symbol (e.g., SOL, BTC, ETH)')
    parser.add_argument('--chain', type=str, default='solana', help='Blockchain network (e.g., solana, ethereum, bsc)')
    
    args = parser.parse_args()
    
    # Get token address from symbol
    token_address = get_token_address_from_symbol(args.token, args.chain)
    if not token_address:
        print(f"❌ Could not find token address for {args.token} on {args.chain}")
        return
        
    print(f"🚀 Starting Gemini Trading Agent for {args.token} ({token_address}) on {args.chain}...")
    
    if not GEMINI_API_KEY or GEMINI_API_KEY == "REPLACE_WITH_YOUR_GEMINI_KEY":
        print("❌ CRITICAL ERROR: Gemini API Key is missing. Please set GEMINI_API_KEY.")
        return
        
    # 1. Fetch Data
    print("...Fetching real-time data...")
    market_data, ohlcv_data = fetch_birdeye_data(token_address, args.chain)
    
    if 'error' in market_data:
        print(f"❌ Failed to start due to data retrieval error: {market_data['error']}")
        return

    # 2. Process Data
    print("...Processing raw data and calculating indicators...")
    analysis_payload = process_data(market_data, ohlcv_data)
    
    # 3. Generate Signal
    print("...Sending structured data to Gemini for high-level analysis...")
    signal = generate_trade_signal(analysis_payload)
    
    # 4. Output/Alert the Result
    if 'error' in signal:
        print(f"\n❌ FAILED SIGNAL GENERATION: {signal['error']}")
    else:
        print("\n" + "="*50)
        print("    🧠 GEMINI HIGH-CONVICTION TRADE SIGNAL")
        print("="*50)
        print(f"   COIN: {market_data.get('symbol', args.token)} @ ${market_data.get('value', 'N/A')}")
        print(f"   ACTION: {signal.get('action', 'N/A').upper()}")
        print(f"   ENTRY PRICE: ${signal.get('entry_price', 'N/A')}")
        print(f"   STOP LOSS: ${signal.get('stop_loss', 'N/A')}")
        print(f"   TAKE PROFIT: ${signal.get('take_profit', 'N/A')}")
        print(f"   CONVICTION: {signal.get('conviction_score', 'N/A')}%")
        print("-" * 50)
        print(f"   REASONING: {signal.get('reasoning', 'N/A')}")
        print("="*50 + "\n")
        
        # NOTE: For a production system, you would replace this print block
        # with an alert mechanism (e.g., email, Telegram, or an exchange API call).


if __name__ == "__main__":
    main()
