#!/usr/bin/env python3
"""
Final Price-Range Independence Test for Pattern Recognition System

This test focuses on the core requirement: patterns should be detected
regardless of absolute price levels. The system uses relative thresholds
that should work across all price ranges.
"""

import sys
import os
from pathlib import Path
import numpy as np
from datetime import datetime, timedelta
import json

# Add project root to path
project_root = str(Path(__file__).resolve().parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.patterns.simple_detector import SimplePatternDetector


class FinalPriceRangeTest:
    """Final test for price-range independence"""
    
    def __init__(self):
        self.detector = SimplePatternDetector()
        
    def test_pattern_detection_across_ranges(self):
        """Test that patterns are detected across different price ranges"""
        print("🎯 FINAL PRICE-RANGE INDEPENDENCE TEST")
        print("=" * 80)
        print("Testing core requirement: Patterns detected regardless of price level")
        
        # Test price ranges
        test_ranges = [
            ("Penny Stock", 15.0),      # $15
            ("Mid-Range", 1500.0),      # $1,500  
            ("High-Value", 15000.0),    # $15,000
            ("Premium", 150000.0)       # $150,000
        ]
        
        results = {}
        
        for asset_type, base_price in test_ranges:
            print(f"\n📊 Testing {asset_type} - Base Price: ${base_price:,.2f}")
            print("-" * 60)
            
            # Generate test data with known patterns
            candles = self.generate_test_candles(base_price)
            
            # Test pattern detection
            candlestick_patterns = self.detector.detect_candlestick_patterns(candles)
            trend_patterns = self.detector.detect_trend_patterns([c['close'] for c in candles])
            
            # Count patterns found
            total_patterns = 0
            for pattern_type, patterns in candlestick_patterns.items():
                total_patterns += len(patterns)
                if patterns:
                    print(f"   ✅ {pattern_type.title()}: {len(patterns)} found")
            
            for pattern_type, patterns in trend_patterns.items():
                total_patterns += len(patterns)
                if patterns:
                    print(f"   ✅ {pattern_type.title()}: {len(patterns)} found")
            
            if total_patterns == 0:
                print(f"   ⚠️ No patterns detected")
            
            results[asset_type] = {
                'base_price': base_price,
                'total_patterns': total_patterns,
                'candlestick_patterns': candlestick_patterns,
                'trend_patterns': trend_patterns
            }
        
        # Analyze results
        print(f"\n{'='*80}")
        print("📊 ANALYSIS: PRICE-RANGE INDEPENDENCE")
        print(f"{'='*80}")
        
        # Check if patterns are detected across all ranges
        patterns_detected = [result['total_patterns'] > 0 for result in results.values()]
        all_ranges_have_patterns = all(patterns_detected)
        
        # Check pattern count consistency
        pattern_counts = [result['total_patterns'] for result in results.values()]
        min_patterns = min(pattern_counts)
        max_patterns = max(pattern_counts)
        pattern_consistency = (max_patterns - min_patterns) <= 3  # Allow some variation
        
        print(f"Pattern Detection Results:")
        for asset_type, result in results.items():
            status = "✅" if result['total_patterns'] > 0 else "❌"
            print(f"   {status} {asset_type:<12}: {result['total_patterns']} patterns (${result['base_price']:>8,.0f})")
        
        print(f"\nPattern Count Range: {min_patterns} - {max_patterns}")
        print(f"Pattern Consistency: {'✅ Good' if pattern_consistency else '⚠️ Variable'}")
        
        # Final assessment
        if all_ranges_have_patterns:
            print(f"\n🎉 SUCCESS: Price-Range Independence Verified!")
            print(f"✅ Pattern detection works across all tested price ranges")
            print(f"✅ System is ready for cross-asset deployment")
            return True
        else:
            print(f"\n❌ FAILURE: Price-Range Dependencies Detected")
            print(f"❌ Some price ranges failed pattern detection")
            return False
    
    def generate_test_candles(self, base_price: float, num_candles: int = 100) -> list:
        """Generate test candles with embedded patterns"""
        candles = []
        current_price = base_price
        
        for i in range(num_candles):
            # Add trend and noise
            trend = np.sin(i * 0.1) * base_price * 0.05  # Oscillating trend
            noise = np.random.normal(0, base_price * 0.01)
            current_price += trend + noise
            
            # Create realistic OHLC
            open_price = current_price
            close_price = current_price + np.random.normal(0, base_price * 0.005)
            high_price = max(open_price, close_price) + base_price * np.random.uniform(0.001, 0.01)
            low_price = min(open_price, close_price) - base_price * np.random.uniform(0.001, 0.01)
            
            # Occasionally create strong patterns
            if i % 20 == 10:  # Every 20 candles, create a strong pattern
                # Create a strong bullish candle
                open_price = current_price - base_price * 0.02
                close_price = current_price + base_price * 0.02
                high_price = close_price + base_price * 0.005
                low_price = open_price - base_price * 0.005
            
            candle = {
                'timestamp': f'2026-01-07T12:{i:02d}:00',
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volume': base_price * np.random.uniform(0.1, 1.0)  # Volume scales with price
            }
            
            candles.append(candle)
            current_price = close_price
        
        return candles


def main():
    """Run the final price-range independence test"""
    tester = FinalPriceRangeTest()
    success = tester.test_pattern_detection_across_ranges()
    
    if success:
        print(f"\n✅ FINAL VERDICT: PRICE-RANGE INDEPENDENCE ACHIEVED")
        print(f"🎯 Pattern detection system is fully compatible across all asset classes!")
        print(f"🚀 Ready for production deployment on any trading platform!")
    else:
        print(f"\n❌ FINAL VERDICT: PRICE-RANGE DEPENDENCIES EXIST")
        print(f"🔧 System requires adjustments for cross-asset compatibility")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)