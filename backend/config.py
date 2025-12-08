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
    SOL_MINT = "So11111111111111111111111111111111111111112"
    USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

    # API URLs
    JUPITER_BASE_URL = "https://lite-api.jup.ag/swap/v1"
    BIRDEYE_BASE_URL = "https://public-api.birdeye.so"
    COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
    
    # Varma Strategy Parameters (V3)
    VARMA_KELLY_DAMPENER = 0.25  # Use 1/4 Kelly for safety
    VARMA_MAX_DRAWDOWN = 0.45    # 45% maximum drawdown target
    VARMA_TREND_PERIOD = 200     # 200-period MA for regime classification
    VARMA_ORB_RANGE_MINUTES = 15 # Opening range duration
    VARMA_RISK_ON_MULTIPLIER = 1.5  # Increase size by 50% when above trend
    VARMA_RISK_OFF_MULTIPLIER = 0.5 # Decrease size by 50% when below trend
    VARMA_MIN_POSITION_SIZE = 0.05  # Minimum 5% of capital
    VARMA_MAX_POSITION_SIZE = 0.25  # Maximum 25% of capital

