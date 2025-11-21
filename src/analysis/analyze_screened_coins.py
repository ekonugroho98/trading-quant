#!/usr/bin/env python3
"""
Analyze Screened Coins Module
Menganalisis hasil screening coin dan menghasilkan:
- TRADING SETUP
- DEEPSEEK AI TRADING RECOMMENDATION
- RINGKASAN QUANT MODEL
"""

import os
import sys

# Add project root to Python path to enable src imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import subprocess
import json
import time
import re
import glob
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional

# Import modules
try:
    from src.utils.config import (
        TRADING_STYLE, DATA_SOURCE, get_days_back, get_interval,
        BINANCE_API_KEY, BINANCE_API_SECRET,
        ENABLE_DEEPSEEK_AI, DEEPSEEK_API_KEY, DEEPSEEK_MODEL,
        ENABLE_TELEGRAM_BOT, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
        ANALYSIS_TIMEOUT, HISTORICAL_DATA_TIMEOUT, PREDICTION_TIMEOUT, AI_TIMEOUT,
        ANALYSIS_BATCH_SIZE, ANALYSIS_THREAD_POOL_SIZE, ANALYSIS_BATCH_DELAY
    )
    from src.screening.coin_screening import screen_coins
    from src.models.ml_prediction_helper import get_ml_prediction_from_file
    from src.integration.telegram_bot import TelegramBot
except ImportError as e:
    print(f"⚠️  Error importing modules: {e}")
    sys.exit(1)


def update_config_symbol(symbol: str):
    """Update SYMBOL di config.py"""
    try:
        # Gunakan path yang benar: src/utils/config.py
        config_path = os.path.join(project_root, 'src', 'utils', 'config.py')
        if not os.path.exists(config_path):
            print(f"⚠️  Error updating config: {config_path} tidak ditemukan")
            return
        
        with open(config_path, 'r') as f:
            content = f.read()
        
        # Replace SYMBOL line (jika ada)
        pattern = r'^SYMBOL\s*=\s*["\'][^"\']*["\']'
        replacement = f'SYMBOL = "{symbol}"'
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        
        with open(config_path, 'w') as f:
            f.write(content)
    except Exception as e:
        print(f"⚠️  Error updating config: {e}")


def update_config_trading_style(trading_style: str):
    """Update TRADING_STYLE di config.py"""
    try:
        # Gunakan path yang benar: src/utils/config.py
        config_path = os.path.join(project_root, 'src', 'utils', 'config.py')
        if not os.path.exists(config_path):
            print(f"⚠️  Error updating TRADING_STYLE: {config_path} tidak ditemukan")
            return
        
        with open(config_path, 'r') as f:
            content = f.read()
        
        # Replace TRADING_STYLE line
        pattern = r'^TRADING_STYLE\s*=\s*["\'][^"\']*["\']'
        replacement = f'TRADING_STYLE = "{trading_style}"'
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        
        with open(config_path, 'w') as f:
            f.write(content)
    except Exception as e:
        print(f"⚠️  Error updating TRADING_STYLE: {e}")


def extract_trading_setup_from_output(output: str, symbol: str) -> Optional[Dict]:
    """
    Extract trading setup dari output analisis_quant.py
    
    Args:
        output: Output string dari analisis_quant.py
        symbol: Coin symbol
    
    Returns:
        Dictionary dengan trading setup atau None
    """
    setup = {}
    
    try:
        # Extract Direction
        direction_match = re.search(r'Direction:\s*(\w+)', output)
        if direction_match:
            setup['direction'] = direction_match.group(1)
        
        # Extract Entry 1, 2, 3
        entry1_match = re.search(r'Entry 1 \(Agresif\):\s*([\d,]+\.?\d*)', output)
        if entry1_match:
            setup['entry1'] = float(entry1_match.group(1).replace(',', ''))
        
        entry2_match = re.search(r'Entry 2 \(Konservatif - Recommended\):\s*([\d,]+\.?\d*)', output)
        if entry2_match:
            entry2 = float(entry2_match.group(1).replace(',', ''))
            setup['entry2'] = entry2
            setup['entry'] = entry2  # Main entry
        
        entry3_match = re.search(r'Entry 3 \(Sangat Konservatif\):\s*([\d,]+\.?\d*)', output)
        if entry3_match:
            setup['entry3'] = float(entry3_match.group(1).replace(',', ''))
        
        # Extract Stop Loss
        sl_match = re.search(r'Stop Loss:\s*([\d,]+\.?\d*)', output)
        if sl_match:
            setup['stop_loss'] = float(sl_match.group(1).replace(',', ''))
        
        # Extract risk percentage
        risk_match = re.search(r'Stop Loss:.*?\(-([\d.]+)%\)', output)
        if risk_match:
            setup['risk_pct'] = float(risk_match.group(1))
        
        # Extract TP1, TP2, TP3
        tp1_match = re.search(r'TP1:\s*([\d,]+\.?\d*)', output)
        if tp1_match:
            setup['tp1'] = float(tp1_match.group(1).replace(',', ''))
        
        tp2_match = re.search(r'TP2:\s*([\d,]+\.?\d*)', output)
        if tp2_match:
            setup['tp2'] = float(tp2_match.group(1).replace(',', ''))
        
        tp3_match = re.search(r'TP3:\s*([\d,]+\.?\d*)', output)
        if tp3_match:
            setup['tp3'] = float(tp3_match.group(1).replace(',', ''))
        
        # Extract action (BUY/SELL)
        if setup.get('direction') == 'LONG':
            setup['action'] = 'BUY'
        elif setup.get('direction') == 'SHORT':
            setup['action'] = 'SELL'
        else:
            setup['action'] = 'HOLD'
        
        setup['symbol'] = symbol
        
        return setup if setup else None
        
    except Exception as e:
        print(f"⚠️  Error parsing trading setup: {e}")
        return None


def extract_price_info_from_output(output: str) -> Dict:
    """
    Extract current price, support, resistance, dan timeframe dari output analisis_quant.py
    
    Args:
        output: Output string dari analisis_quant.py
    
    Returns:
        Dictionary dengan price info
    """
    info = {}
    
    try:
        # Extract Current Price (format baru: "  - Harga: ..." atau format lama: "Current Price: ...")
        # Pattern lebih fleksibel untuk menangkap berbagai format angka (dengan/tanpa koma, dengan/tanpa desimal)
        price_match = re.search(r'(?:💵\s*)?(?:Current Price|Harga):\s*\$?\s*([\d,]+\.?\d*)', output, re.IGNORECASE)
        if price_match:
            price_str = price_match.group(1).replace(',', '').strip()
            try:
                info['current_price'] = float(price_str)
            except ValueError:
                pass
        
        # Extract Support (format baru: "  5️⃣  Support: ..." atau format lama)
        # Pattern lebih fleksibel
        support_match = re.search(r'(?:🟢\s*)?(?:5️⃣\s*)?Support:\s*([\d,]+\.?\d*)', output, re.IGNORECASE)
        if support_match:
            support_str = support_match.group(1).replace(',', '').strip()
            try:
                info['support'] = float(support_str)
            except ValueError:
                pass
        
        # Extract Resistance (format baru: "      Resistance: ..." atau format lama)
        # Pattern lebih fleksibel
        resistance_match = re.search(r'(?:🔴\s*)?(?:5️⃣\s*)?Resistance:\s*([\d,]+\.?\d*)', output, re.IGNORECASE)
        if resistance_match:
            resistance_str = resistance_match.group(1).replace(',', '').strip()
            try:
                info['resistance'] = float(resistance_str)
            except ValueError:
                pass
        
        # Extract Timeframe
        timeframe_match = re.search(r'Timeframe:\s*(\w+)', output, re.IGNORECASE)
        if timeframe_match:
            info['timeframe'] = timeframe_match.group(1)
        
    except Exception as e:
        print(f"⚠️  Error extracting price info: {e}")
    
    return info


