"""
Collect Analysis Data Module
Mengumpulkan semua data analisis untuk dikirim ke DeepSeek AI
"""

from typing import Dict, Any, Optional
import pandas as pd


def collect_analysis_data(data: pd.DataFrame, 
                         market_context: Dict,
                         enhanced_metrics: Dict,
                         ml_prediction: Optional[Dict] = None) -> Dict:
    """
    Collect semua data analisis menjadi satu dictionary
    
    Args:
        data: DataFrame dengan semua data analisis
        market_context: Dictionary dengan market context
        enhanced_metrics: Dictionary dengan enhanced validation metrics
        ml_prediction: Dictionary dengan ML prediction results (optional)
    
    Returns:
        Dictionary dengan semua data analisis
    """
    analysis_results = {}
    
    # Basic Info
    try:
        from config import TRADING_STYLE, SYMBOL, get_interval
        analysis_results['basic_info'] = {
            'symbol': SYMBOL,
            'trading_style': TRADING_STYLE,
            'interval': get_interval(),
            'total_records': len(data),
            'period': f"{data.index.min()} sampai {data.index.max()}"
        }
    except:
        analysis_results['basic_info'] = {
            'symbol': 'N/A',
            'trading_style': 'N/A',
            'interval': 'N/A',
            'total_records': len(data),
            'period': f"{data.index.min()} sampai {data.index.max()}"
        }
    
    # Current Position
    last_idx = data.index[-1]
    last_signal = data['Signal'].iloc[-1] if 'Signal' in data.columns else 0
    # Ambil nilai dengan presisi penuh, jangan bulatkan
    last_close_raw = data['Close'].iloc[-1]
    last_close = float(last_close_raw) if pd.notna(last_close_raw) else None
    last_ma_short = float(data['MA_short'].iloc[-1]) if 'MA_short' in data.columns and pd.notna(data['MA_short'].iloc[-1]) else None
    last_ma_long = float(data['MA_long'].iloc[-1]) if 'MA_long' in data.columns and pd.notna(data['MA_long'].iloc[-1]) else None
    
    signal_text = "BELI" if last_signal == 1 else ("JUAL" if last_signal == -1 else "NETRAL")
    
    # Support/Resistance - ambil dengan presisi penuh
    last_support = None
    last_resistance = None
    support_dist = None
    resistance_dist = None
    
    if 'Support' in data.columns:
        try:
            last_support_val = data['Support'].iloc[-1]
            if pd.notna(last_support_val):
                if isinstance(last_support_val, pd.Series):
                    last_support = float(last_support_val.iloc[0])
                else:
                    # Ambil nilai langsung tanpa pembulatan
                    last_support = float(last_support_val)
                support_dist = ((last_close - last_support) / last_close * 100) if last_close > 0 else 0
        except:
            pass
    
    if 'Resistance' in data.columns:
        try:
            last_resistance_val = data['Resistance'].iloc[-1]
            if pd.notna(last_resistance_val):
                if isinstance(last_resistance_val, pd.Series):
                    last_resistance = float(last_resistance_val.iloc[0])
                else:
                    # Ambil nilai langsung tanpa pembulatan
                    last_resistance = float(last_resistance_val)
                resistance_dist = ((last_resistance - last_close) / last_close * 100) if last_close > 0 else 0
        except:
            pass
    
    analysis_results['current_position'] = {
        'position': signal_text,
        'current_price': last_close,
        'ma_short': last_ma_short,
        'ma_long': last_ma_long,
        'support': last_support,
        'support_distance': f"{support_dist:.2f}%" if support_dist is not None else None,
        'resistance': last_resistance,
        'resistance_distance': f"{resistance_dist:.2f}%" if resistance_dist is not None else None
    }
    
    # Strategy Performance
    buy_periods = (data['Signal'] == 1).sum() if 'Signal' in data.columns else 0
    sell_periods = (data['Signal'] == -1).sum() if 'Signal' in data.columns else 0
    neutral_periods = (data['Signal'] == 0).sum() if 'Signal' in data.columns else 0
    total_periods = len(data)
    
    buy_hold_return = ((data['Cumulative_BuyHold'].iloc[-1] - 1) * 100) if 'Cumulative_BuyHold' in data.columns else 0
    strategy_return = ((data['Cumulative_Strategy'].iloc[-1] - 1) * 100) if 'Cumulative_Strategy' in data.columns else 0
    
    crossover_buy = data['Buy_Signal'].sum() if 'Buy_Signal' in data.columns else 0
    crossover_sell = data['Sell_Signal'].sum() if 'Sell_Signal' in data.columns else 0
    
    analysis_results['strategy_performance'] = {
        'buy_hold_return': f"{buy_hold_return:.2f}%",
        'strategy_return': f"{strategy_return:.2f}%",
        'buy_periods': buy_periods,
        'buy_periods_pct': f"{buy_periods/total_periods*100:.1f}%",
        'sell_periods': sell_periods,
        'sell_periods_pct': f"{sell_periods/total_periods*100:.1f}%",
        'neutral_periods': neutral_periods,
        'neutral_periods_pct': f"{neutral_periods/total_periods*100:.1f}%",
        'buy_signals': int(crossover_buy),
        'sell_signals': int(crossover_sell)
    }
    
    # Trading Setup (jika ada)
    # Ini akan diisi dari analisis_quant.py setelah generate_trading_setup dipanggil
    
    # Volume Analysis
    if 'VWAP' in data.columns:
        last_vwap = float(data['VWAP'].iloc[-1]) if pd.notna(data['VWAP'].iloc[-1]) else None
        price_vs_vwap = ((last_close - last_vwap) / last_vwap * 100) if last_vwap else None
        
        last_vol_ratio = float(data['Volume_Ratio'].iloc[-1]) if 'Volume_Ratio' in data.columns and pd.notna(data['Volume_Ratio'].iloc[-1]) else None
        volume_spikes = int(data['Volume_Spike'].sum()) if 'Volume_Spike' in data.columns else 0
        volume_class = str(data['Volume_Class'].iloc[-1]) if 'Volume_Class' in data.columns and pd.notna(data['Volume_Class'].iloc[-1]) else None
        
        analysis_results['volume_analysis'] = {
            'vwap': last_vwap,
            'price_vs_vwap': f"{price_vs_vwap:.2f}%" if price_vs_vwap else None,
            'volume_ratio': f"{last_vol_ratio:.2f}x" if last_vol_ratio else None,
            'volume_spikes': volume_spikes,
            'volume_class': volume_class
        }
    
    # Market Context
    if market_context:
        analysis_results['market_context'] = {
            'market_regime': str(market_context.get('current_regime', 'Unknown')),
            'trend_direction': 'Up' if market_context.get('trend_direction', 0) > 0 else 'Down' if market_context.get('trend_direction', 0) < 0 else 'Neutral',
            'volatility_regime': str(market_context.get('volatility_regime', 'Unknown')),
            'higher_tf_trend': str(market_context.get('higher_tf_trend', 'Unknown'))
        }
    
    # Advanced Features
    advanced_features = {}
    if 'Z_Score' in data.columns:
        last_z = float(data['Z_Score'].iloc[-1]) if pd.notna(data['Z_Score'].iloc[-1]) else None
        advanced_features['z_score'] = last_z
    
    if 'RSI' in data.columns:
        last_rsi = float(data['RSI'].iloc[-1]) if pd.notna(data['RSI'].iloc[-1]) else None
        advanced_features['rsi'] = last_rsi
    
    if 'Cycle_Period' in data.columns:
        cycle_period = float(data['Cycle_Period'].iloc[-1]) if pd.notna(data['Cycle_Period'].iloc[-1]) else None
        advanced_features['cycle_period'] = cycle_period
    
    patterns = {}
    if 'Pattern_HnS' in data.columns:
        patterns['Head_and_Shoulders'] = bool(data['Pattern_HnS'].iloc[-1]) if pd.notna(data['Pattern_HnS'].iloc[-1]) else False
    if 'Pattern_DoubleTop' in data.columns:
        patterns['Double_Top'] = bool(data['Pattern_DoubleTop'].iloc[-1]) if pd.notna(data['Pattern_DoubleTop'].iloc[-1]) else False
    if 'Pattern_DoubleBottom' in data.columns:
        patterns['Double_Bottom'] = bool(data['Pattern_DoubleBottom'].iloc[-1]) if pd.notna(data['Pattern_DoubleBottom'].iloc[-1]) else False
    
    if patterns:
        advanced_features['patterns'] = patterns
    
    if advanced_features:
        analysis_results['advanced_features'] = advanced_features
    
    # Validation Metrics
    if enhanced_metrics:
        analysis_results['validation_metrics'] = enhanced_metrics
    
    # ML Prediction
    if ml_prediction:
        analysis_results['ml_prediction'] = ml_prediction
    
    return analysis_results


def add_trading_setup_to_analysis(analysis_results: Dict, trading_setup: Dict):
    """
    Add trading setup data ke analysis results
    
    Args:
        analysis_results: Dictionary dengan analysis results
        trading_setup: Dictionary dengan trading setup dari generate_trading_setup
    """
    if trading_setup:
        analysis_results['trading_setup'] = {
            'direction': trading_setup.get('direction', 'N/A'),
            'action': trading_setup.get('action', 'N/A'),
            'limit_entry': trading_setup.get('limit_entry', 'N/A'),
            'stop_loss': trading_setup.get('stop_loss', 'N/A'),
            'stop_loss_pct': trading_setup.get('stop_loss_pct', 'N/A'),
            'targets': trading_setup.get('targets', []),
            'risk_reward': trading_setup.get('risk_reward_ratios', [])
        }

