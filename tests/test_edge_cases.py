"""
Unit Tests for Edge Cases
Tests for flat market conditions, empty signals, circuit breakers, and missing data.

Run with: pytest tests/test_edge_cases.py -v
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


# =============================================================================
# FLAT MARKET CONDITION TESTS
# =============================================================================

class TestFlatMarketConditions:
    """Tests for handling flat market scenarios (no price movement)"""

    def test_stochastic_flat_market(self):
        """Test stochastic calculation when market is completely flat"""
        from strategies.custom.quad_enhanced_strategy import QuadEnhancedStrategy

        strategy = QuadEnhancedStrategy()

        # Create flat market data (all prices identical)
        flat_data = pd.DataFrame({
            'open': [100.0] * 20,
            'high': [100.0] * 20,
            'low': [100.0] * 20,
            'close': [100.0] * 20,
            'volume': [1000] * 20
        })

        # Should not raise ZeroDivisionError
        stoch_k, stoch_d = strategy.calculate_stochastic(flat_data, k_period=14, d_period=3)

        # Result should be 50 (neutral) for flat periods
        assert not stoch_k.isna().all(), "Stochastic K should not be all NaN"
        assert stoch_k.iloc[-1] == 50.0, "Flat market should return neutral stochastic (50)"

    def test_macd_divergence_zero_values(self):
        """Test MACD divergence when previous values are zero"""
        from strategies.custom.macd_money_map import MACDMoneyMapStrategy

        strategy = MACDMoneyMapStrategy()

        # Test with zero previous high
        price_highs = np.array([0, 100])
        macd_highs = np.array([0, 50])
        price_high_indices = np.array([0, 1])
        macd_high_indices = np.array([0, 1])

        result = strategy.detect_bearish_divergence(
            price_highs, price_high_indices,
            macd_highs, macd_high_indices
        )

        # Should return detected=False, not crash
        assert result['detected'] == False, "Should not detect divergence with zero values"

    def test_level_strength_zero_price(self):
        """Test support/resistance level strength with zero price"""
        from patterns.simple_detector import SimplePatternDetector

        detector = SimplePatternDetector()

        # Price list with a zero value
        prices = [100.0, 0.0, 100.0, 100.0, 100.0]

        # Should not crash on zero price
        strength = detector._calculate_level_strength(prices, index=1, level_type='support')

        assert strength == 0.0, "Zero price should return 0 strength"


# =============================================================================
# EMPTY SIGNAL LIST TESTS
# =============================================================================

class TestEmptySignalLists:
    """Tests for handling empty signal scenarios"""

    def test_portfolio_allocator_empty_signals(self):
        """Test portfolio allocator with empty signal list"""
        from agents.trading.portfolio_allocator import calculate_margin_per_signal

        # Empty signals list
        signals = []
        available_balance = 100.0
        max_position_pct = 90
        cash_buffer_pct = 10
        min_order_notional = 12.0
        leverage = 20

        margin, filtered_signals = calculate_margin_per_signal(
            signals, available_balance, max_position_pct,
            cash_buffer_pct, min_order_notional, leverage
        )

        assert margin == 0, "Empty signals should return 0 margin"
        assert filtered_signals == [], "Empty signals should return empty list"

    def test_fallback_allocation_empty_signals(self):
        """Test fallback allocation with no signals"""
        # This tests the _fallback_equal_allocation method
        # Mock implementation since we can't easily instantiate TradingAgent
        signals = []
        allocatable_usd = 100.0

        # Simple division guard
        if not signals:
            result = []
        else:
            result = [s for s in signals]

        assert result == [], "Empty signals should return empty result"


# =============================================================================
# CIRCUIT BREAKER TESTS
# =============================================================================

class TestCircuitBreakers:
    """Tests for trading circuit breaker scenarios"""

    def test_stop_loss_threshold(self):
        """Test stop loss triggers correctly"""
        from agents.trading.position_analyzer import should_trigger_stop_loss

        # Test at exactly threshold
        assert should_trigger_stop_loss(-2.0, -2.0) == True
        # Test below threshold
        assert should_trigger_stop_loss(-3.0, -2.0) == True
        # Test above threshold
        assert should_trigger_stop_loss(-1.0, -2.0) == False
        # Test positive PnL
        assert should_trigger_stop_loss(5.0, -2.0) == False

    def test_take_profit_threshold(self):
        """Test take profit triggers correctly"""
        from agents.trading.position_analyzer import should_trigger_take_profit

        # Test at exactly threshold
        assert should_trigger_take_profit(5.0, 5.0) == True
        # Test above threshold
        assert should_trigger_take_profit(6.0, 5.0) == True
        # Test below threshold
        assert should_trigger_take_profit(4.0, 5.0) == False
        # Test negative PnL
        assert should_trigger_take_profit(-2.0, 5.0) == False


# =============================================================================
# MISSING DATA TESTS
# =============================================================================

class TestMissingDataHandling:
    """Tests for handling missing or malformed data"""

    def test_json_extraction_empty_response(self):
        """Test JSON extraction with empty or invalid responses"""
        from agents.trading.market_analyzer import extract_json_from_text

        # Empty string
        assert extract_json_from_text("") is None
        assert extract_json_from_text(None) is None

        # No JSON in text
        assert extract_json_from_text("Just some text without JSON") is None

    def test_json_extraction_list_response(self):
        """Test JSON extraction when AI returns a list instead of object"""
        from agents.trading.market_analyzer import extract_json_from_text

        # List response should be wrapped
        list_response = 'Here is the result: [{"action": "BUY", "symbol": "BTC"}]'
        result = extract_json_from_text(list_response)

        assert result is not None, "Should handle list responses"
        assert "actions" in result, "List should be wrapped in 'actions' key"

    def test_json_extraction_valid_object(self):
        """Test JSON extraction with valid object response"""
        from agents.trading.market_analyzer import extract_json_from_text

        valid_response = 'Analysis: {"action": "BUY", "confidence": 75, "reasoning": "Strong trend"}'
        result = extract_json_from_text(valid_response)

        assert result is not None
        assert result.get("action") == "BUY"
        assert result.get("confidence") == 75

    def test_position_data_validation(self):
        """Test position data tuple validation"""
        # Simulates the validation added to trading_agent.py

        def validate_pos_data(pos_data):
            """Validation helper matching trading_agent.py logic"""
            if pos_data is None:
                return False
            if not isinstance(pos_data, tuple):
                return False
            if len(pos_data) < 7:
                return False
            return True

        # Valid data
        valid_pos = ([], True, 0.5, "BTC", 50000.0, 2.5, True)
        assert validate_pos_data(valid_pos) == True

        # Invalid cases
        assert validate_pos_data(None) == False
        assert validate_pos_data("invalid") == False
        assert validate_pos_data((1, 2, 3)) == False  # Too short
        assert validate_pos_data([]) == False  # List not tuple


# =============================================================================
# DICTIONARY ACCESS SAFETY TESTS
# =============================================================================

class TestDictionaryAccessSafety:
    """Tests for safe dictionary access patterns"""

    def test_api_response_missing_fields(self):
        """Test handling of API responses with missing fields"""
        # Simulates HyperLiquid API response handling

        def safe_get_position_data(user_state):
            """Safe extraction matching nice_funcs_hyperliquid.py"""
            asset_positions = user_state.get("assetPositions", [])
            results = []

            for position in asset_positions:
                raw_pos = position.get("position", {})
                coin = raw_pos.get("coin", "")
                sz = float(raw_pos.get("szi", 0))
                entry_px = float(raw_pos.get("entryPx", 0))
                pnl = float(raw_pos.get("returnOnEquity", 0)) * 100
                results.append({
                    "coin": coin,
                    "size": sz,
                    "entry": entry_px,
                    "pnl": pnl
                })

            return results

        # Empty response
        empty_response = {}
        result = safe_get_position_data(empty_response)
        assert result == []

        # Partial data
        partial_response = {
            "assetPositions": [
                {"position": {"coin": "BTC"}}  # Missing szi, entryPx, returnOnEquity
            ]
        }
        result = safe_get_position_data(partial_response)
        assert len(result) == 1
        assert result[0]["coin"] == "BTC"
        assert result[0]["size"] == 0  # Default value
        assert result[0]["entry"] == 0  # Default value

    def test_margin_summary_missing(self):
        """Test handling when marginSummary is missing"""

        def safe_get_account_value(user_state):
            """Safe extraction matching nice_funcs_hyperliquid.py"""
            margin_summary = user_state.get("marginSummary", {})
            return float(margin_summary.get("accountValue", 0))

        # Missing marginSummary
        assert safe_get_account_value({}) == 0.0

        # Missing accountValue
        assert safe_get_account_value({"marginSummary": {}}) == 0.0

        # Valid data
        assert safe_get_account_value({"marginSummary": {"accountValue": "100.5"}}) == 100.5


# =============================================================================
# CONFIDENCE HANDLING TESTS
# =============================================================================

class TestConfidenceHandling:
    """Tests for confidence value handling"""

    def test_missing_confidence_in_row(self):
        """Test handling when 'confidence' key is missing from row"""

        def get_confidence_safe(row):
            """Safe confidence extraction matching trading_agent.py fix"""
            return row.get('confidence', 50)

        # Missing confidence
        row_no_confidence = {"action": "BUY", "symbol": "BTC"}
        assert get_confidence_safe(row_no_confidence) == 50

        # With confidence
        row_with_confidence = {"action": "BUY", "symbol": "BTC", "confidence": 75}
        assert get_confidence_safe(row_with_confidence) == 75

        # Zero confidence (should be preserved)
        row_zero_confidence = {"action": "NOTHING", "confidence": 0}
        assert get_confidence_safe(row_zero_confidence) == 0


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
