"""
🕉️ Karma Dev's LLM Trading Agent 🕉️

DUAL-MODE AI TRADING SYSTEM:

SINGLE MODEL MODE (Fast - ~10 seconds per token):
   - Uses one AI model for quick trading decisions
   - Best for: Fast execution, high-frequency strategies
   - Configure model in config.py: AI_MODEL_TYPE and AI_MODEL_NAME

SWARM MODE (Consensus - ~45-60 seconds per token):
   - Queries 6 AI models simultaneously for consensus voting
   - Models vote: "Buy", "Sell", or "Do Nothing"
   - Majority decision wins with confidence percentage
   - Best for: Higher confidence trades, 15-minute+ timeframes

Built with love by Karma Dev 🚀 | KUDOS to Moon Dev for the foundation
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
import re


# extract_json_from_text - Now imported from src.agents.trading.market_analyzer
# (defined after sys.path setup below)


# ============================================================================
# 🚨 CRITICAL: THIS MUST BE HERE (BEFORE 'src' IMPORTS)
# ============================================================================
# Add project root to path so Python can find 'src'
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)
# ============================================================================

# 👇 NOW you can import from src safely
from src.models import model_factory
from src.agents.swarm_agent import SwarmAgent
from src.data.ohlcv_collector import collect_all_tokens
from src.agents.strategy_agent import StrategyAgent

# Import AI prompt templates (extracted for maintainability)
from src.agents.trading.prompts import (
    TRADING_PROMPT,
    SWARM_TRADING_PROMPT,
    SMART_ALLOCATION_PROMPT,
    POSITION_ANALYSIS_PROMPT,
)

# Import AI interface functions (extracted for maintainability)
from src.agents.trading.ai_interface import (
    get_performance_metrics as _get_performance_metrics,
    chat_with_ai as _chat_with_ai,
    format_market_data_for_swarm as _format_market_data_for_swarm,
    parse_vote_from_response as _parse_vote_from_response,
    calculate_swarm_consensus as _calculate_swarm_consensus,
)

# Import position manager functions (extracted for maintainability)
from src.agents.trading.position_manager import (
    calculate_position_size as _calculate_position_size,
    check_tp_sl_thresholds,
    build_position_data,
    format_position_for_display,
    format_position_summary_for_ai,
    build_close_decision,
    evaluate_positions_for_tp_sl,
    extract_current_price,
    build_market_summary,
)

# Import market analyzer functions (extracted for maintainability)
from src.agents.trading.market_analyzer import (
    extract_json_from_text as _extract_json_from_text,
    format_position_context,
    format_performance_context,
    format_strategy_context_text as _format_strategy_context_text,
    format_legacy_strategy_signals,
    parse_single_model_response,
    extract_confidence_from_text,
    apply_confidence_threshold,
    build_recommendation,
    build_error_recommendation,
    validate_market_data,
    get_token_from_market_data,
)

# Import portfolio allocator functions (extracted for maintainability)
from src.agents.trading.portfolio_allocator import (
    normalize_symbol as _normalize_symbol,
    filter_strategy_signals,
    calculate_allocatable_balance,
    calculate_equal_distribution,
    validate_allocation_actions,
    sort_allocation_actions,
    plan_rebalance_closes,
    build_fallback_allocation_actions,
    filter_signals_by_position_alignment,
    SYMBOL_ALIASES,
)

# Import trade executor functions (extracted for maintainability)
from src.agents.trading.trade_executor import (
    calculate_notional,
    check_min_notional,
    validate_trade_action,
    validate_position_for_action,
    check_position_conflict,
    build_execution_summary,
    format_execution_summary,
    get_position_direction,
    calculate_current_notional,
    should_close_for_reversal,
    should_exit_position,
    # Phase 2.1 helpers for execute_allocations refactoring
    unpack_entry_result,
    build_trade_result,
    log_open_trade_result,
    log_close_trade_result,
    log_reduce_trade_result,
    validate_open_action_params,
    validate_reduce_action_params,
    validate_close_action_params,
    has_opposite_position,
    needs_position_close_first,
    # Phase 2.2 helpers for handle_exits refactoring
    should_trigger_stop_loss,
    should_trigger_take_profit,
    signal_contradicts_position,
    format_exit_phase_summary,
    DEFAULT_MIN_NOTIONAL,
)

# Import shared logging utility (prevents circular import with trading_app)
try:
    from src.utils.logging_utils import add_console_log, log_position_open
except ImportError:
    # Fallback if running standalone without trading_app
    def add_console_log(message, level="info", console_file=None):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def log_position_open(symbol, side, size_usd, console_file=None):
        emoji = "📈" if side == "LONG" else "📉"
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {emoji} Opened {side} {symbol} ${size_usd:.2f}")

# Import position tracker for age-based decisions
try:
    from src.utils.position_tracker import (
        record_position_entry, remove_position, get_position_age_hours,
        get_all_tracked_positions, sync_with_exchange_positions
    )
    POSITION_TRACKER_AVAILABLE = True
except ImportError:
    POSITION_TRACKER_AVAILABLE = False
    def record_position_entry(*args, **kwargs): return True
    def remove_position(*args, **kwargs): return True
    def get_position_age_hours(*args, **kwargs): return 0.0
    def get_all_tracked_positions(): return {}
    def sync_with_exchange_positions(*args, **kwargs): return (0, 0)

# Import three-tier close validation system
try:
    from src.utils.close_validator import (
        validate_close_decision, CloseDecision, ValidationResult,
        format_validation_result, STOP_LOSS_THRESHOLD, PROFIT_TARGET_THRESHOLD,
        TAKE_PROFIT_THRESHOLD, MIN_CONFIDENCE_TO_CLOSE
    )
    CLOSE_VALIDATOR_AVAILABLE = True
except ImportError:
    CLOSE_VALIDATOR_AVAILABLE = False
    STOP_LOSS_THRESHOLD = -2.0
    TAKE_PROFIT_THRESHOLD = 6.0
    PROFIT_TARGET_THRESHOLD = 0.5
    MIN_CONFIDENCE_TO_CLOSE = 80

# Import unified AI gateway
try:
    from src.utils.ai_gateway import (
        analyze_with_ai, AIResponse, parse_ai_response,
        format_position_prompt, format_entry_prompt
    )
    AI_GATEWAY_AVAILABLE = True
except ImportError:
    AI_GATEWAY_AVAILABLE = False

# Import risk management system
try:
    from src.risk.risk_manager import RiskManager
    from src.risk.pnl_calculator import Position
    RISK_MANAGER_AVAILABLE = True
except ImportError:
    RISK_MANAGER_AVAILABLE = False

# Import intelligence integrator for strategy and volume signals
try:
    from src.utils.intelligence_integrator import (
        collect_all_intelligence, get_volume_intel_for_token,
        get_strategy_signals, format_strategy_signals_for_ai,
        format_volume_intel_for_ai, get_volume_summary
    )
    INTELLIGENCE_AVAILABLE = True
except ImportError:
    INTELLIGENCE_AVAILABLE = False
    def collect_all_intelligence(*args, **kwargs): return {"token": "", "combined_context": ""}
    def get_volume_intel_for_token(*args, **kwargs): return None
    def get_volume_summary(): return ""


# Load Environment Variables
load_dotenv()

# Import WebSocket infrastructure
try:
    from src.websocket import (
        start_websocket_feeds,
        stop_websocket_feeds,
        is_websocket_enabled,
        get_data_manager
    )
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    def start_websocket_feeds(*args, **kwargs): pass
    def stop_websocket_feeds(*args, **kwargs): pass
    def is_websocket_enabled(): return False
    def get_data_manager(): return None

# ============================================================================
# 🔧 OPTIONAL: COLOR PRINT & PANDAS SHIM (Keep your existing helpers)
# ============================================================================
try:
    from termcolor import cprint
except Exception:
    def cprint(msg, *args, **kwargs):
        print(msg)

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except Exception as e:
    pd = None
    PANDAS_AVAILABLE = False
    cprint(f"⚠️ pandas not installed: {e}. Using lightweight DataFrame shim.", "yellow")
    import types

    class SimpleDataFrame:
        def __init__(self, data=None, columns=None):
            self._data = list(data) if data else []
            if columns:
                self.columns = list(columns)
            else:
                self.columns = list(self._data[0].keys()) if self._data else []
            self.index = list(range(len(self._data)))

        def __len__(self):
            return len(self._data)

        def head(self, n=5):
            return SimpleDataFrame(self._data[:n], columns=self.columns)

        def tail(self, n=3):
            return SimpleDataFrame(self._data[-n:], columns=self.columns)

        def to_string(self):
            if not self._data:
                return "<empty DataFrame>"
            header = " | ".join(self.columns)
            lines = [header]
            for row in self._data:
                lines.append(" | ".join(str(row.get(c, "")) for c in self.columns))
            return "\n".join(lines)

        def __str__(self):
            return self.to_string()

        def to_dict(self):
            return self._data

    def _concat(dfs, ignore_index=True):
        rows = []
        cols = []
        for df in dfs:
            if isinstance(df, SimpleDataFrame):
                rows.extend(df._data)
                for c in df.columns:
                    if c not in cols:
                        cols.append(c)
            elif isinstance(df, dict):
                rows.append(df)
        return SimpleDataFrame(rows, columns=cols)

    pd = types.SimpleNamespace(DataFrame=SimpleDataFrame, concat=_concat)

# ============================================================================
# 🔧 TRADING AGENT CONFIGURATION
# ============================================================================
from eth_account import Account
from src.config import EXCHANGE as CONFIG_EXCHANGE

# 🦈 EXCHANGE SELECTION - Import from config.py
# Convert to uppercase for consistency with checks throughout this file
EXCHANGE = CONFIG_EXCHANGE.upper() if CONFIG_EXCHANGE else "HYPERLIQUID"

# 🌊 AI MODE SELECTION (Default - can be overridden by user settings)
DEFAULT_SWARM_MODE = False  # True = Swarm Mode (all Models), False = Single Model

# 🌊 SWARM CONSENSUS SETTINGS
# Minimum confidence threshold for swarm consensus to execute a trade
# If consensus confidence is below this threshold, default to NOTHING
# Recommended: 55-65% (requires clear majority, not just a tie)
MIN_SWARM_CONFIDENCE = 65  # 55% = requires at least slight majority (e.g., 3/5 models agree)

# 📈 SINGLE MODEL CONFIDENCE SETTINGS
# Minimum confidence threshold for single model to execute a trade
# If confidence is below this threshold, default to NOTHING
# Recommended: 60-80% (requires strong conviction)
MIN_SINGLE_CONFIDENCE = 70  # 70% = requires strong conviction

# 📈 TRADING MODE SETTINGS
LONG_ONLY = False 

# ============================================================================
# ⚙️ POSITION MANAGEMENT SETTINGS
# ============================================================================
# Minimum age before a position can be closed (in hours), Set to 0.0 to allow immediate exits
# Examples: 0.0 = immediate, 0.25 = 15 min, 0.5 = 30 min, 1.0 = 1 hour
MIN_AGE_HOURS = 0.1

# AI confidence threshold for closing positions (percentage), Lower values = more aggressive closing, Higher values = more conservative
# Recommended range: 60-80%
MIN_CLOSE_CONFIDENCE = 70

# Profit threshold for automatic position closing (percentage), Positions with profit >= this value close immediately, bypassing other checks
TP_THRESHOLD = 0.5

# SINGLE MODEL SETTINGS
AI_MODEL_TYPE = 'openrouter' 
AI_MODEL_NAME = 'x-ai/grok-4.1-fast' 
AI_TEMPERATURE = 0.6   # Official recommended "sweet spot"
AI_MAX_TOKENS = 8024   # Increased for multi-step reasoning

# 💰 POSITION SIZING & RISK MANAGEMENT
USE_PORTFOLIO_ALLOCATION = True 
MAX_POSITION_PERCENTAGE = 90      
LEVERAGE = 20                     

# Stop Loss & Take Profit
STOP_LOSS_PERCENTAGE = 2.0      # SL @ -2% PnL
TAKE_PROFIT_PERCENTAGE = 5.0    # TP @ +5% PnL 
PNL_CHECK_INTERVAL = 5          # check PnL every 5 minutes          

# Legacy settings 
usd_size = 25                  
max_usd_order_size = 3           
CASH_PERCENTAGE = 10

# 📊 MARKET DATA COLLECTION (Default values - can be overridden)
DAYSBACK_4_DATA = 2              # Default: 2 days (overridable via __init__)
DATA_TIMEFRAME = '30m'           # Default: 30 minutes (overridable via __init__)
SAVE_OHLCV_DATA = False          

# ⚡ TRADING EXECUTION SETTINGS
slippage = 199                   
SLEEP_BETWEEN_RUNS_MINUTES = 5  

# 🎯 TOKEN CONFIGURATION
# Note: Account address is loaded from .env via os.getenv("ACCOUNT_ADDRESS")
# or from self.account.address in TradingAgent.__init__()

# For SOLANA exchange
USDC_ADDRESS = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v" 
SOL_ADDRESS = "So11111111111111111111111111111111111111111"    
EXCLUDED_TOKENS = [USDC_ADDRESS, SOL_ADDRESS]

MONITORED_TOKENS = []

# For ASTER/HYPERLIQUID exchanges
SYMBOLS = [
    'ETH',        # Ethereum
    'BTC',        # Bitcoin
    'SOL',        # Solana
    'AAVE',       # Aave
    'LINK',       # Chainlink
    'LTC',        # Litecoin
    'HYPE',       # Hyperliquid Exchange Token
    'FARTCOIN',   # FartCoin (for the fun)
]

# ============================================================================
# 🔌 EXCHANGE IMPORTS
# ============================================================================
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# Corrected Import Logic
if EXCHANGE == "ASTER":
    try:
        from src import nice_funcs_aster as n
        cprint("🦈 Exchange: Aster DEX (Futures)", "cyan", attrs=['bold'])
    except ImportError:
        cprint("❌ Error: nice_funcs_aster not found", "red")
        
elif EXCHANGE == "HYPERLIQUID":
    try:
        from src import nice_funcs_hyperliquid as n
        cprint("🦈 Exchange: HyperLiquid (Perpetuals) - Using local nice_funcs_hyperliquid.py", "cyan", attrs=['bold'])
    except ImportError:
        try:
            import nice_funcs_hyperliquid as n
            cprint("🦈 Exchange: HyperLiquid (Perpetuals) - Using src module", "cyan", attrs=['bold'])
        except ImportError:
            cprint("❌ Error: nice_funcs_hyperliquid.py not found! Ensure it is in the same folder.", "red")
            sys.exit(1)
            
elif EXCHANGE == "SOLANA":
    try:
        from src import nice_funcs as n
        cprint("🦈 Exchange: Solana (On-chain DEX)", "cyan", attrs=['bold'])
    except ImportError:
        cprint("❌ Error: Solana functions not found", "red")

else:
    cprint(f"❌ Unknown exchange: {EXCHANGE}", "red")
    cprint("Available exchanges: ASTER, HYPERLIQUID, SOLANA", "yellow")
    sys.exit(1)

from src.data.ohlcv_collector import collect_all_tokens

# ============================================================================
# PROMPTS - Now imported from src.agents.trading.prompts
# ============================================================================
# AI prompt templates have been extracted to src/agents/trading/prompts.py
# for better maintainability. They are imported at the top of this file.


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def extract_json_from_text(text):
    """Extract JSON from text. Wrapper for extracted function in market_analyzer module."""
    return _extract_json_from_text(text)


def get_account_balance(account=None):
    """Get account balance in USD based on exchange type"""
    try:
        if EXCHANGE in ["ASTER", "HYPERLIQUID"]:
            if EXCHANGE == "ASTER":
                balance_dict = n.get_account_balance()
                balance = balance_dict.get('available', 0) 
                cprint(f"💰 {EXCHANGE} Available Balance: ${balance:,.2f} USD", "cyan")
                
            else:  # HYPERLIQUID
                address = os.getenv("ACCOUNT_ADDRESS")
                if not address:
                    if account is None:
                        account = n._get_account_from_env()
                    address = account.address

                try:
                    if hasattr(n, 'get_available_balance'):
                        balance = n.get_available_balance(address)
                        cprint(f"💰 {EXCHANGE} Available (Free) USDC: ${balance}", "cyan")
                        
                        total_val = n.get_account_value(address)
                        cprint(f"   (Total Equity including positions: ${total_val})", "white")
                    else:
                        cprint("⚠️ Using Total Equity (Warning: Checks locked collateral)", "yellow")
                        balance = n.get_account_value(address)
                        
                except Exception as e:
                    cprint(f"❌ Error getting balance: {e}", "red")
                    balance = 0

            return float(balance)
            
        else:
            # SOLANA
            balance = n.get_token_balance_usd(USDC_ADDRESS)
            return balance
            
    except Exception as e:
        cprint(f"❌ Error getting account balance: {e}", "red")
        return 0


def calculate_position_size(account_balance):
    """Calculate position size. Wrapper for extracted function in position_manager module."""
    return _calculate_position_size(account_balance, EXCHANGE, MAX_POSITION_PERCENTAGE, LEVERAGE)


# ============================================================================
# TRADING AGENT CLASS
# ============================================================================

class TradingAgent:
    def __init__(self, timeframe=None, days_back=None, stop_check_callback=None,
                 symbols=None, ai_provider=None, ai_model=None,
                 ai_temperature=None, ai_max_tokens=None,
                 swarm_mode=None, swarm_models=None,
                 min_single_confidence=None, min_swarm_confidence=None,
                 take_profit_pct=None, stop_loss_pct=None,
                 max_position_pct=None, leverage=None, cash_buffer_pct=None,
                 min_age_hours=None, min_close_confidence=None):
        """
        Initialize Trading Agent with configurable settings

        Args:
            timeframe (str): Data timeframe (e.g., '5m', '30m', '1h'). Defaults to DATA_TIMEFRAME.
            days_back (int): Days of historical data to fetch. Defaults to DAYSBACK_4_DATA.
            stop_check_callback (callable): Optional callback that returns True if agent should stop.
            symbols (list): List of token symbols to analyze. Defaults to SYMBOLS.
            ai_provider (str): AI provider to use (e.g., 'gemini', 'anthropic'). Defaults to AI_MODEL_TYPE.
            ai_model (str): AI model name to use. Defaults to AI_MODEL_NAME.
            ai_temperature (float): Temperature for AI model (0.0-1.0). Defaults to AI_TEMPERATURE.
            ai_max_tokens (int): Max tokens for AI response. Defaults to AI_MAX_TOKENS.
            swarm_mode (str): 'single' or 'swarm'. Defaults to 'single'.
            swarm_models (list): List of swarm model configs for multi-agent consensus.
        """
        # Store configurable settings as instance variables
        self.timeframe = timeframe if timeframe is not None else DATA_TIMEFRAME
        self.days_back = days_back if days_back is not None else DAYSBACK_4_DATA
        self.stop_check_callback = stop_check_callback

        # Store AI settings (use passed values or fall back to config defaults)
        self.ai_provider = ai_provider if ai_provider is not None else AI_MODEL_TYPE
        self.ai_model_name = ai_model if ai_model is not None else AI_MODEL_NAME
        self.ai_temperature = ai_temperature if ai_temperature is not None else AI_TEMPERATURE
        self.ai_max_tokens = ai_max_tokens if ai_max_tokens is not None else AI_MAX_TOKENS

        # Store swarm mode settings (use passed values or fall back to defaults)
        self.use_swarm_mode = (swarm_mode == 'swarm') if swarm_mode is not None else DEFAULT_SWARM_MODE
        self.swarm_models_config = swarm_models or []

        # Confidence thresholds
        self.min_single_confidence = min_single_confidence if min_single_confidence is not None else MIN_SINGLE_CONFIDENCE
        self.min_swarm_confidence = min_swarm_confidence if min_swarm_confidence is not None else MIN_SWARM_CONFIDENCE
        
        # Risk management settings
        self.take_profit_pct = take_profit_pct if take_profit_pct is not None else TAKE_PROFIT_PERCENTAGE
        self.stop_loss_pct = stop_loss_pct if stop_loss_pct is not None else STOP_LOSS_PERCENTAGE
        
        # Position sizing settings
        self.max_position_pct = max_position_pct if max_position_pct is not None else MAX_POSITION_PERCENTAGE
        self.leverage = leverage if leverage is not None else LEVERAGE
        self.cash_buffer_pct = cash_buffer_pct if cash_buffer_pct is not None else CASH_PERCENTAGE
        
        # Position management settings
        self.min_age_hours = min_age_hours if min_age_hours is not None else MIN_AGE_HOURS
        self.min_close_confidence = min_close_confidence if min_close_confidence is not None else MIN_CLOSE_CONFIDENCE

        # Store symbols to analyze (use passed values or fall back to config)
        if symbols is not None:
            self.symbols = symbols
        elif EXCHANGE in ["ASTER", "HYPERLIQUID"]:
            self.symbols = SYMBOLS
        else:
            self.symbols = MONITORED_TOKENS

        self.account = None
        if EXCHANGE == "HYPERLIQUID":
            cprint("🔑 Initializing Hyperliquid Account...", "cyan")
            try:
                # Standardized key lookup
                raw_key = os.getenv("HYPER_LIQUID_ETH_PRIVATE_KEY", "") or os.getenv("HYPER_LIQUID_KEY", "")
                clean_key = raw_key.strip().replace('"', '').replace("'", "")

                if not clean_key:
                    raise ValueError("Private Key not found in .env")

                self.account = Account.from_key(clean_key)
                self.address = os.getenv("ACCOUNT_ADDRESS")

                if not self.address:
                    self.address = self.account.address

                cprint(f"✅ Account loaded successfully! Address: {self.address}", "green")
            except Exception as e:
                cprint(f"❌ Error loading key: {e}", "red")
                sys.exit(1)

        # 🚀 WebSocket Startup (for real-time data - ONCE per agent instance)
        if WEBSOCKET_AVAILABLE and EXCHANGE == 'HYPERLIQUID':
            try:
                cprint("\n🔌 Starting WebSocket feeds...", "cyan")
                start_websocket_feeds()

                if is_websocket_enabled():
                    cprint("🟢 WebSocket feeds started successfully", "green")

                    # Subscribe to user state for real-time account updates
                    if hasattr(self, 'address') and self.address:
                        try:
                            dm = get_data_manager()
                            if dm:
                                dm.subscribe_user_state(self.address)
                                cprint(f"📍 Subscribed to user state: {self.address[:6]}...{self.address[-4:]}", "green")
                        except Exception as e:
                            cprint(f"⚠️  User state subscription failed: {e}", "yellow")
                else:
                    cprint("🟡 WebSocket feeds not enabled — using REST fallback", "yellow")
            except Exception as e:
                cprint(f"⚠️  WebSocket initialization failed: {e}", "red")

        # Check if using swarm mode or single model
        if self.use_swarm_mode:
            # Convert user's swarm_models format to SwarmAgent's format
            custom_models = self._build_swarm_models_config()
            num_models = len(custom_models) if custom_models else 6

            cprint(
                f"\n🌊 Initializing Trading Agent in SWARM MODE ({num_models} AI consensus)...",
                "cyan",
                attrs=["bold"]
            )

            # Initialize SwarmAgent with custom models from user settings
            if custom_models:
                self.swarm = SwarmAgent(custom_models=custom_models)
                cprint(f"✅ Swarm mode initialized with {num_models} user-configured AI models!", "green")
            else:
                self.swarm = SwarmAgent()
                cprint("✅ Swarm mode initialized with default AI models!", "green")

            cprint("💼 Initializing fast model for portfolio calculations...", "cyan")
            self.model = model_factory.get_model(self.ai_provider, self.ai_model_name)
            if self.model:
                cprint(f"✅ Allocation model ready: {self.model.model_name}", "green")
        else:
            cprint(f"\n⚙️ Initializing Trading Agent with {self.ai_provider} model...", "cyan")
            self.model = model_factory.get_model(self.ai_provider, self.ai_model_name)
            self.swarm = None

            if not self.model:
                cprint(f"❌ Failed to initialize {self.ai_provider} model!", "red")
                cprint("Available models:", "yellow")
                for model_type in model_factory._models.keys():
                    cprint(f"   - {model_type}", "yellow")
                sys.exit(1)

            cprint(f"✅ Using model: {self.model.model_name}", "green")

        # Initialize risk management system
        if RISK_MANAGER_AVAILABLE:
            self.risk_manager = RiskManager(max_leverage=self.leverage)
            cprint("🛡️ Risk Management System initialized", "cyan")
        else:
            self.risk_manager = None
            cprint("⚠️ Risk Management System not available", "yellow")

        # Add recently_closed tracker for allocation flow fixes
        self.recently_closed = {}  # dict: symbol -> timestamp (float, seconds since epoch)
        self.REENTRY_GRACE_PERIOD = 15  # seconds - short grace period to ignore ghost positions

        self.recommendations_df = pd.DataFrame(
            columns=["token", "action", "confidence", "reasoning"]
        )

        # --- StrategyAgent (non-executing) ---
        try:
            self.strategy_agent = StrategyAgent(execute_signals=False)
            cprint("✅ StrategyAgent initialized (execute_signals=False)", "green")
        except Exception as e:
            self.strategy_agent = None
            cprint(f"⚠️ StrategyAgent failed to initialize: {e}", "yellow")

        # Simple in-memory cache for enriched strategy contexts per token
        # token -> {'data': ..., 'expires_at': datetime}
        self._strategy_context_cache = {}
        self.STRATEGY_CONTEXT_TTL = 120  # seconds (tune for your timeframe)





        # Show which tokens will be analyzed
        cprint("\n🎯 Active Tokens for Trading:", "yellow", attrs=["bold"])
        cprint(f"🦈 Exchange: {EXCHANGE}", "cyan")

        for i, token in enumerate(self.symbols, 1):
            token_display = token[:8] + "..." if len(token) > 8 else token
            cprint(f"   {i}. {token_display}", "cyan")

        cprint(
            f"\n⏱️  Estimated analysis time: ~{len(self.symbols) * 60} seconds\n",
            "yellow"
        )

        cprint(f"\n🦈 Active Exchange: {EXCHANGE}", "yellow", attrs=["bold"])
        cprint("📈 Trading Mode:", "yellow", attrs=["bold"])
        if LONG_ONLY:
            cprint("   📊 LONG ONLY - No shorting enabled", "cyan")
            cprint("   💡 SELL signals close positions, can't open shorts", "white")
        else:
            cprint("   ⚡ LONG/SHORT - Full directional trading", "green")
            cprint("   💡 SELL signals can close longs OR open shorts", "white")

        cprint("\n✅ LLM Trading Agent initialized!", "green")
        add_console_log("Agent initialized!", "success")

    def _get_performance_metrics(self):
        """Calculate recent trading performance for AI motivation.
        Wrapper for extracted function in ai_interface module.
        """
        return _get_performance_metrics()

    def _build_swarm_models_config(self):
        """
        Convert user's swarm_models format to SwarmAgent's expected format.

        User format (from settings):
        [
            {"provider": "gemini", "model": "gemini-2.5-flash", "temperature": 0.3, "max_tokens": 2000},
            {"provider": "openai", "model": "gpt-4o", "temperature": 0.5, "max_tokens": 2000},
            ...
        ]

        SwarmAgent format:
        {
            "gemini_1": (True, "gemini", "gemini-2.5-flash"),
            "openai_2": (True, "openai", "gpt-4o"),
            ...
        }
        """
        if not self.swarm_models_config:
            return None

        custom_models = {}
        for i, model_config in enumerate(self.swarm_models_config, 1):
            provider = model_config.get('provider', 'openrouter')
            model_name = model_config.get('model', 'nex-agi/deepseek-v3.1-nex-n1:free')

            # Create unique key for each model (e.g., "gemini_1", "openai_2")
            model_key = f"{provider}_{i}"

            # SwarmAgent expects: (enabled, provider_type, model_name)
            custom_models[model_key] = (True, provider, model_name)

            cprint(f"   📦 Swarm Model {i}: {provider}/{model_name}", "cyan")

        return custom_models if custom_models else None

    def chat_with_ai(self, system_prompt, user_content):
        """Send prompt to AI model. Wrapper for extracted function in ai_interface module."""
        return _chat_with_ai(
            self.model, system_prompt, user_content,
            self.ai_temperature, self.ai_max_tokens
        )

    def _format_market_data_for_swarm(self, token, market_data):
        """Format market data for swarm analysis. Wrapper for extracted function."""
        return _format_market_data_for_swarm(token, market_data, self.timeframe)

    def _calculate_swarm_consensus(self, swarm_result):
        """Calculate swarm consensus. Wrapper for extracted function."""
        return _calculate_swarm_consensus(swarm_result, self.min_swarm_confidence)

    def _parse_vote_from_response(self, response_upper):
        """Parse vote from response. Wrapper for extracted function in ai_interface module."""
        return _parse_vote_from_response(response_upper)

    def fetch_all_open_positions(self):
        """
        Fetch ALL open positions across all symbols with age tracking.

        CRITICAL FIX: Now iterates through ALL subpositions, not just the first one.
        This ensures we detect multiple positions for the same symbol.
        """
        cprint("\n" + "=" * 60, "cyan")
        cprint("📊 FETCHING ALL OPEN POSITIONS", "white", "on_blue", attrs=["bold"])
        cprint("=" * 60, "cyan")

        all_positions = {}
        exchange_positions = {}  # For syncing with tracker
        # CRITICAL: Use self.symbols (instance variable) NOT global SYMBOLS/MONITORED_TOKENS
        # This ensures user-configured symbols from settings are respected
        check_tokens = self.symbols
        total_position_count = 0

        for symbol in check_tokens:
            try:
                # get_position returns: positions (list), im_in_pos, pos_size, pos_sym, entry_px, pnl_perc, is_long
                # The 'positions' list contains ALL subpositions for this symbol
                pos_data = n.get_position(symbol, self.account)

                # Validate pos_data before unpacking
                if pos_data is None or not isinstance(pos_data, tuple) or len(pos_data) < 7:
                    continue

                positions_list, im_in_pos, _, _, _, _, _ = pos_data

                if im_in_pos and positions_list:
                    # CRITICAL FIX: Iterate through ALL positions, not just the first one
                    for pos in positions_list:
                        pos_size = float(pos.get("szi", 0))
                        entry_px = float(pos.get("entryPx", 0))
                        pnl_perc = float(pos.get("returnOnEquity", 0)) * 100
                        is_long = pos_size > 0

                        if pos_size == 0:
                            continue

                        # Get position age from tracker
                        age_hours = 0.0
                        if POSITION_TRACKER_AVAILABLE:
                            age_hours = get_position_age_hours(symbol)

                        position_data = {
                            "symbol": symbol,
                            "size": pos_size,
                            "entry_price": entry_px,
                            "pnl_percent": pnl_perc,
                            "is_long": is_long,
                            "side": "LONG" if is_long else "SHORT",
                            "age_hours": age_hours,
                        }

                        # Store for tracker sync (use combined size for all positions of this symbol)
                        if symbol not in exchange_positions:
                            exchange_positions[symbol] = {
                                "entry_price": entry_px,
                                "size": 0,
                                "is_long": is_long
                            }
                        exchange_positions[symbol]["size"] += pos_size

                        if symbol not in all_positions:
                            all_positions[symbol] = []
                        all_positions[symbol].append(position_data)
                        total_position_count += 1

                        # Include age in display
                        age_str = f"{age_hours:.1f}h" if age_hours > 0 else "NEW"
                        cprint(
                            f"   {symbol:<10} | {position_data['side']:<10} | "
                            f"Size: {pos_size:>10.4f} | Entry: ${entry_px:>10.2f} | "
                            f"PnL: {pnl_perc:>6.2f}% | Age: {age_str}",
                            "cyan",
                        )

            except Exception as e:
                cprint(f"   ❌ Error fetching {symbol}: {e}", "red")
                continue

        # Show total count (including subpositions)
        cprint(f"\n   📊 Total positions detected: {total_position_count}", "yellow", attrs=["bold"])

        # Sync tracker with actual exchange positions
        if POSITION_TRACKER_AVAILABLE and exchange_positions:
            added, removed = sync_with_exchange_positions(exchange_positions)
            if added > 0:
                cprint(f"   📍 Added {added} position(s) to tracker", "yellow")
            if removed > 0:
                cprint(f"   📍 Removed {removed} stale position(s) from tracker", "yellow")

        if not all_positions:
            cprint("   ℹ️  No open positions found", "yellow")

        cprint("=" * 60 + "\n", "cyan")
        return all_positions

    def validate_close_decision(self, symbol, pnl_percent, age_hours, ai_confidence, ai_decision="CLOSE"):
        """
        Three-Tier Position Close Validation System.

        Tier 0: Emergency Stop Loss (-2% or worse) - FORCE CLOSE
        Tier 1: Profit Target (+0.5% or better) - AI decides
        Tier 2: Age Gating (young positions < 1.5h need protection)
        Tier 3: Mature Position Analysis with loss-adjusted confidence

        Returns: (should_close: bool, reason: str)
        """
        cprint(f"\n🔍 VALIDATING CLOSE DECISION FOR {symbol}:", "yellow", attrs=["bold"])
        cprint(f"   📊 P&L: {pnl_percent:.2f}% | Age: {age_hours:.1f}h | AI Confidence: {ai_confidence}%", "cyan")

        # Use the close validator if available
        if CLOSE_VALIDATOR_AVAILABLE:
            result = validate_close_decision(
                symbol=symbol,
                pnl_percent=pnl_percent,
                age_hours=age_hours,
                ai_decision=ai_decision,
                ai_confidence=ai_confidence
            )

            # Display validation result
            tier_names = {0: "STOP LOSS", 1: "PROFIT TARGET", 2: "YOUNG POSITION", 3: "MATURE POSITION"}
            tier_name = tier_names.get(result.tier_triggered, "UNKNOWN")

            if result.decision == CloseDecision.FORCE_CLOSE:
                cprint(f"   🚨 TIER {result.tier_triggered} ({tier_name}): FORCE CLOSE", "red", attrs=["bold"])
                cprint(f"   💡 {result.reason}", "red")
                add_console_log(f"STOP LOSS: Closing {symbol} at {pnl_percent:.2f}%", "warning")
                return True, result.reason

            elif result.decision == CloseDecision.FORCE_TAKE_PROFIT:
                cprint(f"   🎯 TIER {result.tier_triggered} (TAKE PROFIT): FORCE CLOSE", "green", attrs=["bold"])
                cprint(f"   💡 {result.reason}", "green")
                add_console_log(f"TAKE PROFIT: Closing {symbol} at +{pnl_percent:.2f}%", "success")
                return True, result.reason

            elif result.decision == CloseDecision.CLOSE:
                cprint(f"   ✅ TIER {result.tier_triggered} ({tier_name}): CLOSE APPROVED", "green", attrs=["bold"])
                cprint(f"   📈 Confidence: {result.original_confidence}% → {result.adjusted_confidence}% (boost: +{result.confidence_boost}%)", "green")
                cprint(f"   💡 {result.reason}", "green")
                return True, result.reason

            elif result.decision == CloseDecision.PROTECTED:
                cprint(f"   🛡️ TIER {result.tier_triggered} ({tier_name}): PROTECTED", "cyan", attrs=["bold"])
                cprint(f"   💡 {result.reason}", "cyan")
                return False, result.reason

            else:  # KEEP
                cprint(f"   ⏸️ TIER {result.tier_triggered} ({tier_name}): KEEP", "yellow", attrs=["bold"])
                cprint(f"   📉 Confidence: {result.original_confidence}% → {result.adjusted_confidence}% (boost: +{result.confidence_boost}%)", "yellow")
                cprint(f"   💡 {result.reason}", "yellow")
                return False, result.reason

        # Fallback to simple validation if close validator not available
        else:
            # Simple fallback: Stop loss at -2%, take profit at +5%, otherwise AI decides
            if pnl_percent <= STOP_LOSS_THRESHOLD:
                cprint(f"   🚨 STOP LOSS TRIGGERED: {pnl_percent:.2f}%", "red", attrs=["bold"])
                add_console_log(f"STOP LOSS: Closing {symbol} at {pnl_percent:.2f}%", "warning")
                return True, f"Stop loss at {pnl_percent:.2f}%"

            if pnl_percent >= TAKE_PROFIT_THRESHOLD:
                cprint(f"   🎯 TAKE PROFIT TRIGGERED: +{pnl_percent:.2f}%", "green", attrs=["bold"])
                add_console_log(f"TAKE PROFIT: Closing {symbol} at +{pnl_percent:.2f}%", "success")
                return True, f"Take profit at +{pnl_percent:.2f}%"

            if pnl_percent >= PROFIT_TARGET_THRESHOLD and ai_confidence >= MIN_CONFIDENCE_TO_CLOSE:
                cprint(f"   ✅ PROFIT TARGET: {pnl_percent:.2f}%, confidence {ai_confidence}%", "green")
                return True, f"Profit target at {pnl_percent:.2f}%"

            cprint(f"   ⏸️ KEEP: P&L {pnl_percent:.2f}%, confidence {ai_confidence}%", "yellow")
            return False, f"Keep position - P&L {pnl_percent:.2f}%, confidence {ai_confidence}%"

    def analyze_open_positions_with_ai(self, positions_data, market_data):
        """Enhanced with guaranteed TP/SL enforcement"""
        if not positions_data:
            return {}

        cprint("\n" + "=" * 60, "yellow")
        cprint("📊 AI ANALYZING OPEN POSITIONS", "white", "on_magenta", attrs=["bold"])
        cprint("=" * 60, "yellow")

        # Log each position being analyzed
        for symbol, positions in positions_data.items():
            for pos in positions:
                side = "LONG" if pos["is_long"] else "SHORT"
                entry = pos["entry_price"]
                pnl = pos["pnl_percent"]
                pnl_emoji = "🟢" if pnl >= 0 else "🔴"
                add_console_log(f"   {pnl_emoji} {symbol} ({side}) | Entry: ${entry:.2f} | PnL: {pnl:+.2f}%", "info")

        # CRITICAL: Check TP/SL thresholds FIRST - force close regardless of AI analysis
        validated_decisions = {}
        for symbol, positions in positions_data.items():
            for pos in positions:
                pnl_percent = pos["pnl_percent"]

                # Force TP/SL using helpers
                if should_trigger_take_profit(pnl_percent, TAKE_PROFIT_THRESHOLD):
                    reason = f"TAKE PROFIT: {pnl_percent:.2f}% >= {TAKE_PROFIT_THRESHOLD}%"
                    validated_decisions[symbol] = {"action": "CLOSE", "reasoning": reason, "confidence": 100}
                    cprint(f"🚨 {symbol}: TAKE PROFIT TRIGGERED - {pnl_percent:.2f}%", "red", attrs=["bold"])
                    add_console_log(f"TAKE PROFIT: Closing {symbol} at +{pnl_percent:.2f}%", "success")
                    continue
                elif should_trigger_stop_loss(pnl_percent, STOP_LOSS_THRESHOLD):
                    reason = f"STOP LOSS: {pnl_percent:.2f}% <= {STOP_LOSS_THRESHOLD}%"
                    validated_decisions[symbol] = {"action": "CLOSE", "reasoning": reason, "confidence": 100}
                    cprint(f"🚨 {symbol}: STOP LOSS TRIGGERED - {pnl_percent:.2f}%", "red", attrs=["bold"])
                    add_console_log(f"STOP LOSS: Closing {symbol} at {pnl_percent:.2f}%", "warning")
                    continue

        # Build position summary for remaining positions
        position_summary = []
        for symbol, positions in positions_data.items():
            if symbol in validated_decisions:
                continue  # Skip positions already handled by TP/SL
                
            for pos in positions:
                position_summary.append({
                    "symbol": symbol,
                    "side": "LONG" if pos["is_long"] else "SHORT",
                    "size": pos["size"],
                    "entry_price": pos["entry_price"],
                    "current_pnl": pos["pnl_percent"],
                    "age_hours": pos["age_hours"],
                })

        # Format market conditions
        market_summary = {}
        for symbol in positions_data.keys():
            if symbol in validated_decisions:
                continue  # Skip positions already handled
                
            if symbol in market_data:
                df = market_data[symbol]
                if not df.empty:
                    latest = df.iloc[-1]

                    # Robustly detect the correct close column
                    if "Close" in df.columns:
                        current_price = latest["Close"]
                    elif "close" in df.columns:
                        current_price = latest["close"]
                    elif "close_price" in df.columns:
                        current_price = latest["close_price"]
                    elif "c" in df.columns:
                        current_price = latest["c"]
                    elif "price" in df.columns:
                        current_price = latest["price"]
                    else:
                        cprint(f"⚠️ No close price column found for {symbol}, skipping...", "yellow")
                        continue

                    market_summary[symbol] = {
                        "current_price": current_price,
                        "ma20": latest.get("MA20", 0),
                        "ma40": latest.get("MA40", 0),
                        "rsi": latest.get("RSI", 0),
                        "trend": "Bullish" if current_price > latest.get("MA20", 0) else "Bearish",
                    }

        # Only analyze positions that weren't force-closed by TP/SL
        if position_summary:
            user_prompt = f"""Analyze these open positions:

