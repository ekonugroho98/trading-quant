"""
Market Context Module
Implementasi analisis market context untuk trading quant
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
import yfinance as yf


def get_higher_timeframe_data(symbol: str, current_interval: str, 
                               higher_tf: str = '1h', days: int = 30) -> Optional[pd.DataFrame]:
    """
    Get higher timeframe data for context
    
    Args:
        symbol: Trading symbol (e.g., 'BTC-USD')
        current_interval: Current interval (e.g., '15m')
        higher_tf: Higher timeframe to fetch (e.g., '1h', '4h', '1d')
        days: Number of days to fetch
    
    Returns:
        DataFrame dengan higher timeframe data atau None jika error
    """
    try:
        # Map interval untuk yfinance
        interval_map = {
            '1h': '1h',
            '4h': '1h',  # yfinance tidak support 4h, gunakan 1h
            '1d': '1d'
        }
        
        yf_interval = interval_map.get(higher_tf, '1h')
        
        ticker = yf.Ticker(symbol)
        df = ticker.history(interval=yf_interval, period=f'{days}d')
        
        if df.empty:
            return None
        
        # Rename columns untuk konsistensi
        df.columns = [col.capitalize() for col in df.columns]
        
        return df
    except Exception as e:
        print(f"⚠️  Error fetching higher timeframe data: {e}")
        return None


def analyze_market_regime(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """
    Analyze market regime (trending vs ranging)
    
    Returns:
        DataFrame dengan market regime indicators
    """
    result = df.copy()
    
    # Calculate ADX-like indicator (trend strength)
    high_low = df['High'] - df['Low']
    high_close = abs(df['High'] - df['Close'].shift(1))
    low_close = abs(df['Low'] - df['Close'].shift(1))
    
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(window=window).mean()
    
    # Price movement
    price_change = df['Close'].pct_change()
    price_volatility = price_change.rolling(window=window).std()
    
    # Trend direction
    sma_short = df['Close'].rolling(window=10).mean()
    sma_long = df['Close'].rolling(window=20).mean()
    trend_direction = np.where(sma_short > sma_long, 1, -1)
    
    # Regime classification
    # Trending: high volatility + strong trend
    # Ranging: low volatility + weak trend
    volatility_ratio = price_volatility / price_volatility.rolling(window=window*2).mean()
    trend_strength = abs(sma_short - sma_long) / df['Close']
    
    result['ATR'] = atr
    result['Trend_Direction'] = trend_direction
    result['Trend_Strength'] = trend_strength
    result['Volatility_Ratio'] = volatility_ratio
    
    # Regime classification
    result['Market_Regime'] = pd.cut(
        trend_strength,
        bins=[0, 0.01, 0.03, np.inf],
        labels=['Ranging', 'Weak Trend', 'Strong Trend']
    )
    
    return result


def analyze_volatility_regime(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """
    Analyze volatility regime (high/medium/low volatility)
    
    Returns:
        DataFrame dengan volatility regime indicators
    """
    result = df.copy()
    
    # Calculate volatility (rolling std of returns)
    returns = df['Close'].pct_change()
    volatility = returns.rolling(window=window).std()
    
    # Historical volatility percentile
    vol_percentile = volatility.rolling(window=window*2).apply(
        lambda x: (x.iloc[-1] > x.quantile(0.75)) * 2 + 
                  (x.iloc[-1] > x.quantile(0.25)) * 1,
        raw=False
    )
    
    # Volatility regime classification
    result['Volatility'] = volatility
    result['Volatility_Percentile'] = vol_percentile
    
    result['Volatility_Regime'] = pd.cut(
        vol_percentile,
        bins=[0, 0.5, 1.5, 2.5, np.inf],
        labels=['Very Low', 'Low', 'Medium', 'High']
    )
    
    return result


def calculate_correlation(df: pd.DataFrame, other_symbols: list, 
                          window: int = 20) -> pd.DataFrame:
    """
    Calculate correlation with other assets
    
    Args:
        df: Current asset DataFrame
        other_symbols: List of other symbols to correlate with
        window: Rolling window for correlation
    
    Returns:
        DataFrame dengan correlation data
    """
    result = df.copy()
    
    current_returns = df['Close'].pct_change()
    
    for symbol in other_symbols:
        try:
            ticker = yf.Ticker(symbol)
            other_df = ticker.history(period='1mo')
            
            if not other_df.empty:
                other_returns = other_df['Close'].pct_change()
                
                # Align indices
                aligned = pd.DataFrame({
                    'current': current_returns,
                    'other': other_returns
                }).dropna()
                
                if len(aligned) > window:
                    correlation = aligned['current'].rolling(window=window).corr(
                        aligned['other']
                    )
                    result[f'Corr_{symbol.replace("-", "_")}'] = correlation
        except Exception as e:
            print(f"⚠️  Error calculating correlation with {symbol}: {e}")
    
    return result


def get_market_context(df: pd.DataFrame, symbol: str, current_interval: str) -> Dict:
    """
    Get comprehensive market context
    
    Returns:
        Dictionary dengan market context data
    """
    context = {}
    
    # Market regime
    df_regime = analyze_market_regime(df)
    context['current_regime'] = df_regime['Market_Regime'].iloc[-1] if 'Market_Regime' in df_regime.columns else 'Unknown'
    context['trend_direction'] = int(df_regime['Trend_Direction'].iloc[-1]) if 'Trend_Direction' in df_regime.columns else 0
    
    # Volatility regime
    df_vol = analyze_volatility_regime(df)
    context['volatility_regime'] = df_vol['Volatility_Regime'].iloc[-1] if 'Volatility_Regime' in df_vol.columns else 'Unknown'
    
    # Higher timeframe trend
    higher_tf_data = get_higher_timeframe_data(symbol, current_interval, '1h')
    if higher_tf_data is not None and len(higher_tf_data) > 0:
        higher_tf_trend = 'Up' if higher_tf_data['Close'].iloc[-1] > higher_tf_data['Close'].iloc[-20] else 'Down'
        context['higher_tf_trend'] = higher_tf_trend
    else:
        context['higher_tf_trend'] = 'Unknown'
    
    return context

