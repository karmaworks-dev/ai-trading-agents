"""
Market Analysis Functions for Trading Agent

This module contains standalone functions for market data analysis,
response parsing, and context formatting.

All functions are stateless and take explicit parameters
to enable easier testing and reuse.
"""

import re
import json
from typing import Dict, Any, Tuple, Optional, List

# Import logging utilities with fallback
try:
    from src.utils.logging_utils import add_console_log
except ImportError:
    def add_console_log(message, level="info", console_file=None):
        print(f"[MARKET] {message}")

# Import termcolor with fallback
try:
    from termcolor import cprint
except ImportError:
    def cprint(msg, *args, **kwargs):
        print(msg)


# =============================================================================
# JSON EXTRACTION
# =============================================================================

def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Safely extract JSON object from AI model responses containing text.

    Args:
        text: Raw text that may contain JSON embedded in prose

    Returns:
        Parsed JSON dict or None if extraction fails
    """
    if not text:
        return None

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            cprint("⚠️ JSON extraction failed even after matching braces.", "yellow")
            return None
    cprint("⚠️ No JSON object found in AI response.", "yellow")
    return None


# =============================================================================
# POSITION CONTEXT FORMATTING
# =============================================================================

def format_position_context(
    is_in_position: bool,
    is_long: bool = True,
    size: float = 0,
    entry_price: float = 0,
    pnl_percent: float = 0
) -> str:
    """
    Format position data into a context string for AI prompts.

    Args:
        is_in_position: Whether there's an active position
        is_long: True for long, False for short
        size: Position size
        entry_price: Entry price
        pnl_percent: Current P&L percentage

    Returns:
        Formatted position context string
    """
    if not is_in_position:
        return "CURRENT POSITION: None (You have no exposure)."

    side = "LONG" if is_long else "SHORT"

    # Spot position (no entry price or pnl)
    if entry_price == 0 and pnl_percent == 0:
        return f"CURRENT POSITION: ✅ Active {side} (Spot) | Size: {size}"

    # Perpetual position with full info
    return (
        f"CURRENT POSITION: ✅ Active {side} | "
        f"Size: {size} | Entry: ${entry_price:.4f} | "
        f"PnL: {pnl_percent:.2f}%"
    )


def format_performance_context(metrics: Dict[str, Any]) -> str:
    """
    Format performance metrics into a context string for AI motivation.

    Args:
        metrics: Dict with win_rate, total_pnl, grade, winning_trades, total_trades

    Returns:
        Formatted performance context string
    """
    return (
        f"Win Rate: {metrics.get('win_rate', 0)}% | "
        f"Total PnL: ${metrics.get('total_pnl', 0)} | "
        f"Grade: {metrics.get('grade', 'UNKNOWN')} | "
        f"Recent Trades: {metrics.get('winning_trades', 0)}/{metrics.get('total_trades', 0)}"
    )


# =============================================================================
# STRATEGY CONTEXT FORMATTING
# =============================================================================

def format_strategy_context_text(strategy_context: Optional[Dict[str, Any]]) -> Tuple[str, Dict[str, Any]]:
    """
    Format strategy context into text for AI prompts.

    Args:
        strategy_context: Strategy context dict from StrategyAgent

    Returns:
        Tuple of (formatted_text, original_context_dict)
    """
    if not strategy_context:
        return "No strategy intelligence available.", {}

    lines = []

    lines.append("STRATEGY INTELLIGENCE (JSON)")
    lines.append(json.dumps(strategy_context, indent=2))

    aggregate = strategy_context.get("aggregate", {})

    lines.append("\nSTRATEGY SUMMARY")
    lines.append(f"- Direction bias: {aggregate.get('direction_bias')}")
    lines.append(f"- Confidence: {aggregate.get('confidence')}")
    lines.append(
        f"- Suggested allocation (%): "
        f"{aggregate.get('suggested_allocation_pct')}"
    )
    lines.append(f"- Conflict level: {aggregate.get('conflict_level')}")
    lines.append(f"- Timestamp: {strategy_context.get('timestamp')}")

    return "\n".join(lines), strategy_context


def format_legacy_strategy_signals(market_data: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """
    Format legacy strategy signals from market_data dict.

    Args:
        market_data: Market data dict that may contain 'strategy_signals'

    Returns:
        Tuple of (formatted_text, context_dict)
    """
    if not isinstance(market_data, dict) or "strategy_signals" not in market_data:
        return "No strategy intelligence available.", {}

    try:
        strategy_context_text = (
            "Strategy Signals Available:\n" +
            json.dumps(market_data["strategy_signals"], indent=2)
        )
        strategy_context_json = {"legacy_signals": market_data["strategy_signals"]}
    except Exception:
        strategy_context_text = "Strategy Signals Available (unserializable)."
        strategy_context_json = {"legacy_signals": str(market_data.get("strategy_signals"))}

    return strategy_context_text, strategy_context_json


# =============================================================================
# RESPONSE PARSING
# =============================================================================

def parse_single_model_response(response: str) -> Tuple[str, int, str]:
    """
    Parse a single model AI response into action, confidence, and reasoning.

    Expected format:
    Line 1: Action (BUY, SELL, or NOTHING)
    Remaining lines: Reasoning (may include confidence percentage)

    Args:
        response: Raw AI response text

    Returns:
        Tuple of (action, confidence, reasoning)
    """
    if not response:
        return "NOTHING", 0, "No response from AI"

    lines = response.split("\n")
    action = lines[0].strip().upper() if lines else "NOTHING"

    # Normalize action
    if action not in ["BUY", "SELL", "NOTHING"]:
        # Try to extract action from first line
        if "BUY" in action:
            action = "BUY"
        elif "SELL" in action:
            action = "SELL"
        else:
            action = "NOTHING"

    # Extract confidence from response
    confidence = extract_confidence_from_text(response)

    # Build reasoning from remaining lines
    reasoning = (
        "\n".join(lines[1:]) if len(lines) > 1 else "No detailed reasoning provided"
    )

    return action, confidence, reasoning


def extract_confidence_from_text(text: str) -> int:
    """
    Extract confidence percentage from AI response text.

    Looks for patterns like "82% confidence", "confidence: 75%", etc.

    Args:
        text: Text to search for confidence value

    Returns:
        Confidence value (0-100), defaults to 50 if not found
    """
    for line in text.split("\n"):
        if "confidence" in line.lower():
            try:
                # Extract first percentage number (handles "82% confidence" correctly)
                match = re.search(r'(\d{1,3})\s*%', line)
                if match:
                    return min(100, max(0, int(match.group(1))))
                else:
                    # Fallback: first standalone number
                    match = re.search(r'\b(\d{1,3})\b', line)
                    if match:
                        return min(100, max(0, int(match.group(1))))
            except Exception:
                pass
    return 50  # Default confidence


# =============================================================================
# CONFIDENCE THRESHOLD APPLICATION
# =============================================================================

def apply_confidence_threshold(
    action: str,
    confidence: int,
    min_confidence: int,
    reasoning: str = ""
) -> Tuple[str, str]:
    """
    Apply confidence threshold to trading action.

    If action is BUY or SELL but confidence is below threshold,
    downgrades to NOTHING with updated reasoning.

    Args:
        action: Original action (BUY, SELL, or NOTHING)
        confidence: Confidence level (0-100)
        min_confidence: Minimum confidence threshold
        reasoning: Original reasoning text

    Returns:
        Tuple of (final_action, updated_reasoning)
    """
    if action in ["BUY", "SELL"] and confidence < min_confidence:
        cprint(
            f"⚠️ LOW CONFIDENCE: {confidence}% < {min_confidence}% threshold",
            "yellow",
            attrs=["bold"]
        )
        cprint(f"   → Downgrading {action} to NOTHING", "yellow")

        updated_reasoning = (
            f"Original: {action} ({confidence}%) → Downgraded to NOTHING "
            f"(below {min_confidence}% threshold)\n\n{reasoning}"
        )
        return "NOTHING", updated_reasoning

    return action, reasoning


# =============================================================================
# RECOMMENDATION BUILDING
# =============================================================================

def build_recommendation(
    token: str,
    action: str,
    confidence: int,
    reasoning: str
) -> Dict[str, Any]:
    """
    Build a standardized recommendation dictionary.

    Args:
        token: Token symbol
        action: Trading action (BUY, SELL, NOTHING)
        confidence: Confidence level (0-100)
        reasoning: Reasoning text

    Returns:
        Recommendation dictionary
    """
    return {
        "token": token,
        "action": action,
        "confidence": confidence,
        "reasoning": reasoning,
    }


def build_error_recommendation(token: str, error: str) -> Dict[str, Any]:
    """
    Build a recommendation for error cases.

    Args:
        token: Token symbol
        error: Error message

    Returns:
        Error recommendation dictionary
    """
    return {
        "token": token,
        "action": "NOTHING",
        "confidence": 0,
        "reasoning": f"Error during analysis: {error}",
    }


# =============================================================================
# MARKET DATA VALIDATION
# =============================================================================

def validate_market_data(market_data, token: str) -> bool:
    """
    Validate that market data is usable for analysis.

    Args:
        market_data: DataFrame or dict of market data
        token: Token symbol (for error messages)

    Returns:
        True if valid, False otherwise
    """
    if market_data is None:
        cprint(f"⚠️ No market data for {token}", "yellow")
        return False

    # Check if DataFrame
    try:
        import pandas as pd
        if isinstance(market_data, pd.DataFrame):
            if market_data.empty:
                cprint(f"⚠️ Empty DataFrame for {token}", "yellow")
                return False
            return True
    except ImportError:
        pass

    # Check if dict
    if isinstance(market_data, dict):
        return len(market_data) > 0

    return True


def get_token_from_market_data(market_data, default_token: str) -> str:
    """
    Extract token name from market data dict.

    Args:
        market_data: Market data (DataFrame or dict)
        default_token: Default token name if not found

    Returns:
        Token name
    """
    if isinstance(market_data, dict):
        return market_data.get("symbol") or market_data.get("token") or default_token
    return default_token


# =============================================================================
# ANALYSIS ORCHESTRATION FUNCTIONS
# =============================================================================

def prepare_analysis_context(
    token: str,
    get_position_fn,
    account,
    performance_metrics: Dict[str, Any]
) -> Tuple[str, str]:
    """
    Prepare position and performance context strings for AI analysis.

    Args:
        token: Token symbol
        get_position_fn: Function to get position data (e.g., n.get_position)
        account: Account object for position lookup
        performance_metrics: Dict with win_rate, total_pnl, grade, etc.

    Returns:
        Tuple of (position_context, performance_context)
    """
    # Format position context
    position_context = "CURRENT POSITION: None (You have no exposure)."

    try:
        raw_pos_data = get_position_fn(token, account)
        _, im_in_pos, pos_size, _, entry_px, pnl_perc, is_long = raw_pos_data

        if im_in_pos:
            position_context = format_position_context(
                is_in_position=True,
                is_long=is_long,
                size=pos_size,
                entry_price=entry_px,
                pnl_percent=pnl_perc
            )
    except Exception as e:
        cprint(f"⚠️ Error fetching position context: {e}", "yellow")

    cprint(f"   ℹ️  Context: {position_context}", "cyan")

    # Format performance context
    performance_context = format_performance_context(performance_metrics)

    return position_context, performance_context


def analyze_market_swarm(
    token: str,
    market_data,
    swarm,
    position_context: str,
    performance_context: str,
    format_market_data_fn,
    calculate_consensus_fn,
    swarm_prompt_template: str
) -> Tuple[Optional[Dict[str, Any]], Optional[Any]]:
    """
    Analyze market using swarm mode (multiple AI models voting).

    Args:
        token: Token symbol
        market_data: Market data to analyze
        swarm: Swarm object with query() method
        position_context: Formatted position context string
        performance_context: Formatted performance context string
        format_market_data_fn: Function to format market data for swarm
        calculate_consensus_fn: Function to calculate swarm consensus
        swarm_prompt_template: Template string with {performance_context} placeholder

    Returns:
        Tuple of (recommendation_dict, raw_swarm_result)
    """
    num_models = len(swarm.active_models) if swarm else 6
    cprint(
        f"\n🌊 Analyzing {token[:8]}... with SWARM ({num_models} AI models voting)",
        "cyan",
        attrs=["bold"],
    )

    base_market_data = format_market_data_fn(token, market_data)
    formatted_data = f"{position_context}\n\n{base_market_data}"

    swarm_result = swarm.query(
        prompt=formatted_data,
        system_prompt=swarm_prompt_template.format(performance_context=performance_context)
    )

    if not swarm_result:
        cprint(f"❌ No response from swarm for {token}", "red")
        return None, None

    action, confidence, reasoning = calculate_consensus_fn(swarm_result)

    recommendation = build_recommendation(token, action, confidence, reasoning)

    cprint(f"✅ Swarm analysis complete for {token[:8]}!", "green")
    add_console_log(f"✅ Swarm  {token} -> {action} | {confidence}% Sure", "success")

    return recommendation, swarm_result


def prepare_strategy_context(
    token: str,
    market_data,
    get_cached_strategy_fn,
    format_strategy_context_fn
) -> Tuple[str, Dict[str, Any]]:
    """
    Prepare strategy context for single model analysis.

    Args:
        token: Token symbol
        market_data: Market data that may contain legacy strategy_signals
        get_cached_strategy_fn: Function to get cached strategy context
        format_strategy_context_fn: Function to format strategy context

    Returns:
        Tuple of (strategy_context_text, strategy_context_json)
    """
    token_name = get_token_from_market_data(market_data, token)

    strategy_context_text = "No strategy intelligence available."
    strategy_context_json = {}

    # Try to get enriched context from StrategyAgent (cached)
    try:
        strat_obj = get_cached_strategy_fn(token_name) if get_cached_strategy_fn else None
    except Exception as e:
        cprint(f"⚠️ Error fetching strategy context for {token_name}: {e}", "yellow")
        strat_obj = None

    if strat_obj:
        strategy_context_text, strategy_context_json = format_strategy_context_fn(strat_obj)
        add_console_log("Strategies loaded", "success")
    else:
        # Fallback to legacy market_data['strategy_signals'] if present
        strategy_context_text, strategy_context_json = format_legacy_strategy_signals(market_data)

    return strategy_context_text, strategy_context_json


def analyze_market_single(
    token: str,
    market_data,
    position_context: str,
    strategy_context_text: str,
    performance_context: str,
    chat_fn,
    trading_prompt_template: str,
    min_confidence: int
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Analyze market using single AI model.

    Args:
        token: Token symbol
        market_data: Market data to analyze
        position_context: Formatted position context string
        strategy_context_text: Formatted strategy context string
        performance_context: Formatted performance context string
        chat_fn: Function to chat with AI (chat_with_ai)
        trading_prompt_template: Template with {strategy_context}, {position_context}, {performance_context}
        min_confidence: Minimum confidence threshold

    Returns:
        Tuple of (recommendation_dict, raw_response)
    """
    response = chat_fn(
        trading_prompt_template.format(
            strategy_context=strategy_context_text,
            position_context=position_context,
            performance_context=performance_context,
        ),
        f"Market Data to Analyze:\n{market_data}",
    )

    if not response:
        cprint(f"❌ No response from AI for {token}", "red")
        return None, None

    # Parse the response
    action, confidence, reasoning = parse_single_model_response(response)

    # Apply confidence threshold
    action, reasoning = apply_confidence_threshold(
        action, confidence, min_confidence, reasoning
    )

    # Log the action change if downgraded
    if "Downgraded" in reasoning:
        add_console_log(f"{token} -> NOTHING | {confidence}% (low confidence)", "warning")

    recommendation = build_recommendation(token, action, confidence, reasoning)

    add_console_log(f"Analysis Complete for {token[:4]}...", "info")
    add_console_log(f"{token} -> {action} | {confidence}%", "success")

    return recommendation, response
