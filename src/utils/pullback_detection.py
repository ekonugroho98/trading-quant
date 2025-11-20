"""
Pullback Detection Module
Deteksi pullback dalam trend untuk entry timing yang lebih baik
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')


def detect_swing_points(df: pd.DataFrame,
                        window: int = 5,
                        min_swing_size: float = 0.01) -> Dict:
    """
    Detect swing highs dan swing lows
    
    Args:
        df: DataFrame dengan OHLC data
        window: Window untuk detect local extrema
        min_swing_size: Minimum swing size (percentage) untuk filter noise
    
    Returns:
        Dictionary dengan swing points
    """
    if 'High' not in df.columns or 'Low' not in df.columns:
        return {'swing_highs': [], 'swing_lows': []}
    
    try:
        from scipy.signal import argrelextrema
    except ImportError:
        print("⚠️  scipy tidak tersedia untuk swing detection")
        return {'swing_highs': [], 'swing_lows': []}
    
    # Detect local maxima (swing highs)
    high_values = df['High'].values
    swing_high_indices = argrelextrema(high_values, np.greater, order=window)[0]
    
    # Detect local minima (swing lows)
    low_values = df['Low'].values
    swing_low_indices = argrelextrema(low_values, np.less, order=window)[0]
    
    # Filter berdasarkan min_swing_size
    swing_highs = []
    swing_lows = []
    
    for idx in swing_high_indices:
        if idx < len(df):
            price = df['High'].iloc[idx]
            # Check if swing is significant enough
            if len(swing_highs) > 0:
                last_high = swing_highs[-1]['price']
                swing_size = abs(price - last_high) / last_high
                if swing_size >= min_swing_size:
                    swing_highs.append({
                        'index': idx,
                        'date': df.index[idx] if isinstance(df.index, pd.DatetimeIndex) else idx,
                        'price': price
                    })
            else:
                swing_highs.append({
                    'index': idx,
                    'date': df.index[idx] if isinstance(df.index, pd.DatetimeIndex) else idx,
                    'price': price
                })
    
    for idx in swing_low_indices:
        if idx < len(df):
            price = df['Low'].iloc[idx]
            # Check if swing is significant enough
            if len(swing_lows) > 0:
                last_low = swing_lows[-1]['price']
                swing_size = abs(price - last_low) / last_low
                if swing_size >= min_swing_size:
                    swing_lows.append({
                        'index': idx,
                        'date': df.index[idx] if isinstance(df.index, pd.DatetimeIndex) else idx,
                        'price': price
                    })
            else:
                swing_lows.append({
                    'index': idx,
                    'date': df.index[idx] if isinstance(df.index, pd.DatetimeIndex) else idx,
                    'price': price
                })
    
    return {
        'swing_highs': swing_highs,
        'swing_lows': swing_lows
    }


def calculate_trend(df: pd.DataFrame,
                   ma_short: int = 10,
                   ma_long: int = 20) -> pd.Series:
    """
    Calculate trend direction (1 = uptrend, -1 = downtrend, 0 = neutral)
    
    Args:
        df: DataFrame dengan price data
        ma_short: Short MA window
        ma_long: Long MA window
    
    Returns:
        Series dengan trend direction
    """
    ma_short_val = df['Close'].rolling(window=ma_short).mean()
    ma_long_val = df['Close'].rolling(window=ma_long).mean()
    
    trend = pd.Series(0, index=df.index)
    trend[ma_short_val > ma_long_val] = 1  # Uptrend
    trend[ma_short_val < ma_long_val] = -1  # Downtrend
    
    return trend


def detect_pullback(df: pd.DataFrame,
                    swing_points: Optional[Dict] = None,
                    trend: Optional[pd.Series] = None,
                    min_retracement: float = 0.236,
                    max_retracement: float = 0.786) -> pd.DataFrame:
    """
    Detect pullback dalam trend
    
    Args:
        df: DataFrame dengan OHLC data
        swing_points: Optional pre-calculated swing points
        trend: Optional pre-calculated trend
        min_retracement: Minimum retracement untuk dianggap pullback (default 23.6%)
        max_retracement: Maximum retracement sebelum dianggap reversal (default 78.6%)
    
    Returns:
        DataFrame dengan pullback indicators
    """
    result = df.copy()
    
    # Initialize pullback columns
    result['Pullback_Detected'] = False
    result['Pullback_Type'] = 'None'  # 'Shallow', 'Medium', 'Deep', 'Reversal'
    result['Pullback_Depth'] = 0.0
    result['Pullback_Signal'] = 0  # 1 = LONG opportunity, -1 = SHORT opportunity, 0 = None
    result['Pullback_Confidence'] = 0.0
    
    # Get swing points
    if swing_points is None:
        swing_points = detect_swing_points(df)
    
    # Get trend
    if trend is None:
        trend = calculate_trend(df)
    
    if len(swing_points['swing_highs']) < 2 or len(swing_points['swing_lows']) < 2:
        return result
    
    # Process each period
    for i in range(len(df)):
        current_trend = trend.iloc[i] if i < len(trend) else 0
        current_price = df['Close'].iloc[i]
        
        if current_trend == 0:
            continue
        
        # Find recent swing points
        recent_highs = [s for s in swing_points['swing_highs'] if s['index'] <= i]
        recent_lows = [s for s in swing_points['swing_lows'] if s['index'] <= i]
        
        if len(recent_highs) < 1 or len(recent_lows) < 1:
            continue
        
        if current_trend == 1:  # Uptrend
            # Pullback = price turun dari swing high
            last_high = recent_highs[-1]
            last_low = recent_lows[-1] if recent_lows[-1]['index'] < last_high['index'] else (
                recent_lows[-2] if len(recent_lows) >= 2 else recent_lows[-1]
            )
            
            # Calculate retracement
            swing_range = last_high['price'] - last_low['price']
            if swing_range > 0:
                retracement = (last_high['price'] - current_price) / swing_range
                
                # Check if this is a pullback (not reversal)
                if min_retracement <= retracement <= max_retracement:
                    result.loc[result.index[i], 'Pullback_Detected'] = True
                    result.loc[result.index[i], 'Pullback_Depth'] = retracement
                    
                    # Classify pullback depth
                    if retracement <= 0.382:
                        result.loc[result.index[i], 'Pullback_Type'] = 'Shallow'
                        confidence = 0.8  # High confidence
                    elif retracement <= 0.618:
                        result.loc[result.index[i], 'Pullback_Type'] = 'Medium'
                        confidence = 0.6  # Medium confidence
                    else:
                        result.loc[result.index[i], 'Pullback_Type'] = 'Deep'
                        confidence = 0.4  # Low confidence (bisa jadi reversal)
                    
                    # LONG opportunity signal
                    result.loc[result.index[i], 'Pullback_Signal'] = 1
                    result.loc[result.index[i], 'Pullback_Confidence'] = confidence
        
        elif current_trend == -1:  # Downtrend
            # Pullback = price naik dari swing low
            last_low = recent_lows[-1]
            last_high = recent_highs[-1] if recent_highs[-1]['index'] < last_low['index'] else (
                recent_highs[-2] if len(recent_highs) >= 2 else recent_highs[-1]
            )
            
            # Calculate retracement
            swing_range = last_high['price'] - last_low['price']
            if swing_range > 0:
                retracement = (current_price - last_low['price']) / swing_range
                
                # Check if this is a pullback (not reversal)
                if min_retracement <= retracement <= max_retracement:
                    result.loc[result.index[i], 'Pullback_Detected'] = True
                    result.loc[result.index[i], 'Pullback_Depth'] = retracement
                    
                    # Classify pullback depth
                    if retracement <= 0.382:
                        result.loc[result.index[i], 'Pullback_Type'] = 'Shallow'
                        confidence = 0.8
                    elif retracement <= 0.618:
                        result.loc[result.index[i], 'Pullback_Type'] = 'Medium'
                        confidence = 0.6
                    else:
                        result.loc[result.index[i], 'Pullback_Type'] = 'Deep'
                        confidence = 0.4
                    
                    # SHORT opportunity signal
                    result.loc[result.index[i], 'Pullback_Signal'] = -1
                    result.loc[result.index[i], 'Pullback_Confidence'] = confidence
    
    return result


def calculate_fibonacci_pullback_levels(swing_high: float,
                                      swing_low: float,
                                      trend: int) -> Dict[str, float]:
    """
    Calculate Fibonacci retracement levels untuk pullback
    
    Args:
        swing_high: Swing high price
        swing_low: Swing low price
        trend: 1 = uptrend, -1 = downtrend
    
    Returns:
        Dictionary dengan Fibonacci levels
    """
    price_range = swing_high - swing_low
    
    if trend == 1:  # Uptrend - pullback dari high ke low
        return {
            'fib_236': swing_high - (price_range * 0.236),
            'fib_382': swing_high - (price_range * 0.382),
            'fib_500': swing_high - (price_range * 0.500),
            'fib_618': swing_high - (price_range * 0.618),
            'fib_786': swing_high - (price_range * 0.786)
        }
    else:  # Downtrend - pullback dari low ke high
        return {
            'fib_236': swing_low + (price_range * 0.236),
            'fib_382': swing_low + (price_range * 0.382),
            'fib_500': swing_low + (price_range * 0.500),
            'fib_618': swing_low + (price_range * 0.618),
            'fib_786': swing_low + (price_range * 0.786)
        }


def confirm_pullback_with_volume(df: pd.DataFrame,
                                pullback_signal: pd.Series,
                                volume_threshold: float = 0.8) -> pd.Series:
    """
    Confirm pullback dengan volume analysis
    Pullback yang valid biasanya memiliki volume yang lebih rendah
    
    Args:
        df: DataFrame dengan Volume data
        pullback_signal: Series dengan pullback signals
        volume_threshold: Volume ratio threshold (pullback volume < threshold * avg volume)
    
    Returns:
        Series dengan confirmed pullback signals
    """
    if 'Volume' not in df.columns:
        return pullback_signal
    
    confirmed = pullback_signal.copy()
    avg_volume = df['Volume'].rolling(window=20).mean()
    
    for i in range(len(df)):
        if pullback_signal.iloc[i] != 0:
            current_volume = df['Volume'].iloc[i]
            avg_vol = avg_volume.iloc[i] if pd.notna(avg_volume.iloc[i]) else current_volume
            
            volume_ratio = current_volume / avg_vol if avg_vol > 0 else 1.0
            
            # Pullback valid jika volume rendah (bukan reversal)
            if volume_ratio > volume_threshold:
                confirmed.iloc[i] = 0  # Reject pullback jika volume tinggi
    
    return confirmed


def get_pullback_entry_levels(df: pd.DataFrame,
                              current_price: float,
                              trend: int,
                              swing_points: Optional[Dict] = None) -> Dict:
    """
    Calculate optimal entry levels untuk pullback
    
    Args:
        df: DataFrame dengan price data
        current_price: Current price
        trend: Trend direction (1 = uptrend, -1 = downtrend)
        swing_points: Optional swing points
    
    Returns:
        Dictionary dengan pullback entry levels
    """
    if swing_points is None:
        swing_points = detect_swing_points(df)
    
    entry_levels = {
        'pullback_entry_1': None,  # Shallow pullback entry
        'pullback_entry_2': None,  # Medium pullback entry
        'pullback_entry_3': None,  # Deep pullback entry
        'fib_levels': {}
    }
    
    if trend == 1:  # Uptrend
        if len(swing_points['swing_highs']) >= 1 and len(swing_points['swing_lows']) >= 1:
            last_high = swing_points['swing_highs'][-1]
            last_low = swing_points['swing_lows'][-1] if swing_points['swing_lows'][-1]['index'] < last_high['index'] else (
                swing_points['swing_lows'][-2] if len(swing_points['swing_lows']) >= 2 else swing_points['swing_lows'][-1]
            )
            
            fib_levels = calculate_fibonacci_pullback_levels(
                last_high['price'], last_low['price'], trend
            )
            
            entry_levels['fib_levels'] = fib_levels
            entry_levels['pullback_entry_1'] = fib_levels['fib_382']  # Shallow
            entry_levels['pullback_entry_2'] = fib_levels['fib_618']  # Medium
            entry_levels['pullback_entry_3'] = fib_levels['fib_786']  # Deep
    
    elif trend == -1:  # Downtrend
        if len(swing_points['swing_highs']) >= 1 and len(swing_points['swing_lows']) >= 1:
            last_low = swing_points['swing_lows'][-1]
            last_high = swing_points['swing_highs'][-1] if swing_points['swing_highs'][-1]['index'] < last_low['index'] else (
                swing_points['swing_highs'][-2] if len(swing_points['swing_highs']) >= 2 else swing_points['swing_highs'][-1]
            )
            
            fib_levels = calculate_fibonacci_pullback_levels(
                last_high['price'], last_low['price'], trend
            )
            
            entry_levels['fib_levels'] = fib_levels
            entry_levels['pullback_entry_1'] = fib_levels['fib_382']  # Shallow
            entry_levels['pullback_entry_2'] = fib_levels['fib_618']  # Medium
            entry_levels['pullback_entry_3'] = fib_levels['fib_786']  # Deep
    
    return entry_levels


def add_pullback_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add pullback detection features ke DataFrame
    
    Args:
        df: DataFrame dengan OHLC data
    
    Returns:
        DataFrame dengan pullback features
    """
    result = df.copy()
    
    # Detect swing points
    swing_points = detect_swing_points(df, window=5, min_swing_size=0.01)
    
    # Calculate trend
    trend = calculate_trend(df)
    
    # Detect pullback
    result = detect_pullback(result, swing_points=swing_points, trend=trend)
    
    # Detect reversal
    result = detect_reversal(result, swing_points=swing_points, trend=trend)
    
    # Detect impulse move
    result = detect_impulse_move(result)
    
    # Detect breakout
    result = detect_breakout(result)
    
    # Confirm dengan volume
    if 'Volume' in df.columns:
        result['Pullback_Signal_Confirmed'] = confirm_pullback_with_volume(
            result, result['Pullback_Signal']
        )
    else:
        result['Pullback_Signal_Confirmed'] = result['Pullback_Signal']
    
    # Add pullback features
    result['Is_Pullback'] = result['Pullback_Detected'].astype(int)
    result['Pullback_Strength'] = result['Pullback_Confidence']
    
    # Add reversal features
    result['Is_Reversal'] = result['Reversal_Detected'].astype(int)
    result['Reversal_Strength'] = result['Reversal_Confidence']
    
    # Pullback opportunity score (0-1)
    result['Pullback_Opportunity_Score'] = (
        result['Pullback_Detected'].astype(int) * 
        result['Pullback_Confidence'] *
        (result['Pullback_Signal_Confirmed'] != 0).astype(int)
    )
    
    # Reversal opportunity score (0-1)
    result['Reversal_Opportunity_Score'] = (
        result['Reversal_Detected'].astype(int) * 
        result['Reversal_Confidence'] *
        (result['Reversal_Signal'] != 0).astype(int)
    )
    
    # Add impulse move features
    result['Is_Impulse'] = result['Impulse_Detected'].astype(int)
    
    # Impulse opportunity score (0-1)
    result['Impulse_Opportunity_Score'] = (
        result['Impulse_Detected'].astype(int) * 
        result['Impulse_Confidence'] *
        (result['Impulse_Signal'] != 0).astype(int)
    )
    
    # Add breakout features
    result['Is_Breakout'] = result['Breakout_Detected'].astype(int)
    
    # Breakout opportunity score (0-1)
    result['Breakout_Opportunity_Score'] = (
        result['Breakout_Detected'].astype(int) * 
        result['Breakout_Confidence'] *
        (result['Breakout_Signal'] != 0).astype(int)
    )
    
    return result


