"""
🕉️ Karma Dev's Smart Leverage Calculator 🕉️

Dynamic leverage calculation based on:
- AI confidence score (0.0 - 1.0)
- Market volatility
- Current drawdown

Built with love by Karma Dev 🚀
"""

import math
from typing import Dict, Any


def calculate_smart_leverage(confidence: float, volatility: float = 0.0, drawdown: float = 0.0, max_leverage: int = 20) -> int:
    """
    Calculate optimal leverage based on multiple factors.
    
    Args:
        confidence (float): AI confidence score (0.0 - 1.0)
        volatility (float): Market volatility (0.0 - 1.0, default 0.0)
        drawdown (float): Current drawdown (0.0 - 1.0, default 0.0)
        max_leverage (int): Maximum allowed leverage (default 20)
    
    Returns:
        int: Calculated leverage (1 - max_leverage, integer)
    """
    # Base leverage: 1x to max_leverage based on confidence
    base_leverage = 1 + (confidence * (max_leverage - 1))
    
    # Reduce leverage in high volatility
    if volatility > 0.05:  # > 5% volatility
        base_leverage *= 0.7
        volatility_reduction = True
    else:
        volatility_reduction = False
    
    # Reduce leverage if in drawdown
    if drawdown > 0.05:  # > 5% drawdown
        base_leverage *= 0.5
        drawdown_reduction = True
    else:
        drawdown_reduction = False
    
    # Ensure leverage stays within bounds
    final_leverage = max(1.0, min(base_leverage, max_leverage))
    
    # Return integer leverage
    leverage_int = int(round(final_leverage))
    
    return leverage_int


def get_leverage_details(confidence: float, volatility: float = 0.0, drawdown: float = 0.0, max_leverage: int = 20) -> Dict[str, Any]:
    """
    Get detailed leverage calculation information.
    
    Returns:
        Dict with calculation details for logging/debugging
    """
    base_leverage = 1 + (confidence * (max_leverage - 1))
    original_base = base_leverage
    
    # Apply volatility adjustment
    if volatility > 0.05:
        base_leverage *= 0.7
    
    # Apply drawdown adjustment
    if drawdown > 0.05:
        base_leverage *= 0.5
    
    final_leverage = max(1.0, min(base_leverage, max_leverage))
    leverage_int = int(round(final_leverage))
    
    return {
        "confidence": confidence,
        "volatility": volatility,
        "drawdown": drawdown,
        "max_leverage": max_leverage,
        "base_leverage": round(original_base, 2),
        "volatility_adjustment": volatility > 0.05,
        "drawdown_adjustment": drawdown > 0.05,
        "final_leverage_float": round(final_leverage, 2),
        "final_leverage_int": leverage_int
    }


def calculate_position_size_with_leverage(account_balance: float, leverage: int, max_position_pct: float = 90.0) -> float:
    """
    Calculate position size in USD given leverage and account balance.
    
    Args:
        account_balance (float): Available account balance in USD
        leverage (int): Leverage to apply
        max_position_pct (float): Maximum percentage of balance to use
    
    Returns:
        float: Position size in USD (notional value)
    """
    if leverage < 1:
        leverage = 1
    
    # Calculate margin to use
    margin_to_use = account_balance * (max_position_pct / 100)
    
    # Calculate notional position size
    notional_position = margin_to_use * leverage
    
    return notional_position


def validate_leverage_constraints(leverage: int, position_value: float, min_position_value: float = 12.0) -> bool:
    """
    Validate that leverage meets minimum position value constraints.
    
    Args:
        leverage (int): Proposed leverage
        position_value (float): Position value in USD
        min_position_value (float): Minimum position value (default $12)
    
    Returns:
        bool: True if constraints are met
    """
    if leverage < 1:
        return False
    
    if position_value < min_position_value:
        return False
    
    return True


def get_leverage_recommendation(confidence: float, volatility: float = 0.0, drawdown: float = 0.0, max_leverage: int = 20) -> Dict[str, Any]:
    """
    Get complete leverage recommendation with validation.
    
    Returns:
        Dict with leverage recommendation and validation status
    """
    details = get_leverage_details(confidence, volatility, drawdown, max_leverage)
    leverage = details["final_leverage_int"]
    
    # Determine risk level
    if leverage <= 5:
        risk_level = "LOW"
    elif leverage <= 10:
        risk_level = "MEDIUM"
    elif leverage <= 15:
        risk_level = "HIGH"
    else:
        risk_level = "EXTREME"
    
    # Determine confidence level
    if confidence >= 0.8:
        confidence_level = "VERY HIGH"
    elif confidence >= 0.6:
        confidence_level = "HIGH"
    elif confidence >= 0.4:
        confidence_level = "MEDIUM"
    else:
        confidence_level = "LOW"
    
    return {
        "leverage": leverage,
        "risk_level": risk_level,
        "confidence_level": confidence_level,
        "details": details,
        "recommendation": f"{risk_level} risk ({confidence_level} confidence)"
    }


# Example usage and testing
if __name__ == "__main__":
    # Test cases
    test_cases = [
        {"confidence": 0.9, "volatility": 0.02, "drawdown": 0.01},  # High confidence, low risk
        {"confidence": 0.7, "volatility": 0.08, "drawdown": 0.02},  # Medium confidence, high volatility
        {"confidence": 0.5, "volatility": 0.03, "drawdown": 0.08},  # Low confidence, high drawdown
        {"confidence": 0.3, "volatility": 0.10, "drawdown": 0.12},  # Low confidence, high risk
    ]
    
    print("🧪 Smart Leverage Calculator Test Results:")
    print("=" * 60)
    
    for i, case in enumerate(test_cases, 1):
        result = get_leverage_recommendation(**case)
        print(f"\nTest Case {i}:")
        print(f"  Confidence: {case['confidence']}")
        print(f"  Volatility: {case['volatility']}")
        print(f"  Drawdown: {case['drawdown']}")
        print(f"  Recommended Leverage: {result['leverage']}x")
        print(f"  Risk Level: {result['risk_level']}")
        print(f"  Confidence Level: {result['confidence_level']}")
        print(f"  Recommendation: {result['recommendation']}")