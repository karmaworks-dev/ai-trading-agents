"""
Position Analysis Functions for Trading Agent

This module contains standalone functions for analyzing open positions,
checking TP/SL thresholds, and validating AI close decisions.

All functions are stateless and take explicit parameters
to enable easier testing and reuse.
"""

import json
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

# Import trade executor helpers
from .trade_executor import should_trigger_stop_loss, should_trigger_take_profit
from .market_analyzer import extract_json_from_text


# =============================================================================
# POSITION LOGGING
# =============================================================================

def log_positions_being_analyzed(positions_data: Dict[str, List[Dict[str, Any]]]) -> None:
    """
    Log positions being analyzed with visual formatting.

    Args:
        positions_data: Dict mapping symbol to list of position dicts
    """
    cprint("\n" + "=" * 60, "yellow")
    cprint("AI ANALYZING OPEN POSITIONS", "white", "on_magenta", attrs=["bold"])
    cprint("=" * 60, "yellow")

    for symbol, positions in positions_data.items():
        for pos in positions:
            side = "LONG" if pos.get("is_long", True) else "SHORT"
            entry = pos.get("entry_price", 0)
            pnl = pos.get("pnl_percent", 0)
            pnl_emoji = "+" if pnl >= 0 else ""
            add_console_log(f"   {symbol} ({side}) | Entry: ${entry:.2f} | PnL: {pnl_emoji}{pnl:.2f}%", "info")


# =============================================================================
# TP/SL THRESHOLD CHECKING
# =============================================================================

def check_tp_sl_force_closes(
    positions_data: Dict[str, List[Dict[str, Any]]],
    take_profit_threshold: float,
    stop_loss_threshold: float
) -> Dict[str, Dict[str, Any]]:
    """
    Check TP/SL thresholds and return forced close decisions.

    Args:
        positions_data: Dict mapping symbol to list of position dicts
        take_profit_threshold: TP threshold (e.g., 6.0 for 6%)
        stop_loss_threshold: SL threshold (e.g., -2.0 for -2%)

    Returns:
        Dict of forced close decisions
    """
    forced_decisions = {}

    for symbol, positions in positions_data.items():
        for pos in positions:
            pnl_percent = pos.get("pnl_percent", 0)

            # Check Take Profit
            if should_trigger_take_profit(pnl_percent, take_profit_threshold):
                reason = f"TAKE PROFIT: {pnl_percent:.2f}% >= {take_profit_threshold}%"
                forced_decisions[symbol] = {"action": "CLOSE", "reasoning": reason, "confidence": 100}
                cprint(f"TAKE PROFIT TRIGGERED: {symbol} at {pnl_percent:.2f}%", "red", attrs=["bold"])
                add_console_log(f"TAKE PROFIT: Closing {symbol} at +{pnl_percent:.2f}%", "success")

            # Check Stop Loss
            elif should_trigger_stop_loss(pnl_percent, stop_loss_threshold):
                reason = f"STOP LOSS: {pnl_percent:.2f}% <= {stop_loss_threshold}%"
                forced_decisions[symbol] = {"action": "CLOSE", "reasoning": reason, "confidence": 100}
                cprint(f"STOP LOSS TRIGGERED: {symbol} at {pnl_percent:.2f}%", "red", attrs=["bold"])
                add_console_log(f"STOP LOSS: Closing {symbol} at {pnl_percent:.2f}%", "warning")

    return forced_decisions


# =============================================================================
# POSITION SUMMARY BUILDING
# =============================================================================

def build_position_summary_for_ai(
    positions_data: Dict[str, List[Dict[str, Any]]],
    skip_symbols: set = None
) -> List[Dict[str, Any]]:
    """
    Build position summary for AI analysis prompt.

    Args:
        positions_data: Dict mapping symbol to list of position dicts
        skip_symbols: Set of symbols to skip (already handled by TP/SL)

    Returns:
        List of position summary dicts
    """
    skip_symbols = skip_symbols or set()
    position_summary = []

    for symbol, positions in positions_data.items():
        if symbol in skip_symbols:
            continue

        for pos in positions:
            position_summary.append({
                "symbol": symbol,
                "side": "LONG" if pos.get("is_long", True) else "SHORT",
                "size": pos.get("size", 0),
                "entry_price": pos.get("entry_price", 0),
                "current_pnl": pos.get("pnl_percent", 0),
                "age_hours": pos.get("age_hours", 0),
            })

    return position_summary