def detect_reversal(df: pd.DataFrame,
                    swing_points: Optional[Dict] = None,
                    trend: Optional[pd.Series] = None,
                    min_reversal_retracement: float = 0.786,
                    volume_confirmation: bool = True) -> pd.DataFrame:
    """
    Detect trend reversal (bukan pullback)
    
    Reversal = Perubahan trend yang sebenarnya (bukan retracement sementara)
    
    Args:
        df: DataFrame dengan OHLC data
        swing_points: Optional pre-calculated swing points
        trend: Optional pre-calculated trend
        min_reversal_retracement: Minimum retracement untuk dianggap reversal (default 78.6%)
        volume_confirmation: Use volume untuk confirm reversal
    
    Returns:
        DataFrame dengan reversal indicators
    """
    result = df.copy()
    
    # Initialize reversal columns
    result['Reversal_Detected'] = False
    result['Reversal_Type'] = 'None'  # 'Bullish_Reversal', 'Bearish_Reversal', 'None'
    result['Reversal_Strength'] = 0.0
    result['Reversal_Signal'] = 0  # 1 = Bullish reversal (LONG), -1 = Bearish reversal (SHORT), 0 = None
    result['Reversal_Confidence'] = 0.0
    
    # Get swing points
    if swing_points is None:
        swing_points = detect_swing_points(df)
    
    # Get trend
    if trend is None:
        trend = calculate_trend(df)
    
    if len(swing_points['swing_highs']) < 2 or len(swing_points['swing_lows']) < 2:
        return result
    
    # Process each period
    for i in range(len(df)):
        if i < 5:  # Need some history
            continue
            
        current_trend = trend.iloc[i] if i < len(trend) else 0
        previous_trend = trend.iloc[i-5] if i >= 5 and i-5 < len(trend) else current_trend
        current_price = df['Close'].iloc[i]
        
        # Find recent swing points
        recent_highs = [s for s in swing_points['swing_highs'] if s['index'] <= i]
        recent_lows = [s for s in swing_points['swing_lows'] if s['index'] <= i]
        
        if len(recent_highs) < 2 or len(recent_lows) < 2:
            continue
        
        # Check for trend change (reversal)
        if previous_trend != 0 and current_trend != previous_trend:
            # Trend has changed - potential reversal
            reversal_detected = False
            reversal_type = 'None'
            reversal_signal = 0
            confidence = 0.0
            
            if previous_trend == 1 and current_trend == -1:
                # Uptrend -> Downtrend (Bearish Reversal)
                last_high = recent_highs[-1] if recent_highs else None
                last_low = recent_lows[-1] if recent_lows else None
                
                if last_high and last_low:
                    swing_range = last_high['price'] - last_low['price']
                    if swing_range > 0:
                        retracement = (last_high['price'] - current_price) / swing_range
                        
                        # Check if retracement is deep enough for reversal
                        if retracement >= min_reversal_retracement:
                            reversal_detected = True
                            reversal_type = 'Bearish_Reversal'
                            reversal_signal = -1  # SHORT signal
                            
                            # Calculate confidence based on retracement depth
                            if retracement >= 0.9:
                                confidence = 0.9  # Very strong reversal
                            elif retracement >= 0.85:
                                confidence = 0.75  # Strong reversal
                            else:
                                confidence = 0.6  # Moderate reversal
                            
                            # Volume confirmation
                            if volume_confirmation and 'Volume' in df.columns:
                                if i >= 20:
                                    current_volume = df['Volume'].iloc[i]
                                    avg_volume = df['Volume'].iloc[i-20:i].mean()
                                    volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
                                    
                                    # Reversal biasanya disertai volume tinggi
                                    if volume_ratio >= 1.2:
                                        confidence = min(1.0, confidence * 1.2)  # Boost confidence
                                    elif volume_ratio < 0.8:
                                        confidence = confidence * 0.8  # Reduce confidence
            
            elif previous_trend == -1 and current_trend == 1:
                # Downtrend -> Uptrend (Bullish Reversal)
                last_high = recent_highs[-1] if recent_highs else None
                last_low = recent_lows[-1] if recent_lows else None
                
                if last_high and last_low:
                    swing_range = last_high['price'] - last_low['price']
                    if swing_range > 0:
                        retracement = (current_price - last_low['price']) / swing_range
                        
                        # Check if retracement is deep enough for reversal
                        if retracement >= min_reversal_retracement:
                            reversal_detected = True
                            reversal_type = 'Bullish_Reversal'
                            reversal_signal = 1  # LONG signal
                            
                            # Calculate confidence based on retracement depth
                            if retracement >= 0.9:
                                confidence = 0.9
                            elif retracement >= 0.85:
                                confidence = 0.75
                            else:
                                confidence = 0.6
                            
                            # Volume confirmation
                            if volume_confirmation and 'Volume' in df.columns:
                                if i >= 20:
                                    current_volume = df['Volume'].iloc[i]
                                    avg_volume = df['Volume'].iloc[i-20:i].mean()
                                    volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
                                    
                                    if volume_ratio >= 1.2:
                                        confidence = min(1.0, confidence * 1.2)
                                    elif volume_ratio < 0.8:
                                        confidence = confidence * 0.8
            
            # Additional confirmation: Check for divergence patterns
            if reversal_detected:
                # Check if price broke through key levels
                if i >= 20:
                    ma_20 = df['Close'].rolling(window=20).mean().iloc[i]
                    ma_50 = df['Close'].rolling(window=50).mean().iloc[i] if i >= 50 else ma_20
                    
                    if reversal_type == 'Bullish_Reversal':
                        # Bullish reversal: price should break above MA
                        if current_price > ma_20:
                            confidence = min(1.0, confidence * 1.1)
                    elif reversal_type == 'Bearish_Reversal':
                        # Bearish reversal: price should break below MA
                        if current_price < ma_20:
                            confidence = min(1.0, confidence * 1.1)
            
            # Set reversal indicators
            if reversal_detected:
                result.loc[result.index[i], 'Reversal_Detected'] = True
                result.loc[result.index[i], 'Reversal_Type'] = reversal_type
                result.loc[result.index[i], 'Reversal_Signal'] = reversal_signal
                result.loc[result.index[i], 'Reversal_Confidence'] = confidence
                result.loc[result.index[i], 'Reversal_Strength'] = retracement if 'retracement' in locals() else 0.0
    
    return result


