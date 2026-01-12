"""
Position Management Functions for Trading Agent

This module contains standalone functions for position sizing,
threshold checking, and position data formatting.

All functions are stateless and take explicit parameters
to enable easier testing and reuse.
"""

from typing import Dict, Any, List, Tuple, Optional

# Import logging utilities with fallback
try:
    from src.utils.logging_utils import add_console_log
except ImportError:
    def add_console_log(message, level="info", console_file=None):
        print(f"[POSITION] {message}")

# Import termcolor with fallback
try:
    from termcolor import cprint
except ImportError:
    def cprint(msg, *args, **kwargs):
        print(msg)


# =============================================================================
# POSITION SIZING
# =============================================================================

def calculate_position_size(
    account_balance: float,
    exchange: str,
    max_position_pct: float,
    leverage: float
) -> float:
    """
    Calculate position size based on account balance and risk parameters.

    Args:
        account_balance: Current account balance in USD
        exchange: Exchange name (e.g., "HYPERLIQUID", "ASTER", "SOLANA")
        max_position_pct: Maximum position percentage (0-100)
        leverage: Leverage multiplier (e.g., 5.0 for 5x)

    Returns:
        Position size in USD (notional for leveraged, direct for spot)
    """
    if exchange in ["ASTER", "HYPERLIQUID"]:
        # Perpetual futures: margin * leverage = notional
        margin_to_use = account_balance * (max_position_pct / 100)
        notional_position = margin_to_use * leverage

        cprint(f"   📊 Position Calculation ({exchange}):", "yellow", attrs=['bold'])
        cprint(f"   💵 Account Balance: ${account_balance:,.2f}", "white")
        cprint(f"   📈 Max Position %: {max_position_pct}%", "white")
        cprint(f"   💰 Margin to Use: ${margin_to_use:,.2f}", "green", attrs=['bold'])
        cprint(f"   ⚡ Leverage: {leverage}x", "white")
        cprint(f"   💎 Notional Position: ${notional_position:,.2f}", "cyan", attrs=['bold'])

        return notional_position
    else:
        # For Solana: No leverage, direct position size
        position_size = account_balance * (max_position_pct / 100)

        cprint(f"   📊 Position Calculation (SOLANA):", "yellow", attrs=['bold'])
        cprint(f"   💵 USDC Balance: ${account_balance:,.2f}", "white")
        cprint(f"   📈 Max Position %: {max_position_pct}%", "white")
        cprint(f"   💎 Position Size: ${position_size:,.2f}", "cyan", attrs=['bold'])

        return position_size


# =============================================================================
# THRESHOLD CHECKING
# =============================================================================

def check_tp_sl_thresholds(
    pnl_percent: float,
    take_profit_threshold: float,
    stop_loss_threshold: float
) -> Tuple[bool, str, str]:
    """
    Check if position hits take profit or stop loss thresholds.

    Args:
        pnl_percent: Current position P&L percentage
        take_profit_threshold: Take profit threshold (e.g., 5.0 for 5%)
        stop_loss_threshold: Stop loss threshold (e.g., -2.0 for -2%)

    Returns:
        Tuple of (should_close: bool, action: str, reason: str)
        - should_close: True if threshold hit
        - action: "TAKE_PROFIT", "STOP_LOSS", or "NONE"
        - reason: Human-readable explanation
    """
    if pnl_percent >= take_profit_threshold:
        reason = f"TAKE PROFIT: {pnl_percent:.2f}% >= {take_profit_threshold}%"
        return True, "TAKE_PROFIT", reason
    elif pnl_percent <= stop_loss_threshold:
        reason = f"STOP LOSS: {pnl_percent:.2f}% <= {stop_loss_threshold}%"
        return True, "STOP_LOSS", reason
    else:
        return False, "NONE", ""


def check_profit_target(
    pnl_percent: float,
    profit_target_threshold: float,
    ai_confidence: int,
    min_confidence_to_close: int
) -> Tuple[bool, str]:
    """
    Check if position meets profit target with sufficient AI confidence.

    Args:
        pnl_percent: Current position P&L percentage
        profit_target_threshold: Minimum profit for partial take (e.g., 0.5%)
        ai_confidence: AI confidence level (0-100)
        min_confidence_to_close: Minimum confidence required to close

    Returns:
        Tuple of (should_close: bool, reason: str)
    """
    if pnl_percent >= profit_target_threshold and ai_confidence >= min_confidence_to_close:
        return True, f"Profit target at {pnl_percent:.2f}% with {ai_confidence}% confidence"
    return False, ""


# =============================================================================
# POSITION DATA FORMATTING
# =============================================================================

def build_position_data(
    symbol: str,
    size: float,
    entry_price: float,
    pnl_percent: float,
    age_hours: float = 0.0
) -> Dict[str, Any]:
    """
    Build a standardized position data dictionary.

    Args:
        symbol: Token symbol (e.g., "BTC", "ETH")
        size: Position size (positive for long, negative for short)
        entry_price: Entry price in USD
        pnl_percent: Current P&L percentage
        age_hours: Position age in hours

    Returns:
        Standardized position dictionary
    """
    is_long = size > 0
    return {
        "symbol": symbol,
        "size": size,
        "entry_price": entry_price,
        "pnl_percent": pnl_percent,
        "is_long": is_long,
        "side": "LONG" if is_long else "SHORT",
        "age_hours": age_hours,
    }


