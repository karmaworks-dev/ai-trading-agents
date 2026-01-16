"""
Trade Execution Functions for Trading Agent

This module contains standalone functions for trade execution,
validation, notional calculations, and execution logging.

All functions are stateless and take explicit parameters
to enable easier testing and reuse.
"""

from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime

# Import logging utilities with fallback
try:
    from src.utils.logging_utils import add_console_log
except ImportError:
    def add_console_log(message, level="info", console_file=None):
        print(f"[EXEC] {message}")

# Import termcolor with fallback
try:
    from termcolor import cprint
except ImportError:
    def cprint(msg, *args, **kwargs):
        print(msg)


# =============================================================================
# CONSTANTS
# =============================================================================

# Default minimum notional for most exchanges
DEFAULT_MIN_NOTIONAL = 12.0

# Action types that require margin
MARGIN_REQUIRED_ACTIONS = ["OPEN_LONG", "OPEN_SHORT", "INCREASE"]

# Action types that reduce positions
POSITION_REDUCE_ACTIONS = ["CLOSE", "REDUCE"]


# =============================================================================
# NOTIONAL CALCULATIONS
# =============================================================================

def calculate_notional(margin_usd: float, leverage: float) -> float:
    """
    Calculate notional value from margin and leverage.

    Args:
        margin_usd: Margin amount in USD
        leverage: Leverage multiplier

    Returns:
        Notional value in USD
    """
    return margin_usd * leverage


def calculate_margin_from_notional(notional: float, leverage: float) -> float:
    """
    Calculate margin required for a given notional.

    Args:
        notional: Notional value in USD
        leverage: Leverage multiplier

    Returns:
        Required margin in USD
    """
    if leverage <= 0:
        return notional
    return notional / leverage


def check_min_notional(
    notional: float,
    min_notional: float = DEFAULT_MIN_NOTIONAL
) -> Tuple[bool, str]:
    """
    Check if notional meets minimum exchange requirements.

    Args:
        notional: Notional value in USD
        min_notional: Minimum required notional

    Returns:
        Tuple of (meets_minimum, reason_if_not)
    """
    if notional < min_notional:
        return False, f"notional ${notional:.2f} < min ${min_notional:.2f}"
    return True, ""


# =============================================================================
# TRADE VALIDATION
# =============================================================================

def validate_trade_action(
    action: Dict[str, Any],
    valid_symbols: List[str],
    leverage: float,
    min_notional: float = DEFAULT_MIN_NOTIONAL
) -> Tuple[bool, str]:
    """
    Validate a trade action before execution.

    Args:
        action: Action dict with symbol, action, margin_usd, etc.
        valid_symbols: List of valid trading symbols
        leverage: Current leverage setting
        min_notional: Minimum notional requirement

    Returns:
        Tuple of (is_valid, rejection_reason)
    """
    symbol = action.get("symbol")
    action_type = action.get("action")

    if not symbol:
        return False, "missing symbol"

    if not action_type:
        return False, "missing action type"

    if symbol not in valid_symbols:
        return False, f"{symbol} not in configured symbols"

    # Validate margin for position-opening actions
    if action_type in MARGIN_REQUIRED_ACTIONS:
        margin_usd = action.get("margin_usd", 0)
        if margin_usd <= 0:
            return False, f"{symbol}: invalid margin_usd"

        notional = calculate_notional(margin_usd, leverage)
        meets_min, reason = check_min_notional(notional, min_notional)
        if not meets_min:
            return False, f"{symbol}: {reason}"

    # Validate reduce amount for REDUCE action
    if action_type == "REDUCE":
        reduce_by = action.get("reduce_by_usd", 0)
        if reduce_by <= 0:
            return False, f"{symbol}: invalid reduce_by_usd"

    return True, ""


