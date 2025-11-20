"""
Enhanced Feature Engineering Module
Time-based features, multi-timeframe features, seasonality, dll
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, List
import warnings
warnings.filterwarnings('ignore')


def add_time_based_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tambahkan time-based features (hour, day of week, month, dll)
    
    Args:
        df: DataFrame dengan datetime index
    
    Returns:
        DataFrame dengan time-based features
    """
    result = df.copy()
    
    if not isinstance(df.index, pd.DatetimeIndex):
        if 'date' in df.columns:
            df.index = pd.to_datetime(df['date'])
        else:
            print("⚠️  Index bukan DatetimeIndex, skip time-based features")
            return result
    
    # Hour of day
    result['Hour'] = df.index.hour
    
    # Day of week (0=Monday, 6=Sunday)
    result['DayOfWeek'] = df.index.dayofweek
    
    # Is weekend
    result['IsWeekend'] = (result['DayOfWeek'] >= 5).astype(int)
    
    # Day of month
    result['DayOfMonth'] = df.index.day
    
    # Month
    result['Month'] = df.index.month
    
    # Quarter
    result['Quarter'] = df.index.quarter
    
    # Week of year
    result['WeekOfYear'] = df.index.isocalendar().week
    
    # Cyclical encoding untuk hour (sin/cos)
    result['Hour_Sin'] = np.sin(2 * np.pi * result['Hour'] / 24)
    result['Hour_Cos'] = np.cos(2 * np.pi * result['Hour'] / 24)
    
    # Cyclical encoding untuk day of week
    result['DayOfWeek_Sin'] = np.sin(2 * np.pi * result['DayOfWeek'] / 7)
    result['DayOfWeek_Cos'] = np.cos(2 * np.pi * result['DayOfWeek'] / 7)
    
    # Cyclical encoding untuk month
    result['Month_Sin'] = np.sin(2 * np.pi * result['Month'] / 12)
    result['Month_Cos'] = np.cos(2 * np.pi * result['Month'] / 12)
    
    return result


