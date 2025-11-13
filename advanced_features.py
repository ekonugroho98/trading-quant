"""
Advanced Feature Engineering Module
Implementasi feature engineering lanjutan untuk trading quant
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from scipy import signal
from scipy.fft import fft


def mean_reversion_indicators(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """
    Calculate mean-reversion indicators
    
    Returns:
        DataFrame dengan mean-reversion indicators
    """
    result = df.copy()
    
    # Z-score (deviation from mean)
    sma = df['Close'].rolling(window=window).mean()
    std = df['Close'].rolling(window=window).std()
    result['Z_Score'] = (df['Close'] - sma) / std
    
    # Bollinger Bands position
    bb_upper = sma + (std * 2)
    bb_lower = sma - (std * 2)
    result['BB_Position'] = (df['Close'] - bb_lower) / (bb_upper - bb_lower)
    
    # RSI (Relative Strength Index)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    result['RSI'] = 100 - (100 / (1 + rs))
    
    # Mean reversion signal
    result['Mean_Reversion_Signal'] = np.where(
        (result['Z_Score'] < -2) | (result['RSI'] < 30), 1,  # Oversold
        np.where((result['Z_Score'] > 2) | (result['RSI'] > 70), -1, 0)  # Overbought
    )
    
    return result


def cycle_detection(df: pd.DataFrame, min_period: int = 5, max_period: int = 50) -> pd.DataFrame:
    """
    Detect cycles in price data using FFT
    
    Returns:
        DataFrame dengan cycle indicators
    """
    result = df.copy()
    
    # Use returns for cycle detection
    returns = df['Close'].pct_change().dropna()
    
    if len(returns) < max_period * 2:
        result['Cycle_Period'] = np.nan
        result['Cycle_Phase'] = 0
        return result
    
    # FFT untuk detect dominant cycle
    fft_values = fft(returns.values[-max_period*2:])
    frequencies = np.fft.fftfreq(len(fft_values))
    power = np.abs(fft_values)
    
    # Find dominant frequency (exclude DC component)
    dominant_idx = np.argmax(power[1:max_period]) + 1
    dominant_period = int(len(fft_values) / abs(frequencies[dominant_idx]))
    
    # Clamp period
    dominant_period = max(min_period, min(dominant_period, max_period))
    
    result['Cycle_Period'] = dominant_period
    
    # Calculate cycle phase (0-360 degrees)
    if dominant_period > 0:
        phase = (np.arange(len(df)) % dominant_period) / dominant_period * 360
        result['Cycle_Phase'] = phase
    else:
        result['Cycle_Phase'] = 0
    
    return result


def pattern_recognition(df: pd.DataFrame) -> pd.DataFrame:
    """
    Recognize common chart patterns
    
    Returns:
        DataFrame dengan pattern indicators
    """
    result = df.copy()
    
    # Head and Shoulders detection (simplified)
    # Look for local maxima pattern
    if len(df) >= 20:
        highs = df['High'].rolling(window=5).max()
        local_maxima = signal.argrelextrema(highs.values, np.greater, order=3)[0]
        
        # Simple pattern: three peaks with middle one highest
        if len(local_maxima) >= 3:
            peaks = highs.iloc[local_maxima[-3:]].values
            if peaks[1] > peaks[0] and peaks[1] > peaks[2]:
                result['Pattern_HnS'] = True
            else:
                result['Pattern_HnS'] = False
        else:
            result['Pattern_HnS'] = False
    else:
        result['Pattern_HnS'] = False
    
    # Double Top/Bottom detection
    if len(df) >= 20:
        # Look for two similar highs/lows
        recent_highs = df['High'].rolling(window=10).max()
        recent_lows = df['Low'].rolling(window=10).min()
        
        # Check if last two highs are similar (within 2%)
        if len(recent_highs) >= 20:
            last_two_highs = recent_highs.iloc[-10:].nlargest(2).values
            if len(last_two_highs) == 2:
                similarity = abs(last_two_highs[0] - last_two_highs[1]) / last_two_highs[0]
                result['Pattern_DoubleTop'] = similarity < 0.02
            else:
                result['Pattern_DoubleTop'] = False
        else:
            result['Pattern_DoubleTop'] = False
        
        # Check if last two lows are similar
        if len(recent_lows) >= 20:
            last_two_lows = recent_lows.iloc[-10:].nsmallest(2).values
            if len(last_two_lows) == 2:
                similarity = abs(last_two_lows[0] - last_two_lows[1]) / last_two_lows[0]
                result['Pattern_DoubleBottom'] = similarity < 0.02
            else:
                result['Pattern_DoubleBottom'] = False
        else:
            result['Pattern_DoubleBottom'] = False
    else:
        result['Pattern_DoubleTop'] = False
        result['Pattern_DoubleBottom'] = False
    
    return result


def market_microstructure_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate market microstructure features
    
    Returns:
        DataFrame dengan microstructure features
    """
    result = df.copy()
    
    # Price efficiency (how much price moves vs how much it should)
    returns = df['Close'].pct_change()
    volatility = returns.rolling(window=20).std()
    
    # Realized vs expected volatility
    expected_vol = volatility.shift(1)
    efficiency = abs(returns) / (expected_vol + 1e-8)
    result['Price_Efficiency'] = efficiency
    
    # Tick direction (up/down)
    result['Tick_Direction'] = np.where(df['Close'] > df['Close'].shift(1), 1, -1)
    
    # Price impact (how much volume moves price)
    if 'Volume' in df.columns:
        price_change = abs(df['Close'].pct_change())
        volume_normalized = df['Volume'] / df['Volume'].rolling(window=20).mean()
        result['Price_Impact'] = price_change / (volume_normalized + 1e-8)
    else:
        result['Price_Impact'] = 0
    
    # Spread proxy (high-low range relative to close)
    result['Spread_Proxy'] = (df['High'] - df['Low']) / df['Close']
    
    return result


def get_all_advanced_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Get all advanced features
    
    Returns:
        DataFrame dengan semua advanced features
    """
    result = df.copy()
    
    # Mean reversion
    result = mean_reversion_indicators(result)
    
    # Cycle detection
    result = cycle_detection(result)
    
    # Pattern recognition
    result = pattern_recognition(result)
    
    # Microstructure
    result = market_microstructure_features(result)
    
    return result