def validate_position_for_action(
    action_type: str,
    is_in_position: bool,
    position_size: float,
    is_long: bool
) -> Tuple[bool, str]:
    """
    Validate that position state allows the requested action.

    Args:
        action_type: Type of action to perform
        is_in_position: Whether there's an existing position
        position_size: Current position size
        is_long: Whether current position is long

    Returns:
        Tuple of (can_execute, reason_if_not)
    """
    # CLOSE/REDUCE require existing position
    if action_type in ["CLOSE", "REDUCE"]:
        if not is_in_position or position_size == 0:
            return False, "no position to close/reduce"

    return True, ""


def check_position_conflict(
    action_type: str,
    is_in_position: bool,
    is_long: bool
) -> Tuple[bool, str]:
    """
    Check if action conflicts with existing position direction.

    Args:
        action_type: OPEN_LONG, OPEN_SHORT, INCREASE
        is_in_position: Whether there's an existing position
        is_long: Whether current position is long

    Returns:
        Tuple of (has_conflict, conflict_description)
    """
    if not is_in_position:
        return False, ""

    # OPEN_LONG with existing SHORT = conflict
    if action_type == "OPEN_LONG" and not is_long:
        return True, "OPEN_LONG conflicts with existing SHORT"

    # OPEN_SHORT with existing LONG = conflict
    if action_type == "OPEN_SHORT" and is_long:
        return True, "OPEN_SHORT conflicts with existing LONG"

    # INCREASE must match position direction
    if action_type == "INCREASE":
        # INCREASE on a LONG position is fine if action implies long
        # INCREASE on a SHORT position is fine if action implies short
        pass  # No conflict for INCREASE matching direction

    return False, ""


# =============================================================================
# EXECUTION LOGGING
# =============================================================================

def format_trade_start_log(
    symbol: str,
    action_type: str,
    reason: str = ""
) -> str:
    """
    Format log message for trade execution start.

    Args:
        symbol: Trading symbol
        action_type: Type of action
        reason: Optional reason for the trade

    Returns:
        Formatted log string
    """
    lines = [f"🎯 {symbol}: {action_type}"]
    if reason:
        lines.append(f"   📝 {reason}")
    return "\n".join(lines)


def format_trade_success_log(
    symbol: str,
    action_type: str,
    notional: float,
    leverage: float,
    side: str = "LONG"
) -> str:
    """
    Format log message for successful trade.

    Args:
        symbol: Trading symbol
        action_type: Type of action executed
        notional: Notional value traded
        leverage: Leverage used
        side: Position side (LONG/SHORT)

    Returns:
        Formatted success log string
    """
    if action_type == "CLOSE":
        return f"✅ Closed {symbol} {side}"
    elif action_type == "REDUCE":
        return f"✅ Reduced {symbol} by ${notional:.2f}"
    else:
        return f"✅ Opened {side} {symbol} ${notional:.2f}"


def format_trade_failure_log(
    symbol: str,
    action_type: str,
    error: str = ""
) -> str:
    """
    Format log message for failed trade.

    Args:
        symbol: Trading symbol
        action_type: Type of action attempted
        error: Error message if any

    Returns:
        Formatted failure log string
    """
    if error:
        return f"❌ {symbol} {action_type} failed: {error}"
    return f"❌ {symbol} {action_type} failed (no result)"


# =============================================================================
# EXECUTION SUMMARY
# =============================================================================

def build_execution_summary(
    executed_count: int,
    failed_count: int,
    skipped_count: int = 0
) -> Dict[str, Any]:
    """
    Build execution summary statistics.

    Args:
        executed_count: Number of successfully executed trades
        failed_count: Number of failed trades
        skipped_count: Number of skipped trades

    Returns:
        Summary dict with counts and success rate
    """
    total = executed_count + failed_count + skipped_count
    success_rate = (executed_count / total * 100) if total > 0 else 0

    return {
        "executed": executed_count,
        "failed": failed_count,
        "skipped": skipped_count,
        "total": total,
        "success_rate": round(success_rate, 1),
    }


def format_execution_summary(summary: Dict[str, Any]) -> str:
    """
    Format execution summary for display.

    Args:
        summary: Summary dict from build_execution_summary

    Returns:
        Formatted summary string
    """
    return (
        f"EXECUTION COMPLETE: {summary['executed']} succeeded, "
        f"{summary['failed']} failed"
        + (f", {summary['skipped']} skipped" if summary.get('skipped', 0) > 0 else "")
    )