def detect_impulse_move(df: pd.DataFrame,
                       volume_threshold: float = 1.5,
                       price_change_threshold: float = 0.02,
                       window: int = 5) -> pd.DataFrame:
    """
    Detect impulse move (gerakan harga yang kuat dan cepat)
    
    Impulse Move = Gerakan harga yang kuat dalam satu arah dengan volume tinggi
    
    Args:
        df: DataFrame dengan OHLCV data
        volume_threshold: Minimum volume ratio untuk dianggap impulse (default 1.5x)
        price_change_threshold: Minimum price change untuk dianggap impulse (default 2%)
        window: Window untuk calculate price change
    
    Returns:
        DataFrame dengan impulse move indicators
    """
    result = df.copy()
    
    # Initialize impulse columns
    result['Impulse_Detected'] = False
    result['Impulse_Type'] = 'None'  # 'Bullish_Impulse', 'Bearish_Impulse', 'None'
    result['Impulse_Strength'] = 0.0
    result['Impulse_Signal'] = 0  # 1 = Bullish impulse (LONG), -1 = Bearish impulse (SHORT), 0 = None
    result['Impulse_Confidence'] = 0.0
    
    if len(df) < window + 1:
        return result
    
    # Calculate price change
    price_change = df['Close'].pct_change(window)
    price_change_abs = price_change.abs()
    
    # Calculate volume ratio
    if 'Volume' in df.columns:
        avg_volume = df['Volume'].rolling(window=20).mean()
        volume_ratio = df['Volume'] / avg_volume
    else:
        volume_ratio = pd.Series(1.0, index=df.index)
    
    # Detect impulse moves
    for i in range(window, len(df)):
        current_price_change = price_change.iloc[i]
        current_price_change_abs = price_change_abs.iloc[i]
        current_volume_ratio = volume_ratio.iloc[i] if i < len(volume_ratio) else 1.0
        
        # Check if this is an impulse move
        if (current_price_change_abs >= price_change_threshold and 
            current_volume_ratio >= volume_threshold):
            
            # Determine direction
            if current_price_change > 0:
                # Bullish impulse
                result.loc[result.index[i], 'Impulse_Detected'] = True
                result.loc[result.index[i], 'Impulse_Type'] = 'Bullish_Impulse'
                result.loc[result.index[i], 'Impulse_Signal'] = 1  # LONG
                
                # Calculate strength and confidence
                strength = min(1.0, current_price_change_abs / (price_change_threshold * 2))
                confidence = min(1.0, (current_price_change_abs * 50) * (current_volume_ratio / volume_threshold))
                
                result.loc[result.index[i], 'Impulse_Strength'] = strength
                result.loc[result.index[i], 'Impulse_Confidence'] = min(1.0, confidence)
            
            elif current_price_change < 0:
                # Bearish impulse
                result.loc[result.index[i], 'Impulse_Detected'] = True
                result.loc[result.index[i], 'Impulse_Type'] = 'Bearish_Impulse'
                result.loc[result.index[i], 'Impulse_Signal'] = -1  # SHORT
                
                # Calculate strength and confidence
                strength = min(1.0, abs(current_price_change) / (price_change_threshold * 2))
                confidence = min(1.0, (abs(current_price_change) * 50) * (current_volume_ratio / volume_threshold))
                
                result.loc[result.index[i], 'Impulse_Strength'] = strength
                result.loc[result.index[i], 'Impulse_Confidence'] = min(1.0, confidence)
    
    return result


