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
    Prioritize Binance API untuk akurasi lebih baik (support 4h, 2h, dll)
    
    Args:
        symbol: Trading symbol (e.g., 'BTC-USD' atau 'BTCUSDT')
        current_interval: Current interval (e.g., '15m')
        higher_tf: Higher timeframe to fetch (e.g., '1h', '4h', '1d')
        days: Number of days to fetch
    
    Returns:
        DataFrame dengan higher timeframe data atau None jika error
    """
    try:
        # Coba Binance API dulu (lebih akurat, support lebih banyak timeframe)
        try:
            from src.utils.config import DATA_SOURCE, BINANCE_API_KEY, BINANCE_API_SECRET, BINANCE_API_TYPE
            from src.data.binance_api_helper import get_binance_data
            
            # Convert symbol format jika perlu (BTC-USD -> BTCUSDT)
            binance_symbol = symbol
            if '-' in symbol:
                base = symbol.split('-')[0]
                binance_symbol = f"{base}USDT"
            
            # Cek apakah DATA_SOURCE adalah binance
            if DATA_SOURCE and DATA_SOURCE.lower() == 'binance':
                print(f"📡 [MTF] Mengambil {higher_tf} data dari Binance untuk {binance_symbol}...")
                df = get_binance_data(binance_symbol, days, higher_tf, BINANCE_API_KEY, BINANCE_API_SECRET)
                
                if df is not None and not df.empty:
                    # Ensure columns are capitalized
                    if 'date' in df.columns:
                        df.set_index('date', inplace=True)
                    df.columns = [col.capitalize() for col in df.columns]
                    print(f"✅ [MTF] Berhasil mengambil {len(df)} records dari Binance ({higher_tf})")
                    return df
        except Exception as e:
            print(f"⚠️  [MTF] Binance API tidak tersedia atau error: {e}")
            print(f"   Fallback ke yfinance...")
        
        # Fallback ke yfinance
        # Map interval untuk yfinance
        interval_map = {
            '1h': '1h',
            '4h': '1h',  # yfinance tidak support 4h, gunakan 1h
            '2h': '1h',  # yfinance tidak support 2h, gunakan 1h
            '1d': '1d',
            '1w': '1wk',
            '1mo': '1mo'
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


def analyze_timeframe_trend(df: pd.DataFrame, ma_short: int = 10, ma_long: int = 20) -> Dict:
    """
    Analyze trend untuk satu timeframe
    
    Args:
        df: DataFrame dengan OHLC data
        ma_short: Short moving average window
        ma_long: Long moving average window
    
    Returns:
        Dictionary dengan trend analysis
    """
    if df.empty or len(df) < ma_long:
        return {
            'trend': 'Unknown',
            'trend_signal': 0,
            'trend_strength': 0.0,
            'price_vs_ma': 0.0,
            'ma_alignment': False
        }
    
    # Calculate MAs
    ma_short_val = df['Close'].rolling(window=ma_short).mean().iloc[-1]
    ma_long_val = df['Close'].rolling(window=ma_long).mean().iloc[-1]
    current_price = df['Close'].iloc[-1]
    
    # Trend direction
    if pd.isna(ma_short_val) or pd.isna(ma_long_val):
        trend = 'Unknown'
        trend_signal = 0
    elif ma_short_val > ma_long_val:
        trend = 'Bullish'
        trend_signal = 1
    else:
        trend = 'Bearish'
        trend_signal = -1
    
    # Trend strength (distance between MAs)
    if ma_long_val > 0:
        trend_strength = abs(ma_short_val - ma_long_val) / ma_long_val * 100
    else:
        trend_strength = 0.0
    
    # Price vs MA
    if ma_short_val > 0:
        price_vs_ma = (current_price - ma_short_val) / ma_short_val * 100
    else:
        price_vs_ma = 0.0
    
    # MA alignment (price > short MA > long MA for bullish, reverse for bearish)
    ma_alignment = False
    if trend_signal == 1:
        ma_alignment = current_price > ma_short_val > ma_long_val
    elif trend_signal == -1:
        ma_alignment = current_price < ma_short_val < ma_long_val
    
    return {
        'trend': trend,
        'trend_signal': trend_signal,
        'trend_strength': trend_strength,
        'price_vs_ma': price_vs_ma,
        'ma_alignment': ma_alignment,
        'ma_short': ma_short_val,
        'ma_long': ma_long_val,
        'current_price': current_price
    }


def calculate_support_resistance_levels(df: pd.DataFrame, window: int = 20) -> Dict:
    """
    Calculate support and resistance levels dari satu timeframe
    
    Args:
        df: DataFrame dengan OHLC data
        window: Window untuk mencari local extrema
    
    Returns:
        Dictionary dengan support/resistance levels
    """
    if df.empty or len(df) < window:
        return {
            'support': None,
            'resistance': None,
            'support_strength': 0,
            'resistance_strength': 0
        }
    
    # Local minima (support) dan maxima (resistance)
    recent_data = df.tail(window * 2)
    
    # Support: local minima
    support_levels = recent_data['Low'].rolling(window=window, center=True).min()
    support = support_levels.min() if not support_levels.empty else None
    
    # Resistance: local maxima
    resistance_levels = recent_data['High'].rolling(window=window, center=True).max()
    resistance = resistance_levels.max() if not resistance_levels.empty else None
    
    # Strength: berapa kali level di-test
    if support is not None:
        support_touches = (recent_data['Low'] <= support * 1.01).sum()
        support_strength = min(support_touches / window * 100, 100)
    else:
        support_strength = 0
    
    if resistance is not None:
        resistance_touches = (recent_data['High'] >= resistance * 0.99).sum()
        resistance_strength = min(resistance_touches / window * 100, 100)
    else:
        resistance_strength = 0
    
    return {
        'support': float(support) if support is not None else None,
        'resistance': float(resistance) if resistance is not None else None,
        'support_strength': float(support_strength),
        'resistance_strength': float(resistance_strength)
    }


def analyze_multiple_timeframes(symbol: str, current_df: pd.DataFrame, 
                                current_interval: str) -> Dict:
    """
    Comprehensive multiple timeframe analysis
    
    Args:
        symbol: Trading symbol
        current_df: Current timeframe DataFrame
        current_interval: Current timeframe (e.g., '15m', '1h', '4h')
    
    Returns:
        Dictionary dengan multiple timeframe analysis
    """
    result = {
        'timeframes': {},
        'alignment_score': 0.0,
        'overall_trend': 'Unknown',
        'trend_consensus': 0,
        'support_resistance': {},
        'confidence': 0.0
    }
    
    # Determine timeframes to analyze
    # Current TF, Higher TF (4x), Highest TF (16x)
    tf_hierarchy = {
        'current': current_interval,
        'higher': None,
        'highest': None
    }
    
    # Map intervals untuk higher timeframes
    interval_map = {
        '1m': {'higher': '5m', 'highest': '15m'},
        '5m': {'higher': '15m', 'highest': '1h'},
        '15m': {'higher': '1h', 'highest': '4h'},
        '30m': {'higher': '2h', 'highest': '1d'},
        '1h': {'higher': '4h', 'highest': '1d'},
        '2h': {'higher': '4h', 'highest': '1d'},
        '4h': {'higher': '1d', 'highest': '1w'},
        '1d': {'higher': '1w', 'highest': '1mo'}
    }
    
    # Get higher timeframes
    if current_interval in interval_map:
        tf_hierarchy['higher'] = interval_map[current_interval]['higher']
        tf_hierarchy['highest'] = interval_map[current_interval]['highest']
    
    # Analyze current timeframe
    print(f"\n🔍 [MULTI-TIMEFRAME] Starting analysis untuk {symbol}")
    print(f"   Current TF: {current_interval}")
    
    current_analysis = analyze_timeframe_trend(current_df)
    current_sr = calculate_support_resistance_levels(current_df)
    result['timeframes']['current'] = {
        'interval': current_interval,
        'trend': current_analysis,
        'support_resistance': current_sr
    }
    print(f"   ✅ Current TF ({current_interval}): Trend={current_analysis.get('trend', 'Unknown')}, Signal={current_analysis.get('trend_signal', 0)}")
    
    # Analyze higher timeframe
    if tf_hierarchy['higher']:
        print(f"   📡 Mencoba mengambil Higher TF: {tf_hierarchy['higher']}...")
        try:
            higher_df = get_higher_timeframe_data(symbol, current_interval, tf_hierarchy['higher'])
            if higher_df is not None and not higher_df.empty:
                higher_analysis = analyze_timeframe_trend(higher_df)
                higher_sr = calculate_support_resistance_levels(higher_df)
                result['timeframes']['higher'] = {
                    'interval': tf_hierarchy['higher'],
                    'trend': higher_analysis,
                    'support_resistance': higher_sr
                }
                print(f"   ✅ Higher TF ({tf_hierarchy['higher']}): Trend={higher_analysis.get('trend', 'Unknown')}, Signal={higher_analysis.get('trend_signal', 0)}")
            else:
                print(f"   ❌ Higher TF ({tf_hierarchy['higher']}): Data kosong atau None")
        except Exception as e:
            print(f"   ❌ Error analyzing higher timeframe: {e}")
    else:
        print(f"   ⚠️  Higher TF tidak ditentukan untuk interval {current_interval}")
    
    # Analyze highest timeframe
    if tf_hierarchy['highest']:
        print(f"   📡 Mencoba mengambil Highest TF: {tf_hierarchy['highest']}...")
        try:
            highest_df = get_higher_timeframe_data(symbol, current_interval, tf_hierarchy['highest'])
            if highest_df is not None and not highest_df.empty:
                highest_analysis = analyze_timeframe_trend(highest_df)
                highest_sr = calculate_support_resistance_levels(highest_df)
                result['timeframes']['highest'] = {
                    'interval': tf_hierarchy['highest'],
                    'trend': highest_analysis,
                    'support_resistance': highest_sr
                }
                print(f"   ✅ Highest TF ({tf_hierarchy['highest']}): Trend={highest_analysis.get('trend', 'Unknown')}, Signal={highest_analysis.get('trend_signal', 0)}")
            else:
                print(f"   ❌ Highest TF ({tf_hierarchy['highest']}): Data kosong atau None")
        except Exception as e:
            print(f"   ❌ Error analyzing highest timeframe: {e}")
    else:
        print(f"   ⚠️  Highest TF tidak ditentukan untuk interval {current_interval}")
    
    # Summary
    tf_count = len(result['timeframes'])
    print(f"   📊 Total timeframes berhasil dianalisis: {tf_count}/3 (current + higher + highest)")
    if tf_count < 3:
        print(f"   ⚠️  Warning: Hanya {tf_count} timeframe yang berhasil, mungkin higher/highest TF gagal diambil")
    
    # Calculate alignment score
    trend_signals = []
    for tf_name, tf_data in result['timeframes'].items():
        trend_signal = tf_data['trend'].get('trend_signal', 0)
        if trend_signal != 0:
            trend_signals.append(trend_signal)
    
    if trend_signals:
        # Consensus: semua TF harus align
        if all(s == trend_signals[0] for s in trend_signals):
            result['trend_consensus'] = trend_signals[0]
            result['alignment_score'] = 100.0
            result['overall_trend'] = 'Bullish' if trend_signals[0] == 1 else 'Bearish'
        else:
            # Partial alignment
            bullish_count = sum(1 for s in trend_signals if s == 1)
            bearish_count = sum(1 for s in trend_signals if s == -1)
            if bullish_count > bearish_count:
                result['trend_consensus'] = 1
                result['overall_trend'] = 'Bullish'
            elif bearish_count > bullish_count:
                result['trend_consensus'] = -1
                result['overall_trend'] = 'Bearish'
            else:
                result['trend_consensus'] = 0
                result['overall_trend'] = 'Mixed'
            
            # Alignment score berdasarkan persentase TF yang align
            result['alignment_score'] = max(bullish_count, bearish_count) / len(trend_signals) * 100
    
    # Calculate confidence
    # Confidence = alignment_score * trend_strength_weight
    if result['timeframes']:
        avg_trend_strength = np.mean([
            tf_data['trend'].get('trend_strength', 0)
            for tf_data in result['timeframes'].values()
        ])
        result['confidence'] = result['alignment_score'] * (1 + min(avg_trend_strength / 10, 0.5))
        result['confidence'] = min(result['confidence'], 100.0)
    
    # Aggregate support/resistance (prioritize higher timeframes)
    all_supports = []
    all_resistances = []
    
    for tf_name in ['highest', 'higher', 'current']:
        if tf_name in result['timeframes']:
            sr = result['timeframes'][tf_name]['support_resistance']
            if sr.get('support'):
                all_supports.append({
                    'level': sr['support'],
                    'strength': sr['support_strength'],
                    'timeframe': result['timeframes'][tf_name]['interval']
                })
            if sr.get('resistance'):
                all_resistances.append({
                    'level': sr['resistance'],
                    'strength': sr['resistance_strength'],
                    'timeframe': result['timeframes'][tf_name]['interval']
                })
    
    # Sort by strength and timeframe priority
    if all_supports:
        all_supports.sort(key=lambda x: (x['strength'], x['timeframe']), reverse=True)
        result['support_resistance']['primary_support'] = all_supports[0]
        result['support_resistance']['all_supports'] = all_supports
    
    if all_resistances:
        all_resistances.sort(key=lambda x: (x['strength'], x['timeframe']), reverse=True)
        result['support_resistance']['primary_resistance'] = all_resistances[0]
        result['support_resistance']['all_resistances'] = all_resistances
    
    return result


def get_market_context(df: pd.DataFrame, symbol: str, current_interval: str) -> Dict:
    """
    Get comprehensive market context dengan multiple timeframe analysis
    
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
    
    # Multiple timeframe analysis
    try:
        mtf_analysis = analyze_multiple_timeframes(symbol, df, current_interval)
        context['multiple_timeframe'] = mtf_analysis
        context['mtf_alignment_score'] = mtf_analysis.get('alignment_score', 0)
        context['mtf_overall_trend'] = mtf_analysis.get('overall_trend', 'Unknown')
        context['mtf_confidence'] = mtf_analysis.get('confidence', 0)
        context['mtf_trend_consensus'] = mtf_analysis.get('trend_consensus', 0)
    except Exception as e:
        print(f"⚠️  Error in multiple timeframe analysis: {e}")
        context['multiple_timeframe'] = {}
        context['mtf_alignment_score'] = 0
        context['mtf_overall_trend'] = 'Unknown'
        context['mtf_confidence'] = 0
        context['mtf_trend_consensus'] = 0
    
    # Higher timeframe trend (legacy, untuk backward compatibility)
    higher_tf_data = get_higher_timeframe_data(symbol, current_interval, '1h')
    if higher_tf_data is not None and len(higher_tf_data) > 0:
        higher_tf_trend = 'Up' if higher_tf_data['Close'].iloc[-1] > higher_tf_data['Close'].iloc[-20] else 'Down'
        context['higher_tf_trend'] = higher_tf_trend
    else:
        context['higher_tf_trend'] = 'Unknown'
    
    return context

