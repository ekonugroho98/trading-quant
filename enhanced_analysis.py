"""
Enhanced Analysis Module
Integrasi semua fitur advanced ke dalam analisis trading
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional

# Import modul-modul baru
try:
    from volume_analysis import get_volume_indicators, calculate_vwap, detect_volume_spike
    from market_context import get_market_context, analyze_market_regime, analyze_volatility_regime
    from advanced_features import get_all_advanced_features
    from validation_metrics import get_all_validation_metrics, calculate_maximum_drawdown
    HAS_ENHANCED_FEATURES = True
except ImportError as e:
    print(f"⚠️  Enhanced features tidak tersedia: {e}")
    HAS_ENHANCED_FEATURES = False


def enhance_data_with_volume_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Tambahkan volume analysis ke dataframe"""
    if not HAS_ENHANCED_FEATURES:
        return df
    
    try:
        if 'Volume' in df.columns:
            df = get_volume_indicators(df)
            print("✅ Volume analysis ditambahkan")
        else:
            print("⚠️  Kolom Volume tidak ditemukan, skip volume analysis")
    except Exception as e:
        print(f"⚠️  Error dalam volume analysis: {e}")
    
    return df


def enhance_data_with_market_context(df: pd.DataFrame, symbol: str, 
                                    current_interval: str):
    """Tambahkan market context ke dataframe"""
    context = {}
    
    if not HAS_ENHANCED_FEATURES:
        return df, context
    
    try:
        # Market regime
        df = analyze_market_regime(df)
        
        # Volatility regime
        df = analyze_volatility_regime(df)
        
        # Get comprehensive market context
        context = get_market_context(df, symbol, current_interval)
        
        print("✅ Market context ditambahkan")
    except Exception as e:
        print(f"⚠️  Error dalam market context: {e}")
    
    return df, context


def enhance_data_with_advanced_features(df: pd.DataFrame) -> pd.DataFrame:
    """Tambahkan advanced features ke dataframe"""
    if not HAS_ENHANCED_FEATURES:
        return df
    
    try:
        df = get_all_advanced_features(df)
        print("✅ Advanced features ditambahkan")
    except Exception as e:
        print(f"⚠️  Error dalam advanced features: {e}")
    
    return df


def calculate_enhanced_validation_metrics(df: pd.DataFrame) -> Dict:
    """Hitung validation metrics tambahan"""
    if not HAS_ENHANCED_FEATURES:
        return {}
    
    try:
        signals = df['Signal'] if 'Signal' in df.columns else None
        equity_curve = df['Cumulative_Strategy'] if 'Cumulative_Strategy' in df.columns else None
        
        metrics = get_all_validation_metrics(df, equity_curve, signals)
        
        print("✅ Enhanced validation metrics dihitung")
        return metrics
    except Exception as e:
        print(f"⚠️  Error dalam validation metrics: {e}")
        return {}


def print_enhanced_metrics(metrics: Dict):
    """Print enhanced validation metrics"""
    if not metrics:
        return
    
    print("\n" + "=" * 70)
    print("📊 ENHANCED VALIDATION METRICS")
    print("=" * 70)
    
    # Maximum Drawdown
    if 'max_drawdown' in metrics:
        dd = metrics['max_drawdown']
        print(f"\n📉 Maximum Drawdown:")
        print(f"   Max DD: {dd.get('max_drawdown_pct', 0):.2f}%")
        if dd.get('drawdown_duration'):
            print(f"   Duration: {dd['drawdown_duration']} days")
    
    # Win Rate
    if 'win_rate' in metrics:
        wr = metrics['win_rate']
        print(f"\n🎯 Win Rate:")
        print(f"   Win Rate: {wr.get('win_rate', 0):.2f}%")
        print(f"   Total Trades: {wr.get('total_trades', 0)}")
        print(f"   Winning: {wr.get('winning_trades', 0)} | Losing: {wr.get('losing_trades', 0)}")
        print(f"   Avg Win: {wr.get('avg_winning_trade', 0):.4f}")
        print(f"   Avg Loss: {wr.get('avg_losing_trade', 0):.4f}")
        print(f"   Profit Factor: {wr.get('profit_factor', 0):.2f}")
    
    # Profit Per Trade
    if 'profit_per_trade' in metrics:
        ppt = metrics['profit_per_trade']
        print(f"\n💰 Profit Per Trade:")
        print(f"   Avg Profit: {ppt.get('avg_profit_per_trade', 0):.4f}")
        print(f"   Total Profit: {ppt.get('total_profit', 0):.4f}")
        print(f"   Total Trades: {ppt.get('total_trades', 0)}")
    
    # Time in Market
    if 'time_in_market' in metrics:
        tim = metrics['time_in_market']
        print(f"\n⏱️  Time in Market:")
        print(f"   In Market: {tim.get('time_in_market_pct', 0):.2f}%")
        print(f"   Out of Market: {tim.get('time_out_of_market_pct', 0):.2f}%")
        print(f"   Avg Holding Period: {tim.get('avg_holding_period', 0):.1f} periods")
    
    # Walk-Forward Analysis
    if 'walk_forward' in metrics:
        wf = metrics['walk_forward']
        print(f"\n🔄 Walk-Forward Analysis:")
        print(f"   Total Windows: {wf.get('total_windows', 0)}")
        print(f"   Avg Train Return: {wf.get('avg_train_return', 0):.2f}%")
        print(f"   Avg Test Return: {wf.get('avg_test_return', 0):.2f}%")
        print(f"   Consistency Rate: {wf.get('consistency_rate', 0):.2f}%")
        print(f"   Positive Test Windows: {wf.get('positive_test_windows', 0)}")
    
    print("\n" + "=" * 70)


