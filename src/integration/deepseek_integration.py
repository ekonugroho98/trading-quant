"""
DeepSeek API Integration Module
Mengirim data analisis ke DeepSeek AI untuk mendapatkan rekomendasi trading
"""

import json
import requests
from typing import Dict, Optional, Any
from datetime import datetime


def format_price_no_rounding(price) -> str:
    """
    Format harga tanpa pembulatan, menampilkan semua digit signifikan
    
    Args:
        price: Harga yang akan diformat (bisa float, int, atau None)
    
    Returns:
        String dengan harga yang diformat tanpa pembulatan
    """
    # Handle None dan non-numeric values
    if price is None:
        return "None"
    
    # Convert to float if possible
    try:
        price = float(price)
    except (TypeError, ValueError):
        return str(price) if price is not None else "None"
    
    # Check for NaN or inf
    import math
    if math.isnan(price) or math.isinf(price):
        return "None"
    
    # Konversi ke string dengan format yang menghilangkan trailing zeros
    # Tapi tetap menampilkan semua digit signifikan
    if price >= 1:
        # Untuk harga >= 1, tampilkan hingga 8 desimal (cukup untuk crypto)
        return f"{price:.8f}".rstrip('0').rstrip('.')
    elif price >= 0.01:
        # Untuk harga 0.01-1, tampilkan hingga 8 desimal
        return f"{price:.8f}".rstrip('0').rstrip('.')
    else:
        # Untuk harga < 0.01, tampilkan hingga 10 desimal
        return f"{price:.10f}".rstrip('0').rstrip('.')


