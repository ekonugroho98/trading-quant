"""
Volume Analysis Module
Implementasi analisis volume untuk trading quant
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple


def calculate_vwap(df: pd.DataFrame, period: Optional[int] = None) -> pd.Series:
    """
    Calculate Volume-Weighted Average Price (VWAP)
    
    Args:
        df: DataFrame dengan kolom High, Low, Close, Volume
        period: Period untuk rolling VWAP (None = cumulative)
    
    Returns:
        Series dengan VWAP values
    """
    if 'Volume' not in df.columns:
        return pd.Series(index=df.index, dtype=float)
    
    # Typical Price = (High + Low + Close) / 3
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    price_volume = typical_price * df['Volume']
    
    if period is None:
        # Cumulative VWAP
        vwap = price_volume.cumsum() / df['Volume'].cumsum()
    else:
        # Rolling VWAP
        vwap = price_volume.rolling(window=period).sum() / df['Volume'].rolling(window=period).sum()
    
    return vwap


def analyze_volume_pattern(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """
    Analyze volume patterns
    
    Returns:
        DataFrame dengan kolom volume analysis
    """
    if 'Volume' not in df.columns:
        return df
    
    result = df.copy()
    
    # Volume moving average
    result['Volume_MA'] = df['Volume'].rolling(window=window).mean()
    
    # Volume ratio (current volume vs average)
    result['Volume_Ratio'] = df['Volume'] / result['Volume_MA']
    
    # Volume trend (increasing/decreasing)
    result['Volume_Trend'] = df['Volume'].rolling(window=5).apply(
        lambda x: 1 if x.iloc[-1] > x.iloc[0] else -1, raw=False
    )
    
    # Volume classification
    result['Volume_Class'] = pd.cut(
        result['Volume_Ratio'],
        bins=[0, 0.5, 1.0, 1.5, np.inf],
        labels=['Very Low', 'Low', 'Normal', 'High']
    )
    
    return result


def detect_volume_spike(df: pd.DataFrame, threshold: float = 2.0, window: int = 20) -> pd.Series:
    """
    Detect volume spikes
    
    Args:
        df: DataFrame dengan kolom Volume
        threshold: Multiplier dari average volume untuk dianggap spike
        window: Window untuk menghitung average volume
    
    Returns:
        Series boolean: True jika volume spike terdeteksi
    """
    if 'Volume' not in df.columns:
        return pd.Series(index=df.index, dtype=bool)
    
    volume_ma = df['Volume'].rolling(window=window).mean()
    volume_spike = df['Volume'] > (volume_ma * threshold)
    
    return volume_spike


def calculate_volume_profile(df: pd.DataFrame, bins: int = 20) -> Dict:
    """
    Calculate volume profile (volume at price levels)
    
    Args:
        df: DataFrame dengan kolom High, Low, Close, Volume
        bins: Number of price bins
    
    Returns:
        Dictionary dengan volume profile data
    """
    if 'Volume' not in df.columns:
        return {}
    
    # Price range
    price_min = df['Low'].min()
    price_max = df['High'].max()
    
    # Create price bins
    price_bins = np.linspace(price_min, price_max, bins + 1)
    
    # Distribute volume to price levels
    volume_profile = np.zeros(bins)
    
    for idx, row in df.iterrows():
        # Distribute volume proportionally across price range
        price_range = row['High'] - row['Low']
        if price_range > 0:
            # Find which bins this bar covers
            bin_start = np.searchsorted(price_bins, row['Low'])
            bin_end = np.searchsorted(price_bins, row['High'])
            
            for bin_idx in range(bin_start, min(bin_end, bins)):
                # Proportional volume allocation
                volume_profile[bin_idx] += row['Volume'] / (bin_end - bin_start)
    
    # Find POC (Point of Control) - price level with highest volume
    poc_idx = np.argmax(volume_profile)
    poc_price = (price_bins[poc_idx] + price_bins[poc_idx + 1]) / 2
    
    return {
        'price_bins': price_bins,
        'volume_profile': volume_profile,
        'poc_price': poc_price,
        'poc_volume': volume_profile[poc_idx]
    }


def get_volume_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Get all volume indicators
    
    Returns:
        DataFrame dengan semua volume indicators
    """
    result = df.copy()
    
    # VWAP
    result['VWAP'] = calculate_vwap(df)
    result['VWAP_20'] = calculate_vwap(df, period=20)
    
    # Volume patterns
    result = analyze_volume_pattern(result)
    
    # Volume spikes
    result['Volume_Spike'] = detect_volume_spike(df)
    
    # Volume momentum
    if 'Volume' in df.columns:
        result['Volume_Momentum'] = df['Volume'].pct_change(periods=5)
    
    return result

