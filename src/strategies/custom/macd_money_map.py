"""
🕉️ Karma Dev's MACD Money Map Strategy
Complete implementation of the MACD Money Map trading framework
Based on TradingView's MACD indicator adapted for Python

Systems:
- System 1: Trend Following (Zero Line + Distance Rule)
- System 2: Divergence Detection (Momentum Exhaustion)
- System 3: Multi-Timeframe Alignment (Triple Timeframe Stack) - OPTIONAL
"""

from ..base_strategy import BaseStrategy
from src.config import MONITORED_TOKENS
import pandas as pd
import numpy as np
from termcolor import cprint
from src import nice_funcs as n
from typing import Literal, Tuple, Optional
from scipy.signal import argrelextrema


# ============================================================================
# MACD CALCULATOR (Matches TradingView Implementation)
# ============================================================================

class MACDCalculator:
    """
    Pure MACD calculation engine matching TradingView's behavior
    Adapted from PineScript version 6
    """
    
    def __init__(
        self,
        fast_length: int = 12,
        slow_length: int = 26,
        signal_length: int = 9,
        osc_type: Literal["EMA", "SMA"] = "EMA",
        sig_type: Literal["EMA", "SMA"] = "EMA"
    ):
        self.fast_length = fast_length
        self.slow_length = slow_length
        self.signal_length = signal_length
        self.osc_type = osc_type
        self.sig_type = sig_type
    
    def calculate_ma(self, source: pd.Series, length: int, ma_type: str) -> pd.Series:
        """
        Calculate moving average (EMA or SMA)
        Matches PineScript's ta.ema() and ta.sma() behavior
        """
        if ma_type == "EMA":
            return source.ewm(span=length, adjust=False).mean()
        elif ma_type == "SMA":
            return source.rolling(window=length).mean()
        else:
            raise ValueError(f"Unknown MA type: {ma_type}")
    
    def calculate(self, df: pd.DataFrame, source_col: str = 'close') -> pd.DataFrame:
        """
        Calculate MACD, Signal, and Histogram
        
        Mathematical formulation:
        1. maFast = MA(source, fast_length, osc_type)
        2. maSlow = MA(source, slow_length, osc_type)
        3. macd = maFast - maSlow
        4. signal = MA(macd, signal_length, sig_type)
        5. hist = macd - signal
        """
        df = df.copy()
        source = df[source_col]
        
        # Calculate fast and slow MAs
        ma_fast = self.calculate_ma(source, self.fast_length, self.osc_type)
        ma_slow = self.calculate_ma(source, self.slow_length, self.osc_type)
        
        # Calculate MACD line
        df['macd_line'] = ma_fast - ma_slow
        
        # Calculate signal line
        df['signal_line'] = self.calculate_ma(df['macd_line'], self.signal_length, self.sig_type)
        
        # Calculate histogram
        df['histogram'] = df['macd_line'] - df['signal_line']
        
        return df


# ============================================================================
# SYSTEM 1: TREND FOLLOWING (Zero Line Foundation + Distance Rule)
# ============================================================================

