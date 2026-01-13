"""
AI Interface Functions for Trading Agent

This module contains functions for communicating with AI models,
formatting data for analysis, and processing AI responses.

All functions are standalone (no class dependencies) to enable
easier testing and reuse.
"""

import re
import json
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

import pandas as pd

# Import logging utilities with fallback
try:
    from src.utils.logging_utils import add_console_log
except ImportError:
    def add_console_log(message, level="info", console_file=None):
        print(f"[AI] {message}")

# Import termcolor with fallback
try:
    from termcolor import cprint
except ImportError:
    def cprint(msg, *args, **kwargs):
        print(msg)


# =============================================================================
# PERFORMANCE METRICS
# =============================================================================

def get_performance_metrics(trades_file_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Calculate recent trading performance for AI motivation.

    Args:
        trades_file_path: Path to trades.json file. If None, uses default location.

    Returns:
        Dictionary with win_rate, total_pnl, winning_trades, total_trades, grade
    """
    try:
        if trades_file_path is None:
            trades_file_path = Path(__file__).parent.parent.parent / "data" / "trades.json"

        if not trades_file_path.exists():
            return {
                'win_rate': 0,
                'total_pnl': 0,
                'winning_trades': 0,
                'total_trades': 0,
                'grade': 'STARTING'
            }

        with open(trades_file_path, 'r') as f:
            trades = json.load(f)

        # Get last 20 trades
        recent_trades = trades[-20:] if len(trades) > 20 else trades

        if not recent_trades:
            return {
                'win_rate': 0,
                'total_pnl': 0,
                'winning_trades': 0,
                'total_trades': 0,
                'grade': 'STARTING'
            }

        # Calculate metrics
        winning_trades = len([t for t in recent_trades if t.get('pnl', 0) > 0])
        total_trades = len(recent_trades)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        total_pnl = sum([t.get('pnl', 0) for t in recent_trades])

        # Assign performance grade
        if win_rate >= 70:
            grade = 'EXCELLENT ⭐⭐⭐'
        elif win_rate >= 60:
            grade = 'GREAT ⭐⭐'
        elif win_rate >= 50:
            grade = 'GOOD ⭐'
        else:
            grade = 'NEEDS IMPROVEMENT ⚠️'

        return {
            'win_rate': round(win_rate, 1),
            'total_pnl': round(total_pnl, 2),
            'winning_trades': winning_trades,
            'total_trades': total_trades,
            'grade': grade
        }

    except Exception as e:
        cprint(f"⚠️ Error calculating performance: {e}", "yellow")
        return {
            'win_rate': 0,
            'total_pnl': 0,
            'winning_trades': 0,
            'total_trades': 0,
            'grade': 'UNKNOWN'
        }


# =============================================================================
# AI COMMUNICATION
# =============================================================================

def chat_with_ai(model, system_prompt: str, user_content: str,
                 temperature: float, max_tokens: int) -> Optional[str]:
    """
    Send prompt to AI model and return response.

    Args:
        model: AI model instance (from ModelFactory)
        system_prompt: System/instruction prompt
        user_content: User message/query
        temperature: Model temperature (0.0-1.0)
        max_tokens: Maximum tokens in response

    Returns:
        Response string or None if error
    """
    try:
        response = model.generate_response(
            system_prompt=system_prompt,
            user_content=user_content,
            temperature=temperature,
            max_tokens=max_tokens
        )

        if hasattr(response, "content"):
            return response.content
        return str(response)

    except Exception as e:
        error_str = str(e).lower()
        model_name = getattr(model, 'model_name', 'Unknown')
        provider = getattr(model, 'provider', 'Unknown')

        # Detect specific error types for helpful messages
        if "rate_limit" in error_str or "rate limit" in error_str:
            msg = f"Rate limit: {provider}/{model_name}"
        elif "invalid_api_key" in error_str or "authentication" in error_str or "401" in error_str:
            msg = f"Invalid API key: {provider}"
        elif "insufficient" in error_str or "quota" in error_str or "billing" in error_str:
            msg = f"Quota exceeded: {provider}"
        elif "timeout" in error_str or "timed out" in error_str:
            msg = f"Timeout: {provider}/{model_name}"
        elif "connection" in error_str or "network" in error_str:
            msg = f"Connection error: {provider}"
        else:
            msg = f"Model failed: {provider}/{model_name}"

        add_console_log(msg, "error")
        cprint(f"❌ {msg} - {str(e)[:80]}", "red")
        return None


# =============================================================================
# DATA FORMATTING
# =============================================================================

def format_market_data_for_swarm(token: str, market_data: Any, timeframe: str) -> str:
    """
    Format market data into a clean, readable format for swarm analysis.

    Args:
        token: Token symbol
        market_data: DataFrame or dict of market data
        timeframe: Timeframe string (e.g., '30m', '1h')

    Returns:
        Formatted string for AI prompt
    """
    try:
        cprint(f"\n📊 MARKET DATA RECEIVED FOR {token[:8]}...", "cyan", attrs=["bold"])
        add_console_log(f"📊 MARKET DATA RECEIVED FOR {token[:8]}...", "info")

        if isinstance(market_data, pd.DataFrame):
            cprint(f"✅ DataFrame received: {len(market_data)} bars", "green")
            cprint(f"📅 Date range: {market_data.index[0]} to {market_data.index[-1]}", "yellow")
            cprint(f"🕐 Timeframe: {timeframe}", "yellow")

            cprint("\n📈 First 5 Bars (OHLCV):", "cyan")
            print(market_data.head().to_string())

            cprint("\n📉 Last 3 Bars (Most Recent):", "cyan")
            print(market_data.tail(3).to_string())

            formatted = f"""
TOKEN: {token}
TIMEFRAME: {timeframe} bars
TOTAL BARS: {len(market_data)}
DATE RANGE: {market_data.index[0]} to {market_data.index[-1]}

RECENT PRICE ACTION (Last 10 bars):
{market_data.tail(10).to_string()}

FULL DATASET:
{market_data.to_string()}
"""
        else:
            cprint(f"⚠️ Market data is not a DataFrame: {type(market_data)}", "yellow")
            formatted = f"TOKEN: {token}\nMARKET DATA:\n{str(market_data)}"

        if isinstance(market_data, dict) and "strategy_signals" in market_data:
            formatted += f"\n\nSTRATEGY SIGNALS:\n{json.dumps(market_data['strategy_signals'], indent=2)}"

        cprint("\n✅ Market data formatted and ready for analysis!\n", "green")
        return formatted

    except Exception as e:
        cprint(f"❌ Error formatting market data: {e}", "red")
        return str(market_data)


# =============================================================================
# VOTE PARSING
# =============================================================================

def parse_vote_from_response(response_upper: str) -> Tuple[str, int]:
    """
    Parse a vote from the model response with strict matching.
    Extracts both action AND confidence score.

    Expected format: "BUY | 85%" or "SELL | 70%" or "NOTHING | 45%"
    Falls back to action-only parsing if confidence not found.

    Args:
        response_upper: Uppercase response string from model

    Returns:
        Tuple of (action: str, confidence: int)
        - action: "BUY", "SELL", or "NOTHING"
        - confidence: 0-100 (defaults to 50 if not found)
    """
    # Clean the response (remove extra whitespace, newlines)
    response_clean = response_upper.strip().split('\n')[0].strip()

    # Default confidence if not found
    confidence = 50

    # Try to parse "ACTION | XX%" format
    if "|" in response_clean:
        parts = response_clean.split("|")
        action_part = parts[0].strip()
        confidence_part = parts[1].strip() if len(parts) > 1 else ""

        # Extract confidence number
        confidence_match = re.search(r'(\d+)', confidence_part)
        if confidence_match:
            confidence = min(100, max(0, int(confidence_match.group(1))))

        # Parse action from the first part
        response_clean = action_part

    # Parse action with priority matching
    action = "NOTHING"

    # Priority 1: Exact match
    if response_clean in ["BUY"]:
        action = "BUY"
    elif response_clean in ["SELL"]:
        action = "SELL"
    elif response_clean in ["DO NOTHING", "NOTHING", "HOLD", "WAIT"]:
        action = "NOTHING"
    # Priority 2: Starts with action word
    elif response_clean.startswith("BUY"):
        action = "BUY"
    elif response_clean.startswith("SELL"):
        action = "SELL"
    elif response_clean.startswith("DO NOTHING") or response_clean.startswith("NOTHING"):
        action = "NOTHING"
    # Priority 3: Contains action word (fallback)
    elif "SELL" in response_clean:
        action = "SELL"
    elif "BUY" in response_clean:
        action = "BUY"

    return action, confidence


# =============================================================================
# SWARM CONSENSUS
# =============================================================================

def calculate_swarm_consensus(swarm_result: Dict[str, Any],
                              min_swarm_confidence: int) -> Tuple[str, int, str]:
    """
    Calculate consensus from individual swarm responses with confidence weighting.

    Key features:
    1. Extracts both action AND confidence from each model
    2. Logs individual votes with confidence (e.g., "Model 1 - BUY | 85%")
    3. Calculates weighted average confidence for the majority action
    4. Shows "TIED" instead of "NOTHING" when there's an actual tie
    5. Clear frontend logging: "Swarm -> BUY | 62% sure"

    Args:
        swarm_result: Dictionary with 'responses' key containing model responses
        min_swarm_confidence: Minimum confidence threshold for action

    Returns:
        Tuple of (action, confidence, reasoning)
    """
    try:
        # Track votes with confidence scores
        votes = {"BUY": [], "SELL": [], "NOTHING": []}  # Lists of confidence scores
        model_votes = []  # For detailed logging
        model_index = 1

        cprint("\n📊 Individual Model Votes:", "cyan", attrs=["bold"])

        for provider, data in swarm_result["responses"].items():
            if not data["success"]:
                cprint(f"   ⚠️ Model {model_index} ({provider}): Failed (skipping)", "yellow")
                model_votes.append(f"Model {model_index} ({provider}): FAILED")
                model_index += 1
                continue

            response_text = data["response"].strip() if data["response"] else ""
            response_upper = response_text.upper()

            # Parse vote AND confidence
            action, confidence = parse_vote_from_response(response_upper)

            # Store confidence score for this action
            votes[action].append(confidence)

            # Format vote display
            vote_display = f"Model {model_index} - {action} | {confidence}%"
            model_votes.append(f"Model {model_index} ({provider}): {action} | {confidence}%")

            # Color-coded console output
            if action == "BUY":
                cprint(f"   ✅ {vote_display}", "green")
            elif action == "SELL":
                cprint(f"   🔴 {vote_display}", "red")
            else:
                cprint(f"   ⏸️ {vote_display}", "cyan")

            model_index += 1

        # Count total valid votes
        total_votes = sum(len(v) for v in votes.values())
        if total_votes == 0:
            cprint("❌ No valid responses from swarm - defaulting to NOTHING", "red")
            add_console_log("Swarm -> NOTHING | 0% (no responses)", "warning")
            return "NOTHING", 0, "No valid responses from swarm"

        # Calculate vote counts and average confidence per action
        vote_counts = {action: len(confs) for action, confs in votes.items()}
        avg_confidences = {}
        for action, confs in votes.items():
            if confs:
                avg_confidences[action] = int(sum(confs) / len(confs))
            else:
                avg_confidences[action] = 0

        # Find majority action
        majority_action = max(vote_counts, key=vote_counts.get)
        majority_count = vote_counts[majority_action]

        # Check for ties - look at top 2 vote counts
        sorted_counts = sorted(vote_counts.values(), reverse=True)
        has_tie = len(sorted_counts) >= 2 and sorted_counts[0] == sorted_counts[1] and sorted_counts[0] > 0

        if has_tie:
            # Find which actions are tied
            tied_actions = [a for a, c in vote_counts.items() if c == majority_count]
            tie_avg_confidence = int(sum(avg_confidences[a] for a in tied_actions) / len(tied_actions))

            cprint(
                f"\n⚠️ TIE DETECTED: {', '.join(tied_actions)} each have {majority_count} votes",
                "yellow",
                attrs=["bold"]
            )

            # Log to frontend with TIED status
            add_console_log(f"Swarm -> TIED | {tie_avg_confidence}% sure", "warning")

            reasoning = f"🌊 Swarm Consensus: TIED ({total_votes} models voted)\n\n"
            reasoning += "Vote Breakdown:\n"
            for action in ["BUY", "SELL", "NOTHING"]:
                count = vote_counts[action]
                avg = avg_confidences[action]
                reasoning += f"   {action}: {count} votes (avg {avg}% confidence)\n"
            reasoning += f"\n⚠️ TIE between: {', '.join(tied_actions)}\n"
            reasoning += "   → Conservative approach: No action taken\n\n"
            reasoning += "Individual Votes:\n"
            reasoning += "\n".join(f"   {vote}" for vote in model_votes)

            return "NOTHING", tie_avg_confidence, reasoning

        # Calculate final confidence as weighted average of winning action's votes
        final_confidence = avg_confidences[majority_action]
        vote_percentage = int((majority_count / total_votes) * 100)

        # Check minimum confidence threshold
        if final_confidence < min_swarm_confidence and majority_action != "NOTHING":
            cprint(
                f"\n⚠️ LOW CONFIDENCE: {final_confidence}% < {min_swarm_confidence}% threshold",
                "yellow",
                attrs=["bold"]
            )
            cprint(f"   → Downgrading {majority_action} to NOTHING", "yellow")

            add_console_log(f"Swarm -> NOTHING | {final_confidence}% (low confidence)", "warning")

            reasoning = f"🌊 Swarm Consensus: LOW CONFIDENCE ({total_votes} models voted)\n\n"
            reasoning += "Vote Breakdown:\n"
            for action in ["BUY", "SELL", "NOTHING"]:
                count = vote_counts[action]
                avg = avg_confidences[action]
                reasoning += f"   {action}: {count} votes (avg {avg}% confidence)\n"
            reasoning += f"\n⚠️ Confidence {final_confidence}% below {min_swarm_confidence}% threshold\n"
            reasoning += f"   Original: {majority_action} | Downgraded to: NOTHING\n\n"
            reasoning += "Individual Votes:\n"
            reasoning += "\n".join(f"   {vote}" for vote in model_votes)

            return "NOTHING", final_confidence, reasoning

        # Normal case: clear majority above threshold
        action_emoji = "📈" if majority_action == "BUY" else "📉" if majority_action == "SELL" else "⏸️"

        cprint(
            f"\n🌊 Swarm Consensus: {majority_action} | {final_confidence}% sure ({majority_count}/{total_votes} votes)",
            "cyan",
            attrs=["bold"]
        )

        # Log to frontend with clear format
        add_console_log(f"Swarm -> {majority_action} | {final_confidence}% sure", "trade")

        reasoning = f"🌊 Swarm Consensus: {majority_action} ({total_votes} models voted)\n\n"
        reasoning += "Vote Breakdown:\n"
        for action in ["BUY", "SELL", "NOTHING"]:
            count = vote_counts[action]
            avg = avg_confidences[action]
            reasoning += f"   {action}: {count} votes (avg {avg}% confidence)\n"
        reasoning += f"\n{action_emoji} Final Decision: {majority_action} | {final_confidence}% confident\n"
        reasoning += f"   ({majority_count}/{total_votes} models agreed = {vote_percentage}% consensus)\n\n"
        reasoning += "Individual Votes:\n"
        reasoning += "\n".join(f"   {vote}" for vote in model_votes)

        return majority_action, final_confidence, reasoning

    except Exception as e:
        cprint(f"❌ Error calculating swarm consensus: {e}", "red")
        add_console_log(f"Swarm -> ERROR | 0%", "error")
        return "NOTHING", 0, f"Error calculating consensus: {str(e)}"
