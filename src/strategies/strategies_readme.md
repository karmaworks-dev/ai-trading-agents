# 🕉️ AI Trading Strategies - Complete Guide

## 🎯 Overview

This document provides a comprehensive guide to the AI Trading Strategies system, explaining how to create, integrate, and manage custom trading strategies within the AI Trading Agents platform.

## 🏗️ Strategy Architecture

### Base Strategy Class

**File**: `src/strategies/base_strategy.py`

All custom strategies must inherit from the `BaseStrategy` class and implement the required methods:

```python
class BaseStrategy:
    def __init__(self, name: str):
        self.name = name
    
    def generate_signals(self) -> dict:
        """
        Generate trading signals
        Returns:
            dict: {
                'token': str,          # Token address
                'signal': float,       # Signal strength (0-1)
                'direction': str,      # 'BUY', 'SELL', or 'NEUTRAL'
                'metadata': dict       # Optional strategy-specific data
            }
        """
        raise NotImplementedError("Strategy must implement generate_signals()")
```

### Strategy Registry

**File**: `src/strategies/strategy_registry.py`

The strategy registry manages all available strategies and provides methods for:
- Listing available strategies
- Loading strategy classes dynamically
- Managing enabled/disabled strategies
- Providing metadata for frontend display

## 📚 Available Strategies

### 1. Example Strategy

**File**: `src/strategies/custom/example_strategy.py`

A simple template strategy that demonstrates the basic structure:
- Fixed signal for demonstration purposes
- Basic metadata with reason and indicators
- Used as a starting point for new strategies

### 2. Quad Rotation Strategy

**File**: `src/strategies/custom/quad_enhanced_strategy.py`

**Type**: Multi-Stochastic Multi-Timeframe Rotation System

**Description**:
An advanced strategy using 4 stochastic oscillators with different periods across multiple timeframes to identify high-probability trading opportunities through "rotation" and timeframe agreement.

**Key Features**:
- **Multi-Timeframe Analysis**: Analyzes 15m, 1h, and 4h timeframes.
- **4 Stochastic Oscillators**: Fast (9), Medium (14, 40), Slow (60).
- **Weighted Average**: Combines all 4 stochastics with emphasis on slower ones.
- **MTF Confirmation**: Signal strength is weighted by agreement across different timeframes.
- **Trend Shield**: ABCD pattern across timeframes to avoid counter-trend trades.

### 3. MACD Money Map Strategy

**File**: `src/strategies/custom/macd_money_map.py`

**Type**: Trend Following & Divergence Strategy

**Description**:
Complete implementation of the MACD Money Map trading framework, combining trend-following rules with momentum exhaustion detection.

**Key Features**:
- **System 1 (Trend Following)**: Uses zero-line foundation and distance rules to follow established trends.
- **System 2 (Divergence)**: Detects price-MACD divergence (Bullish/Bearish) with triple histogram confirmation.
- **System 3 (MTF Alignment)**: Optional triple timeframe validation (HTF/MTF/LTF) using 4x multipliers.
- **Risk Management**: Mathematical position sizing with 2R profit targets, swing high/low stop losses, and breakeven/trailing exits.

**Signal Strength**:
- **0.0 - 1.0**: Weighted strength based on timeframe agreement and stochastic signals.

**Technical Details**:
- Uses 15-minute timeframe as the primary trigger timeframe.
- Confirms signals with 1h and 4h higher-level trends.
- Implements comprehensive error handling and logging.

## 🔧 Strategy Development Guide

### Creating a New Strategy

#### Step 1: Create Strategy File

1. Create a new Python file in `src/strategies/custom/`
2. Name it descriptively (e.g., `my_awesome_strategy.py`)
3. Import required modules:
   ```python
   from ..base_strategy import BaseStrategy
   from src.config import MONITORED_TOKENS
   import pandas as pd
   from termcolor import cprint
   from src import nice_funcs as n
   ```

#### Step 2: Implement Base Class

```python
class MyAwesomeStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("My Awesome Strategy")
        # Initialize strategy parameters
        self.param1 = value1
        self.param2 = value2
```

#### Step 3: Implement Signal Generation

```python
    def generate_signals(self) -> dict:
        try:
            for token in MONITORED_TOKENS:
                # Get market data
                data = n.get_data(token, days_back=3, timeframe='15m')
                if data is None or data.empty:
                    continue
                
                # Calculate indicators
                # ... your indicator calculations ...
                
                # Create signal
                signal = {
                    'token': token,
                    'signal': 0,
                    'direction': 'NEUTRAL',
                    'metadata': {
                        'strategy_type': 'my_awesome',
                        # ... your metadata ...
                    }
                }
                
                # Determine signal direction and strength
                # ... your signal logic ...
                
                # Validate and return signal
                if self.validate_signal(signal):
                    signal['metadata'] = self.format_metadata(signal['metadata'])
                    return signal
            
            return None
            
        except Exception as e:
            cprint(f"❌ Error generating signals: {str(e)}", "red")
            return None
```

#### Step 4: Add Validation Methods (Inherited from BaseStrategy)

Strategies inherit `validate_signal()` and `format_metadata()` from `BaseStrategy`. You can override them if needed.

#### Step 5: Register Strategy

Add your strategy to `STRATEGY_METADATA` in `src/strategies/strategy_registry.py`:

