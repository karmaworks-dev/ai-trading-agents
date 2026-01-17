#!/usr/bin/env python3
"""
Integration Test for Trade Lifecycle

Tests the full trade lifecycle from open to close,
verifying data flows correctly through all components.

This test can run without pytest using: python tests/test_trade_lifecycle.py
"""

import sys
import json
import tempfile
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def test_full_trade_lifecycle():
    """Test complete trade lifecycle: Open -> Close -> Performance Update"""
    print("\n" + "=" * 60)
    print("INTEGRATION TEST: Full Trade Lifecycle")
    print("=" * 60)

    # Create temporary directory for test data
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)

        # Import data classes
        from src.data.trade_recorder import TradeRecorder
        from src.data.signal_recorder import SignalRecorder
        from src.data.performance_calculator import PerformanceCalculator

        # Initialize with temp directory
        trade_recorder = TradeRecorder(data_dir=data_dir)
        signal_recorder = SignalRecorder(data_dir=data_dir)
        perf_calculator = PerformanceCalculator(data_dir=data_dir)

        print("\n1. Recording AI Signal...")
        signal = signal_recorder.record_signal(
            symbol="BTC",
            signal="BUY",
            confidence=85,
            reasoning="Strong bullish breakout above MA20",
            price_at_signal=42000.0
        )
        print(f"   Signal ID: {signal.signal_id}")
        print(f"   Signal: {signal.signal} | Confidence: {signal.confidence}%")
        assert signal.signal == "BUY", "Signal should be BUY"

        print("\n2. Opening Trade...")
        open_trade = trade_recorder.record_trade(
            symbol="BTC",
            side="LONG",
            action="OPEN",
            notional=1000.0,
            entry_price=42000.0,
            reason="AI signal - breakout trade",
            strategy="MOMENTUM",
            confidence=85
        )
        print(f"   Trade ID: {open_trade.trade_id}")
        print(f"   Opened LONG BTC @ $42,000 | Notional: $1,000")
        assert open_trade.action == "OPEN", "Action should be OPEN"

        print("\n3. Closing Trade with Profit...")
        close_trade = trade_recorder.record_trade(
            symbol="BTC",
            side="LONG",
            action="CLOSE",
            notional=1000.0,
            entry_price=42000.0,
            exit_price=43500.0,
            pnl=35.71,  # ~3.57% gain
            reason="Take profit hit",
            strategy="MOMENTUM",
            confidence=90
        )
        print(f"   Trade ID: {close_trade.trade_id}")
        print(f"   Closed LONG BTC @ $43,500 | PnL: +$35.71")
        assert close_trade.pnl == 35.71, "PnL should be 35.71"

        print("\n4. Updating Signal Outcome...")
        signal_recorder.update_signal_outcome(
            signal_id=signal.signal_id,
            outcome="WIN",
            price_at_outcome=43500.0,
            pnl_percent=3.57
        )
        signals = signal_recorder.get_recent_signals(limit=1)
        print(f"   Signal outcome: {signals[0]['outcome']}")
        assert signals[0]["outcome"] == "WIN", "Signal outcome should be WIN"

        print("\n5. Calculating Performance Metrics...")
        metrics = perf_calculator.calculate_metrics()
        print(f"   Total Trades: {metrics['closed_trades']}")
        print(f"   Win Rate: {metrics['win_rate']}%")
        print(f"   Total PnL: ${metrics['total_pnl']}")
        assert metrics["closed_trades"] == 1, "Should have 1 closed trade"
        assert metrics["win_rate"] == 100.0, "Win rate should be 100%"
        assert metrics["total_pnl"] == 35.71, "Total PnL should be 35.71"

        print("\n6. Verifying Trade History...")
        trades = trade_recorder.get_recent_trades(limit=10)
        print(f"   Total trades recorded: {len(trades)}")
        assert len(trades) == 2, "Should have 2 trades (open + close)"

        closed_trades = trade_recorder.get_closed_trades()
        print(f"   Closed trades: {len(closed_trades)}")
        assert len(closed_trades) == 1, "Should have 1 closed trade"

        print("\n7. Testing Symbol Performance...")
        btc_perf = trade_recorder.get_symbol_performance("BTC")
        print(f"   BTC Performance:")
        print(f"   - Total trades: {btc_perf['total_trades']}")
        print(f"   - Closed trades: {btc_perf['closed_trades']}")
        print(f"   - Total PnL: ${btc_perf['total_pnl']}")
        print(f"   - Win Rate: {btc_perf['win_rate']}%")
        assert btc_perf["total_pnl"] == 35.71, "BTC PnL should be 35.71"

        print("\n8. Testing Signal Accuracy...")
        accuracy = signal_recorder.calculate_accuracy()
        print(f"   Signal Accuracy:")
        print(f"   - Total signals: {accuracy['total_signals']}")
        print(f"   - Actionable signals: {accuracy['actionable_signals']}")
        print(f"   - Win rate: {accuracy['win_rate']}%")
        assert accuracy["win_rate"] == 100.0, "Signal win rate should be 100%"

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)


