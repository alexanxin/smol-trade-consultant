#!/usr/bin/env python3
import os
import json
import requests
import pandas as pd
import time
import sys
import argparse
import subprocess
from dotenv import load_dotenv
from output_formatter import OutputFormatter
from news_agent import NewsAgent
from risk_manager import RiskManager
from database import LifecycleDatabase
from wallet_manager import SolanaWallet
from jupiter_client import JupiterClient
from drift_client_wrapper import DriftClientWrapper
from datetime import datetime

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

# Additional library for candlestick pattern recognition
try:
    import tulipy as ti
except ImportError:
    print("Note: tulipy library is not installed. Some advanced candlestick patterns may not be available.")
    ti = None

# --- CONFIGURATION (UPDATE THESE OR USE ENVIRONMENT VARIABLES) ---

# It is highly recommended to set these as environment variables for security:
# export BIRDEYE_API_KEY="your-birdeye-key"
# export GEMINI_API_KEY="your-gemini-key"

BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY")

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

def calculate_volume_profile(df, num_bins=20):
    """Calculate comprehensive volume profile with POC and LVN detection."""
    if df.empty or 'v' not in df.columns:
        return {
            'total_volume': 0,
            'avg_volume': 0,
            'high_volume_threshold': 0,
            'low_volume_threshold': 0,
            'poc_price': 0,
            'poc_volume': 0,
            'low_volume_nodes': [],
            'high_volume_nodes': [],
            'value_area_high': 0,
            'value_area_low': 0,
            'imbalance_zones': []
        }
    
    df = df.copy()
    total_volume = df['v'].sum()
    avg_volume = df['v'].mean()
    std_volume = df['v'].std()
    
    # Create price bins for volume profile
    price_range = df['h'].max() - df['l'].min()
    bin_size = price_range / num_bins if num_bins > 0 else price_range
    
    # Calculate volume distribution across price levels
    bins = pd.cut(df['c'], bins=num_bins, labels=False)
    volume_profile = df.groupby(bins).agg({
        'v': 'sum',
        'c': 'mean',
        'h': 'max',
        'l': 'min'
    })
    
    # Access data directly without reset_index to avoid column conflicts
    # Find Point of Control (highest volume bin)
    poc_idx = volume_profile['v'].idxmax()
    poc_price = volume_profile.loc[poc_idx, 'c']
    poc_volume = volume_profile.loc[poc_idx, 'v']
    
    # Find Low Volume Nodes (bottom 20% of volume distribution)
    volume_threshold_20pct = volume_profile['v'].quantile(0.2)
    lvn_candidates = volume_profile[volume_profile['v'] <= volume_threshold_20pct]
    low_volume_nodes = []
    
    for bin_idx, node in lvn_candidates.iterrows():
        low_volume_nodes.append({
            'price': float(node['c']),
            'volume': float(node['v']),
            'strength': 'low' if node['v'] <= volume_profile['v'].quantile(0.1) else 'medium'
        })
    
    # Find High Volume Nodes (top 20% of volume distribution)
    volume_threshold_80pct = volume_profile['v'].quantile(0.8)
    hvn_candidates = volume_profile[volume_profile['v'] >= volume_threshold_80pct]
    high_volume_nodes = []
    
    for bin_idx, node in hvn_candidates.iterrows():
        high_volume_nodes.append({
            'price': float(node['c']),
            'volume': float(node['v']),
            'strength': 'high' if node['v'] >= volume_profile['v'].quantile(0.9) else 'medium'
        })
    
    # Calculate Value Area (70% of volume around POC)
    sorted_volume = volume_profile.sort_values('v', ascending=False)
    cumulative_volume = 0
    target_volume = total_volume * 0.70
    value_area_high = poc_price
    value_area_low = poc_price
    
    for bin_idx, row in sorted_volume.iterrows():
        if cumulative_volume < target_volume:
            value_area_low = min(value_area_low, row['c'])
            value_area_high = max(value_area_high, row['c'])
            cumulative_volume += row['v']
        else:
            break
    
    # Detect imbalance zones (areas where price moved quickly through low volume)
    imbalance_zones = []
    for i in range(1, len(df)):
        prev_bar = df.iloc[i-1]
        curr_bar = df.iloc[i]
        
        # Look for quick moves through low volume areas
        price_move_pct = abs(curr_bar['c'] - prev_bar['c']) / prev_bar['c']
        volume_vs_avg = curr_bar['v'] / avg_volume if avg_volume > 0 else 1
        
        if price_move_pct > 0.02 and volume_vs_avg < 0.8:  # 2% move with below-average volume
            direction = 'bullish' if curr_bar['c'] > prev_bar['c'] else 'bearish'
            imbalance_zones.append({
                'type': direction,
                'price_range': [float(min(prev_bar['l'], curr_bar['l'])), float(max(prev_bar['h'], curr_bar['h']))],
                'strength': 'strong' if price_move_pct > 0.05 else 'medium'
            })
    
    return {
        'total_volume': float(total_volume),
        'avg_volume': float(avg_volume),
        'high_volume_threshold': float(avg_volume + std_volume) if not pd.isna(std_volume) else avg_volume * 1.5,
        'low_volume_threshold': float(max(0, avg_volume - std_volume)) if not pd.isna(std_volume) else avg_volume * 0.5,
        'poc_price': float(poc_price),
        'poc_volume': float(poc_volume),
        'low_volume_nodes': low_volume_nodes,
        'high_volume_nodes': high_volume_nodes,
        'value_area_high': float(value_area_high),
        'value_area_low': float(value_area_low),
        'imbalance_zones': imbalance_zones,
        'volume_concentration': float(poc_volume / total_volume) if total_volume > 0 else 0
    }

