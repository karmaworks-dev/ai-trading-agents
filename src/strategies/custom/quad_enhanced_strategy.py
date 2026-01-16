"""
🕉️ Karma's Quad Rotation Strategy
Based on Quadzilla Lite - Multi-Stochastic Rotation System

This strategy uses 4 stochastic oscillators with different periods to identify
high-probability trading opportunities through "rotation" - when multiple stochastics
agree on direction.

Key Features:
- 4 Stochastics: Fast (9), Medium (14, 40), Slow (60)
- Weighted Average: Combines all 4 with emphasis on slower stochs
- Super Signals: All 4 stochs in extreme zones (>90 or <10)
- Trend Shield: ABCD pattern to avoid counter-trend trades
- Minimum Agreement: Requires 3/4 stochs to agree before entry

Signal Strength:
- 1.0: SUPER signal (all 4 stochs in extreme agreement)
- 0.7-1.0: Regular signal (3/4 stochs agree, scales with agreement)

To keep this strategy private, rename file with prefix:
- private_quad_rotation_strategy.py
- secret_quad_rotation_strategy.py
- dev_quad_rotation_strategy.py
"""
from ..base_strategy import BaseStrategy
from src.config import MONITORED_TOKENS
import pandas as pd
import numpy as np
from termcolor import cprint
from src import nice_funcs as n