def extract_deepseek_recommendation_from_output(output: str) -> Optional[str]:
    """
    Extract DeepSeek recommendation dari output analisis_quant.py
    
    Args:
        output: Output string dari analisis_quant.py
    
    Returns:
        Formatted recommendation string atau None
    """
    try:
        # Cari section DeepSeek AI
        pattern = r'🤖\s*DEEPSEEK AI TRADING RECOMMENDATION.*?(?=\n\n|\n📱|\n⚠️|$)'
        match = re.search(pattern, output, re.DOTALL | re.IGNORECASE)
        
        if match:
            recommendation = match.group(0).strip()
            # Bersihkan dari emoji dan formatting yang tidak perlu
            recommendation = re.sub(r'^🤖\s*DEEPSEEK AI TRADING RECOMMENDATION.*?\n', '', recommendation, flags=re.IGNORECASE)
            recommendation = re.sub(r'={70,}', '', recommendation)  # Hapus separator lines
            return recommendation.strip()
        
        return None
    except Exception as e:
        print(f"⚠️  Error extracting DeepSeek recommendation: {e}")
        return None


def parse_deepseek_recommendation_string(recommendation_str: str) -> Optional[Dict]:
    """
    Parse DeepSeek recommendation string menjadi dictionary
    
    Args:
        recommendation_str: String recommendation dari extract_deepseek_recommendation_from_output
    
    Returns:
        Dictionary dengan recommendation atau None
    """
    if not recommendation_str:
        return None
    
    try:
        rec = {}
        
        # Extract Action
        action_match = re.search(r'Action:\s*(\w+)', recommendation_str, re.IGNORECASE)
        if action_match:
            rec['action'] = action_match.group(1).upper()
        
        # Extract Position
        position_match = re.search(r'Position:\s*(\w+)', recommendation_str, re.IGNORECASE)
        if position_match:
            rec['position'] = position_match.group(1).upper()
        
        # Extract Confidence
        confidence_match = re.search(r'Confidence:\s*([\d.]+)', recommendation_str)
        if confidence_match:
            rec['confidence'] = float(confidence_match.group(1))
        
        # Extract Entry Price
        entry_match = re.search(r'Entry Price:\s*([\d,]+\.?\d*)', recommendation_str)
        if entry_match:
            rec['entry_price'] = float(entry_match.group(1).replace(',', ''))
        
        # Extract Stop Loss
        sl_match = re.search(r'Stop Loss:\s*([\d,]+\.?\d*)', recommendation_str)
        if sl_match:
            rec['stop_loss'] = float(sl_match.group(1).replace(',', ''))
        
        # Extract Targets
        targets = []
        tp_pattern = r'TP(\d+):\s*([\d,]+\.?\d*)'
        for match in re.finditer(tp_pattern, recommendation_str):
            targets.append(float(match.group(2).replace(',', '')))
        if targets:
            rec['targets'] = targets
        
        # Extract Reason
        reason_match = re.search(r'Reason:\s*(.+?)(?=\n|$)', recommendation_str, re.DOTALL)
        if reason_match:
            rec['reason'] = reason_match.group(1).strip()
        
        return rec if rec else None
        
    except Exception as e:
        print(f"⚠️  Error parsing DeepSeek recommendation: {e}")
        return None


def extract_backtest_results_from_output(output: str) -> Optional[Dict]:
    """
    Extract backtesting results dari output analisis_quant.py
    
    Args:
        output: Output string dari analisis_quant.py
    
    Returns:
        Dictionary dengan backtesting metrics atau None
    """
    backtest = {}
    
    try:
        # Cari section Enhanced Backtesting Results
        pattern = r'🔬\s*ENHANCED BACKTESTING RESULTS.*?(?=\n\n|\n📱|\n⚠️|$)'
        match = re.search(pattern, output, re.DOTALL | re.IGNORECASE)
        
        if not match:
            return None
        
        backtest_section = match.group(0)
        
        # Extract Return Before Costs (format: "Return Before Costs: X.XX%")
        return_before_match = re.search(r'Return Before Costs:\s*([\d.+-]+)%', backtest_section)
        if return_before_match:
            backtest['return_before_costs'] = float(return_before_match.group(1))
        
        # Extract Return After Costs (format: "Return After Costs: X.XX%")
        return_after_match = re.search(r'Return After Costs:\s*([\d.+-]+)%', backtest_section)
        if return_after_match:
            backtest['return_after_costs'] = float(return_after_match.group(1))
        
        # Extract Cost Impact (format: "Cost Impact: X.XX%")
        cost_impact_match = re.search(r'Cost Impact:\s*([\d.+-]+)%', backtest_section)
        if cost_impact_match:
            backtest['cost_impact'] = float(cost_impact_match.group(1))
        
        # Extract Sharpe Ratio (After) (format: "Sharpe Ratio (After): X.XX")
        sharpe_after_match = re.search(r'Sharpe Ratio\s*\(After\):\s*([\d.+-]+)', backtest_section)
        if sharpe_after_match:
            backtest['sharpe_ratio_after'] = float(sharpe_after_match.group(1))
        
        # Extract Sortino Ratio (After) (format: "Sortino Ratio (After): X.XX")
        sortino_after_match = re.search(r'Sortino Ratio\s*\(After\):\s*([\d.+-]+)', backtest_section)
        if sortino_after_match:
            backtest['sortino_ratio_after'] = float(sortino_after_match.group(1))
        
        # Extract Monte Carlo results
        mc_mean_match = re.search(r'Mean Final Return:\s*([\d.+-]+)%', backtest_section)
        if mc_mean_match:
            backtest['mc_mean_final_return'] = float(mc_mean_match.group(1))
        
        mc_median_match = re.search(r'Median Final Return:\s*([\d.+-]+)%', backtest_section)
        if mc_median_match:
            backtest['mc_median_final_return'] = float(mc_median_match.group(1))
        
        mc_prob_profit_match = re.search(r'Probability of Profit:\s*([\d.]+)%', backtest_section)
        if mc_prob_profit_match:
            backtest['mc_probability_profit'] = float(mc_prob_profit_match.group(1))
        
        # Extract Max Drawdown (jika ada di output - format fleksibel)
        max_dd_match = re.search(r'Max(?:imum)?\s*Drawdown[:\s]+([\d.+-]+)%?', backtest_section, re.IGNORECASE)
        if max_dd_match:
            backtest['max_drawdown'] = abs(float(max_dd_match.group(1)))
        
        # Extract Win Rate (jika ada di output - format fleksibel)
        win_rate_match = re.search(r'Win\s*Rate[:\s]+([\d.]+)%', backtest_section, re.IGNORECASE)
        if win_rate_match:
            backtest['win_rate'] = float(win_rate_match.group(1))
        
        return backtest if backtest else None
        
    except Exception as e:
        print(f"⚠️  Error extracting backtest results: {e}")
        return None


