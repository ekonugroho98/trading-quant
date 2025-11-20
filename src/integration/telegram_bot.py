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
        
        # Sanitize HTML: escape karakter khusus yang bisa menyebabkan parsing error
        if parse_mode == "HTML":
            import html
            import re
            # Telegram HTML hanya support: <b>, <i>, <u>, <s>, <a>, <code>, <pre>
            # Pattern untuk tag HTML yang valid di Telegram
            valid_tags_pattern = r'</?(?:b|i|u|s|a|code|pre)(?:\s[^>]*)?>'
            
            # Temukan semua tag HTML yang valid
            valid_tags = re.findall(valid_tags_pattern, text)
            
            # Escape semua karakter HTML terlebih dahulu
            text_escaped = html.escape(text)
            
            # Restore tag HTML yang valid
            for tag in valid_tags:
                # Escape tag untuk mencari di text_escaped
                tag_escaped = html.escape(tag)
                # Ganti kembali dengan tag asli
                text_escaped = text_escaped.replace(tag_escaped, tag)
            
            text = text_escaped
        
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
                # Jika error parsing, coba kirim tanpa parse_mode
                if response.status_code == 400 and "parse" in response.text.lower():
                    print("   ⚠️  Mencoba kirim tanpa HTML parsing...")
                    payload_no_html = {
                        "chat_id": self.chat_id,
                        "text": text.replace('<b>', '').replace('</b>', '').replace('<i>', '').replace('</i>', '')
                    }
                    response2 = requests.post(self.api_url, json=payload_no_html, timeout=10)
                    if response2.status_code == 200:
                        print("   ✅ Berhasil dikirim tanpa HTML formatting")
                        return True
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
                                         ml_prediction: Optional[Dict] = None,
                                         recent_trades_analysis: Optional[Dict] = None,
                                         pullback_status: Optional[Dict] = None,
                                         price_source: Optional[str] = None) -> str:
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
            price_source: Source of price data (optional, e.g., "real-time (ticker)" or "klines (last close)")
        
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
            price_str = f"Price: {format_price_with_comma(current_price)}"
            # Tambahkan info sumber harga jika tersedia
            if price_source:
                if "real-time" in price_source.lower():
                    price_str += " ⚡"  # Emoji untuk real-time
                elif "klines" in price_source.lower():
                    price_str += " ⏰"  # Emoji untuk klines (mungkin tidak real-time)
            price_info.append(price_str)
        if support is not None and support > 0:
            price_info.append(f"Support: {format_price_with_comma(support)}")
        if resistance is not None and resistance > 0:
            price_info.append(f"Resistance: {format_price_with_comma(resistance)}")
        
        if price_info:
            lines.append(" | ".join(price_info))
            # Tambahkan warning jika menggunakan klines price (mungkin tidak real-time)
            if price_source and "klines" in price_source.lower():
                lines.append("⚠️ <i>Harga dari klines (mungkin tidak real-time - pastikan data up-to-date)</i>")
            
            # Validasi: cek apakah harga berbeda terlalu jauh dari harga real di exchange
            # Jika berbeda lebih dari 10%, tambahkan warning
            if current_price and current_price > 0:
                try:
                    import requests
                    # Coba fetch real-time price dari Binance untuk validasi
                    symbol_for_check = symbol.replace("-USD", "") + "USDT" if "-USD" in symbol else symbol
                    if not symbol_for_check.endswith("USDT"):
                        symbol_for_check = symbol_for_check + "USDT"
                    
                    # Fetch dari Binance Futures API
                    try:
                        url = f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol_for_check.upper()}"
                        response = requests.get(url, timeout=5)
                        if response.status_code == 200:
                            real_price_data = response.json()
                            real_price = float(real_price_data.get('price', 0))
                            
                            if real_price > 0:
                                price_diff_pct = abs((current_price - real_price) / real_price) * 100
                                if price_diff_pct > 10.0:
                                    lines.append(f"⚠️ <b>WARNING:</b> Harga di signal ({format_price_with_comma(current_price)}) berbeda {price_diff_pct:.1f}% dari harga real di exchange ({format_price_with_comma(real_price)})")
                                    lines.append(f"   💡 Kemungkinan: data klines sudah lama atau symbol berbeda")
                                    lines.append(f"   💡 Pastikan data selalu up-to-date untuk akurasi signal")
                                elif price_diff_pct > 5.0:
                                    lines.append(f"ℹ️ Harga di signal berbeda {price_diff_pct:.1f}% dari harga real ({format_price_with_comma(real_price)}) - normal untuk volatile market")
                    except:
                        pass  # Skip jika tidak bisa fetch real price
                except:
                    pass  # Skip jika error
            
            lines.append("")
        
        # Lakukan direction auto-correction dan AI Strategy adjustment terlebih dahulu
        # agar quant_model_signal menggunakan direction yang sudah diperbaiki
        if trading_setup:
            direction = trading_setup.get('direction', 'N/A')
            entry2 = trading_setup.get('entry2')
            tp1 = trading_setup.get('tp1')
            stop_loss = trading_setup.get('stop_loss')
            
            # VALIDASI: Deteksi dan perbaiki inkonsistensi direction dengan data aktual
            if entry2 and isinstance(entry2, (int, float)) and entry2 > 0:
                tp_suggests_long = False
                tp_suggests_short = False
                sl_suggests_long = False
                sl_suggests_short = False
                
                if tp1 and isinstance(tp1, (int, float)) and tp1 > 0:
                    if tp1 > entry2:
                        tp_suggests_long = True
                    elif tp1 < entry2:
                        tp_suggests_short = True
                
                if stop_loss and isinstance(stop_loss, (int, float)) and stop_loss > 0:
                    if stop_loss < entry2:
                        sl_suggests_long = True
                    elif stop_loss > entry2:
                        sl_suggests_short = True
                
                actual_direction = None
                if tp_suggests_long and sl_suggests_long:
                    actual_direction = "LONG"
                elif tp_suggests_short and sl_suggests_short:
                    actual_direction = "SHORT"
                elif tp_suggests_long:
                    actual_direction = "LONG"
                elif tp_suggests_short:
                    actual_direction = "SHORT"
                elif sl_suggests_long:
                    actual_direction = "LONG"
                elif sl_suggests_short:
                    actual_direction = "SHORT"
                
                if actual_direction and direction != actual_direction:
                    print(f"⚠️  [TELEGRAM] Direction inconsistency detected: direction={direction} but TP/SL suggest {actual_direction}. Auto-correcting...")
                    print(f"   Entry2: {entry2}, TP1: {tp1}, SL: {stop_loss}")
                    direction = actual_direction
                    trading_setup['direction'] = actual_direction
            
            # ADJUSTMENT: Prioritaskan ML Prediction untuk Quant Model setup
            # Jika ML Prediction menunjukkan LONG, maka Quant Model setup harus LONG juga
            # Hanya adjust dengan AI Strategy jika ML Prediction tidak ada atau HOLD
            ml_direction_for_setup = None
            if ml_prediction:
                ml_signal_raw = ml_prediction.get('signal', 'N/A')
                if ml_signal_raw == "BELI":
                    ml_direction_for_setup = "LONG"
                elif ml_signal_raw == "JUAL":
                    ml_direction_for_setup = "SHORT"
            
            # Jika ML Prediction ada dan berbeda dengan direction saat ini, sesuaikan dengan ML Prediction
            # Trading setup sudah dihasilkan berdasarkan ML prediction di analisis_quant.py,
            # jadi kita hanya perlu memastikan direction sesuai dengan ML prediction
            if ml_direction_for_setup and direction != ml_direction_for_setup:
                print(f"🔄 [TELEGRAM] ML Prediction ({ml_direction_for_setup}) berbeda dengan Quant Model ({direction}). Menyesuaikan direction dengan ML Prediction...")
                print(f"   💡 Quant Model setup akan mengikuti ML Prediction: {ml_direction_for_setup}")
                
                # Update direction dengan ML Prediction
                direction = ml_direction_for_setup
                trading_setup['direction'] = ml_direction_for_setup
                
                # Recalculate entry, TP, dan SL agar sesuai dengan ML Prediction direction
                # Gunakan support/resistance untuk recalculate entry levels
                if current_price and current_price > 0 and support and resistance:
                    if ml_direction_for_setup == "LONG":
                        # LONG: entry di support atau di bawah current price, TP di atas, SL di bawah
                        # Entry konservatif: di support atau sedikit di atas support
                        entry2_new = support * 1.001 if support > 0 else current_price * 0.998
                        entry1_new = current_price * 0.999 if current_price > support * 1.002 else support * 1.002  # Agresif
                        entry3_new = support * 0.998 if support > 0 else current_price * 0.995  # Sangat konservatif
                        
                        # TP di atas entry
                        tp1_new = entry2_new * 1.10  # 10% profit
                        tp2_new = entry2_new * 1.15  # 15% profit
                        tp3_new = entry2_new * 1.20  # 20% profit
                        
                        # SL di bawah entry
                        stop_loss_new = entry2_new * 0.98  # 2% risk
                    else:  # SHORT
                        # SHORT: entry di resistance atau di atas current price, TP di bawah, SL di atas
                        # Entry konservatif: di resistance atau sedikit di bawah resistance
                        entry2_new = resistance * 0.999 if resistance > 0 else current_price * 1.002
                        entry1_new = current_price * 1.001 if current_price < resistance * 0.998 else resistance * 0.998  # Agresif
                        entry3_new = resistance * 1.002 if resistance > 0 else current_price * 1.005  # Sangat konservatif
                        
                        # TP di bawah entry
                        tp1_new = entry2_new * 0.90  # 10% profit
                        tp2_new = entry2_new * 0.85  # 15% profit
                        tp3_new = entry2_new * 0.80  # 20% profit
                        
                        # SL di atas entry
                        stop_loss_new = entry2_new * 1.02  # 2% risk
                    
                    # Update trading_setup dictionary
                    trading_setup['entry1'] = entry1_new
                    trading_setup['entry2'] = entry2_new
                    trading_setup['entry3'] = entry3_new
                    trading_setup['entry'] = entry2_new
                    trading_setup['stop_loss'] = stop_loss_new
                    trading_setup['tp1'] = tp1_new
                    trading_setup['tp2'] = tp2_new
                    trading_setup['tp3'] = tp3_new
                    
                    # Update local variables untuk digunakan di bawah
                    entry2 = entry2_new
                    tp1 = tp1_new
                    stop_loss = stop_loss_new
                    
                    # Recalculate risk_pct
                    if entry2_new and stop_loss_new and entry2_new > 0:
                        if ml_direction_for_setup == "LONG":
                            risk_pct = ((entry2_new - stop_loss_new) / entry2_new) * 100
                        else:  # SHORT
                            risk_pct = ((stop_loss_new - entry2_new) / entry2_new) * 100
                        trading_setup['risk_pct'] = abs(risk_pct)
                
                print(f"   ✅ Direction dan TP/SL disesuaikan dengan ML Prediction: {ml_direction_for_setup}")
            
            # ADJUSTMENT: Jika ML Prediction tidak ada atau HOLD, dan AI Strategy berbeda dengan Quant Model,
            # sesuaikan trading setup dengan AI Strategy untuk konsistensi
            elif deepseek_recommendation and (not ml_direction_for_setup or ml_direction_for_setup == "HOLD"):
                ai_action_temp = deepseek_recommendation.get('action', '').upper()
                if ai_action_temp and ai_action_temp != "HOLD":
                    ai_entry = deepseek_recommendation.get('entry_price')
                    ai_targets = deepseek_recommendation.get('targets', [])
                    ai_stop_loss = deepseek_recommendation.get('stop_loss')
                    
                    # Cek apakah AI Strategy direction berbeda dengan Quant Model
                    ai_direction = "SHORT" if ai_action_temp == "SELL" else "LONG" if ai_action_temp == "BUY" else None
                    
                    # Jika direction berbeda ATAU entry/targets/stop_loss berbeda, gunakan AI Strategy setup
                    direction_differs = ai_direction and direction != ai_direction
                    entry_differs = ai_entry and entry2 and abs(ai_entry - entry2) / entry2 > 0.001  # > 0.1% difference
                    targets_differ = ai_targets and len(ai_targets) >= 2 and tp1 and abs(ai_targets[0] - tp1) / tp1 > 0.001
                    sl_differs = ai_stop_loss and stop_loss and abs(ai_stop_loss - stop_loss) / stop_loss > 0.001
                    
                    should_adjust = (direction_differs or entry_differs or targets_differ or sl_differs) and \
                                   ai_entry and ai_stop_loss and len(ai_targets) >= 2
                    
                    if should_adjust:
                        print(f"🔄 [TELEGRAM] AI Strategy ({ai_direction}) berbeda dengan Quant Model ({direction}). Menyesuaikan trading setup dengan AI Strategy...")
                        
                        # Update direction
                        direction = ai_direction
                        trading_setup['direction'] = ai_direction
                        
                        # Update entry levels: gunakan AI entry sebagai entry konservatif
                        entry1_temp = trading_setup.get('entry1')
                        entry2_temp = trading_setup.get('entry2')
                        entry3_temp = trading_setup.get('entry3')
                        
                        if current_price and current_price > 0:
                            if ai_direction == "LONG":
                                # Untuk LONG: entry agresif sedikit di bawah AI entry
                                entry1_temp = ai_entry * 0.999 if ai_entry > current_price * 0.995 else current_price * 0.998
                                entry2_temp = ai_entry  # Konservatif = AI entry
                                entry3_temp = ai_entry * 0.998  # Sangat konservatif = sedikit di bawah AI entry
                            else:  # SHORT
                                # Untuk SHORT: entry agresif sedikit di atas AI entry
                                entry1_temp = ai_entry * 1.001 if ai_entry < current_price * 1.005 else current_price * 1.002
                                entry2_temp = ai_entry  # Konservatif = AI entry
                                entry3_temp = ai_entry * 1.002  # Sangat konservatif = sedikit di atas AI entry
                        else:
                            entry1_temp = ai_entry
                            entry2_temp = ai_entry
                            entry3_temp = ai_entry
                        
                        # Update trading_setup dictionary
                        trading_setup['entry1'] = entry1_temp
                        trading_setup['entry2'] = entry2_temp
                        trading_setup['entry3'] = entry3_temp
                        trading_setup['entry'] = entry2_temp
                        trading_setup['stop_loss'] = ai_stop_loss
                        
                        # Update targets dari AI Strategy
                        if len(ai_targets) >= 3:
                            trading_setup['tp1'] = ai_targets[0]
                            trading_setup['tp2'] = ai_targets[1]
                            trading_setup['tp3'] = ai_targets[2]
                        elif len(ai_targets) >= 2:
                            trading_setup['tp1'] = ai_targets[0]
                            trading_setup['tp2'] = ai_targets[1]
                            trading_setup['tp3'] = ai_targets[1] * (0.98 if ai_direction == "SHORT" else 1.02)
                        elif len(ai_targets) >= 1:
                            trading_setup['tp1'] = ai_targets[0]
                            trading_setup['tp2'] = ai_targets[0] * (0.99 if ai_direction == "SHORT" else 1.01)
                            trading_setup['tp3'] = ai_targets[0] * (0.98 if ai_direction == "SHORT" else 1.02)
                        
                        # Recalculate risk_pct
                        if entry2_temp and ai_stop_loss and entry2_temp > 0:
                            if ai_direction == "LONG":
                                risk_pct_new = ((entry2_temp - ai_stop_loss) / entry2_temp) * 100
                            else:  # SHORT
                                risk_pct_new = ((ai_stop_loss - entry2_temp) / entry2_temp) * 100
                            trading_setup['risk_pct'] = abs(risk_pct_new)
                        
                        print(f"   ✅ Trading setup disesuaikan dengan AI Strategy: {ai_direction}")
        
        # Ambil data untuk deteksi konflik (setelah direction auto-correction)
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
        
        # Tentukan Quant Model signal berdasarkan trading_setup direction yang sudah diperbaiki
        quant_model_signal = ml_signal  # Default: gunakan ml_signal
        quant_model_position = None
        if trading_setup:
            corrected_direction = trading_setup.get('direction', 'N/A')
            if corrected_direction == "LONG":
                quant_model_signal = "BUY"
                quant_model_position = "LONG"
            elif corrected_direction == "SHORT":
                quant_model_signal = "SELL"
                quant_model_position = "SHORT"
        
        # Tampilkan konflik jika ada
        # Konflik bisa terjadi antara:
        # 1. AI Strategy vs Quant Model (trading setup yang sudah diperbaiki)
        # 2. ML Prediction vs Quant Model (jika ML prediction berbeda dengan trading setup)
        has_conflict = False
        conflict_ai_vs_quant = False
        conflict_ml_vs_quant = False
        
        # Cek konflik antara AI Strategy dan Quant Model
        if ai_action and quant_model_signal and ai_action != "HOLD" and quant_model_signal != "HOLD":
            if (ai_action == "BUY" and quant_model_signal == "SELL") or (ai_action == "SELL" and quant_model_signal == "BUY"):
                conflict_ai_vs_quant = True
                has_conflict = True
        
        # Cek konflik antara ML Prediction dan Quant Model (jika berbeda)
        if ml_signal and quant_model_signal and ml_signal != "HOLD" and quant_model_signal != "HOLD":
            if (ml_signal == "BUY" and quant_model_signal == "SELL") or (ml_signal == "SELL" and quant_model_signal == "BUY"):
                conflict_ml_vs_quant = True
                has_conflict = True
        
        if has_conflict:
            lines.append("⚠️ <b>KONFLIKT:</b>")
            
            # Tampilkan AI Strategy jika ada
            if ai_action and ai_action != "HOLD":
                ai_display = f"{ai_action}"
                if ai_position and ai_position != "CASH":
                    ai_display = f"{ai_action} ({ai_position})"
                lines.append(f"   - AI Strategy: {ai_display} ({ai_confidence}% confidence)")
            
            # Tampilkan Quant Model (trading setup yang sudah diperbaiki)
            quant_display = quant_model_signal
            if quant_model_position:
                quant_display = f"{quant_model_signal} ({quant_model_position})"
            elif quant_model_signal == "BUY":
                quant_display = f"{quant_model_signal} (LONG)"
            elif quant_model_signal == "SELL":
                quant_display = f"{quant_model_signal} (SHORT)"
            lines.append(f"   - Quant Model: {quant_display} ({ml_prob:.1f}% probability)")
            
            # Tampilkan ML Prediction jika berbeda dengan Quant Model
            if conflict_ml_vs_quant and ml_signal != quant_model_signal:
                ml_display = ml_signal
                if ml_signal == "BUY":
                    ml_display = f"{ml_signal} (LONG)"
                elif ml_signal == "SELL":
                    ml_display = f"{ml_signal} (SHORT)"
                lines.append(f"   - ML Prediction: {ml_display} ({ml_prob:.1f}% probability) - berbeda dengan Trading Setup")
                
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
        
        # Trading Setup dari Quant Model
        if trading_setup:
            direction = trading_setup.get('direction', 'N/A')
            
            # Entry levels (3 level: agresif, konservatif, sangat konservatif)
            entry1 = trading_setup.get('entry1')  # Agresif
            entry2 = trading_setup.get('entry2')  # Konservatif (recommended)
            entry3 = trading_setup.get('entry3')  # Sangat Konservatif
            
            # Stop Loss
            stop_loss = trading_setup.get('stop_loss')
            risk_pct = trading_setup.get('risk_pct', 0)
            
            # Targets (3 TP dalam satu baris)
            tp1 = trading_setup.get('tp1')
            tp2 = trading_setup.get('tp2')
            tp3 = trading_setup.get('tp3')
            
            # Direction sudah diperbaiki di awal (termasuk adjustment dengan AI Strategy), gunakan yang sudah diperbaiki
            direction = trading_setup.get('direction', 'N/A')
            action_text = "SELL" if direction == "SHORT" else "BUY" if direction == "LONG" else "HOLD"
            
            lines.append(f"💰 <b>SETUP (Quant Model):</b>")
            
            # Hanya tampilkan entry jika nilainya valid (> 0)
            if entry1 and entry1 > 0 and entry2 and entry2 > 0 and entry3 and entry3 > 0:
                lines.append(f"   Entry:")
                lines.append(f"      - {format_price_with_comma(entry1)} (agresif)")
                lines.append(f"      - {format_price_with_comma(entry2)} (konservatif)")
                lines.append(f"      - {format_price_with_comma(entry3)} (sangat konservatif)")
            elif entry1 and entry1 > 0 and entry2 and entry2 > 0:
                lines.append(f"   Entry:")
                lines.append(f"      - {format_price_with_comma(entry1)} (agresif)")
                lines.append(f"      - {format_price_with_comma(entry2)} (konservatif)")
            elif entry2 and entry2 > 0:
                lines.append(f"   Entry: {format_price_with_comma(entry2)}")
            elif entry1 and entry1 > 0:
                lines.append(f"   Entry: {format_price_with_comma(entry1)}")
            
            # Stop Loss - hitung persentase berdasarkan direction
            if stop_loss and stop_loss > 0:
                if entry2 and isinstance(entry2, (int, float)) and entry2 > 0:
                    if direction == "LONG":
                        # Untuk LONG: SL di bawah entry = loss negatif
                        sl_pct = ((stop_loss - entry2) / entry2) * 100
                    else:  # SHORT
                        # Untuk SHORT: SL di atas entry = loss positif (harga naik = loss)
                        sl_pct = ((stop_loss - entry2) / entry2) * 100
                    lines.append(f"   Stop Loss: {format_price_with_comma(stop_loss)} ({sl_pct:+.2f}%)")
                else:
                    # Fallback: gunakan risk_pct jika entry2 tidak tersedia
                    lines.append(f"   Stop Loss: {format_price_with_comma(stop_loss)} (-{risk_pct:.1f}%)")
            
            # Hanya tampilkan TP jika nilainya valid (> 0)
            # Take Profit dengan format list
            lines.append(f"   Take Profit:")
            
            if tp1 and tp1 > 0 and tp2 and tp2 > 0 and tp3 and tp3 > 0:
                # Calculate percentage untuk entry konservatif (entry2)
                if entry2 and isinstance(entry2, (int, float)) and entry2 > 0:
                    if direction == "LONG":
                        # Untuk LONG: TP lebih tinggi dari entry = profit positif
                        tp1_pct = ((tp1 - entry2) / entry2) * 100
                        tp2_pct = ((tp2 - entry2) / entry2) * 100
                        tp3_pct = ((tp3 - entry2) / entry2) * 100
                    else:  # SHORT
                        # Untuk SHORT: TP lebih rendah dari entry = profit positif
                        # Inverse calculation: (entry - tp) / entry * 100
                        tp1_pct = ((entry2 - tp1) / entry2) * 100
                        tp2_pct = ((entry2 - tp2) / entry2) * 100
                        tp3_pct = ((entry2 - tp3) / entry2) * 100
                    
                    # Format persentase dengan 2 desimal, selalu tampilkan tanda
                    lines.append(f"      - TP1: {format_price_with_comma(tp1)} ({tp1_pct:+.2f}%)")
                    lines.append(f"      - TP2: {format_price_with_comma(tp2)} ({tp2_pct:+.2f}%)")
                    lines.append(f"      - TP3: {format_price_with_comma(tp3)} ({tp3_pct:+.2f}%)")
                else:
                    lines.append(f"      - TP1: {format_price_with_comma(tp1)}")
                    lines.append(f"      - TP2: {format_price_with_comma(tp2)}")
                    lines.append(f"      - TP3: {format_price_with_comma(tp3)}")
            elif tp1 and tp1 > 0 and tp2 and tp2 > 0:
                # Fallback jika hanya ada 2 TP
                if entry2 and isinstance(entry2, (int, float)) and entry2 > 0:
                    if direction == "LONG":
                        # Untuk LONG: TP lebih tinggi dari entry = profit positif
                        tp1_pct = ((tp1 - entry2) / entry2) * 100
                        tp2_pct = ((tp2 - entry2) / entry2) * 100
                    else:  # SHORT
                        # Untuk SHORT: TP lebih rendah dari entry = profit positif
                        tp1_pct = ((entry2 - tp1) / entry2) * 100
                        tp2_pct = ((entry2 - tp2) / entry2) * 100
                    
                    lines.append(f"      - TP1: {format_price_with_comma(tp1)} ({tp1_pct:+.2f}%)")
                    lines.append(f"      - TP2: {format_price_with_comma(tp2)} ({tp2_pct:+.2f}%)")
                else:
                    lines.append(f"      - TP1: {format_price_with_comma(tp1)}")
                    lines.append(f"      - TP2: {format_price_with_comma(tp2)}")
            elif tp1 and tp1 > 0:
                # Fallback jika hanya ada 1 TP
                if entry2 and isinstance(entry2, (int, float)) and entry2 > 0:
                    if direction == "LONG":
                        tp1_pct = ((tp1 - entry2) / entry2) * 100
                    else:  # SHORT
                        tp1_pct = ((entry2 - tp1) / entry2) * 100
                    lines.append(f"      - TP1: {format_price_with_comma(tp1)} ({tp1_pct:+.2f}%)")
                else:
                    lines.append(f"      - TP1: {format_price_with_comma(tp1)}")
            
            lines.append("")
        
        # Trading Setup dari AI (DeepSeek)
        if deepseek_recommendation:
            ai_action = deepseek_recommendation.get('action', '').upper()
            ai_entry = deepseek_recommendation.get('entry_price')
            ai_stop_loss = deepseek_recommendation.get('stop_loss')
            ai_targets = deepseek_recommendation.get('targets', [])
            ai_confidence = deepseek_recommendation.get('confidence', 0)
            ai_reason = deepseek_recommendation.get('reason', '')
            
            # Hanya tampilkan jika action bukan HOLD dan ada entry/targets/stop_loss
            if ai_action and ai_action != 'HOLD' and (ai_entry or ai_targets or ai_stop_loss):
                lines.append(f"🤖 <b>SETUP (AI Strategy):</b>")
                lines.append(f"   Confidence: {ai_confidence}%")
                
                # Entry Price
                if ai_entry and isinstance(ai_entry, (int, float)) and ai_entry > 0:
                    lines.append(f"   Entry: {format_price_with_comma(ai_entry)}")
                
                # Stop Loss
                if ai_stop_loss and isinstance(ai_stop_loss, (int, float)) and ai_stop_loss > 0:
                    # Calculate stop loss percentage
                    if ai_entry and isinstance(ai_entry, (int, float)) and ai_entry > 0:
                        if ai_action == "BUY":
                            # Untuk BUY: stop loss di bawah entry
                            sl_pct = ((ai_stop_loss - ai_entry) / ai_entry) * 100
                        else:  # SELL
                            # Untuk SELL: stop loss di atas entry
                            sl_pct = ((ai_stop_loss - ai_entry) / ai_entry) * 100
                        lines.append(f"   Stop Loss: {format_price_with_comma(ai_stop_loss)} ({sl_pct:+.2f}%)")
                    else:
                        lines.append(f"   Stop Loss: {format_price_with_comma(ai_stop_loss)}")
                
                # Targets
                if ai_targets and isinstance(ai_targets, list) and len(ai_targets) > 0:
                    lines.append(f"   Take Profit:")
                    for i, target in enumerate(ai_targets, 1):
                        if isinstance(target, (int, float)) and target > 0:
                            # Calculate target percentage
                            if ai_entry and isinstance(ai_entry, (int, float)) and ai_entry > 0:
                                if ai_action == "BUY":
                                    # Untuk BUY: target di atas entry
                                    target_pct = ((target - ai_entry) / ai_entry) * 100
                                else:  # SELL
                                    # Untuk SELL: target di bawah entry
                                    target_pct = ((ai_entry - target) / ai_entry) * 100
                                lines.append(f"      - TP{i}: {format_price_with_comma(target)} ({target_pct:+.2f}%)")
                            else:
                                lines.append(f"      - TP{i}: {format_price_with_comma(target)}")
                
                # Reason (jika ada)
                if ai_reason:
                    lines.append(f"   💡 Reason: {ai_reason}")
                
                lines.append("")
        
        # Quant Metrics (ringkas dalam satu baris)
        # SELALU tambahkan Quant Metrics, bahkan jika ml_prediction adalah None
        metrics_parts = []
        
        if ml_prediction:
            print(f"🔍 [TELEGRAM DEBUG] ml_prediction received: type={type(ml_prediction)}")
            if isinstance(ml_prediction, dict):
                print(f"   Keys: {list(ml_prediction.keys())}")
                print(f"   accuracy: {ml_prediction.get('accuracy')} (type: {type(ml_prediction.get('accuracy'))})")
                print(f"   sharpe_ratio: {ml_prediction.get('sharpe_ratio')} (type: {type(ml_prediction.get('sharpe_ratio'))})")
                print(f"   expected_value: {ml_prediction.get('expected_value')} (type: {type(ml_prediction.get('expected_value'))})")
            
            # SELALU tambahkan metrics jika key ada di ml_prediction, bahkan jika nilainya 0 atau None
            # Ini memastikan Quant Metrics selalu muncul di Telegram
            accuracy = ml_prediction.get('accuracy') if isinstance(ml_prediction, dict) else None
            sharpe = ml_prediction.get('sharpe_ratio') if isinstance(ml_prediction, dict) else None
            expected_value = ml_prediction.get('expected_value') if isinstance(ml_prediction, dict) else None
            
            print(f"🔍 [TELEGRAM DEBUG] Processing metrics:")
            print(f"   accuracy: {accuracy} (type: {type(accuracy)}, is None: {accuracy is None})")
            print(f"   sharpe_ratio: {sharpe} (type: {type(sharpe)}, is None: {sharpe is None})")
            print(f"   expected_value: {expected_value} (type: {type(expected_value)}, is None: {expected_value is None})")
            
            # Process accuracy - SELALU tambahkan jika key ada (bahkan jika None, gunakan 0)
            # Jika key tidak ada, tambahkan "N/A" untuk memastikan Quant Metrics selalu muncul
            if isinstance(ml_prediction, dict) and 'accuracy' in ml_prediction:
                try:
                    if accuracy is None:
                        accuracy = 0
                    elif isinstance(accuracy, str):
                        accuracy = float(accuracy)
                    elif not isinstance(accuracy, (int, float)):
                        accuracy = float(accuracy)
                    
                    # If accuracy is less than 1, assume it's a decimal (0.85 = 85%)
                    if isinstance(accuracy, (int, float)) and 0 < accuracy < 1:
                        accuracy = accuracy * 100
                    elif accuracy is None:
                        accuracy = 0
                    
                    metrics_parts.append(f"Accuracy {accuracy:.0f}%")
                    print(f"   ✅ Accuracy added: {accuracy:.0f}%")
                except (ValueError, TypeError) as e:
                    print(f"   ⚠️  Error converting accuracy: {e}, using 0")
                    metrics_parts.append(f"Accuracy 0%")
            else:
                # Key tidak ada, tambahkan N/A untuk memastikan Quant Metrics muncul
                metrics_parts.append("Accuracy N/A")
                print(f"   ⚠️  Accuracy key tidak ditemukan, menambahkan N/A")
            
            # Process sharpe - SELALU tambahkan jika key ada (bahkan jika None, gunakan 0)
            # Jika key tidak ada, tambahkan "N/A" untuk memastikan Quant Metrics selalu muncul
            if isinstance(ml_prediction, dict) and 'sharpe_ratio' in ml_prediction:
                try:
                    if sharpe is None:
                        sharpe = 0
                    elif isinstance(sharpe, str):
                        sharpe = float(sharpe)
                    elif not isinstance(sharpe, (int, float)):
                        sharpe = float(sharpe)
                    
                    metrics_parts.append(f"Sharpe {sharpe:.2f}")
                    print(f"   ✅ Sharpe added: {sharpe:.2f}")
                except (ValueError, TypeError) as e:
                    print(f"   ⚠️  Error converting sharpe: {e}, using 0")
                    metrics_parts.append(f"Sharpe 0.00")
            else:
                # Key tidak ada, tambahkan N/A untuk memastikan Quant Metrics muncul
                metrics_parts.append("Sharpe N/A")
                print(f"   ⚠️  Sharpe ratio key tidak ditemukan, menambahkan N/A")
            
            # Process expected_value - SELALU tambahkan jika key ada (bahkan jika None, gunakan 0)
            # Jika key tidak ada, tambahkan "N/A" untuk memastikan Quant Metrics selalu muncul
            if isinstance(ml_prediction, dict) and 'expected_value' in ml_prediction:
                try:
                    if expected_value is None:
                        expected_value = 0
                    elif isinstance(expected_value, str):
                        expected_value = float(expected_value)
                    elif not isinstance(expected_value, (int, float)):
                        expected_value = float(expected_value)
                    
                    metrics_parts.append(f"Expected Value {expected_value:.2f}%")
                    print(f"   ✅ Expected Value added: {expected_value:.2f}%")
                except (ValueError, TypeError) as e:
                    print(f"   ⚠️  Error converting expected_value: {e}, using 0")
                    metrics_parts.append(f"Expected Value 0.00%")
            else:
                # Key tidak ada, tambahkan N/A untuk memastikan Quant Metrics muncul
                metrics_parts.append("Expected Value N/A")
                print(f"   ⚠️  Expected value key tidak ditemukan, menambahkan N/A")
            
        else:
            # ml_prediction is None - tambahkan placeholder untuk semua metrics
            print(f"⚠️  [TELEGRAM] ml_prediction is None atau tidak ada, menambahkan placeholder")
            metrics_parts = ["Accuracy N/A", "Sharpe N/A", "Expected Value N/A"]
        
        # Tambahkan AI Confidence dari DeepSeek jika ada
        if deepseek_recommendation and ai_confidence > 0:
            metrics_parts.append(f"AI Confidence {ai_confidence}%")
            print(f"   ✅ AI Confidence added: {ai_confidence}%")
        
        print(f"🔍 [TELEGRAM DEBUG] metrics_parts: {metrics_parts}")
        
        # SELALU tambahkan Quant Metrics (tidak peduli ml_prediction None atau tidak)
        # metrics_parts tidak akan pernah kosong karena kita selalu menambahkan setidaknya "N/A" untuk setiap metric
        if metrics_parts:
            metrics_line = f"📈 <b>Quant Metrics:</b> {', '.join(metrics_parts)}"
            lines.append(metrics_line)
            lines.append("")
            print(f"✅ [TELEGRAM] Quant Metrics akan ditambahkan: {metrics_line}")
        else:
            # Fallback: seharusnya tidak pernah terjadi karena kita selalu menambahkan metrics
            # Tapi tetap ada sebagai safety net
            print(f"⚠️  [TELEGRAM] ERROR: metrics_parts kosong!")
            metrics_line = f"📈 <b>Quant Metrics:</b> Accuracy N/A, Sharpe N/A, Expected Value N/A"
            lines.append(metrics_line)
            lines.append("")
            print(f"✅ [TELEGRAM] Quant Metrics placeholder ditambahkan (fallback): {metrics_line}")
        
        # Reversal Detection (prioritas tertinggi)
        if pullback_status and pullback_status.get('has_reversal', False):
            lines.append("🔄 <b>REVERSAL DETECTION:</b>")
            
            reversal_type = pullback_status.get('reversal_type', 'N/A')
            reversal_signal = pullback_status.get('reversal_signal', 0)
            reversal_confidence = pullback_status.get('reversal_confidence', 0) * 100
            
            # Emoji berdasarkan signal
            if reversal_signal == 1:
                signal_emoji = "🟢"
                signal_text = "BULLISH REVERSAL (LONG)"
            elif reversal_signal == -1:
                signal_emoji = "🔴"
                signal_text = "BEARISH REVERSAL (SHORT)"
            else:
                signal_emoji = "🟡"
                signal_text = "Reversal Detected"
            
            lines.append(f"   {signal_emoji} <b>{signal_text}</b>")
            lines.append(f"   Type: {reversal_type}")
            lines.append(f"   Confidence: {reversal_confidence:.1f}%")
            lines.append(f"   ⚠️  <i>WARNING: Trend berubah! Ini bukan pullback, tapi reversal sebenarnya</i>")
            lines.append("")
        
        # Breakout Detection (prioritas kedua)
        elif pullback_status and pullback_status.get('has_breakout', False):
            lines.append("🚀 <b>BREAKOUT DETECTION:</b>")
            
            breakout_type = pullback_status.get('breakout_type', 'N/A')
            breakout_signal = pullback_status.get('breakout_signal', 0)
            breakout_confidence = pullback_status.get('breakout_confidence', 0) * 100
            breakout_level = pullback_status.get('breakout_level', 0)
            
            # Emoji berdasarkan signal
            if breakout_signal == 1:
                signal_emoji = "🟢"
                signal_text = "BULLISH BREAKOUT (LONG)"
            elif breakout_signal == -1:
                signal_emoji = "🔴"
                signal_text = "BEARISH BREAKOUT (SHORT)"
            else:
                signal_emoji = "🟡"
                signal_text = "Breakout Detected"
            
            lines.append(f"   {signal_emoji} <b>{signal_text}</b>")
            lines.append(f"   Type: {breakout_type}")
            if breakout_level > 0:
                lines.append(f"   Level: {format_price_with_comma(breakout_level)}")
            lines.append(f"   Confidence: {breakout_confidence:.1f}%")
            lines.append("")
        
        # Impulse Move Detection (prioritas ketiga)
        elif pullback_status and pullback_status.get('has_impulse', False):
            lines.append("⚡ <b>IMPULSE MOVE DETECTION:</b>")
            
            impulse_type = pullback_status.get('impulse_type', 'N/A')
            impulse_signal = pullback_status.get('impulse_signal', 0)
            impulse_confidence = pullback_status.get('impulse_confidence', 0) * 100
            impulse_strength = pullback_status.get('impulse_strength', 0) * 100
            
            # Emoji berdasarkan signal
            if impulse_signal == 1:
                signal_emoji = "🟢"
                signal_text = "BULLISH IMPULSE (LONG)"
            elif impulse_signal == -1:
                signal_emoji = "🔴"
                signal_text = "BEARISH IMPULSE (SHORT)"
            else:
                signal_emoji = "🟡"
                signal_text = "Impulse Detected"
            
            lines.append(f"   {signal_emoji} <b>{signal_text}</b>")
            lines.append(f"   Type: {impulse_type}")
            lines.append(f"   Strength: {impulse_strength:.1f}%")
            lines.append(f"   Confidence: {impulse_confidence:.1f}%")
            lines.append("")
        
        # Pullback Detection (prioritas terendah)
        elif pullback_status and pullback_status.get('has_pullback', False):
            lines.append("📊 <b>PULLBACK DETECTION:</b>")
            
            pullback_type = pullback_status.get('pullback_type', 'N/A')
            pullback_depth = pullback_status.get('pullback_depth', 0) * 100
            pullback_signal = pullback_status.get('pullback_signal', 0)
            pullback_confidence = pullback_status.get('pullback_confidence', 0) * 100
            
            # Emoji berdasarkan signal
            if pullback_signal == 1:
                signal_emoji = "🟢"
                signal_text = "LONG Opportunity"
            elif pullback_signal == -1:
                signal_emoji = "🔴"
                signal_text = "SHORT Opportunity"
            else:
                signal_emoji = "🟡"
                signal_text = "No Clear Signal"
            
            lines.append(f"   {signal_emoji} <b>{signal_text}</b>")
            lines.append(f"   Type: {pullback_type} ({pullback_depth:.1f}% retracement)")
            lines.append(f"   Confidence: {pullback_confidence:.1f}%")
            
            # Entry levels dari pullback (saran tambahan)
            entry_levels = pullback_status.get('entry_levels', {})
            if entry_levels.get('pullback_entry_1'):
                lines.append(f"   💡 <i>Suggested Entry Levels:</i>")
                if entry_levels.get('pullback_entry_1'):
                    lines.append(f"      - {format_price_with_comma(entry_levels['pullback_entry_1'])} (Shallow)")
                if entry_levels.get('pullback_entry_2'):
                    lines.append(f"      - {format_price_with_comma(entry_levels['pullback_entry_2'])} (Medium)")
                if entry_levels.get('pullback_entry_3'):
                    lines.append(f"      - {format_price_with_comma(entry_levels['pullback_entry_3'])} (Deep)")
            
            lines.append("")
        
        # Recent Trades Analysis (Market Aggression & Momentum)
        if recent_trades_analysis:
            aggression = recent_trades_analysis.get('market_aggression', 0)
            buyer_dominance = recent_trades_analysis.get('buyer_dominance', 50)
            momentum = recent_trades_analysis.get('momentum', 0)
            trade_count = recent_trades_analysis.get('trade_count', 0)
            
            # Determine aggression level
            if aggression >= 70:
                aggression_emoji = "🔥"
                aggression_text = "Sangat Tinggi"
            elif aggression >= 50:
                aggression_emoji = "⚡"
                aggression_text = "Tinggi"
            elif aggression >= 30:
                aggression_emoji = "📊"
                aggression_text = "Sedang"
            else:
                aggression_emoji = "😴"
                aggression_text = "Rendah"
            
            # Determine buyer/seller dominance
            if buyer_dominance >= 60:
                dominance_emoji = "🟢"
                dominance_text = f"Buyer {buyer_dominance:.1f}%"
            elif buyer_dominance <= 40:
                dominance_emoji = "🔴"
                dominance_text = f"Seller {100 - buyer_dominance:.1f}%"
            else:
                dominance_emoji = "🟡"
                dominance_text = "Seimbang"
            
            # Determine momentum direction
            if momentum > 0.1:
                momentum_emoji = "📈"
                momentum_text = f"+{momentum:.2f}%"
            elif momentum < -0.1:
                momentum_emoji = "📉"
                momentum_text = f"{momentum:.2f}%"
            else:
                momentum_emoji = "➡️"
                momentum_text = f"{momentum:+.2f}%"
            
            lines.append("🔥 <b>Market Activity (Recent Trades):</b>")
            lines.append(f"   {aggression_emoji} Aggression: {aggression_text} ({aggression:.1f}/100)")
            lines.append(f"   {dominance_emoji} Dominance: {dominance_text}")
            lines.append(f"   {momentum_emoji} Momentum: {momentum_text}")
            lines.append(f"   📊 Trades: {trade_count} recent")
            lines.append("")
        
        return "\n".join(lines)

