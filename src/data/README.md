# src/data/ - Data Management Module

This directory contains data storage files and data management classes for the AI Trading Agent system.

## Core Data Classes

### TradeRecorder (`trade_recorder.py`)
Records trades with comprehensive metadata for dashboard display and agent learning.

**Features:**
- Records trades with strategy, confidence, and market conditions
- Maintains up to 500 trades in history
- Provides queries by symbol, time range, and trade type
- Calculates trading statistics

**Usage:**
```python
from src.data import get_recorder

recorder = get_recorder()
recorder.record_trade(
    symbol="BTC",
    side="LONG",
    action="OPEN",
    notional=1000.0,
    reason="AI signal"
)
```

### SignalRecorder (`signal_recorder.py`)
Records AI trading signals for accuracy analysis and agent learning.

**Features:**
- Records signals with confidence and reasoning
- Tracks signal outcomes (WIN/LOSS)
- Calculates signal accuracy metrics
- Provides learning data for AI context

**Usage:**
```python
from src.data import get_signal_recorder

recorder = get_signal_recorder()
recorder.record_signal(
    symbol="ETH",
    signal="BUY",
    confidence=75,
    reasoning="Strong bullish momentum"
)
```

### PerformanceCalculator (`performance_calculator.py`)
Calculates comprehensive trading performance metrics.

**Features:**
- Win rate, profit factor, Sharpe ratio
- Max drawdown and expectancy
- Daily and symbol-based breakdowns
- Historical performance snapshots

**Usage:**
```python
from src.data import get_performance_calculator

calculator = get_performance_calculator()
metrics = calculator.calculate_metrics()
print(f"Win Rate: {metrics['win_rate']}%")
```

## Data Files

### Trading Data
| File | Description | Retention |
|------|-------------|-----------|
| `trades.json` | Trade history for dashboard | Last 500 trades |
| `signals.json` | AI signal history | Last 1000 signals |
| `performance_history.json` | Performance snapshots | Last 365 days |

### Agent State
| File | Description |
|------|-------------|
| `agent_state.json` | Agent running state (started/stopped, total cycles) |
| `user_settings.json` | User preferences (timeframe, AI model, etc.) |

### Market Data (CSV)
| File | Description |
|------|-------------|
| `funding_history.csv` | Funding rate history |
| `sentiment_history.csv` | Market sentiment scores |
| `liquidation_history.csv` | Liquidation events |
| `oi_history.csv` | Open interest data |
| `portfolio_balance.csv` | Balance snapshots |

## Agent Subdirectories

Each agent may store its outputs in a dedicated subdirectory:

- `rbi/` - Research-Based Inference backtest results
- `execution_results/` - Backtest execution outputs
- `coingecko_results/` - CoinGecko API cache
- `hyperliquid_data/` - Exchange-specific data
- `tweets/` - Tweet generation data
- `volume_agent/` - Volume analysis outputs

## API Endpoints

The data classes are exposed via Flask API endpoints:

| Endpoint | Description |
|----------|-------------|
| `/api/trades` | Recent trades for dashboard |
| `/api/performance` | Overall performance metrics |
| `/api/performance/daily` | Daily performance breakdown |
| `/api/performance/symbols` | Per-symbol performance |
| `/api/trade-stats` | Trade statistics |

## Data Flow

```
Trade Execution
      │
      ▼
TradeRecorder.record_trade()
      │
      ├──► trades.json (dashboard display)
      │
      └──► PerformanceCalculator (metrics update)
                  │
                  ▼
          performance_history.json

AI Analysis
      │
      ▼
SignalRecorder.record_signal()
      │
      ├──► signals.json (signal history)
      │
      └──► get_signals_for_learning()
                  │
                  ▼
          AI Context (next analysis)
```

## Retention Policies

- **trades.json**: 500 trades max, oldest removed first
- **signals.json**: 1000 signals max, oldest removed first
- **performance_history.json**: 365 days of snapshots
- **CSV files**: Unbounded, manual cleanup recommended

## Migration Notes

- `ohlcv_collector.py` has been moved to `src/utils/`
- Legacy `position_tracker.json` is now managed by `src/utils/position_tracker.py`