class QuadRotationStrategy(BaseStrategy):
    def __init__(self):
        """Initialize the Quad Rotation Strategy"""
        super().__init__("Quad Rotation")
        
        # Quad Stochastic Settings (from Quadzilla Lite)
        self.stoch_configs = {
            'stoch1': {'k': 9, 'd': 3, 'smooth': 1, 'weight': 0.2},   # Fastest
            'stoch2': {'k': 14, 'd': 3, 'smooth': 1, 'weight': 0.6},
            'stoch3': {'k': 40, 'd': 4, 'smooth': 1, 'weight': 1.4},
            'stoch4': {'k': 60, 'd': 10, 'smooth': 1, 'weight': 1.8}  # Slowest
        }
        
        # Signal thresholds
        self.overbought = 80
        self.oversold = 20
        self.extreme_overbought = 90
        self.extreme_oversold = 10
        self.midline = 50
        
        # Signal requirements
        self.min_stoch_agreement = 3  # At least 3 of 4 stochs must agree
        self.use_super_signal = True  # Require all 4 stochs in extreme for strongest signal
        self.use_trend_shield = True  # Avoid counter-trend trades
        
        # Trend Shield (ABCD Pattern) settings
        self.abcd_bars_90 = 7  # Bars stoch4 must stay >90 for bullish shield
        self.abcd_bars_10 = 7  # Bars stoch4 must stay <10 for bearish shield
        
        # Multi-Timeframe Settings
        self.timeframes = ['15m', '1h', '4h']
        self.tf_weights = {'15m': 0.5, '1h': 1.0, '4h': 1.5}  # Higher weight for higher timeframes
        
        cprint(f"🕉️ Karma's Quad Rotation Strategy initialized with {len(self.timeframes)} timeframes", "cyan")
    
    def calculate_stochastic(self, data: pd.DataFrame, k_period: int, d_period: int, smooth: int = 1) -> tuple:
        """Calculate Stochastic oscillator"""
        # Calculate %K
        low_min = data['low'].rolling(window=k_period).min()
        high_max = data['high'].rolling(window=k_period).max()

        # Guard against division by zero (flat market scenario)
        denominator = high_max - low_min
        denominator = denominator.replace(0, float('nan'))  # Replace 0 with NaN to avoid div/0

        stoch_k = 100 * (data['close'] - low_min) / denominator
        stoch_k = stoch_k.fillna(50)  # Default to 50 (neutral) for flat periods

        # Apply smoothing
        if smooth > 1:
            stoch_k = stoch_k.rolling(window=smooth).mean()

        # Calculate %D (moving average of %K)
        stoch_d = stoch_k.rolling(window=d_period).mean()

        return stoch_k, stoch_d
    
    def calculate_weighted_average(self, stoch_values: dict) -> pd.Series:
        """Calculate weighted average of all stochastics"""
        total_weight = sum(config['weight'] for config in self.stoch_configs.values())
        
        weighted_sum = pd.Series(0, index=stoch_values['stoch1'].index)
        for name, config in self.stoch_configs.items():
            # Center around 50, apply weight, then shift back
            centered = (stoch_values[name] - 50) * config['weight'] + 50
            weighted_sum += centered
        
        return weighted_sum / len(self.stoch_configs)
    
    def count_stochs_sloping_down_above(self, stoch_values: dict, level: float) -> int:
        """Count how many stochs are above level AND sloping down"""
        count = 0
        for name, stoch_d in stoch_values.items():
            if len(stoch_d) < 2:
                continue
            current = stoch_d.iloc[-1]
            previous = stoch_d.iloc[-2]
            if not pd.isna(current) and not pd.isna(previous):
                if current > level and current < previous:  # Above level and sloping down
                    count += 1
        return count
    
    def count_stochs_sloping_up_below(self, stoch_values: dict, level: float) -> int:
        """Count how many stochs are below level AND sloping up"""
        count = 0
        for name, stoch_d in stoch_values.items():
            if len(stoch_d) < 2:
                continue
            current = stoch_d.iloc[-1]
            previous = stoch_d.iloc[-2]
            if not pd.isna(current) and not pd.isna(previous):
                if current < level and current > previous:  # Below level and sloping up
                    count += 1
        return count
    
    def check_super_signal_down(self, stoch_values: dict) -> bool:
        """Check if ALL 4 stochs are above extreme overbought and sloping down"""
        if not self.use_super_signal:
            return False
        
        for name, stoch_d in stoch_values.items():
            if len(stoch_d) < 2:
                return False
            current = stoch_d.iloc[-1]
            previous = stoch_d.iloc[-2]
            if pd.isna(current) or pd.isna(previous):
                return False
            if current <= self.extreme_overbought or current >= previous:
                return False
        return True
    
    def check_super_signal_up(self, stoch_values: dict) -> bool:
        """Check if ALL 4 stochs are below extreme oversold and sloping up"""
        if not self.use_super_signal:
            return False
        
        for name, stoch_d in stoch_values.items():
            if len(stoch_d) < 2:
                return False
            current = stoch_d.iloc[-1]
            previous = stoch_d.iloc[-2]
            if pd.isna(current) or pd.isna(previous):
                return False
            if current >= self.extreme_oversold or current <= previous:
                return False
        return True
    
    def check_trend_shield_bullish(self, stoch4_d: pd.Series) -> bool:
        """Trend Shield: Stoch4 has been >90 for X bars (strong uptrend continuation)"""
        if not self.use_trend_shield or len(stoch4_d) < self.abcd_bars_90:
            return False
        
        # Check if stoch4 has been >90 for last X bars
        recent_bars = stoch4_d.iloc[-self.abcd_bars_90:]
        return all(val > self.extreme_overbought for val in recent_bars if not pd.isna(val))
    
    def check_trend_shield_bearish(self, stoch4_d: pd.Series) -> bool:
        """Trend Shield: Stoch4 has been <10 for X bars (strong downtrend continuation)"""
        if not self.use_trend_shield or len(stoch4_d) < self.abcd_bars_10:
            return False
        
        # Check if stoch4 has been <10 for last X bars
        recent_bars = stoch4_d.iloc[-self.abcd_bars_10:]
        return all(val < self.extreme_oversold for val in recent_bars if not pd.isna(val))
    
    def analyze_timeframe(self, token: str, timeframe: str) -> dict:
        """Analyze a single timeframe for signals"""
        # Get market data (need more history for higher timeframes)
        days_back = 5 if timeframe == '15m' else 14 if timeframe == '1h' else 30
        data = n.get_data(token, days_back=days_back, timeframe=timeframe)
        
        if data is None or data.empty:
            return None
            
        # Ensure we have required columns
        if not all(col in data.columns for col in ['open', 'high', 'low', 'close']):
            return None
            
        # Calculate all 4 stochastics
        stoch_d_values = {}
        stoch_k_values = {}
        
        for name, config in self.stoch_configs.items():
            stoch_k, stoch_d = self.calculate_stochastic(
                data,
                k_period=config['k'],
                d_period=config['d'],
                smooth=config['smooth']
            )
            stoch_k_values[name] = stoch_k
            stoch_d_values[name] = stoch_d
        
        # Calculate weighted average
        stoch_avg = self.calculate_weighted_average(stoch_d_values)
        
        # Get current values
        stoch1_current = stoch_d_values['stoch1'].iloc[-1]
        stoch1_previous = stoch_d_values['stoch1'].iloc[-2]
        stoch_avg_current = stoch_avg.iloc[-1]
        current_price = float(data['close'].iloc[-1])
        
        # Count agreements
        bullish_count = self.count_stochs_sloping_up_below(stoch_d_values, self.oversold)
        bearish_count = self.count_stochs_sloping_down_above(stoch_d_values, self.overbought)
        
        # Check super signals
        super_signal_up = self.check_super_signal_up(stoch_d_values)
        super_signal_down = self.check_super_signal_down(stoch_d_values)
        
        # Check trend shields
        trend_shield_bullish = self.check_trend_shield_bullish(stoch_d_values['stoch4'])
        trend_shield_bearish = self.check_trend_shield_bearish(stoch_d_values['stoch4'])
        
        return {
            'stoch1_current': stoch1_current,
            'stoch1_previous': stoch1_previous,
            'stoch_avg_current': stoch_avg_current,
            'bullish_count': bullish_count,
            'bearish_count': bearish_count,
            'super_signal_up': super_signal_up,
            'super_signal_down': super_signal_down,
            'trend_shield_bullish': trend_shield_bullish,
            'trend_shield_bearish': trend_shield_bearish,
            'current_price': current_price
        }

    def generate_signals(self) -> dict:
        """Generate trading signals based on Multi-Timeframe Quad Rotation"""
        try:
            for token in MONITORED_TOKENS:
                tf_results = {}
                for tf in self.timeframes:
                    result = self.analyze_timeframe(token, tf)
                    if result:
                        tf_results[tf] = result
                
                if not tf_results:
                    continue
                
                # Base signal from 15m (trigger timeframe)
                trigger_tf = '15m'
                if trigger_tf not in tf_results:
                    continue
                    
                trigger_data = tf_results[trigger_tf]
                
                # Aggregate multi-timeframe confirmation
                total_bullish_weight = 0
                total_bearish_weight = 0
                max_possible_weight = sum(self.tf_weights.values())
                
                for tf, data in tf_results.items():
                    weight = self.tf_weights[tf]
                    if data['bullish_count'] >= self.min_stoch_agreement or data['super_signal_up']:
                        total_bullish_weight += weight
                    if data['bearish_count'] >= self.min_stoch_agreement or data['super_signal_down']:
                        total_bearish_weight += weight

                # Initialize signal
                signal = {
                    'token': token,
                    'signal': 0,
                    'direction': 'NEUTRAL',
                    'metadata': {
                        'strategy_type': 'quad_rotation_mtf',
                        'timeframes_analyzed': list(tf_results.keys()),
                        'trigger_indicators': {
                            'stoch1': float(trigger_data['stoch1_current']),
                            'stoch_avg': float(trigger_data['stoch_avg_current']),
                            'bullish_count': trigger_data['bullish_count'],
                            'bearish_count': trigger_data['bearish_count']
                        },
                        'mtf_confidence': {
                            'bullish_weight': total_bullish_weight / max_possible_weight,
                            'bearish_weight': total_bearish_weight / max_possible_weight
                        }
                    }
                }
                
                # BULLISH SIGNAL LOGIC
                bullish_trigger = (trigger_data['stoch1_previous'] <= self.oversold and
                                  trigger_data['stoch1_current'] > self.oversold and
                                  trigger_data['stoch1_current'] > trigger_data['stoch_avg_current'])
                
                # Bullish Shield Check across timeframes (at least higher TFs should not be extreme bearish)
                shield_allows_long = not any(tf_results[tf]['trend_shield_bearish'] for tf in tf_results if tf != '15m')
                
                if bullish_trigger and total_bullish_weight > 0 and shield_allows_long:
                    # Signal strength weighted by MTF agreement
                    signal_strength = (total_bullish_weight / max_possible_weight)
                    signal.update({
                        'signal': signal_strength,
                        'direction': 'BUY'
                    })
                    cprint(f"🕉️ MTF Bullish Signal: {token} | Strength: {signal_strength:.2f}", "green")
                
                # BEARISH SIGNAL LOGIC
                bearish_trigger = (trigger_data['stoch1_previous'] >= self.overbought and
                                  trigger_data['stoch1_current'] < self.overbought and
                                  trigger_data['stoch1_current'] < trigger_data['stoch_avg_current'])
                
                # Bearish Shield Check across timeframes
                shield_allows_short = not any(tf_results[tf]['trend_shield_bullish'] for tf in tf_results if tf != '15m')
                
                if bearish_trigger and total_bearish_weight > 0 and shield_allows_short:
                    signal_strength = (total_bearish_weight / max_possible_weight)
                    signal.update({
                        'signal': signal_strength,
                        'direction': 'SELL'
                    })
                    cprint(f"🕉️ MTF Bearish Signal: {token} | Strength: {signal_strength:.2f}", "red")
                
                # Validate and format signal
                if signal['direction'] != 'NEUTRAL':
                    if self.validate_signal(signal):
                        signal['metadata'] = self.format_metadata(signal['metadata'])
                        return signal
            
            return None
            
        except Exception as e:
            cprint(f"❌ Error generating Quad Rotation signals: {str(e)}", "red")
            import traceback
            traceback.print_exc()
            return None