POSITIONS:
{json.dumps(position_summary, indent=2)}

CURRENT MARKET CONDITIONS:
{json.dumps(market_summary, indent=2)}

For each position, decide KEEP or CLOSE with reasoning.
Return ONLY valid JSON with the following structure:
{{
  "SYMBOL": {{
     "action": "KEEP" or "CLOSE",
     "reasoning": "short explanation"
  }}
}}"""

            try:
                response = self.chat_with_ai(POSITION_ANALYSIS_PROMPT, user_prompt)

                # Handle None response from AI
                if not response:
                    cprint("❌ No response from AI for position analysis", "red")
                    return validated_decisions

                # Strip Markdown fences if model wrapped response in code blocks
                if "```json" in response:
                    response = response.split("```json")[1].split("```")[0]
                elif "```" in response:
                    response = response.split("```")[1].split("```")[0]

                # Try safe JSON extraction first
                decisions = extract_json_from_text(response)
                if not decisions:
                    cprint("⚠️ AI response not valid JSON. Attempting text fallback...", "yellow")

                    text = response.lower()
                    decisions = {}
                    for symbol in position_summary:
                        sym = symbol["symbol"]
                        if sym.lower() in text:
                            if "close" in text or "sell" in text:
                                decisions[sym] = {
                                    "action": "CLOSE",
                                    "reasoning": "Detected CLOSE or SELL keyword in fallback parsing.",
                                    "confidence": 60  # Default confidence for fallback
                                }
                            elif "keep" in text or "hold" in text or "open" in text:
                                decisions[sym] = {
                                    "action": "KEEP",
                                    "reasoning": "Detected KEEP/HOLD keyword in fallback parsing.",
                                    "confidence": 0
                                }
                            else:
                                decisions[sym] = {
                                    "action": "KEEP",
                                    "reasoning": "No clear directive, default KEEP.",
                                    "confidence": 0
                                }
                        else:
                            decisions[sym] = {
                                "action": "KEEP",
                                "reasoning": "Symbol not mentioned, default KEEP.",
                                "confidence": 0
                            }

                    cprint(f"🧠 Fallback interpreted decisions: {decisions}", "cyan")

                if not decisions:
                    cprint("❌ Error: Could not interpret AI analysis at all.", "red")
                    cprint(f"   Raw response: {response}", "yellow")
                    return validated_decisions

                # ============================================================================
                # APPLY 3-TIER VALIDATION SYSTEM
                # ============================================================================
                cprint("\n" + "=" * 60, "magenta")
                cprint("🛡️ APPLYING 3-TIER VALIDATION SYSTEM", "white", "on_magenta", attrs=["bold"])
                cprint("=" * 60, "magenta")

                for symbol, decision in decisions.items():
                    action = decision.get("action", "KEEP")
                    reason = decision.get("reasoning", "")
                    ai_confidence = int(decision.get("confidence", 0))

                    if action.upper() == "CLOSE":
                        # Get position data for validation
                        pos_data = positions_data.get(symbol, [{}])[0]
                        pnl_percent = pos_data.get("pnl_percent", 0)
                        age_hours = pos_data.get("age_hours", 0)

                        # Run validation
                        should_close, validation_reason = self.validate_close_decision(
                            symbol, pnl_percent, age_hours, ai_confidence
                        )

                        if should_close:
                            validated_decisions[symbol] = {
                                "action": "CLOSE",
                                "reasoning": f"{reason} | Validation: {validation_reason}",
                                "confidence": ai_confidence
                            }
                            cprint(f"✅ {symbol}: CLOSE APPROVED", "green", attrs=["bold"])
                        else:
                            validated_decisions[symbol] = {
                                "action": "KEEP",
                                "reasoning": f"AI suggested CLOSE but validation BLOCKED: {validation_reason}",
                                "confidence": 0
                            }
                            cprint(f"🛡️ {symbol}: CLOSE BLOCKED → FORCING KEEP", "cyan", attrs=["bold"])
                            add_console_log(f"🛡️ {symbol} CLOSE blocked: {validation_reason}", "warning")
                    else:
                        # KEEP decision - no validation needed
                        validated_decisions[symbol] = decision

            except Exception as e:
                cprint(f"❌ Error in AI analysis: {e}", "red")
                import traceback
                traceback.print_exc()

        # Print final validated decisions
        cprint("\n" + "=" * 60, "magenta")
        cprint("🎯 FINAL VALIDATED DECISIONS:", "white", "on_magenta", attrs=["bold"])
        cprint("=" * 60, "magenta")

        for symbol, decision in validated_decisions.items():
            action = decision.get("action", "UNKNOWN")
            reason = decision.get("reasoning", "")
            confidence = decision.get("confidence", 0)
            color = "red" if action.upper() == "CLOSE" else "green"
            cprint(f"   {symbol:<10} → {action:<6} | {reason}", color)
            # Short format for dashboard: "SYMBOL -> ACTION"
            add_console_log(f"{symbol} -> {action}", "info")

            # Short format for dashboard
            if action.upper() == "CLOSE":
                add_console_log(f"{symbol} -> CLOSE ({confidence}% Sure)", "warning")
            else:
                add_console_log(f"{symbol} -> KEEP", "info")

        cprint("=" * 60 + "\n", "magenta")
        return validated_decisions

    def execute_position_closes(self, close_decisions):
        """Execute closes for positions marked by AI with verification"""
        if not close_decisions:
            return

        cprint("\n" + "=" * 60, "red")
        cprint("🔄 EXECUTING POSITION CLOSES", "white", "on_red", attrs=["bold"])
        cprint("=" * 60, "red")

        closed_count = 0
        failed_closes = []

        for symbol, decision in close_decisions.items():
            if decision["action"] == "CLOSE":
                try:
                    cprint(f"\n   📉 Closing {symbol}...", "yellow")
                    cprint(f"   💡 Reason: {decision['reasoning']}", "white")

                    # Execute close
                    close_result = n.close_complete_position(symbol, self.account)

                    if close_result:
                        # Verify position is actually closed
                        verification_attempts = 0
                        max_verification_attempts = 5
                        position_closed = False
                        
                        while verification_attempts < max_verification_attempts:
                            time.sleep(1)  # Wait 1 second between checks
                            verification_attempts += 1
                            
                            try:
                                # Check if position is actually closed
                                pos_data = n.get_position(symbol, self.account)

                                # Validate pos_data before unpacking
                                if pos_data is None or not isinstance(pos_data, tuple) or len(pos_data) < 7:
                                    cprint(f"   ⚠️ Could not verify {symbol} closure - invalid data", "yellow")
                                    break

                                _, im_in_pos, pos_size, _, _, _, _ = pos_data

                                if not im_in_pos or pos_size == 0:
                                    position_closed = True
                                    break
                                else:
                                    cprint(f"   ⏳ Verifying {symbol} closure... (attempt {verification_attempts}/{max_verification_attempts})", "yellow")
                                    
                            except Exception as verify_error:
                                cprint(f"   ⚠️ Verification error for {symbol}: {verify_error}", "yellow")
                                break
                        
                        if position_closed:
                            # Remove from position tracker
                            if POSITION_TRACKER_AVAILABLE:
                                remove_position(symbol)
                                cprint(f"   📍 Removed {symbol} from position tracker", "cyan")

                            cprint(f"✅ {symbol} position closed successfully", "green", attrs=["bold"])
                            add_console_log(f"✅ Closed {symbol} | Reason: {decision['reasoning']}", "success")
                            closed_count += 1
                        else:
                            cprint(f"   ❌ {symbol} position close verification FAILED", "red", attrs=["bold"])
                            cprint(f"   ⚠️ Position may still be open - will retry next cycle", "yellow")
                            add_console_log(f"❌ {symbol} close verification failed - position may still be open", "error")
                            failed_closes.append(symbol)
                    else:
                        cprint(f"   ⚠️ Position close returned False for {symbol}", "yellow")
                        add_console_log(f"⚠️ Close may have failed for {symbol}", "warning")
                        failed_closes.append(symbol)

                    time.sleep(2)

                except Exception as e:
                    cprint(f"   ❌ Error closing {symbol}: {e}", "red")
                    import traceback
                    traceback.print_exc()
                    failed_closes.append(symbol)

        if closed_count > 0:
            cprint(
                f"\n✨ Successfully closed {closed_count} position(s)",
                "white",
                "on_green",
                attrs=["bold"],
            )
        else:
            cprint("\n   ℹ️  No positions needed closing", "cyan")

        if failed_closes:
            cprint(f"\n⚠️ Failed to close {len(failed_closes)} positions: {', '.join(failed_closes)}", "red")
            cprint("💡 These will be retried in the next cycle", "yellow")

        cprint("=" * 60 + "\n", "red")

    # ==================================================
    # Strategy Context Helpers
    # ==================================================

    def _get_cached_strategy_context(self, token):
        try:
            now = datetime.utcnow()

            cache = self._strategy_context_cache.get(token)
            if cache and cache["expires_at"] > now:
                return cache["data"]

            if not self.strategy_agent:
                return None

            strategy_context = self.strategy_agent.get_enriched_context(token)

            self._strategy_context_cache[token] = {
                "data": strategy_context,
                "expires_at": now + timedelta(seconds=self.STRATEGY_CONTEXT_TTL),
            }

            return strategy_context

        except Exception as e:
            cprint(f"⚠️ Strategy context error: {e}", "yellow")
            return None


    def _format_strategy_context_text(self, strategy_context):
        """Format strategy context. Wrapper for extracted function in market_analyzer module."""
        return _format_strategy_context_text(strategy_context)
   

   
    def analyze_market_data(self, token, market_data):
        """Analyze market data using AI model (single or swarm mode)"""
        try:
            if token in EXCLUDED_TOKENS:
                print(f"⚠️ Skipping analysis for excluded token: {token}")
                return None

            # Fetch current position context
            position_context = "CURRENT POSITION: None (You have no exposure)."

            try:
                raw_pos_data = n.get_position(token, self.account)

                # Validate pos_data before unpacking
                if raw_pos_data is None or not isinstance(raw_pos_data, tuple) or len(raw_pos_data) < 7:
                    pass  # Keep default position_context
                else:
                    _, im_in_pos, pos_size, _, entry_px, pnl_perc, is_long = raw_pos_data

                    if im_in_pos:
                        side = "LONG" if is_long else "SHORT"

                        if entry_px == 0 and pnl_perc == 0:
                            position_context = (
                                f"CURRENT POSITION: ✅ Active {side} (Spot) | Size: {pos_size}"
                            )
                        else:
                            position_context = (
                                f"CURRENT POSITION: ✅ Active {side} | "
                                f"Size: {pos_size} | Entry: ${entry_px:.4f} | "
                                f"PnL: {pnl_perc:.2f}%"
                            )
            except Exception as e:
                cprint(f"⚠️ Error fetching position context: {e}", "yellow")

            cprint(f"   ℹ️  Context: {position_context}", "cyan")

            # ============================================================
            # SWARM MODE
            # ============================================================
            if self.use_swarm_mode:
                num_models = len(self.swarm.active_models) if self.swarm else 6
                cprint(
                    f"\n🌊 Analyzing {token[:8]}... with SWARM ({num_models} AI models voting)",
                    "cyan",
                    attrs=["bold"],
                )

                # Get performance context for motivation
                performance_metrics = self._get_performance_metrics()
                performance_context = (
                    f"Win Rate: {performance_metrics['win_rate']}% | "
                    f"Total PnL: ${performance_metrics['total_pnl']} | "
                    f"Grade: {performance_metrics['grade']} | "
                    f"Recent Trades: {performance_metrics['winning_trades']}/{performance_metrics['total_trades']}"
                )

                base_market_data = self._format_market_data_for_swarm(token, market_data)
                formatted_data = f"{position_context}\n\n{base_market_data}"

                swarm_result = self.swarm.query(
                    prompt=formatted_data, system_prompt=SWARM_TRADING_PROMPT.format(performance_context=performance_context)
                )

                if not swarm_result:
                    cprint(f"❌ No response from swarm for {token}", "red")
                    return None

                action, confidence, reasoning = self._calculate_swarm_consensus(
                    swarm_result
                )

                # Store the recommendation only — no trade execution here
                self.recommendations_df = pd.concat(
                    [
                        self.recommendations_df,
                        pd.DataFrame(
                            [
                                {
                                    "token": token,
                                    "action": action,
                                    "confidence": confidence,
                                    "reasoning": reasoning,
                                }
                            ]
                        ),
                    ],
                    ignore_index=True,
                )

                cprint(f"✅ Swarm analysis complete for {token[:8]}!", "green")
                add_console_log(f"✅ Swarm  {token} -> {action} | {confidence}% Sure", "success")

                # Return raw result for dashboard or debugging
                return swarm_result

            # ============================================================
            # SINGLE MODEL MODE
            # ============================================================
            else:
                # -----------------------------
                # Enriched strategy context
                # -----------------------------
                try:
                    # robust token name detection
                    if isinstance(market_data, dict):
                        token_name = market_data.get("symbol") or market_data.get("token") or token
                    else:
                        token_name = token

                    strat_obj = None
                    strategy_context_text = "No strategy intelligence available."
                    strategy_context_json = {}

                    # Attempt to get enriched context from StrategyAgent (cached)
                    try:
                        strat_obj = self._get_cached_strategy_context(token_name)
                    except Exception as e:
                        cprint(f"⚠️ Error fetching strategy context for {token_name}: {e}", "yellow")
                        strat_obj = None

                    if strat_obj:
                        strategy_context_text, strategy_context_json = self._format_strategy_context_text(strat_obj)
                        add_console_log("Strategies loaded", "success")

                    else:
                        # fallback to legacy market_data['strategy_signals'] if present
                        if isinstance(market_data, dict) and "strategy_signals" in market_data:
                            try:
                                strategy_context_text = (
                                    "Strategy Signals Available:\n" +
                                    json.dumps(market_data["strategy_signals"], indent=2)
                                )
                                strategy_context_json = {"legacy_signals": market_data["strategy_signals"]}
                            except Exception:
                                strategy_context_text = "Strategy Signals Available (unserializable)."
                                strategy_context_json = {"legacy_signals": str(market_data.get("strategy_signals"))}
                        else:
                            strategy_context_text = "No strategy intelligence available."
                            strategy_context_json = {}

                    # store last context for debug / dashboard
                    self.last_strategy_context = strategy_context_json

                except Exception as e:
                    cprint(f"⚠️ Failed to prepare strategy context: {e}", "yellow")
                    strategy_context_text = "No strategy intelligence available."

                # Get performance context for motivation
                performance_metrics = self._get_performance_metrics()
                performance_context = (
                    f"Win Rate: {performance_metrics['win_rate']}% | "
                    f"Total PnL: ${performance_metrics['total_pnl']} | "
                    f"Grade: {performance_metrics['grade']} | "
                    f"Recent Trades: {performance_metrics['winning_trades']}/{performance_metrics['total_trades']}"
                )

                response = self.chat_with_ai(
                    TRADING_PROMPT.format(
                        strategy_context=strategy_context_text,
                        position_context=position_context,
                        performance_context=performance_context,
                    ),
                    f"Market Data to Analyze:\n{market_data}",
                )

                if not response:
                    cprint(f"❌ No response from AI for {token}", "red")
                    return None

                lines = response.split("\n")
                action = lines[0].strip() if lines else "NOTHING"

                confidence = 0
                for line in lines:
                    if "confidence" in line.lower():
                        try:
                            # Extract first percentage number (handles "82% confidence" correctly)
                            match = re.search(r'(\d{1,3})\s*%', line)
                            if match:
                                confidence = min(100, max(0, int(match.group(1))))
                            else:
                                # Fallback: first standalone number
                                match = re.search(r'\b(\d{1,3})\b', line)
                                if match:
                                    confidence = min(100, max(0, int(match.group(1))))
                                else:
                                    confidence = 50
                        except Exception:
                            confidence = 50

                reasoning = (
                    "\n".join(lines[1:]) if len(lines) > 1 else "No detailed reasoning provided"
                )

                # Apply confidence threshold for single model
                if action in ["BUY", "SELL"] and confidence < self.min_single_confidence:
                    cprint(
                        f"⚠️ LOW CONFIDENCE: {confidence}% < {self.min_single_confidence}% threshold",
                        "yellow",
                        attrs=["bold"]
                    )
                    cprint(f"   → Downgrading {action} to NOTHING", "yellow")
                    add_console_log(f"{token} -> NOTHING | {confidence}% (low confidence)", "warning")

                    original_action = action
                    action = "NOTHING"
                    reasoning = f"Original: {original_action} ({confidence}%) → Downgraded to NOTHING (below {self.min_single_confidence}% threshold)\n\n{reasoning}"

                self.recommendations_df = pd.concat(
                    [
                        self.recommendations_df,
                        pd.DataFrame(
                            [
                                {
                                    "token": token,
                                    "action": action,
                                    "confidence": confidence,
                                    "reasoning": reasoning,
                                }
                            ]
                        ),
                    ],
                    ignore_index=True,
                )

                add_console_log(f"Analysis Complete for {token[:4]}...", "info")
                add_console_log(f"{token} -> {action} | {confidence}%", "success")

                return response

        except Exception as e:
            print(f"❌ Error in AI analysis: {str(e)}")
            self.recommendations_df = pd.concat(
                [
                    self.recommendations_df,
                    pd.DataFrame(
                        [
                            {
                                "token": token,
                                "action": "NOTHING",
                                "confidence": 0,
                                "reasoning": f"Error during analysis: {str(e)}",
                            }
                        ]
                    ),
                ],
                ignore_index=True,
            )
            return None



    def allocate_portfolio(self, current_allocatable_usd: float):
        """
        Deterministic, verbose, allocation-safe portfolio allocator.
        No silent failures. Every rejection is logged.
        """
        try:
            cprint("\n" + "=" * 70, "cyan")
            cprint("🧠 AI SMART PORTFOLIO ALLOCATION", "white", "on_blue", attrs=["bold"])
            cprint("=" * 70, "cyan")

            # ==========================================================
            # STEP 1 — COLLECT OPEN POSITIONS
            # ==========================================================
            open_positions = {}
            for sym in self.symbols:
                try:
                    pos_data = n.get_position(sym, self.account) if EXCHANGE != "HYPERLIQUID" \
                        else n.get_position(sym, self.account)

                    # Validate pos_data before unpacking
                    if pos_data is None or not isinstance(pos_data, tuple) or len(pos_data) < 7:
                        continue

                    _, im_in_pos, pos_size, _, entry_px, pnl_pct, is_long = pos_data
                    if im_in_pos and pos_size != 0:
                        notional = abs(float(pos_size) * float(entry_px))
                        margin = notional / LEVERAGE
                        open_positions[sym] = {
                            "direction": "LONG" if is_long else "SHORT",
                            "margin_usd": round(margin, 2),
                            "pnl_percent": round(float(pnl_pct), 2),
                        }
                except Exception:
                    continue

            cprint(f"📊 Open positions: {open_positions}", "cyan")

            # ==========================================================
            # STEP 2 — FILTER STRATEGY SIGNALS (using portfolio_allocator helper)
            # ==========================================================
            recommendations = [
                {
                    "token": row.get("token", row.get("symbol", "")),
                    "action": row.get("action", "NOTHING"),
                    "confidence": row.get("confidence", 50)
                }
                for _, row in self.recommendations_df.iterrows()
            ]
            signals, removed = filter_strategy_signals(
                recommendations, self.symbols, LONG_ONLY, open_positions
            )

            if removed:
                cprint(f"\n❌ Removed {len(removed)} signals:", "yellow")
                for r in removed:
                    cprint(f"   - {r}", "white")
                add_console_log(f"Removed {len(removed)} strategy signals", "warning")

            if not signals:
                add_console_log("No actionable signals after filtering", "info")
                cprint("📭 No signals left to allocate.", "yellow")
                return []

            # ==========================================================
            # STEP 3 — ACCOUNT EQUITY (using portfolio_allocator helper)
            # ==========================================================
            account_balance = get_account_balance(self.account)
            total_equity = (
                n.get_account_value(self.account.address)
                if EXCHANGE == "HYPERLIQUID"
                else account_balance
            )

            if total_equity <= 0:
                cprint("❌ Total equity is zero", "red")
                add_console_log("Allocation aborted: zero equity", "error")
                return []

            # Calculate allocatable USD after cash buffer using helper
            required_buffer_usd, allocatable_usd = calculate_allocatable_balance(
                account_balance, total_equity, CASH_PERCENTAGE
            )

            cprint(f"💰 Balance: ${account_balance:.2f}", "cyan")
            cprint(f"💎 Total equity: ${total_equity:.2f}", "cyan")
            cprint(f"🛡️ Required cash buffer: ${required_buffer_usd:.2f} ({CASH_PERCENTAGE}%)", "yellow")
            cprint(f"🎯 Allocatable for trading: ${allocatable_usd:.2f}", "green")

            # ==========================================================
            # STEP 4 — BUILD AI PROMPT
            # ==========================================================
            prompt = SMART_ALLOCATION_PROMPT.format(
                portfolio_state=open_positions,
                signals=signals,
                total_equity=total_equity,
                available_balance=account_balance,
                required_buffer_usd=required_buffer_usd,
                allocatable_usd=allocatable_usd,
                leverage=LEVERAGE,
                max_position_pct=MAX_POSITION_PERCENTAGE,
                cash_buffer_pct=CASH_PERCENTAGE,
                min_order=12.0,
                cycle_minutes=SLEEP_BETWEEN_RUNS_MINUTES,
            )

            cprint("\n🤖 Requesting AI allocation...", "magenta")
            add_console_log("Requesting AI allocation", "info")

            ai_response = self.chat_with_ai(
                "You are a portfolio allocator. Return ONLY valid JSON.",
                prompt
            )

            if not ai_response:
                add_console_log("AI returned no response, using fallback", "warning")
                return self._fallback_equal_allocation(signals, allocatable_usd, open_positions)

            # ==========================================================
            # STEP 5 — PARSE AI RESPONSE
            # ==========================================================
            try:
                allocation = extract_json_from_text(ai_response)
                actions = allocation.get("actions", [])
            except Exception as e:
                add_console_log(f"AI JSON parse failed: {e}", "error")
                return self._fallback_equal_allocation(signals, allocatable_usd, open_positions)

            if not actions:
                add_console_log("AI returned zero actions", "warning")
                return self._fallback_equal_allocation(signals, allocatable_usd, open_positions)

            # ==========================================================
            # STEP 6 — VALIDATE ACTIONS (WITH SYMBOL NORMALIZATION)
            # ==========================================================
            valid_actions = []
            rejected = {}

            def reject(reason):
                rejected[reason] = rejected.get(reason, 0) + 1

            for a in actions:
                if not isinstance(a, dict):
                    reject("not a dict")
                    continue

                raw_sym = a.get("symbol", "")
                act = a.get("action")

                # Normalize symbol (handles AI hallucinations like "BITCOIN" → "BTC")
                sym = self.normalize_symbol(raw_sym)
                a["symbol"] = sym  # Update action with normalized symbol

                if sym not in self.symbols:
                    reject(f"{raw_sym}: unknown symbol" + (f" (normalized: {sym})" if sym != raw_sym else ""))
                    continue

                if act not in ["OPEN_LONG", "OPEN_SHORT", "INCREASE", "REDUCE", "CLOSE"]:
                    reject(f"{sym}: invalid action {act}")
                    continue

                # Size validation
                if act in ["OPEN_LONG", "OPEN_SHORT", "INCREASE"]:
                    if a.get("margin_usd", 0) <= 0:
                        reject(f"{sym}: margin_usd <= 0")
                        continue

                if act == "REDUCE":
                    if a.get("reduce_by_usd", 0) <= 0:
                        reject(f"{sym}: reduce_by_usd <= 0")
                        continue

                # Risk validation
                if RISK_MANAGER_AVAILABLE and self.risk_manager:
                    try:
                        conf = a.get("confidence", 50) / 100.0
                        # Get actual entry price instead of hardcoded value
                        try:
                            entry_price = n.get_current_price(sym)
                        except Exception:
                            entry_price = 100.0  # Fallback if price fetch fails

                        verdict = self.risk_manager.validate_trade_decision(
                            symbol=sym,
                            action=act,
                            confidence=conf,
                            entry_price=entry_price,
                            account_balance=total_equity,
                        )
                        if not verdict["valid"]:
                            # Get detailed rejection reason
                            reason = verdict.get("reason", verdict.get("message", "unknown"))
                            cprint(f"   ⚠️ Risk rejected {sym}: {reason}", "yellow")
                            reject(f"{sym}: risk rejected ({reason})")
                            continue
                    except Exception as e:
                        reject(f"{sym}: risk error {e}")
                        continue

                valid_actions.append(a)

            # ==========================================================
            # STEP 7 — LOG REJECTIONS & HANDLE PARTIAL FAILURES
            # ==========================================================
            total_rejected = sum(rejected.values())
            valid_count = len(valid_actions)

            if rejected:
                # Better logging: show valid vs rejected counts
                cprint(f"\n⚠️ AI Actions: {valid_count} valid, {total_rejected} rejected", "yellow")
                for reason, count in rejected.items():
                    cprint(f"   • {reason} (×{count})", "white")

                if valid_count > 0:
                    # Some actions are valid - proceed with those
                    add_console_log(f"AI allocation: {valid_count} valid, {total_rejected} rejected", "info")
                else:
                    # All rejected - will try partial recovery below
                    add_console_log(f"AI allocation: {total_rejected} action(s) rejected", "warning")

            if not valid_actions:
                # Partial Recovery: Check if we have valid signals that AI didn't properly handle
                ai_symbols = {a.get("symbol") for a in actions if isinstance(a, dict)}
                uncovered_signals = [s for s in signals if s.get("symbol") not in ai_symbols]

                if uncovered_signals:
                    # AI returned actions for wrong symbols, but we have other valid signals
                    cprint(f"\n🔄 Partial recovery: {len(uncovered_signals)} signals not covered by AI", "yellow")
                    add_console_log(
                        f"Using {len(uncovered_signals)} uncovered signals for fallback allocation",
                        "warning"
                    )
                    return self._fallback_equal_allocation(uncovered_signals, allocatable_usd, open_positions)
                else:
                    # AI covered our signals but all were rejected - use all signals for fallback
                    cprint(f"\n❌ All {total_rejected} AI action(s) rejected", "red")
                    add_console_log(
                        f"All {total_rejected} AI action(s) rejected — using fallback allocation",
                        "error"
                    )
                    return self._fallback_equal_allocation(signals, total_equity, open_positions)

            # ==========================================================
            # STEP 8 — FINAL PLAN
            # ==========================================================
            cprint("\n" + "=" * 70, "green")
            cprint("🎯 FINAL ALLOCATION PLAN", "white", "on_green", attrs=["bold"])
            cprint("=" * 70, "green")

            for a in valid_actions:
                cprint(f"   {a}", "white")

            # Log each allocation action with AI reasoning to frontend
            add_console_log(f"🤖 AI Allocation Response:", "success")
            for a in valid_actions:
                action_type = a.get("action", "UNKNOWN")
                symbol = a.get("symbol", "?")
                margin = a.get("margin_usd", 0)
                confidence = a.get("confidence", 0)
                reason = a.get("reason", "")[:60]  # Truncate for display

                if action_type in ["OPEN_LONG", "INCREASE"] and a.get("margin_usd"):
                    add_console_log(f"   📈 {action_type} {symbol}: ${margin:.2f} margin ({confidence}%)", "info")
                elif action_type == "OPEN_SHORT":
                    add_console_log(f"   📉 {action_type} {symbol}: ${margin:.2f} margin ({confidence}%)", "info")
                elif action_type == "CLOSE":
                    add_console_log(f"   🔴 CLOSE {symbol}", "info")
                elif action_type == "REDUCE":
                    reduce_by = a.get("reduce_by_usd", 0)
                    add_console_log(f"   🟡 REDUCE {symbol} by ${reduce_by:.2f}", "info")

                # Log the reasoning (without timestamp for cleaner look)
                if reason:
                    add_console_log(f"      → {reason}...", "info")

            add_console_log(f"✅ Allocation validated: {len(valid_actions)} actions approved", "success")
            return valid_actions

        except Exception as e:
            add_console_log(f"allocate_portfolio crashed: {e}", "error")
            import traceback
            traceback.print_exc()
            return []


    def plan_rebalance_actions(self, open_positions, target_allocations, total_equity):
        """
        Generate CLOSE / REDUCE actions to free margin so OPENs can succeed.

        - open_positions: dict from fetch_all_open_positions/allocate_portfolio (symbol -> margin_usd, direction)
        - target_allocations: list of actions returned by allocate_portfolio()
        - total_equity: USD equity value (same as used by allocator)

        Returns: list of actions (CLOSE/REDUCE) formatted for execute_allocations()
        """
        actions = []
        # Build a map: symbol -> target_margin (for OPEN/INCREASE actions)
        target_map = {}
        for a in target_allocations:
            if not isinstance(a, dict):
                continue
            sym = a.get("symbol")
            if not sym:
                continue
            if a.get("action") in ("OPEN_LONG", "OPEN_SHORT", "INCREASE"):
                target_map[sym] = float(a.get("margin_usd", 0))

        MIN_NOTIONAL = 12.0
        TOLERANCE = 1.05  # 5% tolerance before reducing

        for sym, pos in open_positions.items():
            current_margin = float(pos.get("margin_usd", 0))
            target_margin = float(target_map.get(sym, 0))

            # If not in target_map -> close entire position
            if sym not in target_map:
                # Only plan a CLOSE if there is a meaningful margin to free
                if current_margin >= MIN_NOTIONAL / self.leverage:
                    actions.append({
                        "symbol": sym,
                        "action": "CLOSE",
                        "reason": "Rebalance: not in target allocations"
                    })
                continue

            # If current margin significantly exceeds target -> reduce
            if current_margin > (target_margin * TOLERANCE):
                reduce_by = round(current_margin - target_margin, 2)
                # Only plan a REDUCE if reduction is meaningful
                min_reduce_margin = MIN_NOTIONAL / self.leverage
                if reduce_by >= min_reduce_margin:
                    actions.append({
                        "symbol": sym,
                        "action": "REDUCE",
                        "reduce_by_usd": reduce_by,
                        "reason": f"Rebalance: reduce from {current_margin} to {target_margin}"
                    })
                else:
                    # If target is zero but current small margin >= min notional, prefer CLOSE
                    if target_margin == 0 and current_margin >= min_reduce_margin:
                        actions.append({
                            "symbol": sym,
                            "action": "CLOSE",
                            "reason": "Rebalance: close small position to free margin"
                        })

        # Close actions first, then reduces
        actions_sorted = sorted(actions, key=lambda x: 0 if x["action"] == "CLOSE" else 1)
        if actions_sorted:
            add_console_log(f"Planned {len(actions_sorted)} rebalance actions", "info")
        return actions_sorted

    def normalize_symbol(self, raw_symbol: str) -> str:
        """Normalize symbol. Wrapper for extracted function in portfolio_allocator module."""
        return _normalize_symbol(raw_symbol, self.symbols)

    def _fallback_equal_allocation(self, signals, available_balance, open_positions):
        """
        Fallback to equal distribution when AI allocation fails.
        Returns list of action dicts in the same format as AI.
        """
        cprint("\n📊 Using fallback equal distribution...", "yellow")

        # Minimum order notional (matching exchange requirements)
        min_order_notional = 12.0

        actionable_signals = [s for s in signals if s.get("action", "") in ["BUY", "SELL"]]
        if not actionable_signals:
            return []

        # Filter out signals where we already have aligned position
        # Use grace period and min-margin logic to handle ghost positions
        new_signals = []
        now_ts = time.time()

        actions = []
        for sig in actionable_signals:
            sym = sig.get("symbol", "")
            sig_action = sig.get("action", "NOTHING")
            action_type = "OPEN_LONG" if sig_action == "BUY" else "OPEN_SHORT"

            if sym in open_positions:
                pos = open_positions[sym]
                # If signal aligns with existing position, create an INCREASE action
                if (sig_action == "BUY" and pos.get("direction") == "LONG") or \
                   (sig_action == "SELL" and pos.get("direction") == "SHORT"):
                    action_type = "INCREASE"

            sig_confidence = sig.get("confidence", 50)
            actions.append({
                "symbol": sig.get("symbol", ""),
                "action": action_type,
                "margin_usd": 0,  # Placeholder, will be calculated next
                "confidence": sig_confidence,  # Include for sorting
                "reason": f"Fallback: {sig.get('action', 'UNKNOWN')} signal ({sig_confidence}% confidence)"
            })

        if not actions:
            cprint("   No new positions to open after filtering.", "cyan")
            return []

        # Calculate margin per position with proper cash buffer enforcement
        usable_margin = available_balance * (MAX_POSITION_PERCENTAGE / 100)
        cash_buffer = available_balance * (CASH_PERCENTAGE / 100)
        allocatable_margin = max(0, usable_margin - cash_buffer)

        if not actions:
            cprint("   No signals after filtering.", "cyan")
            return []

        margin_per_position = allocatable_margin / len(actions)
        min_margin = min_order_notional / LEVERAGE

        if margin_per_position < min_margin:
            # Take only highest confidence signals
            actions.sort(key=lambda x: x.get("confidence", 0), reverse=True)
            max_positions = int(allocatable_margin / min_margin)
            actions = actions[:max(1, max_positions)]

            if not actions:
                cprint("   Insufficient margin for any positions.", "yellow")
                return []

            margin_per_position = allocatable_margin / len(actions)

        # Update margin_usd for each action
        for action in actions:
            action["margin_usd"] = round(margin_per_position, 2)


        return actions

    def execute_allocations(self, actions_list):
        """
        Execute the AI-generated allocation plan.

        Args:
            actions_list: List of action dicts from allocate_portfolio()
                Each action has: symbol, action, margin_usd/reduce_by_usd, reason

        Action types:
            - OPEN_LONG: Open new long position
            - OPEN_SHORT: Open new short position
            - INCREASE: Add to existing position
            - REDUCE: Reduce existing position
            - CLOSE: Close position entirely
        """
        if not actions_list:
            cprint("📊 No actions to execute.", "cyan")
            return

        try:
            cprint("\n" + "=" * 60, "yellow")
            cprint("🚀 EXECUTING AI ALLOCATION PLAN", "white", "on_yellow", attrs=["bold"])
            cprint("=" * 60, "yellow")
            add_console_log(f"Executing {len(actions_list)} allocation actions", "info")

            # Sort actions: CLOSE first, then REDUCE, then OPEN/INCREASE
            # This ensures we free up capital before opening new positions
            action_priority = {"CLOSE": 0, "REDUCE": 1, "OPEN_LONG": 2, "OPEN_SHORT": 2, "INCREASE": 3}
            sorted_actions = sorted(actions_list, key=lambda x: action_priority.get(x.get("action", ""), 5))

            executed_count = 0
            failed_count = 0

            for action in sorted_actions:
                symbol = action.get("symbol")
                action_type = action.get("action")
                reason = action.get("reason", "")

                if not symbol or not action_type:
                    continue

                if symbol not in self.symbols:
                    cprint(f"⚠️ Skipping {symbol} - not in configured symbols", "yellow")
                    continue

                cprint(f"\n{'─' * 50}", "cyan")
                cprint(f"🎯 {symbol}: {action_type}", "cyan", attrs=["bold"])
                if reason:
                    cprint(f"   📝 {reason}", "white")

                try:
                    # Get current position state
                    if EXCHANGE == "HYPERLIQUID":
                        pos_data = n.get_position(symbol, self.account)
                    else:
                        pos_data = n.get_position(symbol)

                    # Validate pos_data is valid tuple before unpacking
                    if pos_data is None or not isinstance(pos_data, tuple) or len(pos_data) < 7:
                        cprint(f"⚠️ Invalid position data for {symbol}, skipping", "yellow")
                        continue

                    _, im_in_pos, pos_size, _, entry_px, pnl_pct, is_long = pos_data
                    current_notional = abs(float(pos_size) * float(entry_px)) if im_in_pos else 0
                    current_dir = "LONG" if is_long else "SHORT"

                    # -----------------------
                    # LIVE EXECUTION GUARDS
                    # -----------------------
                    # Compute live balances / available free USDC
                    try:
                        if EXCHANGE == "HYPERLIQUID":
                            live_total_equity = n.get_account_value(
                                self.account.address if hasattr(self.account, "address") else self.account
                            )
                            live_available_balance = get_account_balance(self.account)
                        else:
                            live_total_equity = get_account_balance(self.account)
                            live_available_balance = live_total_equity
                    except Exception:
                        # fallback
                        live_available_balance = get_account_balance(self.account)
                        live_total_equity = live_available_balance

                    # For OPEN / INCREASE actions enforce min notional only
                    if action_type in ("OPEN_LONG", "OPEN_SHORT", "INCREASE"):
                        is_valid, margin_usd, notional, error_reason = validate_open_action_params(
                            action, LEVERAGE, DEFAULT_MIN_NOTIONAL
                        )
                        if not is_valid:
                            cprint(f"   ⚠️ Skipping {symbol}: {error_reason}", "yellow")
                            add_console_log(f"Skipped {symbol}: {error_reason}", "warning")
                            continue

                    # ============================================================
                    # CLOSE: Close entire position
                    # ============================================================
                    if action_type == "CLOSE":
                        can_close, close_error = validate_close_action_params(im_in_pos, pos_size)
                        if not can_close:
                            cprint(f"   ℹ️ {close_error}", "cyan")
                            continue

                        cprint(f"   📊 Closing {current_dir} position (${current_notional:.2f} notional)", "yellow")

                        close_success = False
                        if EXCHANGE == "HYPERLIQUID":
                            close_success = n.close_complete_position(symbol, self.account)
                        else:
                            n.chunk_kill(symbol, max_usd_order_size, slippage)
                            close_success = True  # chunk_kill doesn't return status

                        if close_success and POSITION_TRACKER_AVAILABLE:
                            remove_position(symbol)

                        log_close_trade_result(close_success, symbol, current_dir, current_notional)
                        if close_success:
                            executed_count += 1

                    # ============================================================
                    # REDUCE: Reduce position size
                    # ============================================================
                    elif action_type == "REDUCE":
                        can_reduce, reduce_amount, reduce_error = validate_reduce_action_params(
                            action, im_in_pos, pos_size
                        )
                        if not can_reduce:
                            cprint(f"   ℹ️ {reduce_error}", "cyan" if "no position" in reduce_error else "yellow")
                            continue

                        cprint(f"   📊 Current: ${current_notional:.2f} notional", "white")
                        cprint(f"   ➖ Reducing by: ${reduce_amount:.2f} notional", "yellow")

                        reduce_success = False
                        if hasattr(n, 'partial_close'):
                            n.partial_close(symbol, reduce_amount, account=self.account)
                            reduce_success = True

                        log_reduce_trade_result(reduce_success, symbol, reduce_amount)
                        if reduce_success:
                            executed_count += 1

                    # ============================================================
                    # OPEN_LONG / INCREASE (for LONG)
                    # ============================================================
                    elif action_type in ["OPEN_LONG", "INCREASE"] and (action_type == "OPEN_LONG" or (im_in_pos and is_long)):
                        # margin_usd and notional already validated by validate_open_action_params above
                        is_netting = has_opposite_position("OPEN_LONG", im_in_pos, is_long)

                        # Handle opposite position (SHORT exists, opening LONG)
                        if is_netting:
                            cprint(f"   🔄 Opposite position detected - using position reversal", "cyan")

                            # For HyperLiquid, we can directly open opposite position which will net
                            if EXCHANGE == "HYPERLIQUID":
                                cprint(f"   📈 Opening LONG to net against existing SHORT", "cyan")
                                entry_result = n.ai_entry(symbol, notional, leverage=LEVERAGE, account=self.account)
                                result, actual_lev = unpack_entry_result(entry_result, LEVERAGE)
                                actual_notional = margin_usd * actual_lev

                                log_open_trade_result(bool(result), symbol, "LONG", actual_notional, actual_lev, is_netting=True)

                                if result:
                                    if POSITION_TRACKER_AVAILABLE:
                                        try:
                                            record_position_entry(symbol=symbol, entry_price=0, size=actual_notional, is_long=True)
                                        except Exception as e:
                                            cprint(f"   ⚠️ Position tracker error: {e}", "yellow")
                                    try:
                                        log_position_open(symbol, "LONG", actual_notional)
                                    except Exception:
                                        pass
                                    executed_count += 1
                                else:
                                    failed_count += 1
                                continue
                            else:
                                # For other exchanges, fall back to closing first
                                cprint(f"   ⚠️ Closing SHORT before opening LONG...", "yellow")
                                n.chunk_kill(symbol, max_usd_order_size, slippage)
                                time.sleep(1)

                        cprint(f"   📈 Opening LONG: ${notional:.2f} notional (${margin_usd:.2f} margin)", "green")

                        # Execute trade
                        result = None
                        actual_lev = LEVERAGE
                        if EXCHANGE == "HYPERLIQUID":
                            entry_result = n.ai_entry(symbol, notional, leverage=LEVERAGE, account=self.account)
                            result, actual_lev = unpack_entry_result(entry_result, LEVERAGE)
                        elif EXCHANGE == "ASTER":
                            result = n.ai_entry(symbol, notional, leverage=LEVERAGE)
                        else:
                            result = n.ai_entry(symbol, notional)

                        actual_notional = margin_usd * actual_lev
                        log_open_trade_result(bool(result), symbol, "LONG", actual_notional, actual_lev)

                        if result:
                            if POSITION_TRACKER_AVAILABLE:
                                try:
                                    record_position_entry(symbol=symbol, entry_price=0, size=actual_notional, is_long=True)
                                except Exception as e:
                                    cprint(f"   ⚠️ Position tracker error: {e}", "yellow")
                            try:
                                log_position_open(symbol, "LONG", actual_notional)
                            except Exception:
                                pass
                            executed_count += 1
                        else:
                            failed_count += 1

                    # ============================================================
                    # OPEN_SHORT / INCREASE (for SHORT)
                    # ============================================================
                    elif action_type in ["OPEN_SHORT"] or (action_type == "INCREASE" and im_in_pos and not is_long):
                        # margin_usd and notional already validated by validate_open_action_params above
                        is_netting = has_opposite_position("OPEN_SHORT", im_in_pos, is_long)

                        # Handle opposite position (LONG exists, opening SHORT)
                        if is_netting:
                            cprint(f"   🔄 Opposite position detected - allocating in opposite direction", "cyan")

                            # For HyperLiquid, we can directly open opposite position which will net
                            if EXCHANGE == "HYPERLIQUID":
                                cprint(f"   📉 Opening SHORT to net against existing LONG", "cyan")
                                short_result = n.open_short(symbol, notional, leverage=LEVERAGE, account=self.account)
                                result, actual_lev = unpack_entry_result(short_result, LEVERAGE)
                                actual_notional = margin_usd * actual_lev

                                log_open_trade_result(bool(result), symbol, "SHORT", actual_notional, actual_lev, is_netting=True)

                                if result:
                                    if POSITION_TRACKER_AVAILABLE:
                                        try:
                                            record_position_entry(symbol=symbol, entry_price=0, size=actual_notional, is_long=False)
                                        except Exception as e:
                                            cprint(f"   ⚠️ Position tracker error: {e}", "yellow")
                                    try:
                                        log_position_open(symbol, "SHORT", actual_notional)
                                    except Exception:
                                        pass
                                    executed_count += 1
                                else:
                                    failed_count += 1
                                continue
                            else:
                                # For other exchanges, fall back to closing first
                                cprint(f"   ⚠️ Closing LONG before opening SHORT...", "yellow")
                                n.chunk_kill(symbol, max_usd_order_size, slippage)
                                time.sleep(1)

                        if EXCHANGE == "SOLANA":
                            cprint(f"   ⚠️ SHORT not supported on SOLANA", "yellow")
                            continue

                        cprint(f"   📉 Opening SHORT: ${notional:.2f} notional (${margin_usd:.2f} margin)", "red")

                        # Execute trade
                        result = None
                        actual_lev = LEVERAGE
                        if EXCHANGE == "HYPERLIQUID":
                            short_result = n.open_short(symbol, notional, leverage=LEVERAGE, account=self.account)
                            result, actual_lev = unpack_entry_result(short_result, LEVERAGE)
                        elif EXCHANGE == "ASTER":
                            if hasattr(n, 'open_short'):
                                result = n.open_short(symbol, notional, leverage=LEVERAGE)
                            else:
                                cprint(f"   ⚠️ open_short not available for ASTER", "yellow")
                                failed_count += 1
                                continue

                        actual_notional = margin_usd * actual_lev
                        log_open_trade_result(bool(result), symbol, "SHORT", actual_notional, actual_lev)

                        if result:
                            if POSITION_TRACKER_AVAILABLE:
                                try:
                                    record_position_entry(symbol=symbol, entry_price=0, size=actual_notional, is_long=False)
                                except Exception as e:
                                    cprint(f"   ⚠️ Position tracker error: {e}", "yellow")
                            try:
                                log_position_open(symbol, "SHORT", actual_notional)
                            except Exception:
                                pass
                            executed_count += 1
                        else:
                            failed_count += 1

                    else:
                        cprint(f"   ⚠️ Unknown action type: {action_type}", "yellow")

                except Exception as e:
                    cprint(f"   ❌ Error: {str(e)}", "red")
                    add_console_log(f"❌ {symbol} {action_type} failed: {e}", "error")
                    failed_count += 1
                    import traceback
                    traceback.print_exc()

                time.sleep(2)  # Rate limiting between trades

            # Summary using helper functions
            summary = build_execution_summary(executed_count, failed_count)
            summary_text = format_execution_summary(summary)
            cprint(f"\n{'=' * 60}", "green")
            cprint(f"✅ {summary_text}", "green", attrs=["bold"])
            cprint(f"{'=' * 60}\n", "green")
            add_console_log(summary_text, "success")

        except Exception as e:
            cprint(f"❌ Error in execute_allocations: {e}", "red")
            import traceback
            traceback.print_exc()

    def handle_exits(self):
        """
        PHASE 1: CLOSE positions when signal is OPPOSITE to position direction.

        This function ONLY handles EXITS - it does NOT open new positions.
        New positions are opened in execute_allocations() after balance is recalculated.

        Logic:
        - BUY signal + LONG position → KEEP (signal confirms position)
        - BUY signal + SHORT position → CLOSE (signal contradicts position)
        - SELL signal + LONG position → CLOSE (signal contradicts position)
        - SELL signal + SHORT position → KEEP (signal confirms position)
        - NOTHING signal → KEEP any position

        Order of Operations (per dev_tasks.md 3.1):
        1. CLOSE existing positions (this function)
        2. RE-EVALUATE allocation (allocate_portfolio with fresh balance)
        3. OPEN new positions (execute_allocations)
        """
        cprint("\n🔄 PHASE 1: Checking for positions to exit...", "white", "on_blue")
        add_console_log("Evaluating positions...", "info")

        positions_closed = 0
        positions_held = 0

        for _, row in self.recommendations_df.iterrows():
            token = row["token"]
            token_short = token[:8] + "..." if len(token) > 8 else token

            if token in EXCLUDED_TOKENS:
                continue

            action = row["action"]

            # Get position with direction info
            try:
                if EXCHANGE == "HYPERLIQUID":
                    pos_data = n.get_position(token, self.account)
                else:
                    pos_data = n.get_position(token)

                # Validate pos_data before unpacking
                if pos_data is None or not isinstance(pos_data, tuple) or len(pos_data) < 7:
                    cprint(f"⚠️ Invalid position data for {token}, skipping", "yellow")
                    continue

                _, im_in_pos, pos_size, _, entry_px, pnl_perc, is_long = pos_data

                # If position was manually closed, clean up tracker
                if not im_in_pos and POSITION_TRACKER_AVAILABLE:
                    try:
                        remove_position(token)
                    except Exception:
                        pass

            except Exception as e:
                cprint(f"⚠️ Error getting position for {token}: {e}", "yellow")
                # Try to clean up tracker on error
                if POSITION_TRACKER_AVAILABLE:
                    try:
                        remove_position(token)
                    except Exception:
                        pass
                continue

            cprint(f"\n{'=' * 60}", "cyan")
            cprint(f"🎯 Token: {token_short}", "cyan", attrs=["bold"])
            confidence = row.get('confidence', 50)  # Default 50% if missing
            cprint(f"📊 Signal: {action} ({confidence}% confidence)", "yellow", attrs=["bold"])

            if im_in_pos and pos_size != 0:
                # ============= CASE: HAVE POSITION =============
                position_dir = "LONG" if is_long else "SHORT"
                cprint(f"💼 Current Position: {position_dir} | Size: {abs(pos_size):.4f} | PnL: {pnl_perc:.2f}%", "white")
                cprint(f"{'=' * 60}", "cyan")

                # CRITICAL: Check for stop loss FIRST (overrides all other logic)
                if should_trigger_stop_loss(pnl_perc, STOP_LOSS_THRESHOLD):
                    cprint(f"🚨 STOP LOSS TRIGGERED: {pnl_perc:.2f}% <= {STOP_LOSS_THRESHOLD}%", "white", "on_red", attrs=["bold"])
                    cprint(f"⚠️ FORCE CLOSING {position_dir} position (mandatory -2% stop loss)", "white", "on_red")

                    try:
                        close_ok = False
                        if EXCHANGE == "HYPERLIQUID":
                            close_ok = n.close_complete_position(token, self.account)
                        else:
                            n.chunk_kill(token, max_usd_order_size, slippage)
                            close_ok = True

                        if close_ok:
                            # Remove from position tracker
                            if POSITION_TRACKER_AVAILABLE:
                                remove_position(token)

                            cprint("✅ Stop loss position closed successfully!", "white", "on_green")
                            add_console_log(f"STOP LOSS: Closed {token} {position_dir} at {pnl_perc:.2f}%", "warning")
                            positions_closed += 1
                        else:
                            cprint("⚠️ Stop loss close may have failed - will retry next cycle", "white", "on_yellow")
                            add_console_log(f"⚠️ Stop loss close failed for {token}", "warning")

                    except Exception as e:
                        cprint(f"❌ Error closing stop loss position: {str(e)}", "white", "on_red")
                        add_console_log(f"❌ Failed to close stop loss position {token}: {e}", "error")

                    continue  # Skip to next token after stop loss

                # Determine if signal contradicts position direction using helper
                should_close = signal_contradicts_position(action, is_long)

                if action == "NOTHING":
                    # NOTHING = hold current position regardless of direction
                    cprint("⏸️ DO NOTHING signal - HOLDING POSITION", "white", "on_blue")
                    cprint(f"💎 Maintaining {position_dir} position", "cyan")
                    positions_held += 1

                elif should_close:
                    # Signal contradicts position → CLOSE (ONLY CLOSE, NO OPEN LOGIC HERE)
                    if action == "SELL" and is_long:
                        cprint("🚨 SELL signal vs LONG position - CLOSING", "white", "on_red")
                    else:  # BUY signal vs SHORT position
                        cprint("🚨 BUY signal vs SHORT position - CLOSING", "white", "on_red")

                    try:
                        close_ok = False
                        if EXCHANGE == "HYPERLIQUID":
                            close_ok = n.close_complete_position(token, self.account)
                        else:
                            n.chunk_kill(token, max_usd_order_size, slippage)
                            close_ok = True

                        if close_ok:
                            # Record recently-closed timestamp so allocation ignores transient ghost positions
                            try:
                                self.recently_closed[token] = time.time()
                            except Exception:
                                pass

                            # Remove from position tracker
                            if POSITION_TRACKER_AVAILABLE:
                                remove_position(token)

                            cprint("✅ Position closed successfully!", "white", "on_green")
                            add_console_log(f"✅ Closed {token} {position_dir} | Signal: {action} ({confidence}%)", "success")
                            positions_closed += 1
                        else:
                            cprint("⚠️ Position close may have failed - will retry next cycle", "yellow")
                            add_console_log(f"⚠️ Close failed for {token}", "warning")

                    except Exception as e:
                        cprint(f"❌ Error closing position: {str(e)}", "white", "on_red")

                else:
                    # Signal confirms position direction → KEEP
                    if action == "BUY" and is_long:
                        cprint("✅ BUY signal confirms LONG position - KEEPING", "white", "on_green")
                    else:  # SELL signal confirms SHORT position
                        cprint("✅ SELL signal confirms SHORT position - KEEPING", "white", "on_green")

                    cprint(f"💎 Maintaining {position_dir} position", "cyan")
                    positions_held += 1

            else:
                # ============= CASE: NO POSITION =============
                cprint(f"💼 No position", "white")
                cprint(f"{'=' * 60}", "cyan")

                # Do NOT open new positions here - that happens in execute_allocations()
                if action == "SELL":
                    if LONG_ONLY:
                        cprint("⭐ SELL signal - LONG ONLY mode, can't open SHORT", "white", "on_blue")
                    else:
                        cprint("📉 SELL signal - SHORT will be opened in allocation phase", "white", "on_yellow")

                elif action == "NOTHING":
                    cprint("⏸️ DO NOTHING signal - staying flat", "white", "on_blue")

                else:  # BUY
                    cprint("📈 BUY signal - LONG will be opened in allocation phase", "white", "on_green")

        # Summary using helper function
        summary_text = format_exit_phase_summary(positions_closed, positions_held)
        cprint(f"\n{'=' * 60}", "green")
        cprint(f"✅ {summary_text}", "green", attrs=["bold"])
        cprint(f"{'=' * 60}", "green")
        add_console_log(summary_text, "success")

    def show_final_portfolio_report(self):
        """Display final portfolio status - NO LOOPS, just a snapshot"""
        cprint("\n" + "=" * 60, "cyan")
        cprint("📊 FINAL PORTFOLIO REPORT", "white", "on_blue", attrs=["bold"])
        cprint("=" * 60, "cyan")

        # CRITICAL: Use self.symbols (instance variable) NOT global SYMBOLS/MONITORED_TOKENS
        check_tokens = self.symbols
        active_positions = []

        # Print header
        print(f"   {'TOKEN':<10} | {'SIDE':<10} | {'SIZE':<12} | {'ENTRY':<12} | {'PNL %':<10}")
        print("   " + "-" * 65)

        for token in check_tokens:
            try:
                pos_data = n.get_position(token, self.account)

                # Validate pos_data before unpacking
                if pos_data is None or not isinstance(pos_data, tuple) or len(pos_data) < 7:
                    continue

                _, im_in_pos, pos_size, _, entry_px, pnl_perc, is_long = pos_data

                if im_in_pos and pos_size != 0:
                    side_icon = "LONG" if is_long else "SHORT"
                    entry_str = f"${entry_px:.2f}" if entry_px != 0 else "-"
                    pnl_str = f"{pnl_perc:+.2f}%" if pnl_perc != 0 else "-"

                    print(
                        f"   {token:<10} | {side_icon:<10} | {pos_size:<12.4f} | "
                        f"{entry_str:<12} | {pnl_str:<10}"
                    )
                    active_positions.append(token)

            except Exception:
                pass  # Silently skip errors to keep report clean

        if not active_positions:
            cprint("   (No active positions)", "cyan")

        cprint("=" * 60 + "\n", "cyan")

    def should_stop(self):
        """Enhanced stop signal checking - only check external stop signals"""
        if self.stop_check_callback is not None:
            if self.stop_check_callback():
                return True
        
        # DO NOT check TP/SL here - that's handled within the trading cycle logic
        # TP/SL should trigger position closes, not stop the entire trading cycle
        return False

    def _check_immediate_tp_sl_actions(self):
        """Check if any positions need immediate TP/SL execution"""
        try:
            for symbol in self.symbols:
                if symbol in EXCLUDED_TOKENS:
                    continue

                pos_data = n.get_position(symbol, self.account)

                # Validate pos_data before unpacking
                if pos_data is None or not isinstance(pos_data, tuple) or len(pos_data) < 7:
                    continue

                _, im_in_pos, _, _, _, pnl_perc, _ = pos_data

                if im_in_pos and pnl_perc != 0:
                    # Check TP threshold
                    if pnl_perc >= TAKE_PROFIT_THRESHOLD:
                        cprint(f"🚨 TAKE PROFIT needed for {symbol}: {pnl_perc:.2f}%", "red")
                        return True
                    
                    # Check SL threshold  
                    if pnl_perc <= STOP_LOSS_THRESHOLD:
                        cprint(f"🚨 STOP LOSS needed for {symbol}: {pnl_perc:.2f}%", "red")
                        return True
        except Exception as e:
            cprint(f"⚠️ Error checking TP/SL: {e}", "yellow")
        
        return False

    def run(self):
        """Run the trading agent (implements BaseAgent interface)"""
        self.run_trading_cycle()

    def _cleanup_recently_closed(self):
        """Clean up recently_closed entries older than grace period to prevent memory leaks"""
        try:
            now_ts = time.time()
            grace_period = getattr(self, "REENTRY_GRACE_PERIOD", 15)
            
            # Remove entries older than grace period
            old_entries = []
            for symbol, closed_ts in self.recently_closed.items():
                if (now_ts - closed_ts) > grace_period:
                    old_entries.append(symbol)
            
            for symbol in old_entries:
                del self.recently_closed[symbol]
                
            if old_entries:
                cprint(f"🧹 Cleaned up {len(old_entries)} old recently_closed entries", "cyan")
                
        except Exception as e:
            cprint(f"⚠️ Error cleaning recently_closed: {e}", "yellow")

    def run_trading_cycle(self, strategy_signals=None):
        """Enhanced trading cycle with position management and intelligence integration"""
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cprint(f"\n{'=' * 80}", "cyan")
            cprint(f"🔄 TRADING CYCLE START: {current_time}", "white", "on_green", attrs=["bold"])
            cprint(f"{'=' * 80}", "cyan")

            # ══════════════════════════════════════════════════════════════════
            # PHASE 1: INITIALIZATION
            # ══════════════════════════════════════════════════════════════════
            mode_name = "SWARM" if self.use_swarm_mode else "SINGLE"
            add_console_log(f"══════ TRADING CYCLE STARTED ══════", "info")
            add_console_log(f"Mode: {mode_name} | Exchange: {EXCHANGE}", "info")
            add_console_log(f"Tokens: {', '.join(self.symbols[:5])}{'...' if len(self.symbols) > 5 else ''} ({len(self.symbols)} total)", "info")
            add_console_log(f"Settings: Leverage {LEVERAGE}x | Cash Buffer {CASH_PERCENTAGE}%", "info")

            # Clean up old recently_closed entries
            self._cleanup_recently_closed()

            # CRITICAL FIX: Reset recommendations_df at the start of each cycle
            self.recommendations_df = pd.DataFrame(
                columns=["token", "action", "confidence", "reasoning"]
            )
            cprint("📋 Recommendations cleared for fresh cycle", "cyan")

            # Check for stop signal
            if self.should_stop():
                add_console_log("⏹️ Stop signal received - aborting cycle", "warning")
                return

            # ══════════════════════════════════════════════════════════════════
            # PHASE 1.5: VOLUME INTELLIGENCE (if available)
            # ══════════════════════════════════════════════════════════════════
            if INTELLIGENCE_AVAILABLE:
                volume_summary = get_volume_summary()
                if volume_summary and "No volume" not in volume_summary:
                    cprint("\n📊 VOLUME INTELLIGENCE:", "white", "on_blue")
                    cprint(volume_summary, "cyan")
                    add_console_log("📊 Volume intelligence loaded", "info")

            # ══════════════════════════════════════════════════════════════════
            # PHASE 2: DATA COLLECTION
            # ══════════════════════════════════════════════════════════════════
            add_console_log("────────────────────────────────────", "info")
            add_console_log("📡 PHASE 2: DATA COLLECTION", "info")

            # Fetch open positions
            add_console_log(f"📡 API: Fetching positions from {EXCHANGE}...", "info")
            open_positions = self.fetch_all_open_positions()
            if open_positions:
                # open_positions is {symbol: [list of position dicts]}
                pos_items = []
                for sym, positions_list in list(open_positions.items())[:3]:
                    if positions_list and len(positions_list) > 0:
                        side = positions_list[0].get("side", "UNK")
                        pos_items.append(f"{sym} ({side})")
                pos_summary = ", ".join(pos_items)
                if len(open_positions) > 3:
                    pos_summary += f"... (+{len(open_positions) - 3} more)"
                add_console_log(f"✅ Found {len(open_positions)} positions: {pos_summary}", "success")
            else:
                add_console_log(f"✅ No open positions found", "info")

            if self.should_stop():
                add_console_log("⏹️ Stop signal received - aborting cycle", "warning")
                return

            # Collect market data
            tokens_to_trade = self.symbols
            add_console_log(f"📡 API: Fetching OHLCV data for {len(tokens_to_trade)} tokens...", "info")
            cprint("📊 Collecting market data for analysis...", "white", "on_blue")

            market_data = collect_all_tokens(
                tokens=tokens_to_trade,
                days_back=self.days_back,
                timeframe=self.timeframe,
                exchange=EXCHANGE,
            )
            add_console_log(f"✅ Market data received ({self.timeframe} timeframe, {self.days_back} days)", "success")

            if self.should_stop():
                add_console_log("⏹️ Stop signal received - aborting cycle", "warning")
                return

            # ══════════════════════════════════════════════════════════════════
            # PHASE 3: POSITION ANALYSIS (Existing Positions)
            # ══════════════════════════════════════════════════════════════════
            close_decisions = {}
            if open_positions:
                add_console_log("────────────────────────────────────", "info")
                add_console_log(f"🔍 PHASE 3: Analyzing {len(open_positions)} open positions...", "info")
                close_decisions = self.analyze_open_positions_with_ai(open_positions, market_data)
                if self.should_stop():
                    add_console_log("⏹️ Stop signal received - skipping position closes", "warning")
                    return
                self.execute_position_closes(close_decisions)

            if self.should_stop():
                add_console_log("⏹️ Stop signal received - aborting cycle", "warning")
                return

            # PHASE 3.5: REFETCH AFTER CLOSES
            time.sleep(2)
            open_positions = self.fetch_all_open_positions()
            cprint("📊 Refreshing market data after position updates...", "white", "on_blue")
            market_data = collect_all_tokens(
                tokens=tokens_to_trade,
                days_back=self.days_back,
                timeframe=self.timeframe,
                exchange=EXCHANGE,
            )

            if self.should_stop():
                add_console_log("ℹ️ Stop signal received - aborting cycle", "warning")
                return

            # ══════════════════════════════════════════════════════════════════
            # PHASE 4: NEW ENTRY ANALYSIS (All Tokens)
            # ══════════════════════════════════════════════════════════════════
            add_console_log("────────────────────────────────────", "info")
            add_console_log(f"🔍 PHASE 4: Analyzing {len(market_data)} tokens for entries...", "info")
            cprint("\n📈 Analyzing tokens for new entry opportunities...", "white", "on_blue")

            for token, data in market_data.items():
                if self.should_stop():
                    add_console_log(f"⏹️ Stop signal received - stopping at {token}", "warning")
                    return

                # Get current price for context
                try:
                    current_price = n.get_current_price(token)
                    price_str = f"@ ${current_price:,.2f}" if current_price > 1 else f"@ ${current_price:.6f}"
                except Exception as e:
                    # Price fetch failed - log but continue (non-critical)
                    price_str = ""

                cprint(f"\n📊 Analyzing {token}...", "white", "on_green")
                add_console_log(f"📊 Analyzing {token} {price_str}...", "info")

                if strategy_signals and token in strategy_signals:
                    data["strategy_signals"] = strategy_signals[token]

                analysis = self.analyze_market_data(token, data)
                if analysis:
                    print(f"\n📈 Analysis for {token}:")
                    print(analysis)
                    print("\n" + "=" * 50 + "\n")

            if self.should_stop():
                add_console_log("ℹ️ Stop signal received - aborting cycle", "warning")
                return

            # STEP 6: SHOW RECOMMENDATIONS
            cprint("\n📊 AI TRADING RECOMMENDATIONS:", "white", "on_blue")
            summary_df = self.recommendations_df[["token", "action", "confidence"]].copy()
            print(summary_df.to_string(index=False))

            # Log signals summary to frontend
            buy_count = len(self.recommendations_df[self.recommendations_df["action"] == "BUY"])
            sell_count = len(self.recommendations_df[self.recommendations_df["action"] == "SELL"])
            hold_count = len(self.recommendations_df[self.recommendations_df["action"] == "NOTHING"])
            add_console_log("────────────────────────────────────", "info")
            add_console_log(f"📋 SIGNAL SUMMARY: {buy_count} BUY, {sell_count} SELL, {hold_count} HOLD", "info")

            if self.should_stop():
                add_console_log("ℹ️ Stop signal received - skipping trade execution", "warning")
                return

            # ══════════════════════════════════════════════════════════════════
            # PHASE 5: AI PORTFOLIO ALLOCATION
            # ══════════════════════════════════════════════════════════════════
            try:
                mode_name = "SWARM" if self.use_swarm_mode else "SINGLE"
                cprint(f"\n{'=' * 80}", "yellow")
                cprint(f"🚀 {mode_name} MODE — AI-Driven Allocation Pipeline", "white", "on_yellow", attrs=["bold"])
                cprint(f"{'=' * 80}", "yellow")

                add_console_log("────────────────────────────────────", "info")
                add_console_log(f"💰 PHASE 5: AI PORTFOLIO ALLOCATION", "info")

                # Calculate account status for allocation
                try:
                    account_balance = get_account_balance(self.account)
                    total_equity = n.get_account_value(self.account.address) if EXCHANGE == "HYPERLIQUID" else account_balance
                    in_positions = total_equity - account_balance
                    cash_buffer = total_equity * (CASH_PERCENTAGE / 100.0)
                    allocatable_usd = max(0, account_balance - cash_buffer)
                    add_console_log(f"💰 Equity: ${total_equity:.2f} | Balance: ${account_balance:.2f} | In Positions: ${in_positions:.2f}", "info")
                    add_console_log(f"   Cash Buffer ({CASH_PERCENTAGE}%): ${cash_buffer:.2f} | Allocatable: ${allocatable_usd:.2f}", "info")
                except Exception as e:
                    add_console_log(f"⚠️ Could not fetch account status: {e}", "warning")
                    allocatable_usd = 0.0  # Set to 0 to prevent accidental over-allocation

                # Phase 1: Close contradictory positions (signals vs positions)
                cprint("\n📌 Exit Contradictory Positions", "yellow", attrs=["bold"])
                self.handle_exits()

                if self.should_stop():
                    add_console_log("⏹️ Stop signal received - skipping allocation", "warning")
                    return

                # Wait for exchange to process closes
                cprint("⏳ Waiting for exchange to process...", "cyan")
                time.sleep(3)

                # Phase 2: AI-Driven Smart Allocation (initial call)
                add_console_log("🤖 Requesting AI allocation...", "info")
                cprint("\n📌 AI Smart Allocation", "cyan", attrs=["bold"])
                
                # === ALLOCATION PHASE (rebalance-first) ===
                initial_allocation_actions = self.allocate_portfolio(current_allocatable_usd=allocatable_usd)

                if not initial_allocation_actions:
                    add_console_log("No initial allocation actions generated", "info")
                else:
                    # Re-fetch open positions and recalculate allocatable_usd after initial exits
                    open_positions = self.fetch_all_open_positions()
                    if EXCHANGE == "HYPERLIQUID":
                        total_equity = n.get_account_value(
                            self.account.address if hasattr(self.account, "address") else self.account
                        )
                    else:
                        total_equity = get_account_balance(self.account)
                    account_balance = get_account_balance(self.account)
                    required_buffer_usd = total_equity * (CASH_PERCENTAGE / 100.0)
                    allocatable_usd = max(0, account_balance - required_buffer_usd)

                    cprint(f"\n💰 Re-evaluated Allocatable for trading after exits: ${allocatable_usd:.2f}", "green")
                    add_console_log(f"Re-evaluated Allocatable: ${allocatable_usd:.2f}", "info")

                    # 1) Plan and execute rebalance (CLOSE/REDUCE) actions first
                    rebalance_actions = self.plan_rebalance_actions(open_positions, initial_allocation_actions, total_equity)
                    if rebalance_actions:
                        add_console_log(f"Executing {len(rebalance_actions)} rebalance actions", "info")
                        self.execute_allocations(rebalance_actions)
                        # Give exchange a moment to settle positions and free margin
                        time.sleep(1)

                    # Refresh open_positions and total_equity again after rebalance actions
                    open_positions = self.fetch_all_open_positions()
                    if EXCHANGE == "HYPERLIQUID":
                        total_equity = n.get_account_value(
                            self.account.address if hasattr(self.account, "address") else self.account
                        )
                    else:
                        total_equity = get_account_balance(self.account)
                    account_balance = get_account_balance(self.account)
                    required_buffer_usd = total_equity * (CASH_PERCENTAGE / 100.0)
                    allocatable_usd = max(0, account_balance - required_buffer_usd)

                    cprint(f"\n💰 Re-evaluated Allocatable for trading after rebalance: ${allocatable_usd:.2f}", "green")
                    add_console_log(f"Re-evaluated Allocatable: ${allocatable_usd:.2f}", "info")

                    # ══════════════════════════════════════════════════════════════════
                    # PHASE 6: TRADE EXECUTION
                    # ══════════════════════════════════════════════════════════════════
                    # 2) Filter only OPEN/INCREASE actions and recalculate margin based on updated allocatable_usd
                    open_increase_actions = [a for a in initial_allocation_actions if a.get("action") in ("OPEN_LONG", "OPEN_SHORT", "INCREASE")]

                    if open_increase_actions:
                        # Recalculate margin for OPEN/INCREASE actions based on current allocatable_usd
                        margin_per_position = allocatable_usd / len(open_increase_actions) if open_increase_actions else 0
                        min_order_notional = 12.0 # Assuming this is consistent
                        min_margin = min_order_notional / LEVERAGE

                        if margin_per_position < min_margin:
                            cprint(f"⚠️ Margin per position (${margin_per_position:.2f}) below minimum (${min_margin:.2f}) for some OPEN/INCREASE actions.", "yellow")
                            add_console_log(f"Some OPEN/INCREASE actions skipped due to low margin", "warning")
                            open_increase_actions = [a for a in open_increase_actions if a.get("margin_usd", 0) >= min_margin]
                            if open_increase_actions: # Recalculate if some are still valid
                                margin_per_position = allocatable_usd / len(open_increase_actions)
                            else:
                                margin_per_position = 0

                        for action in open_increase_actions:
                            action["margin_usd"] = round(margin_per_position, 2)

                        add_console_log("────────────────────────────────────", "info")
                        add_console_log(f"🚀 PHASE 6: Executing {len(open_increase_actions)} allocation actions...", "info")
                        self.execute_allocations(open_increase_actions)

                if self.should_stop():
                    add_console_log("⏹️ Stop signal received - skipping execution", "warning")
                    return

                # Execution complete (rebalance + open actions already executed above)
                final_actions_executed = initial_allocation_actions # This now represents all planned actions, not just open ones
                if final_actions_executed and isinstance(final_actions_executed, list) and len(final_actions_executed) > 0:
                    cprint(f"\n✅ {mode_name} mode execution complete!", "green", attrs=["bold"])
                    add_console_log(f"✅ {mode_name} execution complete", "success")
                else:
                    cprint("\nℹ️ No allocation actions to execute.", "yellow")
                    add_console_log("ℹ️ No allocation actions generated", "info")

            except Exception as exec_err:
                cprint(f"❌ Execution pipeline failed: {exec_err}", "red")
                import traceback
                traceback.print_exc()
                add_console_log(f"❌ Execution error: {exec_err}", "error")

            # ══════════════════════════════════════════════════════════════════
            # PHASE 7: CYCLE COMPLETE
            # ══════════════════════════════════════════════════════════════════
            self.show_final_portfolio_report()

            try:
                if os.path.exists("temp_data"):
                    for file in os.listdir("temp_data"):
                        if file.endswith("_latest.csv"):
                            os.remove(os.path.join("temp_data", file))
            except Exception as e:
                cprint(f"⚠️ Error cleaning temp data: {e}", "yellow")

            cprint(f"\n{'=' * 80}", "cyan")
            cprint("✅ TRADING CYCLE COMPLETE", "white", "on_green", attrs=["bold"])

            # Log final summary
            add_console_log("────────────────────────────────────", "info")
            add_console_log("✅ TRADING CYCLE COMPLETE", "success")
            try:
                final_equity = n.get_account_value(self.account.address) if EXCHANGE == "HYPERLIQUID" else get_account_balance(self.account)
                final_positions = self.fetch_all_open_positions()
                add_console_log(f"📊 Final: {len(final_positions)} positions open | Equity: ${final_equity:.2f}", "info")
            except Exception as e:
                # Non-critical: just skip final summary if fetch fails
                cprint(f"⚠️ Could not fetch final status: {e}", "yellow")

            cprint(f"{'' * 80}\n", "cyan")

            try:
                account_balance = get_account_balance(self.account)
            except Exception as e:
                cprint(f"⚠️ Could not retrieve account balance: {e}", "yellow")
                account_balance = 0.0

            try:
                invested_total = 0.0
                positions = self.fetch_all_open_positions()
                for symbol, pos_list in positions.items():
                    for p in pos_list:
                        size = abs(float(p.get("size", 0)))
                        entry_price = float(p.get("entry_price", 0))
                        invested_total += size * entry_price
            except Exception as e:
                cprint(f"⚠️ Could not calculate invested total: {e}", "yellow")
                invested_total = 0.0

            cprint(f"💰 Account Balance: ${account_balance:,.2f}", "cyan", attrs=["bold"])
            cprint(f"🚀 Invested Total: ${invested_total:,.2f}", "cyan", attrs=["bold"])

        except Exception as e:
            cprint(f"\n❌ Error in trading cycle: {e}", "white", "on_red")
            import traceback
            traceback.print_exc()


def main():
    """Main function - simple cycle every X minutes"""
    cprint("🚀 AI Trading System Starting Up! 🚀", "white", "on_blue")
    print("🛑 Press Ctrl+C to stop.\n")

    agent = TradingAgent()

    while True:
        try:
            # Run the complete cycle
            agent.run_trading_cycle()

            # Log next cycle time BEFORE sleeping
            next_run = datetime.now() + timedelta(minutes=SLEEP_BETWEEN_RUNS_MINUTES)
            cprint(f"\n⏰ Next cycle at UTC: {next_run.strftime('%d-%m-%Y %H:%M:%S')}", "white", "on_green")
            add_console_log(f"Next cycle in {SLEEP_BETWEEN_RUNS_MINUTES} minutes", "info")

            # Sleep until next cycle
            time.sleep(SLEEP_BETWEEN_RUNS_MINUTES * 60)

        except KeyboardInterrupt:
            cprint("\n👋 AI Agent shutting down gracefully...", "white", "on_blue")
            add_console_log("👋 Agent shutting down gracefully...", "info")
            if WEBSOCKET_AVAILABLE:
                try:
                    stop_websocket_feeds()
                    cprint("🔌 WebSocket feeds stopped", "cyan")
                except Exception as e:
                    cprint(f"⚠️  Error stopping WebSocket feeds: {e}", "yellow")
            break
        except Exception as e:
            cprint(f"\n❌ Error in main loop: {e}", "white", "on_red")
            import traceback
            traceback.print_exc()
            cprint(f"\n⏰ Retrying in {SLEEP_BETWEEN_RUNS_MINUTES} minutes...", "yellow")
            time.sleep(SLEEP_BETWEEN_RUNS_MINUTES * 60)


if __name__ == "__main__":
    main()
