"""
Telegram Bot Integration Module
Mengirim notifikasi trading recommendation ke Telegram
"""

import requests
from typing import Dict, Optional
from datetime import datetime
import os


def format_price_no_rounding(price: float) -> str:
    """
    Format harga tanpa pembulatan, menampilkan semua digit signifikan
    
    Args:
        price: Harga yang akan diformat
    
    Returns:
        String dengan harga yang diformat tanpa pembulatan
    """
    if price is None:
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


def format_price_with_comma(price: float, decimals: Optional[int] = None) -> str:
    """
    Format harga dengan koma sebagai thousand separator (format internasional)
    Auto-detect jumlah desimal yang tepat berdasarkan ukuran harga
    
    Args:
        price: Harga yang akan diformat
        decimals: Jumlah desimal (None = auto-detect berdasarkan ukuran harga)
    
    Returns:
        String dengan harga yang diformat dengan koma sebagai thousand separator
    """
    if price is None:
        return "None"
    
    try:
        price = float(price)
        
        # Auto-detect decimals jika tidak ditentukan
        if decimals is None:
            if price == 0:
                return "0"
            elif price < 0.01:
                # Harga sangat kecil (< 0.01), gunakan 6-8 desimal
                decimals = 8
            elif price < 1:
                # Harga kecil (< 1), gunakan 4-6 desimal
                decimals = 6
            elif price < 1000:
                # Harga sedang, gunakan 2-4 desimal
                decimals = 4
            else:
                # Harga besar, gunakan 0-2 desimal
                decimals = 2
        
        if decimals == 0:
            # Format tanpa desimal
            return f"{int(round(price)):,}"
        else:
            # Format dengan desimal
            formatted = f"{price:,.{decimals}f}"
            # Hapus trailing zeros tapi tetap tampilkan minimal 2 desimal untuk harga kecil
            if '.' in formatted:
                # Untuk harga < 1, minimal 2 desimal
                if price < 1:
                    # Pastikan minimal 2 desimal
                    parts = formatted.split('.')
                    if len(parts) == 2:
                        decimal_part = parts[1].rstrip('0')
                        if len(decimal_part) < 2:
                            decimal_part = decimal_part.ljust(2, '0')
                        formatted = f"{parts[0]}.{decimal_part}"
                else:
                    # Untuk harga >= 1, hapus trailing zeros
                    formatted = formatted.rstrip('0').rstrip('.')
            return formatted
    except (ValueError, TypeError):
        return str(price)


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
            lines.append(f"💵 <b>Current Price:</b> {format_price_no_rounding(current_price)}")
            lines.append("")
        
        # Support & Resistance
        if support is not None or resistance is not None:
            lines.append("📈 <b>Key Levels:</b>")
            if support is not None:
                lines.append(f"   🟢 Support: {format_price_no_rounding(support)}")
            if resistance is not None:
                lines.append(f"   🔴 Resistance: {format_price_no_rounding(resistance)}")
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
                lines.append(f"   Entry: {format_price_no_rounding(entry_price)}")
            else:
                lines.append(f"   Entry: {entry_price}")
            
            # Stop Loss dengan persentase
            if isinstance(stop_loss, (int, float)) and isinstance(entry_price, (int, float)) and entry_price > 0:
                stop_loss_pct = ((stop_loss - entry_price) / entry_price) * 100
                sign = "+" if stop_loss_pct > 0 else ""
                stop_loss_str = format_price_no_rounding(stop_loss)
                pct_str = f"{sign}{stop_loss_pct:.6f}%".rstrip('0').rstrip('.')
                lines.append(f"   Stop Loss: {stop_loss_str} ({pct_str})")
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
                        target_str = format_price_no_rounding(target)
                        pct_str = f"{sign}{target_pct:.6f}%".rstrip('0').rstrip('.')
                        lines.append(f"   TP{i}: {target_str} ({pct_str})")
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
        
        # Multiple Entry Levels - Tentukan format berdasarkan skala harga
        entry = setup.get('entry', 'N/A')
        entry1 = setup.get('entry1', 'N/A')
        entry2 = setup.get('entry2', 'N/A')
        entry3 = setup.get('entry3', 'N/A')
        
        if isinstance(entry, (int, float)):
            # Tentukan format angka berdasarkan skala harga (sama seperti analisis_quant.py)
            if entry < 1:
                price_format = ".4f"  # 4 desimal untuk harga kecil (< 1)
            elif entry < 100:
                price_format = ".4f"  # 4 desimal untuk harga menengah
            elif entry < 1000:
                price_format = ".2f"  # 2 desimal untuk harga besar
            else:
                price_format = ".0f"  # 0 desimal untuk harga sangat besar
            
            # Format multiple entry levels
            lines.append("💰 <b>MULTIPLE ENTRY LEVELS:</b>")
            if isinstance(entry1, (int, float)):
                if price_format == ".4f":
                    lines.append(f"   Entry 1 (Agresif): {format_price_no_rounding(entry1)}")
                elif price_format == ".2f":
                    lines.append(f"   Entry 1 (Agresif): {format_price_no_rounding(entry1)}")
                else:
                    lines.append(f"   Entry 1 (Agresif): {format_price_no_rounding(entry1)}")
            else:
                lines.append(f"   Entry 1 (Agresif): {entry1}")
            
            if isinstance(entry2, (int, float)):
                if price_format == ".4f":
                    lines.append(f"   Entry 2 (Konservatif - Recommended): {format_price_no_rounding(entry2)}")
                elif price_format == ".2f":
                    lines.append(f"   Entry 2 (Konservatif - Recommended): {format_price_no_rounding(entry2)}")
                else:
                    lines.append(f"   Entry 2 (Konservatif - Recommended): {format_price_no_rounding(entry2)}")
            else:
                lines.append(f"   Entry 2 (Konservatif - Recommended): {entry2}")
            
            if isinstance(entry3, (int, float)):
                if price_format == ".4f":
                    lines.append(f"   Entry 3 (Sangat Konservatif): {format_price_no_rounding(entry3)}")
                elif price_format == ".2f":
                    lines.append(f"   Entry 3 (Sangat Konservatif): {format_price_no_rounding(entry3)}")
                else:
                    lines.append(f"   Entry 3 (Sangat Konservatif): {format_price_no_rounding(entry3)}")
            else:
                lines.append(f"   Entry 3 (Sangat Konservatif): {entry3}")
        else:
            # Fallback jika entry bukan angka
            lines.append("💰 <b>MULTIPLE ENTRY LEVELS:</b>")
            lines.append(f"   Entry 1 (Agresif): {entry1}")
            lines.append(f"   Entry 2 (Konservatif - Recommended): {entry2}")
            lines.append(f"   Entry 3 (Sangat Konservatif): {entry3}")
        lines.append("")
        
        # Stop Loss - Gunakan format yang sama dengan entry
        stop_loss = setup.get('stop_loss', 'N/A')
        risk_pct = setup.get('risk_pct', 0)
        if isinstance(stop_loss, (int, float)):
            # Gunakan format yang sama dengan entry
            if isinstance(entry, (int, float)):
                if entry < 1:
                    price_format = ".4f"
                elif entry < 100:
                    price_format = ".4f"
                elif entry < 1000:
                    price_format = ".2f"
                else:
                    price_format = ".0f"
                
                if price_format == ".4f":
                    lines.append(f"🛑 <b>Stop Loss:</b> {stop_loss:.4f} (-{risk_pct:.2f}%)")
                elif price_format == ".2f":
                    lines.append(f"🛑 <b>Stop Loss:</b> {stop_loss:.2f} (-{risk_pct:.2f}%)")
                else:
                    lines.append(f"🛑 <b>Stop Loss:</b> {stop_loss:.0f} (-{risk_pct:.2f}%)")
            else:
                lines.append(f"🛑 <b>Stop Loss:</b> {stop_loss:.2f} (-{risk_pct:.2f}%)")
        else:
            lines.append(f"🛑 <b>Stop Loss:</b> {stop_loss}")
        lines.append("")
        
        # Targets - Tampilkan persentase untuk setiap entry level
        tp1 = setup.get('tp1', 'N/A')
        tp2 = setup.get('tp2', 'N/A')
        tp3 = setup.get('tp3', 'N/A')
        
        lines.append("🎯 <b>Targets:</b>")
        
        # Tentukan format berdasarkan entry
        if isinstance(entry, (int, float)) and entry > 0:
            if entry < 1:
                price_format = ".4f"
            elif entry < 100:
                price_format = ".4f"
            elif entry < 1000:
                price_format = ".2f"
            else:
                price_format = ".0f"
            
            # Calculate percentages untuk setiap entry level dan format
            if isinstance(tp1, (int, float)) and isinstance(entry1, (int, float)) and isinstance(entry2, (int, float)) and isinstance(entry3, (int, float)):
                # TP1 dengan persentase untuk setiap entry level
                tp1_pct_e1 = ((tp1 - entry1) / entry1) * 100 if direction == "LONG" else ((entry1 - tp1) / entry1) * 100
                tp1_pct_e2 = ((tp1 - entry2) / entry2) * 100 if direction == "LONG" else ((entry2 - tp1) / entry2) * 100
                tp1_pct_e3 = ((tp1 - entry3) / entry3) * 100 if direction == "LONG" else ((entry3 - tp1) / entry3) * 100
                
                if price_format == ".4f":
                    lines.append(f"   TP1: {format_price_no_rounding(tp1)}")
                    lines.append(f"      • Entry 1: {tp1_pct_e1:+.2f}%")
                    lines.append(f"      • Entry 2: {tp1_pct_e2:+.2f}%")
                    lines.append(f"      • Entry 3: {tp1_pct_e3:+.2f}%")
                elif price_format == ".2f":
                    lines.append(f"   TP1: {format_price_no_rounding(tp1)}")
                    lines.append(f"      • Entry 1: {tp1_pct_e1:+.2f}%")
                    lines.append(f"      • Entry 2: {tp1_pct_e2:+.2f}%")
                    lines.append(f"      • Entry 3: {tp1_pct_e3:+.2f}%")
                else:
                    lines.append(f"   TP1: {format_price_no_rounding(tp1)}")
                    lines.append(f"      • Entry 1: {tp1_pct_e1:+.2f}%")
                    lines.append(f"      • Entry 2: {tp1_pct_e2:+.2f}%")
                    lines.append(f"      • Entry 3: {tp1_pct_e3:+.2f}%")
            elif isinstance(tp1, (int, float)):
                # Fallback jika entry levels tidak tersedia
                tp1_pct = ((tp1 - entry) / entry) * 100 if direction == "LONG" else ((entry - tp1) / entry) * 100
                if price_format == ".4f":
                    lines.append(f"   TP1: {format_price_no_rounding(tp1)} (+{tp1_pct:.2f}%)")
                elif price_format == ".2f":
                    lines.append(f"   TP1: {format_price_no_rounding(tp1)} (+{tp1_pct:.2f}%)")
                else:
                    lines.append(f"   TP1: {format_price_no_rounding(tp1)} (+{tp1_pct:.2f}%)")
            else:
                lines.append(f"   TP1: {tp1}")
            
            if isinstance(tp2, (int, float)) and isinstance(entry1, (int, float)) and isinstance(entry2, (int, float)) and isinstance(entry3, (int, float)):
                # TP2 dengan persentase untuk setiap entry level
                tp2_pct_e1 = ((tp2 - entry1) / entry1) * 100 if direction == "LONG" else ((entry1 - tp2) / entry1) * 100
                tp2_pct_e2 = ((tp2 - entry2) / entry2) * 100 if direction == "LONG" else ((entry2 - tp2) / entry2) * 100
                tp2_pct_e3 = ((tp2 - entry3) / entry3) * 100 if direction == "LONG" else ((entry3 - tp2) / entry3) * 100
                
                if price_format == ".4f":
                    lines.append(f"   TP2: {format_price_no_rounding(tp2)}")
                    lines.append(f"      • Entry 1: {tp2_pct_e1:+.2f}%")
                    lines.append(f"      • Entry 2: {tp2_pct_e2:+.2f}%")
                    lines.append(f"      • Entry 3: {tp2_pct_e3:+.2f}%")
                elif price_format == ".2f":
                    lines.append(f"   TP2: {format_price_no_rounding(tp2)}")
                    lines.append(f"      • Entry 1: {tp2_pct_e1:+.2f}%")
                    lines.append(f"      • Entry 2: {tp2_pct_e2:+.2f}%")
                    lines.append(f"      • Entry 3: {tp2_pct_e3:+.2f}%")
                else:
                    lines.append(f"   TP2: {format_price_no_rounding(tp2)}")
                    lines.append(f"      • Entry 1: {tp2_pct_e1:+.2f}%")
                    lines.append(f"      • Entry 2: {tp2_pct_e2:+.2f}%")
                    lines.append(f"      • Entry 3: {tp2_pct_e3:+.2f}%")
            elif isinstance(tp2, (int, float)):
                # Fallback jika entry levels tidak tersedia
                tp2_pct = ((tp2 - entry) / entry) * 100 if direction == "LONG" else ((entry - tp2) / entry) * 100
                if price_format == ".4f":
                    lines.append(f"   TP2: {format_price_no_rounding(tp2)} (+{tp2_pct:.2f}%)")
                elif price_format == ".2f":
                    lines.append(f"   TP2: {format_price_no_rounding(tp2)} (+{tp2_pct:.2f}%)")
                else:
                    lines.append(f"   TP2: {format_price_no_rounding(tp2)} (+{tp2_pct:.2f}%)")
            else:
                lines.append(f"   TP2: {tp2}")
            
            if isinstance(tp3, (int, float)) and isinstance(entry1, (int, float)) and isinstance(entry2, (int, float)) and isinstance(entry3, (int, float)):
                # TP3 dengan persentase untuk setiap entry level
                tp3_pct_e1 = ((tp3 - entry1) / entry1) * 100 if direction == "LONG" else ((entry1 - tp3) / entry1) * 100
                tp3_pct_e2 = ((tp3 - entry2) / entry2) * 100 if direction == "LONG" else ((entry2 - tp3) / entry2) * 100
                tp3_pct_e3 = ((tp3 - entry3) / entry3) * 100 if direction == "LONG" else ((entry3 - tp3) / entry3) * 100
                
                if price_format == ".4f":
                    lines.append(f"   TP3: {format_price_no_rounding(tp3)}")
                    lines.append(f"      • Entry 1: {tp3_pct_e1:+.2f}%")
                    lines.append(f"      • Entry 2: {tp3_pct_e2:+.2f}%")
                    lines.append(f"      • Entry 3: {tp3_pct_e3:+.2f}%")
                elif price_format == ".2f":
                    lines.append(f"   TP3: {format_price_no_rounding(tp3)}")
                    lines.append(f"      • Entry 1: {tp3_pct_e1:+.2f}%")
                    lines.append(f"      • Entry 2: {tp3_pct_e2:+.2f}%")
                    lines.append(f"      • Entry 3: {tp3_pct_e3:+.2f}%")
                else:
                    lines.append(f"   TP3: {format_price_no_rounding(tp3)}")
                    lines.append(f"      • Entry 1: {tp3_pct_e1:+.2f}%")
                    lines.append(f"      • Entry 2: {tp3_pct_e2:+.2f}%")
                    lines.append(f"      • Entry 3: {tp3_pct_e3:+.2f}%")
            elif isinstance(tp3, (int, float)):
                # Fallback jika entry levels tidak tersedia
                tp3_pct = ((tp3 - entry) / entry) * 100 if direction == "LONG" else ((entry - tp3) / entry) * 100
                if price_format == ".4f":
                    lines.append(f"   TP3: {format_price_no_rounding(tp3)} (+{tp3_pct:.2f}%)")
                elif price_format == ".2f":
                    lines.append(f"   TP3: {format_price_no_rounding(tp3)} (+{tp3_pct:.2f}%)")
                else:
                    lines.append(f"   TP3: {format_price_no_rounding(tp3)} (+{tp3_pct:.2f}%)")
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
    
    def format_ml_prediction(self, ml_result: Dict) -> str:
        """
        Format ML prediction results untuk Telegram (sesuai dengan RINGKASAN QUANT MODEL)
        
        Args:
            ml_result: Dictionary dengan hasil ML prediction
        
        Returns:
            Formatted HTML message
        """
        lines = []
        
        # Header (sesuai dengan terminal output)
        lines.append("📊 <b>RINGKASAN QUANT MODEL</b>")
        lines.append("=" * 40)
        lines.append("")
        
        # Data Historis
        if 'data_records' in ml_result:
            lines.append(f"📊 <b>Data Historis:</b> {ml_result['data_records']} records")
        
        # Feature Engineering
        if 'features_count' in ml_result:
            lines.append(f"🔧 <b>Feature Engineering:</b> {ml_result['features_count']} fitur")
        
        # Model
        model = ml_result.get('model', ml_result.get('model_type', 'N/A'))
        lines.append(f"🤖 <b>Model:</b> {model}")
        
        # Signal dengan Probabilitas (sesuai format terminal)
        signal = ml_result.get('signal', 'N/A')
        buy_prob = ml_result.get('buy_probability', ml_result.get('buy_prob', 0))
        
        signal_emoji = "🟢" if signal == "BELI" else "🔴" if signal == "JUAL" else "🟡"
        lines.append(f"📡 <b>Signal:</b> {signal} (Prob: {buy_prob:.1f}%)")
        lines.append("")
        
        # Backtesting Results (sesuai format terminal)
        if 'accuracy' in ml_result or 'expected_value' in ml_result or 'sharpe_ratio' in ml_result:
            if 'accuracy' in ml_result:
                accuracy = ml_result['accuracy']
                if isinstance(accuracy, float) and accuracy < 1:
                    accuracy = accuracy * 100  # Convert dari decimal ke persen
                lines.append(f"📈 <b>Accuracy:</b> {accuracy:.2f}%")
            
            if 'expected_value' in ml_result:
                expected = ml_result['expected_value']
                lines.append(f"📈 <b>Expected Value:</b> {expected:.2f}%")
            
            if 'sharpe_ratio' in ml_result:
                sharpe = ml_result['sharpe_ratio']
                sharpe_status = "Sangat Bagus" if sharpe > 2 else "Bagus" if sharpe > 1 else "Kurang"
                lines.append(f"📊 <b>Sharpe Ratio:</b> {sharpe:.2f} ({sharpe_status})")
            
            lines.append("")
        
        # Warning
        lines.append("⚠️ <i>Prediksi untuk referensi, bukan saran trading!</i>")
        lines.append("")
        
        return "\n".join(lines)
    
    def send_ml_prediction(self, ml_result: Dict) -> bool:
        """
        Kirim ML prediction results ke Telegram
        
        Args:
            ml_result: Dictionary dengan hasil ML prediction
        
        Returns:
            True jika berhasil, False jika gagal
        """
        message = self.format_ml_prediction(ml_result)
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
    
    def format_screening_results(self, results: list) -> str:
        """
        Format screening results untuk Telegram
        
        Args:
            results: List of coin metrics dictionaries dari coin_screening
        
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
            lines.append(f"💵 Price: ${format_price_no_rounding(price)}")
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
    
    def send_screening_results(self, results: list) -> bool:
        """
        Kirim screening results ke Telegram
        
        Args:
            results: List of coin metrics dictionaries
        
        Returns:
            True jika berhasil, False jika gagal
        """
        message = self.format_screening_results(results)
        return self.send_message(message)
    
    def format_simplified_trading_signal(self,
                                         symbol: str,
                                         timeframe: Optional[str] = None,
                                         current_price: Optional[float] = None,
                                         support: Optional[float] = None,
                                         resistance: Optional[float] = None,
                                         trading_setup: Optional[Dict] = None,
                                         deepseek_recommendation: Optional[Dict] = None,
                                         ml_prediction: Optional[Dict] = None) -> str:
        """
        Format trading signal yang disederhanakan - menggabungkan semua informasi
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe (optional)
            current_price: Current price (optional)
            support: Support level (optional)
            resistance: Resistance level (optional)
            trading_setup: Trading setup dictionary (optional)
            deepseek_recommendation: DeepSeek recommendation dictionary (optional)
            ml_prediction: ML prediction dictionary (optional)
        
        Returns:
            Formatted HTML message
        """
        lines = []
        
        # Header (timeframe dalam kurung)
        if timeframe:
            lines.append(f"🤖 <b>TRADING SIGNAL: {symbol} ({timeframe})</b>")
        else:
            lines.append(f"🤖 <b>TRADING SIGNAL: {symbol}</b>")
        lines.append("")
        
        # Price & Key Levels (satu baris dengan koma separator)
        price_info = []
        if current_price is not None and current_price > 0:
            price_info.append(f"Price: {format_price_with_comma(current_price)}")
        if support is not None and support > 0:
            price_info.append(f"Support: {format_price_with_comma(support)}")
        if resistance is not None and resistance > 0:
            price_info.append(f"Resistance: {format_price_with_comma(resistance)}")
        
        if price_info:
            lines.append(" | ".join(price_info))
            lines.append("")
        
        # Deteksi konflik sinyal
        ai_action = None
        ai_position = None
        ai_confidence = 0
        ml_signal = None
        ml_prob = 0
        
        if deepseek_recommendation:
            ai_action = deepseek_recommendation.get('action', '').upper()
            ai_position = deepseek_recommendation.get('position', '').upper()
            ai_confidence = deepseek_recommendation.get('confidence', 0)
        
        if ml_prediction:
            ml_signal_raw = ml_prediction.get('signal', 'N/A')
            ml_prob = ml_prediction.get('buy_probability', ml_prediction.get('buy_prob', 0))
            # Convert ML signal to action
            if ml_signal_raw == "BELI":
                ml_signal = "BUY"
            elif ml_signal_raw == "JUAL":
                ml_signal = "SELL"
            else:
                ml_signal = "HOLD"
        
        # Tampilkan konflik jika ada
        has_conflict = False
        if ai_action and ml_signal and ai_action != "HOLD" and ml_signal != "HOLD":
            if (ai_action == "BUY" and ml_signal == "SELL") or (ai_action == "SELL" and ml_signal == "BUY"):
                has_conflict = True
                # Tampilkan dengan position jika ada
                ai_display = f"{ai_action}"
                if ai_position and ai_position != "CASH":
                    ai_display = f"{ai_action} ({ai_position})"
                
                ml_display = ml_signal
                # Infer position dari signal untuk ML
                if ml_signal == "BUY":
                    ml_display = f"{ml_signal} (LONG)"
                elif ml_signal == "SELL":
                    ml_display = f"{ml_signal} (SHORT)"
                
                lines.append("⚠️ <b>KONFLIKT:</b>")
                lines.append(f"   - AI Strategy: {ai_display} ({ai_confidence}% confidence)")
                lines.append(f"   - Quant Model: {ml_display} ({ml_prob:.1f}% probability)")
                lines.append("")
        
        # Rekomendasi final (prioritas AI Strategy jika ada konflik)
        if has_conflict:
            final_action = ai_action
            final_position = ai_position if ai_position and ai_position != "CASH" else None
            final_reason = "berdasarkan AI Strategy + Technical Pattern"
        elif ai_action:
            final_action = ai_action
            final_position = ai_position if ai_position and ai_position != "CASH" else None
            final_reason = "berdasarkan AI Strategy + Technical Pattern"
        elif ml_signal:
            final_action = ml_signal
            # Infer position dari signal
            final_position = "LONG" if ml_signal == "BUY" else "SHORT" if ml_signal == "SELL" else None
            final_reason = "berdasarkan Quant Model"
        else:
            final_action = "HOLD"
            final_position = None
            final_reason = "tidak ada sinyal jelas"
        
        # Format rekomendasi dengan position
        if final_position:
            lines.append(f"📊 <b>REKOMENDASI:</b> {final_action} ({final_position}) - {final_reason}")
        else:
            lines.append(f"📊 <b>REKOMENDASI:</b> {final_action} ({final_reason})")
        lines.append("")
        
        # Trading Setup (disederhanakan - hanya 2 entry dan 2 TP)
        if trading_setup:
            direction = trading_setup.get('direction', 'N/A')
            action_text = "SELL" if direction == "SHORT" else "BUY" if direction == "LONG" else "HOLD"
            
            lines.append(f"💰 <b>SETUP:</b>")
            
            # Entry levels (3 level: agresif, konservatif, sangat konservatif)
            entry1 = trading_setup.get('entry1')  # Agresif
            entry2 = trading_setup.get('entry2')  # Konservatif (recommended)
            entry3 = trading_setup.get('entry3')  # Sangat Konservatif
            
            # Hanya tampilkan entry jika nilainya valid (> 0)
            if entry1 and entry1 > 0 and entry2 and entry2 > 0 and entry3 and entry3 > 0:
                lines.append(f"   Entry: {format_price_with_comma(entry2)} (konservatif) / {format_price_with_comma(entry1)} (agresif) / {format_price_with_comma(entry3)} (sangat konservatif)")
            elif entry1 and entry1 > 0 and entry2 and entry2 > 0:
                lines.append(f"   Entry: {format_price_with_comma(entry2)} (konservatif) / {format_price_with_comma(entry1)} (agresif)")
            elif entry2 and entry2 > 0:
                lines.append(f"   Entry: {format_price_with_comma(entry2)}")
            elif entry1 and entry1 > 0:
                lines.append(f"   Entry: {format_price_with_comma(entry1)}")
            
            # Stop Loss
            stop_loss = trading_setup.get('stop_loss')
            risk_pct = trading_setup.get('risk_pct', 0)
            if stop_loss and stop_loss > 0:
                lines.append(f"   Stop Loss: {format_price_with_comma(stop_loss)} (-{risk_pct:.1f}%)")
            
            # Targets (3 TP dalam satu baris)
            tp1 = trading_setup.get('tp1')
            tp2 = trading_setup.get('tp2')
            tp3 = trading_setup.get('tp3')
            
            # Hanya tampilkan TP jika nilainya valid (> 0)
            if tp1 and tp1 > 0 and tp2 and tp2 > 0 and tp3 and tp3 > 0:
                # Calculate percentage untuk entry konservatif (entry2)
                if entry2 and isinstance(entry2, (int, float)) and entry2 > 0:
                    if direction == "LONG":
                        tp1_pct = ((tp1 - entry2) / entry2) * 100
                        tp2_pct = ((tp2 - entry2) / entry2) * 100
                        tp3_pct = ((tp3 - entry2) / entry2) * 100
                    else:  # SHORT
                        # Untuk SHORT, TP lebih rendah dari entry, jadi persentase negatif
                        tp1_pct = ((tp1 - entry2) / entry2) * 100
                        tp2_pct = ((tp2 - entry2) / entry2) * 100
                        tp3_pct = ((tp3 - entry2) / entry2) * 100
                    
                    # Format persentase dengan 2 desimal, selalu tampilkan tanda
                    lines.append(f"   TP1: {format_price_with_comma(tp1)} ({tp1_pct:+.2f}%) | TP2: {format_price_with_comma(tp2)} ({tp2_pct:+.2f}%) | TP3: {format_price_with_comma(tp3)} ({tp3_pct:+.2f}%)")
                else:
                    lines.append(f"   TP1: {format_price_with_comma(tp1)} | TP2: {format_price_with_comma(tp2)} | TP3: {format_price_with_comma(tp3)}")
            elif tp1 and tp1 > 0 and tp2 and tp2 > 0:
                # Fallback jika hanya ada 2 TP
                if entry2 and isinstance(entry2, (int, float)) and entry2 > 0:
                    if direction == "LONG":
                        tp1_pct = ((tp1 - entry2) / entry2) * 100
                        tp2_pct = ((tp2 - entry2) / entry2) * 100
                    else:  # SHORT
                        tp1_pct = ((tp1 - entry2) / entry2) * 100
                        tp2_pct = ((tp2 - entry2) / entry2) * 100
                    
                    lines.append(f"   TP1: {format_price_with_comma(tp1)} ({tp1_pct:+.2f}%) | TP2: {format_price_with_comma(tp2)} ({tp2_pct:+.2f}%)")
                else:
                    lines.append(f"   TP1: {format_price_with_comma(tp1)} | TP2: {format_price_with_comma(tp2)}")
            
            lines.append("")
        
        # Quant Metrics (ringkas dalam satu baris)
        if ml_prediction:
            metrics_parts = []
            
            accuracy = ml_prediction.get('accuracy')
            if accuracy is not None:
                if isinstance(accuracy, float) and accuracy < 1:
                    accuracy = accuracy * 100
                metrics_parts.append(f"Accuracy {accuracy:.0f}%")
            
            sharpe = ml_prediction.get('sharpe_ratio')
            if sharpe is not None:
                metrics_parts.append(f"Sharpe {sharpe:.2f}")
            
            expected_value = ml_prediction.get('expected_value')
            if expected_value is not None:
                metrics_parts.append(f"Expected Value {expected_value:.2f}%")
            
            if metrics_parts:
                lines.append(f"📈 <b>Quant Metrics:</b> {', '.join(metrics_parts)}")
                lines.append("")
        
        return "\n".join(lines)