# =============================================================================
# POSITION STATE HELPERS
# =============================================================================

def get_position_direction(is_long: bool) -> str:
    """
    Get position direction string.

    Args:
        is_long: Whether position is long

    Returns:
        "LONG" or "SHORT"
    """
    return "LONG" if is_long else "SHORT"


def calculate_current_notional(
    position_size: float,
    entry_price: float
) -> float:
    """
    Calculate current notional value of a position.

    Args:
        position_size: Position size (can be negative for short)
        entry_price: Entry price

    Returns:
        Notional value in USD
    """
    return abs(float(position_size) * float(entry_price))


def should_close_for_reversal(
    action_type: str,
    is_in_position: bool,
    is_long: bool,
    exchange: str
) -> bool:
    """
    Determine if position should be closed before opening opposite.

    For HyperLiquid, we can net positions directly.
    For other exchanges, we need to close first.

    Args:
        action_type: OPEN_LONG or OPEN_SHORT
        is_in_position: Whether there's an existing position
        is_long: Whether current position is long
        exchange: Exchange name

    Returns:
        True if should close first, False if can net directly
    """
    if not is_in_position:
        return False

    # HyperLiquid supports netting
    if exchange == "HYPERLIQUID":
        return False

    # Check if it's a reversal (opposite direction)
    if action_type == "OPEN_LONG" and not is_long:
        return True
    if action_type == "OPEN_SHORT" and is_long:
        return True

    return False


# =============================================================================
# EXIT SIGNAL LOGIC
# =============================================================================

def should_exit_position(
    signal_action: str,
    is_long: bool
) -> Tuple[bool, str]:
    """
    Determine if position should be exited based on signal.

    Logic:
    - BUY signal + LONG position → KEEP (confirms)
    - BUY signal + SHORT position → CLOSE (contradicts)
    - SELL signal + LONG position → CLOSE (contradicts)
    - SELL signal + SHORT position → KEEP (confirms)
    - NOTHING signal → KEEP any position

    Args:
        signal_action: "BUY", "SELL", or "NOTHING"
        is_long: Whether current position is long

    Returns:
        Tuple of (should_exit, reason)
    """
    signal = signal_action.upper()

    if signal == "NOTHING":
        return False, "NOTHING signal - keeping position"

    if signal == "BUY":
        if is_long:
            return False, "BUY confirms LONG position"
        else:
            return True, "BUY contradicts SHORT position"

    if signal == "SELL":
        if is_long:
            return True, "SELL contradicts LONG position"
        else:
            return False, "SELL confirms SHORT position"

    return False, f"Unknown signal: {signal}"


def categorize_exit_decision(
    signal_action: str,
    position_direction: str
) -> str:
    """
    Categorize the exit decision for logging.

    Args:
        signal_action: The trading signal
        position_direction: "LONG" or "SHORT"

    Returns:
        Category string: "CONFIRM", "EXIT", or "NEUTRAL"
    """
    signal = signal_action.upper()
    is_long = position_direction == "LONG"

    if signal == "NOTHING":
        return "NEUTRAL"

    if (signal == "BUY" and is_long) or (signal == "SELL" and not is_long):
        return "CONFIRM"

    return "EXIT"


# =============================================================================
# TRADE RESULT HANDLING
# =============================================================================

def unpack_entry_result(
    entry_result,
    default_leverage: float
) -> Tuple[Any, float]:
    """
    Unpack entry result which may be a tuple or single value.

    Exchange functions may return:
    - (success: bool, actual_leverage: int) tuple
    - Just a result value

    Args:
        entry_result: Result from exchange entry function
        default_leverage: Default leverage to use if not in result

    Returns:
        Tuple of (result, actual_leverage)
    """
    if isinstance(entry_result, tuple) and len(entry_result) == 2:
        return entry_result[0], entry_result[1]
    return entry_result, default_leverage