def build_market_summary_for_positions(
    market_data: Dict[str, Any],
    positions_data: Dict[str, List[Dict[str, Any]]],
    skip_symbols: set = None
) -> Dict[str, Dict[str, Any]]:
    """
    Build market summary for positions being analyzed.

    Args:
        market_data: Dict mapping symbol to DataFrame of market data
        positions_data: Dict mapping symbol to position data
        skip_symbols: Set of symbols to skip

    Returns:
        Dict mapping symbol to market summary
    """
    skip_symbols = skip_symbols or set()
    market_summary = {}

    for symbol in positions_data.keys():
        if symbol in skip_symbols:
            continue

        if symbol not in market_data:
            continue

        df = market_data[symbol]
        if df is None or (hasattr(df, 'empty') and df.empty):
            continue

        latest = df.iloc[-1] if hasattr(df, 'iloc') else df

        # Robustly detect the correct close column
        current_price = None
        for col in ["Close", "close", "close_price", "c", "price"]:
            if col in df.columns if hasattr(df, 'columns') else col in df:
                current_price = latest[col] if hasattr(latest, '__getitem__') else getattr(latest, col, None)
                break

        if current_price is None:
            cprint(f"No close price column found for {symbol}, skipping...", "yellow")
            continue

        ma20 = latest.get("MA20", 0) if hasattr(latest, 'get') else getattr(latest, 'MA20', 0)
        ma40 = latest.get("MA40", 0) if hasattr(latest, 'get') else getattr(latest, 'MA40', 0)
        rsi = latest.get("RSI", 0) if hasattr(latest, 'get') else getattr(latest, 'RSI', 0)

        market_summary[symbol] = {
            "current_price": current_price,
            "ma20": ma20,
            "ma40": ma40,
            "rsi": rsi,
            "trend": "Bullish" if current_price > ma20 else "Bearish",
        }

    return market_summary


# =============================================================================
# AI RESPONSE PARSING
# =============================================================================