def detect_breakout(df: pd.DataFrame,
                   support: Optional[pd.Series] = None,
                   resistance: Optional[pd.Series] = None,
                   volume_confirmation: bool = True,
                   breakout_threshold: float = 0.005) -> pd.DataFrame:
    """
    Detect breakout dari support/resistance levels
    
    Breakout = Harga yang break melalui support/resistance level yang signifikan
    
    Args:
        df: DataFrame dengan OHLCV data
        support: Optional support levels (Series)
        resistance: Optional resistance levels (Series)
        volume_confirmation: Use volume untuk confirm breakout
        breakout_threshold: Minimum distance untuk dianggap breakout (default 0.5%)
    
    Returns:
        DataFrame dengan breakout indicators
    """
    result = df.copy()
    
    # Initialize breakout columns
    result['Breakout_Detected'] = False
    result['Breakout_Type'] = 'None'  # 'Bullish_Breakout', 'Bearish_Breakout', 'None'
    result['Breakout_Level'] = 0.0
    result['Breakout_Signal'] = 0  # 1 = Bullish breakout (LONG), -1 = Bearish breakout (SHORT), 0 = None
    result['Breakout_Confidence'] = 0.0
    
    if len(df) < 20:
        return result
    
    # Calculate support/resistance jika tidak provided
    if support is None or resistance is None:
        # Use pivot points atau swing highs/lows
        swing_points = detect_swing_points(df)
        
        if len(swing_points['swing_highs']) >= 2 and len(swing_points['swing_lows']) >= 2:
            # Calculate dynamic support/resistance
            recent_highs = [s['price'] for s in swing_points['swing_highs'][-5:]]
            recent_lows = [s['price'] for s in swing_points['swing_lows'][-5:]]
            
            if support is None:
                support = pd.Series(np.nan, index=df.index)
                if recent_lows:
                    support_value = min(recent_lows)
                    support[:] = support_value
            
            if resistance is None:
                resistance = pd.Series(np.nan, index=df.index)
                if recent_highs:
                    resistance_value = max(recent_highs)
                    resistance[:] = resistance_value
    
    # Calculate volume ratio untuk confirmation
    if 'Volume' in df.columns and volume_confirmation:
        avg_volume = df['Volume'].rolling(window=20).mean()
        volume_ratio = df['Volume'] / avg_volume
    else:
        volume_ratio = pd.Series(1.0, index=df.index)
    
    # Detect breakouts
    for i in range(1, len(df)):
        current_price = df['Close'].iloc[i]
        previous_price = df['Close'].iloc[i-1]
        current_high = df['High'].iloc[i]
        current_low = df['Low'].iloc[i]
        
        current_support = support.iloc[i] if support is not None and i < len(support) else None
        current_resistance = resistance.iloc[i] if resistance is not None and i < len(resistance) else None
        current_volume_ratio = volume_ratio.iloc[i] if i < len(volume_ratio) else 1.0
        
        # Check for bullish breakout (break above resistance)
        if current_resistance is not None and pd.notna(current_resistance):
            # Breakout jika price break above resistance dengan threshold
            if (previous_price <= current_resistance and 
                current_high > current_resistance * (1 + breakout_threshold)):
                
                # Volume confirmation
                volume_confirmed = current_volume_ratio >= 1.2 if volume_confirmation else True
                
                if volume_confirmed:
                    result.loc[result.index[i], 'Breakout_Detected'] = True
                    result.loc[result.index[i], 'Breakout_Type'] = 'Bullish_Breakout'
                    result.loc[result.index[i], 'Breakout_Level'] = current_resistance
                    result.loc[result.index[i], 'Breakout_Signal'] = 1  # LONG
                    
                    # Calculate confidence
                    breakout_strength = (current_high - current_resistance) / current_resistance
                    confidence = min(1.0, (breakout_strength / breakout_threshold) * 0.5 + 
                                   (current_volume_ratio / 2.0) * 0.5)
                    result.loc[result.index[i], 'Breakout_Confidence'] = confidence
        
        # Check for bearish breakout (break below support)
        if current_support is not None and pd.notna(current_support):
            # Breakout jika price break below support dengan threshold
            if (previous_price >= current_support and 
                current_low < current_support * (1 - breakout_threshold)):
                
                # Volume confirmation
                volume_confirmed = current_volume_ratio >= 1.2 if volume_confirmation else True
                
                if volume_confirmed:
                    result.loc[result.index[i], 'Breakout_Detected'] = True
                    result.loc[result.index[i], 'Breakout_Type'] = 'Bearish_Breakout'
                    result.loc[result.index[i], 'Breakout_Level'] = current_support
                    result.loc[result.index[i], 'Breakout_Signal'] = -1  # SHORT
                    
                    # Calculate confidence
                    breakout_strength = (current_support - current_low) / current_support
                    confidence = min(1.0, (breakout_strength / breakout_threshold) * 0.5 + 
                                   (current_volume_ratio / 2.0) * 0.5)
                    result.loc[result.index[i], 'Breakout_Confidence'] = confidence
    
    return result


