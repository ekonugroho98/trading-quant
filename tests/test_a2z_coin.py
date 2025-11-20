"""
Unit test khusus untuk coin A2Z dengan data real dari Telegram
Mensimulasikan alur lengkap ketika user mengirim "A2Z" ke Telegram bot
"""

import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.integration.telegram_bot import TelegramBot


class TestA2ZCoinFromTelegram(unittest.TestCase):
    """Test case khusus untuk coin A2Z - mensimulasikan input dari Telegram"""
    
    def setUp(self):
        """Setup test fixtures"""
        self.bot = TelegramBot(bot_token="test_token", chat_id="test_chat_id")
    
    def test_a2z_from_telegram_input(self):
        """
        Test: Mensimulasikan ketika user mengirim "A2Z" ke Telegram bot
        Data sesuai dengan output yang user berikan
        """
        # Data yang sesuai dengan output Telegram yang user berikan
        # Entry agresif: 0.00358616 (bukan 0.00358516)
        # TP1: 0.00357899 (bukan 0.00357799)
        # TP2: 0.00356823 (bukan 0.00356723)
        trading_setup = {
            'direction': 'LONG',  # Akan diperbaiki ke SHORT oleh auto-correction
            'entry1': 0.00358616,  # Entry agresif
            'entry2': 0.00398361,  # Entry konservatif
            'entry3': 0.00399558,  # Entry sangat konservatif
            'stop_loss': 0.00406328,  # SL di atas entry (SHORT)
            'risk_pct': 2.0,
            'tp1': 0.00357899,  # TP di bawah entry (SHORT)
            'tp2': 0.00356823,  # TP di bawah entry (SHORT)
            'tp3': 0.00354589   # TP di bawah entry (SHORT)
        }
        
        deepseek_recommendation = {
            'action': 'SELL',
            'position': 'SHORT',
            'confidence': 72,
            'entry_price': 0.00398361,
            'stop_loss': 0.00406328,
            'targets': [0.00357899, 0.00356823, 0.00354589],
            'reason': 'Strong bearish confluence: Trading setup SHORT, RSI overbought (79.76), seller dominance 65%, price at resistance (0.29% distance), higher TF trend down'
        }
        
        ml_prediction = {
            'signal': 'BELI',  # ML prediction BUY (LONG) - akan konflik dengan AI Strategy
            'buy_probability': 66.0,
            'accuracy': 49,
            'sharpe_ratio': 0.79,
            'expected_value': 0.09
        }
        
        recent_trades_analysis = {
            'market_aggression': 50.1,
            'buyer_dominance': 14.7,  # Seller dominance = 100 - 14.7 = 85.3%
            'momentum': -0.06,
            'trade_count': 100
        }
        
        # Simulasi: User mengirim "A2Z" ke Telegram bot
        # Bot akan memanggil format_simplified_trading_signal dengan data ini
        result = self.bot.format_simplified_trading_signal(
            symbol="A2Z-USD",
            timeframe="15m",
            current_price=0.003976,
            support=0.003732,
            resistance=0.0039876,
            trading_setup=trading_setup,
            deepseek_recommendation=deepseek_recommendation,
            ml_prediction=ml_prediction,
            recent_trades_analysis=recent_trades_analysis
        )
        
        # ============================================
        # VERIFIKASI 1: ML Prediction Priority
        # ============================================
        # Dengan logika baru: Quant Model mengikuti ML Prediction (LONG)
        self.assertEqual(trading_setup['direction'], 'LONG',
                        "❌ Direction harus mengikuti ML Prediction: LONG")
        print("✅ Direction mengikuti ML Prediction: LONG")
        
        # ============================================
        # VERIFIKASI 2: Perhitungan Persentase TP (LONG)
        # ============================================
        # TP1: (tp1 - entry2) / entry2 * 100 (untuk LONG, TP di atas entry)
        entry2 = trading_setup['entry2']
        tp1 = trading_setup['tp1']
        expected_tp1_pct = ((tp1 - entry2) / entry2) * 100
        self.assertIn(f"+{expected_tp1_pct:.2f}%", result,
                     f"❌ TP1 harus menunjukkan +{expected_tp1_pct:.2f}% untuk LONG")
        print(f"✅ TP1 persentase: +{expected_tp1_pct:.2f}%")
        
        # TP2: (tp2 - entry2) / entry2 * 100
        tp2 = trading_setup['tp2']
        expected_tp2_pct = ((tp2 - entry2) / entry2) * 100
        self.assertIn(f"+{expected_tp2_pct:.2f}%", result,
                     f"❌ TP2 harus menunjukkan +{expected_tp2_pct:.2f}% untuk LONG")
        print(f"✅ TP2 persentase: +{expected_tp2_pct:.2f}%")
        
        # TP3: (tp3 - entry2) / entry2 * 100
        tp3 = trading_setup['tp3']
        expected_tp3_pct = ((tp3 - entry2) / entry2) * 100
        self.assertIn(f"+{expected_tp3_pct:.2f}%", result,
                     f"❌ TP3 harus menunjukkan +{expected_tp3_pct:.2f}% untuk LONG")
        print(f"✅ TP3 persentase: +{expected_tp3_pct:.2f}%")
        
        # ============================================
        # VERIFIKASI 3: Perhitungan Persentase SL (LONG)
        # ============================================
        # SL: (entry2 - stop_loss) / entry2 * 100 (untuk LONG, SL di bawah entry)
        stop_loss = trading_setup['stop_loss']
        expected_sl_pct = ((entry2 - stop_loss) / entry2) * 100
        self.assertIn(f"-{expected_sl_pct:.2f}%", result,
                     f"❌ SL harus menunjukkan -{expected_sl_pct:.2f}% untuk LONG")
        print(f"✅ SL persentase: -{expected_sl_pct:.2f}%")
        
        # ============================================
        # VERIFIKASI 4: Entry Levels (LONG - di support)
        # ============================================
        # Entry levels sudah di-recalculate berdasarkan ML Prediction (LONG)
        # Entry harus di support atau di bawah current price untuk LONG
        entry1 = trading_setup['entry1']
        entry2 = trading_setup['entry2']
        entry3 = trading_setup['entry3']
        # Format dengan 8 desimal untuk matching
        self.assertIn(f"{entry1:.8f}", result, "❌ Entry agresif harus ditampilkan")
        self.assertIn(f"{entry2:.8f}", result, "❌ Entry konservatif harus ditampilkan")
        self.assertIn(f"{entry3:.8f}", result, "❌ Entry sangat konservatif harus ditampilkan")
        print("✅ Entry levels ditampilkan dengan benar (LONG setup)")
        
        # ============================================
        # VERIFIKASI 5: Rekomendasi Final
        # ============================================
        self.assertIn("SELL (SHORT)", result,
                     "❌ Rekomendasi final harus SELL (SHORT) berdasarkan AI Strategy")
        print("✅ Rekomendasi final: SELL (SHORT)")
        
        # ============================================
        # VERIFIKASI 6: Konflik Detection & ML Prediction Priority
        # ============================================
        # Dengan logika baru: Quant Model mengikuti ML Prediction (LONG)
        # Konflik terjadi antara:
        # - AI Strategy (SELL/SHORT) vs Quant Model (BUY/LONG - mengikuti ML Prediction)
        # - ML Prediction (BUY/LONG) = Quant Model (BUY/LONG) - TIDAK ada konflik
        self.assertIn("KONFLIKT", result,
                     "❌ Harus menampilkan konflik")
        self.assertIn("AI Strategy: SELL (SHORT)", result,
                     "❌ AI Strategy harus ditampilkan")
        # Quant Model sekarang menunjukkan LONG (mengikuti ML Prediction)
        self.assertIn("Quant Model: BUY (LONG)", result,
                     "❌ Quant Model harus menunjukkan LONG (mengikuti ML Prediction)")
        print("✅ Konflik terdeteksi: AI Strategy (SHORT) vs Quant Model (LONG - mengikuti ML Prediction)")
        
        # Verifikasi: Trading setup sudah disesuaikan dengan ML Prediction (LONG)
        # Entry harus di support (untuk LONG), TP di atas entry, SL di bawah entry
        self.assertEqual(trading_setup['direction'], 'LONG',
                         "❌ Direction harus LONG (mengikuti ML Prediction)")
        self.assertGreater(trading_setup['tp1'], trading_setup['entry2'],
                         "❌ TP1 harus di atas entry untuk LONG")
        self.assertLess(trading_setup['stop_loss'], trading_setup['entry2'],
                         "❌ Stop loss harus di bawah entry untuk LONG")
        print("✅ Trading setup sudah disesuaikan dengan ML Prediction (LONG)")
        
        # ============================================
        # VERIFIKASI 7: Quant Metrics
        # ============================================
        self.assertIn("Quant Metrics", result,
                     "❌ Quant Metrics harus ditampilkan")
        self.assertIn("Accuracy 49%", result,
                     "❌ Accuracy harus ditampilkan")
        self.assertIn("Sharpe 0.79", result,
                     "❌ Sharpe ratio harus ditampilkan")
        self.assertIn("Expected Value 0.09%", result,
                     "❌ Expected Value harus ditampilkan")
        self.assertIn("AI Confidence 72%", result,
                     "❌ AI Confidence harus ditampilkan")
        print("✅ Quant Metrics ditampilkan dengan benar")
        
        # ============================================
        # VERIFIKASI 8: Market Activity
        # ============================================
        self.assertIn("Market Activity", result,
                     "❌ Market Activity harus ditampilkan")
        print("✅ Market Activity ditampilkan")
        
        # ============================================
        # PRINT RESULT UNTUK DEBUGGING
        # ============================================
        print("\n" + "="*80)
        print("📱 SIMULASI: User mengirim 'A2Z' ke Telegram Bot")
        print("="*80)
        print(result)
        print("="*80)
        print(f"\n📊 SUMMARY:")
        print(f"   Direction: {trading_setup['direction']} (auto-corrected dari LONG)")
        print(f"   TP1: +{expected_tp1_pct:.2f}%")
        print(f"   TP2: +{expected_tp2_pct:.2f}%")
        print(f"   TP3: +{expected_tp3_pct:.2f}%")
        print(f"   SL: +{expected_sl_pct:.2f}%")
        print("="*80)


if __name__ == '__main__':
    unittest.main()

