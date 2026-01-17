"""
Unit Tests for TradeRecorder

Tests the TradeRecorder class for trade logging,
retrieval, and statistics calculation.
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
import sys
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.data.trade_recorder import TradeRecorder, TradeRecord


class TestTradeRecorder:
    """Tests for TradeRecorder class."""

    @pytest.fixture
    def temp_data_dir(self):
        """Create a temporary directory for test data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def recorder(self, temp_data_dir):
        """Create a TradeRecorder with temporary storage."""
        return TradeRecorder(data_dir=temp_data_dir, max_trades=100)

    def test_record_trade_basic(self, recorder):
        """Test recording a basic trade."""
        trade = recorder.record_trade(
            symbol="BTC",
            side="LONG",
            action="OPEN",
            notional=1000.0,
            reason="Test trade"
        )

        assert trade.symbol == "BTC"
        assert trade.side == "LONG"
        assert trade.action == "OPEN"
        assert trade.notional == 1000.0
        assert trade.trade_id.startswith("TRD_")

    def test_record_trade_with_pnl(self, recorder):
        """Test recording a trade with P&L."""
        trade = recorder.record_trade(
            symbol="ETH",
            side="SHORT",
            action="CLOSE",
            notional=500.0,
            pnl=25.50,
            entry_price=2000.0,
            exit_price=1950.0
        )

        assert trade.pnl == 25.50
        assert trade.entry_price == 2000.0
        assert trade.exit_price == 1950.0

    def test_get_recent_trades(self, recorder):
        """Test retrieving recent trades."""
        # Record multiple trades
        for i in range(5):
            recorder.record_trade(
                symbol=f"TOKEN{i}",
                side="LONG",
                action="OPEN",
                notional=100.0 * (i + 1)
            )

        trades = recorder.get_recent_trades(limit=3)

        assert len(trades) == 3
        # Should be newest first
        assert trades[0]["symbol"] == "TOKEN4"

    def test_get_trades_by_symbol(self, recorder):
        """Test filtering trades by symbol."""
        recorder.record_trade(symbol="BTC", side="LONG", action="OPEN", notional=100)
        recorder.record_trade(symbol="ETH", side="LONG", action="OPEN", notional=200)
        recorder.record_trade(symbol="BTC", side="LONG", action="CLOSE", notional=100, pnl=10)

        btc_trades = recorder.get_trades_by_symbol("BTC")

        assert len(btc_trades) == 2
        assert all(t["symbol"] == "BTC" for t in btc_trades)

    def test_get_closed_trades(self, recorder):
        """Test retrieving only closed trades."""
        recorder.record_trade(symbol="BTC", side="LONG", action="OPEN", notional=100)
        recorder.record_trade(symbol="BTC", side="LONG", action="CLOSE", notional=100, pnl=10)
        recorder.record_trade(symbol="ETH", side="SHORT", action="OPEN", notional=200)
        recorder.record_trade(symbol="ETH", side="SHORT", action="CLOSE", notional=200, pnl=-5)

        closed = recorder.get_closed_trades()

        assert len(closed) == 2
        assert all(t["action"] == "CLOSE" for t in closed)

    def test_calculate_statistics_empty(self, recorder):
        """Test statistics with no trades."""
        stats = recorder.calculate_statistics()

        assert stats["total_trades"] == 0
        assert stats["win_rate"] == 0.0

    def test_calculate_statistics_with_trades(self, recorder):
        """Test statistics calculation with trades."""
        # Record winning trades
        recorder.record_trade(symbol="BTC", side="LONG", action="CLOSE", notional=100, pnl=20)
        recorder.record_trade(symbol="ETH", side="LONG", action="CLOSE", notional=100, pnl=15)
        recorder.record_trade(symbol="SOL", side="LONG", action="CLOSE", notional=100, pnl=10)

        # Record losing trade
        recorder.record_trade(symbol="DOGE", side="LONG", action="CLOSE", notional=100, pnl=-5)

        stats = recorder.calculate_statistics()

        assert stats["closed_trades"] == 4
        assert stats["total_pnl"] == 40.0  # 20 + 15 + 10 - 5
        assert stats["win_rate"] == 75.0  # 3/4
        assert stats["best_trade"] == 20.0
        assert stats["worst_trade"] == -5.0

    def test_symbol_performance(self, recorder):
        """Test per-symbol performance calculation."""
        recorder.record_trade(symbol="BTC", side="LONG", action="CLOSE", notional=100, pnl=50)
        recorder.record_trade(symbol="BTC", side="LONG", action="CLOSE", notional=100, pnl=30)
        recorder.record_trade(symbol="ETH", side="LONG", action="CLOSE", notional=100, pnl=-10)

        btc_perf = recorder.get_symbol_performance("BTC")

        assert btc_perf["symbol"] == "BTC"
        assert btc_perf["closed_trades"] == 2
        assert btc_perf["total_pnl"] == 80.0
        assert btc_perf["win_rate"] == 100.0

    def test_max_trades_limit(self, temp_data_dir):
        """Test that trades are trimmed to max limit."""
        recorder = TradeRecorder(data_dir=temp_data_dir, max_trades=5)

        # Record more trades than the limit
        for i in range(10):
            recorder.record_trade(
                symbol=f"TOKEN{i}",
                side="LONG",
                action="OPEN",
                notional=100
            )

        # Load trades directly from file
        with open(recorder.trades_file, 'r') as f:
            trades = json.load(f)

        assert len(trades) == 5
        # Should keep the newest 5
        assert trades[0]["symbol"] == "TOKEN5"

    def test_trade_record_to_dict(self):
        """Test TradeRecord dataclass conversion to dict."""
        record = TradeRecord(
            timestamp="2024-01-17T12:00:00",
            symbol="BTC",
            side="LONG",
            action="OPEN",
            notional=1000.0,
            pnl=0.0,
            entry_price=42000.0,
            exit_price=0.0,
            reason="Test",
            strategy="AI_ALLOCATION",
            confidence=75,
            market_conditions={"rsi": 55},
            trade_id="TRD_001"
        )

        d = record.to_dict()

        assert d["symbol"] == "BTC"
        assert d["confidence"] == 75
        assert d["market_conditions"]["rsi"] == 55


