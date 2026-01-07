"""
🕉️ Karma Dev's Dynamic TP/SL Calculator 🕉️

Dynamic Take Profit and Stop Loss calculation based on AI confidence.
Higher confidence = wider TP, tighter SL.

Built with love by Karma Dev 🚀
"""

from typing import Tuple, Dict, Any


def calculate_dynamic_tp_sl(confidence: float) -> Tuple[float, float]:
    """
    Calculate dynamic TP and SL percentages based on AI confidence.
    
    Args:
        confidence (float): AI confidence score (0.0 - 1.0)
    
    Returns:
        Tuple[float, float]: (take_profit_pct, stop_loss_pct)
    """
    if confidence >= 0.8:  # High confidence (80%+)
        # TP: 7% to 8% (increases with confidence above 80%)
        tp = 7.0 + (confidence - 0.8) * 5  # Range: 7% to 8%
        # SL: -1% to -1.4% (tighter with higher confidence)
        sl = -1.0 - (confidence - 0.8) * 2  # Range: -1% to -1.4%
        
    elif confidence >= 0.6:  # Medium confidence (60-79%)
        tp = 5.0  # Fixed 5%
        sl = -2.0  # Fixed -2%
        
    else:  # Low confidence (< 60%)
        tp = 3.0  # Fixed 3%
        sl = -3.0  # Fixed -3%
    
    return tp, sl


def get_tp_sl_details(confidence: float) -> Dict[str, Any]:
    """
    Get detailed TP/SL calculation information.
    
    Returns:
        Dict with calculation details for logging/debugging
    """
    tp, sl = calculate_dynamic_tp_sl(confidence)
    
    # Determine confidence tier
    if confidence >= 0.8:
        confidence_tier = "HIGH"
        rationale = "High confidence allows wider TP targets and tighter SL"
    elif confidence >= 0.6:
        confidence_tier = "MEDIUM"
        rationale = "Medium confidence uses balanced TP/SL ratios"
    else:
        confidence_tier = "LOW"
        rationale = "Low confidence uses conservative TP and wider SL"
    
    return {
        "confidence": confidence,
        "confidence_tier": confidence_tier,
        "take_profit_pct": round(tp, 2),
        "stop_loss_pct": round(sl, 2),
        "rationale": rationale,
        "tp_range": "7-8%" if confidence >= 0.8 else "5%" if confidence >= 0.6 else "3%",
        "sl_range": "-1 to -1.4%" if confidence >= 0.8 else "-2%" if confidence >= 0.6 else "-3%"
    }


def calculate_tp_sl_prices(entry_price: float, tp_pct: float, sl_pct: float) -> Dict[str, float]:
    """
    Calculate actual TP and SL prices from percentages.
    
    Args:
        entry_price (float): Entry price of the position
        tp_pct (float): Take profit percentage
        sl_pct (float): Stop loss percentage
    
    Returns:
        Dict with TP and SL prices
    """
    tp_price = entry_price * (1 + tp_pct / 100)
    sl_price = entry_price * (1 + sl_pct / 100)
    
    return {
        "entry_price": entry_price,
        "take_profit_price": round(tp_price, 2),
        "stop_loss_price": round(sl_price, 2),
        "take_profit_pct": tp_pct,
        "stop_loss_pct": sl_pct
    }


def get_position_tp_sl_recommendation(entry_price: float, confidence: float, position_type: str = "LONG") -> Dict[str, Any]:
    """
    Get complete TP/SL recommendation for a position.
    
    Args:
        entry_price (float): Entry price of the position
        confidence (float): AI confidence score
        position_type (str): "LONG" or "SHORT"
    
    Returns:
        Dict with complete TP/SL recommendation
    """
    tp_pct, sl_pct = calculate_dynamic_tp_sl(confidence)
    
    # For SHORT positions, invert the percentages
    if position_type.upper() == "SHORT":
        tp_pct = -abs(tp_pct)  # TP is below entry for shorts
        sl_pct = abs(sl_pct)   # SL is above entry for shorts
    
    price_details = calculate_tp_sl_prices(entry_price, tp_pct, sl_pct)
    
    details = get_tp_sl_details(confidence)
    
    return {
        "position_type": position_type.upper(),
        "entry_price": entry_price,
        "confidence": confidence,
        "tp_sl_details": details,
        "price_levels": price_details,
        "summary": f"TP: {price_details['take_profit_price']:.2f} ({tp_pct:+.1f}%) | SL: {price_details['stop_loss_price']:.2f} ({sl_pct:+.1f}%)"
    }


def validate_tp_sl_constraints(tp_pct: float, sl_pct: float, min_tp: float = 2.0, max_sl: float = 5.0) -> Dict[str, Any]:
    """
    Validate TP/SL constraints meet minimum requirements.
    
    Args:
        tp_pct (float): Take profit percentage
        sl_pct (float): Stop loss percentage
        min_tp (float): Minimum TP percentage
        max_sl (float): Maximum SL percentage (absolute value)
    
    Returns:
        Dict with validation results
    """
    tp_valid = abs(tp_pct) >= min_tp
    sl_valid = abs(sl_pct) <= max_sl
    
    return {
        "tp_valid": tp_valid,
        "sl_valid": sl_valid,
        "min_tp_required": min_tp,
        "max_sl_allowed": max_sl,
        "tp_meets_minimum": tp_valid,
        "sl_within_limits": sl_valid,
        "overall_valid": tp_valid and sl_valid
    }


def get_risk_reward_ratio(entry_price: float, tp_price: float, sl_price: float, position_type: str = "LONG") -> float:
    """
    Calculate risk-reward ratio for the position.
    
    Args:
        entry_price (float): Entry price
        tp_price (float): Take profit price
        sl_price (float): Stop loss price
        position_type (str): "LONG" or "SHORT"
    
    Returns:
        float: Risk-reward ratio (positive number)
    """
    if position_type.upper() == "LONG":
        risk = abs(entry_price - sl_price)
        reward = abs(tp_price - entry_price)
    else:  # SHORT
        risk = abs(sl_price - entry_price)
        reward = abs(entry_price - tp_price)
    
    if risk == 0:
        return 0.0
    
    return reward / risk


# Example usage and testing
if __name__ == "__main__":
    print("🧪 Dynamic TP/SL Calculator Test Results:")
    print("=" * 60)
    
    test_cases = [
        {"confidence": 0.9, "entry_price": 100.0},
        {"confidence": 0.7, "entry_price": 50.0},
        {"confidence": 0.5, "entry_price": 200.0},
        {"confidence": 0.3, "entry_price": 75.0},
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}:")
        print(f"  Confidence: {case['confidence']}")
        print(f"  Entry Price: ${case['entry_price']}")
        
        # LONG position
        long_result = get_position_tp_sl_recommendation(**case, position_type="LONG")
        print(f"  LONG Position:")
        print(f"    {long_result['summary']}")
        
        # SHORT position
        short_result = get_position_tp_sl_recommendation(**case, position_type="SHORT")
        print(f"  SHORT Position:")
        print(f"    {short_result['summary']}")
        
        # Risk-reward ratio
        rrr = get_risk_reward_ratio(
            case['entry_price'],
            long_result['price_levels']['take_profit_price'],
            long_result['price_levels']['stop_loss_price'],
            "LONG"
        )
        print(f"  Risk-Reward Ratio: {rrr:.2f}:1")