def format_position_for_display(
    symbol: str,
    side: str,
    size: float,
    entry_price: float,
    pnl_percent: float,
    age_hours: float = 0.0
) -> str:
    """
    Format position data for display/logging.

    Args:
        symbol: Token symbol
        side: "LONG" or "SHORT"
        size: Position size
        entry_price: Entry price
        pnl_percent: P&L percentage
        age_hours: Position age in hours

    Returns:
        Formatted string for display
    """
    age_str = f"{age_hours:.1f}h" if age_hours > 0 else "NEW"
    return (
        f"{symbol:<10} | {side:<10} | "
        f"Size: {size:>10.4f} | Entry: ${entry_price:>10.2f} | "
        f"PnL: {pnl_percent:>6.2f}% | Age: {age_str}"
    )


def format_position_summary_for_ai(positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Format position list for AI analysis prompt.

    Args:
        positions: List of position data dictionaries

    Returns:
        List of formatted position summaries for AI prompt
    """
    summary = []
    for pos in positions:
        summary.append({
            "symbol": pos.get("symbol", "UNKNOWN"),
            "side": "LONG" if pos.get("is_long", True) else "SHORT",
            "size": pos.get("size", 0),
            "entry_price": pos.get("entry_price", 0),
            "current_pnl": pos.get("pnl_percent", 0),
            "age_hours": pos.get("age_hours", 0),
        })
    return summary


# =============================================================================
# CLOSE DECISION HELPERS
# =============================================================================

def build_close_decision(
    action: str,
    reasoning: str,
    confidence: int = 0
) -> Dict[str, Any]:
    """
    Build a standardized close decision dictionary.

    Args:
        action: "CLOSE" or "KEEP"
        reasoning: Explanation for the decision
        confidence: Confidence level (0-100)

    Returns:
        Standardized decision dictionary
    """
    return {
        "action": action,
        "reasoning": reasoning,
        "confidence": confidence
    }


def evaluate_positions_for_tp_sl(
    positions_data: Dict[str, List[Dict[str, Any]]],
    take_profit_threshold: float,
    stop_loss_threshold: float
) -> Dict[str, Dict[str, Any]]:
    """
    Evaluate all positions for take profit / stop loss triggers.

    This should be called BEFORE AI analysis to force-close positions
    that hit hard thresholds regardless of AI opinion.

    Args:
        positions_data: Dict mapping symbol -> list of position dicts
        take_profit_threshold: TP threshold percentage
        stop_loss_threshold: SL threshold percentage

    Returns:
        Dict of forced close decisions (symbol -> decision dict)
    """
    forced_decisions = {}

    for symbol, positions in positions_data.items():
        for pos in positions:
            pnl_percent = pos.get("pnl_percent", 0)

            should_close, action, reason = check_tp_sl_thresholds(
                pnl_percent, take_profit_threshold, stop_loss_threshold
            )

            if should_close:
                forced_decisions[symbol] = build_close_decision(
                    action="CLOSE",
                    reasoning=reason,
                    confidence=100
                )

                # Log the trigger
                if action == "TAKE_PROFIT":
                    cprint(f"🎯 {symbol}: TAKE PROFIT TRIGGERED - {pnl_percent:.2f}%", "green", attrs=["bold"])
                    add_console_log(f"TAKE PROFIT: Closing {symbol} at +{pnl_percent:.2f}%", "success")
                else:
                    cprint(f"🚨 {symbol}: STOP LOSS TRIGGERED - {pnl_percent:.2f}%", "red", attrs=["bold"])
                    add_console_log(f"STOP LOSS: Closing {symbol} at {pnl_percent:.2f}%", "warning")

    return forced_decisions


# =============================================================================
# MARKET DATA HELPERS
# =============================================================================

def extract_current_price(df, symbol: str) -> Optional[float]:
    """
    Robustly extract current price from market data DataFrame.

    Args:
        df: pandas DataFrame with OHLCV data
        symbol: Symbol name (for error messages)

    Returns:
        Current price or None if not found
    """
    if df is None or df.empty:
        return None

    latest = df.iloc[-1]

    # Try different column name conventions
    price_columns = ["Close", "close", "close_price", "c", "price"]
    for col in price_columns:
        if col in df.columns:
            return float(latest[col])

    cprint(f"⚠️ No close price column found for {symbol}", "yellow")
    return None


def build_market_summary(
    df,
    symbol: str
) -> Optional[Dict[str, Any]]:
    """
    Build market summary dict from DataFrame for AI analysis.

    Args:
        df: pandas DataFrame with OHLCV and indicator data
        symbol: Symbol name

    Returns:
        Market summary dict or None if data unavailable
    """
    current_price = extract_current_price(df, symbol)
    if current_price is None:
        return None

    latest = df.iloc[-1]
    ma20 = latest.get("MA20", 0)
    ma40 = latest.get("MA40", 0)
    rsi = latest.get("RSI", 0)

    return {
        "current_price": current_price,
        "ma20": ma20,
        "ma40": ma40,
        "rsi": rsi,
        "trend": "Bullish" if current_price > ma20 else "Bearish",
    }
