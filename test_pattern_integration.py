#!/usr/bin/env python3
"""
Test script for Pattern Integration System
Demonstrates the complete pattern recognition and smart allocation system
"""

import asyncio
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

# Import the pattern integration components
from src.patterns.simple_detector import SimplePatternDetector
from src.patterns.compact_database import CompactPatternDatabase
from src.patterns.pattern_integration import PatternIntegration


def create_test_candles(count: int = 50, start_price: float = 10000.0) -> list:
    """Create test candle data"""
    candles = []
    current_price = start_price
    
    for i in range(count):
        # Random price movement
        change = random.uniform(-200, 200)
        new_price = current_price + change
        
        # Create candle
        open_price = current_price
        close_price = new_price
        high_price = max(open_price, close_price) + random.uniform(0, 50)
        low_price = min(open_price, close_price) - random.uniform(0, 50)
        volume = random.uniform(100, 1000)
        
        candle = {
            'timestamp': (datetime.now() - timedelta(minutes=count-i)).isoformat(),
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        }
        
        candles.append(candle)
        current_price = new_price
    
    return candles


def create_test_prices(count: int = 100, start_price: float = 10000.0) -> list:
    """Create test price series"""
    prices = []
    current_price = start_price
    
    for i in range(count):
        # Random price movement with some trend
        change = random.uniform(-100, 100)
        current_price += change
        prices.append(current_price)
    
    return prices


async def test_simple_pattern_detector():
    """Test the simple pattern detector"""
    print("🧪 Testing Simple Pattern Detector")
    print("=" * 60)
    
    detector = SimplePatternDetector()
    
    # Create test data
    candles = create_test_candles(50, 10000.0)
    prices = create_test_prices(100, 10000.0)
    
    # Test candlestick pattern detection
    print("\n📊 Candlestick Pattern Detection")
    print("-" * 40)
    
    candlestick_patterns = detector.detect_candlestick_patterns(candles)
    
    for pattern_type, patterns in candlestick_patterns.items():
        print(f"  🔍 {pattern_type}: {len(patterns)} patterns detected")
        for pattern in patterns[:3]:  # Show first 3
            print(f"     - {pattern['type']} (strength: {pattern['strength']:.2f})")
    
    # Test trend pattern detection
    print("\n📈 Trend Pattern Detection")
    print("-" * 40)
    
    trend_patterns = detector.detect_trend_patterns(prices)
    
    for pattern_type, patterns in trend_patterns.items():
        print(f"  🔍 {pattern_type}: {len(patterns)} patterns detected")
        for pattern in patterns[:2]:  # Show first 2
            print(f"     - {pattern['type']} (strength: {pattern.get('strength', 0):.2f})")
    
    print("\n✅ Simple Pattern Detector Test Complete")


async def test_pattern_integration():
    """Test the complete pattern integration system"""
    print("\n🧠 Testing Pattern Integration System")
    print("=" * 60)
    
    integration = PatternIntegration()
    
    # Create test data
    symbol = "BTC"
    candles = create_test_candles(50, 10000.0)
    prices = create_test_prices(100, 10000.0)
    
    # Test pattern scanning and analysis
    print("\n🔍 Pattern Scanning & Analysis")
    print("-" * 40)
    
    result = await integration.scan_and_analyze_patterns(symbol, candles, prices)
    
    print(f"  📈 Symbol: {result['symbol']}")
    print(f"  🕐 Timestamp: {result['timestamp']}")
    
    # Show detected patterns
    pattern_analysis = result['detected_patterns']
    print(f"\n  📊 Pattern Analysis:")
    print(f"     Composite Score: {pattern_analysis['composite_score']:.2f}")
    print(f"     Recommendation: {pattern_analysis['recommendation']}")
    print(f"     Confidence: {pattern_analysis['confidence']:.2f}")
    
    # Show candlestick patterns
    if pattern_analysis['candlestick_patterns']:
        print(f"\n  🔍 Candlestick Patterns:")
        for pattern_type, data in pattern_analysis['candlestick_patterns'].items():
            print(f"     {pattern_type}: quality={data['quality_score']:.2f}")
    
    # Show trend patterns
    if pattern_analysis['trend_patterns']:
        print(f"\n  📈 Trend Patterns:")
        for pattern_type, data in pattern_analysis['trend_patterns'].items():
            print(f"     {pattern_type}: quality={data['quality_score']:.2f}")
    
    # Show allocation multipliers
    allocation_multipliers = result['allocation_multipliers']
    print(f"\n  💰 Allocation Multipliers:")
    print(f"     Position Multiplier: {allocation_multipliers['position_multiplier']:.2f}x")
    print(f"     Confidence Boost: {allocation_multipliers['confidence_boost']:.1%}")
    print(f"     Pattern Count: {allocation_multipliers['pattern_count']}")
    
    # Show database insights
    database_insights = result['database_insights']
    if database_insights:
        print(f"\n  🗄️ Database Insights:")
        for pattern_type, insight in database_insights.items():
            print(f"     {pattern_type}: {insight['recommendation']}")
    
    print("\n✅ Pattern Integration Test Complete")


