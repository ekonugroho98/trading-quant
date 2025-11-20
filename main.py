#!/usr/bin/env python3
"""
Main Entry Point untuk Trading Quant Bot
Menerima input dari Telegram dan menjalankan analisis untuk coin yang diminta
"""

import os
import sys

# Add project root to Python path to enable src imports
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import time
import json
import requests
import subprocess
import re
from typing import Optional, List, Dict
from src.utils.config import ENABLE_TELEGRAM_BOT, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, SYMBOL as DEFAULT_SYMBOL


class TradingBot:
    """Bot untuk menerima command dari Telegram dan menjalankan analisis"""
    
    def __init__(self, bot_token: str):
        """
        Initialize Trading Bot
        
        Args:
            bot_token: Telegram Bot Token dari @BotFather
        """
        self.bot_token = bot_token
        self.api_url = f"https://api.telegram.org/bot{bot_token}"
        self.offset = 0
        self.running = False
        self.active_users = set()  # Set untuk menyimpan chat_id user yang sudah /start
        self.user_trading_styles = {}  # Dictionary untuk menyimpan TRADING_STYLE per user
        self.valid_trading_styles = ["SCALPING", "DAY_TRADING", "INTRADAY_TRADING", "SWING_TRADING", "POSITION_TRADING"]
    
    def get_updates(self) -> Optional[dict]:
        """
        Ambil update terbaru dari Telegram dengan retry mechanism
        
        Returns:
            Dictionary dengan updates atau None jika error
        """
        max_retries = 3
        retry_delay = 2  # detik
        
        for attempt in range(max_retries):
            try:
                url = f"{self.api_url}/getUpdates"
                params = {
                    "offset": self.offset,
                    "timeout": 10,
                    "allowed_updates": ["message"]  # Hanya ambil message updates untuk mengurangi konflik
                }
                # Increase timeout untuk koneksi yang lambat
                response = requests.get(url, params=params, timeout=30)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 409:
                    # Conflict: biasanya karena offset tidak valid atau bot lain sedang polling
                    # Coba dapatkan update terbaru untuk sinkronisasi offset
                    print(f"⚠️  Conflict (409): Mencoba sinkronisasi offset...")
                    try:
                        # Coba get updates tanpa offset untuk mendapatkan update_id terbaru
                        sync_url = f"{self.api_url}/getUpdates"
                        sync_params = {"limit": 1, "timeout": 1, "allowed_updates": ["message"]}
                        sync_response = requests.get(sync_url, params=sync_params, timeout=10)
                        if sync_response.status_code == 200:
                            sync_data = sync_response.json()
                            if sync_data.get('ok') and sync_data.get('result'):
                                # Update offset ke update_id terbaru + 1
                                latest_update_id = sync_data['result'][-1].get('update_id', 0)
                                self.offset = latest_update_id + 1
                                print(f"   ✅ Offset disinkronkan ke: {self.offset}")
                            else:
                                # Tidak ada update, reset ke 0
                                self.offset = 0
                                print(f"   ✅ Offset direset ke: 0")
                        else:
                            # Gagal sinkronisasi, reset offset
                            self.offset = 0
                            print(f"   ⚠️  Gagal sinkronisasi, offset direset")
                    except Exception as e:
                        # Jika sinkronisasi gagal, reset offset
                        self.offset = 0
                        print(f"   ⚠️  Error sinkronisasi: {e}, offset direset")
                    
                    # Tunggu lebih lama sebelum retry untuk menghindari konflik
                    wait_time = 5 + (attempt * 2)
                    if attempt < max_retries - 1:
                        print(f"   ⏳ Menunggu {wait_time}s sebelum retry...")
                        time.sleep(wait_time)
                        continue
                    return None
                else:
                    print(f"❌ Error mendapatkan updates: {response.status_code}")
                    if response.status_code == 401:
                        print("   ⚠️  Bot token mungkin tidak valid")
                    elif response.status_code == 429:
                        print("   ⚠️  Rate limit exceeded, tunggu sebentar...")
                        time.sleep(60)  # Wait 1 minute for rate limit
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                        continue
                    return None
            except requests.exceptions.ConnectTimeout as e:
                if attempt < max_retries - 1:
                    print(f"⚠️  Connection timeout (attempt {attempt + 1}/{max_retries}), retrying in {retry_delay * (attempt + 1)}s...")
                    time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    print(f"⚠️  Connection timeout setelah {max_retries} attempts. Kemungkinan masalah koneksi internet atau Telegram API.")
                    return None
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    print(f"⚠️  Network error (attempt {attempt + 1}/{max_retries}): {type(e).__name__}, retrying...")
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    print(f"⚠️  Error menghubungi Telegram API setelah {max_retries} attempts: {type(e).__name__}")
                    return None
            except Exception as e:
                print(f"⚠️  Unexpected error menghubungi Telegram API: {e}")
                return None
        
        return None
    
    def send_message(self, chat_id: str, text: str, parse_mode: str = "HTML") -> bool:
        """
        Kirim pesan ke Telegram dengan retry mechanism
        
        Args:
            chat_id: Chat ID tujuan
            text: Text pesan
            parse_mode: Parse mode (HTML atau Markdown)
        
        Returns:
            True jika berhasil, False jika gagal
        """
        max_retries = 3
        retry_delay = 1  # detik
        
        for attempt in range(max_retries):
            try:
                url = f"{self.api_url}/sendMessage"
                payload = {
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": parse_mode
                }
                # Increase timeout untuk koneksi yang lambat
                response = requests.post(url, json=payload, timeout=30)
                success = response.status_code == 200
                if not success:
                    print(f"⚠️  [send_message] HTTP {response.status_code}: {response.text[:200]}")
                return success
            except requests.exceptions.ConnectTimeout as e:
                if attempt < max_retries - 1:
                    print(f"⚠️  Connection timeout saat mengirim pesan (attempt {attempt + 1}/{max_retries}), retrying...")
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    print(f"❌ Connection timeout setelah {max_retries} attempts saat mengirim pesan")
                    return False
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    print(f"⚠️  Network error saat mengirim pesan (attempt {attempt + 1}/{max_retries}): {type(e).__name__}, retrying...")
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    print(f"❌ Error mengirim pesan setelah {max_retries} attempts: {type(e).__name__}")
                    return False
            except Exception as e:
                print(f"❌ Unexpected error mengirim pesan: {e}")
                return False
        
        return False
    
    def parse_symbol(self, text: str) -> Optional[str]:
        """
        Parse symbol dari text message
        
        Args:
            text: Text message dari user
        
        Returns:
            Symbol yang valid (format: BTC-USD) atau None
        """
        if not text:
            return None
        
        text = text.strip().upper()
        
        # Format yang didukung:
        # - BTC-USD
        # - BTC/USD
        # - BTCUSD
        # - BTC (atau coin name apapun)
        
        # Normalize
        if "/" in text:
            text = text.replace("/", "-")
        
        # Jika sudah dalam format COIN-USD, return langsung
        if "-" in text and text.endswith("-USD"):
            return text
        
        # Jika tidak ada "-", berarti format: BTC, BTCUSD, atau coin name
        if "-" not in text:
            # Cek apakah sudah berakhir dengan USD/USDT
            if text.endswith("USDT"):
                # Format: BTCUSDT -> BTC-USD
                text = text[:-4] + "-USD"
            elif text.endswith("USD"):
                # Format: BTCUSD -> BTC-USD
                text = text[:-3] + "-USD"
            else:
                # Format: BTC atau GRIFFAIN -> COIN-USD
                # Tidak ada batasan panjang, semua coin name akan ditambahkan -USD
                text = f"{text}-USD"
        
        # Validasi format akhir: COIN-USD
        if "-" in text and text.endswith("-USD"):
            return text
        
        return None
    
    def parse_multiple_symbols(self, text: str) -> List[str]:
        """
        Parse multiple symbols dari comma-separated text
        
        Args:
            text: Text message dengan multiple symbols dipisahkan koma
                  Contoh: "BTC,ETH,SOL" atau "GALA,ONT,D,BANANA"
        
        Returns:
            List of valid symbols (format: BTC-USD) atau empty list
        """
        if not text:
            return []
        
        # Split by comma
        symbols_raw = [s.strip().upper() for s in text.split(',') if s.strip()]
        
        if len(symbols_raw) <= 1:
            # Hanya satu symbol atau tidak ada, return empty (akan di-handle oleh parse_symbol)
            return []
        
        # Parse setiap symbol menggunakan logic yang sama dengan parse_symbol
        valid_symbols = []
        for symbol_raw in symbols_raw:
            # Gunakan parse_symbol untuk konsistensi
            parsed = self.parse_symbol(symbol_raw)
            if parsed:
                valid_symbols.append(parsed)
            else:
                # Jika parse_symbol return None, coba tambahkan -USD secara langsung
                # (untuk coin names yang tidak terdeteksi oleh parse_symbol)
                symbol = symbol_raw.strip().upper()
                if "/" in symbol:
                    symbol = symbol.replace("/", "-")
                
                # Jika tidak ada "-", tambahkan -USD
                if "-" not in symbol:
                    symbol = f"{symbol}-USD"
                
                # Validasi dan tambahkan jika valid
                if "-" in symbol and symbol.endswith("-USD"):
                    valid_symbols.append(symbol)
        
        return valid_symbols
    
    def run_multiple_analysis(self, symbols: List[str], chat_id: str) -> Dict[str, bool]:
        """
        Jalankan analisis untuk multiple symbols
        
        Args:
            symbols: List of trading symbols (format: BTC-USD)
            chat_id: Chat ID untuk mengirim hasil
        
        Returns:
            Dictionary dengan key=symbol, value=success (True/False)
        """
        results = {}
        
        print(f"📊 [run_multiple_analysis] Starting analysis for {len(symbols)} coins")
        
        for i, symbol in enumerate(symbols, 1):
            print(f"\n{'='*70}")
            print(f"📈 [{i}/{len(symbols)}] Processing {symbol}")
            print(f"{'='*70}")
            
            try:
                result = self.run_analysis(symbol, chat_id)
                results[symbol] = result
                
                if result:
                    print(f"✅ [{i}/{len(symbols)}] {symbol} - Analysis completed successfully")
                else:
                    print(f"❌ [{i}/{len(symbols)}] {symbol} - Analysis failed")
            except Exception as e:
                print(f"❌ [{i}/{len(symbols)}] {symbol} - Error: {e}")
                results[symbol] = False
                
                # Kirim error message ke Telegram
                self.send_message(
                    chat_id,
                    f"❌ <b>Error analisis {symbol}</b>\n\n"
                    f"<code>{str(e)[:200]}</code>"
                )
            
            # Delay kecil antara analisis untuk menghindari rate limit
            if i < len(symbols):
                import time
                time.sleep(2)  # 2 detik delay antara analisis
        
        return results
    
    def run_analysis(self, symbol: str, chat_id: str) -> bool:
        """
        Jalankan analisis untuk symbol tertentu
        
        Args:
            symbol: Trading symbol (format: BTC-USD)
            chat_id: Chat ID untuk mengirim hasil
        
        Returns:
            True jika berhasil, False jika gagal
        """
        try:
            print(f"📊 [run_analysis] Starting analysis for {symbol}, chat_id={chat_id}")
            
            # Kirim notifikasi sedang memproses
            print(f"📤 [run_analysis] Sending processing notification...")
            success = self.send_message(
                chat_id,
                f"🔄 <b>Memproses analisis untuk {symbol}...</b>\n"
                f"⏳ Mohon tunggu, ini mungkin memakan waktu beberapa detik..."
            )
            print(f"{'✅' if success else '❌'} [run_analysis] Processing notification sent: {success}")
            
            # Update config.py dengan symbol baru, chat_id, dan trading style
            print(f"⚙️  [run_analysis] Updating config: SYMBOL={symbol}, CHAT_ID={chat_id}")
            self.update_config_symbol(symbol)
            self.update_config_chat_id(chat_id)
            
            # Update TRADING_STYLE jika user sudah set
            if chat_id in self.user_trading_styles:
                trading_style = self.user_trading_styles[chat_id]
                print(f"⚙️  [run_analysis] Updating TRADING_STYLE={trading_style}")
                self.update_config_trading_style(trading_style)
            else:
                print(f"ℹ️  [run_analysis] No custom TRADING_STYLE for user, using default")
            
            # Tunggu sebentar untuk memastikan file config.py sudah ter-write
            print(f"⏳ [run_analysis] Waiting 1.0s for config file to be written...")
            time.sleep(1.0)  # Increase delay untuk memastikan file ter-write dengan benar
            
            # Verifikasi config sudah ter-update dengan membaca file langsung
            try:
                config_file = "src/utils/config.py"
                with open(config_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if f'SYMBOL = "{symbol}"' in content:
                        print(f"✅ [run_analysis] Config verified: SYMBOL={symbol}")
                    else:
                        print(f"⚠️  [run_analysis] Config verification failed, SYMBOL mungkin belum ter-update")
            except Exception as e:
                print(f"⚠️  [run_analysis] Error verifying config: {e}")
            
            print(f"✅ [run_analysis] Config update completed")
            
            # Verifikasi bahwa config sudah ter-update dengan benar
            try:
                import importlib
                # Force reload config module jika sudah di-import sebelumnya
                if 'src.utils.config' in sys.modules:
                    importlib.reload(sys.modules['src.utils.config'])
                elif 'config' in sys.modules:
                    importlib.reload(sys.modules['config'])
            except:
                pass
            
            # Cek apakah perlu mengambil data historical terlebih dahulu
            # Pastikan file CSV yang ada sesuai dengan symbol yang diminta
            try:
                import glob
                # Cek apakah ada file CSV yang sesuai dengan symbol
                symbol_lower = symbol.replace("-", "").lower() if symbol else ""
                symbol_base = symbol.split("-")[0].lower() if symbol and "-" in symbol else ""
                
                # Cari file CSV yang sesuai dengan symbol
                matching_csv_files = []
                if symbol_lower:
                    matching_csv_files.extend(glob.glob(f"{symbol_lower}_historical_*.csv"))
                if symbol_base:
                    matching_csv_files.extend(glob.glob(f"{symbol_base}_historical_*.csv"))
                
                # Cari semua file CSV
                all_csv_files = glob.glob("*_historical_*.csv")
                
                print(f"📁 [run_analysis] Checking for CSV files:")
                print(f"   Files matching {symbol}: {len(matching_csv_files)}")
                print(f"   Total CSV files: {len(all_csv_files)}")
                
                # Jika tidak ada file yang sesuai dengan symbol, ambil data baru
                if not matching_csv_files:
                    print(f"📥 [run_analysis] No matching CSV file for {symbol}, fetching new data...")
                    success = self.send_message(
                        chat_id,
                        f"📥 <b>Mengambil data historical untuk {symbol}...</b>\n"
                        "⏳ Ini mungkin memakan waktu beberapa detik..."
                    )
                    print(f"{'✅' if success else '❌'} [run_analysis] Historical data notification sent: {success}")
                    
                    print(f"🔄 [run_analysis] Running get_historical_data.py for {symbol}...")
                    # Get project root directory
                    project_root = os.path.dirname(os.path.abspath(__file__))
                    result_data = subprocess.run(
                        [sys.executable, "src/data/get_historical_data.py"],
                        capture_output=True,
                        text=True,
                        timeout=120,  # 2 menit timeout
                        cwd=project_root  # Ensure we're in project root
                    )
                    print(f"📊 [run_analysis] get_historical_data.py completed: returncode={result_data.returncode}")
                    
                    if result_data.returncode == 0:
                        print(f"✅ [run_analysis] Historical data fetched successfully for {symbol}")
                        success = self.send_message(
                            chat_id,
                            f"✅ <b>Data historical untuk {symbol} berhasil diambil</b>\n"
                            "🔄 Melanjutkan ke analisis..."
                        )
                        print(f"{'✅' if success else '❌'} [run_analysis] Success notification sent: {success}")
                    else:
                        # Data tidak berhasil diambil, tampilkan error detail
                        error_output = result_data.stderr[:500] if result_data.stderr else result_data.stdout[-500:] if result_data.stdout else "Unknown error"
                        print(f"⚠️  Warning: Gagal mengambil data historical untuk {symbol}")
                        print(f"   Return code: {result_data.returncode}")
                        print(f"   Error output: {error_output}")
                        
                        # Cek apakah error karena symbol tidak ditemukan
                        error_lower = error_output.lower()
                        if "not found" in error_lower or "no data" in error_lower or "empty" in error_lower:
                            self.send_message(
                                chat_id,
                                f"⚠️ <b>Symbol {symbol} tidak ditemukan atau tidak memiliki data</b>\n\n"
                                f"💡 <b>Kemungkinan penyebab:</b>\n"
                                f"• Symbol tidak valid\n"
                                f"• Coin tidak memiliki data historical\n"
                                f"• Format symbol salah\n\n"
                                f"🔄 <b>Mencoba fallback langsung...</b>"
                            )
                        else:
                            self.send_message(
                                chat_id,
                                f"⚠️ <b>Gagal mengambil data historical untuk {symbol}</b>\n\n"
                                f"🔄 <b>Mencoba fallback langsung...</b>\n\n"
                                f"<code>{error_output[:200]}</code>"
                            )
                        print(f"⚠️  Analisis akan menggunakan data source langsung")
                else:
                    print(f"✅ [run_analysis] Found matching CSV file for {symbol}: {matching_csv_files[0]}")
            except Exception as e:
                # Error mengambil data, tapi lanjutkan saja
                print(f"⚠️  Warning: Error saat mengambil data historical: {e}")
            
            # Jalankan analisis_quant.py
            print(f"🚀 [run_analysis] Running analisis_quant.py...")
            # Get project root directory
            project_root = os.path.dirname(os.path.abspath(__file__))
            result = subprocess.run(
                [sys.executable, "src/analysis/analisis_quant.py"],
                capture_output=True,
                text=True,
                timeout=300,  # 5 menit timeout
                cwd=project_root  # Ensure we're in project root
            )
            print(f"📊 [run_analysis] analisis_quant.py completed: returncode={result.returncode}")
            
            if result.returncode == 0:
                # Analisis berhasil, hasil sudah dikirim otomatis oleh analisis_quant.py
                print(f"✅ [run_analysis] Analysis completed successfully for {symbol}")
                
                # DISABLED: Untuk request satuan (single coin), tidak ada filter/threshold
                # Semua hasil analisis akan dikirim ke Telegram tanpa memandang kriteria
                # Cek kriteria hanya untuk batch request (/analyze command)
                
                # Cek apakah coin memenuhi kriteria berdasarkan output
                # COMMENTED OUT untuk single coin request - selalu kirim ke Telegram
                # Semua hasil analisis untuk single coin request akan selalu dikirim ke Telegram
                # Filter/threshold hanya berlaku untuk batch request di analyze_screened_coins.py
                
                # Tampilkan bagian penting dari output (ml_result dan Quant Metrics)
                if result.stdout:
                    # Cari bagian penting tentang ml_result dan Quant Metrics
                    stdout_lines = result.stdout.split('\n')
                    
                    # Tampilkan bagian ML PREDICTION / QUANT METRICS
                    ml_section_start = None
                    ml_section_end = None
                    for i, line in enumerate(stdout_lines):
                        if "ML PREDICTION / QUANT METRICS" in line or "PRE-TELEGRAM LOGGING" in line:
                            ml_section_start = i
                        elif ml_section_start is not None and ("=" * 70 in line or "Mengirim trading signal" in line):
                            ml_section_end = i
                            break
                    
                    if ml_section_start is not None:
                        print(f"\n📊 [run_analysis] ML Result & Quant Metrics Section:")
                        print("=" * 70)
                        section_lines = stdout_lines[ml_section_start:ml_section_end] if ml_section_end else stdout_lines[ml_section_start:ml_section_start+30]
                        for line in section_lines:
                            if any(keyword in line for keyword in ["ml_result", "Quant Metrics", "accuracy", "sharpe", "expected_value", "TELEGRAM DEBUG", "✅", "❌"]):
                                print(f"   {line}")
                        print("=" * 70)
                    
                    # Cari bagian PREDICTION CHECK dan RUN_PREDICTION - cari SEMUA occurrence
                    prediction_check_lines = []
                    for i, line in enumerate(stdout_lines):
                        if any(keyword in line for keyword in ["PREDICTION CHECK", "RUN_PREDICTION", "LANJUT KE PREDIKSI", "prediksi_next_day.py", "[PREDICTION]", "WILL EXECUTE PREDICTION", "Prediksi TIDAK dijalankan"]):
                            # Ambil 3 baris sebelum dan 15 baris setelah
                            start = max(0, i - 3)
                            end = min(len(stdout_lines), i + 15)
                            prediction_check_lines.extend(stdout_lines[start:end])
                            prediction_check_lines.append("---")  # Separator
                    
                    if prediction_check_lines:
                        print(f"\n🔍 [run_analysis] Prediction Execution Section (ALL occurrences):")
                        print("=" * 70)
                        # Remove duplicates while preserving order
                        seen = set()
                        unique_lines = []
                        for line in prediction_check_lines:
                            if line not in seen:
                                seen.add(line)
                                unique_lines.append(line)
                        for line in unique_lines[:100]:  # Limit to 100 lines
                            print(f"   {line}")
                        print("=" * 70)
                    else:
                        print(f"\n⚠️  [run_analysis] NO PREDICTION CHECK output found in stdout!")
                        print("   This means either:")
                        print("   1. RUN_PREDICTION section was not executed")
                        print("   2. Output was not captured properly")
                        print("   3. Exception occurred before prediction section")
                    
                    # Tampilkan last 500 chars sebagai fallback
                    print(f"\n📝 [run_analysis] stdout (last 500 chars):")
                    print(result.stdout[-500:])
                return True
            else:
                # Ada error
                error_msg = result.stderr[:500] if result.stderr else (result.stdout[-500:] if result.stdout else "Unknown error")
                print(f"❌ [run_analysis] Analysis failed for {symbol}")
                print(f"❌ [run_analysis] Error output: {error_msg}")
                success = self.send_message(
                    chat_id,
                    f"❌ <b>Error menjalankan analisis untuk {symbol}</b>\n\n"
                    f"<code>{error_msg}</code>"
                )
                print(f"{'✅' if success else '❌'} [run_analysis] Error message sent: {success}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"⏱️  [run_analysis] Timeout expired for {symbol}")
            success = self.send_message(
                chat_id,
                f"⏱️ <b>Timeout!</b>\n\n"
                f"Analisis untuk {symbol} memakan waktu terlalu lama (>5 menit).\n"
                f"Silakan coba lagi nanti."
            )
            print(f"{'✅' if success else '❌'} [run_analysis] Timeout message sent: {success}")
            return False
        except Exception as e:
            print(f"❌ [run_analysis] Exception occurred: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            success = self.send_message(
                chat_id,
                f"❌ <b>Error:</b> {str(e)}"
            )
            print(f"{'✅' if success else '❌'} [run_analysis] Exception message sent: {success}")
            return False
    
    def update_config_symbol(self, symbol: str):
        """
        Update SYMBOL di config.py
        
        Args:
            symbol: Symbol baru (format: BTC-USD)
        """
        try:
            config_file = "src/utils/config.py"
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Replace SYMBOL line (handle berbagai format)
            import re
            # Pattern untuk match SYMBOL = "..." atau SYMBOL = '...'
            pattern = r'^SYMBOL\s*=\s*["\'].*?["\']'
            replacement = f'SYMBOL = "{symbol}"'
            new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
            
            if new_content != content:
                with open(config_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"✅ Config updated: SYMBOL = {symbol}")
            else:
                # Coba pattern alternatif jika tidak match
                pattern2 = r'SYMBOL\s*=\s*["\'].*?["\']'
                new_content2 = re.sub(pattern2, replacement, content)
                if new_content2 != content:
                    with open(config_file, 'w', encoding='utf-8') as f:
                        f.write(new_content2)
                    print(f"✅ Config updated: SYMBOL = {symbol}")
        except Exception as e:
            print(f"⚠️  Error updating config: {e}")
    
    def update_config_chat_id(self, chat_id: str):
        """
        Update TELEGRAM_CHAT_ID di config.py
        
        Args:
            chat_id: Chat ID baru
        """
        try:
            config_file = "src/utils/config.py"
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Replace TELEGRAM_CHAT_ID line
            import re
            pattern = r'^TELEGRAM_CHAT_ID\s*=\s*["\'].*?["\']'
            replacement = f'TELEGRAM_CHAT_ID = "{chat_id}"'
            new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
            
            if new_content != content:
                with open(config_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"✅ Config updated: TELEGRAM_CHAT_ID = {chat_id}")
            else:
                # Coba pattern alternatif
                pattern2 = r'TELEGRAM_CHAT_ID\s*=\s*["\'].*?["\']'
                new_content2 = re.sub(pattern2, replacement, content)
                if new_content2 != content:
                    with open(config_file, 'w', encoding='utf-8') as f:
                        f.write(new_content2)
                    print(f"✅ Config updated: TELEGRAM_CHAT_ID = {chat_id}")
        except Exception as e:
            print(f"⚠️  Error updating chat_id in config: {e}")
    
    def update_config_trading_style(self, trading_style: str):
        """
        Update TRADING_STYLE di config.py dan auto-update DAYS_BACK
        
        Args:
            trading_style: Trading style baru (SCALPING, DAY_TRADING, SWING_TRADING, POSITION_TRADING)
        """
        try:
            config_file = "src/utils/config.py"
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Replace TRADING_STYLE line
            import re
            pattern = r'^TRADING_STYLE\s*=\s*["\'].*?["\']'
            replacement = f'TRADING_STYLE = "{trading_style}"'
            new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
            
            # Auto-update DAYS_BACK berdasarkan TRADING_STYLE
            # Mapping DAYS_BACK berdasarkan TRADING_STYLE
            days_back_map = {
                "SCALPING": 7,
                "DAY_TRADING": 30,
                "INTRADAY_TRADING": 60,
                "SWING_TRADING": 365,
                "POSITION_TRADING": 365
            }
            new_days_back = days_back_map.get(trading_style, 30)
            
            # Update DAYS_BACK ke None agar menggunakan auto dari TRADING_STYLE
            # Hanya update DAYS_BACK, JANGAN sentuh TRADING_STYLE_DAYS_BACK dictionary
            # Pattern yang lebih spesifik: hanya match "DAYS_BACK = " di awal baris, bukan "TRADING_STYLE_DAYS_BACK"
            pattern_days = r'^DAYS_BACK\s*=\s*[^\n]*$'
            replacement_days = f'DAYS_BACK = None  # Auto berdasarkan TRADING_STYLE ({new_days_back} hari)'
            new_content = re.sub(pattern_days, replacement_days, new_content, flags=re.MULTILINE)
            
            # Pastikan TRADING_STYLE_DAYS_BACK tetap sebagai dictionary yang valid
            # Jika ada yang merusak (misalnya menjadi None dengan entri di bawahnya), fix itu
            # Pattern untuk detect broken dictionary: TRADING_STYLE_DAYS_BACK = None diikuti oleh "SCALPING"
            pattern_dict_broken = r'TRADING_STYLE_DAYS_BACK\s*=\s*None[^\n]*\n(\s+)"SCALPING"'
            match_broken = re.search(pattern_dict_broken, new_content)
            if match_broken:
                # Jika ada TRADING_STYLE_DAYS_BACK = None diikuti oleh entri dictionary, fix itu
                indent = match_broken.group(1)
                dict_replacement = f'''TRADING_STYLE_DAYS_BACK = {{
{indent}"SCALPING": 7,           # 7 hari untuk scalping
{indent}"DAY_TRADING": 30,
                "INTRADAY_TRADING": 60,       # 30 hari untuk day trading
{indent}"INTRADAY_TRADING": 60,  # 60 hari untuk intraday trading
{indent}"SWING_TRADING": 365,    # 365 hari untuk swing trading
{indent}"POSITION_TRADING": 365  # 365 hari untuk position trading
}}'''
                # Pattern untuk match dari TRADING_STYLE_DAYS_BACK = None sampai closing brace
                pattern_dict_fix = r'TRADING_STYLE_DAYS_BACK\s*=\s*None[^\n]*\n\s*"SCALPING":\s*\d+[^\n]*\n\s*"DAY_TRADING":\s*\d+[^\n]*\n\s*"SWING_TRADING":\s*\d+[^\n]*\n\s*"POSITION_TRADING":\s*\d+[^\n]*\n\s*\}'
                new_content = re.sub(pattern_dict_fix, dict_replacement, new_content, flags=re.MULTILINE)
            
            if new_content != content:
                with open(config_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"✅ Config updated: TRADING_STYLE = {trading_style}, DAYS_BACK = {new_days_back} (auto)")
            else:
                # Coba pattern alternatif
                pattern2 = r'TRADING_STYLE\s*=\s*["\'].*?["\']'
                new_content2 = re.sub(pattern2, replacement, content)
                # Pattern yang lebih spesifik: hanya match "DAYS_BACK = " bukan "TRADING_STYLE_DAYS_BACK"
                pattern_days2 = r'^DAYS_BACK\s*=\s*[^\n]*$'
                new_content2 = re.sub(pattern_days2, replacement_days, new_content2, flags=re.MULTILINE)
                if new_content2 != content:
                    with open(config_file, 'w', encoding='utf-8') as f:
                        f.write(new_content2)
                    print(f"✅ Config updated: TRADING_STYLE = {trading_style}, DAYS_BACK = {new_days_back} (auto)")
        except Exception as e:
            print(f"⚠️  Error updating trading_style in config: {e}")
    
    def handle_message(self, message: dict):
        """
        Handle incoming message
        
        Args:
            message: Message dictionary dari Telegram API
        """
        chat = message.get('chat', {})
        chat_id = str(chat.get('id'))
        text = message.get('text', '').strip()
        
        print(f"📥 [handle_message] Received message from chat_id={chat_id}, text='{text}'")
        
        if not text:
            print(f"⚠️  [handle_message] Empty text, ignoring message")
            return
        
        # Handle /start command
        if text.startswith('/start'):
            self.handle_start_command(chat_id)
            return
        
        # Handle /style command untuk mengatur TRADING_STYLE
        if text.startswith('/style') or text.startswith('/trading_style'):
            self.handle_trading_style_command(chat_id, text)
            return
        
        # Handle /settings command untuk melihat setting saat ini
        if text.startswith('/settings'):
            self.handle_settings_command(chat_id)
            return
        
        # Handle /screen command untuk coin screening
        if text.startswith('/screen') or text.startswith('/screening'):
            self.handle_screening_command(chat_id, text)
            return
        
        # Handle /analyze command untuk analisis screened coins
        if text.startswith('/analyze') or text.startswith('/analyze_screen'):
            self.handle_analyze_screened_command(chat_id, text)
            return
        
        # Check if user has started the bot
        if chat_id not in self.active_users:
            print(f"⚠️  [handle_message] User {chat_id} belum aktif, meminta /start")
            success = self.send_message(
                chat_id,
                "⚠️ <b>Bot belum diaktifkan!</b>\n\n"
                "Silakan kirim command <code>/start</code> terlebih dahulu untuk memulai."
            )
            print(f"{'✅' if success else '❌'} [handle_message] Send message result: {success}")
            return
        
        # Cek apakah ini multiple symbols (comma-separated)
        multiple_symbols = self.parse_multiple_symbols(text)
        
        if len(multiple_symbols) > 1:
            # Multiple symbols detected
            print(f"📊 [handle_message] Multiple symbols detected: {len(multiple_symbols)} coins")
            print(f"   Symbols: {', '.join(multiple_symbols)}")
            
            # Kirim notifikasi mulai analisis multiple
            self.send_message(
                chat_id,
                f"🔄 <b>Memproses analisis untuk {len(multiple_symbols)} coins...</b>\n\n"
                f"📋 Coins: {', '.join([s.replace('-USD', '') for s in multiple_symbols])}\n\n"
                f"⏳ Mohon tunggu, ini mungkin memakan waktu beberapa menit..."
            )
            
            # Jalankan analisis untuk setiap coin
            results = self.run_multiple_analysis(multiple_symbols, chat_id)
            
            # Kirim summary
            success_count = sum(1 for r in results.values() if r)
            failed_count = len(results) - success_count
            
            summary_msg = (
                f"✅ <b>Analisis Multiple Coins Selesai</b>\n\n"
                f"📊 Total: {len(multiple_symbols)} coins\n"
                f"✅ Berhasil: {success_count}\n"
                f"❌ Gagal: {failed_count}\n\n"
            )
            
            if failed_count > 0:
                failed_symbols = [s for s, r in results.items() if not r]
                summary_msg += f"❌ Gagal: {', '.join([s.replace('-USD', '') for s in failed_symbols])}\n"
            
            self.send_message(chat_id, summary_msg)
            print(f"✅ [handle_message] Multiple analysis completed: {success_count}/{len(multiple_symbols)} successful")
            return
        
        # Single symbol - parse seperti biasa
        symbol = self.parse_symbol(text)
        print(f"🔍 [handle_message] Parsed symbol: '{text}' -> '{symbol}'")
        
        if symbol:
            # Valid symbol, jalankan analisis
            print(f"📨 [handle_message] Valid symbol detected: {text} -> {symbol} from chat {chat_id}")
            print(f"🚀 [handle_message] Starting analysis for {symbol}...")
            result = self.run_analysis(symbol, chat_id)
            print(f"{'✅' if result else '❌'} [handle_message] Analysis completed for {symbol}, result: {result}")
        else:
            # Invalid format, kirim help message
            help_text = (
                "🤖 <b>Trading Quant Bot</b>\n\n"
                "Kirim symbol coin untuk mendapatkan analisis trading.\n\n"
                "<b>Format yang didukung:</b>\n"
                "• Single coin: <code>BTC</code>, <code>BTC-USD</code>, <code>ETH</code>\n"
                "• Multiple coins: <code>BTC,ETH,SOL</code> atau <code>GALA,ONT,D,BANANA</code>\n\n"
                "<b>Contoh Single:</b>\n"
                "• <code>BTC-USD</code>\n"
                "• <code>ETH</code>\n"
                "• <code>SOL-USD</code>\n\n"
                "<b>Contoh Multiple:</b>\n"
                "• <code>BTC,ETH,SOL</code>\n"
                "• <code>GALA,ONT,D,BANANA</code>\n\n"
                "Bot akan mengirim analisis lengkap termasuk:\n"
                "• DeepSeek AI Recommendation\n"
                "• ML Prediction Results\n"
                "• Trading Chart"
            )
            self.send_message(chat_id, help_text)
    
    def handle_start_command(self, chat_id: str):
        """
        Handle /start command
        
        Args:
            chat_id: Chat ID dari user
        """
        # Tambahkan user ke active users
        self.active_users.add(chat_id)
        
        welcome_text = (
            "🤖 <b>Selamat Datang di Trading Quant Bot!</b>\n\n"
            "✅ Bot telah diaktifkan untuk Anda.\n\n"
            "📊 <b>Cara menggunakan:</b>\n"
            "Kirim symbol coin untuk mendapatkan analisis trading lengkap.\n\n"
            "<b>Format yang didukung:</b>\n"
            "• BTC-USD\n"
            "• BTC/USD\n"
            "• BTCUSD\n"
            "• BTC\n\n"
            "<b>Contoh:</b>\n"
            "• <code>BTC-USD</code>\n"
            "• <code>ETH</code>\n"
            "• <code>SOL-USD</code>\n\n"
            "📈 Bot akan mengirim analisis lengkap termasuk:\n"
            "• DeepSeek AI Recommendation\n"
            "• ML Prediction Results\n"
            "• Trading Chart\n\n"
            "<b>Command yang tersedia:</b>\n"
            "• <code>/style STYLE</code> - Ubah TRADING_STYLE\n"
            "• <code>/screen [days] [top_n] [direction]</code> - Screen coins\n"
            "  Contoh: <code>/screen</code> (90 hari, top 10)\n"
            "          <code>/screen 7</code> (7 hari, top 10)\n"
            "          <code>/screen 7 15</code> (7 hari, top 15)\n"
            "• <code>/analyze [days] [top_n] [max_coins] [direction]</code> - Analisis screened coins\n"
            "  Contoh: <code>/analyze</code> (90 hari, top 5, analisis 5 coins)\n"
            "          <code>/analyze 7 10 3</code> (7 hari, top 10, analisis 3 coins)\n"
            "• <code>/settings</code> - Lihat pengaturan\n\n"
            "🚀 <b>Mulai dengan mengirim symbol coin atau gunakan /screen untuk mencari peluang!</b>"
        )
        
        self.send_message(chat_id, welcome_text)
        print(f"✅ User {chat_id} started the bot")
    
    def handle_trading_style_command(self, chat_id: str, text: str):
        """
        Handle /style atau /trading_style command
        
        Args:
            chat_id: Chat ID dari user
            text: Command text (format: /style SCALPING)
        """
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            # Tidak ada parameter, tampilkan help
            help_text = (
                "⚙️ <b>Pengaturan TRADING_STYLE</b>\n\n"
                "<b>Format:</b>\n"
                "<code>/style STYLE</code>\n\n"
                "<b>Pilihan TRADING_STYLE:</b>\n"
                "• <code>SCALPING</code> - Trading sangat cepat (5m timeframe)\n"
                "• <code>DAY_TRADING</code> - Trading dalam 1 hari (15m timeframe)\n"
                "• <code>INTRADAY_TRADING</code> - Trading intraday (2h timeframe)\n"
                "• <code>SWING_TRADING</code> - Trading beberapa hari-minggu (4h timeframe)\n"
                "• <code>POSITION_TRADING</code> - Trading jangka panjang (1d timeframe)\n\n"
                "<b>Contoh:</b>\n"
                "<code>/style DAY_TRADING</code>\n"
                "<code>/style INTRADAY_TRADING</code>\n"
                "<code>/style SCALPING</code>"
            )
            self.send_message(chat_id, help_text)
            return
        
        style = parts[1].strip().upper()
        
        # Validasi style
        if style not in self.valid_trading_styles:
            self.send_message(
                chat_id,
                f"❌ <b>TRADING_STYLE tidak valid!</b>\n\n"
                f"Pilihan yang tersedia:\n"
                f"• SCALPING (5m timeframe)\n"
                f"• DAY_TRADING (15m timeframe)\n"
                f"• INTRADAY_TRADING (2h timeframe)\n"
                f"• SWING_TRADING (4h timeframe)\n"
                f"• POSITION_TRADING (1d timeframe)\n\n"
                f"Contoh: <code>/style DAY_TRADING</code>"
            )
            return
        
        # Update TRADING_STYLE untuk user ini
        self.user_trading_styles[chat_id] = style
        
        # Update config.py
        self.update_config_trading_style(style)
        
        # Kirim konfirmasi
        style_descriptions = {
            "SCALPING": "Trading sangat cepat (5m timeframe), banyak sinyal, profit kecil per trade",
            "DAY_TRADING": "Trading dalam 1 hari (15m timeframe), beberapa sinyal per hari",
            "INTRADAY_TRADING": "Trading intraday (2h timeframe), beberapa sinyal per hari",
            "SWING_TRADING": "Trading beberapa hari-minggu (4h timeframe), sinyal lebih jarang tapi lebih reliable",
            "POSITION_TRADING": "Trading jangka panjang (1d timeframe), sinyal sangat jarang"
        }
        
        self.send_message(
            chat_id,
            f"✅ <b>TRADING_STYLE diubah menjadi: {style}</b>\n\n"
            f"📝 <b>Deskripsi:</b>\n"
            f"{style_descriptions.get(style, 'N/A')}\n\n"
            f"🔄 Setting ini akan digunakan untuk analisis selanjutnya."
        )
        print(f"✅ User {chat_id} set TRADING_STYLE to {style}")
    
    def handle_settings_command(self, chat_id: str):
        """
        Handle /settings command untuk melihat setting saat ini
        
        Args:
            chat_id: Chat ID dari user
        """
        current_style = self.user_trading_styles.get(chat_id, "DAY_TRADING")
        
        # Baca config untuk mendapatkan setting lainnya
        try:
            from src.utils.config import TRADING_STYLE, SYMBOL, get_days_back
            config_style = TRADING_STYLE
            config_symbol = SYMBOL
            current_days_back = get_days_back()
        except:
            config_style = "DAY_TRADING"
            config_symbol = "BTC-USD"
            current_days_back = 30
        
        # Gunakan user style jika ada, kalau tidak gunakan config
        active_style = self.user_trading_styles.get(chat_id, config_style)
        
        # DAYS_BACK selalu otomatis berdasarkan TRADING_STYLE
        days_back_map = {
            "SCALPING": 7,
            "DAY_TRADING": 30,
                "INTRADAY_TRADING": 60,
            "SWING_TRADING": 365,
            "POSITION_TRADING": 365
        }
        expected_days = days_back_map.get(active_style, 30)
        
        settings_text = (
            "⚙️ <b>Pengaturan Saat Ini</b>\n\n"
            f"📊 <b>TRADING_STYLE:</b> <code>{active_style}</code>\n"
            f"📅 <b>DAYS_BACK:</b> <code>{expected_days}</code> hari (Auto)\n"
            f"💰 <b>SYMBOL:</b> <code>{config_symbol}</code>\n\n"
            "<b>Command yang tersedia:</b>\n"
            "• <code>/style STYLE</code> - Ubah TRADING_STYLE\n"
                "• <code>/screen [days] [top_n] [direction]</code> - Screen coins\n"
                "  Contoh: <code>/screen</code> (90 hari, top 10, both)\n"
                "          <code>/screen 7</code> (7 hari, top 10, both)\n"
                "          <code>/screen 7 15</code> (7 hari, top 15, both)\n"
                "          <code>/screen 7 15 long</code> (7 hari, top 15, long only)\n"
                "          <code>/screen 7 15 short</code> (7 hari, top 15, short only)\n"
                "• <code>/analyze [days] [top_n] [max_coins] [direction]</code> - Analisis screened coins\n"
                "  Contoh: <code>/analyze</code> (90 hari, top 5, analisis 5 coins)\n"
                "          <code>/analyze 7</code> (7 hari, top 5, analisis 5 coins)\n"
                "          <code>/analyze 7 10 3</code> (7 hari, top 10, analisis 3 coins)\n"
                "          <code>/analyze 7 10 3 long</code> (long only)\n"
                "• <code>/settings</code> - Lihat pengaturan\n"
                "• Kirim symbol coin untuk analisis\n\n"
                "💡 <b>Catatan:</b> DAYS_BACK otomatis disesuaikan berdasarkan TRADING_STYLE"
        )
        
        self.send_message(chat_id, settings_text)
    
    def handle_screening_command(self, chat_id: str, text: str):
        """
        Handle /screen atau /screening command untuk coin screening
        
        Args:
            chat_id: Chat ID dari user
            text: Command text (format: /screen [days] [top_n])
                  Contoh: /screen -> days=90, top_n=10
                          /screen 7 -> days=7, top_n=10
                          /screen 7 15 -> days=7, top_n=15
        """
        try:
            from src.screening.coin_screening import screen_coins, DEFAULT_COINS
            from src.integration.telegram_bot import TelegramBot
            from src.utils.config import (ENABLE_TELEGRAM_BOT, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
                              DATA_SOURCE, BINANCE_API_KEY, BINANCE_API_SECRET)
            
            parts = text.split()
            
            # Parse parameters
            # Format: /screen [days] [top_n]
            # Contoh: /screen -> days=90, top_n=10
            #         /screen 7 -> days=7, top_n=10
            #         /screen 7 15 -> days=7, top_n=15
            days = 90  # Default
            top_n = 10  # Default
            
            if len(parts) > 1:
                try:
                    param1 = int(parts[1])
                    # Parameter pertama selalu dianggap sebagai days (1-365)
                    if 1 <= param1 <= 365:
                        days = param1
                        # Cek apakah ada parameter kedua (top_n)
                        if len(parts) > 2:
                            try:
                                top_n = int(parts[2])
                                if top_n < 1 or top_n > 50:
                                    top_n = 10
                            except:
                                pass
                except:
                    pass
            
            # Validasi days
            if days < 1 or days > 365:
                days = 90
            
            # Kirim notifikasi sedang screening
            self.send_message(
                chat_id,
                f"🔍 <b>Memulai coin screening...</b>\n\n"
                f"📅 Periode: {days} hari\n"
                f"📊 Top {top_n} hasil\n\n"
                f"⏳ Ini mungkin memakan waktu beberapa detik..."
            )
            
            # Parse trade direction dari command (optional)
            # Format: /screen [days] [top_n] [long|short|both]
            trade_direction = "both"  # Default: both
            if len(parts) > 3:
                direction_param = parts[3].lower()
                if direction_param in ["long", "short", "both"]:
                    trade_direction = direction_param
            
            # Jalankan screening dengan filter yang lebih akurat dan realistis
            results = screen_coins(
                coins=None,  # Gunakan default coins
                days=days,  # Parameter dari Telegram atau default 90
                min_volume_ratio=0.3,  # Lebih longgar: 0.3 (was 0.5)
                min_price_change=-80.0,  # Lebih longgar: -80% (was -50%)
                max_price_change=200.0,  # Lebih longgar: +200% (was +100%)
                rsi_range=None,
                top_n=top_n,
                data_source=DATA_SOURCE,  # Gunakan DATA_SOURCE dari config
                api_key=BINANCE_API_KEY,
                api_secret=BINANCE_API_SECRET,
                use_adaptive_filtering=True,  # Auto-relax filters jika tidak ada hasil
                trade_direction=trade_direction  # long, short, atau both
            )
            
            if not results:
                self.send_message(
                    chat_id,
                    "❌ <b>Tidak ada coin yang memenuhi criteria</b>\n\n"
                    "💡 Coba ubah filter criteria atau coba lagi nanti"
                )
                return
            
            # Format dan kirim hasil
            if ENABLE_TELEGRAM_BOT and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                bot = TelegramBot(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
                bot.send_screening_results(results)
            else:
                # Fallback: kirim via main bot
                formatted_results = self.format_screening_results(results)
                self.send_message(chat_id, formatted_results)
                
        except ImportError as e:
            self.send_message(
                chat_id,
                f"❌ <b>Error:</b> Module coin_screening tidak ditemukan\n\n"
                f"Detail: {str(e)}"
            )
        except Exception as e:
            self.send_message(
                chat_id,
                f"❌ <b>Error saat screening:</b> {str(e)}"
            )
            print(f"Error in handle_screening_command: {e}")
    
    def handle_analyze_screened_command(self, chat_id: str, text: str):
        """
        Handle /analyze atau /analyze_screen command untuk analisis screened coins
        
        Args:
            chat_id: Chat ID dari user
            text: Command text (format: /analyze [days] [top_n] [max_coins] [direction])
                  Contoh: /analyze -> days=90, top_n=5, max_coins=5
                          /analyze 7 -> days=7, top_n=5, max_coins=5
                          /analyze 7 10 3 -> days=7, top_n=10, max_coins=3
        """
        try:
            from src.analysis.analyze_screened_coins import analyze_screened_coins
            from src.utils.config import (DATA_SOURCE, BINANCE_API_KEY, BINANCE_API_SECRET)
            
            parts = text.split()
            
            # Parse parameters
            # Format: /analyze [days] [top_n] [max_coins] [direction]
            days = 90  # Default
            top_n = 5  # Default untuk screening
            max_coins = None  # Default: None = analisis semua coin hasil screening (sama dengan top_n)
            trade_direction = "both"  # Default
            
            if len(parts) > 1:
                try:
                    param1 = int(parts[1])
                    if 1 <= param1 <= 365:
                        days = param1
                except:
                    pass
            
            if len(parts) > 2:
                try:
                    top_n = int(parts[2])
                    if top_n < 1 or top_n > 200:  # Increase limit untuk top_n
                        top_n = 5
                except:
                    pass
            
            # Cek apakah user ingin skip screening (parameter "noscreen" atau "direct")
            # HARUS dicek SEBELUM parsing max_coins agar tidak conflict
            skip_screening = False
            if len(parts) > 1:
                # Cek apakah ada parameter "noscreen" atau "direct"
                for part in parts[1:]:
                    if part.lower() in ["noscreen", "direct", "skip"]:
                        skip_screening = True
                        # Hapus parameter ini dari parts untuk parsing normal
                        parts = [p for p in parts if p.lower() not in ["noscreen", "direct", "skip"]]
                        break
            
            if len(parts) > 3:
                try:
                    max_coins = int(parts[3])
                    if max_coins < 1:
                        max_coins = None  # Jika 0 atau negatif, analisis semua
                    elif skip_screening:
                        # Untuk skip_screening, allow lebih banyak coins (sampai 1000)
                        if max_coins > 1000:
                            max_coins = 1000
                    else:
                        # Untuk normal screening, limit 200
                        if max_coins > 200:
                            max_coins = 200
                except:
                    pass
            
            # Jika skip_screening, max_coins default = None (unlimited, analisis semua)
            if skip_screening:
                if max_coins is None:
                    max_coins = None  # Unlimited - analisis semua coins dari list
            else:
                # Jika max_coins tidak di-specify, default = top_n (analisis semua hasil screening)
                if max_coins is None:
                    max_coins = top_n
            
            if len(parts) > 4:
                direction_param = parts[4].lower()
                if direction_param in ["long", "short", "both"]:
                    trade_direction = direction_param
            
            # Tentukan trading style untuk analisis
            trading_style = "DAY_TRADING"  # Default untuk analisis screened coins
            
            # Kirim notifikasi sedang analisis
            if skip_screening:
                self.send_message(
                    chat_id,
                    f"🚀 <b>Memulai analisis langsung (tanpa screening)...</b>\n\n"
                    f"🔢 Menganalisis maksimal {max_coins} coins\n"
                    f"⚙️  Trading Style: {trading_style}\n"
                    f"🔄 Mode: REAL-TIME Processing\n"
                    f"   → Analisis → Filter Ketat → AI → Telegram → Next\n\n"
                    f"⏳ Proses ini mungkin memakan waktu lama..."
                )
            else:
                self.send_message(
                    chat_id,
                    f"🔍 <b>Memulai analisis screened coins...</b>\n\n"
                    f"📅 Periode screening: {days} hari\n"
                    f"📊 Top {top_n} coins dari screening\n"
                    f"🔢 Menganalisis {max_coins} coins teratas\n"
                    f"📈 Direction: {trade_direction}\n"
                    f"⚙️  Trading Style: {trading_style}\n\n"
                    f"⏳ Proses ini mungkin memakan waktu beberapa menit..."
                )
            
            print(f"🔍 [handle_analyze_screened_command] Starting analysis for chat_id={chat_id}")
            print(f"   Parameters: days={days}, top_n={top_n}, max_coins={max_coins}, direction={trade_direction}")
            print(f"   Skip Screening: {skip_screening}")
            
            # Tentukan trading style untuk analisis
            # Default: DAY_TRADING untuk analisis screened coins (lebih stabil)
            # User bisa override dengan parameter jika diperlukan
            trading_style = "DAY_TRADING"  # Default untuk analisis screened coins
            
            # Jalankan analisis (akan otomatis kirim ke Telegram)
            results = analyze_screened_coins(
                coins=None,  # Gunakan default coins
                days=days,
                top_n=top_n,
                trade_direction=trade_direction,
                max_coins=max_coins,
                send_to_telegram=True,  # Otomatis kirim ke Telegram
                trading_style=trading_style,  # DAY_TRADING untuk analisis screened coins
                skip_screening=skip_screening  # Skip screening jika diminta
            )
            
            if not results:
                self.send_message(
                    chat_id,
                    "❌ <b>Tidak ada coin yang berhasil dianalisis</b>\n\n"
                    "💡 Coba ubah parameter atau coba lagi nanti"
                )
                return
            
            # Hitung berapa yang berhasil
            success_count = sum(1 for r in results if r.get('success', False))
            
            # Kirim summary
            self.send_message(
                chat_id,
                f"✅ <b>Analisis Selesai!</b>\n\n"
                f"📊 Total coins dianalisis: {len(results)}\n"
                f"✅ Berhasil: {success_count}\n"
                f"❌ Gagal: {len(results) - success_count}\n\n"
                f"📋 Detail hasil sudah dikirim sebelumnya."
            )
            
            print(f"✅ [handle_analyze_screened_command] Analysis completed: {success_count}/{len(results)} successful")
            
        except ImportError as e:
            error_msg = f"❌ Error: Module analyze_screened_coins tidak ditemukan\n\n{e}"
            self.send_message(chat_id, error_msg)
            print(f"Error in handle_analyze_screened_command: {e}")
        except Exception as e:
            error_msg = f"❌ Error saat analisis: {str(e)[:200]}"
            self.send_message(chat_id, error_msg)
            print(f"Error in handle_analyze_screened_command: {e}")
            import traceback
            traceback.print_exc()
    
    def format_screening_results(self, results: list) -> str:
        """
        Format screening results untuk Telegram (fallback jika telegram_bot tidak tersedia)
        
        Args:
            results: List of coin metrics dictionaries
        
        Returns:
            Formatted HTML string
        """
        if not results:
            return "❌ Tidak ada coin yang memenuhi criteria"
        
        lines = []
        lines.append("🔍 <b>COIN SCREENING RESULTS</b>")
        lines.append("=" * 40)
        lines.append("")
        
        for i, coin in enumerate(results, 1):
            symbol = coin['symbol']
            price = coin['current_price']
            change_1d = coin['price_change_1d']
            change_7d = coin['price_change_7d']
            volume_ratio = coin['volume_ratio']
            rsi = coin['rsi']
            rsi_signal = coin['rsi_signal']
            trend_signal = coin.get('trend_signal', 'NEUTRAL')
            score = coin['combined_score']
            
            # Emoji berdasarkan trend signal
            if "BULLISH" in trend_signal:
                signal_emoji = "🟢"
                signal_text = trend_signal
            elif "BEARISH" in trend_signal:
                signal_emoji = "🔴"
                signal_text = trend_signal
            else:
                signal_emoji = "🟡"
                signal_text = "NEUTRAL"
            
            change_emoji = "📈" if change_7d > 0 else "📉"
            
            lines.append(f"<b>{i}. {symbol}</b>")
            lines.append(f"💵 Price: ${price:,.4f}")
            lines.append(f"{change_emoji} Change: 1d: {change_1d:+.2f}% | 7d: {change_7d:+.2f}%")
            lines.append(f"📊 Volume: {volume_ratio:.2f}x")
            lines.append(f"📈 RSI: {rsi:.2f} ({rsi_signal})")
            lines.append(f"{signal_emoji} Trend: {signal_text}")
            
            # Tampilkan direction dan scores jika ada
            if 'best_direction' in coin:
                direction_emoji = "🟢" if coin['best_direction'] == "LONG" else "🔴" if coin['best_direction'] == "SHORT" else "🟡"
                lines.append(f"{direction_emoji} <b>Direction:</b> {coin['best_direction']}")
                if 'long_score' in coin and 'short_score' in coin:
                    lines.append(f"   Long: {coin['long_score']:.4f} | Short: {coin['short_score']:.4f}")
            
            lines.append(f"⭐ Score: {score:.4f}")
            lines.append("")
        
        lines.append("💡 <i>Kirim symbol coin untuk analisis detail</i>")
        
        return "\n".join(lines)
    
    def start_polling(self):
        """Mulai polling untuk menerima pesan dari Telegram"""
        print("🤖 Starting Trading Quant Bot...")
        
        # Check if another instance is already running
        import subprocess
        try:
            result = subprocess.run(
                ['pgrep', '-f', 'python.*main.py'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                current_pid = str(os.getpid())
                other_pids = [pid for pid in pids if pid != current_pid and pid]
                if other_pids:
                    print(f"⚠️  Warning: Found other bot instances running (PIDs: {', '.join(other_pids)})")
                    print(f"   This may cause 409 conflicts. Consider stopping other instances first.")
                    print(f"   Kill with: pkill -f 'python.*main.py'")
                    print()
        except Exception:
            pass  # Ignore if pgrep not available
        
        print(f"📡 Listening for messages...")
        print(f"💬 Bot siap menerima command!")
        print()
        
        # Sinkronisasi offset awal untuk menghindari konflik
        try:
            sync_url = f"{self.api_url}/getUpdates"
            sync_params = {"limit": 1, "timeout": 1, "allowed_updates": ["message"]}
            sync_response = requests.get(sync_url, params=sync_params, timeout=10)
            if sync_response.status_code == 200:
                sync_data = sync_response.json()
                if sync_data.get('ok') and sync_data.get('result'):
                    latest_update_id = sync_data['result'][-1].get('update_id', 0)
                    self.offset = latest_update_id + 1
                    print(f"📌 Offset awal disinkronkan: {self.offset}")
                else:
                    self.offset = 0
                    print(f"📌 Offset awal: 0 (tidak ada update sebelumnya)")
        except Exception as e:
            print(f"⚠️  Warning: Gagal sinkronisasi offset awal: {e}")
            self.offset = 0
        
        print()
        self.running = True
        
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while self.running:
            try:
                updates = self.get_updates()
                
                if updates and updates.get('ok'):
                    consecutive_errors = 0  # Reset error counter on success
                    result = updates.get('result', [])
                    if result:
                        for update in result:
                            # Update offset ke update_id terbaru + 1
                            update_id = update.get('update_id', 0)
                            self.offset = update_id + 1
                            
                            # Handle message
                            if 'message' in update:
                                message = update['message']
                                self.handle_message(message)
                    else:
                        # No new updates, continue polling
                        pass
                elif updates and not updates.get('ok'):
                    # API returned error in response
                    error_description = updates.get('description', 'Unknown error')
                    print(f"⚠️  Telegram API error: {error_description}")
                    consecutive_errors += 1
                    if "conflict" in error_description.lower() or "409" in str(updates):
                        # Reset offset on conflict
                        self.offset = 0
                        time.sleep(5)  # Wait longer on conflict
                    elif consecutive_errors >= max_consecutive_errors:
                        print(f"❌ Terlalu banyak error berturut-turut ({consecutive_errors}). Berhenti polling.")
                        break
                elif updates is None:
                    # get_updates() returned None (error occurred)
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        print(f"❌ Terlalu banyak error berturut-turut ({consecutive_errors}). Berhenti polling.")
                        break
                    time.sleep(3)  # Wait before retry
                
                # Sleep sebentar sebelum polling lagi
                time.sleep(1)
                
            except KeyboardInterrupt:
                print("\n🛑 Stopping bot...")
                self.running = False
                break
            except Exception as e:
                print(f"⚠️  Error in polling loop: {e}")
                time.sleep(5)  # Wait longer on error


def main():
    """Main entry point"""
    # Check if Telegram bot is enabled
    if not ENABLE_TELEGRAM_BOT:
        print("❌ Telegram Bot integration dinonaktifkan di config.py")
        print("   Set ENABLE_TELEGRAM_BOT = True untuk mengaktifkan")
        sys.exit(1)
    
    if not TELEGRAM_BOT_TOKEN:
        print("❌ Telegram Bot Token tidak ditemukan di config.py")
        print("   Set TELEGRAM_BOT_TOKEN di config.py")
        sys.exit(1)
    
    # Start bot
    bot = TradingBot(TELEGRAM_BOT_TOKEN)
    bot.start_polling()


if __name__ == "__main__":
    main()

