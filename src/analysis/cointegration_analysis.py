"""
Cointegration Analysis Module
Implementasi cointegration untuk pairs trading dan statistical arbitrage
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional, List
import warnings
warnings.filterwarnings('ignore')


def calculate_cointegration(series1: pd.Series, series2: pd.Series) -> Dict:
    """
    Calculate cointegration between two time series using Engle-Granger test
    
    Args:
        series1: First time series
        series2: Second time series
    
    Returns:
        Dictionary dengan cointegration results
    """
    try:
        from statsmodels.tsa.stattools import coint
    except ImportError:
        print("⚠️  statsmodels tidak terinstall. Install dengan: pip install statsmodels")
        return {}
    
    # Remove NaN values and align series
    df = pd.DataFrame({'series1': series1, 'series2': series2}).dropna()
    
    if len(df) < 50:
        print("⚠️  Data terlalu sedikit untuk cointegration analysis (minimal 50 data points)")
        return {}
    
    s1 = df['series1']
    s2 = df['series2']
    
    # Run cointegration test
    try:
        score, pvalue, _ = coint(s1, s2)
        
        # Calculate hedge ratio (beta) using OLS
        from sklearn.linear_model import LinearRegression
        X = s1.values.reshape(-1, 1)
        y = s2.values
        model = LinearRegression()
        model.fit(X, y)
        hedge_ratio = model.coef_[0]
        intercept = model.intercept_
        
        # Calculate spread
        spread = s2 - (hedge_ratio * s1 + intercept)
        
        # Calculate spread statistics
        spread_mean = spread.mean()
        spread_std = spread.std()
        spread_zscore = (spread.iloc[-1] - spread_mean) / spread_std if spread_std != 0 else 0
        
        # Half-life of mean reversion
        spread_lag = spread.shift(1)
        spread_diff = spread - spread_lag
        spread_lag = spread_lag.dropna()
        spread_diff = spread_diff.dropna()
        
        if len(spread_lag) > 0 and len(spread_diff) > 0:
            # Align indices
            common_idx = spread_lag.index.intersection(spread_diff.index)
            if len(common_idx) > 0:
                X_half = spread_lag.loc[common_idx].values.reshape(-1, 1)
                y_half = spread_diff.loc[common_idx].values
                
                half_life_model = LinearRegression()
                half_life_model.fit(X_half, y_half)
                theta = half_life_model.coef_[0]
                
                if theta < 0:
                    half_life = -np.log(2) / theta
                else:
                    half_life = None
            else:
                half_life = None
        else:
            half_life = None
        
        return {
            'cointegrated': pvalue < 0.05,  # 95% confidence
            'pvalue': pvalue,
            'test_statistic': score,
            'hedge_ratio': hedge_ratio,
            'intercept': intercept,
            'spread': spread,
            'spread_mean': spread_mean,
            'spread_std': spread_std,
            'spread_zscore': spread_zscore,
            'half_life': half_life,
            'correlation': s1.corr(s2)
        }
    except Exception as e:
        print(f"⚠️  Error dalam cointegration test: {e}")
        return {}


def find_cointegrated_pairs(price_data: Dict[str, pd.Series], 
                            min_pvalue: float = 0.05) -> List[Dict]:
    """
    Find cointegrated pairs from multiple time series
    
    Args:
        price_data: Dictionary dengan symbol -> price series
        min_pvalue: Maximum p-value untuk cointegration (default 0.05)
    
    Returns:
        List of dictionaries dengan cointegrated pairs
    """
    symbols = list(price_data.keys())
    cointegrated_pairs = []
    
    for i in range(len(symbols)):
        for j in range(i + 1, len(symbols)):
            symbol1 = symbols[i]
            symbol2 = symbols[j]
            
            series1 = price_data[symbol1]
            series2 = price_data[symbol2]
            
            result = calculate_cointegration(series1, series2)
            
            if result and result.get('cointegrated', False) and result.get('pvalue', 1) < min_pvalue:
                cointegrated_pairs.append({
                    'pair': (symbol1, symbol2),
                    'pvalue': result['pvalue'],
                    'test_statistic': result['test_statistic'],
                    'hedge_ratio': result['hedge_ratio'],
                    'correlation': result.get('correlation', 0),
                    'half_life': result.get('half_life'),
                    'spread_zscore': result.get('spread_zscore', 0)
                })
    
    # Sort by p-value (most significant first)
    cointegrated_pairs.sort(key=lambda x: x['pvalue'])
    
    return cointegrated_pairs


def calculate_spread_signals(spread: pd.Series, 
                             entry_threshold: float = 2.0,
                             exit_threshold: float = 0.5) -> pd.Series:
    """
    Calculate trading signals based on spread z-score
    
    Args:
        spread: Spread series
        entry_threshold: Z-score threshold untuk entry (default 2.0)
        exit_threshold: Z-score threshold untuk exit (default 0.5)
    
    Returns:
        Series dengan signals (1 = long spread, -1 = short spread, 0 = neutral)
    """
    spread_mean = spread.mean()
    spread_std = spread.std()
    
    if spread_std == 0:
        return pd.Series(0, index=spread.index)
    
    zscore = (spread - spread_mean) / spread_std
    
    signals = pd.Series(0, index=spread.index)
    
    # Long spread (buy spread) when z-score < -entry_threshold
    signals[zscore < -entry_threshold] = 1
    
    # Short spread (sell spread) when z-score > entry_threshold
    signals[zscore > entry_threshold] = -1
    
    # Exit when z-score returns to near zero
    signals[(zscore.abs() < exit_threshold) & (signals != 0)] = 0
    
    return signals


def print_cointegration_results(results: Dict, symbol1: str, symbol2: str):
    """Print cointegration analysis results"""
    if not results:
        return
    
    print("\n" + "=" * 70)
    print(f"📊 COINTEGRATION ANALYSIS: {symbol1} vs {symbol2}")
    print("=" * 70)
    
    print(f"\n✅ Cointegrated: {'Yes' if results.get('cointegrated', False) else 'No'}")
    print(f"   P-value: {results.get('pvalue', 0):.4f}")
    print(f"   Test Statistic: {results.get('test_statistic', 0):.4f}")
    
    print(f"\n📈 Hedge Ratio: {results.get('hedge_ratio', 0):.4f}")
    print(f"   Intercept: {results.get('intercept', 0):.4f}")
    print(f"   Correlation: {results.get('correlation', 0):.4f}")
    
    print(f"\n📊 Spread Statistics:")
    print(f"   Mean: {results.get('spread_mean', 0):.4f}")
    print(f"   Std: {results.get('spread_std', 0):.4f}")
    print(f"   Current Z-Score: {results.get('spread_zscore', 0):.2f}")
    
    if results.get('half_life'):
        print(f"   Half-Life: {results.get('half_life', 0):.1f} periods")
    
    print("\n" + "=" * 70)

