"""
Portfolio Allocation Functions for Trading Agent

This module contains standalone functions for portfolio allocation,
signal filtering, action validation, and capital distribution.

All functions are stateless and take explicit parameters
to enable easier testing and reuse.
"""

from typing import Dict, Any, List, Tuple, Optional

# Import logging utilities with fallback
try:
    from src.utils.logging_utils import add_console_log
except ImportError:
    def add_console_log(message, level="info", console_file=None):
        print(f"[ALLOC] {message}")

# Import termcolor with fallback
try:
    from termcolor import cprint
except ImportError:
    def cprint(msg, *args, **kwargs):
        print(msg)


# =============================================================================
# SYMBOL NORMALIZATION
# =============================================================================

# Common cryptocurrency name aliases for AI response normalization
SYMBOL_ALIASES = {
    "BITCOIN": "BTC",
    "ETHEREUM": "ETH",
    "SOLANA": "SOL",
    "LITECOIN": "LTC",
    "DOGECOIN": "DOGE",
    "HYPERLIQUID": "HYPE",
    "AVALANCHE": "AVAX",
    "CHAINLINK": "LINK",
    "POLYGON": "MATIC",
    "ARBITRUM": "ARB",
    "OPTIMISM": "OP",
    "COSMOS": "ATOM",
    "POLKADOT": "DOT",
    "UNISWAP": "UNI",
    "AAVE": "AAVE",
    "CELESTIA": "TIA",
    "INJECTIVE": "INJ",
    "JUPITER": "JUP",
    "PEPE": "PEPE",
    "BONK": "BONK",
    "SHIBA": "SHIB",
    "SHIBA INU": "SHIB",
}


def normalize_symbol(raw_symbol: str, valid_symbols: List[str]) -> str:
    """
    Normalize AI-returned symbols to match valid symbols list.

    Handles common AI hallucinations like:
    - "BITCOIN" -> "BTC"
    - "btc" -> "BTC"
    - "ETH/USD" -> "ETH"
    - "BTC-PERP" -> "BTC"

    Args:
        raw_symbol: Raw symbol string from AI response
        valid_symbols: List of valid symbol names

    Returns:
        Normalized symbol if found in valid_symbols,
        otherwise returns the original (will be rejected by validation)
    """
    if not raw_symbol:
        return raw_symbol

    upper = raw_symbol.upper().strip()

    # Check aliases first
    if upper in SYMBOL_ALIASES:
        normalized = SYMBOL_ALIASES[upper]
        if normalized in valid_symbols:
            return normalized

    # Strip common suffixes (e.g., BTC/USD, BTC-USD, BTCUSD, BTC-PERP)
    suffixes = ["/USD", "-USD", "USD", "/USDT", "-USDT", "USDT", "-PERP", "/PERP", "PERP"]
    for suffix in suffixes:
        if upper.endswith(suffix):
            stripped = upper[:-len(suffix)]
            if stripped in valid_symbols:
                return stripped
            break

    # Check if uppercase version is in symbols
    if upper in valid_symbols:
        return upper

    # Return original if no normalization worked
    return raw_symbol


# =============================================================================
# SIGNAL FILTERING
# =============================================================================