class System1TrendDetector:
    """
    Implements the "Absolute Law" and "Distance Rule" from briefing document
    
    Rules:
    - Long-only when MACD > 0
    - Short-only when MACD < 0
    - Distance threshold: |0.5| from zero line
    - Confirmation: Wait 2-3 candles after crossover
    """
    
    def __init__(self, distance_threshold: float = 0.5, confirmation_candles: int = 2):
        self.distance_threshold = distance_threshold
        self.confirmation_candles = confirmation_candles
    
    def detect_crossover(self, macd_series: pd.Series, signal_series: pd.Series) -> pd.Series:
        """
        Detect MACD line crossing signal line
        
        Bullish crossover: macd[t-1] <= signal[t-1] AND macd[t] > signal[t]
        Bearish crossover: macd[t-1] >= signal[t-1] AND macd[t] < signal[t]
        
        Returns:
            Series with values: 1 (bullish), -1 (bearish), 0 (no cross)
        """
        crossover = np.zeros(len(macd_series))
        
        for i in range(1, len(macd_series)):
            # Bullish crossover
            if macd_series.iloc[i-1] <= signal_series.iloc[i-1] and macd_series.iloc[i] > signal_series.iloc[i]:
                crossover[i] = 1
            # Bearish crossover
            elif macd_series.iloc[i-1] >= signal_series.iloc[i-1] and macd_series.iloc[i] < signal_series.iloc[i]:
                crossover[i] = -1
        
        return pd.Series(crossover, index=macd_series.index)
    
    def check_zero_line_regime(self, macd_value: float) -> str:
        """
        Absolute Law: Zero Line Foundation
        
        MACD > 0 → Bullish regime (long-only)
        MACD < 0 → Bearish regime (short-only)
        """
        if macd_value > 0:
            return "BULLISH"
        elif macd_value < 0:
            return "BEARISH"
        else:
            return "NEUTRAL"
    
    def validate_distance(self, macd_value: float, direction: int) -> bool:
        """
        Distance Rule: Filter chop zones
        
        For LONG: MACD must be > +0.5
        For SHORT: MACD must be < -0.5
        """
        if direction == 1:  # Bullish
            return macd_value > self.distance_threshold
        elif direction == -1:  # Bearish
            return macd_value < -self.distance_threshold
        return False
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Complete System 1 signal generation
        
        Process:
        1. Detect crossovers
        2. Check zero line regime
        3. Validate distance from zero
        4. Apply confirmation candles (t+2 or t+3)
        """
        df = df.copy()
        
        # Step 1: Detect raw crossovers
        crossovers = self.detect_crossover(df['macd_line'], df['signal_line'])
        
        # Step 2-3: Validate regime and distance
        valid_signals = np.zeros(len(df))
        
        for i in range(len(df)):
            if crossovers.iloc[i] == 0:
                continue
            
            macd_val = df['macd_line'].iloc[i]
            direction = int(crossovers.iloc[i])
            
            # Check regime alignment
            regime = self.check_zero_line_regime(macd_val)
            regime_valid = (
                (direction == 1 and regime == "BULLISH") or
                (direction == -1 and regime == "BEARISH")
            )
            
            # Check distance
            distance_valid = self.validate_distance(macd_val, direction)
            
            if regime_valid and distance_valid:
                valid_signals[i] = direction
        
        # Step 4: Apply confirmation delay
        df['system1_crossover'] = valid_signals
        df['system1_signal'] = pd.Series(valid_signals).shift(self.confirmation_candles).fillna(0).values
        
        return df


# ============================================================================
# SYSTEM 2: DIVERGENCE DETECTION (Momentum Exhaustion)
# ============================================================================

class System2DivergenceDetector:
    """
    Detects price-MACD divergence and histogram confirmation
    
    Patterns:
    - Bearish Divergence: Price higher high + MACD lower high
    - Bullish Divergence: Price lower low + MACD higher low
    
    Confirmation via histogram:
    - The Flip: First bar of new color
    - The Shrinking Tower: Decreasing magnitude
    - The Zero Bounce: Approaching zero
    """
    
    def __init__(self, lookback: int = 20, peak_order: int = 5):
        self.lookback = lookback
        self.peak_order = peak_order
    
    def find_peaks_and_troughs(self, series: pd.Series, order: int = 5) -> Tuple[np.ndarray, np.ndarray]:
        """
        Find local peaks and troughs in a series
        
        Peak: value > all neighbors within 'order' distance
        Trough: value < all neighbors within 'order' distance
        """
        # Ensure we have enough data
        if len(series) < order * 2 + 1:
            return np.array([]), np.array([])
        
        # Find local maxima (peaks)
        peaks = argrelextrema(series.values, np.greater, order=order)[0]
        
        # Find local minima (troughs)
        troughs = argrelextrema(series.values, np.less, order=order)[0]
        
        return peaks, troughs
    
    def detect_bearish_divergence(
        self, 
        price_highs: np.ndarray, 
        price_high_indices: np.ndarray,
        macd_highs: np.ndarray,
        macd_high_indices: np.ndarray
    ) -> dict:
        """
        Bearish Divergence:
        Price makes higher high BUT MACD makes lower high
        
        Mathematical condition:
        P(t) > P(t-n) AND MACD(t) < MACD(t-n)
        """
        if len(price_highs) < 2 or len(macd_highs) < 2:
            return {'detected': False}

        # Guard against division by zero
        if price_highs[-2] == 0 or macd_highs[-2] == 0:
            return {'detected': False}

        # Check last two peaks
        if (price_highs[-1] > price_highs[-2] and macd_highs[-1] < macd_highs[-2]):

            strength = abs(
                (price_highs[-1] / price_highs[-2] - 1) -
                (macd_highs[-1] / macd_highs[-2] - 1)
            )
            
            return {
                'detected': True,
                'type': 'BEARISH',
                'price_points': [int(price_high_indices[-2]), int(price_high_indices[-1])],
                'macd_points': [int(macd_high_indices[-2]), int(macd_high_indices[-1])],
                'strength': float(strength),
                'price_values': [float(price_highs[-2]), float(price_highs[-1])],
                'macd_values': [float(macd_highs[-2]), float(macd_highs[-1])]
            }
        
        return {'detected': False}
    
    def detect_bullish_divergence(
        self, 
        price_lows: np.ndarray, 
        price_low_indices: np.ndarray,
        macd_lows: np.ndarray,
        macd_low_indices: np.ndarray
    ) -> dict:
        """
        Bullish Divergence:
        Price makes lower low BUT MACD makes higher low
        
        Mathematical condition:
        P(t) < P(t-n) AND MACD(t) > MACD(t-n)
        """
        if len(price_lows) < 2 or len(macd_lows) < 2:
            return {'detected': False}

        # Guard against division by zero
        if price_lows[-2] == 0 or macd_lows[-2] == 0:
            return {'detected': False}

        # Check last two troughs
        if (price_lows[-1] < price_lows[-2] and macd_lows[-1] > macd_lows[-2]):

            strength = abs(
                (price_lows[-1] / price_lows[-2] - 1) -
                (macd_lows[-1] / macd_lows[-2] - 1)
            )
            
            return {
                'detected': True,
                'type': 'BULLISH',
                'price_points': [int(price_low_indices[-2]), int(price_low_indices[-1])],
                'macd_points': [int(macd_low_indices[-2]), int(macd_low_indices[-1])],
                'strength': float(strength),
                'price_values': [float(price_lows[-2]), float(price_lows[-1])],
                'macd_values': [float(macd_lows[-2]), float(macd_lows[-1])]
            }
        
        return {'detected': False}
    
    def check_histogram_confirmation(self, hist_series: pd.Series) -> dict:
        """
        Three histogram confirmation patterns:
        
        1. The Flip: First bar of new color
           sign(hist[t]) ≠ sign(hist[t-1])
        
        2. The Shrinking Tower: Decreasing magnitude
           |hist[t]| < |hist[t-1]| < |hist[t-2]|
        
        3. The Zero Bounce: Approaching zero without crossing
           |hist[t]| < threshold (e.g., 0.1)
        """
        if len(hist_series) < 3:
            return {'flip': False, 'shrinking': False, 'zero_bounce': False, 'any_confirmation': False}
        
        h0 = hist_series.iloc[-1]  # Current
        h1 = hist_series.iloc[-2]  # Previous
        h2 = hist_series.iloc[-3]  # 2 bars ago
        
        # Pattern 1: Flip (color change)
        flip = (np.sign(h0) != np.sign(h1)) and (h1 != 0)
        
        # Pattern 2: Shrinking tower
        shrinking = (abs(h0) < abs(h1)) and (abs(h1) < abs(h2))
        
        # Pattern 3: Zero bounce
        zero_bounce = abs(h0) < 0.1
        
        return {
            'flip': bool(flip),
            'shrinking': bool(shrinking),
            'zero_bounce': bool(zero_bounce),
            'any_confirmation': bool(flip or shrinking or zero_bounce)
        }
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Complete System 2 signal generation
        
        Process:
        1. Find peaks/troughs in price and MACD
        2. Detect divergences
        3. Check histogram confirmation
        4. Only trigger on confirmed divergence
        """
        df = df.copy()
        
        # Initialize columns
        df['system2_signal'] = 0
        df['system2_divergence_type'] = None
        df['system2_divergence_data'] = None
        
        # Check if we have enough data
        if len(df) < self.lookback:
            return df
        
        # Find peaks and troughs
        price_peaks, price_troughs = self.find_peaks_and_troughs(df['close'], self.peak_order)
        macd_peaks, macd_troughs = self.find_peaks_and_troughs(df['macd_line'], self.peak_order)
        
        # Get recent peaks/troughs
        recent_price_peaks = price_peaks[price_peaks >= len(df) - self.lookback]
        recent_price_troughs = price_troughs[price_troughs >= len(df) - self.lookback]
        recent_macd_peaks = macd_peaks[macd_peaks >= len(df) - self.lookback]
        recent_macd_troughs = macd_troughs[macd_troughs >= len(df) - self.lookback]
        
        # Detect bearish divergence
        if len(recent_price_peaks) >= 2 and len(recent_macd_peaks) >= 2:
            bearish_div = self.detect_bearish_divergence(
                df['close'].iloc[recent_price_peaks].values,
                recent_price_peaks,
                df['macd_line'].iloc[recent_macd_peaks].values,
                recent_macd_peaks
            )
            
            if bearish_div['detected']:
                # Check histogram confirmation
                hist_confirm = self.check_histogram_confirmation(df['histogram'])
                
                if hist_confirm['any_confirmation']:
                    df.loc[df.index[-1], 'system2_signal'] = -1
                    df.loc[df.index[-1], 'system2_divergence_type'] = 'BEARISH'
                    df.at[df.index[-1], 'system2_divergence_data'] = bearish_div
        
        # Detect bullish divergence
        if len(recent_price_troughs) >= 2 and len(recent_macd_troughs) >= 2:
            bullish_div = self.detect_bullish_divergence(
                df['close'].iloc[recent_price_troughs].values,
                recent_price_troughs,
                df['macd_line'].iloc[recent_macd_troughs].values,
                recent_macd_troughs
            )
            
            if bullish_div['detected']:
                # Check histogram confirmation
                hist_confirm = self.check_histogram_confirmation(df['histogram'])
                
                if hist_confirm['any_confirmation']:
                    df.loc[df.index[-1], 'system2_signal'] = 1
                    df.loc[df.index[-1], 'system2_divergence_type'] = 'BULLISH'
                    df.at[df.index[-1], 'system2_divergence_data'] = bullish_div
        
        return df