def build_trade_result(
    success: bool,
    symbol: str,
    action_type: str,
    notional: float,
    leverage: float,
    side: str,
    error: str = ""
) -> Dict[str, Any]:
    """
    Build a standardized trade result dictionary.

    Args:
        success: Whether trade succeeded
        symbol: Trading symbol
        action_type: Type of action executed
        notional: Notional value traded
        leverage: Leverage used
        side: Position side (LONG/SHORT)
        error: Error message if failed

    Returns:
        Trade result dictionary
    """
    return {
        "success": success,
        "symbol": symbol,
        "action": action_type,
        "notional": notional,
        "leverage": leverage,
        "side": side,
        "error": error,
    }


def log_open_trade_result(
    success: bool,
    symbol: str,
    side: str,
    notional: float,
    leverage: float,
    is_netting: bool = False
) -> None:
    """
    Log the result of an open trade action.

    Args:
        success: Whether trade succeeded
        symbol: Trading symbol
        side: "LONG" or "SHORT"
        notional: Actual notional after leverage adjustment
        leverage: Actual leverage used
        is_netting: Whether this was a netting operation
    """
    netting_suffix = " (netting)" if is_netting else ""

    if success:
        cprint(f"   ✅ {side} position opened{netting_suffix} @ {leverage}x leverage!", "green")
        add_console_log(f"✅ Opened {side} {symbol} ${notional:.2f}{netting_suffix}", "success")
    else:
        cprint(f"   ❌ {side} position failed to open (no result returned)", "red")
        add_console_log(f"❌ {symbol} {side} failed (no result)", "error")


def log_close_trade_result(
    success: bool,
    symbol: str,
    side: str,
    notional: float = 0
) -> None:
    """
    Log the result of a close trade action.

    Args:
        success: Whether close succeeded
        symbol: Trading symbol
        side: Original position side
        notional: Position notional that was closed
    """
    if success:
        cprint(f"   ✅ Position closed!", "green")
        add_console_log(f"✅ Closed {symbol} {side}", "success")
    else:
        cprint(f"   ⚠️ Close may have failed for {symbol}", "yellow")
        add_console_log(f"⚠️ Close failed for {symbol}", "warning")


def log_reduce_trade_result(
    success: bool,
    symbol: str,
    reduce_amount: float
) -> None:
    """
    Log the result of a reduce trade action.

    Args:
        success: Whether reduce succeeded
        symbol: Trading symbol
        reduce_amount: Amount reduced
    """
    if success:
        cprint(f"   ✅ Position reduced!", "green")
        add_console_log(f"✅ Reduced {symbol} by ${reduce_amount:.2f}", "success")
    else:
        cprint(f"   ⚠️ partial_close not available", "yellow")


# =============================================================================
# ACTION PRE-VALIDATION
# =============================================================================

def validate_open_action_params(
    action: Dict[str, Any],
    leverage: float,
    min_notional: float = DEFAULT_MIN_NOTIONAL
) -> Tuple[bool, float, float, str]:
    """
    Validate parameters for OPEN_LONG/OPEN_SHORT/INCREASE actions.

    Args:
        action: Action dictionary
        leverage: Current leverage setting
        min_notional: Minimum notional requirement

    Returns:
        Tuple of (is_valid, margin_usd, notional, error_reason)
    """
    margin_usd = action.get("margin_usd", 0)

    if margin_usd <= 0:
        return False, 0, 0, "invalid margin_usd"

    notional = calculate_notional(margin_usd, leverage)

    meets_min, reason = check_min_notional(notional, min_notional)
    if not meets_min:
        return False, margin_usd, notional, reason

    return True, margin_usd, notional, ""


def validate_reduce_action_params(
    action: Dict[str, Any],
    is_in_position: bool,
    position_size: float
) -> Tuple[bool, float, str]:
    """
    Validate parameters for REDUCE action.

    Args:
        action: Action dictionary
        is_in_position: Whether there's an existing position
        position_size: Current position size

    Returns:
        Tuple of (is_valid, reduce_amount, error_reason)
    """
    reduce_amount = action.get("reduce_by_usd", 0)

    if not is_in_position or position_size == 0:
        return False, 0, "no position to reduce"

    if reduce_amount <= 0:
        return False, 0, "invalid reduce amount"

    return True, reduce_amount, ""