def filter_strategy_signals(
    recommendations: List[Dict[str, Any]],
    valid_symbols: List[str],
    long_only: bool = False,
    open_positions: Optional[Dict[str, Any]] = None
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Filter strategy signals based on actionability and constraints.

    Args:
        recommendations: List of recommendation dicts with token, action, confidence
        valid_symbols: List of valid trading symbols
        long_only: If True, reject SELL signals for new positions
        open_positions: Dict of current open positions (symbol -> position data)

    Returns:
        Tuple of (filtered_signals, removal_reasons)
    """
    if open_positions is None:
        open_positions = {}

    signals = []
    removed = []

    for rec in recommendations:
        token = rec.get("token", "")
        action = str(rec.get("action", "")).upper()

        if token not in valid_symbols:
            removed.append(f"{token}: not in symbols")
            continue

        if action not in ["BUY", "SELL"]:
            removed.append(f"{token}: action {action} not actionable")
            continue

        if long_only and action == "SELL" and token not in open_positions:
            removed.append(f"{token}: SELL blocked by LONG_ONLY")
            continue

        signals.append({
            "symbol": token,
            "action": action,
            "confidence": int(rec.get("confidence", 50)),
        })

    return signals, removed


# =============================================================================
# BALANCE CALCULATIONS
# =============================================================================

def calculate_allocatable_balance(
    account_balance: float,
    total_equity: float,
    cash_buffer_pct: float
) -> Tuple[float, float]:
    """
    Calculate allocatable USD after applying cash buffer.

    Args:
        account_balance: Available account balance in USD
        total_equity: Total equity value in USD
        cash_buffer_pct: Cash buffer percentage (0-100)

    Returns:
        Tuple of (required_buffer_usd, allocatable_usd)
    """
    required_buffer_usd = total_equity * (cash_buffer_pct / 100.0)
    allocatable_usd = max(0, account_balance - required_buffer_usd)
    return required_buffer_usd, allocatable_usd


def calculate_equal_distribution(
    signals: List[Dict[str, Any]],
    available_balance: float,
    max_position_pct: float,
    cash_buffer_pct: float,
    leverage: float,
    min_order_notional: float = 12.0
) -> Tuple[float, List[Dict[str, Any]]]:
    """
    Calculate equal margin distribution across signals.

    If margin per position is below minimum, prioritizes highest confidence signals.

    Args:
        signals: List of signal dicts with symbol, action, confidence
        available_balance: Available balance in USD
        max_position_pct: Maximum position percentage (0-100)
        cash_buffer_pct: Cash buffer percentage (0-100)
        leverage: Leverage multiplier
        min_order_notional: Minimum order notional in USD

    Returns:
        Tuple of (margin_per_position, filtered_signals)
    """
    if not signals:
        return 0, []

    usable_margin = available_balance * (max_position_pct / 100)
    cash_buffer = available_balance * (cash_buffer_pct / 100)
    allocatable_margin = max(0, usable_margin - cash_buffer)  # Ensure we never go below zero
    min_margin = min_order_notional / leverage

    margin_per_position = allocatable_margin / len(signals)

    if margin_per_position < min_margin:
        # Take only highest confidence signals
        sorted_signals = sorted(signals, key=lambda x: x.get("confidence", 0), reverse=True)
        max_positions = int(allocatable_margin / min_margin)
        filtered_signals = sorted_signals[:max(1, max_positions)]

        if not filtered_signals:
            return 0, []

        margin_per_position = allocatable_margin / len(filtered_signals)
        return margin_per_position, filtered_signals

    return margin_per_position, signals


# =============================================================================
# ACTION VALIDATION
# =============================================================================

VALID_ALLOCATION_ACTIONS = ["OPEN_LONG", "OPEN_SHORT", "INCREASE", "REDUCE", "CLOSE"]


def validate_allocation_action(
    action: Dict[str, Any],
    valid_symbols: List[str]
) -> Tuple[bool, str]:
    """
    Validate a single allocation action.

    Args:
        action: Action dict with symbol, action, margin_usd, etc.
        valid_symbols: List of valid trading symbols

    Returns:
        Tuple of (is_valid, rejection_reason)
    """
    if not isinstance(action, dict):
        return False, "not a dict"

    sym = action.get("symbol", "")
    act = action.get("action", "")

    if not sym:
        return False, "missing symbol"

    if sym not in valid_symbols:
        return False, f"{sym}: unknown symbol"

    if act not in VALID_ALLOCATION_ACTIONS:
        return False, f"{sym}: invalid action {act}"

    # Size validation for position-opening actions
    if act in ["OPEN_LONG", "OPEN_SHORT", "INCREASE"]:
        if action.get("margin_usd", 0) <= 0:
            return False, f"{sym}: margin_usd <= 0"

    if act == "REDUCE":
        if action.get("reduce_by_usd", 0) <= 0:
            return False, f"{sym}: reduce_by_usd <= 0"

    return True, ""


def validate_allocation_actions(
    actions: List[Dict[str, Any]],
    valid_symbols: List[str],
    normalizer_func=None
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """
    Validate a list of allocation actions.

    Args:
        actions: List of action dicts
        valid_symbols: List of valid trading symbols
        normalizer_func: Optional function to normalize symbols

    Returns:
        Tuple of (valid_actions, rejection_counts)
    """
    valid_actions = []
    rejected = {}

    def reject(reason):
        rejected[reason] = rejected.get(reason, 0) + 1

    for action in actions:
        if not isinstance(action, dict):
            reject("not a dict")
            continue

        # Normalize symbol if function provided
        if normalizer_func:
            raw_sym = action.get("symbol", "")
            normalized = normalizer_func(raw_sym, valid_symbols)
            action["symbol"] = normalized

        is_valid, reason = validate_allocation_action(action, valid_symbols)
        if is_valid:
            valid_actions.append(action)
        else:
            reject(reason)

    return valid_actions, rejected


# =============================================================================
# ACTION SORTING
# =============================================================================

ACTION_PRIORITY = {
    "CLOSE": 0,
    "REDUCE": 1,
    "OPEN_LONG": 2,
    "OPEN_SHORT": 2,
    "INCREASE": 3
}


def sort_allocation_actions(actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sort allocation actions by execution priority.

    Order: CLOSE first, then REDUCE, then OPEN/INCREASE.
    This ensures we free up capital before opening new positions.

    Args:
        actions: List of action dicts

    Returns:
        Sorted list of action dicts
    """
    return sorted(actions, key=lambda x: ACTION_PRIORITY.get(x.get("action", ""), 5))


# =============================================================================
# REBALANCE PLANNING
# =============================================================================

def plan_rebalance_closes(
    open_positions: Dict[str, Dict[str, Any]],
    target_allocations: List[Dict[str, Any]],
    leverage: float,
    min_notional: float = 12.0,
    tolerance: float = 1.05
) -> List[Dict[str, Any]]:
    """
    Plan CLOSE/REDUCE actions to free margin for new allocations.

    Args:
        open_positions: Dict of symbol -> {margin_usd, direction}
        target_allocations: List of target allocation actions
        leverage: Current leverage setting
        min_notional: Minimum order notional
        tolerance: Tolerance factor before reducing (e.g., 1.05 = 5%)

    Returns:
        List of CLOSE/REDUCE actions sorted by priority
    """
    actions = []

    # Build target map: symbol -> target_margin
    target_map = {}
    for a in target_allocations:
        if not isinstance(a, dict):
            continue
        sym = a.get("symbol")
        if not sym:
            continue
        if a.get("action") in ("OPEN_LONG", "OPEN_SHORT", "INCREASE"):
            target_map[sym] = float(a.get("margin_usd", 0))

    min_margin = min_notional / leverage

    for sym, pos in open_positions.items():
        current_margin = float(pos.get("margin_usd", 0))
        target_margin = float(target_map.get(sym, 0))

        # If not in target_map -> close entire position
        if sym not in target_map:
            if current_margin >= min_margin:
                actions.append({
                    "symbol": sym,
                    "action": "CLOSE",
                    "reason": "Rebalance: not in target allocations"
                })
            continue

        # If current margin significantly exceeds target -> reduce
        if current_margin > (target_margin * tolerance):
            reduce_by = round(current_margin - target_margin, 2)

            if reduce_by >= min_margin:
                actions.append({
                    "symbol": sym,
                    "action": "REDUCE",
                    "reduce_by_usd": reduce_by,
                    "reason": f"Rebalance: reduce from {current_margin} to {target_margin}"
                })
            elif target_margin == 0 and current_margin >= min_margin:
                # Target is zero but current is meaningful -> close
                actions.append({
                    "symbol": sym,
                    "action": "CLOSE",
                    "reason": "Rebalance: close small position to free margin"
                })

    # Sort: CLOSE first, then REDUCE
    return sort_allocation_actions(actions)


# =============================================================================
# FALLBACK ALLOCATION BUILDING
# =============================================================================

def build_fallback_allocation_actions(
    signals: List[Dict[str, Any]],
    margin_per_position: float
) -> List[Dict[str, Any]]:
    """
    Build allocation actions for fallback equal distribution.

    Args:
        signals: List of filtered signals with symbol, action, confidence
        margin_per_position: Calculated margin per position

    Returns:
        List of allocation action dicts
    """
    actions = []
    for sig in signals:
        action_type = "OPEN_LONG" if sig["action"] == "BUY" else "OPEN_SHORT"
        actions.append({
            "symbol": sig["symbol"],
            "action": action_type,
            "margin_usd": round(margin_per_position, 2),
            "reason": f"Fallback: {sig['action']} signal ({sig.get('confidence', 50)}% confidence)"
        })
    return actions


# =============================================================================
# POSITION ALIGNMENT CHECK
# =============================================================================

def check_position_alignment(
    signal_action: str,
    position_direction: str
) -> bool:
    """
    Check if a signal aligns with an existing position.

    Args:
        signal_action: "BUY" or "SELL"
        position_direction: "LONG" or "SHORT"

    Returns:
        True if aligned (BUY+LONG or SELL+SHORT), False otherwise
    """
    return (
        (signal_action == "BUY" and position_direction == "LONG") or
        (signal_action == "SELL" and position_direction == "SHORT")
    )


def filter_signals_by_position_alignment(
    signals: List[Dict[str, Any]],
    open_positions: Dict[str, Dict[str, Any]],
    recently_closed: Dict[str, float],
    current_time: float,
    grace_period: float = 15.0,
    min_margin: float = 12.0
) -> List[Dict[str, Any]]:
    """
    Filter signals based on position alignment and recent closures.

    Args:
        signals: List of signal dicts
        open_positions: Dict of symbol -> {margin_usd, direction}
        recently_closed: Dict of symbol -> closure timestamp
        current_time: Current timestamp
        grace_period: Seconds after closure to allow re-entry
        min_margin: Minimum margin to consider position significant

    Returns:
        Filtered list of signals
    """
    filtered = []

    for sig in signals:
        sym = sig.get("symbol", "")

        if sym not in open_positions:
            filtered.append(sig)
            continue

        pos = open_positions[sym]
        pos_margin = pos.get("margin_usd", 0)

        # Tiny position: treat as flat
        if pos_margin < min_margin:
            filtered.append(sig)
            continue

        # Recently closed: check grace period
        if sym in recently_closed:
            closed_ts = recently_closed.get(sym, 0)
            if (current_time - closed_ts) < grace_period:
                # Within grace window: treat as flat
                filtered.append(sig)
                continue

        # Check alignment
        if check_position_alignment(sig.get("action", ""), pos.get("direction", "")):
            # Already aligned: skip
            continue

        # Not aligned: allow (could be a reversal signal)
        filtered.append(sig)

    return filtered


# =============================================================================
# OPEN POSITIONS COLLECTION
# =============================================================================

def collect_open_positions(
    symbols: List[str],
    get_position_fn,
    account,
    leverage: float
) -> Dict[str, Dict[str, Any]]:
    """
    Collect current open positions for all symbols.

    Args:
        symbols: List of symbols to check
        get_position_fn: Function to get position (e.g., n.get_position)
        account: Account object
        leverage: Trading leverage

    Returns:
        Dict mapping symbol to position info (direction, margin_usd, pnl_percent)
    """
    open_positions = {}

    for sym in symbols:
        try:
            pos_data = get_position_fn(sym, account)
            _, im_in_pos, pos_size, _, entry_px, pnl_pct, is_long = pos_data

            if im_in_pos and pos_size != 0:
                notional = abs(float(pos_size) * float(entry_px))
                margin = notional / leverage
                open_positions[sym] = {
                    "direction": "LONG" if is_long else "SHORT",
                    "margin_usd": round(margin, 2),
                    "pnl_percent": round(float(pnl_pct), 2),
                }
        except Exception:
            continue

    return open_positions


# =============================================================================
# AI ALLOCATION ACTION VALIDATION
# =============================================================================

def validate_single_allocation_action(
    action: Dict[str, Any],
    symbols: List[str],
    normalize_symbol_fn,
    risk_manager=None,
    total_equity: float = 0,
    get_price_fn=None
) -> Tuple[bool, Dict[str, Any], Optional[str]]:
    """
    Validate a single AI allocation action.

    Args:
        action: Action dict from AI
        symbols: List of valid symbols
        normalize_symbol_fn: Function to normalize symbol names
        risk_manager: Optional risk manager for additional validation
        total_equity: Total account equity (for risk validation)
        get_price_fn: Function to get current price (for risk validation)

    Returns:
        Tuple of (is_valid, normalized_action, rejection_reason)
    """
    if not isinstance(action, dict):
        return False, action, "not a dict"

    raw_sym = action.get("symbol", "")
    act = action.get("action")

    # Normalize symbol
    sym = normalize_symbol_fn(raw_sym)
    action["symbol"] = sym

    if sym not in symbols:
        reason = f"{raw_sym}: unknown symbol" + (f" (normalized: {sym})" if sym != raw_sym else "")
        return False, action, reason

    if act not in VALID_ALLOCATION_ACTIONS:
        return False, action, f"{sym}: invalid action {act}"

    # Size validation for opening actions
    if act in ["OPEN_LONG", "OPEN_SHORT", "INCREASE"]:
        if action.get("margin_usd", 0) <= 0:
            return False, action, f"{sym}: margin_usd <= 0"

    if act == "REDUCE":
        if action.get("reduce_by_usd", 0) <= 0:
            return False, action, f"{sym}: reduce_by_usd <= 0"

    # Risk validation if manager available
    if risk_manager:
        try:
            conf = action.get("confidence", 50) / 100.0
            # Get entry price
            try:
                entry_price = get_price_fn(sym) if get_price_fn else 100.0
            except Exception:
                entry_price = 100.0

            verdict = risk_manager.validate_trade_decision(
                symbol=sym,
                action=act,
                confidence=conf,
                entry_price=entry_price,
                account_balance=total_equity,
            )
            if not verdict.get("valid", False):
                reason = verdict.get("reason", verdict.get("message", "unknown"))
                return False, action, f"{sym}: risk rejected ({reason})"
        except Exception as e:
            return False, action, f"{sym}: risk error {e}"

    return True, action, None


def validate_ai_allocation_actions(
    actions: List[Any],
    symbols: List[str],
    normalize_symbol_fn,
    risk_manager=None,
    total_equity: float = 0,
    get_price_fn=None
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """
    Validate all AI allocation actions.

    Args:
        actions: List of actions from AI response
        symbols: List of valid symbols
        normalize_symbol_fn: Function to normalize symbol names
        risk_manager: Optional risk manager
        total_equity: Total account equity
        get_price_fn: Function to get current price

    Returns:
        Tuple of (valid_actions, rejected_counts_by_reason)
    """
    valid_actions = []
    rejected = {}

    for action in actions:
        is_valid, normalized_action, reason = validate_single_allocation_action(
            action, symbols, normalize_symbol_fn, risk_manager, total_equity, get_price_fn
        )

        if is_valid:
            valid_actions.append(normalized_action)
        else:
            rejected[reason] = rejected.get(reason, 0) + 1
            cprint(f"   {reason}", "yellow")

    return valid_actions, rejected


def log_allocation_rejections(
    valid_count: int,
    rejected: Dict[str, int]
) -> None:
    """
    Log allocation rejections with summary.

    Args:
        valid_count: Number of valid actions
        rejected: Dict mapping reason to count
    """
    total_rejected = sum(rejected.values())

    if rejected:
        cprint(f"\nAI Actions: {valid_count} valid, {total_rejected} rejected", "yellow")
        for reason, count in rejected.items():
            cprint(f"   - {reason} (x{count})", "white")

        if valid_count > 0:
            add_console_log(f"AI allocation: {valid_count} valid, {total_rejected} rejected", "info")
        else:
            add_console_log(f"AI allocation: {total_rejected} action(s) rejected", "warning")