def print_market_context(context: Dict):
    """Print market context information"""
    if not context:
        return
    
    print("\n" + "=" * 70)
    print("🌍 MARKET CONTEXT")
    print("=" * 70)
    
    print(f"📈 Market Regime: {context.get('current_regime', 'Unknown')}")
    print(f"📊 Trend Direction: {'Up' if context.get('trend_direction', 0) > 0 else 'Down' if context.get('trend_direction', 0) < 0 else 'Neutral'}")
    print(f"💹 Volatility Regime: {context.get('volatility_regime', 'Unknown')}")
    print(f"⏰ Higher TF Trend: {context.get('higher_tf_trend', 'Unknown')}")
    
    print("=" * 70)


def print_volume_analysis_summary(df: pd.DataFrame):
    """Print summary volume analysis"""
    if 'VWAP' not in df.columns:
        return
    
    print("\n" + "=" * 70)
    print("📊 VOLUME ANALYSIS SUMMARY")
    print("=" * 70)
    
    if 'VWAP' in df.columns:
        last_vwap = df['VWAP'].iloc[-1]
        last_close = df['Close'].iloc[-1]
        vwap_diff = ((last_close - last_vwap) / last_vwap) * 100
        print(f"💰 VWAP: {last_vwap:.2f}")
        print(f"   Price vs VWAP: {vwap_diff:+.2f}%")
    
    if 'Volume_Ratio' in df.columns:
        last_vol_ratio = df['Volume_Ratio'].iloc[-1]
        print(f"📈 Volume Ratio: {last_vol_ratio:.2f}x average")
    
    if 'Volume_Spike' in df.columns:
        spike_count = df['Volume_Spike'].sum()
        print(f"🚀 Volume Spikes: {spike_count} detected")
    
    if 'Volume_Class' in df.columns:
        last_vol_class = df['Volume_Class'].iloc[-1]
        print(f"📊 Current Volume: {last_vol_class}")
    
    print("=" * 70)


def print_advanced_features_summary(df: pd.DataFrame):
    """Print summary advanced features"""
    print("\n" + "=" * 70)
    print("🔬 ADVANCED FEATURES SUMMARY")
    print("=" * 70)
    
    if 'Z_Score' in df.columns:
        last_z = df['Z_Score'].iloc[-1]
        print(f"📊 Z-Score: {last_z:.2f}")
        if abs(last_z) > 2:
            print(f"   ⚠️  {'Overbought' if last_z > 2 else 'Oversold'} condition detected")
    
    if 'RSI' in df.columns:
        last_rsi = df['RSI'].iloc[-1]
        print(f"📈 RSI: {last_rsi:.2f}")
        if last_rsi > 70:
            print(f"   ⚠️  Overbought")
        elif last_rsi < 30:
            print(f"   ⚠️  Oversold")
    
    if 'Cycle_Period' in df.columns:
        cycle_period = df['Cycle_Period'].iloc[-1]
        if pd.notna(cycle_period):
            print(f"🔄 Detected Cycle Period: {cycle_period:.0f} periods")
    
    if 'Pattern_HnS' in df.columns:
        if df['Pattern_HnS'].iloc[-1]:
            print(f"📉 Pattern: Head and Shoulders detected")
    
    if 'Pattern_DoubleTop' in df.columns:
        if df['Pattern_DoubleTop'].iloc[-1]:
            print(f"📉 Pattern: Double Top detected")
    
    if 'Pattern_DoubleBottom' in df.columns:
        if df['Pattern_DoubleBottom'].iloc[-1]:
            print(f"📈 Pattern: Double Bottom detected")
    
    print("=" * 70)