def calculate_liquidity_levels(df, num_levels=5):
    """Calculate potential liquidity levels based on volume and price action."""
    if df.empty:
        return []
    
    # Calculate support and resistance levels based on high volume nodes
    price_volume = df.groupby(pd.cut(df['c'], bins=num_levels), observed=False).agg({
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

def detect_high_probability_setups(analysis_data):
    """
    Detect high-probability trading setups using multiple confluence factors.
    Combines Fabio Valentino methodology with traditional SMC analysis.
    """
    if not analysis_data:
        return []
    
    setups = []
    
    # Extract key data
    fabio_data = analysis_data.get("fabio_valentino_analysis", {})
    ltf_market_state = fabio_data.get("ltf_market_state", {})
    ltf_order_flow = fabio_data.get("ltf_order_flow", {})
    htf_market_state = fabio_data.get("htf_market_state", {})
    ltf_volume_profile = analysis_data.get("ltf_volume_profile", {})
    htf_volume_profile = analysis_data.get("htf_volume_profile", {})
    current_session = analysis_data.get("current_trading_session", "Low_Volume")
    
    # Current market data
    current_price = float(analysis_data.get("current_price", 0))
    rsi_14 = analysis_data.get("RSI_14", 50)
    macd_signal = analysis_data.get("MACD_signal_cross", "Neutral")
    
    # Pattern analysis
    ltf_patterns = analysis_data.get("ltf_candlestick_patterns", [])
    htf_patterns = analysis_data.get("htf_candlestick_patterns", [])
    daily_patterns = analysis_data.get("daily_candlestick_patterns", [])
    
    # 1. FABIO VALENTINO HIGH-PROBABILITY SETUPS
    
    # A. Trend Following Setup (Imbalance Phase)
    if (ltf_market_state.get("state") == "imbalanced" and
        ltf_order_flow.get("aggressive_orders", False) and
        current_session == "New_York"):
        
        setup_score = 0
        confluence_factors = []
        
        # Volume Profile Validation
        poc_price = ltf_volume_profile.get("poc_price", 0)
        if poc_price > 0:
            poc_distance = abs(current_price - poc_price) / current_price
            if poc_distance < 0.02:  # Within 2% of POC
                setup_score += 25
                confluence_factors.append("Near POC target")
        
        # Order Flow Confirmation
        if ltf_order_flow.get("cvd_trend", "") == ltf_market_state.get("imbalance_direction"):
            setup_score += 20
            confluence_factors.append("CVD trend alignment")
        
        # Multi-timeframe bias
        htf_direction = htf_market_state.get("imbalance_direction")
        if htf_direction and htf_direction == ltf_market_state.get("imbalance_direction"):
            setup_score += 15
            confluence_factors.append("HTF bias alignment")
        
        # RSI confluence
        if isinstance(rsi_14, (int, float)):
            if ltf_market_state.get("imbalance_direction") == "bullish" and 30 < rsi_14 < 70:
                setup_score += 15
                confluence_factors.append("RSI in favorable range")
            elif ltf_market_state.get("imbalance_direction") == "bearish" and 30 < rsi_14 < 70:
                setup_score += 15
                confluence_factors.append("RSI in favorable range")
        
        # High conviction patterns
        high_strength_patterns = [p for p in ltf_patterns if p.get("strength") == "high"]
        if high_strength_patterns:
            setup_score += 15
            confluence_factors.append(f"{len(high_strength_patterns)} high-strength patterns")
        
        if setup_score >= 60:  # Threshold for high probability
            setups.append({
                "setup_type": "Trend Following",
                "direction": ltf_market_state.get("imbalance_direction"),
                "probability": min(setup_score, 95),
                "entry_criteria": f"Break of structure with {ltf_market_state.get('imbalance_direction')} bias",
                "target": f"POC at ${poc_price:.4f}" if poc_price > 0 else "Previous balance area",
                "confidence_level": "HIGH" if setup_score >= 80 else "MEDIUM",
                "confluence_factors": confluence_factors,
                "session_optimization": "NY Session - Optimal for trend following",
                "risk_management": "Aggressive stops below/above aggression"
            })
    
    # B. Mean Reversion Setup (Balanced Phase)
    elif (ltf_market_state.get("state") == "balanced" and
          current_session in ["London", "New_York"]):
        
        setup_score = 0
        confluence_factors = []
        
        # Check for deep discount/premium
        balance_center = ltf_market_state.get("balance_center", current_price)
        balance_range = ltf_market_state.get("balance_high", current_price) - ltf_market_state.get("balance_low", current_price)
        
        price_vs_balance = (current_price - balance_center) / balance_range if balance_range > 0 else 0
        
        if abs(price_vs_balance) > 0.015:  # 1.5% away from balance center
            setup_score += 30
            confluence_factors.append("Price at deep discount/premium")
        
        # Volume profile support/resistance
        poc_price = ltf_volume_profile.get("poc_price", 0)
        if poc_price > 0:
            poc_distance = abs(current_price - poc_price) / current_price
            if poc_distance < 0.025:  # Within 2.5% of POC
                setup_score += 25
                confluence_factors.append("Near POC (70% reversal probability)")
        
        # Order flow confirmation
        if ltf_order_flow.get("cvd_trend", "") != ltf_market_state.get("imbalance_direction"):
            setup_score += 20
            confluence_factors.append("Counter-trend CVD signal")
        
        # RSI oversold/overbought
        if isinstance(rsi_14, (int, float)):
            if price_vs_balance < -0.015 and rsi_14 < 40:  # Deep discount + oversold
                setup_score += 20
                confluence_factors.append("Oversold conditions")
            elif price_vs_balance > 0.015 and rsi_14 > 60:  # Deep premium + overbought
                setup_score += 20
                confluence_factors.append("Overbought conditions")
        
        # Session timing
        if current_session == "London":
            setup_score += 10
            confluence_factors.append("London session optimal for mean reversion")
        
        if setup_score >= 65:  # Slightly higher threshold for mean reversion
            direction = "long" if price_vs_balance < 0 else "short"
            setups.append({
                "setup_type": "Mean Reversion",
                "direction": direction,
                "probability": min(setup_score, 95),
                "entry_criteria": "Retracement from deep discount/premium",
                "target": f"POC at ${poc_price:.4f}" if poc_price > 0 else "Balance center",
                "confidence_level": "HIGH" if setup_score >= 85 else "MEDIUM",
                "confluence_factors": confluence_factors,
                "session_optimization": f"{current_session} session timing",
                "risk_management": "Tight stops, quick break-even movement"
            })
    
    # 2. TRADITIONAL SMC HIGH-PROBABILITY SETUPS
    
    # C. FVG Continuation Setup
    ltf_fvgs = analysis_data.get("ltf_fair_value_gaps", [])
    if ltf_fvgs:
        # Check for price interacting with FVG
        relevant_fvgs = [fvg for fvg in ltf_fvgs if (fvg.get("type") == "bullish" and rsi_14 < 50) or (fvg.get("type") == "bearish" and rsi_14 >= 50)]
        
        if relevant_fvgs:
            fvg_score = 0
            confluence_factors = []
            
            # Multiple timeframe FVG alignment
            htf_fvgs = analysis_data.get("htf_fair_value_gaps", [])
            aligned_fvgs = 0
            
            for ltf_fvg in relevant_fvgs:
                for htf_fvg in htf_fvgs:
                    if (ltf_fvg.get("type") == htf_fvg.get("type") and
                        abs(ltf_fvg.get("zone", [0])[0] - htf_fvg.get("zone", [0])[0]) / current_price < 0.01):
                        aligned_fvgs += 1
                        break
            
            if aligned_fvgs > 0:
                fvg_score += 25
                confluence_factors.append("Multi-timeframe FVG alignment")
            
            # Pattern confluence
            pattern_count = len([p for p in ltf_patterns if p.get("strength") == "high"])
            if pattern_count >= 2:
                fvg_score += 20
                confluence_factors.append(f"{pattern_count} high-strength patterns")
            
            # Volume confirmation
            ltf_volume_analytics = analysis_data.get("ltf_volume_analytics", {})
            if ltf_volume_analytics.get("volume_spike_detected", False):
                fvg_score += 15
                confluence_factors.append("Volume spike confirmation")
            
            if fvg_score >= 50:
                setups.append({
                    "setup_type": "FVG Continuation",
                    "direction": "bullish" if rsi_14 < 50 else "bearish",
                    "probability": fvg_score,
                    "entry_criteria": "Price reaction at FVG level",
                    "target": "Next FVG or structure level",
                    "confidence_level": "MEDIUM" if fvg_score >= 70 else "LOW",
                    "confluence_factors": confluence_factors,
                    "session_optimization": "Any session with volume",
                    "risk_management": "Stop below/above FVG boundary"
                })
    
    return sorted(setups, key=lambda x: x.get("probability", 0), reverse=True)


def detect_candlestick_patterns(df):
    """
    Detect candlestick patterns that may indicate potential bull run ending patterns.
    Includes outside bar engulfing, evening star, and gravestone doji patterns.
    """
    if df.empty:
        return []
    
    df = df.copy()
    df['body'] = abs(df['c'] - df['o'])  # Candle body size
    df['range'] = abs(df['h'] - df['l'])  # Total candle range
    df['body_ratio'] = df['body'] / df['range'].replace(0, 1)  # Avoid division by zero
    df['is_bullish'] = df['c'] > df['o']
    df['is_bearish'] = df['c'] < df['o']
    
    patterns = []
    
    # Detect outside bar/engulfing patterns
    # An outside bar occurs when the current candle's range completely engulfs the previous candle's range
    for i in range(1, len(df)):
        current = df.iloc[i]
        prev = df.iloc[i - 1]
        
        # Outside bar - current candle's high > previous candle's high AND current candle's low < previous candle's low
        if current['h'] > prev['h'] and current['l'] < prev['l']:
            # Determine if it's a bullish or bearish engulfing pattern
            pattern_type = 'bullish_engulfing' if (current['c'] > current['o'] and prev['c'] < prev['o']) else 'bearish_engulfing'
            if current['c'] > current['o'] and prev['c'] < prev['o']:
                pattern_type = 'bullish_engulfing'
            elif current['c'] < current['o'] and prev['c'] > prev['o']:
                pattern_type = 'bearish_engulfing'
            else:
                pattern_type = 'outside_bar'
            
            pattern = {
                'pattern_type': pattern_type,
                'candle_index': i,
                'timeframe': 'current',
                'strength': 'high' if df['body_ratio'].iloc[i] > 0.8 else 'medium',
                'price': float(current['c']),
                'description': f"Outside bar pattern detected - current candle completely engulfs previous candle"
            }
            patterns.append(pattern)
    
    # Detect evening star pattern (bearish reversal pattern)
    # Three candle pattern: large bullish candle, small-bodied candle (star), large bearish candle
    for i in range(2, len(df)):
        third = df.iloc[i]      # Current candle (large bearish)
        second = df.iloc[i - 1] # Middle candle (star)
        first = df.iloc[i - 2]  # First candle (large bullish)
        
        # Evening star conditions:
        # 1. First candle is bullish with large body
        # 2. Second candle gaps up and has small body
        # 3. Third candle is bearish and closes well into first candle's body
        first_body = abs(first['c'] - first['o'])
        second_body = abs(second['c'] - second['o'])
        third_body = abs(third['c'] - third['o'])
        
        first_range = first['h'] - first['l']
        second_range = second['h'] - second['l']
        third_range = third['h'] - third['l']
        
        # Check if first candle is bullish and has a large body
        first_bullish_large = first_range > 0 and first['c'] > first['o'] and first_body / first_range > 0.7
        
        # Check if second candle has a small body (star)
        second_small = second_range > 0 and second_body / second_range < 0.3
        
        # Check if second candle gaps above first candle
        second_gaps_up = min(second['o'], second['c']) > max(first['o'], first['c'])
        
        # Check if third candle is bearish and large
        third_bearish_large = third_range > 0 and third['o'] > third['c'] and third_body / third_range > 0.7
        
        # Check if third candle closes well into first candle's body
        third_closes_deep = third['c'] < (first['o'] + first['c']) / 2
        
        if first_bullish_large and second_small and second_gaps_up and third_bearish_large and third_closes_deep:
            pattern = {
                'pattern_type': 'evening_star',
                'candle_index': i,
                'timeframe': 'current',
                'strength': 'high',
                'price': float(third['c']),
                'description': f"Evening star pattern detected - potential bearish reversal after uptrend"
            }
            patterns.append(pattern)
    
    # Detect gravestone doji - long upper shadow, very small body, little or no lower shadow
    # This pattern suggests rejection of higher prices and potential reversal
    for i in range(len(df)):
        current = df.iloc[i]
        
        body_size = abs(current['c'] - current['o'])
        upper_shadow = current['h'] - max(current['o'], current['c'])
        lower_shadow = min(current['o'], current['c']) - current['l']
        total_range = current['h'] - current['l']
        
        # Gravestone doji conditions:
        # 1. Very small body (small portion of total range)
        # 2. Long upper shadow (significant portion of total range)
        # 3. Little or no lower shadow
        if total_range > 0:
            is_gravestone = (body_size / total_range < 0.1 and 
                             upper_shadow / total_range > 0.7 and 
                             lower_shadow / total_range < 0.1)
        else:
            is_gravestone = False
        
        if is_gravestone:
            pattern = {
                'pattern_type': 'gravestone_doji',
                'candle_index': i,
                'timeframe': 'current',
                'strength': 'high',
                'price': float(current['c']),
                'description': f"Gravestone doji detected - potential reversal signal at top of trend"
            }
            patterns.append(pattern)
    
    return patterns

def get_current_session():
    """Determine current trading session based on UTC time."""
    from datetime import datetime, timezone
    
    current_utc = datetime.now(timezone.utc)
    hour = current_utc.hour
    
    # Market sessions in UTC (non-overlapping priority: NY > London > Asian)
    # New York session: 13:00-21:00 UTC (8:00 AM - 4:00 PM EST)
    if 13 <= hour < 21:
        return "New_York"
    # London session: 8:00-13:00 UTC (overlaps with NY start, but NY takes priority)
    elif 8 <= hour < 13:
        return "London"
    # Asian session: 0:00-8:00 UTC (Tokyo: 9:00 AM - 5:00 PM JST)
    elif 0 <= hour < 8:
        return "Asian"
    # Low volume period: 21:00-24:00 UTC (after NY close, before Asian open)
    else:
        return "Low_Volume"

def detect_market_state(df, volume_profile_data):
    """
    Detect market state using Auction Market Theory:
    - Balanced: Price is consolidating within a range
    - Imbalanced: Price is moving directionally seeking new balance
    """
    if df.empty or len(df) < 10:
        return {
            "state": "unknown",
            "balance_high": 0,
            "balance_low": 0,
            "balance_center": 0,
            "imbalance_direction": None,
            "strength": "low"
        }
    
    # Get recent price data for analysis
    recent_df = df.tail(20)  # Last 20 candles
    current_price = df['c'].iloc[-1]
    
    # Calculate price range and volatility
    price_range = recent_df['h'].max() - recent_df['l'].min()
    avg_range = recent_df['h'] - recent_df['l']
    volatility = avg_range.mean()
    
    # Calculate mean price for balance center
    balance_center = recent_df['c'].mean()
    
    # Determine balance range (80% of price movement around center)
    balance_range = price_range * 0.8
    balance_high = balance_center + balance_range / 2
    balance_low = balance_center - balance_range / 2
    
    # Check for directional movement vs range-bound behavior
    price_changes = recent_df['c'].pct_change().dropna()
    positive_changes = (price_changes > 0).sum()
    negative_changes = (price_changes < 0).sum()
    
    # Calculate trend strength
    total_changes = len(price_changes)
    directional_bias = abs(positive_changes - negative_changes) / total_changes if total_changes > 0 else 0
    
    # Determine market state
    if directional_bias < 0.3:  # Less than 30% directional bias = balanced
        state = "balanced"
        imbalance_direction = None
        strength = "strong" if directional_bias < 0.15 else "medium"
    else:
        state = "imbalanced"
        if positive_changes > negative_changes:
            imbalance_direction = "bullish"
        else:
            imbalance_direction = "bearish"
        strength = "strong" if directional_bias > 0.6 else "medium"
    
    return {
        "state": state,
        "balance_high": float(balance_high),
        "balance_low": float(balance_low),
        "balance_center": float(balance_center),
        "imbalance_direction": imbalance_direction,
        "strength": strength,
        "directional_bias": float(directional_bias),
        "current_price_vs_balance": float((current_price - balance_center) / balance_center) if balance_center > 0 else 0
    }

def analyze_order_flow_pressure(df, volume_profile_data):
    """
    Simulate order flow analysis by analyzing volume-price relationships.
    This provides leading insights into market participation.
    """
    if df.empty or len(df) < 5:
        return {
            "buying_pressure": "neutral",
            "selling_pressure": "neutral",
            "aggressive_orders": False,
            "order_imbalance": 0,
            "cvd_trend": "neutral"
        }
    
    # Calculate volume-weighted price analysis
    df = df.tail(10)  # Last 10 candles for recent flow
    current_price = df['c'].iloc[-1]
    
    # Calculate Cumulative Volume Delta (CVD) simulation
    price_changes = df['c'].diff()
    volume_flow = []
    cumulative_delta = 0
    
    for i in range(1, len(df)):
        change = price_changes.iloc[i]
        volume = df['v'].iloc[i]
        
        if change > 0:  # Price up
            delta = volume  # Buying pressure
        elif change < 0:  # Price down
            delta = -volume  # Selling pressure
        else:
            delta = 0
        
        volume_flow.append(delta)
        cumulative_delta += delta
    
    # Determine pressure direction
    recent_flow = volume_flow[-5:] if len(volume_flow) >= 5 else volume_flow
    buying_pressure = sum([x for x in recent_flow if x > 0])
    selling_pressure = abs(sum([x for x in recent_flow if x < 0]))
    
    # Calculate order imbalance
    total_volume = sum(recent_flow) if recent_flow else 1
    order_imbalance = buying_pressure - selling_pressure
    imbalance_ratio = order_imbalance / abs(total_volume) if total_volume != 0 else 0
    
    # Detect aggressive orders (large volume moves)
    avg_volume = df['v'].mean()
    large_volume_threshold = avg_volume * 2
    aggressive_orders = any(v > large_volume_threshold for v in df['v'].tail(3))
    
    # CVD trend analysis
    if len(volume_flow) >= 3:
        recent_cvd = sum(volume_flow[-3:])
        if recent_cvd > avg_volume * 0.5:
            cvd_trend = "bullish"
        elif recent_cvd < -avg_volume * 0.5:
            cvd_trend = "bearish"
        else:
            cvd_trend = "neutral"
    else:
        cvd_trend = "neutral"
    
    return {
        "buying_pressure": "high" if buying_pressure > selling_pressure * 1.5 else "low" if buying_pressure < selling_pressure * 0.5 else "neutral",
        "selling_pressure": "high" if selling_pressure > buying_pressure * 1.5 else "low" if selling_pressure < buying_pressure * 0.5 else "neutral",
        "aggressive_orders": aggressive_orders,
        "order_imbalance": float(imbalance_ratio),
        "cvd_trend": cvd_trend,
        "cumulative_delta": float(cumulative_delta)
    }

def analyze_trend_following_opportunity(df, market_state, volume_profile, order_flow):
    """
    Fabio Valentino's Trend Following Model for imbalance/expansion phases.
    Capitalizes on strong directional moves when market is "out of balance".
    """
    if market_state["state"] != "imbalanced" or not order_flow["aggressive_orders"]:
        return None
    
    current_price = df['c'].iloc[-1]
    
    # Check if we're in high volatility period (NY session optimal)
    session = get_current_session()
    if session != "New_York":
        return None
    
    # Validate entry location using volume analysis
    poc_price = volume_profile.get("poc_price", current_price)
    lvn_levels = volume_profile.get("low_volume_nodes", [])
    
    if not lvn_levels:
        return None
    
    # Find nearest LVN as reaction level
    nearest_lvn = min(lvn_levels, key=lambda x: abs(x['price'] - current_price))
    
    # Determine if pattern is framed correctly against distribution
    if market_state["imbalance_direction"] == "bullish":
        # For bullish continuation, price should be above POC and moving through LVN
        if current_price < poc_price:
            return None
        
        target = poc_price  # Target is Previous Balance Area (POC)
        confidence = 70  # 70% probability of reversal at target
        
    elif market_state["imbalance_direction"] == "bearish":
        # For bearish continuation, price should be below POC and moving through LVN
        if current_price > poc_price:
            return None
        
        target = poc_price  # Target is Previous Balance Area (POC)
        confidence = 70
    
    else:
        return None
    
    # Calculate stop loss placement (protected exactly above/below big aggression)
    stop_loss = current_price * 0.98 if market_state["imbalance_direction"] == "bullish" else current_price * 1.02
    
    return {
        "model_type": "trend_following",
        "setup_name": f"{market_state['imbalance_direction'].title()} Continuation",
        "direction": market_state["imbalance_direction"],
        "entry_price": current_price,
        "stop_loss": stop_loss,
        "target": target,
        "confidence": confidence,
        "rationale": f"Market in {market_state['state']} state with {market_state['imbalance_direction']} bias. LVN reaction at {nearest_lvn['price']:.4f}. Target POC at {target:.4f}.",
        "risk_reward": abs(target - current_price) / abs(current_price - stop_loss) if stop_loss != current_price else 0
    }

def analyze_mean_reversion_opportunity(df, market_state, volume_profile, order_flow):
    """
    Fabio Valentino's Mean Reverting Model for consolidation/balanced phases.
    Takes advantage when price goes to "deep discount" and snaps back.
    """
    if market_state["state"] != "balanced":
        return None
    
    current_price = df['c'].iloc[-1]
    balance_high = market_state["balance_high"]
    balance_low = market_state["balance_low"]
    balance_center = market_state["balance_center"]
    
    # Avoid first swing outside balance (high risk of fake outs)
    recent_df = df.tail(10)
    first_movement = False
    
    if market_state["imbalance_direction"] is None:
        # Check if this is the first clear breakout
        if len(recent_df) >= 3:
            for i in range(1, len(recent_df)):
                if recent_df['c'].iloc[i] > balance_high or recent_df['c'].iloc[i] < balance_low:
                    first_movement = True
                    break
        
        if first_movement:
            return None  # Wait for retracement
    
    # Wait for confirmation: clear breakout and subsequent retracement
    breakout_occurred = False
    retracement_occurred = False
    
    for i in range(len(recent_df) - 1, 0, -1):
        if recent_df['c'].iloc[i] > balance_high or recent_df['c'].iloc[i] < balance_low:
            breakout_occurred = True
            # Check for retracement back toward balance
            if (recent_df['c'].iloc[i] < recent_df['c'].iloc[i-1] and market_state["imbalance_direction"] == "bullish") or \
               (recent_df['c'].iloc[i] > recent_df['c'].iloc[i-1] and market_state["imbalance_direction"] == "bearish"):
                retracement_occurred = True
                break
    
    if not (breakout_occurred and retracement_occurred):
        return None
    
    # Target is POC (highest probability area to be revisited)
    poc_price = volume_profile.get("poc_price", balance_center)
    target = poc_price
    
    # Aggressive risk management - wrong immediately if trade moves against position
    # Place stop loss one or two ticks below actual high/low
    if market_state["imbalance_direction"] == "bullish":
        # Price went down to deep discount, now bouncing back
        recent_low = recent_df['l'].min()
        stop_loss = recent_low * 0.999  # 1 tick below actual low
        direction = "long"
    else:
        # Price went up to deep premium, now coming back down
        recent_high = recent_df['h'].max()
        stop_loss = recent_high * 1.001  # 1 tick above actual high
        direction = "short"
    
    # Move stop to break-even immediately after small profit
    confidence = 80  # High confidence for mean reversion setups
    
    return {
        "model_type": "mean_reversion",
        "setup_name": f"{direction.title()} Mean Reversion",
        "direction": direction,
        "entry_price": current_price,
        "stop_loss": stop_loss,
        "target": target,
        "confidence": confidence,
        "rationale": f"Market in {market_state['state']} state. Price moved to deep discount/premium and is retracing. Target POC at {target:.4f}.",
        "risk_reward": abs(target - current_price) / abs(current_price - stop_loss) if stop_loss != current_price else 0
    }

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
    # Fabio Valentino Strategy Analysis
    current_session = get_current_session()
    ltf_market_state = {}
    htf_market_state = {}
    daily_market_state = {}
    ltf_order_flow = {}
    htf_order_flow = {}
    daily_order_flow = {}
    fabio_valentino_opportunities = {}
    
    # High Probability Setup Detection
    high_probability_setups = []


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
        
        # Calculate candlestick patterns for LTF
        ltf_candlestick_patterns = detect_candlestick_patterns(df_ltf)

        # Fabio Valentino Strategy Analysis for LTF
        if not df_ltf.empty:
            ltf_market_state = detect_market_state(df_ltf, ltf_volume_profile)
            ltf_order_flow = analyze_order_flow_pressure(df_ltf, ltf_volume_profile)
            
            # Analyze both trend following and mean reversion opportunities
            trend_setup = analyze_trend_following_opportunity(df_ltf, ltf_market_state, ltf_volume_profile, ltf_order_flow)
            mean_reversion_setup = analyze_mean_reversion_opportunity(df_ltf, ltf_market_state, ltf_volume_profile, ltf_order_flow)
            
            fabio_valentino_opportunities = {
                "trend_following": trend_setup,
                "mean_reversion": mean_reversion_setup
            }

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
        
        # Calculate candlestick patterns for HTF
        htf_candlestick_patterns = detect_candlestick_patterns(df_htf)
        
        # Fabio Valentino Strategy Analysis for HTF
        if not df_htf.empty:
            htf_market_state = detect_market_state(df_htf, htf_volume_profile)
            htf_order_flow = analyze_order_flow_pressure(df_htf, htf_volume_profile)

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
        
        # Calculate candlestick patterns for Daily
        daily_candlestick_patterns = detect_candlestick_patterns(df_daily)
        
        # Fabio Valentino Strategy Analysis for Daily
        if not df_daily.empty:
            daily_market_state = detect_market_state(df_daily, daily_volume_profile)
            daily_order_flow = analyze_order_flow_pressure(df_daily, daily_volume_profile)

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
            return str(obj) # Convert booleans to strings
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
        
        # Candlestick Patterns
        "ltf_candlestick_patterns": ltf_candlestick_patterns,
        "htf_candlestick_patterns": htf_candlestick_patterns,
        "daily_candlestick_patterns": daily_candlestick_patterns,
        
        # Additional market structure data
        "market_structure": {
            "current_price_vs_liquidity": liquidity_description,
            "volume_price_relationship": volume_price_relationship,
            "momentum_direction": momentum_direction
        },
        
        # Fabio Valentino Trading Strategy
        "current_trading_session": current_session,
        "fabio_valentino_analysis": {
            "ltf_market_state": ltf_market_state,
            "htf_market_state": htf_market_state,
            "daily_market_state": daily_market_state,
            "ltf_order_flow": ltf_order_flow,
            "htf_order_flow": htf_order_flow,
            "daily_order_flow": daily_order_flow,
            "trading_opportunities": fabio_valentino_opportunities
        }
    }

    # Apply conversion to ensure all data is serializable
    analysis_payload = convert_to_serializable(analysis_payload)
    return json.dumps(analysis_payload)

# ----------------------------------------------------------------------
# 3. AI PROVIDER FUNCTIONS
# ----------------------------------------------------------------------

def check_lm_studio(lmstudio_url: str = "http://127.0.0.1:1234"):
    """Check if LM Studio is running at the specified URL."""
    try:
        response = requests.get(f"{lmstudio_url}/v1/models", timeout=5)
        if response.status_code == 200:
            print(f"✅ LM Studio found at {lmstudio_url}")
            return True
        else:
            print(f"⚠️  LM Studio found but unexpected response: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ LM Studio not found at {lmstudio_url}: {e}")
        return False

def call_lm_studio(prompt: str, system_prompt: str = None, lmstudio_url: str = "http://127.0.0.1:1234") -> str:
    """Call LM Studio API with the given prompt."""
    try:
        # First, get available models
        models_response = requests.get(f"{lmstudio_url}/v1/models", timeout=5)
        if models_response.status_code != 200:
            return f"Error: Cannot get models from LM Studio"
        
        models_data = models_response.json()
        available_models = models_data.get('data', [])
        
        if not available_models:
            return f"Error: No models available in LM Studio"
        
        # Use the first available model
        model_name = available_models[0].get('id', 'local-model')
        
        # Combine prompts
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        else:
            full_prompt = prompt
        
        # Prepare the request using chat completions format
        data = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt or "You are a professional trading analyst."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 20000,  # Allow full detailed responses
            "temperature": 0.7,
            "stream": False
        }
        
        response = requests.post(
            f"{lmstudio_url}/v1/chat/completions",
            json=data,
            timeout=120,  # Increased from 30 to 120 seconds for detailed Qwen analysis
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            choices = result.get('choices', [])
            if choices:
                message = choices[0].get('message', {})
                content = message.get('content', '').strip()
                if content:
                    print(f"✅ LM Studio: Full response received ({len(content)} characters)")
                    return content
                else:
                    print(f"⚠️  DEBUG: Empty content from LM Studio, raw result: {result}")
                    return "Error: Empty response from LM Studio"
            else:
                print(f"⚠️  DEBUG: No choices in LM Studio response: {result}")
                return "Error: No response from LM Studio"
        else:
            print(f"⚠️  DEBUG: HTTP {response.status_code} from LM Studio: {response.text[:200]}")
            return f"Error: HTTP {response.status_code} - {response.text[:200]}"
            
    except requests.exceptions.RequestException as e:
        return f"Error: Request failed - {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"

def get_ai_provider(args):
    """Determine which AI provider to use based on command line argument."""
    
    provider = args.ai_provider
    
    print(f"🔍 DEBUG: Requested AI provider: {provider}")
    
    if provider == 'auto':
        print("🔍 DEBUG: Auto-detecting AI provider...")
        # Auto-detect the best available provider (LM Studio for local, then Gemini)
        if check_lm_studio(args.lmstudio_url):
            print(f"🔍 DEBUG: Auto-selected LM Studio at {args.lmstudio_url} (LOCAL - FREE)")
            return 'lmstudio'
        elif GEMINI_API_KEY and GEMINI_API_KEY != "REPLACE_WITH_YOUR_GEMINI_KEY":
            print("🔍 DEBUG: Auto-selected Gemini API (Cloud)")
            return 'gemini'
        else:
            print("⚠️  No AI provider available, using fallback logic")
            return 'fallback'
    elif provider == 'lmstudio':
        print(f"🔍 DEBUG: Checking LM Studio at {args.lmstudio_url}...")
        if check_lm_studio(args.lmstudio_url):
            print(f"✅ LM Studio confirmed available at {args.lmstudio_url}")
            return 'lmstudio'
        else:
            print("❌ LM Studio not available, falling back...")
            if GEMINI_API_KEY and GEMINI_API_KEY != "REPLACE_WITH_YOUR_GEMINI_KEY":
                print("🔄 Falling back to Gemini API")
                return 'gemini'
            else:
                print("❌ No fallbacks available")
                return 'fallback'
    elif provider == 'gemini':
        print("🔍 DEBUG: Checking Gemini API...")
        if GEMINI_API_KEY and GEMINI_API_KEY != "REPLACE_WITH_YOUR_GEMINI_KEY":
            print("✅ Gemini API confirmed available")
            return 'gemini'
        else:
            print("❌ Gemini API not available, falling back...")
            if check_lm_studio(args.lmstudio_url):
                print(f"🔄 Falling back to LM Studio at {args.lmstudio_url}")
                return 'lmstudio'
            else:
                print("❌ No fallbacks available")
                return 'fallback'
    else:
        print(f"🔍 DEBUG: Unknown provider '{provider}', using fallback")
        return 'fallback'

def call_ai_provider(provider: str, prompt: str, system_prompt: str = None, lmstudio_url: str = "http://127.0.0.1:1234") -> str:
    """Call the specified AI provider."""
    if provider == 'lmstudio':
        return call_lm_studio(prompt, system_prompt, lmstudio_url)
    elif provider == 'gemini':
        try:
            # Combine system and user prompts for the CLI
            full_prompt = f"{system_prompt}\n\n{prompt}"
            
            # Get the Google Cloud Project ID from environment variables
            google_cloud_project = os.getenv("GOOGLE_CLOUD_PROJECT")
            
            # Prepare the environment for the subprocess
            env = os.environ.copy()
            if google_cloud_project:
                env['GOOGLE_CLOUD_PROJECT'] = google_cloud_project
            
            # Execute the gemini CLI command
            process = subprocess.run(
                ['gemini', full_prompt],
                capture_output=True,
                text=True,
                check=True,
                env=env
            )
            return process.stdout.strip()
        except FileNotFoundError:
            return "Error: 'gemini' command not found. Please ensure the Gemini CLI is installed and in your PATH."
        except subprocess.CalledProcessError as e:
            return f"Error: Gemini CLI failed with exit code {e.returncode}. Stderr: {e.stderr}"
        except Exception as e:
            return f"Error: An unexpected error occurred when calling Gemini CLI: {e}"
    else:
        return f"Unknown AI provider: {provider}"

def generate_trade_signal_multi_provider(analysis_json_string: str, ai_provider: str, lmstudio_url: str = "http://127.0.0.1:1234", feedback: str = None) -> dict:
    """Generate trade signal using the specified AI provider."""
    
    if analysis_json_string.startswith('{"error"'):
         return json.loads(analysis_json_string)

    # Use ultra-short prompts for LM Studio due to context length limitations
    if ai_provider == 'lmstudio':
        system_prompt = "Trading analyst: provide JSON signal."
        
        # Extract essential data only
        try:
            data = json.loads(analysis_json_string)
            current_price = data.get("current_price", 0)
            rsi_14 = data.get("RSI_14", 50)
            price_change_1h = data.get("price_change_1h_pct", 0)
            
            user_prompt = f"${current_price}, RSI:{rsi_14}, 1H:{price_change_1h}% → JSON: action, entry_price, stop_loss, take_profit, conviction_score, reasoning"
        except:
            user_prompt = f"Analyze: ${data.get('current_price', 0)}, RSI:{data.get('RSI_14', 50)}, 1H:{data.get('price_change_1h_pct', 0)}%"
            
        if feedback:
             user_prompt += f" | REJECTED: {feedback}. IMPROVE."
    else:
        # Full prompt for Gemini and other providers
        system_prompt = (
            "You are a professional, high-conviction Smart Money Concepts (SMC) trading agent implementing the Fabio Valentino strategy. "
            "Analyze the provided JSON market data using both classic SMC analysis and the advanced Fabio Valentino methodology:\n\n"
            "🔍 FABIO VALENTINO STRATEGY ANALYSIS:\n"
            "1. Market State Detection: Determine if market is in BALANCED (consolidation) or IMBALANCED (expansion) state using Auction Market Theory\n"
            "2. Volume Profile Analysis: Identify Point of Control (POC), Low Volume Nodes (LVN), and High Volume Nodes (HVN)\n"
            "3. Order Flow Pressure: Analyze buying/selling pressure, aggressive orders, and Cumulative Volume Delta (CVD)\n"
            "4. Trading Models:\n"
            "   - TREND FOLLOWING: For imbalance/expansion phases, target POC after moves through LVN\n"
            "   - MEAN REVERSION: For balanced/consolidation phases, wait for deep discount/premium then snap back\n\n"
            "🎯 TRADING FRAMEWORK:\n"
            "- Session Timing: NY session optimal for trend following, London for mean reversion\n"
            "- Location Validation: Frame trades correctly against volume distribution\n"
            "- Aggression Filter: Only trade with confirmed institutional participation\n"
            "- Target Selection: POC serves as primary objective (70% reversal probability)\n"
            "- Risk Management: Aggressive positioning, move stops to break-even quickly\n\n"
            "📊 TECHNICAL ANALYSIS:\n"
            "Focus on liquidity, volume, momentum (RSI/MACD), Fair Value Gaps (FVG), Order Blocks, and candlestick patterns.\n"
            "Pay attention to bearish engulfing, evening star, and gravestone doji patterns.\n\n"
            "Generate a high-probability trade recommendation incorporating both SMC principles and Fabio Valentino methodology.\n"
            "Your output MUST be a single JSON object with keys: 'action' (BUY/SELL/HOLD), 'entry_price', 'stop_loss', 'take_profit', 'conviction_score' (1-100), 'strategy_type' (trend_following/mean_reversion/smc_classic), and 'reasoning'."
        )
        user_prompt = f"Analyze the following data and provide a trade signal: {analysis_json_string}"
        
        if feedback:
            user_prompt += f"\n\nIMPORTANT FEEDBACK FROM RISK MANAGER:\n{feedback}\n\nThe previous signal was REJECTED by the Risk Manager. Please refine your analysis and find a better setup or adjust parameters to address the critique. If no good setup exists, output HOLD."

    try:
        # Parse the analysis data to extract market state and session info
        analysis_data = json.loads(analysis_json_string)
        fabio_data = analysis_data.get("fabio_valentino_analysis", {})
        current_session = analysis_data.get("current_trading_session", "Low_Volume")
        
        response = call_ai_provider(ai_provider, user_prompt, system_prompt, lmstudio_url)
        
        if response.startswith("Error:"):
            return {
                "action": "HOLD",
                "entry_price": 0,
                "stop_loss": 0,
                "take_profit": 0,
                "conviction_score": 50,
                "strategy_type": "error",
                "reasoning": f"{ai_provider.upper()} API Error: {response}"
            }
        
        # Attempt to parse the expected JSON output
        # The model's response may be wrapped in markdown code blocks
        response_text = response.strip()
        if response_text.startswith('```json') and response_text.endswith('```'):
            json_str = response_text[7:-3].strip() # Remove ```json and ```
        else:
            json_str = response_text
        
        result = json.loads(json_str)
        
        # Apply Fabio Valentino risk management framework
        ltf_market_state = fabio_data.get("ltf_market_state", {})
        enhanced_result = calculate_fabio_valentino_risk_management(
            result, ltf_market_state, current_session
        )
        
        return enhanced_result
        
    except Exception as e:
        print(f"❌ Error during {ai_provider.upper()} API call or JSON parsing: {e}")
        return {
            "action": "HOLD",
            "entry_price": 0,
            "stop_loss": 0,
            "take_profit": 0,
            "conviction_score": 50,
            "strategy_type": "error",
            "reasoning": f"Parsing Error: {e}"
        }

def calculate_fabio_valentino_risk_management(signal_data, market_state, session):
    """
    Implement Fabio Valentino's aggressive risk management framework.
    - Conservative risk allocation (0.25% of account per trade)
    - Aggressive stop placement
    - Quick break-even movement
    - High risk-to-reward targeting
    """
    try:
        entry_price = float(signal_data.get("entry_price", 0))
        stop_loss = float(signal_data.get("stop_loss", 0))
        target = float(signal_data.get("take_profit", 0))
        action = signal_data.get("action", "HOLD")
        
        # Enhanced validation: check for valid numeric values and non-zero positions
        if (entry_price <= 0 or stop_loss <= 0 or target <= 0 or
            entry_price is None or stop_loss is None or target is None or
            pd.isna(entry_price) or pd.isna(stop_loss) or pd.isna(target)):
            # Return signal without risk management enhancements if invalid data
            return signal_data
        
        # Calculate risk per trade (conservative 0.25% of account)
        risk_amount = entry_price * 0.0025  # 0.25% risk
        distance_to_stop = abs(entry_price - stop_loss)
        position_size = risk_amount / distance_to_stop if distance_to_stop > 0 else 0
        
        # Apply aggressive stop adjustments based on Fabio's methodology
        if market_state.get("state") == "balanced":
            # Mean reversion - move to break-even immediately after small profit
            break_even_buffer = entry_price * 0.001  # 0.1% buffer
            if action == "BUY":
                break_even_price = entry_price + break_even_buffer
            else:
                break_even_price = entry_price - break_even_buffer
        else:
            # Trend following - tighter stops due to confirmed aggression
            break_even_buffer = entry_price * 0.0005  # 0.05% buffer
            if action == "BUY":
                break_even_price = entry_price + break_even_buffer
            else:
                break_even_price = entry_price - break_even_buffer
        
        # Recalculate targets based on POC targeting (70% reversal probability)
        risk_reward_ratio = abs(target - entry_price) / distance_to_stop if distance_to_stop > 0 else 0
        
        # Fabio's approach: target POC, expect 70% reversal at target
        if risk_reward_ratio < 1.5:  # Minimum 1.5:1 R:R for Fabio
            # Adjust target to achieve better risk/reward
            if action == "BUY":
                target = entry_price + (distance_to_stop * 2.0)  # Target 2:1 R:R
            else:
                target = entry_price - (distance_to_stop * 2.0)
        
        # Session-based adjustments
        if session == "New_York":
            # NY session: trend following optimal, wider stops acceptable
            stop_multiplier = 1.2
        elif session == "London":
            # London session: mean reversion optimal, tighter stops
            stop_multiplier = 0.8
        else:
            # Low volume periods: very tight stops
            stop_multiplier = 0.6
        
        # Apply session-based stop adjustment
        if action == "BUY":
            adjusted_stop = entry_price - (distance_to_stop * stop_multiplier)
        else:
            adjusted_stop = entry_price + (distance_to_stop * stop_multiplier)
        
        # Update signal with risk management enhancements
        enhanced_signal = signal_data.copy()
        enhanced_signal.update({
            "stop_loss": adjusted_stop,
            "take_profit": target,
            "position_size": position_size,
            "break_even_price": break_even_price,
            "risk_reward_ratio": abs(target - entry_price) / abs(entry_price - adjusted_stop) if adjusted_stop != entry_price else 0,
            "risk_management": {
                "risk_per_trade_pct": 0.25,
                "session_adjustment": stop_multiplier,
                "break_even_trigger": break_even_buffer,
                "poc_targeting": True,
                "confidence_at_target": 70
            }
        })
        
        return enhanced_signal
        
    except (TypeError, ValueError, ZeroDivisionError) as e:
        # Return original signal if any calculation fails
        return signal_data

# ----------------------------------------------------------------------
# 4. GEMINI AGENT ANALYSIS FUNCTION
# ----------------------------------------------------------------------

def generate_comprehensive_analysis(analysis_json_string: str) -> dict:
    """Uses the AI provider to analyze data and output a comprehensive market analysis."""
    
    if analysis_json_string.startswith('{"error"'):
         return json.loads(analysis_json_string)

    # Extract coin symbol from the analysis JSON string
    try:
        analysis_data = json.loads(analysis_json_string)
        coin_symbol = analysis_data.get("coin_symbol", "N/A")
    except json.JSONDecodeError:
        coin_symbol = "N/A"

    system_prompt = (
        f"You are a professional, high-conviction Smart Money Concepts (SMC) trading analyst implementing the advanced Fabio Valentino strategy. "
        f"Analyze the provided JSON market data comprehensively for {coin_symbol}, focusing on:\n\n"
        f"🔍 FABIO VALENTINO METHODOLOGY:\n"
        f"• Market State Detection: Balance vs Imbalance using Auction Market Theory\n"
        f"• Volume Profile: POC, LVN/HVN analysis, Value Area identification\n"
        f"• Order Flow: CVD analysis, aggressive order detection, buying/selling pressure\n"
        f"• Trading Models: Trend Following (imbalance) vs Mean Reversion (balanced)\n"
        f"• Session Analysis: NY (trend), London (mean reversion), timing considerations\n\n"
        f"📊 CLASSIC SMC ELEMENTS:\n"
        f"• Liquidity, volume, momentum (RSI/MACD)\n"
        f"• Fair Value Gaps (FVGs), Order Blocks, market structure\n"
        f"• Candlestick patterns (engulfing, evening star, gravestone doji)\n\n"
        f"Provide detailed analysis in this format:\n\n"
        f"⚡ Live {coin_symbol} Market Overview (Fabio Valentino Framework)\n"
        f"Current Price: [price] | Trading Session: [session]\n"
        f"Market State: [balanced/imbalanced] | Volume Profile: [analysis]\n"
        f"24h Change: [change]% | Volume: [volume] | Liquidity: [liquidity]\n\n"
        f"🏛️ Auction Market Theory Analysis\n"
        f"Balance Area: [high-low range] | POC: [price] | Value Area: [analysis]\n"
        f"Market State: [state] | Direction: [bias] | Strength: [level]\n"
        f"Liquidity Grabs: [analysis] | Order Flow: [pressure analysis]\n\n"
        f"📈 Multi-Timeframe Structure\n"
        f"Timeframe | Market State | Order Flow | Opportunity\n"
        f"LTF (5m): [state] | [flow] | [Fabio setup if any]\n"
        f"HTF (1h): [state] | [flow] | [Bias confirmation]\n"
        f"Daily: [state] | [flow] | [Long-term context]\n\n"
        f"💧 Volume Profile & Liquidity\n"
        f"POC: [price] (70% reversal probability)\n"
        f"LVN Levels: [price levels] | HVN Levels: [price levels]\n"
        f"Value Area: [range] | Imbalance Zones: [analysis]\n\n"
        f"🎯 Fabio Valentino Trading Opportunities\n"
        f"TREND FOLLOWING: [setup if imbalance detected]\n"
        f"- Entry: [conditions] | Target: [POC] | R:R: [ratio]\n"
        f"MEAN REVERSION: [setup if balanced detected]\n"
        f"- Entry: [conditions] | Target: [POC] | R:R: [ratio]\n\n"
        f"📊 Traditional SMC Analysis\n"
        f"FVGs: [list] | Order Blocks: [list] | Patterns: [list]\n\n"
        f"🧭 Integrated Trading Plan\n"
        f"Preferred Setup: [Fabio model + SMC confluence]\n"
        f"Entry: [price/range] | Stop: [aggressive placement] | TP: [POC target]\n"
        f"Risk Management: [Fabio's aggressive approach] | Conviction: [score]\n\n"
        f"✅ Final Assessment\n"
        f"Market Context: [comprehensive synthesis]\n"
        f"Bias: [directional bias] with [confidence level]\n"
        f"Action Plan: [specific trading strategy based on Fabio Valentino methodology]"
    )

    user_prompt = f"Analyze the following data and provide a comprehensive market analysis: {analysis_json_string}"

    response = call_ai_provider('gemini', user_prompt, system_prompt)
    if response.startswith("Error:"):
        return {"error": f"AI analysis generation failed: {response}"}
    return {"analysis": response}

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

def generate_fallback_signal(analysis_json_string: str) -> dict:
    """Generate fallback signal when no AI providers are available."""
    try:
        analysis_data = json.loads(analysis_json_string)
        current_price = float(analysis_data.get("current_price", 0))
        price_change_1h = float(analysis_data.get("price_change_1h_pct", 0))
        rsi_14 = analysis_data.get("RSI_14", 50)
        
        # Simple technical analysis based signal
        if isinstance(rsi_14, str):
            rsi_14 = 50  # Default to neutral if RSI is not numeric
        
        # Simple logic: HOLD by default, BUY if oversold, SELL if overbought
        if rsi_14 < 30:  # Oversold
            action = "BUY"
            conviction = 65
            reasoning = f"Fallback Logic: Oversold conditions - 1H: {price_change_1h:.2f}%, RSI: {rsi_14:.1f}"
        elif rsi_14 > 70:  # Overbought
            action = "SELL"
            conviction = 65
            reasoning = f"Fallback Logic: Overbought conditions - 1H: {price_change_1h:.2f}%, RSI: {rsi_14:.1f}"
        else:  # Neutral
            action = "HOLD"
            conviction = 60
            reasoning = f"Fallback Logic: Neutral conditions - 1H: {price_change_1h:.2f}%, RSI: {rsi_14:.1f}"
        
        return {
            "action": action,
            "entry_price": current_price,
            "stop_loss": current_price * (0.98 if action == "BUY" else 1.02),
            "take_profit": current_price * (1.02 if action == "BUY" else 0.98),
            "conviction_score": conviction,
            "reasoning": reasoning
        }
    except Exception as e:
        return {
            "action": "HOLD",
            "entry_price": 0,
            "stop_loss": 0,
            "take_profit": 0,
            "conviction_score": 50,
            "reasoning": f"Fallback Error: {e}"
        }

def main():
    """Executes the trading agent's workflow."""
    parser = argparse.ArgumentParser(description='Run the Trading Agent')
    parser.add_argument('--token', type=str, default='SOL', help='Token symbol (e.g., SOL, BTC, ETH)')
    parser.add_argument('--chain', type=str, default='solana', help='Blockchain network (e.g., solana, ethereum, bsc)')
    parser.add_argument('--mode', type=str, default='signal', choices=['signal', 'analysis'], help='Output mode: signal for trade signal, analysis for comprehensive market analysis')
    parser.add_argument('--ai-provider', type=str, default='auto', choices=['auto', 'gemini', 'lmstudio'], help='AI provider to use (default: auto)')
    parser.add_argument('--lmstudio-url', type=str, default='http://127.0.0.1:1234', help='Custom LM Studio server URL (e.g., http://192.168.100.182:1234)')
    parser.add_argument('--loop', action='store_true', help='Run the agent in a continuous loop')
    parser.add_argument('--interval', type=int, default=300, help='Loop interval in seconds (default: 300s / 5m)')
    parser.add_argument('--leverage', action='store_true', help='Enable leverage trading via Drift Protocol')
    
    args = parser.parse_args()
    
    # Get token address from symbol
    token_address = get_token_address_from_symbol(args.token, args.chain)
    if not token_address:
        print(f"❌ Could not find token address for {args.token} on {args.chain}")
        return
        
    print(f"🚀 Starting Trading Agent for {args.token} ({token_address}) on {args.chain}...")
    
    # Determine which AI provider to use
    selected_provider = get_ai_provider(args)
    
    if selected_provider == 'fallback':
        print("⚠️  No AI providers available. Using fallback technical analysis...")
    
    # --- MAIN LOOP START ---
    while True:
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n⏰ [{current_time}] Starting cycle...")
            
            # --- LIFECYCLE MANAGEMENT START ---
            db = LifecycleDatabase()
            
            # Initialize Wallet and Jupiter Client
            wallet = SolanaWallet()
            jupiter = JupiterClient(wallet)
            drift = DriftClientWrapper() if args.leverage else None
            
            active_trade = db.get_active_trade()
            
            if active_trade:
                print(f"\n🔄 EXISTING TRADE FOUND: {active_trade['symbol']} (ID: {active_trade['id']})")
                print(f"   Entry: {active_trade['entry_price']} | SL: {active_trade['stop_loss']} | TP: {active_trade['take_profit']}")
                print("...Switching to MANAGEMENT MODE...")
                
                # Get the token address for the ACTIVE trade (not the command-line argument)
                active_trade_token_address = get_token_address_from_symbol(active_trade['symbol'], args.chain)
                
                if not active_trade_token_address:
                    print(f"⚠️  Could not find token address for {active_trade['symbol']}. Skipping management.")
                else:
                    # Fetch current price for the ACTIVE trade's token
                    market_data, _ = fetch_birdeye_data(active_trade_token_address, args.chain)
                    if 'value' in market_data:
                        current_price = float(market_data['value'])
                        print(f"   Current Price: {current_price}")
                        
                        # Check for exit conditions
                        if current_price <= active_trade['stop_loss']:
                            print("🛑 STOP LOSS HIT! Closing trade...")
                            
                            # Execute sell via Jupiter (if wallet is configured)
                            if wallet.keypair and active_trade_token_address:
                                print("🔄 Executing SELL on Jupiter...")
                                # For selling, we need to swap the token back to SOL
                                # We'll sell a fixed amount or percentage - for now, let's use the same 0.01 SOL worth
                                # In a real scenario, you'd track how much of the token you bought
                                
                                # Estimate: if we bought with 0.01 SOL, we should have approximately that much in tokens
                                # For simplicity, let's just try to sell back to SOL
                                # This is a simplified approach - in production, you'd track exact token amounts
                                
                                input_mint = active_trade_token_address  # The token we're selling
                                output_mint = "So11111111111111111111111111111111111111112"  # SOL
                                # Use a small amount for testing - this should be calculated based on actual holdings
                                amount_to_sell = 10000000  # Placeholder - should be actual token balance
                                
                                sell_result = jupiter.execute_swap(input_mint, output_mint, amount_to_sell)
                                
                                if "signature" in sell_result:
                                    print(f"✅ SELL Executed! Signature: {sell_result['signature']}")
                                else:
                                    print(f"⚠️  SELL Failed: {sell_result.get('error')} - Trade marked as closed anyway")
                            
                            db.close_trade(active_trade['id'], current_price, "Stop Loss Hit")
                            
                        elif current_price >= active_trade['take_profit']:
                            print("💰 TAKE PROFIT HIT! Closing trade...")
                            
                            # Execute sell via Jupiter (if wallet is configured)
                            if wallet.keypair and active_trade_token_address:
                                print("🔄 Executing SELL on Jupiter...")
                                
                                input_mint = active_trade_token_address  # The token we're selling
                                output_mint = "So11111111111111111111111111111111111111112"  # SOL
                                amount_to_sell = 10000000  # Placeholder - should be actual token balance
                                
                                sell_result = jupiter.execute_swap(input_mint, output_mint, amount_to_sell)
                                
                                if "signature" in sell_result:
                                    print(f"✅ SELL Executed! Signature: {sell_result['signature']}")
                                else:
                                    print(f"⚠️  SELL Failed: {sell_result.get('error')} - Trade marked as closed anyway")
                            
                            db.close_trade(active_trade['id'], current_price, "Take Profit Hit")
                            
                        else:
                            print("✋ Holding... Trade is still active.")
                    else:
                        print("⚠️  Could not fetch current price to manage trade.")
                
                # In Management Mode, we can check more frequently (e.g., every 60s)
                if args.loop:
                    print(f"💤 Sleeping for 60s (Management Mode)...")
                    time.sleep(60)
                    continue
                else:
                    return 
            
            # --- LIFECYCLE MANAGEMENT END ---
                
            # 1. Fetch Data
            print("...Fetching real-time data...")
            market_data, ohlcv_data = fetch_birdeye_data(token_address, args.chain)
            
            if 'error' in market_data:
                print(f"❌ Failed to start due to data retrieval error: {market_data['error']}")
                if args.loop:
                    time.sleep(60) # Retry sooner on error
                    continue
                else:
                    return

            # 2. Process Data
            print("...Processing raw data and calculating indicators...")
            
            # Update the market data to include the token symbol if it's not present
            if not market_data.get('symbol'):
                market_data['symbol'] = args.token
            
            analysis_payload = process_data(market_data, ohlcv_data)
            
            # 3. Generate Analysis/Signal based on mode
            if args.mode == 'analysis':
                print(f"...Sending structured data to {selected_provider.upper()} for comprehensive analysis...")
                
                # Update the analysis payload to include the coin symbol properly before calling analysis
                analysis_payload_dict = json.loads(analysis_payload)
                analysis_payload_dict["coin_symbol"] = args.token
                analysis_payload = json.dumps(analysis_payload_dict)
                
                # For analysis mode, we'll use Gemini if available, otherwise fallback
                if selected_provider == 'gemini':
                    result = generate_comprehensive_analysis(analysis_payload)
                else:
                    result = {
                        "analysis": f"Comprehensive analysis requires AI provider. Using {selected_provider}. Available analysis features: Market structure, Fair Value Gaps, Order Blocks, Volume analysis."
                    }
                
                if 'analysis' in result:
                    # Use the new formatter for beautiful output
                    OutputFormatter.format_comprehensive_analysis(result['analysis'], args.token)
                elif 'error' in result:
                    print(f"\n❌ FAILED ANALYSIS GENERATION: {result['error']}")
            else: # Default to signal mode
                print(f"...Sending structured data to {selected_provider.upper()} for high-level analysis...")
                
                if selected_provider == 'fallback':
                    # Use simple fallback logic
                    signal = generate_fallback_signal(analysis_payload)
                    provider_name = "FALLBACK"
                else:
                    # Use the selected AI provider
                    
                    # --- MULTI-AGENT PIPELINE START ---
                    
                    # 1. News Agent
                    print("...News Agent: Fetching recent news...")
                    news_agent = NewsAgent()
                    news_summary = news_agent.fetch_news(args.token)
                    
                    # Inject news into analysis payload
                    payload_dict = json.loads(analysis_payload)
                    payload_dict["news_summary"] = news_summary
                    analysis_payload_with_news = json.dumps(payload_dict)
                    
                    # 2. Strategy Agent (Existing)
                    print(f"...Strategy Agent: Generating signal using {selected_provider.upper()}...")
                    signal = generate_trade_signal_multi_provider(analysis_payload_with_news, selected_provider, args.lmstudio_url)
                    provider_name = selected_provider.upper()
                    
                    # Add news summary to signal for display
                    signal['news_summary'] = news_summary
                    
                    # 3. Risk Manager Agent (Debate Loop)
                    if 'error' not in signal:
                        print(f"...Risk Manager Agent: Critiquing signal...")
                        risk_manager = RiskManager()
                        
                        # Define callback for Risk Manager to use the same AI provider
                        def risk_ai_callback(user_prompt, system_prompt):
                            return call_ai_provider(selected_provider, user_prompt, system_prompt, args.lmstudio_url)
                        
                        # Debate Loop Variables
                        max_retries = 3
                        retry_count = 0
                        risk_approved = False
                        
                        while retry_count < max_retries:
                            risk_assessment = risk_manager.assess_risk(signal, market_data, news_summary, risk_ai_callback)
                            
                            # Merge Risk Assessment into Signal
                            signal['risk_assessment'] = risk_assessment
                            
                            if risk_assessment.get('approved', True):
                                print("✅ Risk Manager APPROVED the trade.")
                                risk_approved = True
                                break
                            else:
                                print(f"⚠️  Risk Manager REJECTED the trade (Attempt {retry_count + 1}/{max_retries}).")
                                print(f"   Critique: {risk_assessment.get('critique')}")
                                
                                if retry_count < max_retries - 1:
                                    print("🔄 Feedback Loop: Requesting refined signal from Strategy Agent...")
                                    feedback = risk_assessment.get('critique')
                                    # Re-generate signal with feedback
                                    signal = generate_trade_signal_multi_provider(analysis_payload_with_news, selected_provider, args.lmstudio_url, feedback=feedback)
                                    signal['news_summary'] = news_summary # Re-attach news
                                
                                retry_count += 1
                        
                        if not risk_approved:
                            print("❌ Trade REJECTED after debate loop.")
                            signal['action'] = "HOLD (Risk Manager Rejection)"
                            signal['reasoning'] = f"[RISK REJECTED] {signal.get('risk_assessment', {}).get('critique')} | Original: {signal.get('reasoning')}"
                            
                            # Log rejected signal
                            db.save_signal(
                                symbol=args.token,
                                signal_data=signal,
                                risk_assessment=signal.get('risk_assessment'),
                                status="REJECTED"
                            )
                        else:
                            # Trade Approved - Save to DB
                            if signal.get('action') == 'BUY':
                                print("💾 Saving trade to Lifecycle Database...")
                                
                                # Execute Swap via Jupiter
                                swap_status = "PENDING"
                                swap_result = None
                                
                                if wallet.keypair:
                                    if args.leverage and drift:
                                        print("🚀 Executing LEVERAGE LONG on Drift...")
                                        # TODO: Make amount configurable
                                        amount_sol = 0.01 
                                        swap_result = drift.open_position(args.token, "LONG", amount_sol)
                                        
                                        if "signature" in swap_result:
                                            print(f"✅ Drift Long Position Opened! Signature: {swap_result['signature']}")
                                            swap_status = "EXECUTED"
                                        else:
                                            print(f"❌ Drift Order Failed: {swap_result.get('error')}")
                                            swap_status = "FAILED"
                                            signal['swap_error'] = swap_result.get('error')
                                            
                                    else:
                                        print("🚀 Executing LIVE SWAP on Jupiter...")
                                        # Amount to swap: For now, let's use a fixed amount or percentage
                                        # TODO: Make this configurable. Defaulting to 0.01 SOL for safety.
                                        amount_sol = 0.01 
                                        amount_lamports = int(amount_sol * 1e9)
                                        
                                        # Get Quote first (optional but good for logging)
                                        # ... (existing Jupiter logic)
                                        
                                        # Execute Swap
                                        # For SOL -> Token, input is SOL mint
                                        input_mint = "So11111111111111111111111111111111111111112" 
                                        output_mint = get_token_address_from_symbol(args.token, args.chain)
                                        
                                        if output_mint:
                                            swap_result = jupiter.execute_swap(input_mint, output_mint, amount_lamports)
                                            
                                            if "signature" in swap_result:
                                                print(f"✅ Swap Executed! Signature: {swap_result['signature']}")
                                                swap_status = "EXECUTED"
                                                # Update signal with swap details
                                                signal['swap_signature'] = swap_result['signature']
                                            else:
                                                print(f"❌ Swap Failed: {swap_result.get('error')}")
                                                swap_status = "FAILED"
                                                signal['swap_error'] = swap_result.get('error')
                                        else:
                                            print(f"❌ Could not find mint address for {args.token}")
                                            swap_status = "FAILED"
                                            signal['swap_error'] = "Token mint not found"
                                else:
                                    print("⚠️  No wallet configured. Simulation mode only.")
                                    swap_status = "SIMULATED"

                                db.add_trade(
                                    symbol=args.token,
                                    entry_price=signal.get('entry_price'),
                                    stop_loss=signal.get('stop_loss'),
                                    take_profit=signal.get('take_profit'),
                                    strategy_output=signal,
                                    risk_assessment=signal.get('risk_assessment')
                                )
                                
                                # Log executed signal
                                db.save_signal(
                                    symbol=args.token,
                                    signal_data=signal,
                                    risk_assessment=signal.get('risk_assessment'),
                                    status=swap_status
                                )
                            elif signal.get('action') == 'SELL':
                                if args.leverage and drift and wallet.keypair:
                                    print("🚀 Executing LEVERAGE SHORT on Drift...")
                                    amount_sol = 0.01 
                                    swap_result = drift.open_position(args.token, "SHORT", amount_sol)
                                    
                                    if "signature" in swap_result:
                                        print(f"✅ Drift Short Position Opened! Signature: {swap_result['signature']}")
                                        swap_status = "EXECUTED"
                                    else:
                                        print(f"❌ Drift Order Failed: {swap_result.get('error')}")
                                        swap_status = "FAILED"
                                        signal['swap_error'] = swap_result.get('error')
                                    
                                    # Log executed signal
                                    db.save_signal(
                                        symbol=args.token,
                                        signal_data=signal,
                                        risk_assessment=signal.get('risk_assessment'),
                                        status=swap_status
                                    )
                                else:
                                    # Approved but not a BUY (e.g. SELL or HOLD approved?) - unlikely for opening but good to cover
                                    db.save_signal(
                                        symbol=args.token,
                                        signal_data=signal,
                                        risk_assessment=signal.get('risk_assessment'),
                                        status="SKIPPED"
                                    )
                    
                    # --- MULTI-AGENT PIPELINE END ---
                
                # 4. Output/Alert the Result
                if 'error' in signal:
                    print(f"\n❌ FAILED SIGNAL GENERATION: {signal['error']}")
                else:
                    coin_symbol = market_data.get('symbol', args.token)
                    
                    # Update the analysis payload to include the coin symbol properly
                    analysis_payload_dict = json.loads(analysis_payload)
                    analysis_payload_dict["coin_symbol"] = coin_symbol
                    
                    # Detect high-probability setups
                    high_probability_setups = detect_high_probability_setups(analysis_payload_dict)
                    
                    analysis_payload = json.dumps(analysis_payload_dict)
                    
                    # Use the new formatter for beautiful output
                    OutputFormatter.format_trade_signal(signal, market_data, coin_symbol)
                    
                    # Display high-probability setups if any detected
                    if high_probability_setups:
                        print(f"\n🎯 HIGH-PROBABILITY SETUPS DETECTED ({len(high_probability_setups)})")
                        print("=" * 80)
                        for i, setup in enumerate(high_probability_setups, 1):
                            probability_icon = "🔥" if setup.get("probability", 0) >= 80 else "⭐" if setup.get("probability", 0) >= 60 else "⚡"
                            direction_icon = "📈" if setup.get("direction") in ["bullish", "long"] else "📉" if setup.get("direction") in ["bearish", "short"] else "⚖️"
                            
                            print(f"\n{i}. {probability_icon} {setup.get('setup_type', 'Unknown')} - {setup.get('confidence_level', 'MEDIUM')} PROBABILITY")
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
                        print("\n" + "=" * 80)
                    
                    # Add Fabio Valentino analysis if available
                    fabio_data = analysis_payload_dict.get('fabio_valentino_analysis', {})
                    current_session = analysis_payload_dict.get('current_trading_session', 'Unknown')
                    if fabio_data:
                        # Pass the complete analysis data including candlestick patterns
                        OutputFormatter.format_fabio_valentino_analysis(fabio_data, current_session, analysis_payload_dict)
                    
                    # NOTE: For a production system, you would replace this print block
                    # with an alert mechanism (e.g., email, Telegram, or an exchange API call).
        
        except Exception as e:
            print(f"❌ An error occurred in the main loop: {e}")
            import traceback
            traceback.print_exc()
            
        if not args.loop:
            break
            
        print(f"\n💤 Sleeping for {args.interval}s...")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
