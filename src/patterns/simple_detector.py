"""
Simple Pattern Detection System
Uses basic mathematical calculations for pattern recognition without complex dependencies
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)


class SimplePatternDetector:
    """Simple pattern detection using basic mathematical calculations"""
    
    def __init__(self):
        """Initialize the simple pattern detector"""
        self.pattern_thresholds = {
            'hammer': {'wick_ratio': 2.0, 'body_ratio': 0.3},
            'engulfing': {'body_ratio': 1.2},
            'star_patterns': {'gap_ratio': 0.005},
            'support_resistance': {'strength_threshold': 0.3},
            'triangles': {'convergence_threshold': 0.1}
        }
        
        logger.info("Simple Pattern Detector initialized")
    
    def detect_candlestick_patterns(self, candles: List[Dict]) -> Dict[str, List[Dict]]:
        """Detect basic candlestick patterns using simple math"""
        if len(candles) < 3:
            return {}
        
        patterns = {}
        
        # Detect individual candlestick patterns
        patterns['hammer'] = self._detect_hammer(candles)
        patterns['engulfing'] = self._detect_engulfing(candles)
        patterns['star_patterns'] = self._detect_star_patterns(candles)
        
        # Filter out empty pattern lists
        patterns = {k: v for k, v in patterns.items() if v}
        
        return patterns
    
    def _detect_hammer(self, candles: List[Dict]) -> List[Dict]:
        """Detect hammer patterns"""
        hammers = []
        
        for i in range(1, len(candles) - 1):
            candle = candles[i]
            
            try:
                # Calculate candle characteristics
                body_size = abs(candle['close'] - candle['open'])
                total_range = candle['high'] - candle['low']
                
                if total_range == 0:
                    continue
                
                upper_wick = max(candle['open'], candle['close']) - candle['high']
                lower_wick = candle['low'] - min(candle['open'], candle['close'])
                
                # Hammer criteria: small body, long lower wick, small upper wick
                body_ratio = body_size / total_range
                lower_wick_ratio = abs(lower_wick) / total_range
                upper_wick_ratio = abs(upper_wick) / total_range
                
                if (body_ratio < 0.3 and  # Small body (less than 30% of total range)
                    lower_wick_ratio > 0.6 and  # Long lower wick (more than 60% of total range)
                    upper_wick_ratio < 0.1):  # Small upper wick (less than 10% of total range)
                    
                    hammers.append({
                        'index': i,
                        'type': 'hammer',
                        'direction': 'bullish' if candle['close'] > candle['open'] else 'bearish',
                        'strength': lower_wick_ratio,
                        'timestamp': candle.get('timestamp', ''),
                        'candle_data': {
                            'open': candle['open'],
                            'high': candle['high'],
                            'low': candle['low'],
                            'close': candle['close'],
                            'volume': candle.get('volume', 0)
                        }
                    })
            except Exception as e:
                logger.warning(f"Error detecting hammer at index {i}: {e}")
                continue
        
        return hammers
    
    def _detect_engulfing(self, candles: List[Dict]) -> List[Dict]:
        """Detect engulfing patterns"""
        engulfing = []
        
        for i in range(1, len(candles)):
            try:
                prev_candle = candles[i-1]
                curr_candle = candles[i]
                
                # Bullish Engulfing: previous bearish candle engulfed by current bullish candle
                if (prev_candle['close'] < prev_candle['open'] and  # Previous bearish
                    curr_candle['close'] > curr_candle['open'] and  # Current bullish
                    curr_candle['open'] <= prev_candle['close'] and  # Current opens at or below previous close
                    curr_candle['close'] >= prev_candle['open']):   # Current closes at or above previous open
                    
                    strength = (curr_candle['close'] - curr_candle['open']) / (prev_candle['open'] - prev_candle['close'])
                    
                    engulfing.append({
                        'index': i,
                        'type': 'bullish_engulfing',
                        'strength': strength,
                        'timestamp': curr_candle.get('timestamp', ''),
                        'candle_data': {
                            'prev_open': prev_candle['open'],
                            'prev_close': prev_candle['close'],
                            'curr_open': curr_candle['open'],
                            'curr_close': curr_candle['close'],
                            'volume': curr_candle.get('volume', 0)
                        }
                    })
                
                # Bearish Engulfing: previous bullish candle engulfed by current bearish candle
                elif (prev_candle['close'] > prev_candle['open'] and  # Previous bullish
                      curr_candle['close'] < curr_candle['open'] and  # Current bearish
                      curr_candle['open'] >= prev_candle['close'] and  # Current opens at or above previous close
                      curr_candle['close'] <= prev_candle['open']):   # Current closes at or below previous open
                    
                    strength = (curr_candle['open'] - curr_candle['close']) / (prev_candle['close'] - prev_candle['open'])
                    
                    engulfing.append({
                        'index': i,
                        'type': 'bearish_engulfing',
                        'strength': strength,
                        'timestamp': curr_candle.get('timestamp', ''),
                        'candle_data': {
                            'prev_open': prev_candle['open'],
                            'prev_close': prev_candle['close'],
                            'curr_open': curr_candle['open'],
                            'curr_close': curr_candle['close'],
                            'volume': curr_candle.get('volume', 0)
                        }
                    })
            except Exception as e:
                logger.warning(f"Error detecting engulfing at index {i}: {e}")
                continue
        
        return engulfing
    
    def _detect_star_patterns(self, candles: List[Dict]) -> List[Dict]:
        """Detect morning star and evening star patterns"""
        stars = []
        
        for i in range(2, len(candles)):
            try:
                first = candles[i-2]
                second = candles[i-1]
                third = candles[i]
                
                # Morning Star Pattern
                # 1. Long bearish candle
                # 2. Small body candle (star) with gap down
                # 3. Long bullish candle closing above midpoint of first candle
                
                first_body = abs(first['close'] - first['open'])
                second_body = abs(second['close'] - second['open'])
                third_body = abs(third['close'] - third['open'])
                
                # Check if first candle is long bearish
                if (first['close'] < first['open'] and 
                    first_body > (first['high'] - first['low']) * 0.6):
                    
                    # Check if second candle is small (star) with gap down
                    if (second_body < (second['high'] - second['low']) * 0.3 and
                        second['high'] < first['low']):  # Gap down
                        
                        # Check if third candle is long bullish closing above midpoint
                        if (third['close'] > third['open'] and
                            third_body > (third['high'] - third['low']) * 0.6 and
                            third['close'] > (first['open'] + first['close']) / 2):
                            
                            strength = (third['close'] - third['open']) / first_body
                            
                            stars.append({
                                'index': i,
                                'type': 'morning_star',
                                'strength': strength,
                                'timestamp': third.get('timestamp', ''),
                                'candle_data': {
                                    'first': first,
                                    'second': second,
                                    'third': third
                                }
                            })
                
                # Evening Star Pattern
                # 1. Long bullish candle
                # 2. Small body candle (star) with gap up
                # 3. Long bearish candle closing below midpoint of first candle
                
                elif (first['close'] > first['open'] and 
                      first_body > (first['high'] - first['low']) * 0.6):
                    
                    if (second_body < (second['high'] - second['low']) * 0.3 and
                        second['low'] > first['high']):  # Gap up
                        
                        if (third['close'] < third['open'] and
                            third_body > (third['high'] - third['low']) * 0.6 and
                            third['close'] < (first['open'] + first['close']) / 2):
                            
                            strength = (third['open'] - third['close']) / first_body
                            
                            stars.append({
                                'index': i,
                                'type': 'evening_star',
                                'strength': strength,
                                'timestamp': third.get('timestamp', ''),
                                'candle_data': {
                                    'first': first,
                                    'second': second,
                                    'third': third
                                }
                            })
            except Exception as e:
                logger.warning(f"Error detecting star patterns at index {i}: {e}")
                continue
        
        return stars
    
    def detect_trend_patterns(self, prices: List[float], volumes: Optional[List[float]] = None) -> Dict[str, List[Dict]]:
        """Detect simple trend-based patterns"""
        if len(prices) < 10:
            return {}
        
        patterns = {}
        
        # Support/Resistance Detection
        patterns['support_resistance'] = self._detect_support_resistance(prices)
        
        # Triangle Detection
        patterns['triangles'] = self._detect_triangles(prices)
        
        # Moving Average Crossovers
        patterns['ma_crossovers'] = self._detect_ma_crossovers(prices)
        
        # Filter out empty pattern lists
        patterns = {k: v for k, v in patterns.items() if v}
        
        return patterns
    
    def _detect_support_resistance(self, prices: List[float]) -> List[Dict]:
        """Detect support and resistance levels"""
        levels = []
        
        # Find local minima (support) and maxima (resistance)
        for i in range(3, len(prices) - 3):
            price = prices[i]
            
            # Check if local minimum (support)
            if (price <= prices[i-1] and price <= prices[i-2] and price <= prices[i-3] and
                price <= prices[i+1] and price <= prices[i+2] and price <= prices[i+3]):
                
                strength = self._calculate_level_strength(prices, i, 'support')
                if strength > 0.3:  # Only strong levels
                    levels.append({
                        'type': 'support',
                        'price': price,
                        'index': i,
                        'strength': strength,
                        'timestamp': i  # Would be actual timestamp
                    })
            
            # Check if local maximum (resistance)
            elif (price >= prices[i-1] and price >= prices[i-2] and price >= prices[i-3] and
                  price >= prices[i+1] and price >= prices[i+2] and price >= prices[i+3]):
                
                strength = self._calculate_level_strength(prices, i, 'resistance')
                if strength > 0.3:  # Only strong levels
                    levels.append({
                        'type': 'resistance',
                        'price': price,
                        'index': i,
                        'strength': strength,
                        'timestamp': i  # Would be actual timestamp
                    })
        
        return levels
    
    def _detect_triangles(self, prices: List[float]) -> List[Dict]:
        """Detect simple triangle patterns"""
        triangles = []
        
        # Look for converging trendlines in rolling windows
        window_size = 20
        for i in range(window_size, len(prices)):
            window = prices[i-window_size:i]
            
            # Calculate upper and lower trendlines
            upper_trend = self._fit_upper_trendline(window)
            lower_trend = self._fit_lower_trendline(window)
            
            # Check for convergence (triangle formation)
            if self._is_converging(upper_trend, lower_trend):
                convergence = self._calculate_convergence(upper_trend, lower_trend)
                
                triangles.append({
                    'index': i,
                    'type': 'triangle',
                    'direction': 'bullish' if upper_trend['slope'] < 0 and lower_trend['slope'] > 0 else 'bearish',
                    'convergence': convergence,
                    'timestamp': i,
                    'trendlines': {
                        'upper': upper_trend,
                        'lower': lower_trend
                    }
                })
        
        return triangles
    
    def _detect_ma_crossovers(self, prices: List[float]) -> List[Dict]:
        """Detect moving average crossovers"""
        crossovers = []
        
        if len(prices) < 20:
            return crossovers
        
        # Calculate simple moving averages
        ma_short = self._calculate_sma(prices, 10)
        ma_long = self._calculate_sma(prices, 20)
        
        for i in range(1, len(ma_short)):
            try:
                # Bullish crossover: short MA crosses above long MA
                if (ma_short[i-1] <= ma_long[i-1] and 
                    ma_short[i] > ma_long[i]):
                    
                    crossovers.append({
                        'index': i,
                        'type': 'bullish_crossover',
                        'strength': (ma_short[i] - ma_long[i]) / ma_long[i],
                        'timestamp': i
                    })
                
                # Bearish crossover: short MA crosses below long MA
                elif (ma_short[i-1] >= ma_long[i-1] and 
                      ma_short[i] < ma_long[i]):
                    
                    crossovers.append({
                        'index': i,
                        'type': 'bearish_crossover',
                        'strength': (ma_long[i] - ma_short[i]) / ma_long[i],
                        'timestamp': i
                    })
            except Exception as e:
                logger.warning(f"Error detecting MA crossover at index {i}: {e}")
                continue
        
        return crossovers
    
    def _calculate_level_strength(self, prices: List[float], index: int, level_type: str) -> float:
        """Calculate strength of support/resistance level"""
        price = prices[index]
        tests = 0
        
        # Count how many times price came close to this level
        for i, p in enumerate(prices):
            if i != index and abs(p - price) / price < 0.01:  # Within 1%
                tests += 1
        
        # Normalize strength (0.0 to 1.0)
        return min(tests / 5.0, 1.0)
    
    def _fit_upper_trendline(self, prices: List[float]) -> Dict:
        """Fit upper trendline using simple linear regression"""
        n = len(prices)
        x = list(range(n))
        
        # Find highest points for upper trendline
        high_points = []
        for i in range(1, n-1):
            if prices[i] >= prices[i-1] and prices[i] >= prices[i+1]:
                high_points.append((i, prices[i]))
        
        if len(high_points) < 2:
            # Fallback to simple linear regression on all points
            high_points = [(i, p) for i, p in enumerate(prices)]
        
        # Simple linear regression
        sum_x = sum(point[0] for point in high_points)
        sum_y = sum(point[1] for point in high_points)
        sum_xy = sum(point[0] * point[1] for point in high_points)
        sum_x2 = sum(point[0]**2 for point in high_points)
        n_points = len(high_points)
        
        if n_points * sum_x2 - sum_x**2 == 0:
            return {'slope': 0.0, 'intercept': sum_y / n_points}
        
        slope = (n_points * sum_xy - sum_x * sum_y) / (n_points * sum_x2 - sum_x**2)
        intercept = (sum_y - slope * sum_x) / n_points
        
        return {'slope': slope, 'intercept': intercept}
    
    def _fit_lower_trendline(self, prices: List[float]) -> Dict:
        """Fit lower trendline using simple linear regression"""
        n = len(prices)
        x = list(range(n))
        
        # Find lowest points for lower trendline
        low_points = []
        for i in range(1, n-1):
            if prices[i] <= prices[i-1] and prices[i] <= prices[i+1]:
                low_points.append((i, prices[i]))
        
        if len(low_points) < 2:
            # Fallback to simple linear regression on all points
            low_points = [(i, p) for i, p in enumerate(prices)]
        
        # Simple linear regression
        sum_x = sum(point[0] for point in low_points)
        sum_y = sum(point[1] for point in low_points)
        sum_xy = sum(point[0] * point[1] for point in low_points)
        sum_x2 = sum(point[0]**2 for point in low_points)
        n_points = len(low_points)
        
        if n_points * sum_x2 - sum_x**2 == 0:
            return {'slope': 0.0, 'intercept': sum_y / n_points}
        
        slope = (n_points * sum_xy - sum_x * sum_y) / (n_points * sum_x2 - sum_x**2)
        intercept = (sum_y - slope * sum_x) / n_points
        
        return {'slope': slope, 'intercept': intercept}
    
    def _is_converging(self, upper: Dict, lower: Dict) -> bool:
        """Check if trendlines are converging"""
        # Converging if slopes have opposite signs and are not too flat
        upper_slope = abs(upper['slope'])
        lower_slope = abs(lower['slope'])
        
        return (upper_slope > 0.001 and lower_slope > 0.001 and 
                upper['slope'] * lower['slope'] < 0)  # Opposite signs
    
    def _calculate_convergence(self, upper: Dict, lower: Dict) -> float:
        """Calculate convergence strength"""
        upper_slope = abs(upper['slope'])
        lower_slope = abs(lower['slope'])
        
        # Convergence strength based on slope magnitudes
        return min((upper_slope + lower_slope) * 100, 1.0)
    
    def _calculate_sma(self, prices: List[float], period: int) -> List[float]:
        """Calculate simple moving average"""
        if len(prices) < period:
            return []
        
        sma = []
        for i in range(period - 1, len(prices)):
            window = prices[i - period + 1:i + 1]
            sma.append(sum(window) / period)
        
        return sma
