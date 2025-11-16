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
from typing import List, Dict, Optional

# Import modules
try:
    from src.utils.config import (
        TRADING_STYLE, DATA_SOURCE, get_days_back, get_interval,
        BINANCE_API_KEY, BINANCE_API_SECRET,
        ENABLE_DEEPSEEK_AI, DEEPSEEK_API_KEY, DEEPSEEK_MODEL,
        ENABLE_TELEGRAM_BOT, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
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
        with open('config.py', 'r') as f:
            content = f.read()
        
        # Replace SYMBOL line
        pattern = r'^SYMBOL\s*=\s*["\'][^"\']*["\']'
        replacement = f'SYMBOL = "{symbol}"'
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        
        with open('config.py', 'w') as f:
            f.write(content)
    except Exception as e:
        print(f"⚠️  Error updating config: {e}")


def update_config_trading_style(trading_style: str):
    """Update TRADING_STYLE di config.py"""
    try:
        with open('config.py', 'r') as f:
            content = f.read()
        
        # Replace TRADING_STYLE line
        pattern = r'^TRADING_STYLE\s*=\s*["\'][^"\']*["\']'
        replacement = f'TRADING_STYLE = "{trading_style}"'
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        
        with open('config.py', 'w') as f:
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
        data_result = subprocess.run(
            [sys.executable, "get_historical_data.py"],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if data_result.returncode != 0:
            result['error'] = f"Gagal mengambil data: {data_result.stderr[:200]}"
            print(f"❌ {result['error']}")
            return result
        
        # Cari file CSV yang baru dibuat
        csv_files = [f for f in os.listdir('.') if f.endswith('.csv') and symbol.replace('-', '').lower() in f.lower()]
        if not csv_files:
            result['error'] = "File CSV tidak ditemukan setelah get_historical_data"
            print(f"❌ {result['error']}")
            return result
        
        csv_file = max(csv_files, key=os.path.getctime)
        print(f"✅ Data historical: {csv_file}")
        
        # 3. Jalankan analisis_quant.py dengan output capture
        print(f"🔍 Menjalankan analisis quant untuk {symbol}...")
        analysis_result = subprocess.run(
            [sys.executable, "analisis_quant.py"],
            capture_output=True,
            text=True,
            timeout=300,
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
        
        if analysis_result.returncode != 0:
            print(f"⚠️  Warning: analisis_quant.py exit dengan code {analysis_result.returncode}")
            # Continue anyway untuk coba extract hasil
        
        # 4. Jalankan prediksi_next_day.py
        print(f"🤖 Menjalankan ML prediction untuk {symbol}...")
        pred_result = subprocess.run(
            [sys.executable, "prediksi_next_day.py"],
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, 'RUN_FROM_MASTER_SCRIPT': '1'}
        )
        
        time.sleep(1)  # Tunggu file JSON ditulis
        
        # 5. Load ML prediction result
        ml_prediction = get_ml_prediction_from_file()
        if ml_prediction:
            result['ml_prediction'] = ml_prediction
            print(f"✅ ML prediction ditemukan")
        
        # 6. Cleanup CSV file
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
            symbol = result['symbol']
            
            if not result['success']:
                error_msg = f"❌ <b>Error untuk {symbol}:</b> {result.get('error', 'Unknown error')}"
                bot.send_message(error_msg)
                continue
            
            # Parse DeepSeek recommendation string menjadi dict
            deepseek_rec_dict = None
            if result.get('deepseek_recommendation'):
                deepseek_rec_str = result['deepseek_recommendation']
                deepseek_rec_dict = parse_deepseek_recommendation_string(deepseek_rec_str)
            
            # Extract current_price, support, resistance dari price_info atau trading_setup
            price_info = result.get('price_info', {})
            current_price = price_info.get('current_price')
            support = price_info.get('support')
            resistance = price_info.get('resistance')
            timeframe = price_info.get('timeframe')
            
            # Fallback: coba ambil dari trading_setup (jika price_info tidak ada)
            if not current_price and result.get('trading_setup'):
                setup = result['trading_setup']
                # Gunakan entry2 (konservatif) sebagai estimasi current price
                if 'entry2' in setup:
                    current_price = setup.get('entry2')
            
            # Format menggunakan fungsi baru yang disederhanakan
            message = bot.format_simplified_trading_signal(
                symbol=symbol,
                timeframe=timeframe,
                current_price=current_price,
                support=support,
                resistance=resistance,
                trading_setup=result.get('trading_setup'),
                deepseek_recommendation=deepseek_rec_dict,
                ml_prediction=result.get('ml_prediction')
            )
            
            # Kirim pesan
            bot.send_message(message)
            
            # Delay antar pesan
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
    top_n: int = 5,
    trade_direction: str = "both",
    max_coins: int = 10,  # Limit jumlah coin yang dianalisis
    send_to_telegram: bool = True,
    trading_style: Optional[str] = "DAY_TRADING"  # Default: DAY_TRADING untuk analisis screened coins
) -> List[Dict]:
    """
    Screen coins dan analisis hasilnya
    
    Args:
        coins: List of coins (default: None = use Binance top coins)
        days: Days untuk screening
        top_n: Top N coins dari screening
        trade_direction: "long", "short", atau "both"
        max_coins: Maximum jumlah coin yang dianalisis (default: 10)
        send_to_telegram: Kirim hasil ke Telegram (default: True)
        trading_style: Trading style untuk analisis (default: "DAY_TRADING")
                       Pilihan: "SCALPING", "DAY_TRADING", "INTRADAY_TRADING", "SWING_TRADING", "POSITION_TRADING"
    
    Returns:
        List of analysis results
    """
    print(f"\n{'='*70}")
    print("🔍 SCREENING & ANALISIS COINS")
    print(f"{'='*70}")
    print(f"📅 Days: {days}")
    print(f"📊 Top N: {top_n}")
    print(f"📈 Direction: {trade_direction}")
    print(f"🔢 Max coins to analyze: {max_coins}")
    print(f"⚙️  Trading Style: {trading_style}")
    print()
    
    # 1. Screen coins
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
    
    # 2. Analisis setiap coin (limit ke max_coins)
    coins_to_analyze = screened_results[:max_coins]
    print(f"📊 Step 2: Menganalisis {len(coins_to_analyze)} coins...")
    print()
    
    analysis_results = []
    for i, coin_data in enumerate(coins_to_analyze, 1):
        symbol = coin_data['symbol']
        print(f"\n[{i}/{len(coins_to_analyze)}] Menganalisis {symbol}...")
        
        result = run_analysis_for_coin(symbol, trading_style=trading_style)
        analysis_results.append(result)
        
        # Small delay antara analisis
        if i < len(coins_to_analyze):
            time.sleep(2)
    
    # 3. Kirim hasil ke Telegram
    if send_to_telegram and ENABLE_TELEGRAM_BOT and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        print("\n📱 Mengirim hasil ke Telegram...")
        bot = TelegramBot(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
        send_analysis_results_to_telegram(analysis_results, bot)
        print("✅ Hasil dikirim ke Telegram")
    
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
