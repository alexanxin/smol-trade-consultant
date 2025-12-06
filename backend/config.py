import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Keys
    BIRDEYE_API_KEY = os.getenv("BIRDEYE_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY")
    
    # Model Configuration
    MODEL_NAME = "gemini-2.5-flash"
    
    # Trading Parameters
    DEFAULT_TOKEN = "SOL"
    DEFAULT_MONITOR_INTERVAL = 30  # seconds
    DEFAULT_TRAILING_DISTANCE = 2.0  # percentage
    
    # Risk Management
    DEFAULT_STOP_LOSS_PCT = 0.03  # 3%
    DEFAULT_TAKE_PROFIT_PCT = 0.06  # 6%
    
    # Timeouts
    API_TIMEOUT = 10  # seconds
    
    # System
    LOG_LEVEL = "INFO"

    # Token Mints
    SOL_MINT = "So11111111111111111111111111111111111111111"
    USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

    # API URLs
    JUPITER_BASE_URL = "https://lite-api.jup.ag/swap/v1"
    BIRDEYE_BASE_URL = "https://public-api.birdeye.so"
    COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
