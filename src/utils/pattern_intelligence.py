"""
Pattern Intelligence System
Enhanced pattern analysis with entry context and combination analysis
Similar to volume intelligence - loaded once per cycle with frontend logging
"""

import logging
import sys
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

# Add project root to path for imports
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.patterns.pattern_integration import PatternIntegration
from src.patterns.simple_detector import SimplePatternDetector
from src.data.ohlcv_collector import collect_all_tokens

# Configure logging
logger = logging.getLogger(__name__)


class PatternIntelligence:
    """Enhanced pattern intelligence system with entry context analysis"""
    
    def __init__(self, data_dir: Optional[str] = None):
        """Initialize pattern intelligence system"""
        self.pattern_integration = PatternIntegration(data_dir)
        self.detector = SimplePatternDetector()
        self.data_dir = data_dir
        
        logger.info("Pattern Intelligence system initialized")
    
    def collect_pattern_intelligence(self, symbols: List[str], timeframe: str = '30m') -> Dict[str, Any]:
        """Collect pattern intelligence for all symbols (like volume intelligence)"""
        pattern_summary = {}
        
        logger.info(f"Collecting pattern intelligence for {len(symbols)} symbols")
        
        for symbol in symbols:
            try:
                # Get current market data for this symbol
                market_data = self.get_market_data(symbol, timeframe)
                
                if not market_data or not market_data.get('candles'):
                    continue
                
                # Analyze patterns
                pattern_analysis = self.pattern_integration.scan_and_analyze_patterns(
                    symbol, market_data['candles'], market_data['prices']
                )
                
                # Extract actionable intelligence
                intelligence = self.extract_pattern_intelligence(
                    symbol, pattern_analysis, market_data
                )
                
                if intelligence:
                    pattern_summary[symbol] = intelligence
                    
            except Exception as e:
                logger.warning(f"Error collecting pattern intelligence for {symbol}: {e}")
                continue
        
        return pattern_summary
    
    def get_market_data(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Get market data for a symbol"""
        try:
            # Use the existing market data collection
            market_data = collect_all_tokens(
                tokens=[symbol],
                days_back=2,
                timeframe=timeframe,
                exchange="HYPERLIQUID"  # Use configured exchange
            )
            
            if symbol in market_data:
                df = market_data[symbol]
                if not df.empty:
                    # Convert to required format
                    candles = []
                    prices = []
                    
                    for _, row in df.iterrows():
                        # Convert timestamp to ISO format string
                        timestamp_str = row.name.isoformat() if hasattr(row.name, 'isoformat') else str(row.name)
                        
                        candle = {
                            'timestamp': timestamp_str,
                            'open': float(row['Open']),
                            'high': float(row['High']),
                            'low': float(row['Low']),
                            'close': float(row['Close']),
                            'volume': float(row.get('Volume', 0))
                        }
                        candles.append(candle)
                        prices.append(float(row['Close']))
                    
                    return {
                        'candles': candles,
                        'prices': prices,
                        'symbol': symbol
                    }
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {e}")
            return {}
    
    def extract_pattern_intelligence(self, symbol: str, pattern_analysis: Dict, market_data: Dict) -> Dict[str, Any]:
        """Extract actionable intelligence from pattern analysis"""
        current_price = market_data['prices'][-1] if market_data['prices'] else 0
        intelligence = {
            'patterns': [],
            'support_levels': [],
            'resistance_levels': [],
            'entry_context': 'NEUTRAL',
            'pattern_combinations': [],
            'actionable_signals': [],
            'current_price': current_price
        }
        
        # Extract individual patterns
        detected_patterns = pattern_analysis.get('detected_patterns', {})
        for pattern_type, patterns in detected_patterns.items():
            for pattern in patterns:
                if pattern.get('quality_score', 0) > 0.6:  # Only high-quality patterns
                    pattern_intel = self.analyze_individual_pattern(
                        pattern_type, pattern, market_data, current_price
                    )
                    if pattern_intel:
                        intelligence['patterns'].append(pattern_intel)
        
        # Analyze pattern combinations
        intelligence['pattern_combinations'] = self.analyze_pattern_combinations(
            intelligence['patterns']
        )
        
        # Determine entry context based on price vs pattern levels
        intelligence['entry_context'] = self.determine_entry_context(
            current_price, intelligence['patterns']
        )
        
        # Generate actionable signals
        intelligence['actionable_signals'] = self.generate_actionable_signals(
            intelligence, current_price
        )
        
        return intelligence if intelligence['patterns'] else None
    
    def analyze_individual_pattern(self, pattern_type: str, pattern: Dict, market_data: Dict, current_price: float) -> Dict[str, Any]:
        """Analyze individual pattern and extract intelligence"""
        pattern_intel = {
            'type': pattern_type,
            'quality': pattern.get('quality_score', 0),
            'strength': pattern.get('strength', 0.5),
            'levels': {},
            'context': 'NEUTRAL',
            'signal': 'NEUTRAL'
        }
        
        # Extract pattern-specific levels
        if pattern_type in ['hammer', 'engulfing', 'star_patterns']:
            pattern_intel['levels'] = self.extract_candlestick_levels(pattern, market_data)
        elif pattern_type in ['support_resistance', 'triangles']:
            pattern_intel['levels'] = self.extract_trend_levels(pattern, market_data)
        
        # Analyze context relative to current price
        pattern_intel['context'] = self.analyze_pattern_context(
            pattern_type, pattern_intel['levels'], current_price
        )
        
        # Generate signal
        pattern_intel['signal'] = self.generate_pattern_signal(
            pattern_type, pattern_intel['quality'], pattern_intel['context']
        )
        
        return pattern_intel
    
    def extract_candlestick_levels(self, pattern: Dict, market_data: Dict) -> Dict[str, float]:
        """Extract support/resistance levels from candlestick patterns"""
        levels = {}
        
        # For candlestick patterns, use the candle's high/low as levels
        candle_data = pattern.get('candle_data', {})
        if candle_data:
            levels['support'] = float(candle_data.get('low', 0))
            levels['resistance'] = float(candle_data.get('high', 0))
        
        return levels
    
    def extract_trend_levels(self, pattern: Dict, market_data: Dict) -> Dict[str, float]:
        """Extract support/resistance levels from trend patterns"""
        levels = {}
        
        # For trend patterns, use the detected levels
        if pattern.get('type') == 'support':
            levels['support'] = float(pattern.get('price', 0))
        elif pattern.get('type') == 'resistance':
            levels['resistance'] = float(pattern.get('price', 0))
        elif pattern.get('type') == 'triangle':
            # Use triangle boundaries
            levels['support'] = float(pattern.get('lower_bound', 0))
            levels['resistance'] = float(pattern.get('upper_bound', 0))
        
        return levels
    
    def analyze_pattern_context(self, pattern_type: str, levels: Dict[str, float], current_price: float) -> str:
        """Analyze pattern context relative to current price"""
        if not levels:
            return 'NEUTRAL'
        
        context = 'NEUTRAL'
        
        # Check support levels
        if 'support' in levels:
            support_price = levels['support']
            if current_price < support_price * 0.995:  # 0.5% below support
                context = 'BREAKDOWN_BELOW_SUPPORT'
            elif current_price < support_price * 1.005:  # 0.5% above support
                context = 'TESTING_SUPPORT'
        
        # Check resistance levels
        if 'resistance' in levels:
            resistance_price = levels['resistance']
            if current_price > resistance_price * 1.005:  # 0.5% above resistance
                context = 'BREAKOUT_ABOVE_RESISTANCE'
            elif current_price > resistance_price * 0.995:  # 0.5% below resistance
                context = 'TESTING_RESISTANCE'
        
        return context
    
    def determine_entry_context(self, current_price: float, patterns: List[Dict]) -> str:
        """Determine overall entry context based on all patterns"""
        support_breaches = 0
        resistance_breaches = 0
        support_tests = 0
        resistance_tests = 0
        
        for pattern in patterns:
            levels = pattern.get('levels', {})
            
            # Check support levels
            if 'support' in levels:
                support_price = levels['support']
                if current_price < support_price * 0.995:  # 0.5% below support
                    support_breaches += 1
                elif current_price < support_price * 1.005:  # 0.5% above support
                    support_tests += 1
            
            # Check resistance levels
            if 'resistance' in levels:
                resistance_price = levels['resistance']
                if current_price > resistance_price * 1.005:  # 0.5% above resistance
                    resistance_breaches += 1
                elif current_price > resistance_price * 0.995:  # 0.5% below resistance
                    resistance_tests += 1
        
        # Determine overall context
        if support_breaches > 0:
            return "BREAKDOWN_BELOW_SUPPORT"
        elif resistance_breaches > 0:
            return "BREAKOUT_ABOVE_RESISTANCE"
        elif support_tests > 0:
            return "TESTING_SUPPORT"
        elif resistance_tests > 0:
            return "TESTING_RESISTANCE"
        else:
            return "NEUTRAL_POSITION"
    
    def analyze_pattern_combinations(self, patterns: List[Dict]) -> List[Dict[str, Any]]:
        """Analyze combinations of patterns for enhanced signals"""
        combinations = []
        
        # Convert to sets for easier checking
        pattern_types = {p['type'] for p in patterns}
        contexts = {p.get('context', 'NEUTRAL') for p in patterns}
        
        # Bullish combinations
        if 'engulfing' in pattern_types and any(p['type'] == 'engulfing' and p['signal'] == 'BULLISH' for p in patterns):
            if 'support' in pattern_types or any('support' in p.get('levels', {}) for p in patterns):
                combinations.append({
                    'type': 'BULLISH_ENGULFING_AT_SUPPORT',
                    'strength': self.calculate_combination_strength(patterns, ['engulfing', 'support']),
                    'signal': 'STRONG_BUY'
                })
        
        if 'hammer' in pattern_types:
            if any('triangle' in p.get('levels', {}) for p in patterns):
                combinations.append({
                    'type': 'HAMMER_IN_ASCENDING_TRIANGLE',
                    'strength': self.calculate_combination_strength(patterns, ['hammer', 'triangle']),
                    'signal': 'MODERATE_BUY'
                })
        
        # Bearish combinations
        if 'engulfing' in pattern_types and any(p['type'] == 'engulfing' and p['signal'] == 'BEARISH' for p in patterns):
            if 'resistance' in pattern_types or any('resistance' in p.get('levels', {}) for p in patterns):
                combinations.append({
                    'type': 'BEARISH_ENGULFING_AT_RESISTANCE',
                    'strength': self.calculate_combination_strength(patterns, ['engulfing', 'resistance']),
                    'signal': 'STRONG_SELL'
                })
        
        # Neutral/consolidation patterns
        if len(patterns) >= 2 and all(p['signal'] == 'NEUTRAL' for p in patterns):
            combinations.append({
                'type': 'CONSOLIDATION_PATTERN',
                'strength': 0.5,
                'signal': 'WAIT_FOR_BREAKOUT'
            })
        
        return combinations
    
    def calculate_combination_strength(self, patterns: List[Dict], pattern_types: List[str]) -> float:
        """Calculate strength of pattern combination"""
        relevant_patterns = [p for p in patterns if p['type'] in pattern_types]
        if not relevant_patterns:
            return 0.0
        
        # Average quality of relevant patterns
        total_quality = sum(p['quality'] for p in relevant_patterns)
        return total_quality / len(relevant_patterns)
    
    def generate_actionable_signals(self, intelligence: Dict, current_price: float) -> List[Dict[str, Any]]:
        """Generate actionable trading signals from pattern intelligence"""
        signals = []
        
        # Signal from individual patterns
        for pattern in intelligence['patterns']:
            if pattern['signal'] in ['BULLISH', 'BEARISH']:
                signals.append({
                    'type': f"PATTERN_{pattern['signal']}",
                    'strength': pattern['quality'],
                    'description': f"{pattern['type'].title()} pattern detected",
                    'price_level': current_price
                })
        
        # Signal from pattern combinations
        for combination in intelligence['pattern_combinations']:
            if combination['signal'] in ['STRONG_BUY', 'STRONG_SELL', 'MODERATE_BUY']:
                signals.append({
                    'type': f"COMBO_{combination['signal']}",
                    'strength': combination['strength'],
                    'description': f"{combination['type']} combination",
                    'price_level': current_price
                })
        
        # Signal from entry context
        if intelligence['entry_context'] in ['BREAKOUT_ABOVE_RESISTANCE', 'BREAKDOWN_BELOW_SUPPORT']:
            signals.append({
                'type': f"ENTRY_{intelligence['entry_context']}",
                'strength': 0.8,
                'description': f"Price action signal: {intelligence['entry_context']}",
                'price_level': current_price
            })
        
        return signals
    
    def generate_pattern_signal(self, pattern_type: str, quality: float, context: str) -> str:
        """Generate trading signal from pattern"""
        if pattern_type in ['hammer', 'morning_star']:
            return 'BULLISH' if quality > 0.7 else 'NEUTRAL'
        elif pattern_type in ['evening_star', 'bearish_engulfing']:
            return 'BEARISH' if quality > 0.7 else 'NEUTRAL'
        elif pattern_type == 'bullish_engulfing':
            return 'BULLISH' if quality > 0.6 else 'NEUTRAL'
        elif pattern_type == 'bearish_engulfing':
            return 'BEARISH' if quality > 0.6 else 'NEUTRAL'
        else:
            return 'NEUTRAL'
    
    def format_pattern_intelligence_summary(self, pattern_summary: Dict[str, Any]) -> str:
        """Format pattern intelligence for frontend display (like volume intelligence)"""
        if not pattern_summary:
            return "No significant patterns detected"
        
        summary_lines = ["📊 Pattern Intelligence Summary:"]
        
        for symbol, intel in pattern_summary.items():
            summary_lines.append(f"\n{symbol}:")
            
            # Current price
            summary_lines.append(f"  • Current Price: ${intel['current_price']:.2f}")
            
            # Patterns
            for pattern in intel['patterns']:
                summary_lines.append(f"  • {pattern['type'].title()} (Quality: {pattern['quality']:.2f}, Signal: {pattern['signal']})")
                if pattern['levels']:
                    levels_str = ", ".join([f"{k}: ${v:.2f}" for k, v in pattern['levels'].items()])
                    summary_lines.append(f"    Levels: {levels_str}")
            
            # Entry context
            summary_lines.append(f"  • Context: {intel['entry_context']}")
            
            # Pattern combinations
            for combo in intel['pattern_combinations']:
                summary_lines.append(f"  • Combo: {combo['type']} (Strength: {combo['strength']:.2f}, Signal: {combo['signal']})")
            
            # Actionable signals
            for signal in intel['actionable_signals']:
                summary_lines.append(f"  • Signal: {signal['type']} (Strength: {signal['strength']:.2f})")
        
        return "\n".join(summary_lines)
    
    def get_pattern_intelligence_for_trading(self, symbols: List[str], timeframe: str = '30m', market_data_dict: Optional[Dict[str, Any]] = None) -> str:
        """Get formatted pattern intelligence for trading cycle (like volume intelligence)
        
        Args:
            symbols: List of token symbols to analyze
            timeframe: Timeframe of the data (for logging/context)
            market_data_dict: Optional dictionary of {symbol: DataFrame} with OHLCV data
                             If provided, uses existing data instead of fetching new data
        """
        try:
            # Use smart collection method that can use existing data
            pattern_summary = self.collect_pattern_intelligence_smart(symbols, market_data_dict, timeframe)
            formatted_summary = self.format_pattern_intelligence_summary(pattern_summary)
            
            # Log for debugging
            logger.info(f"Pattern intelligence collected for {len(pattern_summary)} symbols")
            
            return formatted_summary
            
        except Exception as e:
            logger.error(f"Error getting pattern intelligence: {e}")
            return "Pattern intelligence unavailable"

    def collect_pattern_intelligence_smart(self, symbols: List[str], market_data_dict: Optional[Dict[str, Any]] = None, timeframe: str = '30m') -> Dict[str, Any]:
        """Smart pattern intelligence collection that uses existing data when available
        
        Args:
            symbols: List of token symbols to analyze
            market_data_dict: Optional dictionary of {symbol: DataFrame} with OHLCV data
                             If provided, uses existing data instead of fetching new data
            timeframe: Timeframe of the data (for logging/context)
            
        Returns:
            Dictionary of {symbol: pattern_intelligence_data}
        """
        pattern_summary = {}
        
        logger.info(f"🔍 Analyzing patterns for {len(symbols)} symbols (timeframe: {timeframe})")
        
        successful = 0
        failed = 0
        total_patterns = 0
        
        for symbol in symbols:
            try:
                # Check if we have data for this symbol
                if market_data_dict and symbol in market_data_dict:
                    # Use existing market data (NO RE-FETCH)
                    df = market_data_dict[symbol]
                    
                    # Validate DataFrame
                    if df.empty:
                        logger.debug(f"Empty DataFrame for {symbol}, skipping")
                        continue
                    
                    # Validate required columns
                    required_cols = ['Open', 'High', 'Low', 'Close']
                    if not all(col in df.columns for col in required_cols):
                        logger.warning(f"Missing OHLCV columns for {symbol}, skipping")
                        continue
                    
                    # Convert DataFrame to pattern detector format
                    candles, prices = self._convert_df_to_candles(df)
                    
                    if not candles or len(candles) < 10:
                        logger.debug(f"Insufficient candles for {symbol} ({len(candles)}), skipping")
                        continue
                    
                else:
                    # Fallback to current behavior - fetch data
                    market_data = self.get_market_data(symbol, timeframe)
                    
                    if not market_data or not market_data.get('candles'):
                        continue
                    
                    candles = market_data['candles']
                    prices = market_data['prices']
                
                # Analyze patterns using existing method
                pattern_analysis = asyncio.run(
                    self.pattern_integration.scan_and_analyze_patterns(
                        symbol, candles, prices
                    )
                )
                
                # Extract actionable intelligence
                intelligence = self.extract_pattern_intelligence(
                    symbol, pattern_analysis, {'candles': candles, 'prices': prices, 'symbol': symbol}
                )
                
                if intelligence and intelligence.get('patterns'):
                    # Limit patterns per symbol to prevent bloat
                    intelligence['patterns'] = sorted(
                        intelligence['patterns'],
                        key=lambda x: x.get('quality', 0),
                        reverse=True
                    )[:5]  # Keep top 5 patterns only
                    
                    pattern_summary[symbol] = intelligence
                    total_patterns += len(intelligence['patterns'])
                    successful += 1
                
            except Exception as e:
                logger.warning(f"Pattern detection failed for {symbol}: {e}")
                failed += 1
                continue
        
        logger.info(
            f"✅ Pattern analysis complete: {successful} succeeded, "
            f"{failed} failed, {total_patterns} patterns detected"
        )
        
        return pattern_summary

    def _convert_df_to_candles(self, df: Any) -> Tuple[List[Dict], List[float]]:
        """
        Convert pandas DataFrame to pattern detector format.
        
        Args:
            df: DataFrame with OHLCV data (index = timestamp)
            
        Returns:
            Tuple of (candles list, prices list)
        """
        candles = []
        prices = []
        
        try:
            for idx, row in df.iterrows():
                # Handle timestamp - could be datetime index or column
                if hasattr(idx, 'isoformat'):
                    timestamp_str = idx.isoformat()
                else:
                    timestamp_str = str(idx)
                
                # Extract OHLCV values with robust type conversion
                candle = {
                    'timestamp': timestamp_str,
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                    'volume': float(row.get('Volume', 0))
                }
                candles.append(candle)
                prices.append(float(row['Close']))
            
        except Exception as e:
            logger.error(f"Error converting DataFrame to candles: {e}")
            return [], []
        
        return candles, prices


# Create global instance
pattern_intelligence = PatternIntelligence()


def get_pattern_intelligence(symbols: List[str], timeframe: str = '30m', market_data_dict: Optional[Dict[str, Any]] = None) -> str:
    """Get pattern intelligence for trading (similar to volume intelligence)
    
    Args:
        symbols: List of token symbols to analyze
        timeframe: Timeframe of the data (for logging/context)
        market_data_dict: Optional dictionary of {symbol: DataFrame} with OHLCV data
                         If provided, uses existing data instead of fetching new data
    """
    return pattern_intelligence.get_pattern_intelligence_for_trading(symbols, timeframe, market_data_dict)


def collect_pattern_intelligence_smart(symbols: List[str], market_data_dict: Optional[Dict[str, Any]] = None, timeframe: str = '30m') -> Dict[str, Any]:
    """Smart pattern intelligence collection that uses existing data when available
    
    Args:
        symbols: List of token symbols to analyze
        market_data_dict: Optional dictionary of {symbol: DataFrame} with OHLCV data
                         If provided, uses existing data instead of fetching new data
        timeframe: Timeframe of the data (for logging/context)
        
    Returns:
        Dictionary of {symbol: pattern_intelligence_data}
    """
    return pattern_intelligence.collect_pattern_intelligence_smart(symbols, market_data_dict, timeframe)
