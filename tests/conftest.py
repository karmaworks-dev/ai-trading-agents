"""
Pytest Configuration and Fixtures

This file is automatically loaded by pytest.
"""

import pytest
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture
def sample_market_data():
    """Sample market data for testing"""
    import pandas as pd
    return pd.DataFrame({
        'open': [100, 101, 102, 103, 104, 105],
        'high': [102, 103, 104, 105, 106, 107],
        'low': [99, 100, 101, 102, 103, 104],
        'close': [101, 102, 103, 104, 105, 106],
        'volume': [1000, 1100, 1200, 1300, 1400, 1500]
    })


@pytest.fixture
def flat_market_data():
    """Flat market data (no price movement) for testing edge cases"""
    import pandas as pd
    return pd.DataFrame({
        'open': [100.0] * 30,
        'high': [100.0] * 30,
        'low': [100.0] * 30,
        'close': [100.0] * 30,
        'volume': [1000] * 30
    })


@pytest.fixture
def sample_position_data():
    """Sample position data tuple for testing"""
    return (
        [{"coin": "BTC", "szi": "0.001", "entryPx": "50000", "returnOnEquity": "0.05"}],
        True,  # im_in_pos
        0.001,  # pos_size
        "BTC",  # pos_sym
        50000.0,  # entry_px
        5.0,  # pnl_perc
        True   # is_long
    )


@pytest.fixture
def empty_position_data():
    """Empty position data tuple for testing"""
    return (
        [],  # positions list
        False,  # im_in_pos
        0,  # pos_size
        "BTC",  # pos_sym
        0,  # entry_px
        0,  # pnl_perc
        True  # is_long (default)
    )


@pytest.fixture
def sample_signals():
    """Sample trading signals for testing"""
    return [
        {"symbol": "BTC", "action": "BUY", "confidence": 80, "reasoning": "Strong uptrend"},
        {"symbol": "ETH", "action": "SELL", "confidence": 70, "reasoning": "Resistance hit"},
        {"symbol": "SOL", "action": "NOTHING", "confidence": 50, "reasoning": "Consolidating"},
    ]


@pytest.fixture
def mock_account():
    """Mock account object for testing"""
    from unittest.mock import Mock
    account = Mock()
    account.address = "0x1234567890abcdef1234567890abcdef12345678"
    return account