class DeepSeekTradingAdvisor:
    """Class untuk integrasi dengan DeepSeek API untuk trading advice"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.deepseek.com"):
        """
        Initialize DeepSeek API client
        
        Args:
            api_key: DeepSeek API key (optional, bisa dari config)
            base_url: Base URL untuk DeepSeek API
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.endpoint = f"{self.base_url}/v1/chat/completions"
    
    def prepare_analysis_data(self, analysis_results: Dict) -> str:
        """
        Prepare analysis data untuk dikirim ke AI
        
        Args:
            analysis_results: Dictionary dengan semua hasil analisis
        
        Returns:
            Formatted string untuk prompt
        """
        prompt_parts = []
        
        # Basic Info
        if 'basic_info' in analysis_results:
            basic = analysis_results['basic_info']
            prompt_parts.append("=== INFORMASI DASAR ===")
            prompt_parts.append(f"Symbol: {basic.get('symbol', 'N/A')}")
            prompt_parts.append(f"Trading Style: {basic.get('trading_style', 'N/A')}")
            prompt_parts.append(f"Interval: {basic.get('interval', 'N/A')}")
            prompt_parts.append(f"Total Records: {basic.get('total_records', 'N/A')}")
            prompt_parts.append(f"Period: {basic.get('period', 'N/A')}")
            prompt_parts.append("")
        
        # Current Position
        if 'current_position' in analysis_results:
            pos = analysis_results['current_position']
            prompt_parts.append("=== POSISI SAAT INI ===")
            prompt_parts.append(f"Position: {pos.get('position', 'N/A')}")
            prompt_parts.append(f"Current Price: {pos.get('current_price', 'N/A')}")
            prompt_parts.append(f"MA Short: {pos.get('ma_short', 'N/A')}")
            prompt_parts.append(f"MA Long: {pos.get('ma_long', 'N/A')}")
            prompt_parts.append(f"Support: {pos.get('support', 'N/A')} (distance: {pos.get('support_distance', 'N/A')})")
            prompt_parts.append(f"Resistance: {pos.get('resistance', 'N/A')} (distance: {pos.get('resistance_distance', 'N/A')})")
            prompt_parts.append("")
        
        # Strategy Performance
        if 'strategy_performance' in analysis_results:
            perf = analysis_results['strategy_performance']
            prompt_parts.append("=== PERFORMANSI STRATEGI ===")
            prompt_parts.append(f"Buy & Hold Return: {perf.get('buy_hold_return', 'N/A')}")
            prompt_parts.append(f"Strategy Return: {perf.get('strategy_return', 'N/A')}")
            prompt_parts.append(f"Buy Periods: {perf.get('buy_periods', 'N/A')} ({perf.get('buy_periods_pct', 'N/A')})")
            prompt_parts.append(f"Sell Periods: {perf.get('sell_periods', 'N/A')} ({perf.get('sell_periods_pct', 'N/A')})")
            prompt_parts.append(f"Neutral Periods: {perf.get('neutral_periods', 'N/A')} ({perf.get('neutral_periods_pct', 'N/A')})")
            prompt_parts.append(f"Buy Signals: {perf.get('buy_signals', 'N/A')}")
            prompt_parts.append(f"Sell Signals: {perf.get('sell_signals', 'N/A')}")
            prompt_parts.append("")
        
        # Trading Setup
        if 'trading_setup' in analysis_results:
            setup = analysis_results['trading_setup']
            prompt_parts.append("=== TRADING SETUP ===")
            prompt_parts.append(f"Direction: {setup.get('direction', 'N/A')}")
            prompt_parts.append(f"Limit Entry: {setup.get('limit_entry', 'N/A')}")
            prompt_parts.append(f"Stop Loss: {setup.get('stop_loss', 'N/A')} ({setup.get('stop_loss_pct', 'N/A')})")
            if 'targets' in setup:
                for i, tp in enumerate(setup['targets'], 1):
                    prompt_parts.append(f"TP{i}: {tp.get('price', 'N/A')} ({tp.get('pct', 'N/A')})")
            if 'risk_reward' in setup:
                prompt_parts.append(f"Risk/Reward: {setup.get('risk_reward', 'N/A')}")
            prompt_parts.append("")
        
        # Volume Analysis
        if 'volume_analysis' in analysis_results:
            vol = analysis_results['volume_analysis']
            prompt_parts.append("=== VOLUME ANALYSIS ===")
            prompt_parts.append(f"VWAP: {vol.get('vwap', 'N/A')}")
            prompt_parts.append(f"Price vs VWAP: {vol.get('price_vs_vwap', 'N/A')}")
            prompt_parts.append(f"Volume Ratio: {vol.get('volume_ratio', 'N/A')}")
            prompt_parts.append(f"Volume Spikes: {vol.get('volume_spikes', 'N/A')}")
            prompt_parts.append(f"Current Volume: {vol.get('volume_class', 'N/A')}")
            prompt_parts.append("")
        
        # Market Context
        if 'market_context' in analysis_results:
            ctx = analysis_results['market_context']
            prompt_parts.append("=== MARKET CONTEXT ===")
            prompt_parts.append(f"Market Regime: {ctx.get('current_regime', 'N/A')}")
            prompt_parts.append(f"Trend Direction: {ctx.get('trend_direction', 'N/A')}")
            prompt_parts.append(f"Volatility Regime: {ctx.get('volatility_regime', 'N/A')}")
            prompt_parts.append(f"Higher TF Trend: {ctx.get('higher_tf_trend', 'N/A')}")
            
            # Multiple Timeframe Analysis
            if 'multiple_timeframe' in ctx:
                mtf = ctx['multiple_timeframe']
                prompt_parts.append("")
                prompt_parts.append("=== MULTIPLE TIMEFRAME ANALYSIS ===")
                prompt_parts.append(f"Overall Trend: {mtf.get('overall_trend', 'N/A')}")
                prompt_parts.append(f"Trend Consensus: {mtf.get('trend_consensus', 'N/A')} (1=Bullish, -1=Bearish, 0=Mixed)")
                prompt_parts.append(f"Alignment Score: {mtf.get('alignment_score', 0):.1f}%")
                prompt_parts.append(f"MTF Confidence: {mtf.get('confidence', 0):.1f}%")
                
                # Detail per timeframe
                for tf_name, tf_data in mtf.get('timeframes', {}).items():
                    interval = tf_data.get('interval', 'Unknown')
                    trend_info = tf_data.get('trend', {})
                    sr_info = tf_data.get('support_resistance', {})
                    prompt_parts.append(f"\n{tf_name.upper()} ({interval}):")
                    prompt_parts.append(f"  Trend: {trend_info.get('trend', 'N/A')} (Strength: {trend_info.get('trend_strength', 0):.2f}%)")
                    prompt_parts.append(f"  MA Alignment: {'Yes' if trend_info.get('ma_alignment', False) else 'No'}")
                    if sr_info.get('support'):
                        prompt_parts.append(f"  Support: {sr_info['support']:.6f} (Strength: {sr_info.get('support_strength', 0):.1f}%)")
                    if sr_info.get('resistance'):
                        prompt_parts.append(f"  Resistance: {sr_info['resistance']:.6f} (Strength: {sr_info.get('resistance_strength', 0):.1f}%)")
                
                # Primary Support/Resistance
                sr_agg = mtf.get('support_resistance', {})
                if sr_agg.get('primary_support'):
                    ps = sr_agg['primary_support']
                    prompt_parts.append(f"\nPrimary Support: {ps['level']:.6f} (from {ps['timeframe']}, strength: {ps['strength']:.1f}%)")
                if sr_agg.get('primary_resistance'):
                    pr = sr_agg['primary_resistance']
                    prompt_parts.append(f"Primary Resistance: {pr['level']:.6f} (from {pr['timeframe']}, strength: {pr['strength']:.1f}%)")
            
            prompt_parts.append("")
        
        # Advanced Features
        if 'advanced_features' in analysis_results:
            adv = analysis_results['advanced_features']
            prompt_parts.append("=== ADVANCED FEATURES ===")
            if 'z_score' in adv and adv['z_score'] is not None:
                z_score = adv['z_score']
                try:
                    z_score_val = float(z_score)
                    z_score_label = '(Overbought)' if z_score_val > 2 else '(Oversold)' if z_score_val < -2 else ''
                    prompt_parts.append(f"Z-Score: {z_score} {z_score_label}")
                except (TypeError, ValueError):
                    prompt_parts.append(f"Z-Score: {z_score}")
            if 'rsi' in adv and adv['rsi'] is not None:
                rsi = adv['rsi']
                try:
                    rsi_val = float(rsi)
                    rsi_label = '(Overbought)' if rsi_val > 70 else '(Oversold)' if rsi_val < 30 else ''
                    prompt_parts.append(f"RSI: {rsi} {rsi_label}")
                except (TypeError, ValueError):
                    prompt_parts.append(f"RSI: {rsi}")
            if 'cycle_period' in adv:
                prompt_parts.append(f"Cycle Period: {adv['cycle_period']}")
            if 'patterns' in adv:
                patterns = [p for p in adv['patterns'] if adv['patterns'][p]]
                if patterns:
                    prompt_parts.append(f"Patterns Detected: {', '.join(patterns)}")
            prompt_parts.append("")
        
        # Validation Metrics
        if 'validation_metrics' in analysis_results:
            metrics = analysis_results['validation_metrics']
            prompt_parts.append("=== VALIDATION METRICS ===")
            if 'max_drawdown' in metrics:
                prompt_parts.append(f"Max Drawdown: {metrics['max_drawdown'].get('max_drawdown_pct', 'N/A')}%")
            if 'win_rate' in metrics:
                wr = metrics['win_rate']
                prompt_parts.append(f"Win Rate: {wr.get('win_rate', 'N/A')}%")
                prompt_parts.append(f"Total Trades: {wr.get('total_trades', 'N/A')}")
                prompt_parts.append(f"Profit Factor: {wr.get('profit_factor', 'N/A')}")
            if 'walk_forward' in metrics:
                wf = metrics['walk_forward']
                prompt_parts.append(f"Walk-Forward Consistency: {wf.get('consistency_rate', 'N/A')}%")
            prompt_parts.append("")
        
        # ML Prediction
        if 'ml_prediction' in analysis_results:
            ml = analysis_results['ml_prediction']
            prompt_parts.append("=== ML PREDICTION ===")
            prompt_parts.append(f"Signal: {ml.get('signal', 'N/A')}")
            prompt_parts.append(f"Buy Probability: {ml.get('buy_prob', 'N/A')}")
            prompt_parts.append(f"Sell Probability: {ml.get('sell_prob', 'N/A')}")
            prompt_parts.append(f"Accuracy: {ml.get('accuracy', 'N/A')}")
            prompt_parts.append(f"Expected Value: {ml.get('expected_value', 'N/A')}")
            prompt_parts.append(f"Sharpe Ratio: {ml.get('sharpe_ratio', 'N/A')}")
            prompt_parts.append("")
        
        # Recent Trades Analysis (Market Activity)
        if 'recent_trades_analysis' in analysis_results:
            trades = analysis_results['recent_trades_analysis']
            prompt_parts.append("=== MARKET ACTIVITY (RECENT TRADES) ===")
            prompt_parts.append(f"Market Aggression: {trades.get('market_aggression', 0):.1f}/100")
            aggression_level = "Sangat Tinggi" if trades.get('market_aggression', 0) >= 70 else "Tinggi" if trades.get('market_aggression', 0) >= 50 else "Sedang" if trades.get('market_aggression', 0) >= 30 else "Rendah"
            prompt_parts.append(f"  → Level: {aggression_level}")
            prompt_parts.append(f"Buyer Dominance: {trades.get('buyer_dominance', 50):.1f}%")
            buyer_dom = trades.get('buyer_dominance', 50)
            if buyer_dom >= 60:
                prompt_parts.append(f"  → Buyer Dominant (Strong buying pressure)")
            elif buyer_dom <= 40:
                prompt_parts.append(f"  → Seller Dominant (Strong selling pressure)")
            else:
                prompt_parts.append(f"  → Balanced market")
            prompt_parts.append(f"Short-term Momentum: {trades.get('momentum', 0):+.2f}%")
            momentum_val = trades.get('momentum', 0)
            if momentum_val > 0.1:
                prompt_parts.append(f"  → Bullish momentum (price increasing)")
            elif momentum_val < -0.1:
                prompt_parts.append(f"  → Bearish momentum (price decreasing)")
            else:
                prompt_parts.append(f"  → Neutral momentum")
            prompt_parts.append(f"Trade Count: {trades.get('trade_count', 0)} recent trades")
            prompt_parts.append(f"Total Volume: {trades.get('total_volume', 0):.2f}")
            prompt_parts.append(f"Buy Volume: {trades.get('buy_volume', 0):.2f} ({trades.get('buy_ratio', 0.5)*100:.1f}%)")
            prompt_parts.append(f"Sell Volume: {trades.get('sell_volume', 0):.2f} ({trades.get('sell_ratio', 0.5)*100:.1f}%)")
            prompt_parts.append(f"Average Trade Size: {trades.get('avg_trade_size', 0):.2f}")
            prompt_parts.append("")
            prompt_parts.append("💡 INTERPRETASI:")
            prompt_parts.append("  - Market Aggression: Tinggi = aktif trading, Rendah = tenang")
            prompt_parts.append("  - Buyer Dominance > 60% = strong buying pressure, < 40% = strong selling pressure")
            prompt_parts.append("  - Momentum positif = bullish short-term, negatif = bearish short-term")
            prompt_parts.append("  - Cocok untuk scalping & high-frequency decision making")
            prompt_parts.append("")
        
        # Open Interest Analysis (Trend Strength)
        if 'open_interest_analysis' in analysis_results:
            oi = analysis_results['open_interest_analysis']
            prompt_parts.append("=== OPEN INTEREST (TREND STRENGTH) ===")
            prompt_parts.append(f"Open Interest: {oi.get('open_interest', 0):.2f}")
            
            if oi.get('oi_change_pct', 0) != 0:
                prompt_parts.append(f"OI Change: {oi.get('oi_change_pct', 0):+.2f}%")
                oi_change_val = oi.get('oi_change_pct', 0)
                if oi_change_val > 0:
                    prompt_parts.append(f"  → OI Meningkat (posisi bertambah)")
                elif oi_change_val < 0:
                    prompt_parts.append(f"  → OI Menurun (posisi berkurang)")
                else:
                    prompt_parts.append(f"  → OI Stabil")
            
            trend_strength = oi.get('trend_strength', 'UNKNOWN')
            trend_direction = oi.get('trend_direction', 'NEUTRAL')
            signal = oi.get('signal', 'NEUTRAL')
            interpretation = oi.get('interpretation', 'No interpretation available')
            
            prompt_parts.append(f"Trend Direction: {trend_direction}")
            prompt_parts.append(f"Trend Strength: {trend_strength}")
            prompt_parts.append(f"Signal: {signal}")
            prompt_parts.append(f"Interpretation: {interpretation}")
            prompt_parts.append("")
            prompt_parts.append("💡 INTERPRETASI UMUM:")
            prompt_parts.append("  - OI naik + harga naik → trend bullish kuat (Long) - posisi long bertambah")
            prompt_parts.append("  - OI naik + harga turun → trend bearish kuat (Short) - posisi short bertambah")
            prompt_parts.append("  - OI turun + harga naik → long liquidation/profit taking (caution)")
            prompt_parts.append("  - OI turun + harga turun → short liquidation/profit taking (caution)")
            prompt_parts.append("  - Trend Strength: VERY_STRONG > STRONG > MODERATE > WEAK")
            prompt_parts.append("  - Cocok untuk trend strength analysis")
            prompt_parts.append("")
        
        # Orderbook Depth Analysis (Orderbook Imbalance, Buy/Sell Walls, Whales)
        if 'orderbook_analysis' in analysis_results:
            ob = analysis_results['orderbook_analysis']
            prompt_parts.append("=== ORDERBOOK DEPTH (ORDERBOOK IMBALANCE) ===")
            prompt_parts.append(f"Total Bid Volume: {ob.get('total_bid_volume', 0):.2f}")
            prompt_parts.append(f"Total Ask Volume: {ob.get('total_ask_volume', 0):.2f}")
            prompt_parts.append(f"Bid/Ask Ratio: {ob.get('bid_ask_ratio', 1.0):.2f}")
            prompt_parts.append(f"Orderbook Imbalance: {ob.get('orderbook_imbalance', 0):+.2%}")
            
            buy_wall_size = ob.get('buy_wall_size', 0)
            buy_wall_price = ob.get('buy_wall_price', 0)
            sell_wall_size = ob.get('sell_wall_size', 0)
            sell_wall_price = ob.get('sell_wall_price', 0)
            
            if buy_wall_size > 0:
                prompt_parts.append(f"Buy Wall: {buy_wall_size:.2f} @ {buy_wall_price:.4f}")
            if sell_wall_size > 0:
                prompt_parts.append(f"Sell Wall: {sell_wall_size:.2f} @ {sell_wall_price:.4f}")
            
            big_orders_count = ob.get('big_orders_count', 0)
            if big_orders_count > 0:
                prompt_parts.append(f"Big Orders (Whales): {big_orders_count}")
            
            liquidity_clusters = ob.get('liquidity_clusters', [])
            if liquidity_clusters:
                prompt_parts.append(f"Liquidity Clusters: {len(liquidity_clusters)} detected")
                # Show top 3 biggest clusters
                top_clusters = sorted(liquidity_clusters, key=lambda x: x.get('volume', 0), reverse=True)[:3]
                for i, cluster in enumerate(top_clusters, 1):
                    cluster_type = cluster.get('type', 'UNKNOWN')
                    cluster_price = cluster.get('price', 0)
                    cluster_volume = cluster.get('volume', 0)
                    cluster_size = cluster.get('size_category', 'BIG')
                    prompt_parts.append(f"  {i}. {cluster_type} {cluster_size}: {cluster_volume:.2f} @ {cluster_price:.4f}")
            
            signal = ob.get('signal', 'NEUTRAL')
            interpretation = ob.get('interpretation', 'No interpretation available')
            
            prompt_parts.append(f"Signal: {signal}")
            prompt_parts.append(f"Interpretation: {interpretation}")
            prompt_parts.append("")
            prompt_parts.append("💡 INTERPRETASI UMUM:")
            prompt_parts.append("  - Buy wall besar → potensi Long (support kuat di level tersebut)")
            prompt_parts.append("  - Sell wall besar → potensi Short (resistance kuat di level tersebut)")
            prompt_parts.append("  - Orderbook imbalance positif (>0.1) = lebih banyak buy orders (buy pressure)")
            prompt_parts.append("  - Orderbook imbalance negatif (<-0.1) = lebih banyak sell orders (sell pressure)")
            prompt_parts.append("  - Big orders (whales) dapat mempengaruhi pergerakan harga")
            prompt_parts.append("  - Liquidity clusters menunjukkan area dengan konsentrasi order besar")
            prompt_parts.append("  - Cocok untuk scalping, orderflow analysis, dan high-frequency trading")
            prompt_parts.append("")
        
        return "\n".join(prompt_parts)
    
    def create_trading_prompt(self, analysis_data: str) -> str:
        """
        Create prompt untuk DeepSeek AI
        
        Args:
            analysis_data: Formatted analysis data
        
        Returns:
            Complete prompt string
        """
        prompt = f"""Anda adalah seorang expert quantitative trader dan technical analyst. Berdasarkan data analisis trading berikut, berikan rekomendasi trading yang tepat.

{analysis_data}

Berdasarkan semua data di atas, berikan rekomendasi trading dalam format JSON berikut:

{{
    "action": "BUY|SELL|HOLD",
    "position": "LONG|SHORT|CASH",
    "confidence": 0-100,
    "entry_price": number,
    "targets": [number],
    "stop_loss": number,
    "reason": "string singkat menjelaskan alasan rekomendasi"
}}

**PENTING - ATURAN REKOMENDASI:**

1. **BUY (LONG)** - Pilih jika:
   - **Multiple TF Alignment >= 66% dan trend consensus = BULLISH** (prioritas tertinggi!)
   - Strategi menunjukkan signal BELI dan confidence > 50%
   - ML prediction menunjukkan BELI dengan probabilitas > 50%
   - Harga di atas support atau mendekati support (bounce opportunity)
   - RSI < 70 (tidak overbought) atau Z-Score menunjukkan oversold
   - Volume analysis menunjukkan akumulasi atau volume spike positif
   - **Market Activity (Recent Trades):**
     * Buyer Dominance > 60% = strong buying pressure (konfirmasi untuk LONG)
     * Momentum positif = bullish short-term (konfirmasi timing entry)
     * Market Aggression tinggi (>70) = aktif trading, cocok untuk entry cepat
   - **Open Interest (Trend Strength):**
     * OI naik + harga naik = trend bullish kuat (konfirmasi untuk LONG)
     * Trend Strength STRONG atau VERY_STRONG = trend kuat, confidence tinggi
   - **Orderbook Depth (Orderbook Imbalance):**
     * Buy wall besar = support kuat (konfirmasi untuk LONG)
     * Orderbook imbalance positif (>0.1) = buy pressure (konfirmasi untuk LONG)
   - Risk/reward ratio dari trading setup > 1.2
   - **WAJIB berikan entry_price, targets (minimal 2), dan stop_loss**

2. **SELL (SHORT)** - Pilih jika:
   - **Multiple TF Alignment >= 66% dan trend consensus = BEARISH** (prioritas tertinggi!)
   - Strategi menunjukkan signal JUAL dan confidence > 50%
   - ML prediction menunjukkan JUAL dengan probabilitas > 50%
   - Harga di bawah resistance atau mendekati resistance (rejection opportunity)
   - RSI > 30 (tidak oversold) atau Z-Score menunjukkan overbought
   - Volume analysis menunjukkan distribusi atau volume spike negatif
   - **Market Activity (Recent Trades):**
     * Buyer Dominance < 40% = strong selling pressure (konfirmasi untuk SHORT)
     * Momentum negatif = bearish short-term (konfirmasi timing entry)
     * Market Aggression tinggi (>70) = aktif trading, cocok untuk entry cepat
   - **Open Interest (Trend Strength):**
     * OI naik + harga turun = trend bearish kuat (konfirmasi untuk SHORT)
     * Trend Strength STRONG atau VERY_STRONG = trend kuat, confidence tinggi
   - **Orderbook Depth (Orderbook Imbalance):**
     * Sell wall besar = resistance kuat (konfirmasi untuk SHORT)
     * Orderbook imbalance negatif (<-0.1) = sell pressure (konfirmasi untuk SHORT)
   - Risk/reward ratio dari trading setup > 1.2
   - **WAJIB berikan entry_price, targets (minimal 2), dan stop_loss**

3. **HOLD (CASH)** - Pilih HANYA jika:
   - **Multiple TF Alignment < 33% atau trend consensus = MIXED** (prioritas tertinggi!)
   - Semua sinyal bertentangan (strategi vs ML vs market context)
   - Confidence < 40% untuk semua sinyal
   - Tidak ada setup yang jelas (harga di tengah-tengah range tanpa konfirmasi)
   - Risk/reward ratio < 1.0
   - Untuk HOLD, set entry_price, targets, dan stop_loss ke null

**PRIORITAS ANALISIS:**
1. Multiple Timeframe Alignment (berat 30%) - **PENTING!**
   - Jika alignment score >= 66% dan semua TF align → confidence tinggi
   - Jika alignment score < 33% atau conflict → confidence rendah, pertimbangkan HOLD
   - Prioritaskan trend consensus dari multiple TF jika alignment tinggi
2. ML prediction signal dan confidence (berat 20%)
3. Strategi signal dan performance metrics (berat 15%)
4. Market Activity (Recent Trades) - **PENTING untuk timing!** (berat 12%)
   - Market Aggression tinggi (>70) = aktif trading, cocok untuk entry/exit cepat
   - Buyer Dominance > 60% = strong buying pressure, konfirmasi untuk LONG
   - Buyer Dominance < 40% = strong selling pressure, konfirmasi untuk SHORT
   - Momentum positif = bullish short-term, momentum negatif = bearish short-term
   - Gunakan untuk konfirmasi timing entry, terutama untuk scalping & day trading
5. Open Interest (Trend Strength) - **PENTING untuk konfirmasi trend!** (berat 10%)
   - OI naik + harga naik → trend bullish kuat (Long) - posisi long bertambah, trend kuat
   - OI naik + harga turun → trend bearish kuat (Short) - posisi short bertambah, trend kuat
   - OI turun + harga naik/turun → liquidation/profit taking (caution, trend melemah)
   - Trend Strength: VERY_STRONG > STRONG > MODERATE > WEAK
   - Gunakan untuk konfirmasi strength trend, terutama untuk swing & position trading
6. Orderbook Depth (Orderbook Imbalance) - **PENTING untuk timing entry/exit!** (berat 8%)
   - Buy wall besar → potensi Long (support kuat di level tersebut)
   - Sell wall besar → potensi Short (resistance kuat di level tersebut)
   - Orderbook imbalance positif = buy pressure, negatif = sell pressure
   - Big orders (whales) dapat mempengaruhi pergerakan harga
   - Cocok untuk scalping, orderflow analysis, dan high-frequency trading
7. Support/Resistance levels dari multiple TF (prioritize higher TF) (berat 6%)
8. Volume analysis dan market context (berat 4%)
9. Advanced features (RSI, Z-Score, patterns) (berat 4%)

**UNTUK BUY/SELL:**
- entry_price: Gunakan limit_entry dari trading setup jika ada, atau current_price ± 0.5% untuk limit order
- targets: Gunakan TP1, TP2, TP3 dari trading setup jika ada, atau hitung berdasarkan support/resistance
- stop_loss: Gunakan stop_loss dari trading setup jika ada, atau hitung berdasarkan support/resistance dengan risk 1-2%
- confidence: Hitung berdasarkan alignment semua sinyal (semakin banyak sinyal yang align, semakin tinggi confidence)

**JANGAN terlalu konservatif!** Jika ada sinyal yang jelas (strategi + ML + market context align), berikan BUY atau SELL dengan entry yang jelas. HOLD hanya untuk situasi yang benar-benar tidak jelas.

Hanya kembalikan JSON, tanpa penjelasan tambahan."""
        
        return prompt
    
    def call_deepseek_api(self, prompt: str, model: str = "deepseek-chat") -> Optional[Dict]:
        """
        Call DeepSeek API untuk mendapatkan rekomendasi
        
        Args:
            prompt: Prompt untuk AI
            model: Model name (default: deepseek-chat)
        
        Returns:
            Dictionary dengan response dari API atau None jika error
        """
        if not self.api_key:
            print("⚠️  DeepSeek API key tidak ditemukan")
            return None
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.5,  # Balanced temperature untuk lebih agresif tapi tetap konsisten
            "max_tokens": 800  # Increase untuk response yang lebih lengkap
        }
        
        try:
            response = requests.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                return self.parse_ai_response(content)
            else:
                print(f"❌ Error dari DeepSeek API: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error menghubungi DeepSeek API: {e}")
            return None
        except Exception as e:
            print(f"❌ Error parsing response: {e}")
            return None
    
    def parse_ai_response(self, content: str) -> Optional[Dict]:
        """
        Parse AI response dan extract JSON
        
        Args:
            content: Raw content dari AI response
        
        Returns:
            Parsed dictionary atau None jika error
        """
        try:
            # Cari JSON di dalam response (bisa ada markdown code block)
            content = content.strip()
            
            # Remove markdown code blocks jika ada
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            
            if content.endswith("```"):
                content = content[:-3]
            
            content = content.strip()
            
            # Parse JSON
            result = json.loads(content)
            
            # Validate structure
            required_fields = ['action', 'position', 'confidence', 'entry_price', 'targets', 'stop_loss', 'reason']
            if not all(field in result for field in required_fields):
                print("⚠️  Response tidak lengkap, field yang hilang:", 
                      [f for f in required_fields if f not in result])
                return None
            
            # Validate action-specific requirements
            action = result.get('action', '').upper()
            if action in ['BUY', 'SELL']:
                # Untuk BUY/SELL, entry_price, targets, dan stop_loss harus ada dan valid
                entry_price = result.get('entry_price')
                targets = result.get('targets', [])
                stop_loss = result.get('stop_loss')
                
                if entry_price is None or (not isinstance(entry_price, (int, float)) and entry_price != 'null'):
                    print(f"⚠️  BUY/SELL memerlukan entry_price yang valid, mendapat: {entry_price}")
                    # Fallback: gunakan current_price dari data jika ada
                    # Tapi kita tidak punya akses ke current_price di sini, jadi return None
                    return None
                
                if not targets or (isinstance(targets, list) and len(targets) == 0):
                    print(f"⚠️  BUY/SELL memerlukan minimal 1 target, mendapat: {targets}")
                    return None
                
                if stop_loss is None or (not isinstance(stop_loss, (int, float)) and stop_loss != 'null'):
                    print(f"⚠️  BUY/SELL memerlukan stop_loss yang valid, mendapat: {stop_loss}")
                    return None
                
                # Convert null string to None if needed
                if isinstance(entry_price, str) and entry_price.lower() == 'null':
                    result['entry_price'] = None
                if isinstance(stop_loss, str) and stop_loss.lower() == 'null':
                    result['stop_loss'] = None
                if isinstance(targets, str) and targets.lower() == 'null':
                    result['targets'] = []
            
            elif action == 'HOLD':
                # Untuk HOLD, entry_price, targets, dan stop_loss harus null
                if result.get('entry_price') not in [None, 'null', '']:
                    result['entry_price'] = None
                if result.get('targets') not in [None, [], 'null']:
                    result['targets'] = []
                if result.get('stop_loss') not in [None, 'null', '']:
                    result['stop_loss'] = None
            
            return result
                
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing JSON: {e}")
            print(f"   Content: {content[:200]}...")
            return None
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def get_trading_recommendation(self, analysis_results: Dict, model: str = "deepseek-chat") -> Optional[Dict]:
        """
        Main method untuk mendapatkan rekomendasi trading dari DeepSeek
        
        Args:
            analysis_results: Dictionary dengan semua hasil analisis
            model: Model name (default: deepseek-chat, bisa diubah ke deepseek-chat-v3.2 atau deepseek-v3.2)
        
        Returns:
            Dictionary dengan rekomendasi trading atau None jika error
        """
        # Prepare data
        analysis_data = self.prepare_analysis_data(analysis_results)
        
        # Create prompt
        prompt = self.create_trading_prompt(analysis_data)
        
        # Call API dengan model yang ditentukan
        recommendation = self.call_deepseek_api(prompt, model=model)
        
        return recommendation