def build_position_analysis_prompt(
    position_summary: List[Dict[str, Any]],
    market_summary: Dict[str, Dict[str, Any]]
) -> str:
    """
    Build user prompt for position analysis.

    Args:
        position_summary: List of position summaries
        market_summary: Dict of market summaries

    Returns:
        Formatted prompt string
    """
    return f"""Analyze these open positions:

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


def strip_markdown_code_blocks(response: str) -> str:
    """
    Strip Markdown code fences from AI response.

    Args:
        response: Raw AI response

    Returns:
        Response with code blocks stripped
    """
    if "```json" in response:
        response = response.split("```json")[1].split("```")[0]
    elif "```" in response:
        response = response.split("```")[1].split("```")[0]
    return response


def parse_position_analysis_response(
    response: str,
    position_summary: List[Dict[str, Any]]
) -> Optional[Dict[str, Dict[str, Any]]]:
    """
    Parse AI response for position analysis with fallback.

    Args:
        response: AI response text
        position_summary: List of position summaries (for fallback parsing)

    Returns:
        Dict of decisions or None if parsing failed
    """
    if not response:
        cprint("No response from AI for position analysis", "red")
        return None

    # Strip code blocks
    cleaned_response = strip_markdown_code_blocks(response)

    # Try JSON extraction first
    decisions = extract_json_from_text(cleaned_response)

    if decisions:
        return decisions

    # Fallback: keyword-based parsing
    cprint("AI response not valid JSON. Attempting text fallback...", "yellow")

    text = response.lower()
    decisions = {}

    for pos in position_summary:
        sym = pos["symbol"]
        if sym.lower() in text:
            if "close" in text or "sell" in text:
                decisions[sym] = {
                    "action": "CLOSE",
                    "reasoning": "Detected CLOSE or SELL keyword in fallback parsing.",
                    "confidence": 60
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

    cprint(f"Fallback interpreted decisions: {decisions}", "cyan")
    return decisions if decisions else None


# =============================================================================
# VALIDATION
# =============================================================================

def validate_ai_close_decisions(
    decisions: Dict[str, Dict[str, Any]],
    positions_data: Dict[str, List[Dict[str, Any]]],
    validate_close_fn
) -> Dict[str, Dict[str, Any]]:
    """
    Apply 3-tier validation to AI close decisions.

    Args:
        decisions: Dict of AI decisions
        positions_data: Dict mapping symbol to position data
        validate_close_fn: Function to validate close decision

    Returns:
        Dict of validated decisions
    """
    cprint("\n" + "=" * 60, "magenta")
    cprint("APPLYING 3-TIER VALIDATION SYSTEM", "white", "on_magenta", attrs=["bold"])
    cprint("=" * 60, "magenta")

    validated_decisions = {}

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
            should_close, validation_reason = validate_close_fn(
                symbol, pnl_percent, age_hours, ai_confidence
            )

            if should_close:
                validated_decisions[symbol] = {
                    "action": "CLOSE",
                    "reasoning": f"{reason} | Validation: {validation_reason}",
                    "confidence": ai_confidence
                }
                cprint(f"{symbol}: CLOSE APPROVED", "green", attrs=["bold"])
            else:
                validated_decisions[symbol] = {
                    "action": "KEEP",
                    "reasoning": f"AI suggested CLOSE but validation BLOCKED: {validation_reason}",
                    "confidence": 0
                }
                cprint(f"{symbol}: CLOSE BLOCKED -> FORCING KEEP", "cyan", attrs=["bold"])
                add_console_log(f"{symbol} CLOSE blocked: {validation_reason}", "warning")
        else:
            # KEEP decision - no validation needed
            validated_decisions[symbol] = decision

    return validated_decisions


# =============================================================================
# OUTPUT LOGGING
# =============================================================================

def log_final_decisions(validated_decisions: Dict[str, Dict[str, Any]]) -> None:
    """
    Log final validated decisions with visual formatting.

    Args:
        validated_decisions: Dict of validated decisions
    """
    cprint("\n" + "=" * 60, "magenta")
    cprint("FINAL VALIDATED DECISIONS:", "white", "on_magenta", attrs=["bold"])
    cprint("=" * 60, "magenta")

    for symbol, decision in validated_decisions.items():
        action = decision.get("action", "UNKNOWN")
        reason = decision.get("reasoning", "")
        confidence = decision.get("confidence", 0)
        color = "red" if action.upper() == "CLOSE" else "green"
        cprint(f"   {symbol:<10} -> {action:<6} | {reason}", color)

        # Log for dashboard
        if action.upper() == "CLOSE":
            add_console_log(f"{symbol} -> CLOSE ({confidence}% Sure)", "warning")
        else:
            add_console_log(f"{symbol} -> KEEP", "info")

    cprint("=" * 60 + "\n", "magenta")


# =============================================================================
# ORCHESTRATION
# =============================================================================

def analyze_positions_with_ai(
    positions_data: Dict[str, List[Dict[str, Any]]],
    market_data: Dict[str, Any],
    take_profit_threshold: float,
    stop_loss_threshold: float,
    chat_fn,
    system_prompt: str,
    validate_close_fn
) -> Dict[str, Dict[str, Any]]:
    """
    Analyze open positions using AI with TP/SL enforcement.

    This is the main orchestration function that combines all helpers.

    Args:
        positions_data: Dict mapping symbol to list of position dicts
        market_data: Dict mapping symbol to market data DataFrame
        take_profit_threshold: TP threshold percentage
        stop_loss_threshold: SL threshold percentage
        chat_fn: Function to chat with AI
        system_prompt: System prompt for position analysis
        validate_close_fn: Function to validate close decisions

    Returns:
        Dict of validated decisions
    """
    if not positions_data:
        return {}

    # Step 1: Log positions
    log_positions_being_analyzed(positions_data)

    # Step 2: Check TP/SL thresholds (force close)
    validated_decisions = check_tp_sl_force_closes(
        positions_data, take_profit_threshold, stop_loss_threshold
    )
    handled_symbols = set(validated_decisions.keys())

    # Step 3: Build summaries for remaining positions
    position_summary = build_position_summary_for_ai(positions_data, handled_symbols)
    market_summary = build_market_summary_for_positions(market_data, positions_data, handled_symbols)

    # Step 4: Get AI analysis for remaining positions
    if position_summary:
        user_prompt = build_position_analysis_prompt(position_summary, market_summary)

        try:
            response = chat_fn(system_prompt, user_prompt)

            if not response:
                return validated_decisions

            decisions = parse_position_analysis_response(response, position_summary)

            if not decisions:
                cprint("Could not interpret AI analysis at all.", "red")
                return validated_decisions

            # Step 5: Validate AI decisions
            ai_validated = validate_ai_close_decisions(
                decisions, positions_data, validate_close_fn
            )
            validated_decisions.update(ai_validated)

        except Exception as e:
            cprint(f"Error in AI analysis: {e}", "red")
            import traceback
            traceback.print_exc()

    # Step 6: Log final decisions
    log_final_decisions(validated_decisions)

    return validated_decisions
