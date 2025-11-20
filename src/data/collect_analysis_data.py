"""
Collect Analysis Data Module
Mengumpulkan semua data analisis untuk dikirim ke DeepSeek AI
"""

from typing import Dict, Any, Optional
import pandas as pd


def collect_analysis_data(data: pd.DataFrame, 
                         market_context: Dict,
                         enhanced_metrics: Dict,
                         ml_prediction: Optional[Dict] = None,
                         recent_trades_analysis: Optional[Dict] = None,
                         open_interest_analysis: Optional[Dict] = None,
                         orderbook_analysis: Optional[Dict] = None) -> Dict:
    """
    Collect semua data analisis menjadi satu dictionary
    
    Args:
        data: DataFrame dengan semua data analisis
        market_context: Dictionary dengan market context
        enhanced_metrics: Dictionary dengan enhanced validation metrics
        ml_prediction: Dictionary dengan ML prediction results (optional)
        recent_trades_analysis: Dictionary dengan recent trades analysis (optional)
        open_interest_analysis: Dictionary dengan open interest analysis (optional)
        orderbook_analysis: Dictionary dengan orderbook depth analysis (optional)
    
    Returns:
        Dictionary dengan semua data analisis
    """
    analysis_results = {}
    
    # Basic Info
    try:
        from src.utils.config import TRADING_STYLE, SYMBOL, get_interval
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
        try:
            # Ensure trend_direction is a scalar, not a Series
            trend_dir = market_context.get('trend_direction', 0)
            if isinstance(trend_dir, pd.Series):
                trend_dir = float(trend_dir.iloc[0]) if len(trend_dir) > 0 else 0
            else:
                trend_dir = float(trend_dir) if trend_dir is not None else 0
            
            trend_text = 'Up' if trend_dir > 0 else 'Down' if trend_dir < 0 else 'Neutral'
        except:
            trend_text = 'Neutral'
        
        market_context_data = {
            'market_regime': str(market_context.get('current_regime', 'Unknown')),
            'trend_direction': trend_text,
            'volatility_regime': str(market_context.get('volatility_regime', 'Unknown')),
            'higher_tf_trend': str(market_context.get('higher_tf_trend', 'Unknown'))
        }
        
        # Tambahkan Multiple Timeframe Analysis jika ada
        if 'multiple_timeframe' in market_context:
            mtf = market_context['multiple_timeframe']
            
            # Debug: cek apakah ada data timeframes
            has_timeframes = 'timeframes' in mtf and mtf['timeframes']
            print(f"🔍 [DEBUG] Multiple Timeframe Data Check:")
            print(f"   - Has 'multiple_timeframe' key: ✅")
            print(f"   - Has 'timeframes' data: {'✅' if has_timeframes else '❌'}")
            if has_timeframes:
                print(f"   - Timeframes available: {list(mtf['timeframes'].keys())}")
            
            market_context_data['multiple_timeframe'] = {
                'alignment_score': float(mtf.get('alignment_score', 0)) if mtf.get('alignment_score') is not None else 0,
                'overall_trend': str(mtf.get('overall_trend', 'Unknown')),
                'confidence': float(mtf.get('confidence', 0)) if mtf.get('confidence') is not None else 0,
                'trend_consensus': int(mtf.get('trend_consensus', 0)) if mtf.get('trend_consensus') is not None else 0,
                'timeframes': {}
            }
            
            # Tambahkan data per timeframe
            if 'timeframes' in mtf and mtf['timeframes']:
                print(f"   ✅ Found {len(mtf['timeframes'])} timeframes: {list(mtf['timeframes'].keys())}")
                for tf_name, tf_data in mtf['timeframes'].items():
                    tf_info = {
                        'interval': str(tf_data.get('interval', 'Unknown')),
                        'trend_signal': int(tf_data.get('trend', {}).get('trend_signal', 0)) if isinstance(tf_data.get('trend'), dict) else 0,
                        'trend_strength': float(tf_data.get('trend', {}).get('trend_strength', 0)) if isinstance(tf_data.get('trend'), dict) and tf_data.get('trend', {}).get('trend_strength') is not None else 0
                    }
                    
                    # Tambahkan support/resistance per timeframe
                    if 'support_resistance' in tf_data:
                        sr = tf_data['support_resistance']
                        tf_info['support'] = float(sr.get('support', 0)) if sr.get('support') is not None else None
                        tf_info['resistance'] = float(sr.get('resistance', 0)) if sr.get('resistance') is not None else None
                    
                    market_context_data['multiple_timeframe']['timeframes'][tf_name] = tf_info
                    print(f"      - {tf_name}: {tf_info['interval']}, signal={tf_info['trend_signal']}, strength={tf_info['trend_strength']:.2f}")
            else:
                print(f"   ⚠️  No timeframes data found in multiple_timeframe")
                print(f"   💡 Kemungkinan: get_higher_timeframe_data gagal mengambil data atau USE_ENHANCED_FEATURES = False")
            
            # Tambahkan primary support/resistance dari multiple TF
            if 'support_resistance' in mtf:
                sr = mtf['support_resistance']
                if 'primary_support' in sr:
                    market_context_data['multiple_timeframe']['primary_support'] = {
                        'level': float(sr['primary_support'].get('level', 0)) if sr['primary_support'].get('level') is not None else None,
                        'strength': float(sr['primary_support'].get('strength', 0)) if sr['primary_support'].get('strength') is not None else 0,
                        'timeframe': str(sr['primary_support'].get('timeframe', 'Unknown'))
                    }
                if 'primary_resistance' in sr:
                    market_context_data['multiple_timeframe']['primary_resistance'] = {
                        'level': float(sr['primary_resistance'].get('level', 0)) if sr['primary_resistance'].get('level') is not None else None,
                        'strength': float(sr['primary_resistance'].get('strength', 0)) if sr['primary_resistance'].get('strength') is not None else 0,
                        'timeframe': str(sr['primary_resistance'].get('timeframe', 'Unknown'))
                    }
        
        # Tambahkan MTF metrics jika ada (untuk backward compatibility)
        if 'mtf_alignment_score' in market_context:
            if 'multiple_timeframe' not in market_context_data:
                market_context_data['multiple_timeframe'] = {}
            market_context_data['multiple_timeframe']['alignment_score'] = float(market_context.get('mtf_alignment_score', 0))
            market_context_data['multiple_timeframe']['overall_trend'] = str(market_context.get('mtf_overall_trend', 'Unknown'))
            market_context_data['multiple_timeframe']['confidence'] = float(market_context.get('mtf_confidence', 0))
            market_context_data['multiple_timeframe']['trend_consensus'] = int(market_context.get('mtf_trend_consensus', 0))
        
        analysis_results['market_context'] = market_context_data
    
    # Advanced Features
    advanced_features = {}
    if 'Z_Score' in data.columns:
        try:
            z_score_val = data['Z_Score'].iloc[-1]
            if pd.notna(z_score_val):
                # Convert to scalar if it's a Series
                if isinstance(z_score_val, pd.Series):
                    z_score_val = float(z_score_val.iloc[0]) if len(z_score_val) > 0 else None
                else:
                    z_score_val = float(z_score_val)
                advanced_features['z_score'] = z_score_val
            else:
                advanced_features['z_score'] = None
        except:
            advanced_features['z_score'] = None
    
    if 'RSI' in data.columns:
        try:
            rsi_val = data['RSI'].iloc[-1]
            if pd.notna(rsi_val):
                # Convert to scalar if it's a Series
                if isinstance(rsi_val, pd.Series):
                    rsi_val = float(rsi_val.iloc[0]) if len(rsi_val) > 0 else None
                else:
                    rsi_val = float(rsi_val)
                advanced_features['rsi'] = rsi_val
            else:
                advanced_features['rsi'] = None
        except:
            advanced_features['rsi'] = None
    
    if 'Cycle_Period' in data.columns:
        try:
            cycle_val = data['Cycle_Period'].iloc[-1]
            if pd.notna(cycle_val):
                # Convert to scalar if it's a Series
                if isinstance(cycle_val, pd.Series):
                    cycle_val = float(cycle_val.iloc[0]) if len(cycle_val) > 0 else None
                else:
                    cycle_val = float(cycle_val)
                advanced_features['cycle_period'] = cycle_val
            else:
                advanced_features['cycle_period'] = None
        except:
            advanced_features['cycle_period'] = None
    
    patterns = {}
    if 'Pattern_HnS' in data.columns:
        try:
            pattern_val = data['Pattern_HnS'].iloc[-1]
            if pd.notna(pattern_val):
                # Convert to scalar if it's a Series
                if isinstance(pattern_val, pd.Series):
                    pattern_val = pattern_val.iloc[0] if len(pattern_val) > 0 else False
                patterns['Head_and_Shoulders'] = bool(pattern_val)
            else:
                patterns['Head_and_Shoulders'] = False
        except:
            patterns['Head_and_Shoulders'] = False
    
    if 'Pattern_DoubleTop' in data.columns:
        try:
            pattern_val = data['Pattern_DoubleTop'].iloc[-1]
            if pd.notna(pattern_val):
                # Convert to scalar if it's a Series
                if isinstance(pattern_val, pd.Series):
                    pattern_val = pattern_val.iloc[0] if len(pattern_val) > 0 else False
                patterns['Double_Top'] = bool(pattern_val)
            else:
                patterns['Double_Top'] = False
        except:
            patterns['Double_Top'] = False
    
    if 'Pattern_DoubleBottom' in data.columns:
        try:
            pattern_val = data['Pattern_DoubleBottom'].iloc[-1]
            if pd.notna(pattern_val):
                # Convert to scalar if it's a Series
                if isinstance(pattern_val, pd.Series):
                    pattern_val = pattern_val.iloc[0] if len(pattern_val) > 0 else False
                patterns['Double_Bottom'] = bool(pattern_val)
            else:
                patterns['Double_Bottom'] = False
        except:
            patterns['Double_Bottom'] = False
    
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
    
    # Recent Trades Analysis (Market Activity)
    if recent_trades_analysis:
        analysis_results['recent_trades_analysis'] = {
            'market_aggression': recent_trades_analysis.get('market_aggression', 0),
            'buyer_dominance': recent_trades_analysis.get('buyer_dominance', 50),
            'momentum': recent_trades_analysis.get('momentum', 0),
            'price_trend': recent_trades_analysis.get('price_trend', 0),
            'trade_count': recent_trades_analysis.get('trade_count', 0),
            'total_volume': recent_trades_analysis.get('total_volume', 0),
            'buy_volume': recent_trades_analysis.get('buy_volume', 0),
            'sell_volume': recent_trades_analysis.get('sell_volume', 0),
            'buy_ratio': recent_trades_analysis.get('buy_ratio', 0.5),
            'sell_ratio': recent_trades_analysis.get('sell_ratio', 0.5),
            'avg_trade_size': recent_trades_analysis.get('avg_trade_size', 0)
        }
    
    # Open Interest Analysis (Trend Strength)
    if open_interest_analysis:
        analysis_results['open_interest_analysis'] = {
            'open_interest': open_interest_analysis.get('open_interest', 0),
            'oi_change': open_interest_analysis.get('oi_change', 0),
            'oi_change_pct': open_interest_analysis.get('oi_change_pct', 0),
            'trend_strength': open_interest_analysis.get('trend_strength', 'UNKNOWN'),
            'trend_direction': open_interest_analysis.get('trend_direction', 'NEUTRAL'),
            'signal': open_interest_analysis.get('signal', 'NEUTRAL'),
            'interpretation': open_interest_analysis.get('interpretation', 'No interpretation available')
        }
    
    # Orderbook Depth Analysis (Orderbook Imbalance, Buy/Sell Walls, Whales)
    if orderbook_analysis:
        analysis_results['orderbook_analysis'] = {
            'total_bid_volume': orderbook_analysis.get('total_bid_volume', 0),
            'total_ask_volume': orderbook_analysis.get('total_ask_volume', 0),
            'bid_ask_ratio': orderbook_analysis.get('bid_ask_ratio', 1.0),
            'orderbook_imbalance': orderbook_analysis.get('orderbook_imbalance', 0),
            'buy_wall_size': orderbook_analysis.get('buy_wall_size', 0),
            'sell_wall_size': orderbook_analysis.get('sell_wall_size', 0),
            'buy_wall_price': orderbook_analysis.get('buy_wall_price', 0),
            'sell_wall_price': orderbook_analysis.get('sell_wall_price', 0),
            'big_orders_count': orderbook_analysis.get('big_orders_count', 0),
            'liquidity_clusters': orderbook_analysis.get('liquidity_clusters', []),
            'signal': orderbook_analysis.get('signal', 'NEUTRAL'),
            'interpretation': orderbook_analysis.get('interpretation', 'No interpretation available')
        }
    
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