class TestSignalRecorder:
    """Tests for SignalRecorder class."""

    @pytest.fixture
    def temp_data_dir(self):
        """Create a temporary directory for test data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def recorder(self, temp_data_dir):
        """Create a SignalRecorder with temporary storage."""
        from src.data.signal_recorder import SignalRecorder
        return SignalRecorder(data_dir=temp_data_dir, max_signals=100)

    def test_record_signal(self, recorder):
        """Test recording a signal."""
        signal = recorder.record_signal(
            symbol="BTC",
            signal="BUY",
            confidence=80,
            reasoning="Strong bullish momentum"
        )

        assert signal.symbol == "BTC"
        assert signal.signal == "BUY"
        assert signal.confidence == 80

    def test_get_actionable_signals(self, recorder):
        """Test filtering for actionable signals (BUY/SELL only)."""
        recorder.record_signal(symbol="BTC", signal="BUY", confidence=80)
        recorder.record_signal(symbol="ETH", signal="NOTHING", confidence=40)
        recorder.record_signal(symbol="SOL", signal="SELL", confidence=70)

        actionable = recorder.get_actionable_signals()

        assert len(actionable) == 2
        assert all(s["signal"] in ["BUY", "SELL"] for s in actionable)

    def test_update_signal_outcome(self, recorder):
        """Test updating signal with outcome."""
        signal = recorder.record_signal(
            symbol="BTC",
            signal="BUY",
            confidence=80,
            price_at_signal=42000.0
        )

        success = recorder.update_signal_outcome(
            signal_id=signal.signal_id,
            outcome="WIN",
            price_at_outcome=43000.0,
            pnl_percent=2.38
        )

        assert success

        # Verify the update
        signals = recorder.get_recent_signals(limit=1)
        assert signals[0]["outcome"] == "WIN"
        assert signals[0]["pnl_percent"] == 2.38


class TestPerformanceCalculator:
    """Tests for PerformanceCalculator class."""

    @pytest.fixture
    def temp_data_dir(self):
        """Create a temporary directory for test data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def calculator(self, temp_data_dir):
        """Create a PerformanceCalculator with temporary storage."""
        from src.data.performance_calculator import PerformanceCalculator
        return PerformanceCalculator(data_dir=temp_data_dir)

    @pytest.fixture
    def populated_calculator(self, temp_data_dir):
        """Create a calculator with some trade data."""
        from src.data.performance_calculator import PerformanceCalculator

        # Create trades.json with test data
        trades = [
            {"timestamp": "2024-01-17T10:00:00", "symbol": "BTC", "action": "CLOSE", "pnl": 100},
            {"timestamp": "2024-01-17T11:00:00", "symbol": "ETH", "action": "CLOSE", "pnl": 50},
            {"timestamp": "2024-01-17T12:00:00", "symbol": "SOL", "action": "CLOSE", "pnl": -30},
            {"timestamp": "2024-01-17T13:00:00", "symbol": "BTC", "action": "CLOSE", "pnl": 75},
        ]

        trades_file = temp_data_dir / "trades.json"
        with open(trades_file, 'w') as f:
            json.dump(trades, f)

        return PerformanceCalculator(data_dir=temp_data_dir)

    def test_calculate_metrics_empty(self, calculator):
        """Test metrics with no trades."""
        metrics = calculator.calculate_metrics()

        assert metrics["total_trades"] == 0
        assert metrics["win_rate"] == 0.0

    def test_calculate_metrics_with_data(self, populated_calculator):
        """Test metrics calculation with trade data."""
        metrics = populated_calculator.calculate_metrics()

        assert metrics["closed_trades"] == 4
        assert metrics["total_pnl"] == 195.0  # 100 + 50 - 30 + 75
        assert metrics["win_rate"] == 75.0  # 3/4 wins
        assert metrics["largest_win"] == 100.0
        assert metrics["largest_loss"] == -30.0

    def test_profit_factor(self, populated_calculator):
        """Test profit factor calculation."""
        metrics = populated_calculator.calculate_metrics()

        # Total wins: 225, Total losses: 30
        # Profit factor: 225 / 30 = 7.5
        assert metrics["profit_factor"] == 7.5

    def test_get_symbol_breakdown(self, populated_calculator):
        """Test symbol-based performance breakdown."""
        breakdown = populated_calculator.get_symbol_breakdown()

        assert len(breakdown) == 3  # BTC, ETH, SOL

        # Should be sorted by PnL descending
        assert breakdown[0]["symbol"] == "BTC"
        assert breakdown[0]["pnl"] == 175.0  # 100 + 75

    def test_get_daily_breakdown(self, populated_calculator):
        """Test daily performance breakdown."""
        daily = populated_calculator.get_daily_breakdown(days=7)

        # All trades are on 2024-01-17
        assert len(daily) == 1
        assert daily[0]["pnl"] == 195.0
        assert daily[0]["trades"] == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
