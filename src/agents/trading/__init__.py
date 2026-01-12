"""
Trading Agent Submodules

This package contains extracted components from the main TradingAgent class
to improve maintainability and testability.
"""

from .prompts import (
    TRADING_PROMPT,
    SWARM_TRADING_PROMPT,
    SMART_ALLOCATION_PROMPT,
    POSITION_ANALYSIS_PROMPT,
)

from .ai_interface import (
    get_performance_metrics,
    chat_with_ai,
    format_market_data_for_swarm,
    parse_vote_from_response,
    calculate_swarm_consensus,
)

__all__ = [
    # Prompts
    "TRADING_PROMPT",
    "SWARM_TRADING_PROMPT",
    "SMART_ALLOCATION_PROMPT",
    "POSITION_ANALYSIS_PROMPT",
    # AI Interface
    "get_performance_metrics",
    "chat_with_ai",
    "format_market_data_for_swarm",
    "parse_vote_from_response",
    "calculate_swarm_consensus",
]
