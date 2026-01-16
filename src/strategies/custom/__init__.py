"""
🕉️ Karma Dev's Custom Strategies Package
"""
from src.strategies.base_strategy import BaseStrategy
from .karma_compounding_agr import KarmaCompoundingStrategy
from .quad_enhanced_strategy import QuadRotationStrategy
from .macd_money_map import MACDMoneyMapStrategy

__all__ = ['ExampleStrategy', 'KarmaCompoundingStrategy', 'QuadRotationStrategy', 'MACDMoneyMapStrategy']