# ============================================================================
# SYSTEM 3: MULTI-TIMEFRAME ALIGNMENT (Triple Timeframe Stack)
# ============================================================================

class System3MTFAlignment:
    """
    Validates signals across HTF, MTF, LTF using 4x multiplier
    
    Timeframe Tiers:
    - Scalping: 15min → 5min → 1min
    - Day Trading: 1hour → 15min → 5min
    - Swing Trading: 1day → 4hour → 1hour
    """
    
    TIMEFRAME_CONFIGS = {
        'scalping': {'htf': '15m', 'mtf': '5m', 'ltf': '1m'},
        'day_trading': {'htf': '1h', 'mtf': '15m', 'ltf': '5m'},
        'swing_trading': {'htf': '1d', 'mtf': '4h', 'ltf': '1h'}
    }
    
    def __init__(self, trading_style: str = 'day_trading'):
        if trading_style not in self.TIMEFRAME_CONFIGS:
            raise ValueError(f"Unknown style: {trading_style}. Choose from {list(self.TIMEFRAME_CONFIGS.keys())}")
        
        self.config = self.TIMEFRAME_CONFIGS[trading_style]
        self.htf = self.config['htf']
        self.mtf = self.config['mtf']
        self.ltf = self.config['ltf']
    
    def check_htf_bias(self, htf_macd_value: float) -> str:
        """
        Higher Timeframe Trend Bias
        
        HTF MACD > 0 → Bullish bias (look for longs)
        HTF MACD < 0 → Bearish bias (look for shorts)
        """
        if htf_macd_value > 0:
            return "BULLISH"
        elif htf_macd_value < 0:
            return "BEARISH"
        return "NEUTRAL"
    
    def validate_alignment(
        self,
        htf_macd: float,
        mtf_signal: int,
        ltf_signal: int,
        direction: str
    ) -> dict:
        """
        Triple Timeframe Validation
        
        For LONG:
        - HTF: MACD > 0 (bullish bias)
        - MTF: Signal = 1 (bullish setup)
        - LTF: Signal = 1 (bullish trigger)
        
        For SHORT:
        - HTF: MACD < 0 (bearish bias)
        - MTF: Signal = -1 (bearish setup)
        - LTF: Signal = -1 (bearish trigger)
        """
        htf_bias = self.check_htf_bias(htf_macd)
        
        if direction == "LONG":
            htf_valid = htf_bias == "BULLISH"
            mtf_valid = mtf_signal == 1
            ltf_valid = ltf_signal == 1
        elif direction == "SHORT":
            htf_valid = htf_bias == "BEARISH"
            mtf_valid = mtf_signal == -1
            ltf_valid = ltf_signal == -1
        else:
            return {'aligned': False, 'confidence': 0.0}
        
        aligned = htf_valid and mtf_valid and ltf_valid
        
        # Calculate confidence
        valid_count = sum([htf_valid, mtf_valid, ltf_valid])
        confidence = valid_count / 3.0
        
        return {
            'aligned': aligned,
            'htf_bias': htf_bias,
            'htf_valid': htf_valid,
            'mtf_valid': mtf_valid,
            'ltf_valid': ltf_valid,
            'confidence': float(confidence)
        }


