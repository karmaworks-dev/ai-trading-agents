"""
🕉️ Karma Dev's Risk Management Integration 🕉️

Central risk management system that integrates all risk calculators:
- Smart leverage calculation
- Dynamic TP/SL
- Hyperliquid fees
- Enhanced P&L calculation

Built with love by Karma Dev 🚀
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

from .leverage_calculator import calculate_smart_leverage, get_leverage_recommendation
from .tp_sl_calculator import calculate_dynamic_tp_sl, get_position_tp_sl_recommendation
from .fee_calculator import calculate_total_trade_cost, get_fee_summary
from .pnl_calculator import calculate_net_pnl, get_pnl_summary, Position


@dataclass
class RiskContext:
    """Context for risk calculations."""
    confidence: float
    volatility: float = 0.0
    drawdown: float = 0.0
    max_leverage: int = 20
    slippage_pct: float = 0.1
    tokens_used: int = 0
    min_position_value: float = 12.0


@dataclass
class TradeRecommendation:
    """Complete trade recommendation with risk management."""
    symbol: str
    action: str  # "BUY", "SELL", "NOTHING"
    confidence: float
    leverage: int
    position_value: float
    tp_pct: float
    sl_pct: float
    tp_price: float
    sl_price: float
    estimated_pnl: float
    estimated_costs: float
    risk_reward_ratio: float
    recommendation: str


class RiskManager:
    """Central risk management system."""
    
    def __init__(self, max_leverage: int = 20):
        self.max_leverage = max_leverage
        self.risk_context = None
    
    def set_risk_context(self, confidence: float, volatility: float = 0.0, 
                        drawdown: float = 0.0, slippage_pct: float = 0.1, 
                        tokens_used: int = 0) -> None:
        """Set the current risk context."""
        self.risk_context = RiskContext(
            confidence=confidence,
            volatility=volatility,
            drawdown=drawdown,
            max_leverage=self.max_leverage,
            slippage_pct=slippage_pct,
            tokens_used=tokens_used
        )
    
    def calculate_position_risk(self, symbol: str, action: str, confidence: float,
                              entry_price: float, account_balance: float,
                              max_position_pct: float = 90.0) -> Dict[str, Any]:
        """
        Calculate complete position risk profile.
        
        Returns:
            Dict with complete risk analysis
        """
        if not self.risk_context:
            self.set_risk_context(confidence)
        
        # Calculate leverage
        leverage = calculate_smart_leverage(
            confidence=self.risk_context.confidence,
            volatility=self.risk_context.volatility,
            drawdown=self.risk_context.drawdown,
            max_leverage=self.max_leverage
        )
        
        # Calculate position size
        position_value = account_balance * (max_position_pct / 100) * leverage
        
        # Calculate TP/SL
        tp_pct, sl_pct = calculate_dynamic_tp_sl(self.risk_context.confidence)
        
        # Calculate TP/SL prices
        tp_price = entry_price * (1 + tp_pct / 100)
        sl_price = entry_price * (1 + sl_pct / 100)
        
        # Calculate costs
        cost_summary = get_fee_summary(
            position_value=position_value,
            order_type="taker",
            slippage_pct=self.risk_context.slippage_pct,
            tokens_used=self.risk_context.tokens_used
        )
        
        # Calculate estimated P&L
        estimated_pnl = position_value * (tp_pct / 100)
        estimated_costs = cost_summary["fee_summary"]["grand_total"]
        
        # Calculate risk-reward ratio
        risk_amount = position_value * (abs(sl_pct) / 100)
        reward_amount = position_value * (tp_pct / 100)
        risk_reward_ratio = reward_amount / risk_amount if risk_amount > 0 else 0
        
        return {
            "symbol": symbol,
            "action": action,
            "confidence": confidence,
            "leverage": leverage,
            "position_value": position_value,
            "tp_pct": tp_pct,
            "sl_pct": sl_pct,
            "tp_price": tp_price,
            "sl_price": sl_price,
            "estimated_pnl": estimated_pnl,
            "estimated_costs": estimated_costs,
            "risk_reward_ratio": risk_reward_ratio,
            "cost_breakdown": cost_summary,
            "recommendation": f"{action} with {leverage}x leverage"
        }
    
    def validate_trade_decision(self, symbol: str, action: str, confidence: float,
                               entry_price: float, account_balance: float,
                               max_position_pct: float = 90.0) -> Dict[str, Any]:
        """
        Validate a trade decision against risk constraints.
        
        Returns:
            Dict with validation results and recommendations
        """
        risk_profile = self.calculate_position_risk(
            symbol, action, confidence, entry_price, account_balance, max_position_pct
        )
        
        # Check constraints
        # Note: position_value is the leveraged notional, margin is position_value / leverage
        leverage = risk_profile["leverage"]
        margin = risk_profile["position_value"] / leverage if leverage > 0 else 0
        constraints = {
            "min_position_value": risk_profile["position_value"] >= self.risk_context.min_position_value,
            "max_leverage": leverage <= self.max_leverage,
            "confidence_threshold": confidence >= 0.5,  # Minimum confidence
            "cost_efficiency": risk_profile["risk_reward_ratio"] >= 1.0,  # Minimum R:R
            # Check that margin (not leveraged position) doesn't exceed max position percentage
            "position_size": margin <= account_balance * (max_position_pct / 100)
        }
        
        # Determine overall validation
        all_passed = all(constraints.values())
        
        # Generate recommendations
        recommendations = []
        if not constraints["min_position_value"]:
            recommendations.append("Position value too small")
        if not constraints["max_leverage"]:
            recommendations.append("Leverage exceeds maximum")
        if not constraints["confidence_threshold"]:
            recommendations.append("Confidence too low")
        if not constraints["cost_efficiency"]:
            recommendations.append("Risk-reward ratio too low")
        if not constraints["position_size"]:
            recommendations.append("Position size exceeds limits")

        # Create reason string from recommendations for easier logging
        reason = "; ".join(recommendations) if recommendations else "All constraints passed"

        return {
            "valid": all_passed,
            "constraints": constraints,
            "recommendations": recommendations,
            "reason": reason,
            "risk_profile": risk_profile,
            "action": "PROCEED" if all_passed else "REJECT"
        }
    
    def calculate_exit_risk(self, symbol: str, position: Position) -> Dict[str, Any]:
        """
        Calculate risk analysis for position exit.
        
        Returns:
            Dict with exit risk analysis
        """
        pnl_analysis = calculate_net_pnl(position)
        
        # Determine exit strategy
        net_pnl_pct = pnl_analysis["net_pnl"]["percentage"]
        
        if net_pnl_pct >= 5.0:  # High profit
            exit_strategy = "TAKE_PROFIT"
            reason = "High profit target reached"
        elif net_pnl_pct <= -2.0:  # Stop loss
            exit_strategy = "STOP_LOSS"
            reason = "Stop loss triggered"
        elif net_pnl_pct >= 0.5:  # Small profit
            exit_strategy = "PARTIAL_PROFIT"
            reason = "Small profit, consider partial exit"
        else:
            exit_strategy = "HOLD"
            reason = "Position still in acceptable range"
        
        return {
            "symbol": symbol,
            "current_pnl": pnl_analysis["net_pnl"]["amount"],
            "current_pnl_pct": net_pnl_pct,
            "exit_strategy": exit_strategy,
            "reason": reason,
            "pnl_analysis": pnl_analysis,
            "recommendation": f"{exit_strategy}: {reason}"
        }
    
    def get_risk_summary(self, account_balance: float, open_positions: List[Position]) -> Dict[str, Any]:
        """
        Get overall risk summary for the account.
        
        Returns:
            Dict with account risk summary
        """
        total_exposure = sum(pos.position_value for pos in open_positions)
        total_leverage = sum(pos.leverage for pos in open_positions) / len(open_positions) if open_positions else 0
        
        # Calculate total P&L
        total_pnl = 0
        total_costs = 0
        wins = 0
        losses = 0
        
        for pos in open_positions:
            pnl_analysis = calculate_net_pnl(pos)
            total_pnl += pnl_analysis["net_pnl"]["amount"]
            total_costs += pnl_analysis["costs"]["total_costs"]
            
            if pnl_analysis["net_pnl"]["profitable"]:
                wins += 1
            else:
                losses += 1
        
        win_rate = wins / (wins + losses) if (wins + losses) > 0 else 0
        
        return {
            "account_balance": account_balance,
            "total_exposure": total_exposure,
            "exposure_pct": (total_exposure / account_balance) * 100 if account_balance > 0 else 0,
            "avg_leverage": total_leverage,
            "total_pnl": total_pnl,
            "total_costs": total_costs,
            "win_rate": win_rate,
            "wins": wins,
            "losses": losses,
            "risk_metrics": {
                "cost_to_pnl_ratio": total_costs / abs(total_pnl) if total_pnl != 0 else 0,
                "roi": (total_pnl / total_exposure) * 100 if total_exposure > 0 else 0,
                "risk_score": min(100, (total_exposure / account_balance) * 100)
            }
        }
    
    def optimize_position_sizing(self, account_balance: float, opportunities: List[Dict]) -> Dict[str, Any]:
        """
        Optimize position sizing across multiple opportunities.
        
        Args:
            account_balance (float): Available account balance
            opportunities (List[Dict]): List of trading opportunities
        
        Returns:
            Dict with optimized allocation
        """
        # Sort opportunities by confidence
        sorted_opportunities = sorted(opportunities, key=lambda x: x["confidence"], reverse=True)
        
        # Allocate capital based on confidence
        allocations = {}
        remaining_balance = account_balance
        total_allocated = 0
        
        for opp in sorted_opportunities:
            # Calculate position size based on confidence
            confidence_weight = opp["confidence"] / 10.0  # 0.1 to 1.0
            max_allocation = account_balance * 0.1  # Max 10% per position
            allocation = min(max_allocation * confidence_weight, remaining_balance)
            
            if allocation >= self.risk_context.min_position_value:
                allocations[opp["symbol"]] = allocation
                remaining_balance -= allocation
                total_allocated += allocation
        
        return {
            "allocations": allocations,
            "total_allocated": total_allocated,
            "remaining_balance": remaining_balance,
            "allocation_strategy": "confidence_weighted"
        }


# Example usage and testing
if __name__ == "__main__":
    print("🧪 Risk Management Integration Test Results:")
    print("=" * 60)
    
    # Initialize risk manager
    risk_manager = RiskManager(max_leverage=20)
    
    # Test case 1: Position risk calculation
    print("\nTest Case 1: Position Risk Calculation")
    risk_manager.set_risk_context(confidence=0.8, volatility=0.03, drawdown=0.02, tokens_used=5000)
    
    risk_profile = risk_manager.calculate_position_risk(
        symbol="BTC",
        action="BUY",
        confidence=0.8,
        entry_price=50000,
        account_balance=10000
    )
    
    print(f"  Symbol: {risk_profile['symbol']}")
    print(f"  Action: {risk_profile['action']}")
    print(f"  Leverage: {risk_profile['leverage']}x")
    print(f"  Position Value: ${risk_profile['position_value']:.2f}")
    print(f"  TP: {risk_profile['tp_pct']:.1f}% (${risk_profile['tp_price']:.2f})")
    print(f"  SL: {risk_profile['sl_pct']:.1f}% (${risk_profile['sl_price']:.2f})")
    print(f"  Risk-Reward: {risk_profile['risk_reward_ratio']:.2f}:1")
    
    # Test case 2: Trade validation
    print("\nTest Case 2: Trade Validation")
    validation = risk_manager.validate_trade_decision(
        symbol="ETH",
        action="BUY",
        confidence=0.7,
        entry_price=3000,
        account_balance=5000
    )
    
    print(f"  Valid: {validation['valid']}")
    print(f"  Action: {validation['action']}")
    print(f"  Constraints: {validation['constraints']}")
    
    # Test case 3: Exit risk analysis
    print("\nTest Case 3: Exit Risk Analysis")
    test_position = Position(
        symbol="SOL",
        direction="LONG",
        entry_price=100,
        exit_price=105,
        position_value=1000,
        leverage=10,
        order_type="taker",
        tokens_used=3000
    )
    
    exit_analysis = risk_manager.calculate_exit_risk("SOL", test_position)
    print(f"  Current P&L: ${exit_analysis['current_pnl']:.2f} ({exit_analysis['current_pnl_pct']:.2f}%)")
    print(f"  Exit Strategy: {exit_analysis['exit_strategy']}")
    print(f"  Reason: {exit_analysis['reason']}")
    
    # Test case 4: Account risk summary
    print("\nTest Case 4: Account Risk Summary")
    positions = [
        Position("BTC", "LONG", 50000, 51000, 2000, 10, "taker", 5000),
        Position("ETH", "SHORT", 3000, 2950, 1000, 5, "maker", 3000),
    ]
    
    risk_summary = risk_manager.get_risk_summary(10000, positions)
    print(f"  Account Balance: ${risk_summary['account_balance']:.2f}")
    print(f"  Total Exposure: ${risk_summary['total_exposure']:.2f} ({risk_summary['exposure_pct']:.1f}%)")
    print(f"  Total P&L: ${risk_summary['total_pnl']:.2f}")
    print(f"  Win Rate: {risk_summary['win_rate']:.1%}")
    print(f"  ROI: {risk_summary['risk_metrics']['roi']:.2f}%")