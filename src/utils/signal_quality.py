"""
Signal Quality Module
Signal confidence scoring, filtering, dan validation
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger('signal_quality')


def calculate_signal_confidence(signal: int,
                               indicators: Dict[str, float],
                               weights: Optional[Dict[str, float]] = None) -> float:
    """
    Calculate signal confidence score berdasarkan multiple indicators
    
    Args:
        signal: Trading signal (1 = buy, -1 = sell, 0 = neutral)
        indicators: Dictionary dengan indicator values
        weights: Optional weights untuk indicators
    
    Returns:
        Confidence score (0.0 - 1.0)
    """
    if signal == 0:
        return 0.0
    
    if weights is None:
        # Default equal weights
        weights = {key: 1.0 / len(indicators) for key in indicators.keys()}
    
    confidence = 0.0
    
    # Normalize indicators to 0-1 range
    for indicator_name, indicator_value in indicators.items():
        weight = weights.get(indicator_name, 0.0)
        
        # Normalize based on indicator type
        if 'rsi' in indicator_name.lower():
            # RSI: 0-100, convert to confidence
            if signal == 1:  # Buy signal
                # RSI < 30 = high confidence, RSI > 70 = low confidence
                normalized = max(0, (70 - indicator_value) / 40)
            else:  # Sell signal
                # RSI > 70 = high confidence, RSI < 30 = low confidence
                normalized = max(0, (indicator_value - 30) / 40)
        
        elif 'macd' in indicator_name.lower() or 'signal' in indicator_name.lower():
            # MACD: positive = bullish, negative = bearish
            if signal == 1:  # Buy signal
                normalized = max(0, min(1, (indicator_value + 1) / 2))
            else:  # Sell signal
                normalized = max(0, min(1, (-indicator_value + 1) / 2))
        
        elif 'zscore' in indicator_name.lower():
            # Z-score: absolute value indicates strength
            normalized = min(1.0, abs(indicator_value) / 3.0)
        
        elif 'volume' in indicator_name.lower():
            # Volume: higher = more confidence
            normalized = min(1.0, indicator_value / 2.0)  # Assume 2x = max
        
        else:
            # Default: use absolute value normalized
            normalized = min(1.0, abs(indicator_value))
        
        confidence += weight * normalized
    
    return min(1.0, max(0.0, confidence))


def filter_signals_by_confidence(signals: pd.Series,
                                 confidence_scores: pd.Series,
                                 min_confidence: float = 0.5) -> pd.Series:
    """
    Filter signals berdasarkan confidence score
    
    Args:
        signals: Trading signals
        confidence_scores: Confidence scores untuk each signal
        min_confidence: Minimum confidence threshold
    
    Returns:
        Filtered signals (0 if confidence too low)
    """
    filtered = signals.copy()
    low_confidence = confidence_scores < min_confidence
    filtered[low_confidence] = 0
    return filtered


def validate_signal_with_volume(signal: int,
                               volume: float,
                               avg_volume: float,
                               min_volume_ratio: float = 0.8) -> bool:
    """
    Validate signal dengan volume confirmation
    
    Args:
        signal: Trading signal
        volume: Current volume
        avg_volume: Average volume
        min_volume_ratio: Minimum volume ratio untuk validation
    
    Returns:
        True if signal is valid
    """
    if signal == 0:
        return True
    
    volume_ratio = volume / avg_volume if avg_volume > 0 else 0
    return volume_ratio >= min_volume_ratio


def filter_signals_by_market_conditions(signals: pd.Series,
                                       market_regime: pd.Series,
                                       volatility_regime: pd.Series,
                                       trend_direction: pd.Series) -> pd.Series:
    """
    Filter signals berdasarkan market conditions
    
    Args:
        signals: Trading signals
        market_regime: Market regime ('trending', 'ranging')
        volatility_regime: Volatility regime ('high', 'low', 'normal')
        trend_direction: Trend direction (1 = up, -1 = down, 0 = neutral)
    
    Returns:
        Filtered signals
    """
    filtered = signals.copy()
    
    # Filter based on market regime
    # In ranging market, reduce signal strength
    ranging_market = market_regime == 'ranging'
    filtered[ranging_market] = filtered[ranging_market] * 0.5
    
    # Filter based on volatility
    # In high volatility, be more conservative
    high_vol = volatility_regime == 'high'
    filtered[high_vol] = filtered[high_vol] * 0.7
    
    # Filter based on trend alignment
    # Only take signals aligned with trend
    misaligned = (signals == 1) & (trend_direction == -1) | (signals == -1) & (trend_direction == 1)
    filtered[misaligned] = filtered[misaligned] * 0.3
    
    # Round to nearest signal value
    filtered = filtered.round().astype(int)
    filtered = filtered.clip(-1, 1)
    
    return filtered


def calculate_dynamic_threshold(signals: pd.Series,
                               returns: pd.Series,
                               window: int = 30,
                               min_threshold: float = 0.5,
                               max_threshold: float = 0.7) -> float:
    """
    Calculate dynamic threshold berdasarkan historical performance
    
    Args:
        signals: Trading signals
        returns: Returns series
        window: Window untuk calculate performance
        min_threshold: Minimum threshold
        max_threshold: Maximum threshold
    
    Returns:
        Optimal threshold
    """
    if len(signals) < window or len(returns) < window:
        return min_threshold
    
    # Test berbagai threshold
    best_threshold = min_threshold
    best_sharpe = -np.inf
    
    for threshold in np.arange(min_threshold, max_threshold + 0.01, 0.01):
        # Filter signals dengan threshold
        filtered_signals = signals.copy()
        filtered_signals[filtered_signals < threshold] = 0
        
        # Calculate returns untuk filtered signals
        strategy_returns = returns[filtered_signals != 0]
        
        if len(strategy_returns) > 10:
            # Calculate Sharpe ratio
            if strategy_returns.std() > 0:
                sharpe = strategy_returns.mean() / strategy_returns.std() * np.sqrt(252)
                if sharpe > best_sharpe:
                    best_sharpe = sharpe
                    best_threshold = threshold
    
    return best_threshold


def multi_signal_confirmation(ml_signal: int,
                             technical_signal: int,
                             volume_confirmed: bool,
                             market_aligned: bool,
                             require_all: bool = False) -> Tuple[int, float]:
    """
    Multi-signal confirmation - hanya ambil signal jika multiple sources konfirmasi
    
    Args:
        ml_signal: Signal dari ML model (1, -1, 0)
        technical_signal: Signal dari technical indicators (1, -1, 0)
        volume_confirmed: Volume confirmation
        market_aligned: Market alignment
        require_all: True = semua harus konfirmasi, False = minimal 2 dari 4
    
    Returns:
        Tuple of (confirmed_signal, confidence_score)
    """
    if ml_signal == 0:
        return (0, 0.0)
    
    confirmations = 0
    total_checks = 4
    
    # Check ML signal
    if ml_signal != 0:
        confirmations += 1
    
    # Check technical signal alignment
    if technical_signal == ml_signal:
        confirmations += 1
    
    # Check volume confirmation
    if volume_confirmed:
        confirmations += 1
    
    # Check market alignment
    if market_aligned:
        confirmations += 1
    
    # Determine if signal is confirmed
    if require_all:
        confirmed = (confirmations == total_checks)
    else:
        confirmed = (confirmations >= 2)  # Minimal 2 dari 4
    
    if confirmed:
        confidence = confirmations / total_checks
        return (ml_signal, confidence)
    else:
        return (0, confirmations / total_checks)  # No signal, tapi return confidence untuk info


def apply_signal_decay(signals: pd.Series,
                       decay_rate: float = 0.1,
                       max_age: int = 10) -> pd.Series:
    """
    Apply signal decay over time - signal yang lebih fresh lebih reliable
    
    Args:
        signals: Trading signals
        decay_rate: Decay rate per period
        max_age: Maximum age sebelum signal dianggap expired
    
    Returns:
        Signals dengan decay applied
    """
    decayed_signals = signals.copy()
    
    for i in range(len(signals)):
        if signals.iloc[i] != 0:
            # Check how long signal has been active
            age = 0
            for j in range(i-1, max(0, i-max_age)-1, -1):
                if signals.iloc[j] == signals.iloc[i]:
                    age += 1
                else:
                    break
            
            # Apply decay
            if age > 0:
                decay_factor = (1 - decay_rate) ** age
                decayed_signals.iloc[i] = signals.iloc[i] * decay_factor
    
    return decayed_signals


def calculate_signal_quality_score(signal: int,
                                   confidence: float,
                                   volume_confirmed: bool,
                                   market_aligned: bool) -> float:
    """
    Calculate overall signal quality score
    
    Args:
        signal: Trading signal
        confidence: Confidence score
        volume_confirmed: Whether volume confirms signal
        market_aligned: Whether signal aligns with market conditions
    
    Returns:
        Quality score (0.0 - 1.0)
    """
    if signal == 0:
        return 0.0
    
    quality = confidence
    
    # Adjust based on volume confirmation
    if volume_confirmed:
        quality *= 1.2
    else:
        quality *= 0.8
    
    # Adjust based on market alignment
    if market_aligned:
        quality *= 1.1
    else:
        quality *= 0.9
    
    return min(1.0, max(0.0, quality))


def enhance_signals_with_quality(df: pd.DataFrame,
                                signal_column: str = 'Signal',
                                min_confidence: float = 0.5,
                                require_volume_confirmation: bool = True) -> pd.DataFrame:
    """
    Enhance signals dengan quality scoring dan filtering
    
    Args:
        df: DataFrame dengan signals dan indicators
        signal_column: Name of signal column
        min_confidence: Minimum confidence threshold
        require_volume_confirmation: Whether to require volume confirmation
    
    Returns:
        DataFrame dengan enhanced signals
    """
    df = df.copy()
    
    if signal_column not in df.columns:
        logger.warning(f"Signal column {signal_column} not found")
        return df
    
    # Calculate confidence scores
    confidence_scores = pd.Series(0.0, index=df.index)
    
    for idx in df.index:
        signal = df.loc[idx, signal_column]
        
        # Extract indicators
        indicators = {}
        if 'RSI' in df.columns:
            indicators['rsi'] = df.loc[idx, 'RSI']
        if 'MACD' in df.columns:
            indicators['macd'] = df.loc[idx, 'MACD']
        if 'Z_Score' in df.columns:
            indicators['zscore'] = df.loc[idx, 'Z_Score']
        if 'Volume_Ratio' in df.columns:
            indicators['volume'] = df.loc[idx, 'Volume_Ratio']
        
        if indicators:
            confidence_scores.loc[idx] = calculate_signal_confidence(
                signal, indicators
            )
    
    df['Signal_Confidence'] = confidence_scores
    
    # Filter by confidence
    if min_confidence > 0:
        df['Signal_Filtered'] = filter_signals_by_confidence(
            df[signal_column], confidence_scores, min_confidence
        )
    else:
        df['Signal_Filtered'] = df[signal_column]
    
    # Volume confirmation
    if require_volume_confirmation and 'Volume' in df.columns:
        avg_volume = df['Volume'].rolling(window=20).mean()
        volume_confirmed = pd.Series(False, index=df.index)
        
        for idx in df.index:
            signal = df.loc[idx, signal_column]
            volume = df.loc[idx, 'Volume']
            avg_vol = avg_volume.loc[idx] if pd.notna(avg_volume.loc[idx]) else volume
            
            volume_confirmed.loc[idx] = validate_signal_with_volume(
                signal, volume, avg_vol
            )
        
        df['Volume_Confirmed'] = volume_confirmed
        # Filter signals without volume confirmation
        df.loc[~volume_confirmed, 'Signal_Filtered'] = 0
    
    # Calculate quality score
    quality_scores = pd.Series(0.0, index=df.index)
    for idx in df.index:
        signal = df.loc[idx, signal_column]
        confidence = confidence_scores.loc[idx]
        volume_conf = df.loc[idx, 'Volume_Confirmed'] if 'Volume_Confirmed' in df.columns else True
        market_align = True  # Simplified for now
        
        quality_scores.loc[idx] = calculate_signal_quality_score(
            signal, confidence, volume_conf, market_align
        )
    
    df['Signal_Quality'] = quality_scores
    
    return df

