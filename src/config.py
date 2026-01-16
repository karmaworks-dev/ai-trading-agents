"""
🕉️ Karma Dev's Configuration File
Built with love by Karma Dev 🚀
Updated for Hyperliquid Small Account ($10)
"""

# 🔄 Exchange Selection
EXCHANGE = 'hyperliquid'  # Options: 'solana', 'hyperliquid'

# 💰 Wallet Configuration
# NOTE: Your Private Key and Address are loaded from .env
# We leave these here just to prevent errors, but they aren't used for Hyperliquid auth
USDC_ADDRESS = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v" 
SOL_ADDRESS = "So11111111111111111111111111111111111111111" 

# Create a list of addresses to exclude from trading/closing
EXCLUDED_TOKENS = [USDC_ADDRESS, SOL_ADDRESS]

# ⚡ HyperLiquid Configuration
# Main trading tokens - diversified portfolio
HYPERLIQUID_SYMBOLS = ['BTC', 'ETH', 'SOL', 'LTC', 'AAVE', 'HYPE']
# NOTE: HYPERLIQUID_LEVERAGE is now an alias for LEVERAGE (defined in Risk Management below)

# Position sizing 🎯
# CRITICAL FOR $10 ACCOUNT:
# Hyperliquid minimum position size is $10 USD. 
# We set this to 12 to be safe.
usd_size = 12  
max_usd_order_size = 12  # Cap the max order size
tx_sleep = 5  # Faster execution for perps

# 🔄 Exchange-Specific Token Lists
def get_active_tokens():
    """Returns the appropriate token/symbol list based on active exchange"""
    if EXCHANGE == 'hyperliquid':
        return HYPERLIQUID_SYMBOLS
    else:
        return MONITORED_TOKENS

# Token to Exchange Mapping
TOKEN_EXCHANGE_MAP = {
    'BTC': 'hyperliquid',
    'ETH': 'hyperliquid',
    'SOL': 'hyperliquid',
    'LTC': 'hyperliquid',
    'XRP': 'hyperliquid',
    'AAVE': 'hyperliquid',
    'LINK': 'hyperliquid',
    'HYPE': 'hyperliquid',
    'FARTCOIN': 'hyperliquid',
}

# 🛡️ Risk Management Settings (Tuned for $10 Account)
# NOTE: These are the authoritative settings - no duplicates below
CASH_PERCENTAGE = 10  # Keep 10% of account as cash buffer
MAX_POSITION_PERCENTAGE = 90  # Max % of balance per position
LEVERAGE = 20  # Leverage multiplier (also used by trading_agent.py)
HYPERLIQUID_LEVERAGE = LEVERAGE  # Alias for backwards compatibility
TAKE_PROFIT_PERCENT = 4.5  # Take profit at +4.5%
STOP_LOSS_PERCENT = 1.5   # Stop loss at -1.5%
STOPLOSS_PRICE = 0    # Not used in this specific agent logic yet
BREAKOUT_PRICE = 0
SLEEP_AFTER_CLOSE = 30 # Sleep 30s after closing a trade

MAX_LOSS_GAIN_CHECK_HOURS = 12 
SLEEP_BETWEEN_RUNS_MINUTES = 1 # Check markets every minute

# Max Loss/Gain Settings
USE_PERCENTAGE = False

# Percentage-based limits (used when USE_PERCENTAGE = True)
MAX_LOSS_PERCENT = 10   # 10% max loss
MAX_GAIN_PERCENT = 20   # 20% max gain

# USD-based limits (Protective Stops)
MAX_LOSS_USD = 2   # If we lose $2, stop trading (Protects your $10)
MAX_GAIN_USD = 3   # If we make $5, stop and take profit

# USD MINIMUM BALANCE RISK CONTROL
MINIMUM_BALANCE_USD = 1  # If balance drops below $5, close everything
USE_AI_CONFIRMATION = True # Set to False for faster exits

# Transaction settings ⚡
slippage = 0.01  # 1% Slippage
orders_per_open = 1  # 1 Order is enough for small size