def validate_close_action_params(
    is_in_position: bool,
    position_size: float
) -> Tuple[bool, str]:
    """
    Validate parameters for CLOSE action.

    Args:
        is_in_position: Whether there's an existing position
        position_size: Current position size

    Returns:
        Tuple of (is_valid, error_reason)
    """
    if not is_in_position or position_size == 0:
        return False, "no position to close"

    return True, ""


# =============================================================================
# EXECUTION FLOW HELPERS
# =============================================================================

def determine_open_action_side(action_type: str) -> str:
    """
    Determine the side (LONG/SHORT) for an open action.

    Args:
        action_type: OPEN_LONG, OPEN_SHORT, or INCREASE

    Returns:
        "LONG" or "SHORT"
    """
    if action_type in ["OPEN_LONG"]:
        return "LONG"
    elif action_type in ["OPEN_SHORT"]:
        return "SHORT"
    return "UNKNOWN"


def needs_position_close_first(
    action_type: str,
    is_in_position: bool,
    is_long: bool,
    exchange: str
) -> bool:
    """
    Determine if existing position needs to be closed before opening new one.

    For HyperLiquid, positions can be netted directly.
    For other exchanges, opposite positions need to be closed first.

    Args:
        action_type: OPEN_LONG or OPEN_SHORT
        is_in_position: Whether there's an existing position
        is_long: Whether current position is long
        exchange: Exchange name

    Returns:
        True if position should be closed first
    """
    if not is_in_position:
        return False

    # HyperLiquid supports netting
    if exchange == "HYPERLIQUID":
        return False

    # Check if opposite direction
    if action_type == "OPEN_LONG" and not is_long:
        return True
    if action_type == "OPEN_SHORT" and is_long:
        return True

    return False


def has_opposite_position(
    action_type: str,
    is_in_position: bool,
    is_long: bool
) -> bool:
    """
    Check if there's an opposite position that would be netted.

    Args:
        action_type: OPEN_LONG or OPEN_SHORT
        is_in_position: Whether there's an existing position
        is_long: Whether current position is long

    Returns:
        True if opposite position exists
    """
    if not is_in_position:
        return False

    if action_type == "OPEN_LONG" and not is_long:
        return True
    if action_type == "OPEN_SHORT" and is_long:
        return True

    return False


# =============================================================================
# EXIT PHASE HELPERS
# =============================================================================

def should_trigger_stop_loss(
    pnl_percent: float,
    threshold: float = -2.0
) -> bool:
    """
    Check if stop loss should be triggered.

    Args:
        pnl_percent: Current PnL percentage
        threshold: Stop loss threshold (negative number)

    Returns:
        True if stop loss should trigger
    """
    return pnl_percent <= threshold


def signal_contradicts_position(
    signal_action: str,
    is_long: bool
) -> bool:
    """
    Check if signal contradicts current position direction.

    Logic:
    - SELL signal + LONG position → contradicts (True)
    - BUY signal + SHORT position → contradicts (True)
    - Otherwise → confirms (False)

    Args:
        signal_action: "BUY", "SELL", or "NOTHING"
        is_long: Whether current position is long

    Returns:
        True if signal contradicts position
    """
    action = signal_action.upper()

    if action == "NOTHING":
        return False  # NOTHING never contradicts

    if action == "SELL" and is_long:
        return True
    if action == "BUY" and not is_long:
        return True

    return False


def format_exit_phase_summary(
    closed_count: int,
    held_count: int
) -> str:
    """
    Format summary for exit phase completion.

    Args:
        closed_count: Number of positions closed
        held_count: Number of positions held

    Returns:
        Formatted summary string
    """
    return f"PHASE 1 COMPLETE: Closed {closed_count}, Held {held_count} positions"
