"""
Pattern Integration System
Integrates simple pattern detection with the compact pattern database and risk management
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

# Import components
from src.patterns.simple_detector import SimplePatternDetector
from src.patterns.compact_database import get_pattern_database
from src.agents.database_integration import get_database_integration
from src.risk.risk_manager import RiskManager

# Configure logging
logger = logging.getLogger(__name__)


class PatternIntegration:
    """Integrates pattern detection with database and risk management"""
    
    def __init__(self, data_dir: Optional[str] = None):
        """Initialize pattern integration system"""
        self.detector = SimplePatternDetector()
        self.pattern_db = get_pattern_database(data_dir)
        self.database_integration = get_database_integration(data_dir)
        self.risk_manager = RiskManager()  # Your existing risk manager
        
        logger.info("Pattern Integration system initialized")
    
    async def scan_and_analyze_patterns(self, symbol: str, candles: List[Dict], prices: List[float]) -> Dict[str, Any]:
        """
        Scan for patterns and analyze their quality for trading decisions
        
        Args:
            symbol: Trading symbol (e.g., 'BTC')
            candles: OHLCV candle data
            prices: Price series for trend analysis
            
        Returns:
            Pattern analysis results with quality scoring and allocation recommendations
        """
        try:
            logger.info(f"Scanning patterns for {symbol}")
            
            # 1. Detect patterns using simple detector
            candlestick_patterns = self.detector.detect_candlestick_patterns(candles)
            trend_patterns = self.detector.detect_trend_patterns(prices)
            
            # 2. Analyze pattern quality and context
            pattern_analysis = self._analyze_patterns(symbol, candlestick_patterns, trend_patterns, candles, prices)
            
            # 3. Get database insights for similar patterns
            database_insights = self._get_database_insights(symbol, pattern_analysis)
            
            # 4. Calculate allocation multipliers
            allocation_multipliers = self._calculate_allocation_multipliers(pattern_analysis, database_insights)
            
            # 5. Store high-quality patterns in database
            await self._store_patterns_to_database(symbol, pattern_analysis)
            
            return {
                'symbol': symbol,
                'detected_patterns': pattern_analysis,
                'database_insights': database_insights,
                'allocation_multipliers': allocation_multipliers,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in pattern analysis for {symbol}: {e}")
            return {
                'symbol': symbol,
                'detected_patterns': {},
                'database_insights': {},
                'allocation_multipliers': {'position_multiplier': 1.0, 'confidence_boost': 0.0},
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def _analyze_patterns(self, symbol: str, candlestick_patterns: Dict, trend_patterns: Dict, 
                         candles: List[Dict], prices: List[float]) -> Dict[str, Any]:
        """Analyze detected patterns for quality and trading potential"""
        analysis = {
            'candlestick_patterns': {},
            'trend_patterns': {},
            'composite_score': 0.0,
            'recommendation': 'neutral',
            'confidence': 0.0
        }
        
        # Analyze candlestick patterns
        for pattern_type, patterns in candlestick_patterns.items():
            if not isinstance(patterns, list):
                logger.warning(f"Pattern type {pattern_type} is not a list: {type(patterns)}")
                continue
                
            for pattern in patterns:
                if not isinstance(pattern, dict):
                    logger.warning(f"Pattern is not a dict: {pattern}")
                    continue
                    
                try:
                    quality_score = self._calculate_pattern_quality(pattern, candles, prices)
                    analysis['candlestick_patterns'][pattern_type] = {
                        'patterns': patterns,
                        'quality_score': quality_score,
                        'trading_implication': self._get_trading_implication(pattern, quality_score)
                    }
                except Exception as e:
                    logger.warning(f"Error analyzing candlestick pattern {pattern_type}: {e}")
                    continue
        
        # Analyze trend patterns
        for pattern_type, patterns in trend_patterns.items():
            if not isinstance(patterns, list):
                logger.warning(f"Trend pattern type {pattern_type} is not a list: {type(patterns)}")
                continue
                
            for pattern in patterns:
                if not isinstance(pattern, dict):
                    logger.warning(f"Trend pattern is not a dict: {pattern}")
                    continue
                    
                try:
                    quality_score = self._calculate_trend_pattern_quality(pattern, prices)
                    analysis['trend_patterns'][pattern_type] = {
                        'patterns': patterns,
                        'quality_score': quality_score,
                        'trading_implication': self._get_trend_trading_implication(pattern, quality_score)
                    }
                except Exception as e:
                    logger.warning(f"Error analyzing trend pattern {pattern_type}: {e}")
                    continue
        
        # Calculate composite score
        analysis['composite_score'] = self._calculate_composite_score(analysis)
        analysis['recommendation'] = self._get_trading_recommendation(analysis['composite_score'])
        analysis['confidence'] = analysis['composite_score']
        
        return analysis
    
    def _calculate_pattern_quality(self, pattern: Dict, candles: List[Dict], prices: List[float]) -> float:
        """Calculate quality score for a detected pattern"""
        base_strength = pattern.get('strength', 0.5)
        
        # Context factors
        context_score = 1.0
        
        # Volume confirmation (if available)
        if 'volume' in pattern.get('candle_data', {}):
            volume = pattern['candle_data']['volume']
            avg_volume = sum(c.get('volume', 0) for c in candles[-20:]) / 20
            if volume > avg_volume * 1.5:
                context_score += 0.2
            elif volume < avg_volume * 0.5:
                context_score -= 0.1
        
        # Trend alignment
        trend_score = self._calculate_trend_alignment(pattern, prices)
        context_score += trend_score
        
        # Pattern timing (recent patterns are more relevant)
        age_factor = max(0.5, 1.0 - (len(candles) - pattern['index']) * 0.05)
        
        quality_score = base_strength * context_score * age_factor
        
        # Clamp to 0-1 range
        return max(0.0, min(1.0, quality_score))
    
    def _calculate_trend_pattern_quality(self, pattern: Dict, prices: List[float]) -> float:
        """Calculate quality score for trend patterns"""
        base_strength = pattern.get('strength', 0.5)
        
        # Pattern-specific quality factors
        if pattern['type'] == 'support':
            # Support level quality based on number of tests
            quality = min(1.0, base_strength * 1.5)
        elif pattern['type'] == 'resistance':
            # Resistance level quality
            quality = min(1.0, base_strength * 1.5)
        elif pattern['type'] == 'triangle':
            # Triangle quality based on convergence
            convergence = pattern.get('convergence', 0.0)
            quality = min(1.0, base_strength + convergence * 0.5)
        else:
            quality = base_strength
        
        return max(0.0, min(1.0, quality))
    
    def _calculate_trend_alignment(self, pattern: Dict, prices: List[float]) -> float:
        """Calculate how well pattern aligns with current trend"""
        if len(prices) < 20:
            return 0.0
        
        # Calculate trend direction (20-period SMA slope)
        sma_20 = sum(prices[-20:]) / 20
        sma_10 = sum(prices[-10:]) / 10
        
        if sma_10 > sma_20:  # Uptrend
            trend_direction = 1.0
        elif sma_10 < sma_20:  # Downtrend
            trend_direction = -1.0
        else:
            trend_direction = 0.0
        
        # Pattern direction
        pattern_direction = 1.0 if pattern.get('direction', '').lower() == 'bullish' else -1.0
        
        # Alignment score (1.0 if aligned, -0.5 if against trend)
        if trend_direction * pattern_direction > 0:
            return 0.3  # Positive alignment
        elif trend_direction * pattern_direction < 0:
            return -0.2  # Against trend
        else:
            return 0.0  # Neutral
    
    def _get_trading_implication(self, pattern: Dict, quality_score: float) -> str:
        """Get trading implication for pattern"""
        if quality_score > 0.8:
            return "strong_buy" if pattern.get('direction') == 'bullish' else "strong_sell"
        elif quality_score > 0.6:
            return "moderate_buy" if pattern.get('direction') == 'bullish' else "moderate_sell"
        elif quality_score > 0.4:
            return "weak_buy" if pattern.get('direction') == 'bullish' else "weak_sell"
        else:
            return "neutral"
    
    def _get_trend_trading_implication(self, pattern: Dict, quality_score: float) -> str:
        """Get trading implication for trend patterns"""
        pattern_type = pattern.get('type', '')
        
        if pattern_type == 'support' and quality_score > 0.6:
            return "buy_near_support"
        elif pattern_type == 'resistance' and quality_score > 0.6:
            return "sell_near_resistance"
        elif pattern_type == 'triangle' and quality_score > 0.6:
            return "breakout_trade"
        else:
            return "monitor"
    
    def _calculate_composite_score(self, analysis: Dict) -> float:
        """Calculate composite pattern score"""
        scores = []
        
        # Candlestick pattern scores
        for pattern_data in analysis['candlestick_patterns'].values():
            scores.append(pattern_data['quality_score'] * 0.7)  # Weight 0.7
        
        # Trend pattern scores
        for pattern_data in analysis['trend_patterns'].values():
            scores.append(pattern_data['quality_score'] * 0.3)  # Weight 0.3
        
        if not scores:
            return 0.0
        
        return sum(scores) / len(scores)
    
    def _get_trading_recommendation(self, composite_score: float) -> str:
        """Get trading recommendation based on composite score"""
        if composite_score > 0.8:
            return "strong_buy" if composite_score > 0.9 else "buy"
        elif composite_score > 0.6:
            return "weak_buy"
        elif composite_score > 0.4:
            return "hold"
        elif composite_score > 0.2:
            return "weak_sell"
        else:
            return "sell"
    
    def _get_database_insights(self, symbol: str, pattern_analysis: Dict) -> Dict[str, Any]:
        """Get insights from pattern database for similar patterns"""
        try:
            # Get current market context
            current_context = self._get_current_context(symbol)
            
            insights = {}
            
            # Analyze candlestick patterns
            for pattern_type, pattern_data in pattern_analysis['candlestick_patterns'].items():
                if pattern_data['quality_score'] > 0.5:  # Only high-quality patterns
                    similar_examples = self.pattern_db.get_similar_examples(
                        pattern_type, current_context, limit=3
                    )
                    
                    if similar_examples:
                        avg_profit = sum(ex.get('profit_pct', 0) for ex in similar_examples) / len(similar_examples)
                        success_rate = sum(1 for ex in similar_examples if ex.get('result') == 'SUCCESS') / len(similar_examples)
                        
                        insights[pattern_type] = {
                            'similar_examples_count': len(similar_examples),
                            'avg_profit': avg_profit,
                            'success_rate': success_rate,
                            'recommendation': f"Similar {pattern_type} patterns averaged +{avg_profit:.1f}% profit"
                        }
            
            return insights
            
        except Exception as e:
            logger.error(f"Error getting database insights for {symbol}: {e}")
            return {}
    
    def _calculate_allocation_multipliers(self, pattern_analysis: Dict, database_insights: Dict) -> Dict[str, float]:
        """Calculate allocation multipliers based on pattern analysis"""
        base_multiplier = 1.0
        confidence_boost = 0.0
        
        composite_score = pattern_analysis.get('composite_score', 0.0)
        
        # Pattern quality-based allocation
        if composite_score > 0.8:
            base_multiplier = 2.0      # Excellent patterns get 2x allocation
            confidence_boost = 0.25    # 25% confidence boost
        elif composite_score > 0.6:
            base_multiplier = 1.5      # Good patterns get 1.5x allocation
            confidence_boost = 0.15    # 15% confidence boost
        elif composite_score > 0.4:
            base_multiplier = 1.0      # Average patterns get baseline
            confidence_boost = 0.05    # 5% confidence boost
        elif composite_score > 0.2:
            base_multiplier = 0.7      # Poor patterns get reduced allocation
            confidence_boost = -0.05   # Slight confidence reduction
        else:
            base_multiplier = 0.5      # Very poor patterns get minimal allocation
            confidence_boost = -0.15   # Significant confidence reduction
        
        # Database insights adjustment
        for pattern_type, insight in database_insights.items():
            success_rate = insight.get('success_rate', 0.5)
            avg_profit = insight.get('avg_profit', 0.0)
            
            # Adjust based on historical success
            if success_rate > 0.7 and avg_profit > 2.0:
                base_multiplier *= 1.2
                confidence_boost += 0.1
            elif success_rate < 0.4:
                base_multiplier *= 0.8
                confidence_boost -= 0.05
        
        # Clamp multipliers
        base_multiplier = max(0.3, min(3.0, base_multiplier))
        confidence_boost = max(-0.3, min(0.4, confidence_boost))
        
        return {
            'position_multiplier': base_multiplier,
            'confidence_boost': confidence_boost,
            'composite_score': composite_score,
            'pattern_count': len(pattern_analysis.get('candlestick_patterns', {})) + 
                           len(pattern_analysis.get('trend_patterns', {}))
        }
    
    async def _store_patterns_to_database(self, symbol: str, pattern_analysis: Dict):
        """Store high-quality patterns to database for future reference"""
        try:
            for pattern_type, pattern_data in pattern_analysis['candlestick_patterns'].items():
                if pattern_data['quality_score'] > 0.6:  # Only store high-quality patterns
                    for pattern in pattern_data['patterns']:
                        # Convert pattern to database format
                        pattern_example = self._convert_pattern_to_database_format(
                            symbol, pattern_type, pattern, pattern_data['quality_score']
                        )
                        
                        # Add to database (will be updated with actual results later)
                        self.pattern_db.add_successful_example(pattern_type, pattern_example)
            
            logger.info(f"Stored patterns for {symbol} in database")
            
        except Exception as e:
            logger.error(f"Error storing patterns to database for {symbol}: {e}")
    
    def _convert_pattern_to_database_format(self, symbol: str, pattern_type: str, 
                                           pattern: Dict, quality_score: float) -> Dict:
        """Convert detected pattern to database format"""
        return {
            # Pattern Characteristics
            "pattern_type": pattern_type,
            "formation_quality": quality_score,
            "duration_bars": 3,  # Simplified
            "volume_pattern": "unknown",  # Would need volume analysis
            
            # Market Context
            "market_trend": "unknown",  # Would need trend analysis
            "volatility": 0.02,  # Would calculate from data
            "volume_confirmation": 1.0,  # Would calculate from volume
            "time_of_day": "unknown",  # Would extract from timestamp
            
            # Trade Execution (placeholder - will be updated after trade)
            "entry_price": pattern.get('candle_data', {}).get('close', 0),
            "entry_timing": "immediate",
            "entry_confidence": quality_score,
            "position_size": 1.0,  # Will be multiplier
            
            # Risk Management (placeholder)
            "stop_loss": 0.0,
            "take_profit": 0.0,
            "risk_reward": 2.0,
            
            # Outcome & Learning (placeholder - will be updated after trade)
            "result": "pending",
            "profit_pct": 0.0,
            "time_to_target": 0,
            "confirmation_signals": [],
            "key_insights": f"Detected {pattern_type} pattern with quality {quality_score:.2f}",
            
            # Timing Optimization (placeholder)
            "optimal_entry_time": "unknown",
            "optimal_exit_time": "unknown",
            "market_session": "unknown",
            
            # Pattern Quality Metrics (simplified)
            "shoulder_symmetry": 0.0,
            "neckline_quality": 0.0,
            "head_prominence": 0.0,
            
            # Metadata
            "timestamp": pattern.get('timestamp', ''),
            "symbol": symbol,
            "timeframe": "15m",
            "quality_score": quality_score
        }
    
    def _get_current_context(self, symbol: str) -> Dict[str, Any]:
        """Get current market context for symbol"""
        # This would integrate with your existing market data collection
        # For now, return a basic context
        return {
            "market_trend": "unknown",
            "volatility": 0.02,
            "volume_confirmation": 1.0,
            "time_of_day": datetime.now().strftime("%H:%M"),
            "symbol": symbol,
            "timeframe": "15m"
        }
    
    def integrate_with_risk_manager(self, symbol: str, base_risk_params: Dict, 
                                   pattern_analysis: Dict) -> Dict:
        """Integrate pattern analysis with existing risk management"""
        try:
            # Get allocation multipliers from pattern analysis
            allocation_multipliers = pattern_analysis.get('allocation_multipliers', {})
            
            position_multiplier = allocation_multipliers.get('position_multiplier', 1.0)
            confidence_boost = allocation_multipliers.get('confidence_boost', 0.0)
            
            # Apply pattern-based adjustments to base risk parameters
            adjusted_params = base_risk_params.copy()
            
            # Adjust position size based on pattern quality
            if 'position_size' in adjusted_params:
                adjusted_params['position_size'] *= position_multiplier
            
            # Adjust confidence based on pattern quality
            if 'confidence' in adjusted_params:
                adjusted_params['confidence'] = min(1.0, adjusted_params['confidence'] + confidence_boost)
            
            # Adjust risk parameters based on pattern quality
            if composite_score := allocation_multipliers.get('composite_score', 0.0):
                if composite_score > 0.8:  # Excellent patterns
                    adjusted_params['risk_tolerance'] *= 1.2  # Slightly higher risk tolerance
                elif composite_score < 0.4:  # Poor patterns
                    adjusted_params['risk_tolerance'] *= 0.8  # More conservative
            
            return {
                'original_params': base_risk_params,
                'adjusted_params': adjusted_params,
                'pattern_multiplier': position_multiplier,
                'confidence_adjustment': confidence_boost,
                'pattern_quality': allocation_multipliers.get('composite_score', 0.0)
            }
            
        except Exception as e:
            logger.error(f"Error integrating patterns with risk manager for {symbol}: {e}")
            return {
                'original_params': base_risk_params,
                'adjusted_params': base_risk_params,
                'pattern_multiplier': 1.0,
                'confidence_adjustment': 0.0,
                'pattern_quality': 0.0,
                'error': str(e)
            }


# Create singleton instance
pattern_integration = PatternIntegration()


def get_pattern_integration(data_dir: Optional[str] = None) -> PatternIntegration:
    """Get the global pattern integration instance"""
    global pattern_integration
    if data_dir:
        pattern_integration = PatternIntegration(data_dir)
    return pattern_integration