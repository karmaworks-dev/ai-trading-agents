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

__all__ = [
    "TRADING_PROMPT",
    "SWARM_TRADING_PROMPT",
    "SMART_ALLOCATION_PROMPT",
    "POSITION_ANALYSIS_PROMPT",
]