def run_analysis_for_coin(symbol: str, trading_style: Optional[str] = None) -> Optional[Dict]:
    """
    Jalankan analisis lengkap untuk satu coin dan extract hasil penting
    
    Args:
        symbol: Coin symbol (format: BTC-USD)
        trading_style: Trading style untuk analisis (default: None = gunakan dari config)
    
    Returns:
        Dictionary dengan:
        - trading_setup: Trading setup dari analisis
        - deepseek_recommendation: Rekomendasi dari DeepSeek AI
        - ml_prediction: Ringkasan ML prediction
        - success: Boolean apakah analisis berhasil
    """
    print(f"\n{'='*70}")
    print(f"📊 ANALISIS: {symbol}")
    print(f"{'='*70}")
    
    result = {
        'symbol': symbol,
        'success': False,
        'trading_setup': None,
        'deepseek_recommendation': None,
        'ml_prediction': None,
        'price_info': None,
        'recent_trades_analysis': None,
        'backtest_results': None,  # Tambahkan backtest results
        'error': None
    }
    
    try:
        # 1. Update config dengan symbol dan trading_style (jika diberikan)
        update_config_symbol(symbol)
        if trading_style:
            update_config_trading_style(trading_style)
        time.sleep(0.5)  # Tunggu file ditulis
        
        # 2. Jalankan get_historical_data.py
        print(f"📥 Mengambil data historical untuk {symbol}...")
        # Gunakan path yang benar: src/data/get_historical_data.py
        historical_data_script = os.path.join(project_root, 'src', 'data', 'get_historical_data.py')
        # Capture output tapi print agar log "get klines" terlihat
        data_result = subprocess.run(
            [sys.executable, historical_data_script],
            capture_output=True,  # Capture untuk cek error
            text=True,
            timeout=HISTORICAL_DATA_TIMEOUT,
            cwd=project_root  # Set working directory ke project root
        )
        
        # Print output agar log "get klines" terlihat
        if data_result.stdout:
            print(data_result.stdout)
        if data_result.stderr:
            print(data_result.stderr, file=sys.stderr)
        
        if data_result.returncode != 0:
            result['error'] = f"Gagal mengambil data: {data_result.stderr[:200] if data_result.stderr else 'Unknown error'}"
            print(f"❌ {result['error']}")
            return result
        
        # Cari file CSV yang baru dibuat (di project root)
        csv_files = [f for f in os.listdir(project_root) if f.endswith('.csv') and symbol.replace('-', '').lower() in f.lower()]
        if not csv_files:
            result['error'] = "File CSV tidak ditemukan setelah get_historical_data"
            print(f"❌ {result['error']}")
            return result
        
        csv_file = os.path.join(project_root, max(csv_files, key=lambda f: os.path.getctime(os.path.join(project_root, f))))
        print(f"✅ Data historical: {os.path.basename(csv_file)}")
        
        # 3. Jalankan analisis_quant.py dengan output capture
        print(f"🔍 Menjalankan analisis quant untuk {symbol}...")
        analysis_script = os.path.join(project_root, 'src', 'analysis', 'analisis_quant.py')
        analysis_result = subprocess.run(
            [sys.executable, analysis_script],
            capture_output=True,
            text=True,
            timeout=ANALYSIS_TIMEOUT,
            cwd=project_root,  # Set working directory ke project root
            env={**os.environ, 'RUN_FROM_MASTER_SCRIPT': '1'}  # Set flag untuk tidak delete CSV
        )
        
        # Extract trading setup dan price info dari output
        if analysis_result.stdout:
            trading_setup = extract_trading_setup_from_output(analysis_result.stdout, symbol)
            if trading_setup:
                result['trading_setup'] = trading_setup
                print(f"✅ Trading setup ditemukan")
            
            # Extract price info (current_price, support, resistance, timeframe)
            price_info = extract_price_info_from_output(analysis_result.stdout)
            if price_info:
                result['price_info'] = price_info
                print(f"✅ Price info ditemukan")
            
            # Extract DeepSeek recommendation
            if ENABLE_DEEPSEEK_AI and DEEPSEEK_API_KEY:
                deepseek_rec = extract_deepseek_recommendation_from_output(analysis_result.stdout)
                if deepseek_rec:
                    result['deepseek_recommendation'] = deepseek_rec
                    print(f"✅ DeepSeek recommendation ditemukan")
            
            # Extract backtesting results
            backtest_results = extract_backtest_results_from_output(analysis_result.stdout)
            if backtest_results:
                result['backtest_results'] = backtest_results
                print(f"✅ Backtesting results ditemukan")
                print(f"   Sharpe Ratio (After): {backtest_results.get('sharpe_ratio_after', 'N/A')}")
                print(f"   Sortino Ratio (After): {backtest_results.get('sortino_ratio_after', 'N/A')}")
                print(f"   Return After Costs: {backtest_results.get('return_after_costs', 'N/A')}%")
        
        if analysis_result.returncode != 0:
            print(f"⚠️  Warning: analisis_quant.py exit dengan code {analysis_result.returncode}")
            # Continue anyway untuk coba extract hasil
        
        # 4. Jalankan prediksi_next_day.py
        print(f"🤖 Menjalankan ML prediction untuk {symbol}...")
        prediction_script = os.path.join(project_root, 'src', 'prediksi_next_day.py')
        pred_result = subprocess.run(
            [sys.executable, prediction_script],
            capture_output=True,
            text=True,
            timeout=PREDICTION_TIMEOUT,
            cwd=project_root,  # Set working directory ke project root
            env={**os.environ, 'RUN_FROM_MASTER_SCRIPT': '1'}
        )
        
        time.sleep(1)  # Tunggu file JSON ditulis
        
        # 5. Load ML prediction result
        ml_prediction = get_ml_prediction_from_file()
        if ml_prediction:
            result['ml_prediction'] = ml_prediction
            print(f"✅ ML prediction ditemukan")
        
        # 6. Get recent trades analysis (untuk market aggression & momentum)
        try:
            from src.data.binance_futures_data import get_futures_recent_trades, analyze_recent_trades
            from src.utils.config import DATA_SOURCE
            
            # Convert symbol format: BTC-USD -> BTCUSDT
            binance_symbol = symbol.replace('-USD', 'USDT').replace('-', '')
            
            print(f"📊 Mengambil recent trades untuk {symbol}...")
            trades = get_futures_recent_trades(
                symbol=binance_symbol,
                limit=500,  # Ambil 500 recent trades untuk akurasi lebih baik
                testnet=False
            )
            
            if trades:
                trades_analysis = analyze_recent_trades(trades)
                result['recent_trades_analysis'] = trades_analysis
                print(f"✅ Recent trades analysis ditemukan")
                print(f"   Market Aggression: {trades_analysis['market_aggression']:.1f}/100")
                print(f"   Buyer Dominance: {trades_analysis['buyer_dominance']:.1f}%")
                print(f"   Momentum: {trades_analysis['momentum']:+.2f}%")
            else:
                print(f"⚠️  Recent trades tidak ditemukan untuk {symbol}")
        except Exception as e:
            print(f"⚠️  Error mengambil recent trades: {e}")
            # Continue tanpa recent trades analysis
        
        # 7. Cleanup CSV file
        try:
            if os.path.exists(csv_file):
                os.remove(csv_file)
                print(f"🗑️  CSV file dihapus: {csv_file}")
        except:
            pass
        
        # 7. Cleanup chart files
        try:
            chart_files = glob.glob("trading_chart_*.png")
            for chart_file in chart_files:
                try:
                    if os.path.exists(chart_file):
                        os.remove(chart_file)
                except:
                    pass
        except:
            pass
        
        result['success'] = True
        print(f"✅ Analisis selesai untuk {symbol}")
        
    except subprocess.TimeoutExpired:
        result['error'] = "Timeout: Analisis terlalu lama"
        print(f"❌ {result['error']}")
    except Exception as e:
        result['error'] = str(e)
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    return result