# ============================================================================
# RISK MANAGEMENT MODULE
# ============================================================================

class RiskManager:
    """
    Implements 2R profit target, breakeven, and trailing exit
    
    Rules:
    - Stop loss at recent swing high/low
    - Take profit at 2R (2x risk)
    - Close 50% at 2R, move SL to breakeven
    - Trail remaining 50% with opposite MACD crossover
    """
    
    def __init__(self, risk_percent: float = 1.0, r_multiple: float = 2.0):
        self.risk_percent = risk_percent
        self.r_multiple = r_multiple
    
    def find_swing_low(self, df: pd.DataFrame, lookback: int = 20) -> dict:
        """
        Find recent swing low for long stop loss
        
        Swing Low: Local minimum in lookback period
        """
        if len(df) < lookback:
            lookback = len(df)
        
        lows = df['low'].tail(lookback)
        swing_low_idx = lows.idxmin()
        swing_low_price = lows.min()
        
        return {
            'price': float(swing_low_price),
            'index': swing_low_idx,
            'candles_ago': len(df) - df.index.get_loc(swing_low_idx) - 1
        }
    
    def find_swing_high(self, df: pd.DataFrame, lookback: int = 20) -> dict:
        """
        Find recent swing high for short stop loss
        
        Swing High: Local maximum in lookback period
        """
        if len(df) < lookback:
            lookback = len(df)
        
        highs = df['high'].tail(lookback)
        swing_high_idx = highs.idxmax()
        swing_high_price = highs.max()
        
        return {
            'price': float(swing_high_price),
            'index': swing_high_idx,
            'candles_ago': len(df) - df.index.get_loc(swing_high_idx) - 1
        }
    
    def calculate_position_parameters(
        self,
        entry_price: float,
        stop_loss: float,
        direction: str,
        account_size: float
    ) -> dict:
        """
        Calculate complete position parameters
        
        Formula:
        1. Risk = |Entry - SL|
        2. Position_Size = (Account × Risk%) / Risk
        3. TP_2R = Entry ± (2 × Risk)
        """
        # Calculate risk per unit
        risk_per_unit = abs(entry_price - stop_loss)
        
        if risk_per_unit == 0:
            raise ValueError("Stop loss cannot equal entry price")
        
        # Calculate dollars at risk
        risk_dollars = account_size * (self.risk_percent / 100)
        
        # Calculate position size
        position_size_usd = risk_dollars / (risk_per_unit / entry_price)
        
        # Calculate 2R take profit
        if direction == "LONG":
            take_profit_2r = entry_price + (self.r_multiple * risk_per_unit)
        else:  # SHORT
            take_profit_2r = entry_price - (self.r_multiple * risk_per_unit)
        
        # Calculate reward
        reward_per_unit = abs(take_profit_2r - entry_price)
        reward_dollars = position_size_usd * (reward_per_unit / entry_price)
        
        return {
            'entry': float(entry_price),
            'stop_loss': float(stop_loss),
            'take_profit_2r': float(take_profit_2r),
            'breakeven': float(entry_price),
            'risk_per_unit': float(risk_per_unit),
            'risk_dollars': float(risk_dollars),
            'position_size_usd': float(position_size_usd),
            'reward_dollars': float(reward_dollars),
            'r_ratio': self.r_multiple,
            'partial_close_percent': 50
        }


