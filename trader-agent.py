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

BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY")

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
    
    # Fetch 1-day data (Daily timeframe for more accurate 24H changes)
    daily_data = fetch_ohlcv_coingecko(pool_address, network, "day", 1, 30)  # 30 days to get accurate 24H changes
    
    return {
        "ltf": ltf_data, # Lower timeframe for execution
        "htf": htf_data,   # Higher timeframe for bias
        "daily": daily_data   # Daily timeframe for accurate 24H analysis
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
        ohlcv_data = {"ltf": [], "htf": [], "daily": []}

    return market_data, ohlcv_data

# ----------------------------------------------------------------------
# 2. DATA PROCESSING AND ANALYSIS FUNCTION
# ----------------------------------------------------------------------

def calculate_fair_value_gaps(df):
    """Calculate Fair Value Gaps (FVG) from OHLCV data."""
    if df.empty:
        return []
    
    # A Fair Value Gap occurs when the previous high is lower than the next low (bullish FVG)
    # or when the previous low is higher than the next high (bearish FVG)
    
    # Create shifted columns to compare current and adjacent candles
    df = df.copy() # Avoid modifying the original dataframe
    df['prev_high'] = df['h'].shift(1)
    df['prev_low'] = df['l'].shift(1)
    df['next_high'] = df['h'].shift(-1)
    df['next_low'] = df['l'].shift(-1)
    
    # Bullish FVG: current candle's low is higher than previous candle's high
    # and current candle's high is lower than next candle's low
    bullish_fvg = df[(df['l'] > df['prev_high']) & (df['h'] < df['next_low'])]
    
    # Bearish FVG: current candle's high is lower than previous candle's low
    # and current candle's low is higher than next candle's high
    bearish_fvg = df[(df['h'] < df['prev_low']) & (df['l'] > df['next_high'])]
    
    fvg_list = []
    
    # Add bullish FVGs
    for idx in bullish_fvg.index:
        if not pd.isna(idx) and idx < len(df):
            fvg_list.append({
                'type': 'bullish',
                'zone': [float(df.loc[idx, 'prev_high']), float(df.loc[idx, 'next_low'])],
                'candle_index': int(idx),
                'timeframe': 'current'
            })
    
    # Add bearish FVGs
    for idx in bearish_fvg.index:
        if not pd.isna(idx) and idx < len(df):
            fvg_list.append({
                'type': 'bearish',
                'zone': [float(df.loc[idx, 'next_high']), float(df.loc[idx, 'prev_low'])],
                'candle_index': int(idx),
                'timeframe': 'current'
            })
    
    return fvg_list

def calculate_market_structure(df):
    """Calculate basic market structure elements like higher highs, lower lows, etc."""
    if df.empty:
        return {
            "higher_highs": [],
            "lower_lows": [],
            "higher_lows": [],
            "lower_highs": [],
            "break_of_structure": []
        }
    
    # Calculate swing highs and lows using local maxima/minima
    df = df.copy()
    window = 3  # Look at 3 candles to identify swings
    
    # Identify swing highs (current high is highest in window)
    swing_high_series = (df['h'] > df['h'].shift(1)) & (df['h'] > df['h'].shift(-1))
    # Identify swing lows (current low is lowest in window)
    swing_low_series = (df['l'] < df['l'].shift(1)) & (df['l'] < df['l'].shift(-1))
    
    # Convert boolean series to regular Python boolean values to ensure JSON serialization
    df['swing_high'] = swing_high_series.astype(bool)
    df['swing_low'] = swing_low_series.astype(bool)
    
    # Extract swing points
    swing_highs = df[df['swing_high']]['h'].dropna()
    swing_lows = df[df['swing_low']]['l'].dropna()
    
    # Determine market structure
    structure = {
        "swing_highs": [float(x) for x in swing_highs.tolist()],
        "swing_lows": [float(x) for x in swing_lows.tolist()],
        "recent_high": float(df['h'].tail(10).max()) if len(df) >= 10 else None,
        "recent_low": float(df['l'].tail(10).min()) if len(df) >= 10 else None
    }
    
    return structure

def calculate_volume_analytics(df):
    """Calculate volume-based analytics."""
    if df.empty or 'v' not in df.columns:
        return {
            "volume_trend": "unknown",
            "volume_spike_detected": False,
            "avg_volume_last_10": 0,
            "current_volume_vs_avg": 0
        }
    
    df = df.copy()
    df['vol_ema_short'] = df['v'].ewm(span=5).mean()
    df['vol_ema_long'] = df['v'].ewm(span=20).mean()
    
    # Check for volume spikes (current volume > 2x average)
    recent_avg_vol = df['v'].tail(10).mean()
    current_vol = df['v'].iloc[-1] if len(df) > 0 else 0
    
    volume_spike = current_vol > 2 * recent_avg_vol if recent_avg_vol > 0 else False
    
    # Determine if volume is increasing on dips (if we can identify dips)
    volume_trend = "neutral"
    if len(df) > 20:
        if df['vol_ema_short'].iloc[-1] > df['vol_ema_long'].iloc[-1]:
            volume_trend = "increasing"
        else:
            volume_trend = "decreasing"
    
    return {
        "volume_trend": volume_trend,
        "volume_spike_detected": volume_spike,
        "avg_volume_last_10": float(recent_avg_vol),
        "current_volume_vs_avg": float(current_vol / recent_avg_vol if recent_avg_vol > 0 else 0)
    }

def calculate_volume_profile(df):
    """Calculate basic volume profile metrics."""
    if df.empty or 'v' not in df.columns:
        return {
            'total_volume': 0,
            'avg_volume': 0,
            'high_volume_threshold': 0,
            'low_volume_threshold': 0
        }
    
    total_volume = df['v'].sum()
    avg_volume = df['v'].mean()
    std_volume = df['v'].std()
    
    # Calculate high/low volume thresholds based on standard deviation
    high_volume_threshold = avg_volume + std_volume if not pd.isna(std_volume) else avg_volume * 1.5
    low_volume_threshold = max(0, avg_volume - std_volume) if not pd.isna(std_volume) else avg_volume * 0.5
    
    return {
        'total_volume': float(total_volume),
        'avg_volume': float(avg_volume),
        'high_volume_threshold': float(high_volume_threshold),
        'low_volume_threshold': float(low_volume_threshold)
    }

def calculate_liquidity_levels(df, num_levels=5):
    """Calculate potential liquidity levels based on volume and price action."""
    if df.empty:
        return []
    
    # Calculate support and resistance levels based on high volume nodes
    price_volume = df.groupby(pd.cut(df['c'], bins=num_levels)).agg({
        'v': 'sum',
        'h': 'max',
        'l': 'min'
    }).reset_index()
    
    liquidity_levels = []
    for _, row in price_volume.iterrows():
        if not pd.isna(row['v']):
            # Get the price range for this bin
            bin_range = row['c']
            if hasattr(bin_range, 'left') and hasattr(bin_range, 'right'):
                avg_price = (bin_range.left + bin_range.right) / 2
                liquidity_levels.append({
                    'price': float(avg_price),
                    'volume': float(row['v']),
                    'resistance': float(row['h']),
                    'support': float(row['l'])
                })
    
    # Sort by volume descending to get the most significant levels
    liquidity_levels.sort(key=lambda x: x['volume'], reverse=True)
    return liquidity_levels[:num_levels]

def calculate_order_blocks(df, min_body_ratio=0.6, lookback_period=20):
    """
    Calculate potential order blocks based on SMC concepts.
    Order blocks are identified by:
    1. A significant price move (sharp movement)
    2. The preceding opposite candle that creates the order block zone
    """
    if df.empty:
        return []
    
    df = df.copy()
    df['body'] = abs(df['c'] - df['o'])  # Candle body size
    df['range'] = abs(df['h'] - df['l'])  # Total candle range
    df['body_ratio'] = df['body'] / df['range']  # Ratio of body to total range
    df['is_bullish'] = df['c'] > df['o']
    df['is_bearish'] = df['c'] < df['o']
    
    order_blocks = []
    
    # Iterate through the dataframe to find potential order blocks
    for i in range(2, len(df) - 1):  # Start from 2 to allow for previous candles, end at len-1 to allow for next candles
        # Check if we have a significant move followed by a pullback
        # Current candle is part of the significant move
        current = df.iloc[i]
        prev = df.iloc[i - 1]  # This is the potential order block candle
        two_prev = df.iloc[i - 2]  # This is the candle before the order block candle
        
        # Calculate the size of the significant move (current vs previous candle)
        significant_move_size = abs(current['c'] - prev['h']) if current['c'] > prev['h'] else abs(prev['l'] - current['c'])
        
        # Check if we have a significant move followed by a pullback
        # For bullish order block: look for bearish candle followed by strong bullish move
        if prev['is_bearish'] and current['c'] > prev['h']:  # Bearish candle followed by strong bullish move
            # Check if the move is significant
            avg_range = df['range'].rolling(lookback_period).mean().iloc[i]
            if significant_move_size > avg_range * 0.8:  # Significant move threshold
                order_block = {
                    'type': 'bullish',
                    'high': float(prev['h']),
                    'low': float(prev['l']),
                    'open': float(prev['o']),
                    'close': float(prev['c']),
                    'candle_index': i - 1,  # Index of the order block candle
                    'strength': float(prev['body_ratio']),  # How strong the order block candle was
                    'volume': float(prev['v']) if 'v' in df.columns else 0,
                    'timeframe': 'current'
                }
                
                order_blocks.append(order_block)
        
        # For bearish order block: look for bullish candle followed by strong bearish move
        elif prev['is_bullish'] and current['c'] < prev['l']:  # Bullish candle followed by strong bearish move
            # Check if the move is significant
            avg_range = df['range'].rolling(lookback_period).mean().iloc[i]
            if significant_move_size > avg_range * 0.8:  # Significant move threshold
                order_block = {
                    'type': 'bearish',
                    'high': float(prev['h']),
                    'low': float(prev['l']),
                    'open': float(prev['o']),
                    'close': float(prev['c']),
                    'candle_index': i - 1,  # Index of the order block candle
                    'strength': float(prev['body_ratio']),  # How strong the order block candle was
                    'volume': float(prev['v']) if 'v' in df.columns else 0,
                    'timeframe': 'current'
                }
                
                order_blocks.append(order_block)
    
    return order_blocks

def process_data(market_data: dict, ohlcv_data: dict) -> str:
    """Calculates technical indicators and formats the payload for Gemini. Uses defaults if no OHLCV data."""

    current_price = market_data.get('value', 0)

    # Get LTF (Lower TimeFrame), HTF (Higher TimeFrame), and Daily data
    ltf_data = ohlcv_data.get("ltf", [])
    htf_data = ohlcv_data.get("htf", [])
    daily_data = ohlcv_data.get("daily", [])

    # Initialize variables
    current_rsi = 50
    current_macd_line = 0
    current_macd_signal = 0
    price_change_1hr = 0
    last_10_close_prices = [current_price] * 10
    macd_signal = "Neutral"
    htf_trend = "Unknown"
    ltf_fvg_list = []
    htf_fvg_list = []
    daily_fvg_list = []
    ltf_volume_profile = {}
    htf_volume_profile = {}
    daily_volume_profile = {}
    ltf_liquidity_levels = []
    htf_liquidity_levels = []
    daily_liquidity_levels = []
    ltf_order_blocks = []
    htf_order_blocks = []
    daily_order_blocks = []
    price_change_4h = 0
    price_change_12h = 0
    price_change_24h = 0
    ltf_market_structure = {}
    htf_market_structure = {}
    daily_market_structure = {}
    ltf_volume_analytics = {}
    htf_volume_analytics = {}
    daily_volume_analytics = {}

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
        price_change_4h = ((df_ltf['c'].iloc[-1] - df_ltf['c'].iloc[-48]) / df_ltf['c'].iloc[-48]) * 10 if len(df_ltf) >= 48 else 0
        price_change_12h = ((df_ltf['c'].iloc[-1] - df_ltf['c'].iloc[-144]) / df_ltf['c'].iloc[-144]) * 10 if len(df_ltf) >= 144 else 0
        price_change_24h = ((df_ltf['c'].iloc[-1] - df_ltf['c'].iloc[-288]) / df_ltf['c'].iloc[-288]) * 100 if len(df_ltf) >= 288 else 0

        last_10_close_prices = df_ltf['c'].tail(10).tolist()
        macd_signal = "Bullish Crossover" if current_macd_line > current_macd_signal and current_macd_line is not None else "Bearish Crossover"
        
        # Calculate FVGs for LTF
        ltf_fvg_list = calculate_fair_value_gaps(df_ltf)
        
        # Calculate volume profile for LTF
        ltf_volume_profile = calculate_volume_profile(df_ltf)
        
        # Calculate liquidity levels for LTF
        ltf_liquidity_levels = calculate_liquidity_levels(df_ltf)
        
        # Calculate order blocks for LTF
        ltf_order_blocks = calculate_order_blocks(df_ltf)
        
        # Calculate market structure for LTF
        ltf_market_structure = calculate_market_structure(df_ltf)
        
        # Calculate volume analytics for LTF
        ltf_volume_analytics = calculate_volume_analytics(df_ltf)

    # Calculate HTF indicators if HTF data is available
    if htf_data:
        df_htf = pd.DataFrame(htf_data)
        df_htf.columns = ['t', 'o', 'h', 'l', 'c', 'v']
        df_htf['c'] = df_htf['c'].astype(float)

        # HTF RSI for trend bias
        df_htf['RSI'] = ta.momentum.rsi(df_htf['c'], window=14)
        htf_rsi = df_htf['RSI'].iloc[-1]
        htf_trend = "Bullish" if htf_rsi > 50 else "Bearish" if htf_rsi < 50 else "Neutral"
        
        # Calculate FVGs for HTF
        htf_fvg_list = calculate_fair_value_gaps(df_htf)
        
        # Calculate volume profile for HTF
        htf_volume_profile = calculate_volume_profile(df_htf)
        
        # Calculate liquidity levels for HTF
        htf_liquidity_levels = calculate_liquidity_levels(df_htf)
        
        # Calculate order blocks for HTF
        htf_order_blocks = calculate_order_blocks(df_htf)
        
        # Calculate market structure for HTF
        htf_market_structure = calculate_market_structure(df_htf)
        
        # Calculate volume analytics for HTF
        htf_volume_analytics = calculate_volume_analytics(df_htf)

    # Calculate Daily indicators if Daily data is available
    if daily_data:
        df_daily = pd.DataFrame(daily_data)
        df_daily.columns = ['t', 'o', 'h', 'l', 'c', 'v']
        df_daily['c'] = df_daily['c'].astype(float)

        # Daily RSI for long-term trend bias
        df_daily['RSI'] = ta.momentum.rsi(df_daily['c'], window=14)
        daily_rsi = df_daily['RSI'].iloc[-1]
        
        # Calculate FVGs for Daily
        daily_fvg_list = calculate_fair_value_gaps(df_daily)
        
        # Calculate volume profile for Daily
        daily_volume_profile = calculate_volume_profile(df_daily)
        
        # Calculate liquidity levels for Daily
        daily_liquidity_levels = calculate_liquidity_levels(df_daily)
        
        # Calculate order blocks for Daily
        daily_order_blocks = calculate_order_blocks(df_daily)
        
        # Calculate market structure for Daily
        daily_market_structure = calculate_market_structure(df_daily)
        
        # Calculate volume analytics for Daily
        daily_volume_analytics = calculate_volume_analytics(df_daily)
        
        # Calculate more accurate 24H and 12H changes using daily data
        # 24H change (1 day ago vs current)
        if len(df_daily) >= 2:
            price_change_24h = ((df_daily['c'].iloc[-1] - df_daily['c'].iloc[-2]) / df_daily['c'].iloc[-2]) * 100
        else:
            price_change_24h = 0
            
        # 12H change (approximated using daily data - half day change)
        if len(df_daily) >= 2:
            # For 12H change, we'll use a weighted average between daily and hourly if available
            # If we have both daily and hourly data, we'll use daily data for better accuracy
            # since the daily data is more reliable for longer-term changes
            daily_half_change = ((df_daily['c'].iloc[-1] - df_daily['c'].iloc[-2]) / df_daily['c'].iloc[-2]) * 100
            price_change_12h = daily_half_change / 2  # Approximate 12H as half of daily change
        else:
            price_change_12h = 0

    # Calculate market structure elements
    current_price = float(market_data.get('value', 0)) if market_data.get('value') is not None else 0
    
    # Determine current_price_vs_liquidity based on liquidity levels
    liquidity_description = "neutral"
    if ltf_liquidity_levels:
        # Find the closest support and resistance levels
        sorted_levels = sorted(ltf_liquidity_levels, key=lambda x: x['price'])
        closest_support = None
        closest_resistance = None
        
        for level in sorted_levels:
            if level['price'] < current_price and (closest_support is None or level['price'] > closest_support):
                closest_support = level['price']
            elif level['price'] > current_price and (closest_resistance is None or level['price'] < closest_resistance):
                closest_resistance = level['price']
        
        if closest_support is not None and closest_resistance is not None:
            if current_price > (closest_support + closest_resistance) / 2:
                liquidity_description = "above_support"
            else:
                liquidity_description = "below_resistance"
        elif closest_support is not None and current_price > closest_support:
            liquidity_description = "above_support"
        elif closest_resistance is not None and current_price < closest_resistance:
            liquidity_description = "below_resistance"
        elif closest_support is not None and closest_resistance is not None and closest_support <= current_price <= closest_resistance:
            liquidity_description = "between_levels"
    
    # Determine volume_price_relationship based on volume analytics
    volume_price_relationship = "neutral"
    if ltf_volume_analytics:
        vol_trend = ltf_volume_analytics.get("volume_trend", "neutral")
        vol_vs_avg = ltf_volume_analytics.get("current_volume_vs_avg", 0)
        
        if vol_trend == "increasing" and vol_vs_avg > 1.5:
            volume_price_relationship = "high_volume_increasing"
        elif vol_trend == "decreasing" and vol_vs_avg < 0.5:
            volume_price_relationship = "low_volume_decreasing"
        elif vol_trend == "increasing":
            volume_price_relationship = "volume_increasing"
        elif vol_trend == "decreasing":
            volume_price_relationship = "volume_decreasing"
        else:
            volume_price_relationship = "neutral"
    
    # Determine momentum_direction based on RSI and MACD
    momentum_direction = "neutral"
    if current_rsi is not None and not pd.isna(current_rsi):
        if current_rsi > 70:
            momentum_direction = "overbought"
        elif current_rsi < 30:
            momentum_direction = "oversold"
        elif current_rsi > 50:
            momentum_direction = "bullish"
        else:
            momentum_direction = "bearish"
    
    # Additional check using MACD if available
    if current_macd_line is not None and current_macd_signal is not None:
        if current_macd_line > current_macd_signal:
            if momentum_direction == "bullish" or momentum_direction == "overbought":
                momentum_direction = "strong_bullish"
            else:
                momentum_direction = "turning_bullish"
        else:
            if momentum_direction == "bearish" or momentum_direction == "oversold":
                momentum_direction = "strong_bearish"
            else:
                momentum_direction = "turning_bearish"
    
    # --- Create the Structured Payload for Gemini ---

    # Helper function to convert data to JSON serializable format
    def convert_to_serializable(obj):
        if isinstance(obj, dict):
            return {str(k): convert_to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_to_serializable(item) for item in obj]
        elif isinstance(obj, (int, float)):
            return float(obj)
        elif isinstance(obj, bool):
            return str(obj)  # Convert booleans to strings
        elif isinstance(obj, str):
            return obj
        elif obj is None:
            return None
        else:
            return str(obj)  # Convert everything else to string

    # Convert all data to ensure JSON serializability
    analysis_payload = {
        "coin_symbol": str(market_data.get('symbol', 'N/A')),
        "current_price": float(current_price) if current_price is not None else 0,
        "liquidity_usd": float(market_data.get('liquidity', 0)) if market_data.get('liquidity') is not None else 0,
        "volume_24hr": float(market_data.get('volume', market_data.get('v24h', 0))) if (market_data.get('volume') is not None or market_data.get('v24h') is not None) else 0,
        "price_change_1h_pct": round(float(price_change_1hr), 2) if price_change_1hr is not None and not pd.isna(price_change_1hr) else 0,
        "price_change_4h_pct": round(float(price_change_4h), 2) if price_change_4h is not None and not pd.isna(price_change_4h) else 0,
        "price_change_12h_pct": round(float(price_change_12h), 2) if price_change_12h is not None and not pd.isna(price_change_12h) else 0,
        "price_change_24h_pct": round(float(price_change_24h), 2) if price_change_24h is not None and not pd.isna(price_change_24h) else 0,
        "RSI_14": round(float(current_rsi), 2) if current_rsi is not None and not pd.isna(current_rsi) else "N/A",
        "RSI_14_HTF": round(float(htf_rsi), 2) if 'htf_rsi' in locals() and htf_rsi is not None and not pd.isna(htf_rsi) else "N/A",
        "RSI_14_daily": round(float(daily_rsi), 2) if 'daily_rsi' in locals() and daily_rsi is not None and not pd.isna(daily_rsi) else "N/A",
        "MACD_signal_cross": str(macd_signal) if macd_signal is not None else "Neutral",
        "last_10_close_prices": [float(price) for price in last_10_close_prices if price is not None],
        "htf_trend": str(htf_trend) if htf_trend is not None else "Unknown",
        
        # Fair Value Gaps
        "ltf_fair_value_gaps": ltf_fvg_list,
        "htf_fair_value_gaps": htf_fvg_list,
        "daily_fair_value_gaps": daily_fvg_list,
        
        # Volume Profile
        "ltf_volume_profile": ltf_volume_profile,
        "htf_volume_profile": htf_volume_profile,
        "daily_volume_profile": daily_volume_profile,
        
        # Liquidity Levels
        "ltf_liquidity_levels": ltf_liquidity_levels,
        "htf_liquidity_levels": htf_liquidity_levels,
        "daily_liquidity_levels": daily_liquidity_levels,
        
        # Order Blocks
        "ltf_order_blocks": ltf_order_blocks,
        "htf_order_blocks": htf_order_blocks,
        "daily_order_blocks": daily_order_blocks,
        
        # Market Structure
        "ltf_market_structure": ltf_market_structure,
        "htf_market_structure": htf_market_structure,
        "daily_market_structure": daily_market_structure,
        
        # Volume Analytics
        "ltf_volume_analytics": ltf_volume_analytics,
        "htf_volume_analytics": htf_volume_analytics,
        "daily_volume_analytics": daily_volume_analytics,
        
        # Additional market structure data
        "market_structure": {
            "current_price_vs_liquidity": liquidity_description,
            "volume_price_relationship": volume_price_relationship,
            "momentum_direction": momentum_direction
        }
    }

    # Apply conversion to ensure all data is serializable
    analysis_payload = convert_to_serializable(analysis_payload)
    return json.dumps(analysis_payload)

# ----------------------------------------------------------------------
# 3. GEMINI AGENT ANALYSIS FUNCTION
# ----------------------------------------------------------------------

def generate_comprehensive_analysis(analysis_json_string: str) -> dict:
    """Uses the Gemini API to analyze data and output a comprehensive market analysis."""
    
    if analysis_json_string.startswith('{"error"'):
         return json.loads(analysis_json_string)

    # Extract coin symbol from the analysis JSON string
    try:
        analysis_data = json.loads(analysis_json_string)
        coin_symbol = analysis_data.get("coin_symbol", "N/A")
    except json.JSONDecodeError:
        coin_symbol = "N/A"

    system_prompt = (
        f"You are a professional, high-conviction Smart Money Concepts (SMC) trading analyst. "
        f"Analyze the provided JSON market data comprehensively, focusing on liquidity, volume, momentum (RSI/MACD), "
        f"Fair Value Gaps (FVGs), Order Blocks, and market structure for {coin_symbol}. "
        f"Provide a detailed analysis in the following format:\n\n"
        f"⚡ Live {coin_symbol} Market Overview\n"
        f"Current Price: [price] (Birdeye live)\n"
        f"24h Change: [change]%\n"
        f"Volume (24h): ~$[volume] ([change]%)\n"
        f"Liquidity: ~$[liquidity] — [description of liquidity conditions].\n\n"
        f"🔍 Price & Momentum Read\n"
        f"Timeframe | Change | Structure | Momentum\n"
        f"1H | [change]% | [structure] | [momentum]\n"
        f"4H | [change]% | [structure] | [momentum]\n"
        f"12H | [change]% | [structure] | [momentum]\n"
        f"24H | [change]% | [structure] | [momentum]\n\n"
        f"Short-term: [analysis].\n\n"
        f"Medium-term: [analysis].\n\n"
        f"Volume: [analysis].\n\n"
        f"Wallet inflows: [analysis if available, otherwise mention it's not available].\n\n"
        f"👉 This tells us: [synthesis of momentum and market conditions].\n\n"
        f"💧 Liquidity & Order Flow\n"
        f"Resting liquidity:\n\n"
        f"Buy side: [analysis based on liquidity levels]\n"
        f"Sell side: [analysis based on liquidity levels]\n\n"
        f"Liquidity imbalance shows [analysis] → [trading implications].\n\n"
        f"📊 Fair Value Gaps (FVGs)\n"
        f"Zone | Type | Impact\n"
        f"[list FVGs with price zones, type (bullish/bearish), and impact]\n\n"
        f"🏗️ Order Blocks\n"
        f"Timeframe | Type | Price Zone | Strength | Volume\n"
        f"[list order blocks with timeframe (LTF/HTF), type (bullish/bearish), price zone (high/low), strength, and volume]\n\n"
        f"🧭 Trading Plan\n"
        f"🎯 [Preferred setup name] Setup ([long/short] preferred)\n\n"
        f"Entry: [price/range]\n\n"
        f"Stop Loss: [price]\n\n"
        f"TP1: [price]\n\n"
        f"TP2: [price]\n\n"
        f"R:R: [ratio]\n\n"
        f"[Additional setup details]\n\n"
        f"✅ My Take\n\n"
        f"Given the data:\n\n"
        f"[Key points from analysis including order blocks]\n\n"
        f"👉 I'm [bias] [detailed explanation of trading bias and plan]"
    )

    user_prompt = f"Analyze the following data and provide a comprehensive market analysis: {analysis_json_string}"

    try:
        response = client.models.generate_content(
            model='models/gemini-2.5-flash',  # Changed to stable model
            contents=[user_prompt],
            config=genai.types.GenerateContentConfig(
                system_instruction=system_prompt
            )
        )
        return {"analysis": response.text}
    except Exception as e:
        print(f"❌ Error during Gemini API call: {e}")
        return {"error": f"AI analysis generation failed: {e}"}

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
    parser.add_argument('--mode', type=str, default='signal', choices=['signal', 'analysis'], help='Output mode: signal for trade signal, analysis for comprehensive market analysis')
    
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
    
    # Update the market data to include the token symbol if it's not present
    if not market_data.get('symbol'):
        market_data['symbol'] = args.token
    
    analysis_payload = process_data(market_data, ohlcv_data)
    
    # 3. Generate Analysis/Signal based on mode
    print("...Sending structured data to Gemini for high-level analysis...")
    if args.mode == 'analysis':
        # Update the analysis payload to include the coin symbol properly before calling analysis
        analysis_payload_dict = json.loads(analysis_payload)
        analysis_payload_dict["coin_symbol"] = args.token
        analysis_payload = json.dumps(analysis_payload_dict)
        
        # Optional: Print the data being sent to Gemini for debugging (can be removed)
        # print("\n" + "-"*60)
        # print("    DATA BEING SENT TO GEMINI FOR ANALYSIS")
        # print("-"*60)
        # print(json.dumps(json.loads(analysis_payload), indent=2))
        # print("-"*60 + "\n")
        
        result = generate_comprehensive_analysis(analysis_payload)
        if 'analysis' in result:
            print("\n" + "="*60)
            print("    📊 COMPREHENSIVE MARKET ANALYSIS")
            print("="*60)
            print(result['analysis'])
            print("="*60 + "\n")
        elif 'error' in result:
            print(f"\n❌ FAILED ANALYSIS GENERATION: {result['error']}")
    else: # Default to signal mode
        signal = generate_trade_signal(analysis_payload)
        
        # 4. Output/Alert the Result
        if 'error' in signal:
            print(f"\n❌ FAILED SIGNAL GENERATION: {signal['error']}")
        else:
            print("\n" + "="*50)
            print("    🧠 GEMINI HIGH-CONVICTION TRADE SIGNAL")
            print("="*50)
            coin_symbol = market_data.get('symbol', args.token)
            print(f"   COIN: {coin_symbol} @ ${market_data.get('value', 'N/A')}")
            
            # Update the analysis payload to include the coin symbol properly
            analysis_payload_dict = json.loads(analysis_payload)
            analysis_payload_dict["coin_symbol"] = coin_symbol
            analysis_payload = json.dumps(analysis_payload_dict)
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