def get_current_reversal_status(df: pd.DataFrame) -> Dict:
    """
    Get current reversal status untuk coin
    
    Args:
        df: DataFrame dengan price data
    
    Returns:
        Dictionary dengan current reversal status
    """
    if len(df) == 0:
        return {
            'has_reversal': False,
            'reversal_type': 'None',
            'reversal_signal': 0,
            'reversal_confidence': 0.0,
            'recommendation': 'No reversal detected'
        }
    
    # Add reversal features
    df_with_reversal = add_pullback_features(df)  # Includes reversal detection
    
    # Get latest status
    latest = df_with_reversal.iloc[-1]
    
    has_reversal = latest['Reversal_Detected']
    reversal_type = latest['Reversal_Type']
    reversal_signal = latest['Reversal_Signal']
    reversal_confidence = latest['Reversal_Confidence']
    reversal_strength = latest['Reversal_Strength']
    
    # Generate recommendation
    if has_reversal:
        if reversal_signal == 1:  # Bullish reversal (LONG)
            recommendation = f"🟢 BULLISH REVERSAL detected - Trend berubah dari Bearish ke Bullish (Confidence: {reversal_confidence*100:.1f}%)"
        elif reversal_signal == -1:  # Bearish reversal (SHORT)
            recommendation = f"🔴 BEARISH REVERSAL detected - Trend berubah dari Bullish ke Bearish (Confidence: {reversal_confidence*100:.1f}%)"
        else:
            recommendation = "Reversal detected but no clear signal"
    else:
        recommendation = "No reversal detected - trend masih intact"
    
    return {
        'has_reversal': bool(has_reversal),
        'reversal_type': reversal_type,
        'reversal_signal': int(reversal_signal),
        'reversal_confidence': float(reversal_confidence),
        'reversal_strength': float(reversal_strength),
        'recommendation': recommendation,
        'current_price': float(df['Close'].iloc[-1])
    }


