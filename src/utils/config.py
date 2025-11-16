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
import os

# Determine project root directory (2 levels up from this file: src/utils/config.py -> project root)
_config_file_path = os.path.abspath(__file__)
_config_dir = os.path.dirname(_config_file_path)
_project_root = os.path.dirname(os.path.dirname(_config_dir))  # Go up 2 levels: utils -> src -> root
_env_path = os.path.join(_project_root, '.env')

try:
    from dotenv import load_dotenv
    # Load .env file from project root
    if os.path.exists(_env_path):
        load_dotenv(_env_path)
    else:
        # Fallback: try to find .env in current directory or parent directories
        load_dotenv()
except ImportError:
    # Jika python-dotenv tidak terinstall, gunakan os.environ langsung
    print("⚠️  python-dotenv tidak terinstall. Install dengan: pip install python-dotenv")
    print("   Atau set environment variables secara manual")
except Exception as e:
    print(f"⚠️  Error loading .env file: {e}")
    print(f"   Mencari .env di: {_env_path}")
    print("   Menggunakan environment variables atau nilai default")

# ============================================
# KONFIGURASI STRATEGI TRADING
# ============================================
# Pilih jenis trading yang ingin digunakan:
# - "SCALPING": Trading sangat cepat (detik-menit), banyak sinyal, profit kecil per trade
# - "DAY_TRADING": Trading dalam 1 hari, beberapa sinyal per hari
# - "INTRADAY_TRADING": Trading intraday dengan timeframe 2 jam, beberapa sinyal per hari
# - "SWING_TRADING": Trading beberapa hari-minggu, sinyal lebih jarang tapi lebih reliable
# - "POSITION_TRADING": Trading jangka panjang (minggu-bulan), sinyal sangat jarang

TRADING_STYLE = "SWING_TRADING"  # Pilihan: "SCALPING", "DAY_TRADING", "INTRADAY_TRADING", "SWING_TRADING", "POSITION_TRADING"

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
SYMBOL = "BTC-USD"  # Untuk yfinance: BTC-USD, ETH-USD, XRP-USD, DOGE-USD, SOL-USD, ADA-USD, ENA-USD, dll

# ============================================
# KONFIGURASI BINANCE API TYPE
# ============================================
# Pilih jenis Binance API yang ingin digunakan:
# - "spot": Binance Spot API (default) - untuk trading spot
# - "futures": Binance USDⓈ-M Futures API - untuk trading futures
# 
# Catatan:
# - Spot API: https://api.binance.com (untuk trading spot)
# - Futures API: https://fapi.binance.com (untuk trading futures/derivatives)
# - Keduanya menggunakan API key yang sama, tapi endpoint berbeda
# - Data format sama (OHLC candles), tapi futures memiliki leverage dan funding rate
BINANCE_API_TYPE = os.getenv("BINANCE_API_TYPE", "spot")  # Pilihan: "spot", "futures"
# Load dari .env: BINANCE_API_TYPE=futures atau BINANCE_API_TYPE=spot
# Daftar coin populer: BTC-USD, ETH-USD, XRP-USD, DOGE-USD, BNB-USD, ADA-USD, SOL-USD, DOT-USD, LINK-USD
# Lihat YFINANCE_COINS.md untuk daftar lengkap coin yang didukung
# DAYS_BACK akan otomatis disesuaikan berdasarkan TRADING_STYLE
# Bisa di-override manual jika perlu
DAYS_BACK = None  # Auto berdasarkan TRADING_STYLE (365 hari)