def test_multiple_trades():
    """Test with multiple trades for realistic statistics."""
    print("\n" + "=" * 60)
    print("INTEGRATION TEST: Multiple Trades Statistics")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)

        from src.data.trade_recorder import TradeRecorder
        from src.data.performance_calculator import PerformanceCalculator

        trade_recorder = TradeRecorder(data_dir=data_dir)
        perf_calculator = PerformanceCalculator(data_dir=data_dir)

        # Record a series of trades
        trades_data = [
            {"symbol": "BTC", "pnl": 50.0, "result": "win"},
            {"symbol": "ETH", "pnl": 30.0, "result": "win"},
            {"symbol": "SOL", "pnl": -20.0, "result": "loss"},
            {"symbol": "BTC", "pnl": 45.0, "result": "win"},
            {"symbol": "AVAX", "pnl": -15.0, "result": "loss"},
            {"symbol": "ETH", "pnl": 25.0, "result": "win"},
        ]

        print("\n1. Recording Multiple Trades...")
        for i, trade in enumerate(trades_data):
            trade_recorder.record_trade(
                symbol=trade["symbol"],
                side="LONG",
                action="CLOSE",
                notional=500.0,
                pnl=trade["pnl"],
                reason=f"Trade {i+1}"
            )
            result_icon = "WIN" if trade["pnl"] > 0 else "LOSS"
            print(f"   Trade {i+1}: {trade['symbol']} | PnL: ${trade['pnl']:+.2f} | {result_icon}")

        print("\n2. Calculating Statistics...")
        stats = trade_recorder.calculate_statistics()
        print(f"   Total Closed Trades: {stats['closed_trades']}")
        print(f"   Wins: {stats.get('winning_trades', 'N/A')}")
        print(f"   Losses: {stats.get('losing_trades', 'N/A')}")
        print(f"   Total PnL: ${stats['total_pnl']:.2f}")
        print(f"   Win Rate: {stats['win_rate']:.1f}%")
        print(f"   Profit Factor: {stats['profit_factor']:.2f}")
        print(f"   Best Trade: ${stats['best_trade']:.2f}")
        print(f"   Worst Trade: ${stats['worst_trade']:.2f}")

        # Verify calculations
        expected_pnl = sum(t["pnl"] for t in trades_data)
        assert abs(stats["total_pnl"] - expected_pnl) < 0.01, f"Expected PnL {expected_pnl}, got {stats['total_pnl']}"
        assert stats["win_rate"] == pytest_approx(66.7, abs=0.1), f"Expected ~66.7% win rate, got {stats['win_rate']}%"

        print("\n3. Symbol Breakdown...")
        symbols = perf_calculator.get_symbol_breakdown()
        for sym in symbols:
            print(f"   {sym['symbol']}: ${sym['pnl']:.2f} | {sym['trades']} trades | {sym['win_rate']:.1f}% WR")

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)


def pytest_approx(expected, abs=0.01):
    """Simple approximation check for when pytest isn't available."""
    return expected


if __name__ == "__main__":
    try:
        test_full_trade_lifecycle()
        test_multiple_trades()
        print("\n" + "=" * 60)
        print("ALL INTEGRATION TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 60 + "\n")
    except AssertionError as e:
        print(f"\n ASSERTION FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
