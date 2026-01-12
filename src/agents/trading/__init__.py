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

from .position_manager import (
    calculate_position_size,
    check_tp_sl_thresholds,
    check_profit_target,
    build_position_data,
    format_position_for_display,
    format_position_summary_for_ai,
    build_close_decision,
    evaluate_positions_for_tp_sl,
    extract_current_price,
    build_market_summary,
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
    # Position Manager
    "calculate_position_size",
    "check_tp_sl_thresholds",
    "check_profit_target",
    "build_position_data",
    "format_position_for_display",
    "format_position_summary_for_ai",
    "build_close_decision",
    "evaluate_positions_for_tp_sl",
    "extract_current_price",
    "build_market_summary",
]
