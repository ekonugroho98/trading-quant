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
import subprocess
import json
import time
import re
import glob
from typing import List, Dict, Optional

# Import modules
try:
    from config import (
        TRADING_STYLE, DATA_SOURCE, get_days_back, get_interval,
        BINANCE_API_KEY, BINANCE_API_SECRET,
        ENABLE_DEEPSEEK_AI, DEEPSEEK_API_KEY, DEEPSEEK_MODEL,
        ENABLE_TELEGRAM_BOT, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
    )
    from coin_screening import screen_coins
    from ml_prediction_helper import get_ml_prediction_from_file
    from telegram_bot import TelegramBot
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
        
        # Extract trading setup dari output
        if analysis_result.stdout:
            trading_setup = extract_trading_setup_from_output(analysis_result.stdout, symbol)
            if trading_setup:
                result['trading_setup'] = trading_setup
                print(f"✅ Trading setup ditemukan")
            
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
    Kirim hasil analisis ke Telegram
    
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
            
            # Header untuk setiap coin
            message_parts = []
            message_parts.append(f"📊 <b>ANALISIS COIN #{i}</b>")
            message_parts.append(f"<b>{symbol}</b>")
            message_parts.append("")
            
            if not result['success']:
                message_parts.append(f"❌ <b>Error:</b> {result.get('error', 'Unknown error')}")
                bot.send_message("\n".join(message_parts))
                continue
            
            # TRADING SETUP
            if result['trading_setup']:
                setup = result['trading_setup']
                message_parts.append("📋 <b>TRADING SETUP</b>")
                message_parts.append("-" * 40)
                
                if 'direction' in setup:
                    message_parts.append(f"📈 <b>Direction:</b> {setup['direction']}")
                
                if 'entry1' in setup and 'entry2' in setup and 'entry3' in setup:
                    message_parts.append("💰 <b>MULTIPLE ENTRY LEVELS:</b>")
                    message_parts.append(f"   Entry 1 (Agresif): {setup['entry1']}")
                    message_parts.append(f"   Entry 2 (Konservatif - Recommended): {setup['entry2']}")
                    message_parts.append(f"   Entry 3 (Sangat Konservatif): {setup['entry3']}")
                    message_parts.append("")
                
                if 'stop_loss' in setup:
                    risk_pct = setup.get('risk_pct', 0)
                    message_parts.append(f"🛑 <b>Stop Loss:</b> {setup['stop_loss']} (-{risk_pct:.2f}%)")
                    message_parts.append("")
                
                if 'tp1' in setup and 'tp2' in setup and 'tp3' in setup:
                    message_parts.append("🎯 <b>Targets:</b>")
                    message_parts.append(f"   TP1: {setup['tp1']}")
                    message_parts.append(f"   TP2: {setup['tp2']}")
                    message_parts.append(f"   TP3: {setup['tp3']}")
                    message_parts.append("")
            
            # DEEPSEEK AI RECOMMENDATION
            if result['deepseek_recommendation']:
                message_parts.append("🤖 <b>DEEPSEEK AI TRADING RECOMMENDATION</b>")
                message_parts.append("-" * 40)
                # DeepSeek recommendation sudah dalam format HTML
                message_parts.append(result['deepseek_recommendation'])
                message_parts.append("")
            
            # ML PREDICTION SUMMARY
            if result['ml_prediction']:
                ml = result['ml_prediction']
                message_parts.append("📊 <b>RINGKASAN QUANT MODEL</b>")
                message_parts.append("-" * 40)
                
                if 'data_records' in ml:
                    message_parts.append(f"📊 <b>Data Historis:</b> {ml['data_records']} records")
                
                if 'features_count' in ml:
                    message_parts.append(f"🔧 <b>Feature Engineering:</b> {ml['features_count']} fitur")
                
                model = ml.get('model', ml.get('model_type', 'N/A'))
                message_parts.append(f"🤖 <b>Model:</b> {model}")
                
                signal = ml.get('signal', 'N/A')
                buy_prob = ml.get('buy_probability', ml.get('buy_prob', 0))
                signal_emoji = "🟢" if signal == "BELI" else "🔴" if signal == "JUAL" else "🟡"
                message_parts.append(f"📡 <b>Signal:</b> {signal_emoji} {signal} (Prob: {buy_prob:.1f}%)")
                
                if 'accuracy' in ml:
                    acc = ml['accuracy']
                    if isinstance(acc, float) and acc < 1:
                        acc = acc * 100
                    message_parts.append(f"📈 <b>Accuracy:</b> {acc:.2f}%")
                
                if 'expected_value' in ml:
                    message_parts.append(f"📈 <b>Expected Value:</b> {ml['expected_value']:.2f}%")
                
                if 'sharpe_ratio' in ml:
                    message_parts.append(f"📊 <b>Sharpe Ratio:</b> {ml['sharpe_ratio']:.2f}")
                
                message_parts.append("")
            
            # Kirim pesan (split jika terlalu panjang)
            message = "\n".join(message_parts)
            if len(message) > 4000:  # Telegram limit ~4096 chars
                # Split message
                parts = message.split("\n\n")
                current_part = []
                for part in parts:
                    if len("\n\n".join(current_part + [part])) > 4000:
                        if current_part:
                            bot.send_message("\n\n".join(current_part))
                        current_part = [part]
                    else:
                        current_part.append(part)
                if current_part:
                    bot.send_message("\n\n".join(current_part))
            else:
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
                       Pilihan: "SCALPING", "DAY_TRADING", "SWING_TRADING", "POSITION_TRADING"
    
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
