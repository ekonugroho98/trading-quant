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
            ma_signal = coin['ma_signal']
            score = coin['combined_score']
            
            # Emoji berdasarkan signal
            signal_emoji = "🟢" if ma_signal == "BUY" else "🔴" if ma_signal == "SELL" else "🟡"
            change_emoji = "📈" if change_7d > 0 else "📉"
            
            lines.append(f"<b>{i}. {symbol}</b>")
            lines.append(f"💵 Price: ${format_price_no_rounding(price)}")
            lines.append(f"{change_emoji} Change: 1d: {change_1d:+.2f}% | 7d: {change_7d:+.2f}%")
            lines.append(f"📊 Volume: {volume_ratio:.2f}x")
            lines.append(f"📈 RSI: {rsi:.2f} ({rsi_signal})")
            lines.append(f"{signal_emoji} Signal: {ma_signal}")
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