def validate_trading_setup(setup: Dict, current_price: Optional[float] = None) -> bool:
    """
    Validasi trading setup untuk memastikan data konsisten
    
    Args:
        setup: Trading setup dictionary
        current_price: Current price (optional, untuk validasi)
    
    Returns:
        True jika valid, False jika tidak valid
    """
    if not setup:
        return False
    
    direction = setup.get('direction', '').upper()
    entry1 = setup.get('entry1')
    entry2 = setup.get('entry2')
    entry3 = setup.get('entry3')
    stop_loss = setup.get('stop_loss')
    tp1 = setup.get('tp1')
    tp2 = setup.get('tp2')
    tp3 = setup.get('tp3')
    
    # Validasi entry levels
    if not all(isinstance(x, (int, float)) and x > 0 for x in [entry1, entry2, entry3] if x is not None):
        return False
    
    if direction == "LONG":
        # Untuk LONG: entry harus <= current_price (jika ada), TP harus > entry, SL harus < entry
        entry_min = min([e for e in [entry1, entry2, entry3] if e is not None])
        entry_max = max([e for e in [entry1, entry2, entry3] if e is not None])
        
        # Entry harus konsisten (entry1 >= entry2 >= entry3 untuk LONG agresif)
        # Atau entry1 <= entry2 <= entry3 untuk LONG konservatif (wait for pullback)
        # Untuk sekarang, kita validasi bahwa entry levels masuk akal
        
        # TP harus > entry untuk LONG
        if tp1 and tp1 <= entry_max:
            print(f"⚠️  [VALIDASI] TP1 ({tp1}) harus > entry max ({entry_max}) untuk LONG")
            return False
        if tp2 and tp2 <= tp1:
            print(f"⚠️  [VALIDASI] TP2 ({tp2}) harus > TP1 ({tp1}) untuk LONG")
            return False
        if tp3 and tp3 <= tp2:
            print(f"⚠️  [VALIDASI] TP3 ({tp3}) harus > TP2 ({tp2}) untuk LONG")
            return False
        
        # Stop Loss harus < entry untuk LONG
        if stop_loss and stop_loss >= entry_min:
            print(f"⚠️  [VALIDASI] Stop Loss ({stop_loss}) harus < entry min ({entry_min}) untuk LONG")
            return False
        
        # Jika ada current_price, entry seharusnya tidak terlalu jauh dari current_price
        # Untuk LONG: entry bisa di atas atau di bawah current_price (untuk pullback)
        # Tapi tidak boleh terlalu jauh (max 30% dari current_price)
        if current_price:
            if entry_max > current_price * 1.3:  # Entry tidak boleh > 30% dari current price
                print(f"⚠️  [VALIDASI] Entry max ({entry_max}) terlalu jauh dari current price ({current_price}) untuk LONG")
                return False
            if entry_min < current_price * 0.7:  # Entry tidak boleh < 30% dari current price (terlalu jauh di bawah)
                print(f"⚠️  [VALIDASI] Entry min ({entry_min}) terlalu jauh di bawah current price ({current_price}) untuk LONG")
                return False
    
    elif direction == "SHORT":
        # Untuk SHORT: entry harus >= current_price (jika ada), TP harus < entry, SL harus > entry
        entry_min = min([e for e in [entry1, entry2, entry3] if e is not None])
        entry_max = max([e for e in [entry1, entry2, entry3] if e is not None])
        
        # TP harus < entry untuk SHORT
        if tp1 and tp1 >= entry_min:
            print(f"⚠️  [VALIDASI] TP1 ({tp1}) harus < entry min ({entry_min}) untuk SHORT")
            return False
        if tp2 and tp2 >= tp1:
            print(f"⚠️  [VALIDASI] TP2 ({tp2}) harus < TP1 ({tp1}) untuk SHORT")
            return False
        if tp3 and tp3 >= tp2:
            print(f"⚠️  [VALIDASI] TP3 ({tp3}) harus < TP2 ({tp2}) untuk SHORT")
            return False
        
        # Stop Loss harus > entry untuk SHORT
        if stop_loss and stop_loss <= entry_max:
            print(f"⚠️  [VALIDASI] Stop Loss ({stop_loss}) harus > entry max ({entry_max}) untuk SHORT")
            return False
        
        # Jika ada current_price, entry seharusnya tidak terlalu jauh dari current_price
        # Untuk SHORT: entry harus di atas current_price
        # Tapi tidak boleh terlalu jauh (max 30% dari current_price)
        if current_price:
            if entry_min < current_price * 0.7:  # Entry tidak boleh < 30% dari current price (terlalu jauh di bawah)
                print(f"⚠️  [VALIDASI] Entry min ({entry_min}) terlalu jauh di bawah current price ({current_price}) untuk SHORT")
                return False
            if entry_max > current_price * 1.3:  # Entry tidak boleh > 30% dari current price (terlalu jauh di atas)
                print(f"⚠️  [VALIDASI] Entry max ({entry_max}) terlalu jauh dari current price ({current_price}) untuk SHORT")
                return False
    
    return True