# Market maker settings (Simple Supply/Demand)
buy_under = 0.99  # Buy if price drops 1% below target
sell_over = 1.01  # Sell if price rises 1% above target

# Data collection settings 📈
DAYSBACK_4_DATA = 2
DATA_TIMEFRAME = '30m' 
SAVE_OHLCV_DATA = False 

# AI Model Settings
# AI AGENT SETTINGS - DeepSeek Trading Optimized
#
# Available DeepSeek models (via OllamaFreeAPI - FREE!):
# - "deepseek-v3.2" - Latest flagship (671B) ⚡ BEST
# - "deepseek-v3.2:671b-q4_K_M" - Quantized version (memory efficient)
# - "deepseek-v3.1:671b" - Stable trading model ⚡ RECOMMENDED
# - "deepseek-r1:7b/14b/32b" - Reasoning models
#
# Alternative paid options:
# - Anthropic: "claude-sonnet-4-5-20250929" - Best balance
# - OpenAI: "gpt-4.1-mini" - Efficient
# - Gemini: "gemini-2.5-flash" - Fast

# SINGLE MODEL SETTINGS (DEFAULT: DeepSeek V3.1)
AI_MODEL_TYPE = 'ollamafreeapi'      # FREE API - no key required
AI_MODEL = "deepseek-v3.1:671b"       # ⚡ RECOMMENDED for trading
AI_MAX_TOKENS = 8024                  # Increased for multi-step reasoning
AI_TEMPERATURE = 0.6                  # Official DeepSeek recommended "sweet spot"

# Trading Strategy Agent Settings
ENABLE_STRATEGIES = True
STRATEGY_MIN_CONFIDENCE = 0.6   # 60% confidence threshold

# ⚡ WebSocket Settings (Real-time data feeds)
# Set to True to use WebSocket for price/orderbook data instead of API polling
# This reduces API calls and provides faster updates
USE_WEBSOCKET_FEEDS = True  # Feature flag for gradual rollout
WEBSOCKET_FALLBACK_TO_API = True  # If WebSocket fails, fall back to API polling

# Legacy/Solana Variables (Kept to prevent errors, but ignored)
symbol = 'SOL'
tokens_to_trade = HYPERLIQUID_SYMBOLS
MONITORED_TOKENS = []
# NOTE: slippage is now defined only once at line 75 (0.01 = 1%)
PRIORITY_FEE = 100000
sell_at_multiple = 3
USDC_SIZE = 1
limit = 49
timeframe = '15m'
stop_loss_percentage = -0.24  # Fixed typo: was 'stop_loss_perctentage'
EXIT_ALL_POSITIONS = False
DO_NOT_TRADE_LIST = ['777']
CLOSED_POSITIONS_TXT = '777'
minimum_trades_in_last_hour = 2
MIN_TRADES_LAST_HOUR = 2  # Alias for nice_funcs.py compatibility
REALTIME_CLIPS_ENABLED = False

# 💰 POSITION SIZING & RISK MANAGEMENT
# NOTE: CASH_PERCENTAGE, MAX_POSITION_PERCENTAGE, and LEVERAGE are defined above
# in the Risk Management section to avoid duplicate definitions
USE_PORTFOLIO_ALLOCATION = True

# Stop Loss & Take Profit (PnL-based)
STOP_LOSS_PERCENTAGE = 2.0  # SL @ -2% PnL
TAKE_PROFIT_PERCENTAGE = 5.0  # TP @ +5% PnL

# 🌊 CONFIDENCE THRESHOLDS
MIN_SINGLE_CONFIDENCE = 60  # Single model confidence threshold (50-70% recommended)
MIN_SWARM_CONFIDENCE = 65  # Swarm consensus threshold (55-65% recommended)

# ⚙️ POSITION MANAGEMENT SETTINGS
MIN_AGE_HOURS = 0.1  # Minimum hold time before close (hours)
MIN_CLOSE_CONFIDENCE = 70  # AI confidence needed to close position

# Minimum order value for HyperLiquid
MIN_ORDER_NOTIONAL = 12.0  # $12 minimum (HyperLiquid requires $10, we use $12 for safety)
