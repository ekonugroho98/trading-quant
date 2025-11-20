"""
Unit tests untuk validasi direction dan perhitungan persentase di Telegram Bot
"""

import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.integration.telegram_bot import TelegramBot


class TestTelegramBotDirection(unittest.TestCase):
    """Test cases untuk validasi direction dan perhitungan persentase"""
    
    def setUp(self):
        """Setup test fixtures"""
        # Mock bot token dan chat_id untuk testing
        self.bot = TelegramBot(bot_token="test_token", chat_id="test_chat_id")
    
    def test_direction_auto_correction_long_to_short(self):
        """Test: Auto-correction direction dari LONG ke SHORT ketika TP < entry dan SL > entry"""
        # Kasus A2Z: direction LONG tapi data menunjukkan SHORT
        trading_setup = {
            'direction': 'LONG',  # Salah, seharusnya SHORT
            'entry1': 0.00358516,
            'entry2': 0.00398361,  # Entry konservatif
            'entry3': 0.00399558,
            'stop_loss': 0.00406328,  # SL di atas entry (SHORT)
            'risk_pct': 2.0,
            'tp1': 0.00357799,  # TP di bawah entry (SHORT)
            'tp2': 0.00356723,
            'tp3': 0.00354589
        }
        
        result = self.bot.format_simplified_trading_signal(
            symbol="A2Z-USD",
            timeframe="15m",
            current_price=0.003976,
            support=0.003732,
            resistance=0.0039876,
            trading_setup=trading_setup
        )
        
        # Verifikasi: direction harus diperbaiki ke SHORT
        self.assertEqual(trading_setup['direction'], 'SHORT', 
                        "Direction harus diperbaiki dari LONG ke SHORT")
        
        # Verifikasi: TP persentase harus positif untuk SHORT
        # TP1: (entry2 - tp1) / entry2 * 100 = (0.00398361 - 0.00357799) / 0.00398361 * 100
        expected_tp1_pct = ((0.00398361 - 0.00357799) / 0.00398361) * 100
        self.assertIn(f"+{expected_tp1_pct:.2f}%", result, 
                     "TP1 persentase harus positif untuk SHORT")
        
        # Verifikasi: SL persentase harus positif untuk SHORT
        # SL: (stop_loss - entry2) / entry2 * 100 = (0.00406328 - 0.00398361) / 0.00398361 * 100
        expected_sl_pct = ((0.00406328 - 0.00398361) / 0.00398361) * 100
        self.assertIn(f"+{expected_sl_pct:.2f}%", result,
                     "SL persentase harus positif untuk SHORT")
    
    def test_direction_auto_correction_short_to_long(self):
        """Test: Auto-correction direction dari SHORT ke LONG ketika TP > entry dan SL < entry"""
        trading_setup = {
            'direction': 'SHORT',  # Salah, seharusnya LONG
            'entry1': 0.0035,
            'entry2': 0.0036,  # Entry konservatif
            'entry3': 0.0037,
            'stop_loss': 0.0035,  # SL di bawah entry (LONG)
            'risk_pct': 2.0,
            'tp1': 0.0038,  # TP di atas entry (LONG)
            'tp2': 0.0039,
            'tp3': 0.0040
        }
        
        result = self.bot.format_simplified_trading_signal(
            symbol="TEST-USD",
            timeframe="15m",
            current_price=0.00365,
            support=0.0035,
            resistance=0.0040,
            trading_setup=trading_setup
        )
        
        # Verifikasi: direction harus diperbaiki ke LONG
        self.assertEqual(trading_setup['direction'], 'LONG',
                        "Direction harus diperbaiki dari SHORT ke LONG")
        
        # Verifikasi: TP persentase harus positif untuk LONG
        expected_tp1_pct = ((0.0038 - 0.0036) / 0.0036) * 100
        self.assertIn(f"+{expected_tp1_pct:.2f}%", result,
                     "TP1 persentase harus positif untuk LONG")
        
        # Verifikasi: SL persentase harus negatif untuk LONG
        expected_sl_pct = ((0.0035 - 0.0036) / 0.0036) * 100
        self.assertIn(f"{expected_sl_pct:.2f}%", result,
                     "SL persentase harus negatif untuk LONG")
    
    def test_direction_correct_long(self):
        """Test: Direction LONG yang sudah benar tidak perlu diperbaiki"""
        trading_setup = {
            'direction': 'LONG',  # Benar
            'entry1': 0.0035,
            'entry2': 0.0036,
            'entry3': 0.0037,
            'stop_loss': 0.0035,  # SL di bawah entry (LONG)
            'risk_pct': 2.0,
            'tp1': 0.0038,  # TP di atas entry (LONG)
            'tp2': 0.0039,
            'tp3': 0.0040
        }
        
        result = self.bot.format_simplified_trading_signal(
            symbol="TEST-USD",
            timeframe="15m",
            current_price=0.00365,
            trading_setup=trading_setup
        )
        
        # Verifikasi: direction tetap LONG
        self.assertEqual(trading_setup['direction'], 'LONG',
                        "Direction harus tetap LONG")
    
    def test_direction_correct_short(self):
        """Test: Direction SHORT yang sudah benar tidak perlu diperbaiki"""
        trading_setup = {
            'direction': 'SHORT',  # Benar
            'entry1': 0.0040,
            'entry2': 0.0039,  # Entry konservatif
            'entry3': 0.0038,
            'stop_loss': 0.0040,  # SL di atas entry (SHORT)
            'risk_pct': 2.0,
            'tp1': 0.0037,  # TP di bawah entry (SHORT)
            'tp2': 0.0036,
            'tp3': 0.0035
        }
        
        result = self.bot.format_simplified_trading_signal(
            symbol="TEST-USD",
            timeframe="15m",
            current_price=0.00385,
            trading_setup=trading_setup
        )
        
        # Verifikasi: direction tetap SHORT
        self.assertEqual(trading_setup['direction'], 'SHORT',
                        "Direction harus tetap SHORT")
    
    def test_tp_percentage_calculation_long(self):
        """Test: Perhitungan persentase TP untuk LONG"""
        trading_setup = {
            'direction': 'LONG',
            'entry1': 0.0035,
            'entry2': 0.0036,  # Entry konservatif
            'entry3': 0.0037,
            'stop_loss': 0.0035,
            'risk_pct': 2.0,
            'tp1': 0.0038,  # TP di atas entry
            'tp2': 0.0039,
            'tp3': 0.0040
        }
        
        result = self.bot.format_simplified_trading_signal(
            symbol="TEST-USD",
            timeframe="15m",
            trading_setup=trading_setup
        )
        
        # Verifikasi: TP1 persentase = (tp1 - entry2) / entry2 * 100
        expected_tp1_pct = ((0.0038 - 0.0036) / 0.0036) * 100
        self.assertIn(f"+{expected_tp1_pct:.2f}%", result,
                     f"TP1 harus menunjukkan +{expected_tp1_pct:.2f}%")
    
    def test_tp_percentage_calculation_short(self):
        """Test: Perhitungan persentase TP untuk SHORT"""
        trading_setup = {
            'direction': 'SHORT',
            'entry1': 0.0040,
            'entry2': 0.0039,  # Entry konservatif
            'entry3': 0.0038,
            'stop_loss': 0.0040,
            'risk_pct': 2.0,
            'tp1': 0.0037,  # TP di bawah entry
            'tp2': 0.0036,
            'tp3': 0.0035
        }
        
        result = self.bot.format_simplified_trading_signal(
            symbol="TEST-USD",
            timeframe="15m",
            trading_setup=trading_setup
        )
        
        # Verifikasi: TP1 persentase = (entry2 - tp1) / entry2 * 100
        expected_tp1_pct = ((0.0039 - 0.0037) / 0.0039) * 100
        self.assertIn(f"+{expected_tp1_pct:.2f}%", result,
                     f"TP1 harus menunjukkan +{expected_tp1_pct:.2f}%")
    
    def test_sl_percentage_calculation_long(self):
        """Test: Perhitungan persentase SL untuk LONG"""
        trading_setup = {
            'direction': 'LONG',
            'entry1': 0.0035,
            'entry2': 0.0036,  # Entry konservatif
            'entry3': 0.0037,
            'stop_loss': 0.0035,  # SL di bawah entry
            'risk_pct': 2.0,
            'tp1': 0.0038,
            'tp2': 0.0039,
            'tp3': 0.0040
        }
        
        result = self.bot.format_simplified_trading_signal(
            symbol="TEST-USD",
            timeframe="15m",
            trading_setup=trading_setup
        )
        
        # Verifikasi: SL persentase = (stop_loss - entry2) / entry2 * 100 (negatif untuk LONG)
        expected_sl_pct = ((0.0035 - 0.0036) / 0.0036) * 100
        self.assertIn(f"{expected_sl_pct:.2f}%", result,
                     f"SL harus menunjukkan {expected_sl_pct:.2f}% (negatif)")
    
    def test_sl_percentage_calculation_short(self):
        """Test: Perhitungan persentase SL untuk SHORT"""
        trading_setup = {
            'direction': 'SHORT',
            'entry1': 0.0040,
            'entry2': 0.0039,  # Entry konservatif
            'entry3': 0.0038,
            'stop_loss': 0.0040,  # SL di atas entry
            'risk_pct': 2.0,
            'tp1': 0.0037,
            'tp2': 0.0036,
            'tp3': 0.0035
        }
        
        result = self.bot.format_simplified_trading_signal(
            symbol="TEST-USD",
            timeframe="15m",
            trading_setup=trading_setup
        )
        
        # Verifikasi: SL persentase = (stop_loss - entry2) / entry2 * 100 (positif untuk SHORT)
        expected_sl_pct = ((0.0040 - 0.0039) / 0.0039) * 100
        self.assertIn(f"+{expected_sl_pct:.2f}%", result,
                     f"SL harus menunjukkan +{expected_sl_pct:.2f}% (positif)")


if __name__ == '__main__':
    unittest.main()