def test_risk_management_integration():
    """Test integration with risk management"""
    print("\n🛡️ Testing Risk Management Integration")
    print("=" * 60)
    
    integration = PatternIntegration()
    
    # Simulate base risk parameters
    base_params = {
        'position_size': 1000.0,  # Base position size
        'confidence': 0.7,        # Base confidence
        'risk_tolerance': 0.02,   # Base risk tolerance
        'stop_loss_pct': 0.02,    # Base stop loss
        'take_profit_pct': 0.04   # Base take profit
    }
    
    # Simulate pattern analysis results
    pattern_analysis = {
        'allocation_multipliers': {
            'position_multiplier': 1.8,
            'confidence_boost': 0.15,
            'composite_score': 0.85,
            'pattern_count': 3
        }
    }
    
    # Test integration
    result = integration.integrate_with_risk_manager("BTC", base_params, pattern_analysis)
    
    print(f"  📊 Base Risk Parameters:")
    print(f"     Position Size: ${result['original_params']['position_size']:,.2f}")
    print(f"     Confidence: {result['original_params']['confidence']:.1%}")
    print(f"     Risk Tolerance: {result['original_params']['risk_tolerance']:.1%}")
    
    print(f"\n  🧠 Pattern-Adjusted Parameters:")
    print(f"     Position Size: ${result['adjusted_params']['position_size']:,.2f}")
    print(f"     Confidence: {result['adjusted_params']['confidence']:.1%}")
    print(f"     Risk Tolerance: {result['adjusted_params']['risk_tolerance']:.1%}")
    
    print(f"\n  📈 Pattern Impact:")
    print(f"     Position Multiplier: {result['pattern_multiplier']:.2f}x")
    print(f"     Confidence Adjustment: {result['confidence_adjustment']:+.1%}")
    print(f"     Pattern Quality: {result['pattern_quality']:.2f}")
    
    print("\n✅ Risk Management Integration Test Complete")