# Mapping DAYS_BACK berdasarkan TRADING_STYLE
TRADING_STYLE_DAYS_BACK = {
    "SCALPING": 7,           # 7 hari untuk scalping
    "DAY_TRADING": 30,       # 30 hari untuk day trading
    "INTRADAY_TRADING": 60,  # 60 hari untuk intraday trading (2h timeframe)
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
    "SCALPING": "5m",        # 5 menit untuk scalping
    "DAY_TRADING": "15m",    # 15 menit untuk day trading
    "INTRADAY_TRADING": "2h", # 2 jam untuk intraday trading
    "SWING_TRADING": "4h",   # 4 jam untuk swing trading
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
# - INTRADAY_TRADING: risk_percent = 1.5-2.0%, tp_multiplier sedang (1.5x, 2.5x, 3.5x)
# - SWING_TRADING: risk_percent = 2.0-3.0%, tp_multiplier besar (2.0x, 3.0x, 5.0x)
# - POSITION_TRADING: risk_percent = 3.0-5.0%, tp_multiplier sangat besar (3.0x, 5.0x, 8.0x)

SETUP_RISK_PERCENT = None  # None = auto berdasarkan TRADING_STYLE, atau set manual (e.g., 1.0)
SETUP_TP_MULTIPLIERS = None  # None = auto berdasarkan TRADING_STYLE, atau set manual [1.5, 2.5, 3.5]

# ============================================
# KONFIGURASI MACHINE LEARNING MODEL
# ============================================
# Pilihan metode prediksi:
# - "linear": Linear Regression saja
# - "random_forest": Random Forest saja
# - "moving_avg": Moving Average + Momentum saja
# - "ensemble": Gabungkan beberapa model (fleksibel, lihat ML_MODELS_CONFIG di bawah)

PREDICTION_METHOD = "ensemble"  # Pilihan: "linear", "random_forest", "moving_avg", "ensemble"

# Konfigurasi untuk ensemble (jika PREDICTION_METHOD = "ensemble")
# Format: List of dict dengan keys: "model", "weight", "enabled"
# - "model": Nama model ("linear", "random_forest", "moving_avg")
# - "weight": Bobot model dalam ensemble (0.0 - 1.0), total harus <= 1.0
# - "enabled": True/False untuk enable/disable model tertentu

ML_MODELS_CONFIG = [
    {
        "model": "random_forest",
        "weight": 0.5,  # 50% weight untuk Random Forest
        "enabled": True
    },
    {
        "model": "linear",
        "weight": 0.3,  # 30% weight untuk Linear Regression
        "enabled": True
    },
    {
        "model": "moving_avg",
        "weight": 0.2,  # 20% weight untuk Moving Average
        "enabled": True
    }
]

# Mode prediksi:
# - True: Classification (prediksi Beli/Jual dengan probabilitas)
# - False: Regression (prediksi harga)
USE_CLASSIFICATION = True  # True = prediksi Beli/Jual, False = prediksi harga

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
# KONFIGURASI QUANTITATIVE ANALYSIS
# ============================================
# Risk Metrics
ENABLE_RISK_METRICS = True  # VaR, CVaR, Expected Shortfall
RISK_CONFIDENCE_LEVELS = [0.90, 0.95, 0.99]  # Confidence levels untuk risk metrics

# Enhanced Backtesting
ENABLE_ENHANCED_BACKTESTING = True  # Monte Carlo simulation + Transaction costs
COMMISSION_PCT = 0.001  # Commission 0.1%
SLIPPAGE_PCT = 0.0005  # Slippage 0.05%
MONTE_CARLO_SIMULATIONS = 1000  # Number of Monte Carlo simulations

# Time Series Models
ENABLE_TIME_SERIES_MODELS = True  # ARIMA + GARCH
ARIMA_MAX_ORDER = (2, 1, 2)  # Maximum ARIMA order (p, d, q)
GARCH_ORDER = (1, 1)  # GARCH order (p, q)

# ============================================
# KONFIGURASI ADVANCED TRADING STRATEGIES
# ============================================
# Pairs Trading
ENABLE_PAIRS_TRADING = True  # Aktifkan pairs trading strategy
PAIRS_ENTRY_THRESHOLD = 2.0  # Z-score threshold untuk entry
PAIRS_EXIT_THRESHOLD = 0.5   # Z-score threshold untuk exit
PAIRS_STOP_LOSS_PCT = 3.0    # Stop loss percentage
PAIRS_LONG_ONLY = True       # True = long-only (spot trading), False = long-short (futures)

# Statistical Arbitrage
ENABLE_STATISTICAL_ARBITRAGE = True  # Aktifkan statistical arbitrage
STAT_ARB_ENTRY_THRESHOLD = 2.0  # Z-score threshold untuk entry
STAT_ARB_EXIT_THRESHOLD = 0.5    # Z-score threshold untuk exit
STAT_ARB_MIN_CORRELATION = 0.7   # Minimum correlation untuk inclusion
STAT_ARB_LONG_ONLY = True        # True = long-only (spot trading), False = long-short (futures)

# Grid Trading
ENABLE_GRID_TRADING = True  # Aktifkan grid trading strategy
GRID_LEVELS = 10  # Number of grid levels
GRID_SPACING_PCT = 1.0  # Spacing between grid levels (percentage)

# Dollar Cost Averaging (DCA)
ENABLE_DCA = True  # Aktifkan DCA strategy
DCA_INVESTMENT_AMOUNT = 100.0  # Amount to invest per period
DCA_FREQUENCY = 7  # Investment frequency (every N periods)

# Multi-Strategy Portfolio
ENABLE_MULTI_STRATEGY_PORTFOLIO = True  # Aktifkan multi-strategy portfolio
PORTFOLIO_SELECTION_METHOD = "composite"  # 'sharpe', 'return', 'win_rate', 'composite'
PORTFOLIO_WEIGHTING_METHOD = "sharpe"  # 'equal', 'sharpe', 'inverse_vol', 'performance'
PORTFOLIO_TOP_N = 3  # Number of top strategies to include
PORTFOLIO_PERFORMANCE_WINDOW = 30  # Window untuk performance calculation

# ============================================
# KONFIGURASI DERIVATIVES MODELING
# ============================================
ENABLE_DERIVATIVES_MODELING = True  # Aktifkan derivatives modeling (opsional)
# Catatan: Derivatives modeling hanya diperlukan jika expand ke options/futures trading

# Black-Scholes Parameters
RISK_FREE_RATE = 0.05  # Risk-free rate (5% annual)
DEFAULT_VOLATILITY = 0.30  # Default volatility (30% annual)

# Options Strategies
ENABLE_OPTIONS_STRATEGIES = False  # Aktifkan options strategies
OPTIONS_CONTRACTS = 1  # Number of contracts (each = 100 shares)

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

