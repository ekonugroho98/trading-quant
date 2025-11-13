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
            
            # Update config.py dengan symbol baru dan chat_id
            self.update_config_symbol(symbol)
            self.update_config_chat_id(chat_id)
            
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
            "🚀 <b>Mulai dengan mengirim symbol coin!</b>"
        )
        
        self.send_message(chat_id, welcome_text)
        print(f"✅ User {chat_id} started the bot")
    
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