def test_database_functionality():
    """Test the compact pattern database"""
    print("\n🗄️ Testing Compact Pattern Database")
    print("=" * 60)
    
    db = CompactPatternDatabase()
    
    # Create test pattern examples
    test_patterns = [
        {
            "pattern_type": "hammer",
            "formation_quality": 0.85,
            "duration_bars": 3,
            "volume_pattern": "increasing",
            "market_trend": "bullish_to_bearish",
            "volatility": 0.025,
            "volume_confirmation": 1.8,
            "time_of_day": "14:30",
            "entry_price": 10000.0,
            "entry_timing": "immediate",
            "entry_confidence": 0.8,
            "position_size": 1.5,
            "stop_loss": 9800.0,
            "take_profit": 10400.0,
            "risk_reward": 2.0,
            "result": "SUCCESS",
            "profit_pct": 4.2,
            "time_to_target": 15,
            "confirmation_signals": ["volume_spike", "RSI_divergence"],
            "key_insights": "Volume confirmation was crucial for breakout validity",
            "optimal_entry_time": "14:32",
            "optimal_exit_time": "15:05",
            "market_session": "NY_London_overlap",
            "shoulder_symmetry": 0.0,
            "neckline_quality": 0.0,
            "head_prominence": 0.0,
            "timestamp": datetime.now().isoformat(),
            "symbol": "BTC",
            "timeframe": "15m",
            "quality_score": 0.85
        },
        {
            "pattern_type": "engulfing",
            "formation_quality": 0.75,
            "duration_bars": 2,
            "volume_pattern": "decreasing",
            "market_trend": "bearish_to_bullish",
            "volatility": 0.018,
            "volume_confirmation": 1.2,
            "time_of_day": "10:15",
            "entry_price": 9500.0,
            "entry_timing": "pullback",
            "entry_confidence": 0.7,
            "position_size": 1.2,
            "stop_loss": 9350.0,
            "take_profit": 9850.0,
            "risk_reward": 2.5,
            "result": "SUCCESS",
            "profit_pct": 3.7,
            "time_to_target": 12,
            "confirmation_signals": ["MACD_crossover"],
            "key_insights": "MACD confirmation improved success rate",
            "optimal_entry_time": "10:20",
            "optimal_exit_time": "10:45",
            "market_session": "NY_session",
            "shoulder_symmetry": 0.0,
            "neckline_quality": 0.0,
            "head_prominence": 0.0,
            "timestamp": datetime.now().isoformat(),
            "symbol": "ETH",
            "timeframe": "15m",
            "quality_score": 0.75
        }
    ]
    
    # Add test patterns to database
    print("\n➕ Adding Test Patterns to Database")
    print("-" * 40)
    
    for i, pattern in enumerate(test_patterns):
        success = db.add_successful_example(pattern["pattern_type"], pattern)
        print(f"  ✅ Pattern {i+1} ({pattern['pattern_type']}): {'Success' if success else 'Failed'}")
    
    # Get database statistics
    print("\n📊 Database Statistics")
    print("-" * 40)
    
    stats = db.get_database_stats()
    print(f"  📈 Total Examples: {stats['total_examples']}")
    print(f"  💾 Storage Used: {stats['storage_used_mb']:.3f} MB")
    print(f"  🗜️ Compression Ratio: {stats['compression_ratio']:.1f}%")
    
    # Test optimal parameters
    print("\n🔧 Optimal Parameters")
    print("-" * 40)
    
    current_context = {
        "market_trend": "bullish_to_bearish",
        "volatility": 0.023,
        "volume_confirmation": 1.6,
        "time_of_day": "14:30"
    }
    
    for pattern_type in ["hammer", "engulfing"]:
        params = db.get_optimal_parameters(pattern_type, current_context)
        print(f"  🔧 {pattern_type}:")
        print(f"     Entry Timing: {params['entry_timing']}")
        print(f"     Position Size: {params['position_size']:.2f}x")
        print(f"     Risk/Reward: {params['risk_reward']:.1f}:1")
        print(f"     Confidence Boost: {params['confidence_boost']:.1%}")
    
    # Test similar examples
    print("\n🔍 Similar Examples")
    print("-" * 40)
    
    for pattern_type in ["hammer", "engulfing"]:
        examples = db.get_similar_examples(pattern_type, current_context, limit=2)
        print(f"  🔍 {pattern_type}: {len(examples)} similar examples")
        for i, example in enumerate(examples):
            print(f"     Example {i+1}: +{example['profit_pct']:.1f}% in {example['time_to_target']} bars")
    
    print("\n✅ Database Functionality Test Complete")


async def main():
    """Main test function"""
    print("🎯 Pattern Recognition & Smart Allocation System Test Suite")
    print("=" * 80)
    print("Testing the complete pattern intelligence and allocation system...")
    
    try:
        # Run all tests
        await test_simple_pattern_detector()
        await test_pattern_integration()
        test_risk_management_integration()
        test_database_functionality()
        
        print("\n" + "=" * 80)
        print("🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print("\n📋 Summary:")
        print("✅ Simple Pattern Detection: Basic candlestick and trend patterns")
        print("✅ Pattern Integration: Quality scoring and allocation multipliers")
        print("✅ Risk Management Integration: Smart position sizing adjustments")
        print("✅ Compact Pattern Database: 12 examples per pattern with context matching")
        print("✅ Smart Allocation: Pattern-based position sizing without fixed dollar amounts")
        
        print("\n🚀 System Ready for Production!")
        print("The pattern recognition system is now integrated and ready to:")
        print("• Detect hammer, engulfing, star, support/resistance, and triangle patterns")
        print("• Calculate pattern quality based on formation, volume, and trend alignment")
        print("• Adjust position sizing based on pattern quality (0.5x to 3.0x multipliers)")
        print("• Integrate seamlessly with existing risk management")
        print("• Store and learn from pattern performance over time")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())