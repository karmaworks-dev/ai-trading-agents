"""
Signal Recorder - Records AI trading signals for analysis and learning.

This module provides a SignalRecorder class for recording AI-generated
trading signals, enabling analysis of signal accuracy and agent learning.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

try:
    from termcolor import cprint
except ImportError:
    def cprint(msg, *args, **kwargs):
        print(msg)


@dataclass
class SignalRecord:
    """Structured signal record with all relevant metadata."""
    timestamp: str
    symbol: str
    signal: str  # BUY, SELL, NOTHING
    confidence: int  # 0-100
    reasoning: str
    strategy: str
    price_at_signal: float
    market_data: Dict[str, Any]
    signal_id: str
    # Outcome tracking (updated later)
    outcome: Optional[str] = None  # WIN, LOSS, PENDING
    price_at_outcome: Optional[float] = None
    pnl_percent: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class SignalRecorder:
    """
    Records AI trading signals with comprehensive metadata.

    Features:
    - Records signals with confidence and reasoning
    - Tracks signal outcomes for accuracy analysis
    - Supports queries by symbol, strategy, time range
    - Calculates signal accuracy metrics
    """

    def __init__(self, data_dir: Optional[Path] = None, max_signals: int = 1000):
        """
        Initialize SignalRecorder.

        Args:
            data_dir: Directory for storing signal data. Defaults to src/data/
            max_signals: Maximum signals to keep in history
        """
        if data_dir is None:
            self.data_dir = Path(__file__).parent
        else:
            self.data_dir = Path(data_dir)

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.signals_file = self.data_dir / "signals.json"
        self.max_signals = max_signals
        self._signal_counter = 0

    def _generate_signal_id(self) -> str:
        """Generate unique signal ID."""
        self._signal_counter += 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"SIG_{timestamp}_{self._signal_counter:04d}"

    def _load_signals(self) -> List[Dict[str, Any]]:
        """Load existing signals from file."""
        if not self.signals_file.exists():
            return []

        try:
            with open(self.signals_file, 'r') as f:
                content = f.read()
                return json.loads(content) if content.strip() else []
        except (json.JSONDecodeError, IOError) as e:
            cprint(f"   Warning: Error loading signals: {e}", "yellow")
            return []

    def _save_signals(self, signals: List[Dict[str, Any]]) -> None:
        """Save signals to file."""
        try:
            with open(self.signals_file, 'w') as f:
                json.dump(signals, f, indent=2)
        except IOError as e:
            cprint(f"   Error saving signals: {e}", "red")

    def record_signal(
        self,
        symbol: str,
        signal: str,
        confidence: int = 0,
        reasoning: str = "",
        strategy: str = "AI_ANALYSIS",
        price_at_signal: float = 0.0,
        market_data: Optional[Dict[str, Any]] = None
    ) -> SignalRecord:
        """
        Record an AI trading signal.

        Args:
            symbol: Trading symbol
            signal: Signal type ("BUY", "SELL", "NOTHING")
            confidence: Confidence score (0-100)
            reasoning: AI reasoning for the signal
            strategy: Strategy that generated the signal
            price_at_signal: Current price when signal was generated
            market_data: Additional market context

        Returns:
            SignalRecord object
        """
        signal_id = self._generate_signal_id()

        record = SignalRecord(
            timestamp=datetime.now().isoformat(),
            symbol=symbol.upper(),
            signal=signal.upper(),
            confidence=confidence,
            reasoning=reasoning[:500] if reasoning else "",  # Limit length
            strategy=strategy,
            price_at_signal=round(price_at_signal, 6),
            market_data=market_data or {},
            signal_id=signal_id
        )

        # Load existing signals
        signals = self._load_signals()

        # Add new signal
        signals.append(record.to_dict())

        # Trim to max signals
        if len(signals) > self.max_signals:
            signals = signals[-self.max_signals:]

        # Save signals
        self._save_signals(signals)

        cprint(f"   Signal recorded: {signal} {symbol} ({confidence}%)", "cyan")

        return record

    def update_signal_outcome(
        self,
        signal_id: str,
        outcome: str,
        price_at_outcome: float = 0.0,
        pnl_percent: float = 0.0
    ) -> bool:
        """
        Update a signal with its outcome.

        Args:
            signal_id: ID of the signal to update
            outcome: Outcome ("WIN", "LOSS", "BREAKEVEN")
            price_at_outcome: Price when outcome was determined
            pnl_percent: Profit/loss percentage

        Returns:
            True if signal was found and updated
        """
        signals = self._load_signals()

        for signal in signals:
            if signal.get("signal_id") == signal_id:
                signal["outcome"] = outcome
                signal["price_at_outcome"] = round(price_at_outcome, 6)
                signal["pnl_percent"] = round(pnl_percent, 2)
                self._save_signals(signals)
                return True

        return False

    def get_recent_signals(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent signals (newest first)."""
        signals = self._load_signals()
        return list(reversed(signals[-limit:]))

    def get_signals_by_symbol(self, symbol: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get signals for a specific symbol."""
        signals = self._load_signals()
        symbol_upper = symbol.upper()
        filtered = [s for s in signals if s.get("symbol", "").upper() == symbol_upper]
        return list(reversed(filtered[-limit:]))

    def get_actionable_signals(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get signals that are not NOTHING (BUY or SELL only)."""
        signals = self._load_signals()
        actionable = [s for s in signals if s.get("signal", "").upper() in ["BUY", "SELL"]]
        return list(reversed(actionable[-limit:]))

    def get_pending_signals(self) -> List[Dict[str, Any]]:
        """Get signals that don't have an outcome yet."""
        signals = self._load_signals()
        return [s for s in signals if s.get("outcome") is None]

    def calculate_accuracy(self) -> Dict[str, Any]:
        """
        Calculate signal accuracy metrics.

        Returns:
            Dictionary with accuracy statistics
        """
        signals = self._load_signals()
        actionable = [s for s in signals if s.get("signal", "").upper() in ["BUY", "SELL"]]
        with_outcome = [s for s in actionable if s.get("outcome") is not None]

        if not with_outcome:
            return {
                "total_signals": len(signals),
                "actionable_signals": len(actionable),
                "signals_with_outcome": 0,
                "win_rate": 0.0,
                "avg_confidence": 0.0,
                "high_confidence_accuracy": 0.0
            }

        wins = [s for s in with_outcome if s.get("outcome") == "WIN"]
        high_conf = [s for s in with_outcome if s.get("confidence", 0) >= 70]
        high_conf_wins = [s for s in high_conf if s.get("outcome") == "WIN"]

        avg_confidence = sum(s.get("confidence", 0) for s in actionable) / len(actionable) if actionable else 0

        return {
            "total_signals": len(signals),
            "actionable_signals": len(actionable),
            "signals_with_outcome": len(with_outcome),
            "win_rate": round(len(wins) / len(with_outcome) * 100, 1),
            "avg_confidence": round(avg_confidence, 1),
            "high_confidence_accuracy": round(len(high_conf_wins) / len(high_conf) * 100, 1) if high_conf else 0
        }

    def get_strategy_performance(self, strategy: str) -> Dict[str, Any]:
        """
        Get performance metrics for a specific strategy.

        Args:
            strategy: Strategy name to analyze

        Returns:
            Performance metrics for the strategy
        """
        signals = self._load_signals()
        strategy_signals = [s for s in signals if s.get("strategy", "").upper() == strategy.upper()]
        actionable = [s for s in strategy_signals if s.get("signal", "").upper() in ["BUY", "SELL"]]
        with_outcome = [s for s in actionable if s.get("outcome") is not None]

        if not with_outcome:
            return {
                "strategy": strategy,
                "total_signals": len(strategy_signals),
                "actionable_signals": len(actionable),
                "win_rate": 0.0
            }

        wins = len([s for s in with_outcome if s.get("outcome") == "WIN"])

        return {
            "strategy": strategy,
            "total_signals": len(strategy_signals),
            "actionable_signals": len(actionable),
            "signals_with_outcome": len(with_outcome),
            "win_rate": round(wins / len(with_outcome) * 100, 1)
        }

    def get_signals_for_learning(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get signals formatted for agent learning context.

        Returns signals with outcomes for the AI to learn from.

        Args:
            limit: Maximum signals to return

        Returns:
            List of signals with outcomes, formatted for learning
        """
        signals = self._load_signals()
        with_outcome = [s for s in signals if s.get("outcome") is not None]

        # Format for learning context
        learning_signals = []
        for s in with_outcome[-limit:]:
            learning_signals.append({
                "symbol": s.get("symbol"),
                "signal": s.get("signal"),
                "confidence": s.get("confidence"),
                "outcome": s.get("outcome"),
                "pnl_percent": s.get("pnl_percent"),
                "reasoning": s.get("reasoning", "")[:200],  # Truncated reasoning
                "strategy": s.get("strategy")
            })

        return learning_signals


# Global instance
_global_signal_recorder: Optional[SignalRecorder] = None


def get_signal_recorder() -> SignalRecorder:
    """Get or create the global SignalRecorder instance."""
    global _global_signal_recorder
    if _global_signal_recorder is None:
        _global_signal_recorder = SignalRecorder()
    return _global_signal_recorder
