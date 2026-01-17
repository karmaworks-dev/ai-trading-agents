"""
Trade Recorder - Enhanced trade logging and retrieval.

This module provides a TradeRecorder class for recording trades
with comprehensive metadata, supporting both dashboard display
and agent learning from past trades.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

# Import logging utilities with fallback
try:
    from src.utils.logging_utils import add_console_log
except ImportError:
    def add_console_log(message, level="info", console_file=None):
        print(f"[TRADE] {message}")

try:
    from termcolor import cprint
except ImportError:
    def cprint(msg, *args, **kwargs):
        print(msg)


@dataclass
class TradeRecord:
    """Structured trade record with all relevant metadata."""
    timestamp: str
    symbol: str
    side: str  # LONG or SHORT
    action: str  # OPEN, CLOSE, REDUCE, INCREASE
    notional: float
    pnl: float
    entry_price: float
    exit_price: float
    reason: str
    strategy: str
    confidence: int
    market_conditions: Dict[str, Any]
    trade_id: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class TradeRecorder:
    """
    Enhanced trade recorder with rich metadata and retrieval capabilities.

    Features:
    - Records trades with comprehensive metadata
    - Supports trade queries by symbol, time range, strategy
    - Calculates running statistics
    - Thread-safe file operations
    """

    def __init__(self, data_dir: Optional[Path] = None, max_trades: int = 500):
        """
        Initialize TradeRecorder.

        Args:
            data_dir: Directory for storing trade data. Defaults to src/data/
            max_trades: Maximum trades to keep in history (oldest removed first)
        """
        if data_dir is None:
            # Default to src/data/ directory
            self.data_dir = Path(__file__).parent
        else:
            self.data_dir = Path(data_dir)

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.trades_file = self.data_dir / "trades.json"
        self.max_trades = max_trades
        self._trade_counter = 0

    def _generate_trade_id(self) -> str:
        """Generate unique trade ID."""
        self._trade_counter += 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"TRD_{timestamp}_{self._trade_counter:04d}"

    def _load_trades(self) -> List[Dict[str, Any]]:
        """Load existing trades from file."""
        if not self.trades_file.exists():
            return []

        try:
            with open(self.trades_file, 'r') as f:
                content = f.read()
                return json.loads(content) if content.strip() else []
        except (json.JSONDecodeError, IOError) as e:
            cprint(f"   Warning: Error loading trades: {e}", "yellow")
            return []

    def _save_trades(self, trades: List[Dict[str, Any]]) -> None:
        """Save trades to file."""
        try:
            with open(self.trades_file, 'w') as f:
                json.dump(trades, f, indent=2)
        except IOError as e:
            cprint(f"   Error saving trades: {e}", "red")

    def record_trade(
        self,
        symbol: str,
        side: str,
        action: str,
        notional: float = 0.0,
        pnl: float = 0.0,
        entry_price: float = 0.0,
        exit_price: float = 0.0,
        reason: str = "",
        strategy: str = "AI_ALLOCATION",
        confidence: int = 0,
        market_conditions: Optional[Dict[str, Any]] = None
    ) -> TradeRecord:
        """
        Record a trade with comprehensive metadata.

        Args:
            symbol: Trading symbol (e.g., "BTC", "ETH")
            side: Position side ("LONG" or "SHORT")
            action: Trade action ("OPEN", "CLOSE", "REDUCE", "INCREASE")
            notional: Position notional value in USD
            pnl: Realized profit/loss (for CLOSE trades)
            entry_price: Entry price
            exit_price: Exit price (for CLOSE trades)
            reason: Reason for trade
            strategy: Strategy name that generated the trade
            confidence: AI confidence score (0-100)
            market_conditions: Optional market context (funding rate, volatility, etc.)

        Returns:
            TradeRecord object
        """
        trade_id = self._generate_trade_id()

        trade = TradeRecord(
            timestamp=datetime.now().isoformat(),
            symbol=symbol.upper(),
            side=side.upper(),
            action=action.upper(),
            notional=round(notional, 2),
            pnl=round(pnl, 2),
            entry_price=round(entry_price, 6) if entry_price else 0.0,
            exit_price=round(exit_price, 6) if exit_price else 0.0,
            reason=reason,
            strategy=strategy,
            confidence=confidence,
            market_conditions=market_conditions or {},
            trade_id=trade_id
        )

        # Load existing trades
        trades = self._load_trades()

        # Add new trade
        trades.append(trade.to_dict())

        # Trim to max trades (keep newest)
        if len(trades) > self.max_trades:
            trades = trades[-self.max_trades:]

        # Save trades
        self._save_trades(trades)

        # Log the trade
        cprint(f"   Trade recorded: {action} {side} {symbol}", "cyan")
        add_console_log(f"Trade: {action} {side} {symbol} ${notional:.2f}", "info")

        # Notify trading_app for position refresh
        try:
            from trading_app import mark_trade_executed
            mark_trade_executed()
        except ImportError:
            pass

        return trade

    def get_recent_trades(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get recent trades for dashboard display.

        Args:
            limit: Maximum number of trades to return

        Returns:
            List of trade dictionaries (newest first)
        """
        trades = self._load_trades()
        # Return newest first
        return list(reversed(trades[-limit:]))

    def get_trades_by_symbol(self, symbol: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get trades for a specific symbol.

        Args:
            symbol: Trading symbol to filter by
            limit: Maximum trades to return

        Returns:
            List of matching trades (newest first)
        """
        trades = self._load_trades()
        symbol_upper = symbol.upper()
        filtered = [t for t in trades if t.get("symbol", "").upper() == symbol_upper]
        return list(reversed(filtered[-limit:]))

    def get_trades_since(self, since_timestamp: str) -> List[Dict[str, Any]]:
        """
        Get trades since a specific timestamp.

        Args:
            since_timestamp: ISO format timestamp

        Returns:
            List of trades since the timestamp
        """
        trades = self._load_trades()
        return [t for t in trades if t.get("timestamp", "") > since_timestamp]

    def get_closed_trades(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get closed trades (trades with PnL).

        Args:
            limit: Maximum trades to return

        Returns:
            List of closed trades
        """
        trades = self._load_trades()
        closed = [t for t in trades if t.get("action", "").upper() == "CLOSE"]
        return list(reversed(closed[-limit:]))

    def calculate_statistics(self) -> Dict[str, Any]:
        """
        Calculate trading statistics from recorded trades.

        Returns:
            Dictionary with trading statistics
        """
        trades = self._load_trades()
        closed_trades = [t for t in trades if t.get("action", "").upper() == "CLOSE"]

        if not closed_trades:
            return {
                "total_trades": len(trades),
                "closed_trades": 0,
                "total_pnl": 0.0,
                "win_rate": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "best_trade": 0.0,
                "worst_trade": 0.0,
                "profit_factor": 0.0
            }

        pnls = [t.get("pnl", 0) for t in closed_trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]

        total_wins = sum(wins) if wins else 0
        total_losses = abs(sum(losses)) if losses else 0

        return {
            "total_trades": len(trades),
            "closed_trades": len(closed_trades),
            "total_pnl": round(sum(pnls), 2),
            "win_rate": round(len(wins) / len(closed_trades) * 100, 1) if closed_trades else 0,
            "avg_win": round(total_wins / len(wins), 2) if wins else 0,
            "avg_loss": round(total_losses / len(losses), 2) if losses else 0,
            "best_trade": round(max(pnls), 2) if pnls else 0,
            "worst_trade": round(min(pnls), 2) if pnls else 0,
            "profit_factor": round(total_wins / total_losses, 2) if total_losses > 0 else float('inf')
        }

    def get_symbol_performance(self, symbol: str) -> Dict[str, Any]:
        """
        Get performance statistics for a specific symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Performance statistics for the symbol
        """
        trades = self.get_trades_by_symbol(symbol, limit=1000)
        closed = [t for t in trades if t.get("action", "").upper() == "CLOSE"]

        if not closed:
            return {
                "symbol": symbol,
                "total_trades": len(trades),
                "closed_trades": 0,
                "total_pnl": 0.0,
                "win_rate": 0.0
            }

        pnls = [t.get("pnl", 0) for t in closed]
        wins = len([p for p in pnls if p > 0])

        return {
            "symbol": symbol,
            "total_trades": len(trades),
            "closed_trades": len(closed),
            "total_pnl": round(sum(pnls), 2),
            "win_rate": round(wins / len(closed) * 100, 1)
        }


# Global instance for backward compatibility with existing save_trade calls
_global_recorder: Optional[TradeRecorder] = None


def get_recorder() -> TradeRecorder:
    """Get or create the global TradeRecorder instance."""
    global _global_recorder
    if _global_recorder is None:
        _global_recorder = TradeRecorder()
    return _global_recorder


def save_trade(
    symbol: str,
    side: str,
    action: str,
    notional: float = 0,
    pnl: float = 0,
    entry_price: float = 0,
    exit_price: float = 0,
    reason: str = ""
) -> None:
    """
    Backward-compatible save_trade function.

    This function wraps TradeRecorder.record_trade() to maintain
    compatibility with existing code that calls save_trade().
    """
    recorder = get_recorder()
    recorder.record_trade(
        symbol=symbol,
        side=side,
        action=action,
        notional=notional,
        pnl=pnl,
        entry_price=entry_price,
        exit_price=exit_price,
        reason=reason
    )