def get_current_pullback_status(df: pd.DataFrame) -> Dict:
    """
    Get current pullback status untuk coin (misalnya XAN)
    Includes reversal status as well
    
    Args:
        df: DataFrame dengan price data
    
    Returns:
        Dictionary dengan current pullback dan reversal status
    """
    if len(df) == 0:
        return {
            'has_pullback': False,
            'pullback_type': 'None',
            'pullback_signal': 0,
            'pullback_confidence': 0.0,
            'has_reversal': False,
            'reversal_type': 'None',
            'reversal_signal': 0,
            'reversal_confidence': 0.0,
            'recommendation': 'No pullback or reversal detected'
        }
    
    # Add pullback and reversal features
    df_with_features = add_pullback_features(df)
    
    # Get latest status
    latest = df_with_features.iloc[-1]
    
    # Pullback status
    has_pullback = latest['Pullback_Detected']
    pullback_type = latest['Pullback_Type']
    pullback_signal = latest['Pullback_Signal']
    pullback_confidence = latest['Pullback_Confidence']
    pullback_depth = latest['Pullback_Depth']
    
    # Reversal status
    has_reversal = latest['Reversal_Detected']
    reversal_type = latest['Reversal_Type']
    reversal_signal = latest['Reversal_Signal']
    reversal_confidence = latest['Reversal_Confidence']
    
    # Impulse move status
    has_impulse = latest['Impulse_Detected']
    impulse_type = latest['Impulse_Type']
    impulse_signal = latest['Impulse_Signal']
    impulse_confidence = latest['Impulse_Confidence']
    impulse_strength = latest['Impulse_Strength']
    
    # Breakout status
    has_breakout = latest['Breakout_Detected']
    breakout_type = latest['Breakout_Type']
    breakout_signal = latest['Breakout_Signal']
    breakout_confidence = latest['Breakout_Confidence']
    breakout_level = latest['Breakout_Level']
    
    # Get entry levels
    trend = calculate_trend(df).iloc[-1]
    swing_points = detect_swing_points(df)
    entry_levels = get_pullback_entry_levels(df, df['Close'].iloc[-1], int(trend), swing_points)
    
    # Generate recommendation (prioritize: reversal > breakout > impulse > pullback)
    if has_reversal:
        if reversal_signal == 1:
            recommendation = f"🟢 BULLISH REVERSAL: Trend berubah ke Bullish ({reversal_confidence*100:.1f}% confidence)"
        elif reversal_signal == -1:
            recommendation = f"🔴 BEARISH REVERSAL: Trend berubah ke Bearish ({reversal_confidence*100:.1f}% confidence)"
        else:
            recommendation = "Reversal detected but no clear signal"
    elif has_breakout:
        if breakout_signal == 1:
            recommendation = f"🚀 BULLISH BREAKOUT: Price break above resistance ${breakout_level:.6f} ({breakout_confidence*100:.1f}% confidence)"
        elif breakout_signal == -1:
            recommendation = f"📉 BEARISH BREAKOUT: Price break below support ${breakout_level:.6f} ({breakout_confidence*100:.1f}% confidence)"
        else:
            recommendation = "Breakout detected but no clear signal"
    elif has_impulse:
        if impulse_signal == 1:
            recommendation = f"⚡ BULLISH IMPULSE: Strong upward move detected ({impulse_confidence*100:.1f}% confidence, strength: {impulse_strength*100:.1f}%)"
        elif impulse_signal == -1:
            recommendation = f"⚡ BEARISH IMPULSE: Strong downward move detected ({impulse_confidence*100:.1f}% confidence, strength: {impulse_strength*100:.1f}%)"
        else:
            recommendation = "Impulse move detected but no clear signal"
    elif has_pullback:
        if pullback_signal == 1:  # LONG opportunity
            recommendation = f"LONG opportunity: {pullback_type} pullback ({pullback_depth*100:.1f}% retracement)"
        elif pullback_signal == -1:  # SHORT opportunity
            recommendation = f"SHORT opportunity: {pullback_type} pullback ({pullback_depth*100:.1f}% retracement)"
        else:
            recommendation = "Pullback detected but no clear signal"
    else:
        recommendation = "No pullback or reversal detected - wait for better entry"
    
    return {
        'has_pullback': bool(has_pullback),
        'pullback_type': pullback_type,
        'pullback_signal': int(pullback_signal),
        'pullback_confidence': float(pullback_confidence),
        'pullback_depth': float(pullback_depth),
        'has_reversal': bool(has_reversal),
        'reversal_type': reversal_type,
        'reversal_signal': int(reversal_signal),
        'reversal_confidence': float(reversal_confidence),
        'has_impulse': bool(has_impulse),
        'impulse_type': impulse_type,
        'impulse_signal': int(impulse_signal),
        'impulse_confidence': float(impulse_confidence),
        'impulse_strength': float(impulse_strength),
        'has_breakout': bool(has_breakout),
        'breakout_type': breakout_type,
        'breakout_signal': int(breakout_signal),
        'breakout_confidence': float(breakout_confidence),
        'breakout_level': float(breakout_level) if breakout_level > 0 else None,
        'entry_levels': entry_levels,
        'recommendation': recommendation,
        'current_price': float(df['Close'].iloc[-1]),
        'trend': int(trend)
    }

