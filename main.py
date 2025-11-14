#!/usr/bin/env python3
"""
Main Entry Point untuk Trading Quant Bot
Menerima input dari Telegram dan menjalankan analisis untuk coin yang diminta
"""

import os
import sys
import time
import json
import requests
import subprocess
from typing import Optional
from config import ENABLE_TELEGRAM_BOT, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, SYMBOL as DEFAULT_SYMBOL


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
        self.valid_trading_styles = ["SCALPING", "DAY_TRADING", "SWING_TRADING", "POSITION_TRADING"]
    
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
                    "timeout": 10
                }
                # Increase timeout untuk koneksi yang lambat
                response = requests.get(url, params=params, timeout=30)
                
                if response.status_code == 200:
                    return response.json()
                else:
                    print(f"❌ Error mendapatkan updates: {response.status_code}")
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
        # - BTC
        
        # Normalize
        if "/" in text:
            text = text.replace("/", "-")
        
        if "-" not in text and len(text) <= 6:
            # Format: BTC -> BTC-USD
            text = f"{text}-USD"
        elif "-" not in text:
            # Format: BTCUSD -> BTC-USD
            if text.endswith("USD"):
                text = text[:-3] + "-USD"
            elif text.endswith("USDT"):
                text = text[:-4] + "-USD"
        
        # Validasi format akhir: COIN-USD
        if "-" in text and text.endswith("-USD"):
            return text
        
        return None
    
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
            print(f"⏳ [run_analysis] Waiting 0.5s for config file to be written...")
            time.sleep(0.5)
            print(f"✅ [run_analysis] Config update completed")
            
            # Verifikasi bahwa config sudah ter-update dengan benar
            try:
                import importlib
                # Force reload config module jika sudah di-import sebelumnya
                if 'config' in sys.modules:
                    importlib.reload(sys.modules['config'])
            except:
                pass
            
            # Cek apakah perlu mengambil data historical terlebih dahulu
            # (analisis_quant.py akan otomatis mengambil jika tidak ada CSV, tapi lebih baik kita ambil dulu)
            try:
                # Cek apakah ada file CSV
                import glob
                csv_files = glob.glob("*_historical_*.csv")
                print(f"📁 [run_analysis] Checking for CSV files: found {len(csv_files)} files")
                if not csv_files:
                    # Tidak ada file CSV, ambil data historical terlebih dahulu
                    print(f"📥 [run_analysis] No CSV files found, fetching historical data...")
                    success = self.send_message(
                        chat_id,
                        "📥 <b>Mengambil data historical...</b>\n"
                        "⏳ Ini mungkin memakan waktu beberapa detik..."
                    )
                    print(f"{'✅' if success else '❌'} [run_analysis] Historical data notification sent: {success}")
                    
                    print(f"🔄 [run_analysis] Running get_historical_data.py...")
                    result_data = subprocess.run(
                        [sys.executable, "get_historical_data.py"],
                        capture_output=True,
                        text=True,
                        timeout=120  # 2 menit timeout
                    )
                    print(f"📊 [run_analysis] get_historical_data.py completed: returncode={result_data.returncode}")
                    
                    if result_data.returncode == 0:
                        print(f"✅ [run_analysis] Historical data fetched successfully")
                        success = self.send_message(
                            chat_id,
                            "✅ <b>Data historical berhasil diambil</b>\n"
                            "🔄 Melanjutkan ke analisis..."
                        )
                        print(f"{'✅' if success else '❌'} [run_analysis] Success notification sent: {success}")
                    else:
                        # Data tidak berhasil diambil, tampilkan error detail
                        error_output = result_data.stderr[:500] if result_data.stderr else result_data.stdout[-500:] if result_data.stdout else "Unknown error"
                        print(f"⚠️  Warning: Gagal mengambil data historical")
                        print(f"   Return code: {result_data.returncode}")
                        print(f"   Error output: {error_output}")
                        
                        # Cek apakah error karena symbol tidak ditemukan
                        error_lower = error_output.lower()
                        if "not found" in error_lower or "no data" in error_lower or "empty" in error_lower:
                            self.send_message(
                                chat_id,
                                f"⚠️ <b>Symbol {symbol} tidak ditemukan atau tidak memiliki data</b>\n\n"
                                f"💡 <b>Kemungkinan penyebab:</b>\n"
                                f"• Symbol tidak valid di yfinance\n"
                                f"• Coin tidak memiliki data historical\n"
                                f"• Format symbol salah\n\n"
                                f"🔄 <b>Mencoba fallback ke yfinance langsung...</b>"
                            )
                        else:
                            self.send_message(
                                chat_id,
                                f"⚠️ <b>Gagal mengambil data historical</b>\n\n"
                                f"🔄 <b>Mencoba fallback ke yfinance langsung...</b>\n\n"
                                f"<code>{error_output[:200]}</code>"
                            )
                        print(f"⚠️  Analisis akan menggunakan yfinance langsung")
            except Exception as e:
                # Error mengambil data, tapi lanjutkan saja
                print(f"⚠️  Warning: Error saat mengambil data historical: {e}")
            
            # Jalankan analisis_quant.py
            print(f"🚀 [run_analysis] Running analisis_quant.py...")
            result = subprocess.run(
                [sys.executable, "analisis_quant.py"],
                capture_output=True,
                text=True,
                timeout=300  # 5 menit timeout
            )
            print(f"📊 [run_analysis] analisis_quant.py completed: returncode={result.returncode}")
            
            if result.returncode == 0:
                # Analisis berhasil, hasil sudah dikirim otomatis oleh analisis_quant.py
                print(f"✅ [run_analysis] Analysis completed successfully for {symbol}")
                if result.stdout:
                    print(f"📝 [run_analysis] stdout (last 200 chars): {result.stdout[-200:]}")
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
            config_file = "config.py"
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
            config_file = "config.py"
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
            config_file = "config.py"
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
{indent}"DAY_TRADING": 30,       # 30 hari untuk day trading
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
        
        # Parse symbol
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
                "• BTC-USD\n"
                "• BTC/USD\n"
                "• BTCUSD\n"
                "• BTC\n\n"
                "<b>Contoh:</b>\n"
                "• <code>BTC-USD</code>\n"
                "• <code>ETH</code>\n"
                "• <code>SOL-USD</code>\n\n"
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
            "• <code>/screen [days] [top_n]</code> - Screen coins\n"
            "  Contoh: <code>/screen</code> (90 hari, top 10)\n"
            "          <code>/screen 7</code> (7 hari, top 10)\n"
            "          <code>/screen 7 15</code> (7 hari, top 15)\n"
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
                "• <code>SCALPING</code> - Trading sangat cepat (detik-menit)\n"
                "• <code>DAY_TRADING</code> - Trading dalam 1 hari\n"
                "• <code>SWING_TRADING</code> - Trading beberapa hari-minggu\n"
                "• <code>POSITION_TRADING</code> - Trading jangka panjang (minggu-bulan)\n\n"
                "<b>Contoh:</b>\n"
                "<code>/style DAY_TRADING</code>\n"
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
                f"• SCALPING\n"
                f"• DAY_TRADING\n"
                f"• SWING_TRADING\n"
                f"• POSITION_TRADING\n\n"
                f"Contoh: <code>/style DAY_TRADING</code>"
            )
            return
        
        # Update TRADING_STYLE untuk user ini
        self.user_trading_styles[chat_id] = style
        
        # Update config.py
        self.update_config_trading_style(style)
        
        # Kirim konfirmasi
        style_descriptions = {
            "SCALPING": "Trading sangat cepat (detik-menit), banyak sinyal, profit kecil per trade",
            "DAY_TRADING": "Trading dalam 1 hari, beberapa sinyal per hari",
            "SWING_TRADING": "Trading beberapa hari-minggu, sinyal lebih jarang tapi lebih reliable",
            "POSITION_TRADING": "Trading jangka panjang (minggu-bulan), sinyal sangat jarang"
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
            from config import TRADING_STYLE, SYMBOL, get_days_back
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
            "• <code>/screen [days] [top_n]</code> - Screen coins\n"
            "  Contoh: <code>/screen</code> (90 hari, top 10)\n"
            "          <code>/screen 7</code> (7 hari, top 10)\n"
            "          <code>/screen 7 15</code> (7 hari, top 15)\n"
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
            from coin_screening import screen_coins, DEFAULT_COINS
            from telegram_bot import TelegramBot
            from config import (ENABLE_TELEGRAM_BOT, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
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
                use_adaptive_filtering=True  # Auto-relax filters jika tidak ada hasil
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
            ma_signal = coin['ma_signal']
            score = coin['combined_score']
            
            # Emoji berdasarkan signal
            signal_emoji = "🟢" if ma_signal == "BUY" else "🔴" if ma_signal == "SELL" else "🟡"
            change_emoji = "📈" if change_7d > 0 else "📉"
            
            lines.append(f"<b>{i}. {symbol}</b>")
            lines.append(f"💵 Price: ${price:,.4f}")
            lines.append(f"{change_emoji} Change: 1d: {change_1d:+.2f}% | 7d: {change_7d:+.2f}%")
            lines.append(f"📊 Volume: {volume_ratio:.2f}x")
            lines.append(f"📈 RSI: {rsi:.2f} ({rsi_signal})")
            lines.append(f"{signal_emoji} Signal: {ma_signal}")
            lines.append(f"⭐ Score: {score:.4f}")
            lines.append("")
        
        lines.append("💡 <i>Kirim symbol coin untuk analisis detail</i>")
        
        return "\n".join(lines)
    
    def start_polling(self):
        """Mulai polling untuk menerima pesan dari Telegram"""
        print("🤖 Starting Trading Quant Bot...")
        print(f"📡 Listening for messages...")
        print(f"💬 Bot siap menerima command!")
        print()
        
        self.running = True
        
        while self.running:
            try:
                updates = self.get_updates()
                
                if updates and updates.get('ok'):
                    for update in updates.get('result', []):
                        # Update offset
                        self.offset = update.get('update_id', 0) + 1
                        
                        # Handle message
                        if 'message' in update:
                            message = update['message']
                            self.handle_message(message)
                
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

