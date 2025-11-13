"""
Telegram Bot Integration Module
Mengirim notifikasi trading recommendation ke Telegram
"""

import requests
from typing import Dict, Optional
from datetime import datetime


class TelegramBot:
    """Class untuk mengirim pesan ke Telegram Bot"""
    
    def __init__(self, bot_token: str, chat_id: str):
        """
        Initialize Telegram Bot
        
        Args:
            bot_token: Telegram Bot Token dari @BotFather
            chat_id: Chat ID untuk mengirim pesan
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """
        Kirim pesan ke Telegram
        
        Args:
            text: Text pesan yang akan dikirim
            parse_mode: Parse mode (HTML atau Markdown)
        
        Returns:
            True jika berhasil, False jika gagal
        """
        if not self.bot_token or not self.chat_id:
            print("⚠️  Telegram Bot Token atau Chat ID tidak ditemukan")
            return False
        
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        
        try:
            response = requests.post(self.api_url, json=payload, timeout=10)
            if response.status_code == 200:
                return True
            else:
                print(f"❌ Error mengirim ke Telegram: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error menghubungi Telegram API: {e}")
            return False
    
    def format_trading_recommendation(self, 
                                     recommendation: Dict,
                                     current_price: Optional[float] = None,
                                     support: Optional[float] = None,
                                     resistance: Optional[float] = None,
                                     timeframe: Optional[str] = None,
                                     symbol: Optional[str] = None) -> str:
        """
        Format trading recommendation untuk Telegram
        
        Args:
            recommendation: Dictionary dengan rekomendasi dari DeepSeek
            current_price: Harga saat ini
            support: Support level
            resistance: Resistance level
            timeframe: Timeframe trading
            symbol: Trading symbol
        
        Returns:
            Formatted HTML message
        """
        lines = []
        
        # Header
        lines.append("🤖 <b>DEEPSEEK AI TRADING RECOMMENDATION</b>")
        lines.append("=" * 40)
        lines.append("")
        
        # Symbol dan Timeframe
        if symbol:
            lines.append(f"📊 <b>Symbol:</b> {symbol}")
        if timeframe:
            lines.append(f"⏰ <b>Timeframe:</b> {timeframe}")
        lines.append("")
        
        # Current Price
        if current_price is not None:
            lines.append(f"💵 <b>Current Price:</b> {current_price:,.2f}")
            lines.append("")
        
        # Support & Resistance
        if support is not None or resistance is not None:
            lines.append("📈 <b>Key Levels:</b>")
            if support is not None:
                lines.append(f"   🟢 Support: {support:,.2f}")
            if resistance is not None:
                lines.append(f"   🔴 Resistance: {resistance:,.2f}")
            lines.append("")
        
        # Action & Position
        action = recommendation.get('action', 'N/A')
        position = recommendation.get('position', 'N/A')
        confidence = recommendation.get('confidence', 0)
        
        # Emoji berdasarkan action
        action_emoji = "🟢" if action == "BUY" else "🔴" if action == "SELL" else "🟡"
        
        lines.append(f"{action_emoji} <b>Action:</b> {action}")
        lines.append(f"📍 <b>Position:</b> {position}")
        lines.append(f"🎯 <b>Confidence:</b> {confidence}%")
        lines.append("")
        
        # Entry & Stop Loss
        entry_price = recommendation.get('entry_price', 'N/A')
        stop_loss = recommendation.get('stop_loss', 'N/A')
        
        lines.append("💰 <b>Trading Setup:</b>")
        if isinstance(entry_price, (int, float)):
            lines.append(f"   Entry: {entry_price:,.2f}")
        else:
            lines.append(f"   Entry: {entry_price}")
        
        # Stop Loss dengan persentase
        if isinstance(stop_loss, (int, float)) and isinstance(entry_price, (int, float)) and entry_price > 0:
            stop_loss_pct = ((stop_loss - entry_price) / entry_price) * 100
            sign = "+" if stop_loss_pct > 0 else ""
            lines.append(f"   Stop Loss: {stop_loss:,.2f} ({sign}{stop_loss_pct:.2f}%)")
        else:
            lines.append(f"   Stop Loss: {stop_loss}")
        lines.append("")
        
        # Targets dengan persentase
        targets = recommendation.get('targets', [])
        if targets:
            lines.append("🎯 <b>Targets:</b>")
            for i, target in enumerate(targets, 1):
                if isinstance(target, (int, float)) and isinstance(entry_price, (int, float)) and entry_price > 0:
                    target_pct = ((target - entry_price) / entry_price) * 100
                    sign = "+" if target_pct > 0 else ""
                    lines.append(f"   TP{i}: {target:,.2f} ({sign}{target_pct:.2f}%)")
                else:
                    lines.append(f"   TP{i}: {target}")
            lines.append("")
        
        # Reason
        reason = recommendation.get('reason', '')
        if reason:
            lines.append("💡 <b>Reason:</b>")
            lines.append(f"   {reason}")
            lines.append("")
        
        # Timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines.append(f"⏰ <i>{timestamp}</i>")
        
        return "\n".join(lines)
    
    def send_trading_recommendation(self,
                                   recommendation: Dict,
                                   current_price: Optional[float] = None,
                                   support: Optional[float] = None,
                                   resistance: Optional[float] = None,
                                   timeframe: Optional[str] = None,
                                   symbol: Optional[str] = None) -> bool:
        """
        Kirim trading recommendation ke Telegram
        
        Args:
            recommendation: Dictionary dengan rekomendasi
            current_price: Harga saat ini
            support: Support level
            resistance: Resistance level
            timeframe: Timeframe trading
            symbol: Trading symbol
        
        Returns:
            True jika berhasil, False jika gagal
        """
        message = self.format_trading_recommendation(
            recommendation,
            current_price,
            support,
            resistance,
            timeframe,
            symbol
        )
        
        return self.send_message(message)