# ============================================================================
# MAIN STRATEGY CLASS (Karma Dev Structure)
# ============================================================================

class MACDMoneyMapStrategy(BaseStrategy):
    """
    🕉️ Karma Dev's MACD Money Map Strategy
    
    Complete implementation combining:
    - System 1: Trend following via zero line + distance
    - System 2: Divergence detection with histogram confirmation
    - System 3: Triple timeframe alignment (4x multiplier) - OPTIONAL
    - Mathematical risk management (2R, breakeven, trailing)
    
    Trading Styles:
    - scalping: 15m/5m/1m
    - day_trading: 1h/15m/5m
    - swing_trading: 1d/4h/1h
    
    ========================================================================
    FRONTEND INPUT HINTS:
    ========================================================================
    
    BASIC PARAMETERS:
    -----------------
    trading_style: str = 'day_trading'
        Options: 'scalping', 'day_trading', 'swing_trading'
        Description: Determines timeframe configuration (HTF/MTF/LTF)
        
    account_size: float = 10000
        Description: Total account value in USD for position sizing
        
    distance_threshold: float = 0.5
        Description: Minimum MACD distance from zero line (filters chop)
        Range: 0.1 - 2.0
        
    confirmation_candles: int = 2
        Description: Number of candles to wait after crossover
        Range: 0 - 5
        
    ========================================================================
    SYSTEM 3 (MULTI-TIMEFRAME) CONTROLS:
    ========================================================================
    
    use_mtf_confirmation: bool = True
        Description: Enable/disable System 3 (Multi-Timeframe Alignment)
        - True: Requires HTF, MTF, and LTF alignment (A+ setups only)
        - False: Uses single timeframe only (more signals, less filtering)
        Default: True (recommended for beginners)
        
    single_timeframe: str = '5m'
        Description: Which timeframe to use when MTF is disabled
        Only used if use_mtf_confirmation = False
        Options: '1m', '5m', '15m', '1h', '4h', '1d'
        
    mtf_min_confidence: float = 1.0
        Description: Minimum timeframe alignment confidence (0.0 - 1.0)
        - 1.0 = All 3 timeframes must align (strictest)
        - 0.66 = At least 2 out of 3 timeframes (moderate)
        - 0.33 = At least 1 out of 3 timeframes (loose)
        Default: 1.0
        
    ========================================================================
    SYSTEM PRIORITY:
    ========================================================================
    
    prioritize_divergence: bool = True
        Description: Give System 2 (divergence) priority over System 1 (trend)
        - True: Divergence signals override trend signals
        - False: Both systems weighted equally
        
    ========================================================================
    RISK MANAGEMENT:
    ========================================================================
    
    risk_percent: float = 1.0
        Description: % of account to risk per trade
        Range: 0.1 - 5.0
        
    r_multiple: float = 2.0
        Description: Reward-to-risk ratio (take profit)
        Range: 1.0 - 10.0
        
    swing_lookback: int = 20
        Description: Candles to look back for swing high/low (stop loss)
        Range: 5 - 50
        
    ========================================================================
    USAGE EXAMPLES:
    ========================================================================
    
    # Conservative A+ Setup (All timeframes aligned):
    strategy = MACDMoneyMapStrategy(
        trading_style='day_trading',
        use_mtf_confirmation=True,
        mtf_min_confidence=1.0
    )
    
    # Aggressive Single Timeframe:
    strategy = MACDMoneyMapStrategy(
        trading_style='day_trading',
        use_mtf_confirmation=False,
        single_timeframe='5m'
    )
    
    # Moderate (2 out of 3 timeframes):
    strategy = MACDMoneyMapStrategy(
        trading_style='swing_trading',
        use_mtf_confirmation=True,
        mtf_min_confidence=0.66
    )
    
    ========================================================================
    """
    
    def __init__(
        self, 
        # Basic parameters
        trading_style: str = 'day_trading',
        account_size: float = 10000,
        distance_threshold: float = 0.5,
        confirmation_candles: int = 2,
        
        # System 3 (MTF) controls
        use_mtf_confirmation: bool = True,
        single_timeframe: str = '5m',
        mtf_min_confidence: float = 1.0,
        
        # System priority
        prioritize_divergence: bool = True,
        
        # Risk management
        risk_percent: float = 1.0,
        r_multiple: float = 2.0,
        swing_lookback: int = 20
    ):
        """
        Initialize MACD Money Map Strategy
        
        See class docstring for detailed parameter descriptions
        """
        super().__init__("MACD Money Map")
        
        # Store configuration
        self.trading_style = trading_style
        self.account_size = account_size
        self.use_mtf_confirmation = use_mtf_confirmation
        self.single_timeframe = single_timeframe
        self.mtf_min_confidence = mtf_min_confidence
        self.prioritize_divergence = prioritize_divergence
        self.swing_lookback = swing_lookback
        
        # Initialize subsystems
        self.macd_calc = MACDCalculator()
        self.system1 = System1TrendDetector(
            distance_threshold=distance_threshold,
            confirmation_candles=confirmation_candles
        )
        self.system2 = System2DivergenceDetector()
        self.risk_mgr = RiskManager(risk_percent=risk_percent, r_multiple=r_multiple)
        
        # Initialize System 3 only if enabled
        if self.use_mtf_confirmation:
            self.system3 = System3MTFAlignment(trading_style)
            self.timeframes = System3MTFAlignment.TIMEFRAME_CONFIGS[trading_style]
        else:
            self.system3 = None
            self.timeframes = {'single': single_timeframe}
        
        # Print configuration
        cprint(f"\n{'='*70}", "cyan")
        cprint(f"🕉️ MACD Money Map Strategy Initialized", "cyan")
        cprint(f"{'='*70}", "cyan")
        cprint(f"Trading Style: {trading_style}", "white")
        
        if self.use_mtf_confirmation:
            cprint(f"Multi-Timeframe: ENABLED", "green")
            cprint(f"  HTF: {self.timeframes['htf']} (Trend Bias)", "white")
            cprint(f"  MTF: {self.timeframes['mtf']} (Setup)", "white")
            cprint(f"  LTF: {self.timeframes['ltf']} (Trigger)", "white")
            cprint(f"  Min Confidence: {mtf_min_confidence:.0%}", "white")
        else:
            cprint(f"Multi-Timeframe: DISABLED", "yellow")
            cprint(f"  Single Timeframe: {single_timeframe}", "white")
        
        cprint(f"Distance Threshold: {distance_threshold}", "white")
        cprint(f"Confirmation Candles: {confirmation_candles}", "white")
        cprint(f"Prioritize Divergence: {prioritize_divergence}", "white")
        cprint(f"Risk per Trade: {risk_percent}%", "white")
        cprint(f"R Multiple: {r_multiple}R", "white")
        cprint(f"{'='*70}\n", "cyan")
    
    def fetch_mtf_data(self, token: str) -> Optional[dict]:
        """
        Fetch data for timeframes based on MTF setting
        
        Returns:
            Single timeframe mode: {'single': DataFrame}
            Multi timeframe mode: {'htf': DataFrame, 'mtf': DataFrame, 'ltf': DataFrame}
        """
        try:
            if not self.use_mtf_confirmation:
                # Single timeframe mode
                days_back = 7 if self.single_timeframe in ['1m', '5m'] else 30
                data = n.get_data(token, days_back=days_back, timeframe=self.single_timeframe)
                
                if data is None or data.empty:
                    cprint(f"  ⚠️  No data for {token} on {self.single_timeframe}", "yellow")
                    return None
                
                if len(data) < 50:
                    cprint(f"  ⚠️  Insufficient data for {token}", "yellow")
                    return None
                
                return {'single': data}
            
            else:
                # Multi-timeframe mode
                if self.trading_style == 'scalping':
                    htf_days, mtf_days, ltf_days = 1, 1, 1
                elif self.trading_style == 'day_trading':
                    htf_days, mtf_days, ltf_days = 7, 3, 1
                else:  # swing_trading
                    htf_days, mtf_days, ltf_days = 30, 14, 7
                
                htf_data = n.get_data(token, days_back=htf_days, timeframe=self.timeframes['htf'])
                mtf_data = n.get_data(token, days_back=mtf_days, timeframe=self.timeframes['mtf'])
                ltf_data = n.get_data(token, days_back=ltf_days, timeframe=self.timeframes['ltf'])
                
                # Validate data
                if any(d is None or d.empty for d in [htf_data, mtf_data, ltf_data]):
                    cprint(f"  ⚠️  Missing timeframe data for {token}", "yellow")
                    return None
                
                # Ensure minimum data
                min_candles = 50
                if any(len(d) < min_candles for d in [htf_data, mtf_data, ltf_data]):
                    cprint(f"  ⚠️  Insufficient data for {token}", "yellow")
                    return None
                
                return {
                    'htf': htf_data,
                    'mtf': mtf_data,
                    'ltf': ltf_data
                }
            
        except Exception as e:
            cprint(f"  ❌ Error fetching data for {token}: {e}", "red")
            return None
    
    def generate_signals(self) -> Optional[dict]:
        """
        🕉️ Main signal generation with optional MTF validation
        
        Single Timeframe Mode (use_mtf_confirmation=False):
        - Analyzes single timeframe only
        - Faster signal generation
        - More signals but less filtered
        
        Multi-Timeframe Mode (use_mtf_confirmation=True):
        - Analyzes HTF, MTF, LTF
        - Requires alignment across timeframes
        - Fewer but higher quality A+ setups
        """
        try:
            cprint("\n" + "="*70, "cyan")
            cprint("🕉️ MACD Money Map - Scanning for signals...", "cyan")
            cprint("="*70, "cyan")
            
            for token in MONITORED_TOKENS:
                cprint(f"\n📊 Analyzing {token}...", "white")
                
                # Fetch data based on MTF setting
                data = self.fetch_mtf_data(token)
                if data is None:
                    continue
                
                # ============================================================
                # SINGLE TIMEFRAME MODE
                # ============================================================
                if not self.use_mtf_confirmation:
                    df = data['single']
                    
                    # Calculate MACD
                    df = self.macd_calc.calculate(df)
                    
                    # Generate signals from both systems
                    df = self.system1.generate_signals(df)
                    df = self.system2.generate_signals(df)
                    
                    s1_signal = df['system1_signal'].iloc[-1]
                    s2_signal = df['system2_signal'].iloc[-1]
                    
                    cprint(f"  System 1: {int(s1_signal)}, System 2: {int(s2_signal)}", "white")
                    
                    # Determine final signal
                    if self.prioritize_divergence and s2_signal != 0:
                        final_signal = s2_signal
                        signal_system = "SYSTEM2"
                        cprint(f"  💎 System 2 DIVERGENCE signal!", "green")
                    elif s1_signal != 0:
                        final_signal = s1_signal
                        signal_system = "SYSTEM1"
                        cprint(f"  ⚡ System 1 TREND signal!", "green")
                    else:
                        cprint(f"  ⏸️  No signal", "yellow")
                        continue
                    
                    direction = "LONG" if final_signal == 1 else "SHORT"
                    entry_price = df['close'].iloc[-1]
                    
                    # Calculate risk parameters
                    try:
                        if direction == "LONG":
                            swing = self.risk_mgr.find_swing_low(df, self.swing_lookback)
                            stop_loss = swing['price']
                            if stop_loss >= entry_price:
                                cprint(f"  ❌ Invalid SL for LONG", "red")
                                continue
                        else:
                            swing = self.risk_mgr.find_swing_high(df, self.swing_lookback)
                            stop_loss = swing['price']
                            if stop_loss <= entry_price:
                                cprint(f"  ❌ Invalid SL for SHORT", "red")
                                continue
                        
                        position_params = self.risk_mgr.calculate_position_parameters(
                            entry_price, stop_loss, direction, self.account_size
                        )
                    except Exception as e:
                        cprint(f"  ❌ Risk calculation error: {e}", "red")
                        continue
                    
                    # Build signal
                    signal = {
                        'token': token,
                        'signal': 1.0,  # Single timeframe confidence
                        'direction': 'BUY' if direction == "LONG" else 'SELL',
                        'metadata': {
                            'strategy_type': 'macd_money_map',
                            'system': signal_system,
                            'trading_style': 'single_timeframe',
                            'mtf_enabled': False,
                            'timeframe': self.single_timeframe,
                            
                            # Entry parameters
                            'entry_price': float(entry_price),
                            'stop_loss': float(position_params['stop_loss']),
                            'take_profit_2r': float(position_params['take_profit_2r']),
                            'breakeven': float(position_params['breakeven']),
                            
                            # Position sizing
                            'position_size_usd': float(position_params['position_size_usd']),
                            'risk_dollars': float(position_params['risk_dollars']),
                            'reward_dollars': float(position_params['reward_dollars']),
                            'r_ratio': position_params['r_ratio'],
                            
                            # MACD values
                            'macd_line': float(df['macd_line'].iloc[-1]),
                            'signal_line': float(df['signal_line'].iloc[-1]),
                            'histogram': float(df['histogram'].iloc[-1]),
                            
                            # Divergence data
                            'divergence_data': df['system2_divergence_data'].iloc[-1] if signal_system == "SYSTEM2" else None,
                            
                            'current_price': float(df['close'].iloc[-1]),
                            'entry_candle_close_time': str(df.index[-1]),
                            'partial_close_percent': 50,
                            'trailing_exit': 'opposite_macd_crossover'
                        }
                    }
                    
                    if self.validate_signal(signal):
                        signal['metadata'] = self.format_metadata(signal['metadata'])
                        self._print_signal_success(signal, position_params, token, entry_price)
                        return signal
                
                # ============================================================
                # MULTI-TIMEFRAME MODE
                # ============================================================
                else:
                    # Calculate MACD for all timeframes
                    htf_df = self.macd_calc.calculate(data['htf'])
                    mtf_df = self.macd_calc.calculate(data['mtf'])
                    ltf_df = self.macd_calc.calculate(data['ltf'])
                    
                    # Check HTF bias
                    htf_macd_current = htf_df['macd_line'].iloc[-1]
                    htf_bias = self.system3.check_htf_bias(htf_macd_current)
                    
                    cprint(f"  📈 HTF Bias: {htf_bias} (MACD: {htf_macd_current:.4f})", "white")
                    
                    if htf_bias == "NEUTRAL":
                        cprint(f"  ⏸️  HTF neutral - skipping", "yellow")
                        continue
                    
                    # Generate signals on MTF
                    mtf_df = self.system1.generate_signals(mtf_df)
                    mtf_df = self.system2.generate_signals(mtf_df)
                    
                    mtf_s1 = mtf_df['system1_signal'].iloc[-1]
                    mtf_s2 = mtf_df['system2_signal'].iloc[-1]
                    
                    cprint(f"  🎯 MTF S1: {int(mtf_s1)}, S2: {int(mtf_s2)}", "white")
                    
                    if self.prioritize_divergence and mtf_s2 != 0:
                        mtf_signal = mtf_s2
                        signal_system = "SYSTEM2"
                        cprint(f"  💎 System 2 DIVERGENCE on MTF!", "green")
                    elif mtf_s1 != 0:
                        mtf_signal = mtf_s1
                        signal_system = "SYSTEM1"
                        cprint(f"  ⚡ System 1 TREND on MTF", "green")
                    else:
                        cprint(f"  ⏸️  No MTF setup", "yellow")
                        continue
                    
                    # Generate signals on LTF
                    ltf_df = self.system1.generate_signals(ltf_df)
                    ltf_df = self.system2.generate_signals(ltf_df)
                    
                    ltf_s1 = ltf_df['system1_signal'].iloc[-1]
                    ltf_s2 = ltf_df['system2_signal'].iloc[-1]
                    
                    ltf_signal = ltf_s2 if ltf_s2 != 0 else ltf_s1
                    
                    cprint(f"  🎯 LTF S1: {int(ltf_s1)}, S2: {int(ltf_s2)}", "white")
                    
                    if ltf_signal == 0:
                        cprint(f"  ⏸️  No LTF trigger", "yellow")
                        continue
                    
                    direction = "LONG" if ltf_signal == 1 else "SHORT"
                    
                    # Validate alignment
                    alignment = self.system3.validate_alignment(
                        htf_macd_current, int(mtf_signal), int(ltf_signal), direction
                    )
                    
                    cprint(f"  🔗 Alignment: {alignment['confidence']:.1%} (Min: {self.mtf_min_confidence:.1%})", "white")
                    
                    if alignment['confidence'] < self.mtf_min_confidence:
                        cprint(f"  ❌ Below confidence threshold", "red")
                        continue
                    
                    # Calculate risk
                    entry_price = ltf_df['close'].iloc[-1]
                    
                    try:
                        if direction == "LONG":
                            swing = self.risk_mgr.find_swing_low(ltf_df, self.swing_lookback)
                            stop_loss = swing['price']
                            if stop_loss >= entry_price:
                                cprint(f"  ❌ Invalid SL for LONG", "red")
                                continue
                        else:
                            swing = self.risk_mgr.find_swing_high(ltf_df, self.swing_lookback)
                            stop_loss = swing['price']
                            if stop_loss <= entry_price:
                                cprint(f"  ❌ Invalid SL for SHORT", "red")
                                continue
                        
                        position_params = self.risk_mgr.calculate_position_parameters(
                            entry_price, stop_loss, direction, self.account_size
                        )
                    except Exception as e:
                        cprint(f"  ❌ Risk calculation error: {e}", "red")
                        continue
                    
                    # Build signal
                    signal = {
                        'token': token,
                        'signal': alignment['confidence'],
                        'direction': 'BUY' if direction == "LONG" else 'SELL',
                        'metadata': {
                            'strategy_type': 'macd_money_map',
                            'system': signal_system,
                            'trading_style': self.trading_style,
                            'mtf_enabled': True,
                            
                            'entry_price': float(entry_price),
                            'stop_loss': float(position_params['stop_loss']),
                            'take_profit_2r': float(position_params['take_profit_2r']),
                            'breakeven': float(position_params['breakeven']),
                            
                            'position_size_usd': float(position_params['position_size_usd']),
                            'risk_dollars': float(position_params['risk_dollars']),
                            'reward_dollars': float(position_params['reward_dollars']),
                            'r_ratio': position_params['r_ratio'],
                            
                            'htf_bias': htf_bias,
                            'htf_macd': float(htf_macd_current),
                            'timeframe_alignment': alignment,
                            
                            'ltf_macd_line': float(ltf_df['macd_line'].iloc[-1]),
                            'ltf_signal_line': float(ltf_df['signal_line'].iloc[-1]),
                            'ltf_histogram': float(ltf_df['histogram'].iloc[-1]),
                            
                            'mtf_macd_line': float(mtf_df['macd_line'].iloc[-1]),
                            'mtf_signal_line': float(mtf_df['signal_line'].iloc[-1]),
                            'mtf_histogram': float(mtf_df['histogram'].iloc[-1]),
                            
                            'divergence_data': mtf_df['system2_divergence_data'].iloc[-1] if signal_system == "SYSTEM2" else None,
                            
                            'current_price': float(ltf_df['close'].iloc[-1]),
                            'timeframes': self.timeframes,
                            'entry_candle_close_time': str(ltf_df.index[-1]),
                            'partial_close_percent': 50,
                            'trailing_exit': 'opposite_macd_crossover'
                        }
                    }
                    
                    if self.validate_signal(signal):
                        signal['metadata'] = self.format_metadata(signal['metadata'])
                        self._print_signal_success(signal, position_params, token, entry_price)
                        return signal
            
            cprint("\n⏸️  No valid signals found", "yellow")
            return None
            
        except Exception as e:
            cprint(f"\n❌ Error: {str(e)}", "red")
            import traceback
            traceback.print_exc()
            return None
    
    def _print_signal_success(self, signal: dict, position_params: dict, token: str, entry_price: float):
        """Helper to print signal success message"""
        cprint("\n" + "="*70, "green")
        cprint(f"✅ {signal['metadata']['system']} {signal['direction']} SIGNAL!", "green")
        cprint("="*70, "green")
        cprint(f"Token: {token}", "white")
        cprint(f"Entry: ${entry_price:.6f}", "white")
        cprint(f"Stop Loss: ${position_params['stop_loss']:.6f}", "white")
        cprint(f"Take Profit: ${position_params['take_profit_2r']:.6f}", "white")
        cprint(f"Position: ${position_params['position_size_usd']:.2f}", "white")
        cprint(f"Risk: ${position_params['risk_dollars']:.2f} | Reward: ${position_params['reward_dollars']:.2f}", "white")
        cprint(f"Confidence: {signal['signal']:.1%}", "white")
        cprint("="*70 + "\n", "green")