def filter_analysis_results_by_metrics(results: List[Dict], print_summary: bool = True) -> List[Dict]:
    """
    Filter hasil analisis berdasarkan ML metrics DAN backtesting metrics
    Hanya return coin yang memenuhi SEMUA kriteria ketat
    
    KRITERIA KETAT (HARUS SEMUA MEMENUHI):
    
    ML Metrics (WAJIB):
    - Accuracy: TIDAK DIVALIDASI (berapapun tetap lolos)
    - Sharpe Ratio >= 0.5 (risk-adjusted return bagus)
    - Expected Value > 0% (positif expected return)
    
    Backtesting Metrics (WAJIB):
    - Sharpe Ratio (After Costs) >= 0.5
    - Sortino Ratio (After Costs) >= 1.5
    - Max Drawdown < 20% (atau tidak ada data)
    - Win Rate >= 55% (atau tidak ada data)
    - Return After Costs > 0% (positif setelah transaction costs)
    
    Args:
        results: List of analysis results
        print_summary: Print summary filtering (default: True, set False untuk real-time filtering)
    
    Returns:
        Filtered list of results yang memenuhi SEMUA kriteria ketat
    """
    if not results:
        return []
    
    filtered_results = []
    skipped_count = 0
    
    # KRITERIA KETAT - HARUS SEMUA MEMENUHI
    # Accuracy TIDAK DIVALIDASI - berapapun tetap lolos
    min_sharpe_ml = 0.5
    min_expected_value = 0.0  # Harus > 0 (positif)
    
    # Backtesting criteria
    min_sharpe_backtest = 0.5
    min_sortino_backtest = 1.5
    max_drawdown_pct = 20.0  # Max drawdown < 20%
    min_win_rate = 55.0
    min_return_after_costs = 0.0  # Harus > 0 (positif)
    
    # Hanya print header jika print_summary=True (untuk final summary)
    if print_summary:
        print("\n" + "=" * 70)
        print("🔍 FILTERING HASIL ANALISIS - KRITERIA SANGAT KETAT")
        print("=" * 70)
        print("📋 Semua kriteria berikut HARUS dipenuhi:")
        print(f"   ML Metrics:")
        print(f"   - Accuracy: TIDAK DIVALIDASI (berapapun tetap lolos)")
        print(f"   - Sharpe Ratio >= {min_sharpe_ml}")
        print(f"   - Expected Value > {min_expected_value}%")
        print(f"   Backtesting Metrics:")
        print(f"   - Sharpe Ratio (After) >= {min_sharpe_backtest}")
        print(f"   - Sortino Ratio (After) >= {min_sortino_backtest}")
        print(f"   - Max Drawdown < {max_drawdown_pct}%")
        print(f"   - Win Rate >= {min_win_rate}%")
        print(f"   - Return After Costs > {min_return_after_costs}%")
        print("=" * 70)
        print()
    
    for result in results:
        symbol = result.get('symbol', 'Unknown')
        
        if not result.get('success', False):
            skipped_count += 1
            print(f"❌ {symbol}: Skip (error dalam analisis)")
            continue
        
        # ============================================
        # VALIDASI ML METRICS
        # ============================================
        ml_prediction = result.get('ml_prediction')
        if not ml_prediction:
            skipped_count += 1
            print(f"❌ {symbol}: Tidak ada ML prediction - SKIP")
            continue
        
        accuracy = ml_prediction.get('accuracy')
        sharpe_ml = ml_prediction.get('sharpe_ratio')
        expected_value = ml_prediction.get('expected_value')
        
        # Validasi nilai (accuracy tidak wajib, hanya sharpe dan expected_value)
        if sharpe_ml is None or expected_value is None:
            skipped_count += 1
            print(f"❌ {symbol}: ML metrics tidak lengkap (Sharpe/Expected Value) - SKIP")
            continue
        
        try:
            # Accuracy tidak perlu divalidasi, hanya untuk display
            if accuracy is not None:
                accuracy = float(accuracy)
            sharpe_ml = float(sharpe_ml)
            expected_value = float(expected_value)
        except (TypeError, ValueError):
            skipped_count += 1
            print(f"❌ {symbol}: ML metrics tidak valid (Sharpe/Expected Value) - SKIP")
            continue
        
        # Cek ML metrics (HARUS SEMUA MEMENUHI - kecuali accuracy yang tidak divalidasi)
        # Accuracy TIDAK DIVALIDASI - berapapun tetap lolos
        ml_sharpe_ok = sharpe_ml >= min_sharpe_ml
        ml_expected_ok = expected_value > min_expected_value
        
        if not (ml_sharpe_ok and ml_expected_ok):
            skipped_count += 1
            print(f"❌ {symbol}: ML metrics TIDAK memenuhi kriteria ketat:")
            accuracy_display = f"{accuracy:.1f}%" if accuracy is not None else "N/A"
            print(f"      - Accuracy: {accuracy_display} (TIDAK DIVALIDASI - berapapun tetap lolos)")
            print(f"      - Sharpe: {sharpe_ml:.2f} (min: {min_sharpe_ml}) {'✅' if ml_sharpe_ok else '❌'}")
            print(f"      - Expected Value: {expected_value:.2f}% (min: >{min_expected_value}%) {'✅' if ml_expected_ok else '❌'}")
            print(f"   ⏭️  SKIP - tidak akan dikirim ke AI dan Telegram")
            continue
        
        # ============================================
        # VALIDASI BACKTESTING METRICS
        # ============================================
        backtest_results = result.get('backtest_results')
        
        if not backtest_results:
            skipped_count += 1
            print(f"❌ {symbol}: Tidak ada backtesting results - SKIP")
            print(f"   💡 Backtesting WAJIB untuk validasi kuantitatif")
            continue
        
        sharpe_backtest = backtest_results.get('sharpe_ratio_after')
        sortino_backtest = backtest_results.get('sortino_ratio_after')
        max_dd = backtest_results.get('max_drawdown')
        win_rate = backtest_results.get('win_rate')
        return_after = backtest_results.get('return_after_costs')
        
        # Validasi backtesting metrics
        backtest_sharpe_ok = sharpe_backtest is not None and sharpe_backtest >= min_sharpe_backtest
        backtest_sortino_ok = sortino_backtest is not None and sortino_backtest >= min_sortino_backtest
        backtest_dd_ok = max_dd is None or max_dd < max_drawdown_pct
        backtest_winrate_ok = win_rate is None or win_rate >= min_win_rate
        backtest_return_ok = return_after is not None and return_after > min_return_after_costs
        
        if not (backtest_sharpe_ok and backtest_sortino_ok and backtest_dd_ok and backtest_winrate_ok and backtest_return_ok):
            skipped_count += 1
            print(f"❌ {symbol}: Backtesting metrics TIDAK memenuhi kriteria ketat:")
            print(f"      - Sharpe (After): {sharpe_backtest:.2f if sharpe_backtest else 'N/A'} (min: {min_sharpe_backtest}) {'✅' if backtest_sharpe_ok else '❌'}")
            print(f"      - Sortino (After): {sortino_backtest:.2f if sortino_backtest else 'N/A'} (min: {min_sortino_backtest}) {'✅' if backtest_sortino_ok else '❌'}")
            print(f"      - Max Drawdown: {max_dd:.2f if max_dd else 'N/A'}% (max: <{max_drawdown_pct}%) {'✅' if backtest_dd_ok else '❌'}")
            print(f"      - Win Rate: {win_rate:.1f if win_rate else 'N/A'}% (min: {min_win_rate}%) {'✅' if backtest_winrate_ok else '❌'}")
            print(f"      - Return After Costs: {return_after:.2f if return_after else 'N/A'}% (min: >{min_return_after_costs}%) {'✅' if backtest_return_ok else '❌'}")
            print(f"   ⏭️  SKIP - tidak akan dikirim ke AI dan Telegram")
            continue
        
        # ============================================
        # SEMUA KRITERIA TERPENUHI
        # ============================================
        print(f"✅ {symbol}: SEMUA kriteria terpenuhi!")
        accuracy_display = f"{accuracy:.1f}%" if accuracy is not None else "N/A"
        print(f"   ML Metrics: Accuracy={accuracy_display}, Sharpe={sharpe_ml:.2f}, EV={expected_value:.2f}%")
        print(f"   Backtesting: Sharpe={sharpe_backtest:.2f}, Sortino={sortino_backtest:.2f}, Return={return_after:.2f}%")
        if max_dd:
            print(f"   Max DD: {max_dd:.2f}%, Win Rate: {win_rate:.1f}%")
        print(f"   ✅ Coin ini akan dikirim ke AI dan Telegram")
        
        # Validasi trading setup
        setup = result.get('trading_setup')
        price_info = result.get('price_info', {})
        current_price = price_info.get('current_price')
        
        if setup:
            if not validate_trading_setup(setup, current_price):
                print(f"   ⚠️  [WARNING] Trading setup tidak valid, tapi tetap kirim karena metrics bagus")
                result['setup_warning'] = True
        
        filtered_results.append(result)
    
    # Hanya print summary jika print_summary=True (untuk final summary di akhir)
    if print_summary:
        print("\n" + "=" * 70)
        print("📊 SUMMARY FILTERING (KRITERIA KETAT):")
        print(f"   ✅ Coin yang memenuhi SEMUA kriteria: {len(filtered_results)}")
        print(f"   ❌ Coin yang di-skip: {skipped_count}")
        print(f"   📈 Total coin dianalisis: {len(results)}")
        print("=" * 70)
        print()
    
    return filtered_results


