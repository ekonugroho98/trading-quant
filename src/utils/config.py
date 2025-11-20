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

TRADING_STYLE = "DAY_TRADING"  # Pilihan: "SCALPING", "DAY_TRADING", "INTRADAY_TRADING", "SWING_TRADING", "POSITION_TRADING"

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
SYMBOL = "1000000BOB-USD"  # Untuk yfinance: BTC-USD, ETH-USD, XRP-USD, DOGE-USD, SOL-USD, ADA-USD, ENA-USD, dll

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
DAYS_BACK = None  # Auto berdasarkan TRADING_STYLE (60 hari)

# ============================================
# AUTO-CONFIGURATION BERDASARKAN BINANCE_API_TYPE
# ============================================
# Auto-enable derivatives modeling dan set strategies untuk Futures
# Jika BINANCE_API_TYPE = "futures", sistem akan otomatis:
# 1. Enable derivatives modeling (untuk options/futures analysis)
# 2. Set pairs trading dan statistical arbitrage ke long-short mode
# 
# Catatan: Auto-config akan dijalankan di akhir file setelah semua konfigurasi didefinisikan
# Jika ingin manual override, set nilai setelah section AUTO-CONFIGURATION EXECUTION

# Mapping DAYS_BACK berdasarkan TRADING_STYLE
# OPTIMIZED untuk akurasi maksimal (menggunakan maksimal data yang tersedia)
# 
# Catatan:
# - Untuk yfinance: Akan auto-adjust jika melebihi limit berdasarkan interval
# - Untuk Binance API: Sangat fleksibel, bisa request data tahun-tahun sebelumnya!
#   - Limit per request: 1500 klines
#   - Dengan pagination: Bisa dapat data berapa tahun pun (otomatis di get_futures_data)
#   - Rate limit: 2400 requests/minute (dengan API key)
#   - TIDAK ADA LIMIT WAKTU: Bisa ambil data sejak coin listing
# 
# Rekomendasi untuk akurasi maksimal:
# - Untuk interval kecil (1m, 5m, 15m): 60-180 hari sudah cukup (banyak data)
# - Untuk interval sedang (1h, 2h, 4h): 365-730 hari optimal (1-2 tahun)
# - Untuk interval besar (1d): 365-1095 hari optimal (1-3 tahun, bisa lebih)
TRADING_STYLE_DAYS_BACK = {
    "SCALPING": 7,           # 7 hari untuk scalping (cukup untuk 5m, 1m terbatas)
    "DAY_TRADING": 60,       # 60 hari untuk day trading (optimal untuk 15m, meningkatkan akurasi)
    "INTRADAY_TRADING": 180, # 180 hari untuk intraday trading (2h timeframe, optimal balance)
    "SWING_TRADING": 365,    # 365 hari untuk swing trading (4h timeframe, optimal untuk pattern jangka panjang)
    "POSITION_TRADING": 730  # 730 hari (2 tahun) untuk position trading (1d timeframe, lebih banyak data = lebih akurat)
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
FREECRYPTOAPI_SYMBOL = "XAN-USD"  # Symbol untuk FreeCryptoAPI (default: BTC)

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
TRADING_SYMBOL = "XAN-USD"  # Symbol untuk trading setup (contoh: BTCUSDT, XRPUSDT, DOGEUSDT, ENAUSDT, MAGICUSDT, dll)

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
    },
    # Optional: Uncomment untuk enable XGBoost dan LSTM
    {
        "model": "xgboost",
        "weight": 0.3,
        "enabled": True
    },
    {
        "model": "lstm",
        "weight": 0.2,
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

# ============================================
# CONSTANTS (Magic Numbers)
# ============================================
# Constants untuk digunakan di seluruh codebase, bukan hardcoded values

# Z-Score thresholds
ZSCORE_ENTRY_THRESHOLD = 2.0  # Default entry threshold untuk mean reversion
ZSCORE_EXIT_THRESHOLD = 0.5   # Default exit threshold untuk mean reversion

# RSI thresholds
RSI_OVERSOLD = 30.0  # RSI oversold level
RSI_OVERBOUGHT = 70.0  # RSI overbought level

# Volume thresholds
VOLUME_SPIKE_THRESHOLD = 2.0  # Volume spike detection threshold (2x average)
MIN_VOLUME_RATIO = 0.8  # Minimum volume ratio untuk signal validation

# Correlation thresholds
MIN_CORRELATION = 0.7  # Minimum correlation untuk pairs trading/arbitrage

# Confidence levels
DEFAULT_CONFIDENCE_LEVEL = 0.95  # Default confidence level untuk risk metrics
MIN_SIGNAL_CONFIDENCE = 0.5  # Minimum confidence untuk signal filtering

# Grid spacing
DEFAULT_GRID_SPACING_PCT = 1.0  # Default grid spacing percentage

# IQR multiplier untuk outlier detection
IQR_MULTIPLIER = 1.5  # IQR multiplier untuk outlier detection

# Z-score threshold untuk outlier detection
OUTLIER_ZSCORE_THRESHOLD = 3.0  # Z-score threshold untuk outlier detection

# Time Series Models
ENABLE_TIME_SERIES_MODELS = True  # ARIMA + GARCH
ARIMA_MAX_ORDER = (2, 1, 2)  # Maximum ARIMA order (p, d, q)
GARCH_ORDER = (1, 1)  # GARCH order (p, q)

# ============================================
# KONFIGURASI LSTM/GRU MODELS
# ============================================
# Konfigurasi untuk LSTM/GRU neural networks
# Catatan: LSTM/GRU memerlukan data cukup banyak (minimal 100+ data points)
# dan training lebih lama dibanding model lain

# Enable LSTM/GRU models
ENABLE_LSTM = True  # True = enable LSTM, False = disable (akan lebih cepat)

# LSTM/GRU Parameters
LSTM_SEQUENCE_LENGTH = 60  # Length of input sequences (60 periods = melihat 60 data points sebelumnya)
LSTM_UNITS = 50  # Number of LSTM/GRU units (lebih banyak = lebih kompleks, tapi lebih lambat)
LSTM_DROPOUT_RATE = 0.2  # Dropout rate untuk prevent overfitting (0.0 - 1.0)
LSTM_EPOCHS = 50  # Number of training epochs (lebih banyak = lebih lama training)
LSTM_BATCH_SIZE = 32  # Batch size untuk training (32, 64, 128, dll)
LSTM_USE_GRU = False  # True = gunakan GRU, False = gunakan LSTM (GRU lebih cepat, LSTM lebih powerful)

# Catatan:
# - sequence_length: 60 = melihat 60 periods sebelumnya untuk prediksi
#   - Untuk data 15m: 60 periods = 15 jam
#   - Untuk data 1h: 60 periods = 60 jam (2.5 hari)
#   - Untuk data 1d: 60 periods = 60 hari
# - lstm_units: 50 = 50 neurons per layer (bisa 25, 50, 100, 200)
#   - Lebih banyak = lebih powerful tapi lebih lambat
# - dropout_rate: 0.2 = 20% neurons di-dropout untuk prevent overfitting
#   - 0.0 = no dropout, 0.5 = 50% dropout
# - epochs: 50 = train 50 kali (bisa 20, 50, 100, 200)
#   - Early stopping akan stop jika tidak improve
# - batch_size: 32 = process 32 samples sekaligus
#   - 16, 32, 64, 128 (lebih besar = lebih cepat tapi butuh lebih banyak memory)
# - use_gru: False = LSTM, True = GRU
#   - GRU lebih cepat tapi biasanya LSTM lebih akurat untuk time series

# ============================================
# KONFIGURASI ADVANCED TRADING STRATEGIES
# ============================================
# Pairs Trading
ENABLE_PAIRS_TRADING = True  # Aktifkan pairs trading strategy
PAIRS_ENTRY_THRESHOLD = 2.0  # Z-score threshold untuk entry
PAIRS_EXIT_THRESHOLD = 0.5   # Z-score threshold untuk exit
PAIRS_STOP_LOSS_PCT = 3.0    # Stop loss percentage
# PAIRS_LONG_ONLY akan di-set otomatis berdasarkan BINANCE_API_TYPE
# True = long-only (spot trading), False = long-short (futures)
# Default: True (untuk spot), akan auto-set ke False jika BINANCE_API_TYPE = "futures"
PAIRS_LONG_ONLY = True

# Statistical Arbitrage
ENABLE_STATISTICAL_ARBITRAGE = True  # Aktifkan statistical arbitrage
STAT_ARB_ENTRY_THRESHOLD = 2.0  # Z-score threshold untuk entry
STAT_ARB_EXIT_THRESHOLD = 0.5    # Z-score threshold untuk exit
STAT_ARB_MIN_CORRELATION = 0.7   # Minimum correlation untuk inclusion
# STAT_ARB_LONG_ONLY akan di-set otomatis berdasarkan BINANCE_API_TYPE
# True = long-only (spot trading), False = long-short (futures)
# Default: True (untuk spot), akan auto-set ke False jika BINANCE_API_TYPE = "futures"
STAT_ARB_LONG_ONLY = True

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
# ENABLE_DERIVATIVES_MODELING akan di-set otomatis berdasarkan BINANCE_API_TYPE
# Default: True (untuk futures), akan auto-enable jika BINANCE_API_TYPE = "futures"
# Catatan: Derivatives modeling berguna untuk options/futures trading analysis
ENABLE_DERIVATIVES_MODELING = True

# Black-Scholes Parameters
RISK_FREE_RATE = 0.05  # Risk-free rate (5% annual)
DEFAULT_VOLATILITY = 0.30  # Default volatility (30% annual)

# Options Strategies
# ENABLE_OPTIONS_STRATEGIES akan di-set otomatis berdasarkan BINANCE_API_TYPE
# Default: True (untuk futures), akan auto-enable jika BINANCE_API_TYPE = "futures"
ENABLE_OPTIONS_STRATEGIES = True
OPTIONS_CONTRACTS = 1  # Number of contracts (each = 100 shares)

# ============================================
# AUTO-CONFIGURATION EXECUTION
# ============================================
# Auto-configure berdasarkan BINANCE_API_TYPE
# Eksekusi setelah semua konfigurasi didefinisikan
# 
# Catatan: Jika ingin manual override auto-config, set nilai setelah section ini
# Contoh: ENABLE_DERIVATIVES_MODELING = False  # Override auto-config

if BINANCE_API_TYPE and BINANCE_API_TYPE.lower() == "futures":
    # Auto-enable derivatives modeling untuk futures
    ENABLE_DERIVATIVES_MODELING = True
    ENABLE_OPTIONS_STRATEGIES = True
    
    # Auto-set strategies ke long-short mode untuk futures
    PAIRS_LONG_ONLY = False
    STAT_ARB_LONG_ONLY = False
    
    print("🔵 [AUTO-CONFIG] Binance Futures detected - Auto-configuring:")
    print("   ✅ Derivatives modeling: ENABLED")
    print("   ✅ Options strategies: ENABLED")
    print("   ✅ Pairs trading: Long-Short mode")
    print("   ✅ Statistical arbitrage: Long-Short mode")
    print("✅ [AUTO-CONFIG] Konfigurasi Futures selesai")
elif BINANCE_API_TYPE and BINANCE_API_TYPE.lower() == "spot":
    # Spot trading: default long-only (sudah di-set di atas)
    # Derivatives modeling tetap bisa di-enable manual jika diperlukan
    print("🟢 [AUTO-CONFIG] Binance Spot detected - Long-only mode aktif")
    print("   ℹ️  Derivatives modeling: Manual (set ENABLE_DERIVATIVES_MODELING untuk enable)")
    print("   ✅ Pairs trading: Long-only mode")
    print("   ✅ Statistical arbitrage: Long-only mode")

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

# ============================================
# KONFIGURASI MULTI-THREADING
# ============================================
# Konfigurasi untuk parallel processing analisis coin
ANALYSIS_THREAD_POOL_SIZE = int(os.getenv("ANALYSIS_THREAD_POOL_SIZE", "1"))  # Default: 1 thread
# Batch size untuk processing (berapa coin diproses bersamaan)
ANALYSIS_BATCH_SIZE = int(os.getenv("ANALYSIS_BATCH_SIZE", "1"))  # Default: 1 coin per batch

# ============================================
# KONFIGURASI TIMEOUT
# ============================================
# Timeout untuk subprocess calls (dalam detik)
ANALYSIS_TIMEOUT = int(os.getenv("ANALYSIS_TIMEOUT", "600"))  # Default: 10 menit (600 detik)
# Timeout untuk get_historical_data.py
HISTORICAL_DATA_TIMEOUT = int(os.getenv("HISTORICAL_DATA_TIMEOUT", "180"))  # Default: 3 menit (180 detik)
# Timeout untuk prediksi_next_day.py
PREDICTION_TIMEOUT = int(os.getenv("PREDICTION_TIMEOUT", "180"))  # Default: 3 menit (180 detik)
# Timeout untuk AI DeepSeek call
AI_TIMEOUT = int(os.getenv("AI_TIMEOUT", "300"))  # Default: 5 menit (300 detik)

