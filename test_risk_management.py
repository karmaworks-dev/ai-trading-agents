#!/usr/bin/env python3
"""
🧪 Risk Management System Test Script

Test the new risk management modules for Phase 3: Smart Execution & Risk Management

Built with love by Karma Dev 🚀
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).resolve().parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# Import risk management modules
try:
    from src.risk.leverage_calculator import calculate_smart_leverage, get_leverage_details
    from src.risk.tp_sl_calculator import calculate_dynamic_tp_sl, get_position_tp_sl_recommendation
    from src.risk.fee_calculator import calculate_total_trade_cost, get_fee_summary
    from src.risk.pnl_calculator import calculate_net_pnl, Position
    from src.risk.risk_manager import RiskManager
    print("✅ All risk management modules imported successfully!")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


def test_leverage_calculator():
    """Test smart leverage calculation"""
    print("\n🧪 Testing Leverage Calculator...")
    print("=" * 50)
    
    test_cases = [
        {"confidence": 0.9, "volatility": 0.02, "drawdown": 0.01, "max_leverage": 20},
        {"confidence": 0.7, "volatility": 0.08, "drawdown": 0.02, "max_leverage": 20},
        {"confidence": 0.5, "volatility": 0.03, "drawdown": 0.08, "max_leverage": 20},
        {"confidence": 0.3, "volatility": 0.10, "drawdown": 0.12, "max_leverage": 20},
    ]
    
    for i, case in enumerate(test_cases, 1):
        leverage = calculate_smart_leverage(**case)
        details = get_leverage_details(**case)
        
        print(f"\nTest Case {i}:")
        print(f"  Confidence: {case['confidence']}")
        print(f"  Volatility: {case['volatility']}")
        print(f"  Drawdown: {case['drawdown']}")
        print(f"  Max Leverage: {case['max_leverage']}")
        print(f"  Calculated Leverage: {leverage}x")
        print(f"  Risk Level: {details['risk_level']}")
        print(f"  Confidence Level: {details['confidence_level']}")


def test_tp_sl_calculator():
    """Test dynamic TP/SL calculation"""
    print("\n🧪 Testing TP/SL Calculator...")
    print("=" * 50)
    
    test_cases = [
        {"confidence": 0.9, "entry_price": 100.0},
        {"confidence": 0.7, "entry_price": 50.0},
        {"confidence": 0.5, "entry_price": 200.0},
        {"confidence": 0.3, "entry_price": 75.0},
    ]
    
    for i, case in enumerate(test_cases, 1):
        tp_pct, sl_pct = calculate_dynamic_tp_sl(case["confidence"])
        recommendation = get_position_tp_sl_recommendation(
            entry_price=case["entry_price"],
            confidence=case["confidence"],
            position_type="LONG"
        )
        
        print(f"\nTest Case {i}:")
        print(f"  Confidence: {case['confidence']}")
        print(f"  Entry Price: ${case['entry_price']}")
        print(f"  TP: {tp_pct:.1f}% (${recommendation['price_levels']['take_profit_price']:.2f})")
        print(f"  SL: {sl_pct:.1f}% (${recommendation['price_levels']['stop_loss_price']:.2f})")
        print(f"  Risk-Reward: {recommendation['price_levels']['take_profit_pct'] / abs(recommendation['price_levels']['stop_loss_pct']):.2f}:1")


def test_fee_calculator():
    """Test Hyperliquid fee calculation"""
    print("\n🧪 Testing Fee Calculator...")
    print("=" * 50)
    
    test_cases = [
        {"position_value": 1000.0, "order_type": "taker", "tokens_used": 5000},
        {"position_value": 500.0, "order_type": "maker", "tokens_used": 3000},
        {"position_value": 2000.0, "order_type": "taker", "tokens_used": 8000},
        {"position_value": 250.0, "order_type": "maker", "tokens_used": 2000},
    ]
    
    for i, case in enumerate(test_cases, 1):
        summary = get_fee_summary(**case)
        
        print(f"\nTest Case {i}:")
        print(f"  Position Value: ${case['position_value']}")
        print(f"  Order Type: {case['order_type']}")
        print(f"  Tokens Used: {case['tokens_used']}")
        print(f"  Exchange Fee: {summary['fee_summary']['exchange_fee']}")
        print(f"  Slippage Cost: {summary['fee_summary']['slippage_cost']}")
        print(f"  AI Cost: {summary['fee_summary']['ai_cost']}")
        print(f"  Total Cost: {summary['fee_summary']['grand_total']}")
        print(f"  Total Cost %: {summary['percentages']['grand_total_pct']}")


def test_pnl_calculator():
    """Test enhanced P&L calculation"""
    print("\n🧪 Testing P&L Calculator...")
    print("=" * 50)
    
    test_positions = [
        Position("BTC", "LONG", 50000, 52000, 1000, 10, "taker", 5000),
        Position("ETH", "SHORT", 3000, 2800, 500, 5, "maker", 3000),
        Position("SOL", "LONG", 100, 95, 200, 20, "taker", 8000),
        Position("LINK", "SHORT", 20, 21, 100, 15, "taker", 2000),
    ]
    
    for i, position in enumerate(test_positions, 1):
        pnl_analysis = calculate_net_pnl(position)
        
        print(f"\nTest Case {i}: {position.symbol} {position.direction}")
        print(f"  Entry: ${position.entry_price}, Exit: ${position.exit_price}")
        print(f"  Position Value: ${position.position_value}")
        print(f"  Leverage: {position.leverage}x")
        print(f"  Base P&L: ${pnl_analysis['base_pnl']['amount']:.2f} ({pnl_analysis['base_pnl']['percentage']:.2f}%)")
        print(f"  Total Costs: ${pnl_analysis['costs']['total_costs']:.2f} ({pnl_analysis['costs']['total_cost_pct']:.3f}%)")
        print(f"  Net P&L: ${pnl_analysis['net_pnl']['amount']:.2f} ({pnl_analysis['net_pnl']['percentage']:.2f}%)")
        print(f"  Profitable: {pnl_analysis['net_pnl']['profitable']}")


def test_risk_manager():
    """Test integrated risk management system"""
    print("\n🧪 Testing Risk Manager Integration...")
    print("=" * 50)
    
    risk_manager = RiskManager(max_leverage=20)
    
    test_cases = [
        {
            "symbol": "BTC",
            "action": "BUY",
            "confidence": 0.8,
            "entry_price": 50000,
            "account_balance": 10000,
            "volatility": 0.03,
            "drawdown": 0.02,
            "tokens_used": 5000
        },
        {
            "symbol": "ETH",
            "action": "SELL",
            "confidence": 0.6,
            "entry_price": 3000,
            "account_balance": 5000,
            "volatility": 0.05,
            "drawdown": 0.01,
            "tokens_used": 3000
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        # Set risk context
        risk_manager.set_risk_context(
            confidence=case["confidence"],
            volatility=case["volatility"],
            drawdown=case["drawdown"],
            slippage_pct=0.1,
            tokens_used=case["tokens_used"]
        )
        
        # Calculate position risk
        risk_profile = risk_manager.calculate_position_risk(**case)
        
        print(f"\nTest Case {i}: {case['symbol']} {case['action']}")
        print(f"  Confidence: {case['confidence']}")
        print(f"  Entry Price: ${case['entry_price']}")
        print(f"  Account Balance: ${case['account_balance']}")
        print(f"  Calculated Leverage: {risk_profile['leverage']}x")
        print(f"  Position Value: ${risk_profile['position_value']:.2f}")
        print(f"  TP: {risk_profile['tp_pct']:.1f}% (${risk_profile['tp_price']:.2f})")
        print(f"  SL: {risk_profile['sl_pct']:.1f}% (${risk_profile['sl_price']:.2f})")
        print(f"  Risk-Reward: {risk_profile['risk_reward_ratio']:.2f}:1")
        print(f"  Estimated P&L: ${risk_profile['estimated_pnl']:.2f}")
        print(f"  Estimated Costs: ${risk_profile['estimated_costs']:.2f}")


def main():
    """Run all tests"""
    print("🧪 Risk Management System Test Suite")
    print("=" * 60)
    print("Testing Phase 3: Smart Execution & Risk Management")
    print("=" * 60)
    
    try:
        test_leverage_calculator()
        test_tp_sl_calculator()
        test_fee_calculator()
        test_pnl_calculator()
        test_risk_manager()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed successfully!")
        print("🛡️ Risk Management System is ready for integration")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())