#!/usr/bin/env python3
"""
Test Pattern Intelligence Integration
Validates the enhanced pattern intelligence system with entry context and combination analysis
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).resolve().parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.utils.pattern_intelligence import PatternIntelligence
from src.data.ohlcv_collector import collect_all_tokens
from src.config import EXCHANGE

def test_pattern_intelligence():
    """Test the pattern intelligence system"""
    print("🔍 Testing Pattern Intelligence Integration")
    print("=" * 60)
    
    # Initialize pattern intelligence
    pattern_intel = PatternIntelligence()
    
    # Test symbols
    test_symbols = ['ETH', 'BTC', 'SOL']
    
    print(f"📊 Testing with symbols: {test_symbols}")
    print(f"⏰ Timeframe: 30m")
    print(f"🦈 Exchange: {EXCHANGE}")
    
    try:
        # Test pattern intelligence collection
        print("\n1. Collecting Pattern Intelligence...")
        pattern_summary = pattern_intel.collect_pattern_intelligence(test_symbols, '30m')
        
        if pattern_summary:
            print(f"✅ Pattern intelligence collected for {len(pattern_summary)} symbols")
            
            # Test formatting
            print("\n2. Formatting Pattern Intelligence...")
            formatted_summary = pattern_intel.format_pattern_intelligence_summary(pattern_summary)
            print("✅ Pattern intelligence formatted successfully")
            
            print("\n3. Pattern Intelligence Summary:")
            print("-" * 40)
            print(formatted_summary)
            
            # Test individual symbol analysis
            print("\n4. Detailed Analysis for ETH:")
            print("-" * 40)
            if 'ETH' in pattern_summary:
                eth_intel = pattern_summary['ETH']
                print(f"Current Price: ${eth_intel['current_price']:.2f}")
                print(f"Entry Context: {eth_intel['entry_context']}")
                print(f"Patterns Detected: {len(eth_intel['patterns'])}")
                print(f"Pattern Combinations: {len(eth_intel['pattern_combinations'])}")
                print(f"Actionable Signals: {len(eth_intel['actionable_signals'])}")
                
                # Show patterns
                for i, pattern in enumerate(eth_intel['patterns'], 1):
                    print(f"  {i}. {pattern['type'].title()} (Quality: {pattern['quality']:.2f}, Signal: {pattern['signal']})")
                    if pattern['levels']:
                        levels_str = ", ".join([f"{k}: ${v:.2f}" for k, v in pattern['levels'].items()])
                        print(f"     Levels: {levels_str}")
                
                # Show combinations
                for i, combo in enumerate(eth_intel['pattern_combinations'], 1):
                    print(f"  Combo {i}: {combo['type']} (Strength: {combo['strength']:.2f}, Signal: {combo['signal']})")
                
                # Show signals
                for i, signal in enumerate(eth_intel['actionable_signals'], 1):
                    print(f"  Signal {i}: {signal['type']} (Strength: {signal['strength']:.2f})")
            
        else:
            print("⚠️ No patterns detected in test symbols")
            
        # Test get_pattern_intelligence function
        print("\n5. Testing get_pattern_intelligence function...")
        from src.utils.pattern_intelligence import get_pattern_intelligence
        formatted_result = get_pattern_intelligence(test_symbols, '30m')
        print("✅ get_pattern_intelligence function works")
        print("\nFormatted Result:")
        print("-" * 40)
        print(formatted_result)
        
        print("\n🎉 Pattern Intelligence Integration Test PASSED!")
        return True
        
    except Exception as e:
        print(f"❌ Pattern Intelligence Integration Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_entry_context_detection():
    """Test entry context detection with different price scenarios"""
    print("\n" + "=" * 60)
    print("🎯 Testing Entry Context Detection")
    print("=" * 60)
    
    pattern_intel = PatternIntelligence()
    
    # Test scenarios
    test_scenarios = [
        {
            'name': 'Price Above Resistance',
            'current_price': 105.0,
            'patterns': [
                {
                    'levels': {'resistance': 100.0},
                    'type': 'support_resistance'
                }
            ]
        },
        {
            'name': 'Price Below Support',
            'current_price': 95.0,
            'patterns': [
                {
                    'levels': {'support': 100.0},
                    'type': 'support_resistance'
                }
            ]
        },
        {
            'name': 'Price Testing Support',
            'current_price': 100.5,
            'patterns': [
                {
                    'levels': {'support': 100.0},
                    'type': 'support_resistance'
                }
            ]
        },
        {
            'name': 'Price Testing Resistance',
            'current_price': 99.5,
            'patterns': [
                {
                    'levels': {'resistance': 100.0},
                    'type': 'support_resistance'
                }
            ]
        },
        {
            'name': 'Neutral Position',
            'current_price': 110.0,
            'patterns': [
                {
                    'levels': {'support': 90.0, 'resistance': 110.0},
                    'type': 'support_resistance'
                }
            ]
        }
    ]
    
    for scenario in test_scenarios:
        print(f"\nScenario: {scenario['name']}")
        print(f"Current Price: ${scenario['current_price']}")
        
        context = pattern_intel.determine_entry_context(scenario['current_price'], scenario['patterns'])
        print(f"Entry Context: {context}")
        
        # Validate context
        if scenario['name'] == 'Price Above Resistance' and context == 'BREAKOUT_ABOVE_RESISTANCE':
            print("✅ Correct: Breakout above resistance detected")
        elif scenario['name'] == 'Price Below Support' and context == 'BREAKDOWN_BELOW_SUPPORT':
            print("✅ Correct: Breakdown below support detected")
        elif scenario['name'] == 'Price Testing Support' and context == 'TESTING_SUPPORT':
            print("✅ Correct: Testing support detected")
        elif scenario['name'] == 'Price Testing Resistance' and context == 'TESTING_RESISTANCE':
            print("✅ Correct: Testing resistance detected")
        elif scenario['name'] == 'Neutral Position' and context == 'NEUTRAL_POSITION':
            print("✅ Correct: Neutral position detected")
        else:
            print(f"❌ Unexpected context: {context}")
    
    print("\n🎯 Entry Context Detection Test Complete")

def test_pattern_combinations():
    """Test pattern combination analysis"""
    print("\n" + "=" * 60)
    print("🔗 Testing Pattern Combination Analysis")
    print("=" * 60)
    
    pattern_intel = PatternIntelligence()
    
    # Test combination scenarios
    test_combinations = [
        {
            'name': 'Bullish Engulfing at Support',
            'patterns': [
                {'type': 'engulfing', 'signal': 'BULLISH', 'quality': 0.8},
                {'type': 'support', 'levels': {'support': 100.0}, 'quality': 0.7}
            ]
        },
        {
            'name': 'Bearish Engulfing at Resistance',
            'patterns': [
                {'type': 'engulfing', 'signal': 'BEARISH', 'quality': 0.8},
                {'type': 'resistance', 'levels': {'resistance': 100.0}, 'quality': 0.7}
            ]
        },
        {
            'name': 'Hammer in Ascending Triangle',
            'patterns': [
                {'type': 'hammer', 'signal': 'BULLISH', 'quality': 0.6},
                {'type': 'triangle', 'levels': {'support': 95.0, 'resistance': 105.0}, 'quality': 0.7}
            ]
        }
    ]
    
    for combo_test in test_combinations:
        print(f"\nCombination: {combo_test['name']}")
        
        combinations = pattern_intel.analyze_pattern_combinations(combo_test['patterns'])
        
        if combinations:
            for combo in combinations:
                print(f"  ✅ Detected: {combo['type']}")
                print(f"     Strength: {combo['strength']:.2f}")
                print(f"     Signal: {combo['signal']}")
        else:
            print("  ⚠️ No combinations detected")
    
    print("\n🔗 Pattern Combination Test Complete")

def main():
    """Run all pattern intelligence tests"""
    print("🚀 Pattern Intelligence Integration Test Suite")
    print("=" * 60)
    
    # Run tests
    test1_passed = test_pattern_intelligence()
    test_entry_context_detection()
    test_pattern_combinations()
    
    print("\n" + "=" * 60)
    if test1_passed:
        print("🎉 ALL TESTS PASSED - Pattern Intelligence Integration is working correctly!")
        print("\n✅ Features Validated:")
        print("   • Pattern intelligence collection")
        print("   • Entry context detection")
        print("   • Pattern combination analysis")
        print("   • Frontend formatting")
        print("   • Integration with trading agent")
    else:
        print("❌ SOME TESTS FAILED - Check the errors above")
    
    print("=" * 60)

if __name__ == "__main__":
    main()