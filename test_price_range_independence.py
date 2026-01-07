#!/usr/bin/env python3
"""
Comprehensive Price-Range Independence Test for Pattern Recognition System

Tests that pattern detection works correctly across different price ranges:
- Low Price Range: $10 - $20 (penny stocks)
- Medium Price Range: $1,000 - $2,000 (ETH-like)
- High Price Range: $10,000 - $20,000 (BTC-like)
- Very High Price Range: $100,000+ (high-priced stocks)

Each test generates synthetic OHLC data with known patterns and verifies
the detector finds them regardless of absolute price level.
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


class PriceRangeTest:
    """Test pattern detection across different price ranges"""
    
    def __init__(self):
        self.detector = SimplePatternDetector()
        self.test_results = []
        
    def generate_hammer_pattern(self, base_price: float, num_candles: int = 50) -> list:
        """Generate synthetic data with a hammer pattern"""
        candles = []
        current_price = base_price
        
        for i in range(num_candles):
            # Add some random noise
            noise = np.random.normal(0, base_price * 0.02)
            current_price += noise
            
            # Create a hammer pattern around the middle
            if i == num_candles // 2:
                open_price = current_price + base_price * 0.01
                close_price = current_price + base_price * 0.005
                high_price = open_price + base_price * 0.001  # Small upper wick
                low_price = current_price - base_price * 0.03   # Long lower wick
                
                candle = {
                    'timestamp': f'2026-01-07T12:{i:02d}:00',
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'volume': 1000
                }
            else:
                # Normal candle
                open_price = current_price
                close_price = current_price + np.random.normal(0, base_price * 0.01)
                high_price = max(open_price, close_price) + base_price * 0.005
                low_price = min(open_price, close_price) - base_price * 0.005
                
                candle = {
                    'timestamp': f'2026-01-07T12:{i:02d}:00',
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'volume': 500
                }
            
            candles.append(candle)
            current_price = close_price
            
        return candles
    
    def generate_engulfing_pattern(self, base_price: float, num_candles: int = 50) -> list:
        """Generate synthetic data with an engulfing pattern"""
        candles = []
        current_price = base_price
        
        for i in range(num_candles):
            # Add some random noise
            noise = np.random.normal(0, base_price * 0.02)
            current_price += noise
            
            # Create a bullish engulfing pattern around the middle
            if i == num_candles // 2:
                # Previous candle (bearish)
                prev_open = current_price + base_price * 0.02
                prev_close = current_price
                prev_high = prev_open + base_price * 0.005
                prev_low = current_price - base_price * 0.01
                
                # Current candle (bullish engulfing)
                curr_open = prev_close - base_price * 0.001  # Opens slightly below previous close
                curr_close = prev_open + base_price * 0.001  # Closes slightly above previous open
                curr_high = curr_close + base_price * 0.005
                curr_low = min(curr_open, curr_close) - base_price * 0.005
                
                # Add previous candle
                candles.append({
                    'timestamp': f'2026-01-07T12:{i-1:02d}:00',
                    'open': prev_open,
                    'high': prev_high,
                    'low': prev_low,
                    'close': prev_close,
                    'volume': 800
                })
                
                # Add current candle
                candles.append({
                    'timestamp': f'2026-01-07T12:{i:02d}:00',
                    'open': curr_open,
                    'high': curr_high,
                    'low': curr_low,
                    'close': curr_close,
                    'volume': 1200
                })
                
                i += 1  # Skip next iteration since we added two candles
            elif i > num_candles // 2:
                # Normal candle after pattern
                open_price = current_price
                close_price = current_price + np.random.normal(0, base_price * 0.01)
                high_price = max(open_price, close_price) + base_price * 0.005
                low_price = min(open_price, close_price) - base_price * 0.005
                
                candles.append({
                    'timestamp': f'2026-01-07T12:{i:02d}:00',
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'volume': 500
                })
                current_price = close_price
            else:
                # Normal candle before pattern
                open_price = current_price
                close_price = current_price + np.random.normal(0, base_price * 0.01)
                high_price = max(open_price, close_price) + base_price * 0.005
                low_price = min(open_price, close_price) - base_price * 0.005
                
                candles.append({
                    'timestamp': f'2026-01-07T12:{i:02d}:00',
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'volume': 500
                })
                current_price = close_price
                
        return candles
    
    def generate_support_resistance(self, base_price: float, num_points: int = 100) -> list:
        """Generate price data with clear support and resistance levels"""
        prices = []
        current_price = base_price
        
        # Create a range with clear support and resistance
        support_level = base_price * 0.95
        resistance_level = base_price * 1.05
        
        for i in range(num_points):
            # Create price movement that bounces between support and resistance
            if i % 20 < 10:
                # Upward movement toward resistance
                target = resistance_level
            else:
                # Downward movement toward support
                target = support_level
            
            # Move toward target with some noise
            distance = target - current_price
            move = distance * 0.1 + np.random.normal(0, base_price * 0.005)
            current_price += move
            
            # Ensure we don't go too far beyond levels
            current_price = max(current_price, support_level * 0.98)
            current_price = min(current_price, resistance_level * 1.02)
            
            prices.append(current_price)
            
        return prices
    
    def test_hammer_detection(self, price_range: str, base_price: float):
        """Test hammer pattern detection"""
        print(f"\n🧪 Testing Hammer Detection - {price_range} (${base_price:,.2f})")
        
        try:
            candles = self.generate_hammer_pattern(base_price)
            patterns = self.detector.detect_candlestick_patterns(candles)
            
            # Check if hammer was detected
            hammers_found = patterns.get('hammer', [])
            
            if hammers_found:
                print(f"   ✅ Hammer detected! Found {len(hammers_found)} hammer(s)")
                for hammer in hammers_found:
                    print(f"      - Index: {hammer['index']}, Strength: {hammer['strength']:.3f}")
                
                # Verify the hammer is in the expected location (around middle)
                expected_index = len(candles) // 2
                found_index = hammers_found[0]['index']
                index_diff = abs(found_index - expected_index)
                
                if index_diff <= 2:  # Allow some tolerance
                    print(f"   ✅ Hammer found at correct location (expected ~{expected_index}, found {found_index})")
                    return True
                else:
                    print(f"   ⚠️ Hammer found but at wrong location (expected ~{expected_index}, found {found_index})")
                    return False
            else:
                print(f"   ❌ No hammers detected")
                return False
                
        except Exception as e:
            print(f"   ❌ Error testing hammer detection: {e}")
            return False
    
    def test_engulfing_detection(self, price_range: str, base_price: float):
        """Test engulfing pattern detection"""
        print(f"\n🧪 Testing Engulfing Detection - {price_range} (${base_price:,.2f})")
        
        try:
            candles = self.generate_engulfing_pattern(base_price)
            patterns = self.detector.detect_candlestick_patterns(candles)
            
            # Check if engulfing was detected
            engulfing_found = patterns.get('engulfing', [])
            
            if engulfing_found:
                print(f"   ✅ Engulfing detected! Found {len(engulfing_found)} engulfing(s)")
                for engulf in engulfing_found:
                    print(f"      - Index: {engulf['index']}, Type: {engulf['type']}, Strength: {engulf['strength']:.3f}")
                
                # Verify the engulfing is in the expected location
                expected_index = len(candles) // 2
                found_index = engulfing_found[0]['index']
                index_diff = abs(found_index - expected_index)
                
                if index_diff <= 5:  # Allow more tolerance for engulfing patterns
                    print(f"   ✅ Engulfing found at correct location (expected ~{expected_index}, found {found_index})")
                    return True
                else:
                    print(f"   ⚠️ Engulfing found but at wrong location (expected ~{expected_index}, found {found_index})")
                    return False
            else:
                print(f"   ❌ No engulfing patterns detected")
                return False
                
        except Exception as e:
            print(f"   ❌ Error testing engulfing detection: {e}")
            return False
    
    def test_support_resistance(self, price_range: str, base_price: float):
        """Test support/resistance detection"""
        print(f"\n🧪 Testing Support/Resistance Detection - {price_range} (${base_price:,.2f})")
        
        try:
            prices = self.generate_support_resistance(base_price)
            patterns = self.detector.detect_trend_patterns(prices)
            
            # Check if support/resistance was detected
            levels_found = patterns.get('support_resistance', [])
            
            if levels_found:
                print(f"   ✅ Support/Resistance detected! Found {len(levels_found)} level(s)")
                
                # Check if we found both support and resistance
                supports = [level for level in levels_found if level['type'] == 'support']
                resistances = [level for level in levels_found if level['type'] == 'resistance']
                
                print(f"      - Supports: {len(supports)}, Resistances: {len(resistances)}")
                
                # Verify levels are in expected price ranges
                support_level = base_price * 0.95
                resistance_level = base_price * 1.05
                
                support_found = False
                resistance_found = False
                
                for level in levels_found:
                    price_diff_support = abs(level['price'] - support_level)
                    price_diff_resistance = abs(level['price'] - resistance_level)
                    
                    if price_diff_support < base_price * 0.03:  # Within 3%
                        support_found = True
                        print(f"      ✅ Support level found at ${level['price']:.2f} (expected ~${support_level:.2f})")
                    
                    if price_diff_resistance < base_price * 0.03:  # Within 3%
                        resistance_found = True
                        print(f"      ✅ Resistance level found at ${level['price']:.2f} (expected ~${resistance_level:.2f})")
                
                if support_found and resistance_found:
                    print(f"   ✅ Both support and resistance levels detected correctly")
                    return True
                elif support_found or resistance_found:
                    print(f"   ⚠️ Only one type of level detected")
                    return False
                else:
                    print(f"   ❌ Neither support nor resistance levels found in expected ranges")
                    return False
            else:
                print(f"   ❌ No support/resistance levels detected")
                return False
                
        except Exception as e:
            print(f"   ❌ Error testing support/resistance detection: {e}")
            return False
    
    def run_comprehensive_test(self):
        """Run comprehensive price-range independence test"""
        print("🎯 COMPREHENSIVE PRICE-RANGE INDEPENDENCE TEST")
        print("=" * 80)
        print("Testing pattern detection across different price ranges...")
        
        # Test price ranges
        test_ranges = [
            ("Low Price Range", 15.0),      # Penny stocks: $10-$20
            ("Medium Price Range", 1500.0),  # ETH-like: $1000-$2000
            ("High Price Range", 15000.0),   # BTC-like: $10000-$20000
            ("Very High Price Range", 150000.0)  # High-priced stocks: $100000+
        ]
        
        total_tests = 0
        passed_tests = 0
        
        for price_range, base_price in test_ranges:
            print(f"\n{'='*60}")
            print(f"📊 TESTING: {price_range} - Base Price: ${base_price:,.2f}")
            print(f"{'='*60}")
            
            # Test hammer detection
            total_tests += 1
            if self.test_hammer_detection(price_range, base_price):
                passed_tests += 1
            
            # Test engulfing detection
            total_tests += 1
            if self.test_engulfing_detection(price_range, base_price):
                passed_tests += 1
            
            # Test support/resistance detection
            total_tests += 1
            if self.test_support_resistance(price_range, base_price):
                passed_tests += 1
        
        # Summary
        print(f"\n{'='*80}")
        print("📊 TEST RESULTS SUMMARY")
        print(f"{'='*80}")
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if passed_tests == total_tests:
            print(f"\n🎉 ALL TESTS PASSED! Pattern detection is price-range independent.")
            print(f"✅ The system works correctly across all tested price ranges.")
            return True
        else:
            print(f"\n⚠️ Some tests failed. Pattern detection may have price-range dependencies.")
            print(f"❌ The system needs adjustments for full price-range independence.")
            return False


def main():
    """Run the comprehensive price-range independence test"""
    tester = PriceRangeTest()
    success = tester.run_comprehensive_test()
    
    if success:
        print(f"\n✅ PRICE-RANGE INDEPENDENCE: VERIFIED")
        print(f"🎯 Pattern detection system is ready for production across all asset classes!")
    else:
        print(f"\n❌ PRICE-RANGE INDEPENDENCE: FAILED")
        print(f"🔧 Pattern detection system needs fixes for cross-asset compatibility.")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)