def format_recommendation_output(recommendation: Dict, 
                                 current_price: Optional[float] = None,
                                 support: Optional[float] = None,
                                 resistance: Optional[float] = None,
                                 timeframe: Optional[str] = None,
                                 symbol: Optional[str] = None) -> str:
    """
    Format recommendation untuk ditampilkan
    
    Args:
        recommendation: Dictionary dengan rekomendasi
        current_price: Harga saat ini (optional)
        support: Support level (optional)
        resistance: Resistance level (optional)
        timeframe: Timeframe trading (optional)
        symbol: Trading symbol (optional)
    
    Returns:
        Formatted string
    """
    if not recommendation:
        return "❌ Tidak ada rekomendasi"
    
    output = []
    output.append("\n" + "=" * 70)
    output.append("🤖 DEEPSEEK AI TRADING RECOMMENDATION")
    output.append("=" * 70)
    
    # Symbol dan Timeframe
    if symbol:
        output.append(f"\n📊 Symbol: {symbol}")
    if timeframe:
        output.append(f"⏰ Timeframe: {timeframe}")
    
    # Tampilkan current price jika tersedia
    if current_price is not None:
        output.append(f"\n💵 Current Price: {format_price_no_rounding(current_price)}")
    
    # Support & Resistance
    if support is not None or resistance is not None:
        output.append(f"\n📈 Key Levels:")
        if support is not None:
            output.append(f"   🟢 Support: {format_price_no_rounding(support)}")
        if resistance is not None:
            output.append(f"   🔴 Resistance: {format_price_no_rounding(resistance)}")
    
    output.append(f"\n📊 Action: {recommendation.get('action', 'N/A')}")
    output.append(f"📍 Position: {recommendation.get('position', 'N/A')}")
    output.append(f"🎯 Confidence: {recommendation.get('confidence', 0)}%")
    
    # Check if HOLD
    action = recommendation.get('action', '').upper()
    
    if action == 'HOLD':
        # Untuk HOLD, tampilkan None
        output.append(f"\n💰 Entry Price: None")
        output.append(f"🛑 Stop Loss: None")
        output.append(f"\n🎯 Targets: None")
        output.append(f"\n⚠️  No Entry - Tidak ada posisi trading saat ini")
    else:
        # Entry Price
        entry_price = recommendation.get('entry_price')
        if isinstance(entry_price, (int, float)):
            output.append(f"\n💰 Entry Price: {format_price_no_rounding(entry_price)}")
        else:
            output.append(f"\n💰 Entry Price: {entry_price}")
        
        # Stop Loss dengan persentase
        stop_loss = recommendation.get('stop_loss')
        if (isinstance(stop_loss, (int, float)) and 
            isinstance(entry_price, (int, float)) and 
            entry_price is not None and 
            entry_price > 0 and
            stop_loss is not None):
            try:
                stop_loss_pct = ((stop_loss - entry_price) / entry_price) * 100
                sign = "+" if stop_loss_pct > 0 else ""
                # Format persentase dengan lebih banyak desimal untuk akurasi
                stop_loss_str = format_price_no_rounding(stop_loss)
                output.append(f"🛑 Stop Loss: {stop_loss_str} ({sign}{stop_loss_pct:.6f}%)".rstrip('0').rstrip('.'))
            except (TypeError, ValueError, ZeroDivisionError):
                output.append(f"🛑 Stop Loss: {format_price_no_rounding(stop_loss)}")
        else:
            output.append(f"🛑 Stop Loss: {format_price_no_rounding(stop_loss) if stop_loss is not None else 'None'}")
        
        # Targets dengan persentase
        targets = recommendation.get('targets', [])
        if targets:
            output.append(f"\n🎯 Targets:")
            for i, target in enumerate(targets, 1):
                if (isinstance(target, (int, float)) and 
                    isinstance(entry_price, (int, float)) and 
                    entry_price is not None and 
                    entry_price > 0 and
                    target is not None):
                    try:
                        target_pct = ((target - entry_price) / entry_price) * 100
                        sign = "+" if target_pct > 0 else ""
                        # Format target dengan lebih banyak desimal untuk akurasi
                        target_str = format_price_no_rounding(target)
                        pct_str = f"{sign}{target_pct:.6f}%".rstrip('0').rstrip('.')
                        output.append(f"   TP{i}: {target_str} ({pct_str})")
                    except (TypeError, ValueError, ZeroDivisionError):
                        output.append(f"   TP{i}: {format_price_no_rounding(target)}")
                else:
                    output.append(f"   TP{i}: {format_price_no_rounding(target) if target is not None else 'None'}")
        else:
            output.append(f"\n🎯 Targets: None")
    
    reason = recommendation.get('reason', '')
    if reason:
        output.append(f"\n💡 Reason: {reason}")
    
    output.append("\n" + "=" * 70)
    
    return "\n".join(output)

