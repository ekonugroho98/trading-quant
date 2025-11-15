# ============================================
# KONFIGURASI TERPUSAT UNTUK QUANT TRADING
# ============================================
# Semua script akan membaca konfigurasi dari file ini
# Ubah sekali, berlaku untuk semua script
#
# CREDENTIAL PRIBADI: Pindah ke file .env
# - DEEPSEEK_API_KEY
# - TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
# - BINANCE_API_KEY, BINANCE_API_SECRET
# - COINGECKO_API_KEY (optional)
# - FREECRYPTOAPI_KEY (optional)

# Load environment variables dari .env file
try:
    from dotenv import load_dotenv
    import os
    load_dotenv()  # Load .env file
except ImportError:
    # Jika python-dotenv tidak terinstall, gunakan os.environ langsung
    import os
    print("⚠️  python-dotenv tidak terinstall. Install dengan: pip install python-dotenv")
    print("   Atau set environment variables secara manual")
except Exception as e:
    import os
    print(f"⚠️  Error loading .env file: {e}")
    print("   Menggunakan environment variables atau nilai default")

# ============================================
# KONFIGURASI STRATEGI TRADING
# ============================================
# Pilih jenis trading yang ingin digunakan:
# - "SCALPING": Trading sangat cepat (detik-menit), banyak sinyal, profit kecil per trade
# - "DAY_TRADING": Trading dalam 1 hari, beberapa sinyal per hari
# - "SWING_TRADING": Trading beberapa hari-minggu, sinyal lebih jarang tapi lebih reliable
# - "POSITION_TRADING": Trading jangka panjang (minggu-bulan), sinyal sangat jarang

TRADING_STYLE = "SCALPING"  # Pilihan: "SCALPING", "DAY_TRADING", "SWING_TRADING", "POSITION_TRADING"

# ============================================
# KONFIGURASI DATA
# ============================================
# ============================================
USE_CSV_DATA = True  # True = gunakan data dari get_data.py, False = gunakan yfinance
CSV_FILE = None  # None = ambil file CSV terbaru, atau spesifik nama file
FILTER_YEAR = 2025  # Filter data hanya tahun tertentu (None = tidak filter)

# ============================================
# KONFIGURASI DATA HISTORICAL
# ============================================
DATA_SOURCE = "binance"  # Pilihan: "yfinance", "binance", "coingecko", "indodax", "freecryptoapi"
SYMBOL = "RSR-USD"  # Untuk yfinance: BTC-USD, ETH-USD, XRP-USD, DOGE-USD, SOL-USD, ADA-USD, ENA-USD, dll
# Daftar coin populer: BTC-USD, ETH-USD, XRP-USD, DOGE-USD, BNB-USD, ADA-USD, SOL-USD, DOT-USD, LINK-USD
# Lihat YFINANCE_COINS.md untuk daftar lengkap coin yang didukung
# DAYS_BACK akan otomatis disesuaikan berdasarkan TRADING_STYLE
# Bisa di-override manual jika perlu
DAYS_BACK = None  # Auto berdasarkan TRADING_STYLE (7 hari)

# Mapping DAYS_BACK berdasarkan TRADING_STYLE
TRADING_STYLE_DAYS_BACK = {
    "SCALPING": 7,           # 7 hari untuk scalping
    "DAY_TRADING": 30,       # 30 hari untuk day trading
    "SWING_TRADING": 365,    # 365 hari untuk swing trading
    "POSITION_TRADING": 365  # 365 hari untuk position trading
}

def get_days_back():
    """Mendapatkan DAYS_BACK berdasarkan TRADING_STYLE atau manual override"""
    if DAYS_BACK is not None:
        return DAYS_BACK
    return TRADING_STYLE_DAYS_BACK.get(TRADING_STYLE, 30)

# Catatan: yfinance memiliki limit berdasarkan interval:
# - Interval 1m: maksimal 7 hari (auto-adjust jika lebih)
# - Interval 5m, 15m, 30m: maksimal 60 hari (auto-adjust jika lebih)
# - Interval 1h: maksimal 730 hari (auto-adjust jika lebih)
# - Interval 1d: tidak ada limit

# Coin ID untuk CoinGecko (jika menggunakan DATA_SOURCE = "coingecko")
# Mapping coin ID CoinGecko (cari di https://www.coingecko.com):
# - BTC: "bitcoin"
# - XRP: "ripple"
# - DOGE: "dogecoin"
# - ENA: "ethena"
# - MAGIC: "magic"
# - HYPE: "hype-token" atau "hyperliquid" (cek di coingecko.com)
# - ASTER: "aster" (cek di coingecko.com jika tidak ditemukan)
# - XPL: "xpl" (cek di coingecko.com jika tidak ditemukan)
# 
# Untuk yfinance, gunakan format SYMBOL: XRP-USD, DOGE-USD, dll
# Untuk CoinGecko, gunakan COIN_ID: ripple, dogecoin, dll
COIN_ID = "bitcoin"  # Coin ID untuk CoinGecko (untuk yfinance, gunakan SYMBOL di atas)

# API Key untuk CoinGecko (opsional - hanya jika diperlukan)
# Dapatkan API key gratis di: https://www.coingecko.com/en/api
# Load dari .env file atau environment variable
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", None)  # Load dari .env, None = gunakan free API

# API Key untuk FreeCryptoAPI (jika menggunakan DATA_SOURCE = "freecryptoapi")
# Dapatkan API key gratis di: https://freecryptoapi.com/
# FreeCryptoAPI menyediakan data historis OHLC harian
# Load dari .env file atau environment variable
FREECRYPTOAPI_KEY = os.getenv("FREECRYPTOAPI_KEY", None)  # Load dari .env

