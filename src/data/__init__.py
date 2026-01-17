"""
Data Management Module

This module provides classes for recording and analyzing trading data:
- TradeRecorder: Enhanced trade logging with metadata
- SignalRecorder: AI signal recording and accuracy tracking
- PerformanceCalculator: Trading performance metrics
"""

from src.data.trade_recorder import TradeRecorder, get_recorder, save_trade
from src.data.signal_recorder import SignalRecorder, get_signal_recorder
from src.data.performance_calculator import PerformanceCalculator, get_performance_calculator

__all__ = [
    "TradeRecorder",
    "get_recorder",
    "save_trade",
    "SignalRecorder",
    "get_signal_recorder",
    "PerformanceCalculator",
    "get_performance_calculator",
]