def _extract_price_info(result: Dict) -> tuple:
    """
    Extract price information from result
    
    Returns:
        Tuple of (current_price, support, resistance, timeframe)
    """
    price_info = result.get('price_info', {})
    current_price = price_info.get('current_price')
    support = price_info.get('support')
    resistance = price_info.get('resistance')
    timeframe = price_info.get('timeframe')
    
    if not current_price and result.get('trading_setup'):
        setup = result['trading_setup']
        if 'entry2' in setup:
            current_price = setup.get('entry2')
    
    return current_price, support, resistance, timeframe


def _get_pullback_status(result: Dict) -> Optional[Dict]:
    """
    Get pullback status from result data
    
    Returns:
        Pullback status dict or None
    """
    try:
        if 'data' in result and result['data'] is not None and len(result['data']) > 0:
            from src.utils.pullback_detection import get_current_pullback_status
            return get_current_pullback_status(result['data'])
    except Exception:
        pass
    return None


def _process_single_result(result: Dict, bot: TelegramBot) -> bool:
    """
    Process and send a single analysis result to Telegram
    
    Returns:
        True if successful, False otherwise
    """
    symbol = result['symbol']
    
    if not result['success']:
        error_msg = f"❌ <b>Error untuk {symbol}:</b> {result.get('error', 'Unknown error')}"
        bot.send_message(error_msg)
        return False
    
    deepseek_rec_dict = None
    if result.get('deepseek_recommendation'):
        deepseek_rec_str = result['deepseek_recommendation']
        deepseek_rec_dict = parse_deepseek_recommendation_string(deepseek_rec_str)
    
    current_price, support, resistance, timeframe = _extract_price_info(result)
    pullback_status_data = _get_pullback_status(result)
    
    message = bot.format_simplified_trading_signal(
        symbol=symbol,
        timeframe=timeframe,
        current_price=current_price,
        support=support,
        resistance=resistance,
        trading_setup=result.get('trading_setup'),
        deepseek_recommendation=deepseek_rec_dict,
        ml_prediction=result.get('ml_prediction'),
        recent_trades_analysis=result.get('recent_trades_analysis'),
        pullback_status=pullback_status_data
    )
    
    bot.send_message(message)
    return True


def _process_single_coin(
    coin_data: Dict,
    index: int,
    total: int,
    trading_style: Optional[str],
    bot: Optional[TelegramBot],
    results_lock: threading.Lock,
    passed_lock: threading.Lock,
    failed_lock: threading.Lock
) -> Dict:
    """
    Process single coin analysis (thread-safe)
    
    Args:
        coin_data: Coin data dict dengan 'symbol' key
        index: Index coin (1-based)
        total: Total jumlah coins
        trading_style: Trading style untuk analisis
        bot: Telegram bot instance (thread-safe)
        results_lock: Lock untuk thread-safe append ke results
        passed_lock: Lock untuk thread-safe increment passed_count
        failed_lock: Lock untuk thread-safe increment failed_count
    
    Returns:
        Analysis result dict
    """
    symbol = coin_data['symbol']
    result = None
    
    try:
        print(f"\n{'='*70}")
        print(f"[{index}/{total}] Menganalisis {symbol}...")
        print(f"{'='*70}")
        
        # Analisis coin
        result = run_analysis_for_coin(symbol, trading_style=trading_style)
        
        if not result:
            result = {'symbol': symbol, 'success': False, 'error': 'No result returned'}
        
        # Filter langsung (cek apakah coin ini lolos kriteria ketat)
        filtered_single = filter_analysis_results_by_metrics([result], print_summary=False)
        
        if filtered_single:
            # Coin lolos filter ketat!
            with passed_lock:
                pass  # Increment akan dilakukan di caller
            
            result = filtered_single[0]  # Ambil hasil yang sudah terfilter
            
            print(f"\n✅ {symbol}: LOLOS FILTER KETAT!")
            print(f"   Langsung memproses AI dan mengirim ke Telegram...")
            
            # Panggil AI DeepSeek untuk coin yang lolos filter
            if ENABLE_DEEPSEEK_AI and DEEPSEEK_API_KEY:
                if not result.get('deepseek_recommendation'):
                    print(f"🤖 {symbol}: Memanggil AI DeepSeek...")
                    try:
                        # Convert symbol format (COINUSDT -> COIN-USD untuk SYMBOL)
                        if symbol.endswith('USDT'):
                            coin_name = symbol.replace('USDT', '')
                            symbol_for_config = f"{coin_name}-USD"
                        else:
                            symbol_for_config = symbol
                        
                        # Jalankan analisis_quant.py lagi untuk bagian AI
                        analysis_script = os.path.join(project_root, 'src', 'analysis', 'analisis_quant.py')
                        env_vars = {
                            **os.environ,
                            'RUN_FROM_MASTER_SCRIPT': '1',
                            'TRADING_SYMBOL': symbol,
                            'SYMBOL': symbol_for_config
                        }
                        ai_result = subprocess.run(
                            [sys.executable, analysis_script],
                            capture_output=True,
                            text=True,
                            timeout=AI_TIMEOUT,
                            cwd=project_root,
                            env=env_vars
                        )
                        
                        if ai_result.stdout:
                            deepseek_rec = extract_deepseek_recommendation_from_output(ai_result.stdout)
                            if deepseek_rec:
                                result['deepseek_recommendation'] = deepseek_rec
                                print(f"   ✅ AI recommendation berhasil didapat")
                            else:
                                print(f"   ⚠️  AI recommendation tidak ditemukan di output")
                        else:
                            print(f"   ⚠️  Tidak ada output dari analisis_quant.py")
                            
                    except Exception as e:
                        print(f"   ❌ Error memanggil AI: {e}")
            
            # Kirim langsung ke Telegram (thread-safe)
            if bot:
                try:
                    print(f"📱 {symbol}: Mengirim ke Telegram...")
                    send_analysis_results_to_telegram([result], bot)
                    result['_sent_to_telegram'] = True
                    print(f"   ✅ {symbol} berhasil dikirim ke Telegram")
                except Exception as e:
                    print(f"   ❌ Error mengirim ke Telegram: {e}")
        else:
            # Coin tidak lolos filter
            with failed_lock:
                pass  # Increment akan dilakukan di caller
            print(f"\n❌ {symbol}: TIDAK memenuhi kriteria ketat")
            print(f"   ⏭️  Skip - tidak akan dikirim ke AI dan Telegram")
    
    except Exception as e:
        print(f"❌ Error processing {symbol}: {e}")
        import traceback
        traceback.print_exc()
        if not result:
            result = {'symbol': symbol, 'success': False, 'error': str(e)}
    
    return result


def send_analysis_results_to_telegram(results: List[Dict], bot: TelegramBot) -> bool:
    """
    Kirim hasil analisis ke Telegram dengan format yang disederhanakan
    
    Args:
        results: List of analysis results
        bot: TelegramBot instance
    
    Returns:
        True jika berhasil, False jika gagal
    """
    if not results:
        return False
    
    try:
        for i, result in enumerate(results, 1):
            _process_single_result(result, bot)
            
            if i < len(results):
                time.sleep(1)
        
        return True
        
    except Exception as e:
        print(f"❌ Error mengirim ke Telegram: {e}")
        import traceback
        traceback.print_exc()
        return False