```python
"my_awesome": {
    "id": "my_awesome",
    "name": "My Awesome Strategy",
    "description": "Description of your awesome strategy",
    "category": "momentum",  # or position_sizing, mean_reversion, etc.
    "risk_level": "medium",  # low, medium, or high
    "recommended_timeframes": ["15m", "30m", "1h"],
    "module": "src.strategies.custom.my_awesome_strategy",
    "class_name": "MyAwesomeStrategy",
}
```

### Strategy Categories

- **momentum**: Strategies based on price trends and momentum
- **position_sizing**: Strategies focused on portfolio allocation
- **mean_reversion**: Strategies that trade reversions to mean
- **breakout**: Strategies that trade price breakouts
- **statistical_arbitrage**: Strategies based on statistical relationships
- **volatility**: Strategies based on volatility patterns
- **fundamental**: Strategies based on fundamental analysis

### Risk Levels

- **low**: Conservative strategies with minimal risk
- **medium**: Balanced strategies with moderate risk
- **high**: Aggressive strategies with higher risk

## 🎛️ Strategy Configuration

### Timeframes

Recommended timeframes for different strategy types:
- **Scalping**: 1m, 3m, 5m
- **Day Trading**: 15m, 30m, 1h
- **Swing Trading**: 1h, 4h, 1d
- **Position Trading**: 1d, 1w, 1M

### Data Requirements

- **Historical Data**: Most strategies require 3-7 days of historical data
- **Timeframe**: Match data timeframe to strategy timeframe
- **Data Quality**: Ensure data is clean and complete
- **Data Frequency**: Higher frequency for shorter timeframes

## 🔍 Strategy Analysis

### Signal Validation

All signals are validated through `BaseStrategy.validate_signal()`:

1. **Required Fields**: token, signal, direction, metadata
2. **Signal Range**: 0-1 (0 = no signal, 1 = strongest signal)
3. **Direction**: BUY, SELL, or NEUTRAL
4. **Metadata**: Should include strategy-specific information

### Error Handling

Implement comprehensive error handling:
- Catch exceptions in signal generation
- Log errors with colored output
- Return None for invalid signals
- Include traceback for debugging

### Performance Optimization

- **Efficiency**: Optimize data processing for speed
- **Memory**: Use efficient data structures
- **Robustness**: Handle edge cases gracefully
- **Scalability**: Design for multiple tokens

## 📊 Strategy Integration

### Frontend Integration

Strategies are displayed in the dashboard with:
- Strategy name and description
- Category and risk level
- Recommended timeframes
- Enable/disable toggle
- Performance metrics

### Backend Integration

Strategies are loaded and executed by:
1. **Strategy Registry**: Loads enabled strategies
2. **Trading Agent**: Processes strategy signals
3. **Signal Processor**: Combines multiple strategy signals
4. **Trade Executor**: Executes trades based on signals

## 🚀 Advanced Strategy Development

### Multi-Timeframe Analysis

The Quad Rotation strategy demonstrates multi-timeframe analysis by aggregating signals from 15m, 1h, and 4h charts to ensure higher-level trend alignment.

### Strategy Optimization

Optimize strategies using:
- **Parameter Tuning**: Find optimal parameter values
- **Walk-Forward Testing**: Test on out-of-sample data
- **Monte Carlo Simulation**: Test robustness
- **Risk-Adjusted Returns**: Optimize for Sharpe ratio

### Strategy Validation

Validate strategies with:
- **Backtesting**: Test on historical data
- **Forward Testing**: Test on live market data
- **Stress Testing**: Test under extreme conditions
- **Performance Metrics**: Track key metrics

## 📝 Best Practices

### Code Quality

- **Modular Design**: Keep strategies focused and modular
- **Clear Documentation**: Document strategy logic and parameters
- **Consistent Naming**: Use clear, consistent variable names
- **Error Handling**: Implement comprehensive error handling

### Strategy Design

- **Simplicity**: Start with simple strategies
- **Robustness**: Design for various market conditions
- **Risk Management**: Include built-in risk controls
- **Performance**: Optimize for speed and efficiency

### Testing

- **Unit Testing**: Test individual components
- **Integration Testing**: Test strategy integration
- **Performance Testing**: Test under load
- **Regression Testing**: Test after changes

## 🎓 Learning Resources

### Example Strategies

Study the existing strategies to understand:
- Strategy structure and organization
- Signal generation patterns
- Error handling approaches
- Metadata formatting

### Documentation

- **Strategy Registry**: Understand strategy loading
- **Base Strategy**: Learn the core interface
- **Custom Strategies**: See real implementations
- **Configuration**: Learn parameter settings

### Community

- **Discord**: Get help and share strategies
- **GitHub**: Contribute strategies
- **YouTube**: Watch strategy tutorials
- **Bootcamp**: Learn advanced techniques

## 🛡️ Strategy Security

### Best Practices

- **Code Review**: Review strategies before deployment
- **Sandbox Testing**: Test in isolated environment
- **Risk Limits**: Set appropriate risk limits
- **Monitoring**: Monitor strategy performance

### Risk Management

- **Position Sizing**: Limit position sizes
- **Stop Loss**: Always use stop losses
- **Take Profit**: Set realistic take profit levels
- **Diversification**: Don't rely on single strategy

## 📞 Support

For strategy development support:
- **Discord**: Join the Moon Dev community
- **GitHub**: Open issues for strategy problems
- **Documentation**: Read strategy guides
- **Tutorials**: Watch strategy development videos

This guide provides everything you need to create, integrate, and manage custom trading strategies within the AI Trading Agents platform.