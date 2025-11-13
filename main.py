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
        Ambil update terbaru dari Telegram
        
        Returns:
            Dictionary dengan updates atau None jika error
        """
        try:
            url = f"{self.api_url}/getUpdates"
            params = {
                "offset": self.offset,
                "timeout": 10
            }
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Error mendapatkan updates: {response.status_code}")
                return None
        except Exception as e:
            print(f"⚠️  Error menghubungi Telegram API: {e}")
            return None
    
    def send_message(self, chat_id: str, text: str, parse_mode: str = "HTML") -> bool:
        """
        Kirim pesan ke Telegram
        
        Args:
            chat_id: Chat ID tujuan
            text: Text pesan
            parse_mode: Parse mode (HTML atau Markdown)
        
        Returns:
            True jika berhasil, False jika gagal
        """
        try:
            url = f"{self.api_url}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode
            }
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Error mengirim pesan: {e}")
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
            # Kirim notifikasi sedang memproses
            self.send_message(
                chat_id,
                f"🔄 <b>Memproses analisis untuk {symbol}...</b>\n"
                f"⏳ Mohon tunggu, ini mungkin memakan waktu beberapa detik..."
            )
            
            # Update config.py dengan symbol baru, chat_id, dan trading style
            self.update_config_symbol(symbol)
            self.update_config_chat_id(chat_id)
            
            # Update TRADING_STYLE jika user sudah set
            if chat_id in self.user_trading_styles:
                self.update_config_trading_style(self.user_trading_styles[chat_id])
            
            # Tunggu sebentar untuk memastikan file config.py sudah ter-write
            time.sleep(0.5)
            
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
                if not csv_files:
                    # Tidak ada file CSV, ambil data historical terlebih dahulu
                    self.send_message(
                        chat_id,
                        "📥 <b>Mengambil data historical...</b>\n"
                        "⏳ Ini mungkin memakan waktu beberapa detik..."
                    )
                    
                    result_data = subprocess.run(
                        [sys.executable, "get_historical_data.py"],
                        capture_output=True,
                        text=True,
                        timeout=120  # 2 menit timeout
                    )
                    
                    if result_data.returncode == 0:
                        self.send_message(
                            chat_id,
                            "✅ <b>Data historical berhasil diambil</b>\n"
                            "🔄 Melanjutkan ke analisis..."
                        )
                    else:
                        # Data tidak berhasil diambil, tapi lanjutkan saja (analisis_quant.py akan fallback ke yfinance)
                        print(f"⚠️  Warning: Gagal mengambil data historical, analisis akan menggunakan yfinance")
            except Exception as e:
                # Error mengambil data, tapi lanjutkan saja
                print(f"⚠️  Warning: Error saat mengambil data historical: {e}")
            
            # Jalankan analisis_quant.py
            result = subprocess.run(
                [sys.executable, "analisis_quant.py"],
                capture_output=True,
                text=True,
                timeout=300  # 5 menit timeout
            )
            
            if result.returncode == 0:
                # Analisis berhasil, hasil sudah dikirim otomatis oleh analisis_quant.py
                return True
            else:
                # Ada error
                error_msg = result.stderr[:500] if result.stderr else "Unknown error"
                self.send_message(
                    chat_id,
                    f"❌ <b>Error menjalankan analisis untuk {symbol}</b>\n\n"
                    f"<code>{error_msg}</code>"
                )
                return False
                
        except subprocess.TimeoutExpired:
            self.send_message(
                chat_id,
                f"⏱️ <b>Timeout!</b>\n\n"
                f"Analisis untuk {symbol} memakan waktu terlalu lama (>5 menit).\n"
                f"Silakan coba lagi nanti."
            )
            return False
        except Exception as e:
            self.send_message(
                chat_id,
                f"❌ <b>Error:</b> {str(e)}"
            )
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
        Update TRADING_STYLE di config.py
        
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
            
            if new_content != content:
                with open(config_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"✅ Config updated: TRADING_STYLE = {trading_style}")
            else:
                # Coba pattern alternatif
                pattern2 = r'TRADING_STYLE\s*=\s*["\'].*?["\']'
                new_content2 = re.sub(pattern2, replacement, content)
                if new_content2 != content:
                    with open(config_file, 'w', encoding='utf-8') as f:
                        f.write(new_content2)
                    print(f"✅ Config updated: TRADING_STYLE = {trading_style}")
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
        
        if not text:
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
        
        # Check if user has started the bot
        if chat_id not in self.active_users:
            self.send_message(
                chat_id,
                "⚠️ <b>Bot belum diaktifkan!</b>\n\n"
                "Silakan kirim command <code>/start</code> terlebih dahulu untuk memulai."
            )
            return
        
        # Parse symbol
        symbol = self.parse_symbol(text)
        
        if symbol:
            # Valid symbol, jalankan analisis
            print(f"📨 Received command: {text} -> {symbol} from chat {chat_id}")
            self.run_analysis(symbol, chat_id)
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
            "• <code>/settings</code> - Lihat pengaturan\n\n"
            "🚀 <b>Mulai dengan mengirim symbol coin!</b>"
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
            from config import TRADING_STYLE, SYMBOL
            config_style = TRADING_STYLE
            config_symbol = SYMBOL
        except:
            config_style = "DAY_TRADING"
            config_symbol = "BTC-USD"
        
        # Gunakan user style jika ada, kalau tidak gunakan config
        active_style = self.user_trading_styles.get(chat_id, config_style)
        
        settings_text = (
            "⚙️ <b>Pengaturan Saat Ini</b>\n\n"
            f"📊 <b>TRADING_STYLE:</b> <code>{active_style}</code>\n"
            f"💰 <b>SYMBOL:</b> <code>{config_symbol}</code>\n\n"
            "<b>Command yang tersedia:</b>\n"
            "• <code>/style STYLE</code> - Ubah TRADING_STYLE\n"
            "• <code>/settings</code> - Lihat pengaturan\n"
            "• Kirim symbol coin untuk analisis"
        )
        
        self.send_message(chat_id, settings_text)
    
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