def add_multi_timeframe_features(df: pd.DataFrame,
                                timeframes: Optional[List[str]] = None,
                                current_interval: Optional[str] = None) -> pd.DataFrame:
    """
    Tambahkan features dari multiple timeframes
    
    Args:
        df: DataFrame dengan OHLCV data
        timeframes: List of timeframes untuk resample (default: auto berdasarkan current_interval)
        current_interval: Current interval untuk auto-determine higher timeframes
    
    Returns:
        DataFrame dengan multi-timeframe features
    """
    result = df.copy()
    
    if 'Close' not in df.columns:
        print("⚠️  Kolom 'Close' tidak ditemukan, skip multi-timeframe features")
        return result
    
    # Auto-determine timeframes jika tidak provided
    if timeframes is None:
        if current_interval:
            # Map current interval ke higher timeframes
            interval_map = {
                '1m': ['5m', '15m', '1h', '4h'],
                '5m': ['15m', '1h', '4h', '1d'],
                '15m': ['1h', '4h', '1d'],
                '30m': ['1h', '4h', '1d'],
                '1h': ['4h', '1d'],
                '2h': ['4h', '1d'],
                '4h': ['1d'],
                '1d': []  # No higher timeframe
            }
            timeframes = interval_map.get(current_interval.lower(), ['1h', '4h', '1d'])
        else:
            # Default timeframes
            timeframes = ['1h', '4h', '1d']
    
    # Filter timeframes yang valid (harus lebih besar dari current interval)
    if current_interval:
        # Convert interval ke minutes untuk comparison
        def interval_to_minutes(interval: str) -> int:
            if interval.endswith('m'):
                return int(interval[:-1])
            elif interval.endswith('h'):
                return int(interval[:-1]) * 60
            elif interval.endswith('d'):
                return int(interval[:-1]) * 1440
            return 0
        
        current_minutes = interval_to_minutes(current_interval)
        timeframes = [tf for tf in timeframes if interval_to_minutes(tf) > current_minutes]
    
    if not timeframes:
        return result
    
    for tf in timeframes:
        try:
            # Resample ke timeframe
            if isinstance(df.index, pd.DatetimeIndex):
                resampled = df.resample(tf).agg({
                    'Close': 'last',
                    'High': 'max' if 'High' in df.columns else 'last',
                    'Low': 'min' if 'Low' in df.columns else 'last',
                    'Volume': 'sum' if 'Volume' in df.columns else 'last',
                    'Open': 'first' if 'Open' in df.columns else 'last'
                })
            else:
                # Jika bukan DatetimeIndex, skip
                continue
            
            # Calculate features untuk timeframe ini
            ma_20 = resampled['Close'].rolling(window=20).mean()
            ma_50 = resampled['Close'].rolling(window=50).mean()
            ma_200 = resampled['Close'].rolling(window=200).mean() if len(resampled) >= 200 else None
            rsi = calculate_rsi(resampled['Close'], period=14)
            
            # Volatility
            volatility = resampled['Close'].rolling(window=20).std()
            
            # Forward fill ke original timeframe
            result[f'MA_20_{tf}'] = ma_20.reindex(df.index, method='ffill')
            result[f'MA_50_{tf}'] = ma_50.reindex(df.index, method='ffill')
            if ma_200 is not None:
                result[f'MA_200_{tf}'] = ma_200.reindex(df.index, method='ffill')
            result[f'RSI_{tf}'] = rsi.reindex(df.index, method='ffill')
            result[f'Volatility_{tf}'] = volatility.reindex(df.index, method='ffill')
            
            # Price relative to higher timeframe MA
            result[f'Price_MA20_Ratio_{tf}'] = df['Close'] / result[f'MA_20_{tf}']
            result[f'Price_MA50_Ratio_{tf}'] = df['Close'] / result[f'MA_50_{tf}']
            if ma_200 is not None:
                result[f'Price_MA200_Ratio_{tf}'] = df['Close'] / result[f'MA_200_{tf}']
            
            # Trend alignment (semua MA naik = bullish, semua turun = bearish)
            if ma_200 is not None:
                result[f'Trend_Alignment_{tf}'] = (
                    (result[f'MA_20_{tf}'] > result[f'MA_50_{tf}']).astype(int) +
                    (result[f'MA_50_{tf}'] > result[f'MA_200_{tf}']).astype(int)
                ) / 2.0  # 0 = bearish, 1 = bullish, 0.5 = mixed
            
        except Exception as e:
            print(f"⚠️  Error processing timeframe {tf}: {e}")
            continue
    
    return result


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Calculate RSI"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def detect_seasonality(df: pd.DataFrame, 
                      column: str = 'Close',
                      period: Optional[int] = None) -> Dict:
    """
    Detect seasonality dalam time series
    
    Args:
        df: DataFrame dengan time series data
        column: Column name untuk analyze
        period: Period untuk seasonal decomposition (default: auto-detect)
    
    Returns:
        Dictionary dengan seasonal components
    """
    try:
        from statsmodels.tsa.seasonal import seasonal_decompose
    except ImportError:
        print("⚠️  statsmodels tidak tersedia untuk seasonal decomposition")
        return {}
    
    if column not in df.columns:
        print(f"⚠️  Kolom {column} tidak ditemukan")
        return {}
    
    series = df[column].dropna()
    
    if len(series) < 50:
        print("⚠️  Data terlalu sedikit untuk seasonal decomposition")
        return {}
    
    # Auto-detect period jika tidak specified
    if period is None:
        # Default: 24 untuk hourly data, 7 untuk daily data
        if pd.infer_freq(series.index) == 'H':
            period = 24
        elif pd.infer_freq(series.index) == 'D':
            period = 7
        else:
            period = min(24, len(series) // 2)
    
    try:
        decomposition = seasonal_decompose(
            series,
            model='multiplicative',
            period=period,
            extrapolate_trend='freq'
        )
        
        return {
            'trend': decomposition.trend,
            'seasonal': decomposition.seasonal,
            'residual': decomposition.resid,
            'period': period
        }
    except Exception as e:
        print(f"⚠️  Error dalam seasonal decomposition: {e}")
        return {}


def add_seasonal_features(df: pd.DataFrame,
                        column: str = 'Close') -> pd.DataFrame:
    """
    Tambahkan seasonal features ke DataFrame
    
    Args:
        df: DataFrame dengan time series data
        column: Column name untuk analyze
    
    Returns:
        DataFrame dengan seasonal features
    """
    result = df.copy()
    
    seasonal_result = detect_seasonality(df, column=column)
    
    if seasonal_result:
        # Add seasonal components
        result['Seasonal_Trend'] = seasonal_result['trend']
        result['Seasonal_Component'] = seasonal_result['seasonal']
        result['Seasonal_Residual'] = seasonal_result['residual']
        
        # Forward fill NaN values
        result['Seasonal_Trend'] = result['Seasonal_Trend'].fillna(method='ffill').fillna(method='bfill')
        result['Seasonal_Component'] = result['Seasonal_Component'].fillna(method='ffill').fillna(method='bfill')
        result['Seasonal_Residual'] = result['Seasonal_Residual'].fillna(method='ffill').fillna(method='bfill')
        
        # Cyclical features dari seasonal component
        if len(result) > 0:
            # Normalize seasonal component untuk cyclical encoding
            seasonal_norm = (result['Seasonal_Component'] - result['Seasonal_Component'].min()) / (
                result['Seasonal_Component'].max() - result['Seasonal_Component'].min() + 1e-8
            )
            result['Seasonal_Sin'] = np.sin(2 * np.pi * seasonal_norm)
            result['Seasonal_Cos'] = np.cos(2 * np.pi * seasonal_norm)
    
    return result


def add_rolling_window_features(df: pd.DataFrame,
                               windows: List[int] = [5, 10, 20, 50, 100]) -> pd.DataFrame:
    """
    Tambahkan rolling window features dengan multiple window sizes
    
    Args:
        df: DataFrame dengan price data
        windows: List of window sizes
    
    Returns:
        DataFrame dengan rolling features
    """
    result = df.copy()
    
    if 'Close' not in df.columns:
        return result
    
    for window in windows:
        if len(df) >= window:
            # Moving averages
            result[f'MA_{window}'] = df['Close'].rolling(window=window).mean()
            result[f'EMA_{window}'] = df['Close'].ewm(span=window, adjust=False).mean()
            
            # Volatility
            result[f'Std_{window}'] = df['Close'].rolling(window=window).std()
            result[f'Volatility_{window}'] = result[f'Std_{window}'] / result[f'MA_{window}']
            
            # Momentum
            result[f'Momentum_{window}'] = df['Close'].pct_change(window)
            
            # Price ratios
            result[f'Price_MA_{window}_Ratio'] = df['Close'] / result[f'MA_{window}']
    
    return result


def add_garch_volatility_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tambahkan GARCH volatility features
    
    Args:
        df: DataFrame dengan returns data
    
    Returns:
        DataFrame dengan GARCH features
    """
    result = df.copy()
    
    try:
        from src.models.time_series_models import fit_garch_model
    except ImportError:
        print("⚠️  time_series_models tidak tersedia, skip GARCH features")
        return result
    
    if 'Return' not in df.columns:
        if 'Close' in df.columns:
            result['Return'] = df['Close'].pct_change()
        else:
            print("⚠️  Tidak ada kolom 'Return' atau 'Close', skip GARCH features")
            return result
    
    # Fit GARCH model
    garch_result = fit_garch_model(result['Return'], p=1, q=1)
    
    if garch_result and 'conditional_volatility' in garch_result:
        result['GARCH_Volatility'] = garch_result['conditional_volatility']
        result['GARCH_Volatility'] = result['GARCH_Volatility'].fillna(method='ffill').fillna(method='bfill')
    
    return result


def create_enhanced_features(df: pd.DataFrame,
                           include_time_features: bool = True,
                           include_multi_tf: bool = True,
                           include_seasonal: bool = True,
                           include_rolling: bool = True,
                           include_garch: bool = True,
                           include_pullback: bool = True) -> pd.DataFrame:
    """
    Create semua enhanced features
    
    Args:
        df: DataFrame dengan OHLCV data
        include_time_features: Include time-based features
        include_multi_tf: Include multi-timeframe features
        include_seasonal: Include seasonal features
        include_rolling: Include rolling window features
        include_garch: Include GARCH volatility
        include_pullback: Include pullback detection features
    
    Returns:
        DataFrame dengan semua enhanced features
    """
    result = df.copy()
    
    # Time-based features
    if include_time_features:
        result = add_time_based_features(result)
    
    # Multi-timeframe features
    if include_multi_tf:
        result = add_multi_timeframe_features(result)
    
    # Rolling window features
    if include_rolling:
        result = add_rolling_window_features(result)
    
    # Seasonal features
    if include_seasonal:
        result = add_seasonal_features(result)
    
    # GARCH volatility
    if include_garch:
        result = add_garch_volatility_features(result)
    
    # Pullback detection features
    if include_pullback:
        try:
            from src.utils.pullback_detection import add_pullback_features
            result = add_pullback_features(result)
        except Exception as e:
            print(f"⚠️  Error adding pullback features: {e}")
    
    return result

