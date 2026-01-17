"""
Performance Calculator - Calculates and tracks trading performance metrics.

This module provides a PerformanceCalculator class for computing
comprehensive trading metrics from trade history.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

try:
    from termcolor import cprint
except ImportError:
    def cprint(msg, *args, **kwargs):
        print(msg)


@dataclass
class PerformanceSnapshot:
    """Snapshot of performance metrics at a point in time."""
    timestamp: str
    total_pnl: float
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    avg_trade_duration: float  # in hours
    balance: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class PerformanceCalculator:
    """
    Calculates comprehensive trading performance metrics.

    Features:
    - Calculates key metrics: win rate, profit factor, Sharpe ratio
    - Tracks drawdown and equity curve
    - Provides daily/weekly/monthly breakdowns
    - Generates performance snapshots for historical tracking
    """

    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize PerformanceCalculator.

        Args:
            data_dir: Directory for storing performance data. Defaults to src/data/
        """
        if data_dir is None:
            self.data_dir = Path(__file__).parent
        else:
            self.data_dir = Path(data_dir)

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.performance_file = self.data_dir / "performance_history.json"
        self.trades_file = self.data_dir / "trades.json"

    def _load_trades(self) -> List[Dict[str, Any]]:
        """Load trades from file."""
        if not self.trades_file.exists():
            return []

        try:
            with open(self.trades_file, 'r') as f:
                content = f.read()
                return json.loads(content) if content.strip() else []
        except (json.JSONDecodeError, IOError):
            return []

    def _load_performance_history(self) -> List[Dict[str, Any]]:
        """Load performance history."""
        if not self.performance_file.exists():
            return []

        try:
            with open(self.performance_file, 'r') as f:
                content = f.read()
                return json.loads(content) if content.strip() else []
        except (json.JSONDecodeError, IOError):
            return []

    def _save_performance_history(self, history: List[Dict[str, Any]]) -> None:
        """Save performance history."""
        try:
            # Keep last 365 days of snapshots
            history = history[-365:]
            with open(self.performance_file, 'w') as f:
                json.dump(history, f, indent=2)
        except IOError as e:
            cprint(f"   Error saving performance history: {e}", "red")

    def calculate_metrics(self, trades: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Calculate comprehensive performance metrics.

        Args:
            trades: Optional list of trades. If None, loads from file.

        Returns:
            Dictionary of performance metrics
        """
        if trades is None:
            trades = self._load_trades()

        closed_trades = [t for t in trades if t.get("action", "").upper() == "CLOSE"]

        if not closed_trades:
            return {
                "total_trades": len(trades),
                "closed_trades": 0,
                "total_pnl": 0.0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "largest_win": 0.0,
                "largest_loss": 0.0,
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0,
                "expectancy": 0.0
            }

        pnls = [t.get("pnl", 0) for t in closed_trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]

        total_wins = sum(wins) if wins else 0
        total_losses = abs(sum(losses)) if losses else 0

        # Calculate drawdown
        equity_curve = []
        running_total = 0
        for pnl in pnls:
            running_total += pnl
            equity_curve.append(running_total)

        max_drawdown = self._calculate_max_drawdown(equity_curve)

        # Calculate Sharpe ratio (simplified - assuming risk-free rate of 0)
        sharpe = self._calculate_sharpe_ratio(pnls)

        # Calculate expectancy
        win_rate = len(wins) / len(closed_trades) if closed_trades else 0
        avg_win = total_wins / len(wins) if wins else 0
        avg_loss = total_losses / len(losses) if losses else 0
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)

        return {
            "total_trades": len(trades),
            "closed_trades": len(closed_trades),
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "total_pnl": round(sum(pnls), 2),
            "win_rate": round(win_rate * 100, 1),
            "profit_factor": round(total_wins / total_losses, 2) if total_losses > 0 else float('inf'),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "largest_win": round(max(pnls), 2) if pnls else 0,
            "largest_loss": round(min(pnls), 2) if pnls else 0,
            "max_drawdown": round(max_drawdown, 2),
            "sharpe_ratio": round(sharpe, 2),
            "expectancy": round(expectancy, 2)
        }

    def _calculate_max_drawdown(self, equity_curve: List[float]) -> float:
        """Calculate maximum drawdown from equity curve."""
        if not equity_curve:
            return 0.0

        max_drawdown = 0
        peak = equity_curve[0]

        for value in equity_curve:
            if value > peak:
                peak = value
            drawdown = peak - value
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        return max_drawdown

    def _calculate_sharpe_ratio(self, pnls: List[float], periods_per_year: int = 365) -> float:
        """
        Calculate simplified Sharpe ratio.

        Args:
            pnls: List of P&L values
            periods_per_year: Number of periods in a year

        Returns:
            Sharpe ratio
        """
        if len(pnls) < 2:
            return 0.0

        import statistics
        mean_return = statistics.mean(pnls)
        std_dev = statistics.stdev(pnls)

        if std_dev == 0:
            return 0.0

        # Annualized Sharpe ratio
        return (mean_return / std_dev) * (periods_per_year ** 0.5)

    def get_daily_breakdown(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get daily performance breakdown.

        Args:
            days: Number of days to include

        Returns:
            List of daily performance summaries
        """
        trades = self._load_trades()
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff.isoformat()

        daily_data = {}

        for trade in trades:
            timestamp = trade.get("timestamp", "")
            if timestamp < cutoff_str:
                continue

            if trade.get("action", "").upper() != "CLOSE":
                continue

            # Extract date
            date_str = timestamp[:10]  # YYYY-MM-DD
            if date_str not in daily_data:
                daily_data[date_str] = {"pnl": 0, "trades": 0, "wins": 0}

            pnl = trade.get("pnl", 0)
            daily_data[date_str]["pnl"] += pnl
            daily_data[date_str]["trades"] += 1
            if pnl > 0:
                daily_data[date_str]["wins"] += 1

        # Format output
        result = []
        for date_str in sorted(daily_data.keys()):
            data = daily_data[date_str]
            win_rate = (data["wins"] / data["trades"] * 100) if data["trades"] > 0 else 0
            result.append({
                "date": date_str,
                "pnl": round(data["pnl"], 2),
                "trades": data["trades"],
                "win_rate": round(win_rate, 1)
            })

        return result

    def get_symbol_breakdown(self) -> List[Dict[str, Any]]:
        """
        Get performance breakdown by symbol.

        Returns:
            List of symbol performance summaries
        """
        trades = self._load_trades()
        symbol_data = {}

        for trade in trades:
            if trade.get("action", "").upper() != "CLOSE":
                continue

            symbol = trade.get("symbol", "UNKNOWN")
            if symbol not in symbol_data:
                symbol_data[symbol] = {"pnl": 0, "trades": 0, "wins": 0}

            pnl = trade.get("pnl", 0)
            symbol_data[symbol]["pnl"] += pnl
            symbol_data[symbol]["trades"] += 1
            if pnl > 0:
                symbol_data[symbol]["wins"] += 1

        # Format and sort by PnL
        result = []
        for symbol, data in symbol_data.items():
            win_rate = (data["wins"] / data["trades"] * 100) if data["trades"] > 0 else 0
            result.append({
                "symbol": symbol,
                "pnl": round(data["pnl"], 2),
                "trades": data["trades"],
                "win_rate": round(win_rate, 1)
            })

        return sorted(result, key=lambda x: x["pnl"], reverse=True)

    def create_snapshot(self, balance: float = 0.0) -> PerformanceSnapshot:
        """
        Create a performance snapshot for historical tracking.

        Args:
            balance: Current account balance

        Returns:
            PerformanceSnapshot object
        """
        metrics = self.calculate_metrics()

        snapshot = PerformanceSnapshot(
            timestamp=datetime.now().isoformat(),
            total_pnl=metrics["total_pnl"],
            win_rate=metrics["win_rate"],
            profit_factor=metrics["profit_factor"] if metrics["profit_factor"] != float('inf') else 999.99,
            sharpe_ratio=metrics["sharpe_ratio"],
            max_drawdown=metrics["max_drawdown"],
            total_trades=metrics["closed_trades"],
            winning_trades=metrics["winning_trades"],
            losing_trades=metrics["losing_trades"],
            avg_win=metrics["avg_win"],
            avg_loss=metrics["avg_loss"],
            largest_win=metrics["largest_win"],
            largest_loss=metrics["largest_loss"],
            avg_trade_duration=0.0,  # Would need trade timestamps to calculate
            balance=balance
        )

        # Save to history
        history = self._load_performance_history()
        history.append(snapshot.to_dict())
        self._save_performance_history(history)

        return snapshot

    def get_performance_history(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get historical performance snapshots.

        Args:
            days: Number of days of history to return

        Returns:
            List of performance snapshots
        """
        history = self._load_performance_history()
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff.isoformat()

        return [h for h in history if h.get("timestamp", "") > cutoff_str]

    def get_summary_for_dashboard(self) -> Dict[str, Any]:
        """
        Get a summary suitable for dashboard display.

        Returns:
            Simplified metrics for dashboard
        """
        metrics = self.calculate_metrics()

        return {
            "total_pnl": f"${metrics['total_pnl']:,.2f}",
            "win_rate": f"{metrics['win_rate']:.1f}%",
            "profit_factor": f"{metrics['profit_factor']:.2f}" if metrics['profit_factor'] != float('inf') else "INF",
            "total_trades": metrics["closed_trades"],
            "best_trade": f"${metrics['largest_win']:,.2f}",
            "worst_trade": f"${metrics['largest_loss']:,.2f}",
            "max_drawdown": f"${metrics['max_drawdown']:,.2f}"
        }


# Global instance
_global_calculator: Optional[PerformanceCalculator] = None


def get_performance_calculator() -> PerformanceCalculator:
    """Get or create the global PerformanceCalculator instance."""
    global _global_calculator
    if _global_calculator is None:
        _global_calculator = PerformanceCalculator()
    return _global_calculator
