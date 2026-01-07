"""
🕉️ Karma Dev's Enhanced P&L Calculator 🕉️

Calculate accurate P&L including:
- Base price P&L
- Exchange fees (Hyperliquid)
- Slippage costs
- AI API costs
- Break-even analysis

Built with love by Karma Dev 🚀
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Position:
    """Position data structure for P&L calculations."""
    symbol: str
    direction: str  # "LONG" or "SHORT"
    entry_price: float
    exit_price: float
    position_value: float  # Notional value in USD
    leverage: int = 1
    order_type: str = "taker"
    tokens_used: int = 0
    entry_time: Optional[datetime] = None
    exit_time: Optional[datetime] = None


def calculate_base_pnl(position: Position) -> float:
    """
    Calculate base P&L from price movement only.
    
    Args:
        position (Position): Position data
    
    Returns:
        float: Base P&L (before fees)
    """
    if position.direction.upper() == "LONG":
        price_change = position.exit_price - position.entry_price
    else:  # SHORT
        price_change = position.entry_price - position.exit_price
    
    # Calculate P&L percentage
    price_pnl_pct = price_change / position.entry_price
    
    # Convert to USD value
    base_pnl = position.position_value * price_pnl_pct
    
    return base_pnl


def calculate_total_costs(position: Position, slippage_pct: float = 0.1) -> Dict[str, float]:
    """
    Calculate all trading costs.
    
    Args:
        position (Position): Position data
        slippage_pct (float): Slippage percentage
    
    Returns:
        Dict with cost breakdown
    """
    from .fee_calculator import calculate_hyperliquid_fees, calculate_cycle_ai_cost
    
    # Entry fees
    entry_fees = calculate_hyperliquid_fees(
        position.position_value, 
        position.order_type, 
        slippage_pct
    )
    
    # Exit fees (assume same order type and slippage)
    exit_fees = calculate_hyperliquid_fees(
        position.position_value, 
        position.order_type, 
        slippage_pct
    )
    
    # AI costs
    ai_costs = calculate_cycle_ai_cost(position.tokens_used)
    
    # Total costs
    total_exchange_fees = entry_fees["total_cost"] + exit_fees["total_cost"]
    total_ai_cost = ai_costs["ai_cost"]
    total_costs = total_exchange_fees + total_ai_cost
    
    return {
        "entry_exchange_fee": entry_fees["total_cost"],
        "exit_exchange_fee": exit_fees["total_cost"],
        "total_exchange_fees": total_exchange_fees,
        "ai_cost": total_ai_cost,
        "total_costs": total_costs,
        "break_even_pnl": total_costs
    }


def calculate_net_pnl(position: Position, slippage_pct: float = 0.1) -> Dict[str, Any]:
    """
    Calculate complete P&L analysis including all costs.
    
    Args:
        position (Position): Position data
        slippage_pct (float): Slippage percentage
    
    Returns:
        Dict with complete P&L analysis
    """
    # Calculate base P&L
    base_pnl = calculate_base_pnl(position)
    
    # Calculate all costs
    cost_breakdown = calculate_total_costs(position, slippage_pct)
    
    # Calculate net P&L
    net_pnl = base_pnl - cost_breakdown["total_costs"]
    
    # Calculate percentages
    base_pnl_pct = (base_pnl / position.position_value) * 100
    net_pnl_pct = (net_pnl / position.position_value) * 100
    total_cost_pct = (cost_breakdown["total_costs"] / position.position_value) * 100
    
    # Determine profitability
    profitable = net_pnl > 0
    break_even = net_pnl >= 0
    
    return {
        "position": {
            "symbol": position.symbol,
            "direction": position.direction,
            "entry_price": position.entry_price,
            "exit_price": position.exit_price,
            "position_value": position.position_value,
            "leverage": position.leverage,
            "order_type": position.order_type,
            "tokens_used": position.tokens_used
        },
        "base_pnl": {
            "amount": base_pnl,
            "percentage": base_pnl_pct,
            "description": "P&L from price movement only"
        },
        "costs": {
            "total_costs": cost_breakdown["total_costs"],
            "total_cost_pct": total_cost_pct,
            "break_even_pnl": cost_breakdown["break_even_pnl"],
            "exchange_fees": cost_breakdown["total_exchange_fees"],
            "ai_costs": cost_breakdown["ai_cost"],
            "details": cost_breakdown
        },
        "net_pnl": {
            "amount": net_pnl,
            "percentage": net_pnl_pct,
            "profitable": profitable,
            "break_even": break_even,
            "description": "Net P&L after all costs"
        },
        "metrics": {
            "risk_reward_ratio": abs(base_pnl / cost_breakdown["total_costs"]) if cost_breakdown["total_costs"] > 0 else 0,
            "cost_efficiency": (base_pnl / cost_breakdown["total_costs"]) if cost_breakdown["total_costs"] > 0 else 0,
            "roi": net_pnl_pct
        }
    }


def calculate_position_metrics(position: Position, slippage_pct: float = 0.1) -> Dict[str, Any]:
    """
    Calculate comprehensive position metrics.
    
    Returns:
        Dict with all position metrics
    """
    pnl_analysis = calculate_net_pnl(position, slippage_pct)
    
    # Calculate additional metrics
    base_pnl = pnl_analysis["base_pnl"]["amount"]
    net_pnl = pnl_analysis["net_pnl"]["amount"]
    total_costs = pnl_analysis["costs"]["total_costs"]
    
    # Win/Loss classification
    if net_pnl > 0:
        result = "WIN"
        win_amount = net_pnl
        loss_amount = 0
    elif net_pnl < 0:
        result = "LOSS"
        win_amount = 0
        loss_amount = abs(net_pnl)
    else:
        result = "BREAK_EVEN"
        win_amount = 0
        loss_amount = 0
    
    # Cost breakdown percentages
    exchange_fee_pct = (pnl_analysis["costs"]["exchange_fees"] / position.position_value) * 100
    ai_cost_pct = (pnl_analysis["costs"]["ai_costs"] / position.position_value) * 100
    
    return {
        "result": result,
        "win_amount": win_amount,
        "loss_amount": loss_amount,
        "base_pnl": base_pnl,
        "net_pnl": net_pnl,
        "total_costs": total_costs,
        "cost_breakdown": {
            "exchange_fees_pct": exchange_fee_pct,
            "ai_costs_pct": ai_cost_pct,
            "total_costs_pct": pnl_analysis["costs"]["total_cost_pct"]
        },
        "efficiency": {
            "cost_to_pnl_ratio": total_costs / abs(base_pnl) if base_pnl != 0 else 0,
            "net_roi": pnl_analysis["metrics"]["roi"],
            "gross_roi": pnl_analysis["base_pnl"]["percentage"]
        },
        "full_analysis": pnl_analysis
    }


def get_pnl_summary(position: Position, slippage_pct: float = 0.1) -> Dict[str, Any]:
    """
    Get a formatted P&L summary for display/logging.
    
    Returns:
        Dict with formatted summary
    """
    metrics = calculate_position_metrics(position, slippage_pct)
    
    return {
        "summary": {
            "result": metrics["result"],
            "base_pnl": f"${metrics['base_pnl']:.2f}",
            "net_pnl": f"${metrics['net_pnl']:.2f}",
            "total_costs": f"${metrics['total_costs']:.2f}"
        },
        "percentages": {
            "base_pnl_pct": f"{metrics['full_analysis']['base_pnl']['percentage']:.2f}%",
            "net_pnl_pct": f"{metrics['full_analysis']['net_pnl']['percentage']:.2f}%",
            "total_costs_pct": f"{metrics['cost_breakdown']['total_costs_pct']:.3f}%"
        },
        "cost_breakdown": {
            "exchange_fees": f"${metrics['full_analysis']['costs']['exchange_fees']:.2f}",
            "ai_costs": f"${metrics['full_analysis']['costs']['ai_costs']:.2f}",
            "exchange_fees_pct": f"{metrics['cost_breakdown']['exchange_fees_pct']:.3f}%",
            "ai_costs_pct": f"{metrics['cost_breakdown']['ai_costs_pct']:.3f}%"
        },
        "metrics": {
            "roi": f"{metrics['efficiency']['net_roi']:.2f}%",
            "cost_efficiency": f"{metrics['full_analysis']['metrics']['cost_efficiency']:.2f}",
            "risk_reward": f"{metrics['full_analysis']['metrics']['risk_reward_ratio']:.2f}:1"
        },
        "details": {
            "symbol": position.symbol,
            "direction": position.direction,
            "entry_price": position.entry_price,
            "exit_price": position.exit_price,
            "position_value": position.position_value,
            "leverage": position.leverage,
            "order_type": position.order_type,
            "tokens_used": position.tokens_used,
            "slippage_estimate": f"{slippage_pct}%"
        }
    }


def validate_pnl_thresholds(position: Position, min_profit_pct: float = 0.5, 
                           max_loss_pct: float = 2.0, slippage_pct: float = 0.1) -> Dict[str, Any]:
    """
    Validate P&L against minimum thresholds.
    
    Args:
        position (Position): Position data
        min_profit_pct (float): Minimum profit percentage to consider successful
        max_loss_pct (float): Maximum loss percentage allowed
        slippage_pct (float): Slippage percentage
    
    Returns:
        Dict with validation results
    """
    pnl_analysis = calculate_net_pnl(position, slippage_pct)
    net_pnl_pct = pnl_analysis["net_pnl"]["percentage"]
    
    # Determine status
    if net_pnl_pct >= min_profit_pct:
        status = "SUCCESS"
        reason = f"Profit {net_pnl_pct:.2f}% >= {min_profit_pct}% threshold"
    elif net_pnl_pct <= -max_loss_pct:
        status = "FAILURE"
        reason = f"Loss {abs(net_pnl_pct):.2f}% >= {max_loss_pct}% threshold"
    else:
        status = "MARGINAL"
        reason = f"P&L {net_pnl_pct:.2f}% within acceptable range"
    
    return {
        "status": status,
        "reason": reason,
        "net_pnl_pct": net_pnl_pct,
        "min_profit_threshold": min_profit_pct,
        "max_loss_threshold": max_loss_pct,
        "within_thresholds": -max_loss_pct < net_pnl_pct < min_profit_pct,
        "recommendation": "CONTINUE" if status != "FAILURE" else "REVIEW_STRATEGY"
    }


# Example usage and testing
if __name__ == "__main__":
    print("🧪 Enhanced P&L Calculator Test Results:")
    print("=" * 60)
    
    # Test cases
    test_positions = [
        Position("BTC", "LONG", 50000, 52000, 1000, 10, "taker", 5000),  # Profitable
        Position("ETH", "SHORT", 3000, 2800, 500, 5, "maker", 3000),     # Profitable with maker rebate
        Position("SOL", "LONG", 100, 95, 200, 20, "taker", 8000),        # Loss
        Position("LINK", "SHORT", 20, 21, 100, 15, "taker", 2000),       # Loss
    ]
    
    for i, position in enumerate(test_positions, 1):
        print(f"\nTest Case {i}: {position.symbol} {position.direction}")
        print(f"  Entry: ${position.entry_price}, Exit: ${position.exit_price}")
        print(f"  Position Value: ${position.position_value}, Leverage: {position.leverage}x")
        
        summary = get_pnl_summary(position)
        
        print(f"  Results:")
        print(f"    Result: {summary['summary']['result']}")
        print(f"    Base P&L: {summary['summary']['base_pnl']} ({summary['percentages']['base_pnl_pct']})")
        print(f"    Net P&L: {summary['summary']['net_pnl']} ({summary['percentages']['net_pnl_pct']})")
        print(f"    Total Costs: {summary['summary']['total_costs']} ({summary['percentages']['total_costs_pct']})")
        
        print(f"  Cost Breakdown:")
        print(f"    Exchange Fees: {summary['cost_breakdown']['exchange_fees']} ({summary['cost_breakdown']['exchange_fees_pct']})")
        print(f"    AI Costs: {summary['cost_breakdown']['ai_costs']} ({summary['cost_breakdown']['ai_costs_pct']})")
        
        print(f"  Metrics:")
        print(f"    ROI: {summary['metrics']['roi']}")
        print(f"    Risk-Reward: {summary['metrics']['risk_reward']}")