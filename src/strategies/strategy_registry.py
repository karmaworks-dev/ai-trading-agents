"""
Strategy Registry
==================
Auto-discover and manage trading strategies.
Provides strategy metadata for frontend display.
"""

from pathlib import Path
from typing import Dict, List, Optional
import importlib
import inspect


# Strategy metadata - defines display info for each strategy
# Add new strategies here when creating them
STRATEGY_METADATA = {
    "quad_rotation": {
        "id": "quad_rotation",
        "name": "Quad Rotation",
        "description": "Multi-stochastic rotation system using 4 stochastics with different periods to identify high-probability entries through agreement signals.",
        "category": "momentum",
        "risk_level": "medium",
        "recommended_timeframes": ["15m", "30m", "1h"],
        "module": "src.strategies.custom.quad_enhanced_strategy",
        "class_name": "QuadRotationStrategy",
    },
    "compounding_agr": {
        "id": "compounding_agr",
        "name": "Compounding AGR",
        "description": "Adaptive position sizing strategy that compounds gains while managing risk through dynamic allocation percentages.",
        "category": "position_sizing",
        "risk_level": "medium",
        "recommended_timeframes": ["30m", "1h", "4h"],
        "module": "src.strategies.custom.karma_compounding_agr",
        "class_name": "KarmaCompoundingStrategy",
    },
    "macd_money_map": {
        "id": "macd_money_map",
        "name": "MACD Money Map",
        "description": "Complete implementation of the MACD Money Map trading framework. Includes trend following (zero line), divergence detection (momentum exhaustion), and mathematical risk management.",
        "category": "momentum",
        "risk_level": "medium",
        "recommended_timeframes": ["15m", "1h", "4h"],
        "module": "src.strategies.custom.macd_money_map",
        "class_name": "MACDMoneyMapStrategy",
    },
}


def get_available_strategies() -> List[Dict]:
    """
    Get list of all available strategies with their metadata.

    Returns:
        List of strategy dicts with: id, name, description, category, risk_level, etc.
    """
    strategies = []
    for strategy_id, metadata in STRATEGY_METADATA.items():
        strategies.append({
            "id": metadata["id"],
            "name": metadata["name"],
            "description": metadata["description"],
            "category": metadata["category"],
            "risk_level": metadata["risk_level"],
            "recommended_timeframes": metadata["recommended_timeframes"],
        })
    return strategies


def get_strategy_metadata(strategy_id: str) -> Optional[Dict]:
    """
    Get metadata for a specific strategy.

    Args:
        strategy_id: The strategy identifier (e.g., 'quad_rotation')

    Returns:
        Strategy metadata dict or None if not found
    """
    return STRATEGY_METADATA.get(strategy_id)


def load_strategy_class(strategy_id: str):
    """
    Dynamically load a strategy class by its ID.

    Args:
        strategy_id: The strategy identifier

    Returns:
        Strategy class (not instantiated) or None if not found
    """
    metadata = STRATEGY_METADATA.get(strategy_id)
    if not metadata:
        print(f"⚠️ Strategy '{strategy_id}' not found in registry")
        return None

    try:
        module = importlib.import_module(metadata["module"])
        strategy_class = getattr(module, metadata["class_name"])
        return strategy_class
    except ImportError as e:
        print(f"⚠️ Failed to import strategy '{strategy_id}': {e}")
        return None
    except AttributeError as e:
        print(f"⚠️ Strategy class '{metadata['class_name']}' not found: {e}")
        return None


def get_enabled_strategies(settings: Dict) -> List:
    """
    Load and instantiate only the strategies that are enabled in settings.

    Args:
        settings: User settings dict containing 'enabled_strategies' key

    Returns:
        List of instantiated strategy objects
    """
    enabled_strategies = []
    enabled_config = settings.get("enabled_strategies", {})

    for strategy_id, is_enabled in enabled_config.items():
        if not is_enabled:
            continue

        strategy_class = load_strategy_class(strategy_id)
        if strategy_class:
            try:
                strategy_instance = strategy_class()
                enabled_strategies.append(strategy_instance)
                print(f"✅ Loaded strategy: {strategy_id}")
            except Exception as e:
                print(f"⚠️ Failed to instantiate strategy '{strategy_id}': {e}")

    return enabled_strategies


def get_strategies_with_status(settings: Dict) -> List[Dict]:
    """
    Get all strategies with their enabled/disabled status from settings.
    Used by frontend to display strategy toggles.

    Args:
        settings: User settings dict

    Returns:
        List of strategy dicts with 'enabled' field added
    """
    enabled_config = settings.get("enabled_strategies", {})
    strategies = []

    for strategy_id, metadata in STRATEGY_METADATA.items():
        strategies.append({
            "id": metadata["id"],
            "name": metadata["name"],
            "description": metadata["description"],
            "category": metadata["category"],
            "risk_level": metadata["risk_level"],
            "recommended_timeframes": metadata["recommended_timeframes"],
            "enabled": enabled_config.get(strategy_id, False),
        })

    return strategies
