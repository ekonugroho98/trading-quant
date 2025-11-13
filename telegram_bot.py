"""
Telegram Bot Integration Module
Mengirim notifikasi trading recommendation ke Telegram
"""

import requests
from typing import Dict, Optional
from datetime import datetime
import os


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
        self.photo_url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    
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
    
    def send_photo(self, photo_path: str, caption: Optional[str] = None) -> bool:
        """
        Kirim foto ke Telegram
        
        Args:
            photo_path: Path ke file foto yang akan dikirim
            caption: Caption untuk foto (optional)
        
        Returns:
            True jika berhasil, False jika gagal
        """
        if not self.bot_token or not self.chat_id:
            print("⚠️  Telegram Bot Token atau Chat ID tidak ditemukan")
            return False
        
        if not os.path.exists(photo_path):
            print(f"⚠️  File foto tidak ditemukan: {photo_path}")
            return False
        
        try:
            with open(photo_path, 'rb') as photo:
                files = {'photo': photo}
                data = {
                    'chat_id': self.chat_id
                }
                if caption:
                    data['caption'] = caption
                
                response = requests.post(
                    self.photo_url,
                    files=files,
                    data=data,
                    timeout=30
                )
                
                if response.status_code == 200:
                    return True
                else:
                    print(f"❌ Error mengirim foto ke Telegram: {response.status_code}")
                    print(f"   Response: {response.text}")
                    return False
        except Exception as e:
            print(f"❌ Error mengirim foto ke Telegram: {e}")
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
        
        # Trading Setup
        if action == 'HOLD':
            # Untuk HOLD, tampilkan None
            lines.append("💰 <b>Trading Setup:</b>")
            lines.append("   Entry Price: None")
            lines.append("   Stop Loss: None")
            lines.append("")
            lines.append("🎯 <b>Targets:</b> None")
            lines.append("")
            lines.append("⚠️ <b>No Entry</b> - Tidak ada posisi trading saat ini")
            lines.append("")
        else:
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
            else:
                lines.append("🎯 <b>Targets:</b> None")
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
    
    def format_trading_setup(self, setup: Dict, symbol: Optional[str] = None) -> str:
        """
        Format trading setup untuk Telegram
        
        Args:
            setup: Dictionary dengan trading setup dari generate_trading_setup
            symbol: Trading symbol (optional)
        
        Returns:
            Formatted HTML message
        """
        lines = []
        
        # Header
        lines.append("📋 <b>TRADING SETUP</b>")
        lines.append("=" * 40)
        lines.append("")
        
        if symbol:
            lines.append(f"📊 <b>Symbol:</b> {symbol}")
            lines.append("")
        
        # Direction dan Action
        direction = setup.get('direction', 'N/A')
        action = setup.get('action', 'N/A')
        lines.append(f"📈 <b>Direction:</b> {direction} ({action})")
        lines.append("")
        
        # Entry Price
        entry = setup.get('entry', 'N/A')
        if isinstance(entry, (int, float)):
            lines.append(f"💰 <b>LIMIT ENTRY:</b> {entry:,.2f}")
        else:
            lines.append(f"💰 <b>LIMIT ENTRY:</b> {entry}")
        lines.append("")
        
        # Stop Loss
        stop_loss = setup.get('stop_loss', 'N/A')
        risk_pct = setup.get('risk_pct', 0)
        if isinstance(stop_loss, (int, float)):
            lines.append(f"🛑 <b>Stop Loss:</b> {stop_loss:,.2f} (-{risk_pct:.2f}%)")
        else:
            lines.append(f"🛑 <b>Stop Loss:</b> {stop_loss}")
        lines.append("")
        
        # Targets
        tp1 = setup.get('tp1', 'N/A')
        tp2 = setup.get('tp2', 'N/A')
        tp3 = setup.get('tp3', 'N/A')
        
        lines.append("🎯 <b>Targets:</b>")
        
        # Calculate percentages
        if isinstance(entry, (int, float)) and entry > 0:
            if isinstance(tp1, (int, float)):
                tp1_pct = ((tp1 - entry) / entry) * 100 if direction == "LONG" else ((entry - tp1) / entry) * 100
                lines.append(f"   TP1: {tp1:,.2f} (+{tp1_pct:.2f}%)")
            else:
                lines.append(f"   TP1: {tp1}")
            
            if isinstance(tp2, (int, float)):
                tp2_pct = ((tp2 - entry) / entry) * 100 if direction == "LONG" else ((entry - tp2) / entry) * 100
                lines.append(f"   TP2: {tp2:,.2f} (+{tp2_pct:.2f}%)")
            else:
                lines.append(f"   TP2: {tp2}")
            
            if isinstance(tp3, (int, float)):
                tp3_pct = ((tp3 - entry) / entry) * 100 if direction == "LONG" else ((entry - tp3) / entry) * 100
                lines.append(f"   TP3: {tp3:,.2f} (+{tp3_pct:.2f}%)")
            else:
                lines.append(f"   TP3: {tp3}")
        else:
            lines.append(f"   TP1: {tp1}")
            lines.append(f"   TP2: {tp2}")
            lines.append(f"   TP3: {tp3}")
        
        lines.append("")
        
        # Risk/Reward Ratio
        if isinstance(entry, (int, float)) and isinstance(stop_loss, (int, float)) and entry > 0:
            if direction == "LONG":
                rr1 = (tp1 - entry) / (entry - stop_loss) if isinstance(tp1, (int, float)) else 0
                rr2 = (tp2 - entry) / (entry - stop_loss) if isinstance(tp2, (int, float)) else 0
                rr3 = (tp3 - entry) / (entry - stop_loss) if isinstance(tp3, (int, float)) else 0
            else:
                rr1 = (entry - tp1) / (stop_loss - entry) if isinstance(tp1, (int, float)) else 0
                rr2 = (entry - tp2) / (stop_loss - entry) if isinstance(tp2, (int, float)) else 0
                rr3 = (entry - tp3) / (stop_loss - entry) if isinstance(tp3, (int, float)) else 0
            
            lines.append("📊 <b>Risk/Reward Ratio:</b>")
            lines.append(f"   TP1: {rr1:.2f}:1")
            lines.append(f"   TP2: {rr2:.2f}:1")
            lines.append(f"   TP3: {rr3:.2f}:1")
            lines.append("")
        
        # Warning
        lines.append("⚠️ <i>Setup berdasarkan analisis teknis. Gunakan risk management!</i>")
        lines.append("")
        
        return "\n".join(lines)
    
    def send_trading_setup(self, setup: Dict, symbol: Optional[str] = None) -> bool:
        """
        Kirim trading setup ke Telegram
        
        Args:
            setup: Dictionary dengan trading setup
            symbol: Trading symbol (optional)
        
        Returns:
            True jika berhasil, False jika gagal
        """
        message = self.format_trading_setup(setup, symbol)
        return self.send_message(message)
    
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