# Symbol untuk FreeCryptoAPI (format berbeda dari yfinance)
# Format: "BTC", "ETH", "XRP", "DOGE", "BNB", "ADA", "SOL", dll (tanpa "-USD")
# Cek daftar lengkap di: https://freecryptoapi.com/api/v1/getCryptoList
# Atau gunakan endpoint: GET https://freecryptoapi.com/api/v1/getCryptoList?api_key=YOUR_KEY
FREECRYPTOAPI_SYMBOL = "BTC-USD"  # Symbol untuk FreeCryptoAPI (default: BTC)

# Interval akan otomatis disesuaikan berdasarkan TRADING_STYLE
# Tapi bisa di-override manual jika perlu
# Untuk time frame 4H, set: INTERVAL = "4h"
INTERVAL = None  # None = auto berdasarkan TRADING_STYLE, atau set manual (e.g., "1m", "15m", "1h", "4h", "1d")

# Mapping interval berdasarkan TRADING_STYLE
TRADING_STYLE_INTERVALS = {
    "SCALPING": "5m",        # 1 menit untuk scalping
    "DAY_TRADING": "15m",    # 15 menit untuk day trading
    "SWING_TRADING": "4h",   # 1 jam untuk swing trading (atau bisa "4h" untuk swing lebih pendek)
    "POSITION_TRADING": "1d" # 1 hari untuk position trading
}

# Catatan: Untuk time frame 4H (4 jam), bisa digunakan dengan:
# 1. Set manual: INTERVAL = "4h" (akan override otomatis)
# 2. Atau gunakan SWING_TRADING dan set INTERVAL = "4h" manual
# 3. 4H cocok untuk swing trading jangka pendek (beberapa hari)

def get_interval():
    """Mendapatkan interval berdasarkan TRADING_STYLE atau manual override"""
    if INTERVAL is not None:
        return INTERVAL
    return TRADING_STYLE_INTERVALS.get(TRADING_STYLE, "15m")

# ============================================
# KONFIGURASI TRADING SETUP
# ============================================
TRADING_SYMBOL = "BTC-USD"  # Symbol untuk trading setup (contoh: BTCUSDT, XRPUSDT, DOGEUSDT, ENAUSDT, MAGICUSDT, dll)

# Konfigurasi Risk & Reward untuk Trading Setup
# Sesuaikan berdasarkan TRADING_STYLE:
# - SCALPING: risk_percent = 0.5-1.0%, tp_multiplier lebih kecil (1.2x, 1.5x, 2.0x)
# - DAY_TRADING: risk_percent = 1.5-2.5%, tp_multiplier sedang (1.5x, 2.5x, 3.5x)
# - SWING_TRADING: risk_percent = 2.0-3.0%, tp_multiplier besar (2.0x, 3.0x, 5.0x)
# - POSITION_TRADING: risk_percent = 3.0-5.0%, tp_multiplier sangat besar (3.0x, 5.0x, 8.0x)

SETUP_RISK_PERCENT = None  # None = auto berdasarkan TRADING_STYLE, atau set manual (e.g., 1.0)
SETUP_TP_MULTIPLIERS = None  # None = auto berdasarkan TRADING_STYLE, atau set manual [1.5, 2.5, 3.5]

# ============================================
# KONFIGURASI LAINNYA
# ============================================
RUN_PREDICTION = True  # True = jalankan prediksi_next_day.py setelah analisis selesai

# ============================================
# KONFIGURASI ENHANCED FEATURES
# ============================================
# Aktifkan fitur-fitur advanced untuk validasi lebih akurat
ENABLE_VOLUME_ANALYSIS = True  # Volume analysis (VWAP, volume patterns, spikes)
ENABLE_MARKET_CONTEXT = True  # Market context (regime, volatility, higher TF)
ENABLE_ADVANCED_FEATURES = True  # Advanced features (mean-reversion, cycles, patterns)
ENABLE_ENHANCED_METRICS = True  # Enhanced validation metrics (drawdown, win rate, etc.)

# Konfigurasi untuk correlation analysis
CORRELATION_SYMBOLS = ["ETH-USD", "BNB-USD"]  # Symbols untuk korelasi (opsional)

# ============================================
# KONFIGURASI DEEPSEEK AI INTEGRATION
# ============================================
ENABLE_DEEPSEEK_AI = True  # Aktifkan integrasi DeepSeek AI
# API key dari .env file atau environment variable
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", None)  # Load dari .env
DEEPSEEK_MODEL = "deepseek-chat"  # Model yang digunakan (default: deepseek-chat)
# Model tersedia: deepseek-chat (default), deepseek-chat-v3.2, deepseek-v3.2
# Untuk menggunakan DeepSeek-V3.2, ubah ke: "deepseek-chat-v3.2" atau "deepseek-v3.2"

# ============================================
# KONFIGURASI TELEGRAM BOT INTEGRATION
# ============================================
ENABLE_TELEGRAM_BOT = True  # Aktifkan integrasi Telegram Bot
# Credential dari .env file atau environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", None)  # Load dari .env
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", None)  # Load dari .env

# ============================================
# KONFIGURASI BINANCE API INTEGRATION
# ============================================
ENABLE_BINANCE_API = True  # Aktifkan integrasi Binance API
# Credential dari .env file atau environment variables
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", None)  # Load dari .env
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", None)  # Load dari .env
# Catatan: Credential disimpan di file .env (tidak di-commit ke repository)
# Testnet: https://testnet.binance.vision (untuk testing tanpa risiko)