def analyze_screened_coins(
    coins: Optional[List[str]] = None,
    days: int = 90,
    top_n: int = 50,
    trade_direction: str = "both",
    max_coins: int = 100,  # Limit jumlah coin yang dianalisis
    send_to_telegram: bool = True,
    trading_style: Optional[str] = "DAY_TRADING",  # Default: DAY_TRADING untuk analisis screened coins
    skip_screening: bool = False,  # NEW: Skip screening, langsung analisis semua coins
    batch_size: Optional[int] = None  # NEW: Batch size untuk parallel processing (default: dari config atau 10)
) -> List[Dict]:
    """
    Screen coins dan analisis hasilnya (atau langsung analisis tanpa screening)
    
    Args:
        coins: List of coins (default: None = use Binance top coins)
        days: Days untuk screening (tidak digunakan jika skip_screening=True)
        top_n: Top N coins dari screening (tidak digunakan jika skip_screening=True)
        trade_direction: "long", "short", atau "both" (tidak digunakan jika skip_screening=True)
        max_coins: Maximum jumlah coin yang dianalisis (default: 100)
        send_to_telegram: Kirim hasil ke Telegram (default: True)
        trading_style: Trading style untuk analisis (default: "DAY_TRADING")
                       Pilihan: "SCALPING", "DAY_TRADING", "INTRADAY_TRADING", "SWING_TRADING", "POSITION_TRADING"
        skip_screening: Skip screening, langsung analisis semua coins (default: False)
        batch_size: Batch size untuk parallel processing (default: dari config atau 10)
                    Jika None, akan menggunakan ANALYSIS_BATCH_SIZE dari config
                    Jika 1, akan menggunakan sequential processing (satu per satu)
    
    Returns:
        List of analysis results
    """
    print(f"\n{'='*70}")
    if skip_screening:
        print("🚀 LANGSUNG ANALISIS COINS (TANPA SCREENING)")
    else:
        print("🔍 SCREENING & ANALISIS COINS")
    print(f"{'='*70}")
    print(f"📅 Days: {days}")
    if not skip_screening:
        print(f"📊 Top N: {top_n}")
        print(f"📈 Direction: {trade_direction}")
    print(f"🔢 Max coins to analyze: {max_coins}")
    print(f"⚙️  Trading Style: {trading_style}")
    print(f"⏭️  Skip Screening: {skip_screening}")
    print()
    
    # Jika skip_screening, langsung ambil semua coins dari list
    if skip_screening:
        print("🚀 Mode: LANGSUNG ANALISIS (Skip Screening)")
        print("   Langsung analisis semua coins tanpa screening")
        print()
        
        # Load coins dari Binance atau default
        if coins is None:
            from src.screening.coin_screening import load_binance_coins, BINANCE_COINS, DEFAULT_COINS
            coins_list = BINANCE_COINS if BINANCE_COINS else DEFAULT_COINS
            if not coins_list:
                print("❌ Tidak ada coins tersedia")
                return []
            print(f"✅ Loaded {len(coins_list)} coins dari Binance list")
        else:
            coins_list = coins
            print(f"✅ Menggunakan {len(coins_list)} coins yang diberikan")
        
        # Convert ke format yang diharapkan (list of dict dengan 'symbol')
        coins_to_analyze = [{'symbol': coin} for coin in coins_list]
        
        # Limit jika max_coins di-specify (jika None, analisis semua)
        if max_coins is not None and max_coins > 0 and max_coins < len(coins_to_analyze):
            coins_to_analyze = coins_to_analyze[:max_coins]
            print(f"📊 Membatasi analisis ke {max_coins} coins pertama dari {len(coins_list)} total")
        else:
            print(f"📊 Akan menganalisis SEMUA {len(coins_to_analyze)} coins (tidak ada limit)")
        
        print(f"📊 Total coins yang akan dianalisis: {len(coins_to_analyze)}")
        print()
    else:
        # 1. Screen coins (mode normal)
        print("🔍 Step 1: Screening coins...")
        screened_results = screen_coins(
            coins=coins,
            days=days,
            top_n=top_n,
            trade_direction=trade_direction,
            data_source=DATA_SOURCE,
            api_key=BINANCE_API_KEY,
            api_secret=BINANCE_API_SECRET,
            use_adaptive_filtering=True
        )
        
        if not screened_results:
            print("❌ Tidak ada coin yang memenuhi criteria screening")
            if send_to_telegram and ENABLE_TELEGRAM_BOT and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                bot = TelegramBot(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
                bot.send_message("❌ <b>Tidak ada coin yang memenuhi criteria screening</b>\n\n💡 Coba ubah filter criteria atau coba lagi nanti")
            return []
        
        print(f"✅ Ditemukan {len(screened_results)} coins")
        print()
        
        # 2. Analisis setiap coin dengan REAL-TIME processing
        # Alur: Analisis → Filter → AI → Telegram → Next Coin
        # Jika max_coins >= len(screened_results), analisis semua
        if max_coins and max_coins < len(screened_results):
            coins_to_analyze = screened_results[:max_coins]
            print(f"📊 Step 2: Menganalisis {len(coins_to_analyze)} coins dari {len(screened_results)} hasil screening...")
        else:
            coins_to_analyze = screened_results
            print(f"📊 Step 2: Menganalisis SEMUA {len(coins_to_analyze)} coins hasil screening...")
        print()
    
    # REAL-TIME processing untuk semua coins (baik dari screening atau langsung)
    print("🔄 Mode: REAL-TIME Processing")
    print("   Setiap coin yang lolos filter akan langsung diproses AI dan dikirim ke Telegram")
    print()
    print("🔄 Mode: REAL-TIME Processing")
    print("   Setiap coin yang lolos filter akan langsung diproses AI dan dikirim ke Telegram")
    print()
    
    # Initialize Telegram bot sekali untuk semua coin (thread-safe)
    bot = None
    if send_to_telegram and ENABLE_TELEGRAM_BOT and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        bot = TelegramBot(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
    
    # Set batch size (default: 10 untuk /analyze_cycle, atau dari config)
    if batch_size is None:
        batch_size = ANALYSIS_BATCH_SIZE if ANALYSIS_BATCH_SIZE > 1 else 10
    
    # Jika batch_size = 1, gunakan sequential processing (satu per satu)
    use_parallel = batch_size > 1
    
    analysis_results = []
    passed_count = 0
    failed_count = 0
    
    # Thread-safe locks
    results_lock = threading.Lock()
    passed_lock = threading.Lock()
    failed_lock = threading.Lock()
    
    if use_parallel:
        # PARALLEL PROCESSING MODE (batch processing)
        print(f"🚀 Mode: PARALLEL Processing (Batch Size: {batch_size})")
        print(f"   {batch_size} coins akan dianalisis bersamaan per batch")
        print(f"   ⏱️  Delay: 4 detik antara setiap coin dalam batch (untuk menghindari rate limit)")
        print()
        
        # Process coins in batches
        total_coins = len(coins_to_analyze)
        num_batches = (total_coins + batch_size - 1) // batch_size  # Ceiling division
        
        for batch_num in range(num_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, total_coins)
            batch = coins_to_analyze[start_idx:end_idx]
            
            print(f"\n{'='*70}")
            print(f"📦 BATCH {batch_num + 1}/{num_batches} ({len(batch)} coins)")
            print(f"{'='*70}")
            
            # Process batch dengan ThreadPoolExecutor dengan staggered start (delay per coin)
            # Ini untuk menghindari rate limit dari Binance API
            batch_delay_seconds = ANALYSIS_BATCH_DELAY  # Delay antara setiap coin dalam batch (dari config)
            
            with ThreadPoolExecutor(max_workers=batch_size) as executor:
                futures = []
                for i, coin_data in enumerate(batch, start=start_idx + 1):
                    # Staggered start: setiap coin mulai dengan delay 4 detik dari coin sebelumnya
                    if i > start_idx + 1:  # Skip delay untuk coin pertama dalam batch
                        time.sleep(batch_delay_seconds)
                    
                    future = executor.submit(
                        _process_single_coin,
                        coin_data,
                        i,
                        total_coins,
                        trading_style,
                        bot,
                        results_lock,
                        passed_lock,
                        failed_lock
                    )
                    futures.append(future)
                
                # Collect results as they complete
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        if result:
                            with results_lock:
                                analysis_results.append(result)
                            
                            # Count passed/failed
                            filtered_single = filter_analysis_results_by_metrics([result], print_summary=False)
                            if filtered_single:
                                with passed_lock:
                                    passed_count += 1
                            else:
                                with failed_lock:
                                    failed_count += 1
                    except Exception as e:
                        print(f"❌ Error in future: {e}")
                        with failed_lock:
                            failed_count += 1
            
            # Small delay antara batches
            if batch_num < num_batches - 1:
                time.sleep(1)
    else:
        # SEQUENTIAL PROCESSING MODE (satu per satu)
        print("🔄 Mode: SEQUENTIAL Processing (satu per satu)")
        print()
        
        for i, coin_data in enumerate(coins_to_analyze, 1):
            result = _process_single_coin(
                coin_data,
                i,
                len(coins_to_analyze),
                trading_style,
                bot,
                results_lock,
                passed_lock,
                failed_lock
            )
            
            if result:
                analysis_results.append(result)
                
                # Count passed/failed
                filtered_single = filter_analysis_results_by_metrics([result], print_summary=False)
                if filtered_single:
                    passed_count += 1
                else:
                    failed_count += 1
            
            # Small delay antara analisis
            if i < len(coins_to_analyze):
                time.sleep(2)
    
    # Summary
    print(f"\n{'='*70}")
    print(f"📊 SUMMARY ANALISIS")
    print(f"{'='*70}")
    print(f"   Total coin dianalisis: {len(coins_to_analyze)}")
    print(f"   ✅ Lolos filter ketat: {passed_count}")
    print(f"   ❌ Tidak memenuhi kriteria: {failed_count}")
    print(f"{'='*70}")
    print()
    
    # 3. Filter hasil berdasarkan metrics (untuk return value - sudah diproses real-time di atas)
    # Print summary di akhir (setelah semua coin selesai dianalisis)
    filtered_results = filter_analysis_results_by_metrics(analysis_results, print_summary=True)
    
    # 4. Panggil AI DeepSeek untuk coin yang LOLOS filter ketat (jika belum dipanggil)
    # (Ini untuk backup jika ada yang terlewat)
    if ENABLE_DEEPSEEK_AI and DEEPSEEK_API_KEY:
        print(f"\n{'='*70}")
        print("🤖 MEMASTIKAN AI RECOMMENDATION UNTUK COIN YANG LOLOS FILTER")
        print(f"{'='*70}")
        
        for result in filtered_results:
            symbol = result.get('symbol', 'Unknown')
            
            # Jika sudah ada AI recommendation, skip
            if result.get('deepseek_recommendation'):
                print(f"✅ {symbol}: Sudah ada AI recommendation")
                continue
            
            # Panggil AI untuk coin yang lolos filter tapi belum dapat AI
            print(f"🤖 {symbol}: Memanggil AI DeepSeek (backup)...")
            try:
                # Convert symbol format (COINUSDT -> COIN-USD untuk SYMBOL)
                if symbol.endswith('USDT'):
                    coin_name = symbol.replace('USDT', '')
                    symbol_for_config = f"{coin_name}-USD"
                else:
                    symbol_for_config = symbol
                
                analysis_script = os.path.join(project_root, 'src', 'analysis', 'analisis_quant.py')
                env_vars = {
                    **os.environ,
                    'RUN_FROM_MASTER_SCRIPT': '1',
                    'TRADING_SYMBOL': symbol,  # Set trading symbol
                    'SYMBOL': symbol_for_config  # Set symbol untuk config
                }
                ai_result = subprocess.run(
                    [sys.executable, analysis_script],
                    capture_output=True,
                    text=True,
                    timeout=AI_TIMEOUT,
                    cwd=project_root,
                    env=env_vars
                )
                
                if ai_result.stdout:
                    deepseek_rec = extract_deepseek_recommendation_from_output(ai_result.stdout)
                    if deepseek_rec:
                        result['deepseek_recommendation'] = deepseek_rec
                        print(f"   ✅ AI recommendation berhasil didapat")
                    else:
                        print(f"   ⚠️  AI recommendation tidak ditemukan di output")
                else:
                    print(f"   ⚠️  Tidak ada output dari analisis_quant.py")
                    
            except Exception as e:
                print(f"   ❌ Error memanggil AI: {e}")
    
    # 5. Kirim hasil ke Telegram (backup - untuk coin yang mungkin terlewat)
    if send_to_telegram and ENABLE_TELEGRAM_BOT and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        if filtered_results:
            # Cek apakah ada coin yang belum dikirim
            unsent_results = [r for r in filtered_results if not r.get('_sent_to_telegram', False)]
            if unsent_results:
                print("\n📱 Mengirim hasil yang terlewat ke Telegram...")
                if not bot:
                    bot = TelegramBot(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
                send_analysis_results_to_telegram(unsent_results, bot)
                print(f"✅ {len(unsent_results)} coin yang terlewat dikirim ke Telegram")
            else:
                print("\n✅ Semua coin yang lolos filter sudah dikirim ke Telegram (real-time)")
        else:
            print("\n⚠️  Tidak ada coin yang memenuhi kriteria untuk dikirim ke Telegram")
            bot = TelegramBot(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
            bot.send_message(
                "⚠️ <b>Tidak ada coin yang memenuhi kriteria ketat</b>\n\n"
                "📋 <b>Kriteria yang harus dipenuhi (SEMUA):</b>\n\n"
                "<b>ML Metrics:</b>\n"
                "   - Accuracy: TIDAK DIVALIDASI (berapapun tetap lolos)\n"
                "   - Sharpe Ratio >= 0.5\n"
                "   - Expected Value > 0%\n\n"
                "<b>Backtesting Metrics:</b>\n"
                "   - Sharpe Ratio (After Costs) >= 0.5\n"
                "   - Sortino Ratio (After Costs) >= 1.5\n"
                "   - Max Drawdown < 20%\n"
                "   - Win Rate >= 55%\n"
                "   - Return After Costs > 0%\n\n"
                "💡 Semua coin yang dianalisis tidak memenuhi SEMUA kriteria di atas.\n"
                "🔍 Coba analisis lagi nanti atau ubah parameter screening."
            )
    
    return analysis_results


if __name__ == "__main__":
    # Test
    results = analyze_screened_coins(
        days=7,
        top_n=3,
        trade_direction="both",
        max_coins=3,
        send_to_telegram=False  # Set False untuk testing
    )
    
    if results:
        print("\n" + "="*70)
        print("📊 HASIL ANALISIS")
        print("="*70)
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result['symbol']}: {'✅' if result['success'] else '❌'}")
