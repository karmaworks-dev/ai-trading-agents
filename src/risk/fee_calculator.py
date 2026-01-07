"""
🕉️ Karma Dev's Hyperliquid Fee Calculator 🕉️

Calculate Hyperliquid exchange fees including:
- Maker fees (rebate)
- Taker fees
- Slippage estimation
- AI API costs

Built with love by Karma Dev 🚀
"""

from typing import Dict, Any, Optional
from decimal import Decimal


def calculate_hyperliquid_fees(position_value: float, order_type: str = "taker", slippage_pct: float = 0.1) -> Dict[str, Any]:
    """
    Calculate Hyperliquid exchange fees for a position.
    
    Args:
        position_value (float): Position value in USD
        order_type (str): "maker" or "taker"
        slippage_pct (float): Slippage percentage (default 0.1%)
    
    Returns:
        Dict with fee breakdown
    """
    # Hyperliquid fee rates
    MAKER_FEE_RATE = -0.0001  # -0.01% (maker rebate)
    TAKER_FEE_RATE = 0.0004   # 0.04% (average taker fee)
    
    # Select fee rate based on order type
    if order_type.lower() == "maker":
        fee_rate = MAKER_FEE_RATE
    else:  # taker
        fee_rate = TAKER_FEE_RATE
    
    # Calculate fees
    exchange_fee = position_value * fee_rate
    slippage_cost = position_value * (slippage_pct / 100)
    
    # Total cost
    total_cost = exchange_fee + slippage_cost
    
    return {
        "position_value": position_value,
        "order_type": order_type.lower(),
        "fee_rate": fee_rate,
        "exchange_fee": exchange_fee,
        "slippage_pct": slippage_pct,
        "slippage_cost": slippage_cost,
        "total_cost": total_cost,
        "total_cost_pct": (total_cost / position_value) * 100 if position_value > 0 else 0
    }


def calculate_cycle_ai_cost(tokens_used: int, cost_per_million: float = 3.00) -> Dict[str, Any]:
    """
    Calculate AI API cost for a trading cycle.
    
    Args:
        tokens_used (int): Number of tokens used in the cycle
        cost_per_million (float): Cost per million tokens (default $3.00)
    
    Returns:
        Dict with AI cost breakdown
    """
    ai_cost = (tokens_used / 1_000_000) * cost_per_million
    
    return {
        "tokens_used": tokens_used,
        "cost_per_million": cost_per_million,
        "ai_cost": ai_cost,
        "ai_cost_per_token": cost_per_million / 1_000_000
    }


def calculate_total_trade_cost(position_value: float, order_type: str = "taker", 
                              slippage_pct: float = 0.1, tokens_used: int = 0) -> Dict[str, Any]:
    """
    Calculate total cost of a trade including all fees and AI costs.
    
    Args:
        position_value (float): Position value in USD
        order_type (str): "maker" or "taker"
        slippage_pct (float): Slippage percentage
        tokens_used (int): AI tokens used for this trade
    
    Returns:
        Dict with complete cost breakdown
    """
    # Calculate exchange fees
    fee_breakdown = calculate_hyperliquid_fees(position_value, order_type, slippage_pct)
    
    # Calculate AI costs
    ai_breakdown = calculate_cycle_ai_cost(tokens_used)
    
    # Total costs
    total_fees = fee_breakdown["total_cost"]
    total_ai_cost = ai_breakdown["ai_cost"]
    grand_total = total_fees + total_ai_cost
    
    return {
        "position_value": position_value,
        "exchange_fees": fee_breakdown,
        "ai_costs": ai_breakdown,
        "total_fees": total_fees,
        "total_ai_cost": total_ai_cost,
        "grand_total_cost": grand_total,
        "grand_total_pct": (grand_total / position_value) * 100 if position_value > 0 else 0
    }


def calculate_break_even_pnl(position_value: float, order_type: str = "taker", 
                           slippage_pct: float = 0.1, tokens_used: int = 0) -> Dict[str, Any]:
    """
    Calculate the minimum P&L needed to break even after all costs.
    
    Args:
        position_value (float): Position value in USD
        order_type (str): "maker" or "taker"
        slippage_pct (float): Slippage percentage
        tokens_used (int): AI tokens used
    
    Returns:
        Dict with break-even analysis
    """
    cost_breakdown = calculate_total_trade_cost(position_value, order_type, slippage_pct, tokens_used)
    
    # Break-even P&L must cover all costs
    break_even_pnl = cost_breakdown["grand_total_cost"]
    break_even_pct = cost_breakdown["grand_total_pct"]
    
    return {
        "position_value": position_value,
        "total_costs": cost_breakdown["grand_total_cost"],
        "break_even_pnl": break_even_pnl,
        "break_even_pct": break_even_pct,
        "cost_breakdown": cost_breakdown
    }


def get_fee_summary(position_value: float, order_type: str = "taker", 
                   slippage_pct: float = 0.1, tokens_used: int = 0) -> Dict[str, Any]:
    """
    Get a comprehensive fee summary for display/logging.
    
    Returns:
        Dict with formatted fee summary
    """
    cost_breakdown = calculate_total_trade_cost(position_value, order_type, slippage_pct, tokens_used)
    break_even = calculate_break_even_pnl(position_value, order_type, slippage_pct, tokens_used)
    
    return {
        "position_value": position_value,
        "fee_summary": {
            "exchange_fee": f"${cost_breakdown['exchange_fees']['exchange_fee']:.4f}",
            "slippage_cost": f"${cost_breakdown['exchange_fees']['slippage_cost']:.4f}",
            "ai_cost": f"${cost_breakdown['ai_costs']['ai_cost']:.4f}",
            "total_fees": f"${cost_breakdown['total_fees']:.4f}",
            "ai_cost_total": f"${cost_breakdown['total_ai_cost']:.4f}",
            "grand_total": f"${cost_breakdown['grand_total_cost']:.4f}"
        },
        "percentages": {
            "exchange_fee_pct": f"{cost_breakdown['exchange_fees']['total_cost_pct']:.3f}%",
            "ai_cost_pct": f"{cost_breakdown['ai_costs']['ai_cost'] / position_value * 100:.3f}%" if position_value > 0 else "0.000%",
            "grand_total_pct": f"{break_even['break_even_pct']:.3f}%"
        },
        "break_even": {
            "pnl_needed": f"${break_even['break_even_pnl']:.4f}",
            "percentage_needed": f"{break_even['break_even_pct']:.3f}%"
        },
        "details": {
            "order_type": order_type,
            "slippage_estimate": f"{slippage_pct}%",
            "tokens_used": tokens_used,
            "cost_per_million": "$3.00"
        }
    }


def validate_cost_constraints(position_value: float, max_cost_pct: float = 2.0, 
                             order_type: str = "taker", slippage_pct: float = 0.1) -> Dict[str, Any]:
    """
    Validate that trading costs are within acceptable limits.
    
    Args:
        position_value (float): Position value in USD
        max_cost_pct (float): Maximum acceptable cost percentage
        order_type (str): Order type
        slippage_pct (float): Slippage percentage
    
    Returns:
        Dict with validation results
    """
    fee_breakdown = calculate_hyperliquid_fees(position_value, order_type, slippage_pct)
    total_cost_pct = fee_breakdown["total_cost_pct"]
    
    within_limits = total_cost_pct <= max_cost_pct
    
    return {
        "position_value": position_value,
        "total_cost_pct": total_cost_pct,
        "max_allowed_pct": max_cost_pct,
        "within_limits": within_limits,
        "exchange_fee_pct": fee_breakdown["fee_rate"] * 100,
        "slippage_pct": slippage_pct,
        "recommendation": "PROCEED" if within_limits else "REVIEW_POSITION_SIZE"
    }


# Example usage and testing
if __name__ == "__main__":
    print("🧪 Hyperliquid Fee Calculator Test Results:")
    print("=" * 60)
    
    test_cases = [
        {"position_value": 1000.0, "order_type": "taker", "tokens_used": 5000},
        {"position_value": 500.0, "order_type": "maker", "tokens_used": 3000},
        {"position_value": 2000.0, "order_type": "taker", "tokens_used": 8000},
        {"position_value": 250.0, "order_type": "maker", "tokens_used": 2000},
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}:")
        print(f"  Position Value: ${case['position_value']}")
        print(f"  Order Type: {case['order_type']}")
        print(f"  Tokens Used: {case['tokens_used']}")
        
        summary = get_fee_summary(**case)
        
        print(f"  Fee Breakdown:")
        for key, value in summary["fee_summary"].items():
            print(f"    {key.replace('_', ' ').title()}: {value}")
        
        print(f"  Cost Percentages:")
        for key, value in summary["percentages"].items():
            print(f"    {key.replace('_', ' ').title()}: {value}")
        
        print(f"  Break-Even Analysis:")
        print(f"    P&L Needed: {summary['break_even']['pnl_needed']}")
        print(f"    Percentage Needed: {summary['break_even']['percentage_needed']}")