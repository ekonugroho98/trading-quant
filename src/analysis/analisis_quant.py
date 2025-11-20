import os
import sys

# Add project root to Python path to enable src imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
import glob
from datetime import datetime, timedelta

# Global variable untuk menyimpan nama file CSV yang digunakan
used_csv_file = None

# Fungsi helper untuk format harga (menangani harga kecil dan besar)
def format_price(price):
    """Format harga dengan presisi yang sesuai"""
    if price == 0 or price is None:
        return "0"
    elif price < 0.01:
        # Harga sangat kecil (< 0.01), gunakan lebih banyak desimal
        return f"{price:.6f}"
    elif price < 1:
        # Harga kecil (< 1), gunakan 4 desimal
        return f"{price:.4f}"
    elif price < 1000:
        # Harga sedang, gunakan 2 desimal
        return f"{price:,.2f}"
    else:
        # Harga besar, gunakan 0 desimal dengan separator
        return f"{price:,.0f}"

# Import untuk Support/Resistance calculation
try:
    from scipy.signal import argrelextrema
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

# Import konfigurasi terpusat
# Force reload config untuk memastikan menggunakan nilai terbaru
try:
    import importlib
    import src.utils.config as config
    # Reload config module untuk memastikan menggunakan nilai terbaru dari file
    importlib.reload(config)
    from src.utils.config import (
        TRADING_STYLE, USE_CSV_DATA, CSV_FILE, FILTER_YEAR,
        TRADING_SYMBOL, SETUP_RISK_PERCENT, SETUP_TP_MULTIPLIERS,
        RUN_PREDICTION, SYMBOL, DATA_SOURCE
    )
    # Debug: Print RUN_PREDICTION value immediately after loading
    print(f"\n🔍 [CONFIG DEBUG] RUN_PREDICTION = {RUN_PREDICTION} (type: {type(RUN_PREDICTION)})")
    print(f"🔍 [CONFIG DEBUG] SYMBOL = {SYMBOL}")
    print(f"🔍 [CONFIG DEBUG] DATA_SOURCE = {DATA_SOURCE}")
    # Konversi SYMBOL (format: COIN-USD) ke format trading symbol (COINUSDT)
    # Auto-generate TRADING_SYMBOL dari SYMBOL jika SYMBOL tersedia
    # User bisa override dengan set TRADING_SYMBOL manual di config.py
    if SYMBOL:
        # Extract coin name dari SYMBOL (format: COIN-USD -> COIN)
        coin_name = SYMBOL.replace("-USD", "").replace("-", "").upper()
        # Auto-generate dari SYMBOL (selalu update untuk match dengan coin yang dipilih)
        generated_symbol = f"{coin_name}USDT"
        if TRADING_SYMBOL != generated_symbol:
            TRADING_SYMBOL = generated_symbol
            print(f"📌 Trading symbol: {TRADING_SYMBOL} (auto-generated dari SYMBOL: {SYMBOL})")
except ImportError:
    # Fallback jika config.py tidak ada
    print("⚠️  config.py tidak ditemukan, menggunakan konfigurasi default")
    TRADING_STYLE = "DAY_TRADING"
    USE_CSV_DATA = True
    CSV_FILE = None
    FILTER_YEAR = 2025
    TRADING_SYMBOL = "BTCUSDT"
    SETUP_RISK_PERCENT = None
    SETUP_TP_MULTIPLIERS = None
    RUN_PREDICTION = True
    SYMBOL = "BTC-USD"
    DATA_SOURCE = "yfinance"
except Exception as e:
    # Jika reload gagal, coba import normal
    print(f"⚠️  Warning: Gagal reload config, menggunakan import normal: {e}")
    try:
        from src.utils.config import (
            TRADING_STYLE, USE_CSV_DATA, CSV_FILE, FILTER_YEAR,
            TRADING_SYMBOL, SETUP_RISK_PERCENT, SETUP_TP_MULTIPLIERS,
            RUN_PREDICTION, SYMBOL, DATA_SOURCE
        )
    except ImportError:
        print("⚠️  config.py tidak ditemukan, menggunakan konfigurasi default")
        TRADING_STYLE = "DAY_TRADING"
        USE_CSV_DATA = True
        CSV_FILE = None
        FILTER_YEAR = 2025
        TRADING_SYMBOL = "BTCUSDT"
        SETUP_RISK_PERCENT = None
        SETUP_TP_MULTIPLIERS = None
        RUN_PREDICTION = True
        SYMBOL = "BTC-USD"
        DATA_SOURCE = "yfinance"

def load_data_from_csv(csv_file=None):
    """Load data dari CSV yang dihasilkan get_data.py atau get_historical_data.py"""
    global used_csv_file  # Global variable untuk menyimpan nama file yang digunakan
    
    if csv_file is None:
        # Cari file CSV yang sesuai dengan SYMBOL yang diminta
        # Prioritaskan file yang sesuai dengan symbol, baru kemudian file terbaru
        csv_files = []
        
        # Jika SYMBOL tersedia, cari file yang sesuai dengan symbol tersebut
        if SYMBOL:
            # Convert SYMBOL ke format filename (DOGE-USD -> doge atau dogeusd)
            symbol_lower = SYMBOL.replace("-", "").lower()  # DOGE-USD -> dogeusd
            symbol_base = SYMBOL.split("-")[0].lower()  # DOGE-USD -> doge
            
            # Pattern untuk file yang sesuai dengan symbol
            symbol_patterns = [
                f"{symbol_lower}_historical_*.csv",  # dogeusd_historical_*.csv
                f"{symbol_base}_historical_*.csv",  # doge_historical_*.csv
                f"{symbol_lower}*.csv",  # dogeusd*.csv
                f"{symbol_base}*.csv",  # doge*.csv
            ]
            
            for pattern in symbol_patterns:
                csv_files.extend(glob.glob(pattern))
        
        # Jika tidak ada file yang sesuai dengan symbol, cari file historical terbaru
        if not csv_files:
            csv_files.extend(glob.glob("*_historical_*.csv"))
        
        # Fallback: cari file dengan pattern umum
        if not csv_files:
            csv_files.extend(glob.glob("*_*.csv"))
        
        if not csv_files:
            raise FileNotFoundError("Tidak ada file CSV ditemukan. Jalankan get_data.py atau get_historical_data.py terlebih dahulu.")
        
        # Pilih file yang sesuai dengan symbol jika ada, jika tidak gunakan yang terbaru
        if SYMBOL:
            symbol_lower = SYMBOL.replace("-", "").lower()
            symbol_base = SYMBOL.split("-")[0].lower()
            # Prioritaskan file yang mengandung symbol
            matching_files = [f for f in csv_files if symbol_lower in f.lower() or symbol_base in f.lower()]
            if matching_files:
                csv_file = max(matching_files, key=os.path.getctime)
                print(f"✅ Menggunakan file CSV yang sesuai dengan symbol {SYMBOL}: {csv_file}")
            else:
                csv_file = max(csv_files, key=os.path.getctime)
                print(f"⚠️  Tidak ada file CSV untuk {SYMBOL}, menggunakan file terbaru: {csv_file}")
                print(f"   ⚠️  PERINGATAN: File ini mungkin berisi data untuk coin lain!")
        else:
            csv_file = max(csv_files, key=os.path.getctime)
            print(f"Menggunakan file: {csv_file}")
    
    # Simpan nama file untuk dihapus nanti
    used_csv_file = csv_file
    
    # Baca CSV
    df = pd.read_csv(csv_file)
    print(f"File CSV: {len(df)} baris raw data")
    
    # Deteksi format CSV (historical vs real-time)
    # Historical: sudah punya kolom Open, High, Low, Close
    # Real-time: punya kolom price, amount, date (dari get_data.py)
    
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        
        if 'Close' in df.columns:
            # Format historical (sudah OHLCV)
            print("Format: Historical data (OHLCV)")
            df_resampled = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
        elif 'price' in df.columns:
            # Format real-time (tick data)
            print("Format: Real-time tick data")
            # Resample data tick menjadi data per menit
            df_resampled = pd.DataFrame()
            df_resampled['Open'] = df['price'].resample('1min').first()
            df_resampled['High'] = df['price'].resample('1min').max()
            df_resampled['Low'] = df['price'].resample('1min').min()
            df_resampled['Close'] = df['price'].resample('1min').last()
            
            # Jika ada kolom amount, gunakan sebagai volume
            if 'amount' in df.columns:
                df_resampled['Volume'] = df['amount'].resample('1min').sum()
            else:
                df_resampled['Volume'] = 0
        else:
            raise ValueError("Format CSV tidak dikenali. Pastikan ada kolom 'Close' atau 'price'")
    else:
        raise ValueError("Kolom 'date' tidak ditemukan di CSV")
    
    df_resampled = df_resampled.dropna()
    
    # Validasi: pastikan data tidak terlalu lama (maksimal 30 hari)
    if len(df_resampled) > 0:
        data_start = df_resampled.index.min()
        data_end = df_resampled.index.max()
        days_span = (data_end - data_start).days
        
        print(f"Periode data CSV: {data_start} sampai {data_end}")
        print(f"Rentang waktu: {days_span} hari")
        
        # Filter berdasarkan tahun jika FILTER_YEAR diatur
        if FILTER_YEAR is not None:
            before_filter = len(df_resampled)
            df_resampled = df_resampled[df_resampled.index.year == FILTER_YEAR]
            after_filter = len(df_resampled)
            if before_filter != after_filter:
                print(f"⚠️  Filter tahun {FILTER_YEAR}: {before_filter} -> {after_filter} records")
        
        # Validasi: jika data lebih dari 30 hari, peringatkan
        if days_span > 30:
            print(f"⚠️  PERINGATAN: Data mencakup {days_span} hari (lebih dari 30 hari)")
            print(f"   Pastikan ini adalah data yang diinginkan!")
    
    return df_resampled

def load_data_from_binance():
    """Load data dari Binance API (Spot atau Futures berdasarkan BINANCE_API_TYPE)"""
    try:
        # Gunakan helper yang otomatis memilih Spot atau Futures berdasarkan config
        from src.data.binance_api_helper import get_binance_data
        from src.utils.config import BINANCE_API_KEY, BINANCE_API_SECRET, get_days_back, get_interval, BINANCE_API_TYPE
        
        print("Mengambil data dari Binance API...")
        days_back = get_days_back()
        interval = get_interval()
        
        # Gunakan SYMBOL dari config, fallback ke BTC-USD jika tidak ada
        symbol_to_download = SYMBOL if SYMBOL else "BTC-USD"
        
        # Tampilkan info API type yang digunakan
        api_type = BINANCE_API_TYPE.lower() if BINANCE_API_TYPE else "spot"
        print(f"📡 Menggunakan Binance {api_type.upper()} API")
        print(f"Symbol: {symbol_to_download}")
        print(f"Periode: {days_back} hari terakhir")
        print(f"Interval: {interval}")
        
        # get_binance_data() otomatis memilih Spot atau Futures berdasarkan BINANCE_API_TYPE
        data = get_binance_data(
            symbol_to_download,
            days_back,
            interval,
            BINANCE_API_KEY,
            BINANCE_API_SECRET
        )
        
        if data is None or data.empty:
            print("⚠️  Data kosong dari Binance API")
            return None
        
        # Set date sebagai index (seperti yfinance)
        if 'date' in data.columns:
            data['date'] = pd.to_datetime(data['date'])
            data.set_index('date', inplace=True)
        
        # Filter tahun jika diperlukan
        if FILTER_YEAR is not None and not data.empty:
            data = data[data.index.year == FILTER_YEAR]
            print(f"Data setelah filter tahun {FILTER_YEAR}: {len(data)} records")
        
        return data
        
    except ImportError as e:
        print(f"⚠️  Binance data module tidak tersedia: {e}")
        return None
    except Exception as e:
        print(f"⚠️  Error mengambil data dari Binance: {e}")
        import traceback
        traceback.print_exc()
        return None

def load_data_from_yfinance():
    """Load data dari yfinance (fallback)"""
    print("Mengambil data dari yfinance...")
    # Gunakan tanggal yang valid (hari ini atau kemarin untuk memastikan ada data)
    end_date = datetime.now() - timedelta(days=1)  # Kemarin untuk memastikan data tersedia
    
    # Gunakan FILTER_YEAR jika diatur, atau tahun saat ini
    target_year = FILTER_YEAR if FILTER_YEAR is not None else datetime.now().year
    start_date = datetime(target_year, 1, 1)  # Mulai dari 1 Januari tahun target
    
    # Pastikan start_date tidak lebih dari end_date
    if start_date > end_date:
        # Jika tahun target belum ada data, gunakan tahun sebelumnya
        start_date = datetime(target_year - 1, 1, 1)
        target_year = target_year - 1
    
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    print(f"Periode: {start_str} sampai {end_str} (Target tahun: {target_year})")
    # Gunakan SYMBOL dari config, fallback ke BTC-USD jika tidak ada
    symbol_to_download = SYMBOL if SYMBOL else "BTC-USD"
    print(f"Mengunduh data untuk: {symbol_to_download}")
    
    try:
        # Explicitly set auto_adjust=False to suppress FutureWarning
        data = yf.download(symbol_to_download, start=start_str, end=end_str, progress=False, auto_adjust=False)
        
        # Check if data is empty or None
        if data is None or data.empty:
            print(f"⚠️  Tidak ada data untuk {symbol_to_download} pada periode {start_str} sampai {end_str}")
            print(f"   Symbol mungkin tidak valid atau tidak memiliki data di yfinance")
            return None
        
        # Filter tambahan: pastikan hanya data tahun target
        if not data.empty and FILTER_YEAR is not None:
            data = data[data.index.year == FILTER_YEAR]
            print(f"Data setelah filter tahun {FILTER_YEAR}: {len(data)} records")
        
        return data
    
    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        print(f"❌ Error mengambil data dari yfinance: {error_type}: {error_msg}")
        
        # Check for specific yfinance errors
        if "YFPricesMissingError" in error_type or "no price data found" in error_msg.lower() or "possibly delisted" in error_msg.lower():
            print(f"💡 Symbol '{symbol_to_download}' mungkin tidak valid, delisted, atau tidak memiliki data di yfinance")
            print(f"   Coba gunakan symbol lain seperti: BTC-USD, ETH-USD, XRP-USD, dll")
        elif "not found" in error_msg.lower() or "no data" in error_msg.lower():
            print(f"💡 Symbol '{symbol_to_download}' tidak ditemukan di yfinance")
        elif "timeout" in error_msg.lower():
            print(f"💡 Request timeout - coba lagi nanti")
        elif "rate limit" in error_msg.lower():
            print(f"💡 Rate limit tercapai - tunggu beberapa saat")
        
        return None

# 1️⃣ Ambil data historis
data = None
if USE_CSV_DATA:
    try:
        data = load_data_from_csv(CSV_FILE)
        print(f"\n✅ Data CSV dimuat: {len(data)} records")
        print(f"   Periode: {data.index.min()} sampai {data.index.max()}")
        
        # Validasi: pastikan data tidak kosong
        if len(data) == 0:
            raise ValueError("Data CSV kosong setelah processing")
            
    except FileNotFoundError as e:
        # Jika file CSV tidak ditemukan, coba ambil data otomatis
        print(f"\n⚠️  File CSV tidak ditemukan: {e}")
        print("🔄 Mencoba mengambil data historical otomatis...")
        
        try:
            # Jalankan get_historical_data.py untuk mengambil data
            import subprocess
            result = subprocess.run(
                [sys.executable, "get_historical_data.py"],
                capture_output=True,
                text=True,
                timeout=120  # 2 menit timeout
            )
            
            if result.returncode == 0:
                print("✅ Data historical berhasil diambil")
                # Coba load lagi
                try:
                    data = load_data_from_csv(CSV_FILE)
                    print(f"\n✅ Data CSV dimuat: {len(data)} records")
                    print(f"   Periode: {data.index.min()} sampai {data.index.max()}")
                except Exception as e2:
                    print(f"⚠️  Masih gagal memuat CSV setelah pengambilan data: {e2}")
                    print(f"⚠️  Fallback ke {DATA_SOURCE}...")
                    if DATA_SOURCE == "binance":
                        data = load_data_from_binance()
                        if data is None or data.empty:
                            print("⚠️  Binance gagal, fallback ke yfinance...")
                            data = load_data_from_yfinance()
                    else:
                        data = load_data_from_yfinance()
            else:
                print(f"⚠️  Gagal mengambil data historical: {result.stderr[:200] if result.stderr else 'Unknown error'}")
                print(f"⚠️  Fallback ke {DATA_SOURCE}...")
                if DATA_SOURCE == "binance":
                    data = load_data_from_binance()
                    if data is None or data.empty:
                        print("⚠️  Binance gagal, fallback ke yfinance...")
                        data = load_data_from_yfinance()
                else:
                    data = load_data_from_yfinance()
        except Exception as e2:
            print(f"⚠️  Error menjalankan get_historical_data.py: {e2}")
            print(f"⚠️  Fallback ke {DATA_SOURCE}...")
            if DATA_SOURCE == "binance":
                data = load_data_from_binance()
                if data is None or data.empty:
                    print("⚠️  Binance gagal, fallback ke yfinance...")
                    data = load_data_from_yfinance()
            else:
                data = load_data_from_yfinance()
            
    except Exception as e:
        print(f"\n❌ Error memuat data CSV: {e}")
        print(f"⚠️  Fallback ke {DATA_SOURCE}...")
        if DATA_SOURCE == "binance":
            data = load_data_from_binance()
            if data is None or data.empty:
                print("⚠️  Binance gagal, fallback ke yfinance...")
                print("   PERINGATAN: Ini akan mengambil data lebih lama (1 tahun), mungkin tidak sesuai dengan data CSV!")
                data = load_data_from_yfinance()
        else:
            print("   PERINGATAN: Ini akan mengambil data lebih lama (1 tahun), mungkin tidak sesuai dengan data CSV!")
            print("   Jika ingin menggunakan data CSV, perbaiki error di atas atau set USE_CSV_DATA = False")
            data = load_data_from_yfinance()
else:
    # Gunakan DATA_SOURCE dari config untuk menentukan sumber data
    if DATA_SOURCE == "binance":
        data = load_data_from_binance()
        # Fallback ke yfinance jika Binance gagal
        if data is None or data.empty:
            print("⚠️  Binance API gagal, fallback ke yfinance...")
            data = load_data_from_yfinance()
    else:
        data = load_data_from_yfinance()

if data is None or len(data) == 0:
    print("❌ Tidak ada data yang bisa digunakan!")
    sys.exit(1)

# Pastikan kolom Close ada
if 'Close' not in data.columns:
    if isinstance(data, pd.Series):
        data = pd.DataFrame({'Close': data})
    else:
        raise ValueError("Kolom 'Close' tidak ditemukan")

# Deteksi interval data yang sebenarnya
def detect_data_interval(df):
    """Deteksi interval data berdasarkan perbedaan waktu antar baris"""
    if len(df) < 2:
        return "unknown"
    
    time_diffs = df.index.to_series().diff().dropna()
    median_diff = time_diffs.median()
    
    # Konversi ke menit
    if isinstance(median_diff, pd.Timedelta):
        minutes = median_diff.total_seconds() / 60
        if minutes <= 1:
            return "1m"
        elif minutes <= 5:
            return "5m"
        elif minutes <= 15:
            return "15m"
        elif minutes <= 30:
            return "30m"
        elif minutes <= 60:
            return "1h"
        elif minutes <= 1440:
            return "1d"
        else:
            return "1d+"
    return "unknown"

detected_interval = detect_data_interval(data)
print(f"\n📅 Interval data terdeteksi: {detected_interval}")
print(f"   Periode data: {data.index.min()} sampai {data.index.max()}")
print(f"   Total records: {len(data)}")

# Hitung return
data['Return'] = data['Close'].pct_change()

# ============================================
# ENHANCED FEATURES - Volume, Market Context, Advanced Features
# ============================================
try:
    from src.analysis.enhanced_analysis import (
        enhance_data_with_volume_analysis,
        enhance_data_with_market_context,
        enhance_data_with_advanced_features,
        calculate_enhanced_validation_metrics,
        print_enhanced_metrics,
        print_market_context,
        print_volume_analysis_summary,
        print_advanced_features_summary
    )
    USE_ENHANCED_FEATURES = True
except ImportError:
    USE_ENHANCED_FEATURES = False
    print("ℹ️  Enhanced features tidak tersedia, menggunakan analisis dasar")

# Tambahkan volume analysis
if USE_ENHANCED_FEATURES:
    data = enhance_data_with_volume_analysis(data)

# Tambahkan market context
market_context = {}
if USE_ENHANCED_FEATURES:
    data, market_context = enhance_data_with_market_context(data, SYMBOL, detected_interval)

# Tambahkan advanced features
if USE_ENHANCED_FEATURES:
    data = enhance_data_with_advanced_features(data)

# 2️⃣ Buat indikator sederhana (Moving Average)
# Sesuaikan window berdasarkan trading style dan frekuensi data

# Konfigurasi berdasarkan Trading Style
TRADING_CONFIG = {
    "SCALPING": {
        "ma_short": 3,   # 3 periode (sangat cepat)
        "ma_long": 9,    # 9 periode
        "interval": "1m", # 1 menit
        "description": "Scalping - Trading sangat cepat (detik-menit)"
    },
    "DAY_TRADING": {
        "ma_short": 5,   # 5 periode
        "ma_long": 15,   # 15 periode
        "interval": "15m", # 15 menit
        "description": "Day Trading - Trading dalam 1 hari"
    },
    "SWING_TRADING": {
        "ma_short": 10,  # 10 periode
        "ma_long": 30,   # 30 periode
        "interval": "1h", # 1 jam (atau "4h" untuk swing lebih pendek)
        "description": "Swing Trading - Trading beberapa hari-minggu"
    },
    "POSITION_TRADING": {
        "ma_short": 20,  # 20 periode
        "ma_long": 50,   # 50 periode
        "interval": "1d", # 1 hari
        "description": "Position Trading - Trading jangka panjang (minggu-bulan)"
    }
}

# Ambil konfigurasi berdasarkan trading style
if TRADING_STYLE in TRADING_CONFIG:
    config = TRADING_CONFIG[TRADING_STYLE]
    expected_interval = config['interval']
    
    # print(f"\n📊 Trading Style: {TRADING_STYLE}")
    # print(f"   {config['description']}")
    # print(f"   MA Short: {config['ma_short']} | MA Long: {config['ma_long']}")
    # print(f"   Interval yang direkomendasikan: {expected_interval}")
    
    # Validasi interval (fleksibel untuk variasi yang masih masuk akal)
    # Untuk SWING_TRADING, terima "1h" atau "4h" sebagai valid
    valid_intervals = {
        "SCALPING": ["1m", "5m"],
        "DAY_TRADING": ["5m", "15m", "30m"],
        "SWING_TRADING": ["1h", "4h"],  # Terima 1h atau 4h untuk swing trading
        "POSITION_TRADING": ["1d", "1wk"]
    }
    
    if TRADING_STYLE in valid_intervals:
        if detected_interval not in valid_intervals[TRADING_STYLE]:
            print(f"\n⚠️  PERINGATAN: Interval data ({detected_interval}) tidak sesuai dengan trading style!")
            print(f"   Trading style '{TRADING_STYLE}' membutuhkan interval: {', '.join(valid_intervals[TRADING_STYLE])}")
            print(f"   Data saat ini menggunakan interval: {detected_interval}")
            print(f"\n💡 SOLUSI:")
            print(f"   1. Ambil data baru dengan interval yang sesuai")
            print(f"   2. Ubah di config.py: INTERVAL = \"{valid_intervals[TRADING_STYLE][0]}\"")
            print(f"   3. Atau ubah TRADING_STYLE ke yang sesuai dengan interval {detected_interval}")
    elif detected_interval != expected_interval:
        print(f"\n⚠️  PERINGATAN: Interval data ({detected_interval}) tidak sesuai dengan trading style!")
        print(f"   Trading style '{TRADING_STYLE}' membutuhkan interval: {expected_interval}")
        print(f"   Data saat ini menggunakan interval: {detected_interval}")
        print(f"\n💡 SOLUSI:")
        print(f"   1. Ambil data baru dengan interval {expected_interval}")
        print(f"   2. Ubah di config.py: INTERVAL = \"{expected_interval}\"")
        print(f"   3. Atau ubah TRADING_STYLE ke yang sesuai dengan interval {detected_interval}")
    
    # Sesuaikan dengan tipe data
    if USE_CSV_DATA:
        # Data dari CSV (biasanya per menit)
        ma_short_window = config['ma_short']
        ma_long_window = config['ma_long']
    else:
        # Data dari yfinance (biasanya harian)
        # Untuk swing/position trading, gunakan window yang lebih besar
        if TRADING_STYLE in ["SWING_TRADING", "POSITION_TRADING"]:
            ma_short_window = config['ma_short']
            ma_long_window = config['ma_long']
        else:
            # Untuk scalping/day trading dengan data harian, sesuaikan
            ma_short_window = max(config['ma_short'], 5)
            ma_long_window = max(config['ma_long'], 15)
else:
    # Default: Swing Trading
    print(f"\n⚠️  Trading style '{TRADING_STYLE}' tidak dikenal, menggunakan SWING_TRADING")
    if USE_CSV_DATA:
        ma_short_window = 5
        ma_long_window = 15
    else:
        ma_short_window = 10
        ma_long_window = 30

# Cek apakah ada data hari ini
today = datetime.now().date()
last_data_date = pd.to_datetime(data.index[-1]).date()
data_dates = [pd.to_datetime(idx).date() for idx in data.index]
has_today_data = today in data_dates

if not has_today_data:
    days_diff = (today - last_data_date).days
    print(f"\n⚠️  Data terakhir: {last_data_date} (hari ini: {today})")
    print(f"   Selisih: {days_diff} hari")
    if days_diff > 1:
        print(f"   ⚠️  Data tidak up-to-date! Ambil data terbaru untuk sinyal hari ini.")
        if TRADING_STYLE in TRADING_CONFIG:
            print(f"   💡 Jalankan: python get_historical_data.py (dengan INTERVAL = \"{expected_interval}\")")
        else:
            print(f"   💡 Jalankan: python get_historical_data.py untuk mengambil data terbaru")
    elif days_diff == 1:
        print(f"   ℹ️  Data kemarin, mungkin belum ada data hari ini (pasar tutup atau belum update)")
else:
    print(f"\n✅ Data hari ini tersedia")

# 2️⃣ Hitung 5 Indikator Wajib
# Indikator 1: EMA 20, 50, 200 → trend
print("\n📊 Menghitung EMA 20, 50, 200...")
data['EMA_20'] = data['Close'].ewm(span=20, adjust=False).mean()
if len(data) >= 50:
    data['EMA_50'] = data['Close'].ewm(span=50, adjust=False).mean()
else:
    data['EMA_50'] = data['EMA_20']  # Fallback jika data kurang
if len(data) >= 200:
    data['EMA_200'] = data['Close'].ewm(span=200, adjust=False).mean()
else:
    data['EMA_200'] = data['EMA_50']  # Fallback jika data kurang
print("✅ EMA 20, 50, 200 berhasil dihitung")

# Indikator 3: MACD → perubahan arah
print("\n📊 Menghitung MACD...")
ema_fast = data['Close'].ewm(span=12, adjust=False).mean()
ema_slow = data['Close'].ewm(span=26, adjust=False).mean()
data['MACD'] = ema_fast - ema_slow
data['MACD_Signal'] = data['MACD'].ewm(span=9, adjust=False).mean()
data['MACD_Histogram'] = data['MACD'] - data['MACD_Signal']
print("✅ MACD berhasil dihitung")

# Untuk kompatibilitas dengan kode lama, tetap hitung MA_short dan MA_long
# Tapi gunakan EMA untuk sinyal utama
data['MA_short'] = data['Close'].rolling(window=ma_short_window).mean()
data['MA_long'] = data['Close'].rolling(window=ma_long_window).mean()

# 2.5️⃣ Hitung Support dan Resistance
def calculate_support_resistance(df, window=20, pivot_window=5):
    """
    Menghitung Support dan Resistance menggunakan:
    1. Pivot Points (klasik)
    2. Local Minima/Maxima (dinamis)
    """
    result = pd.DataFrame(index=df.index)
    
    # Method 1: Pivot Points (menggunakan high, low, close)
    # Pivot Point = (High + Low + Close) / 3
    # Resistance 1 = 2 * Pivot - Low
    # Support 1 = 2 * Pivot - High
    if 'High' in df.columns and 'Low' in df.columns:
        # Rolling pivot (menggunakan window untuk smoothing)
        rolling_high = df['High'].rolling(window=pivot_window).max()
        rolling_low = df['Low'].rolling(window=pivot_window).min()
        rolling_close = df['Close'].rolling(window=pivot_window).mean()
        
        pivot = (rolling_high + rolling_low + rolling_close) / 3
        result['Resistance_Pivot'] = 2 * pivot - rolling_low
        result['Support_Pivot'] = 2 * pivot - rolling_high
    else:
        # Fallback jika tidak ada High/Low
        result['Resistance_Pivot'] = df['Close'].rolling(window=window).max()
        result['Support_Pivot'] = df['Close'].rolling(window=window).min()
    
    # Method 2: Local Minima/Maxima (lebih dinamis)
    # Cari local minima (support) dan maxima (resistance)
    if not HAS_SCIPY:
        # Fallback jika scipy tidak tersedia
        support_levels = pd.Series(df['Close'].rolling(window=window).min(), index=df.index)
        resistance_levels = pd.Series(df['Close'].rolling(window=window).max(), index=df.index)
        result['Support_Local'] = support_levels
        result['Resistance_Local'] = resistance_levels
        result['Support'] = result[['Support_Pivot', 'Support_Local']].min(axis=1)
        result['Resistance'] = result[['Resistance_Pivot', 'Resistance_Local']].max(axis=1)
        return result
    
    # Local minima (support) - harga terendah dalam window
    local_min_indices = argrelextrema(df['Close'].values, np.less_equal, order=window//2)[0]
    local_max_indices = argrelextrema(df['Close'].values, np.greater_equal, order=window//2)[0]
    
    # Buat series untuk support dan resistance dari local extrema
    support_levels = pd.Series(index=df.index, dtype=float)
    resistance_levels = pd.Series(index=df.index, dtype=float)
    
    # Isi dengan nilai local extrema
    if len(local_min_indices) > 0:
        for idx in local_min_indices:
            if idx < len(df):
                support_levels.iloc[idx] = df['Close'].iloc[idx]
    
    if len(local_max_indices) > 0:
        for idx in local_max_indices:
            if idx < len(df):
                resistance_levels.iloc[idx] = df['Close'].iloc[idx]
    
    # Forward fill untuk membuat level yang kontinyu
    support_levels = support_levels.ffill()
    resistance_levels = resistance_levels.ffill()
    
    # Backward fill untuk mengisi nilai awal
    support_levels = support_levels.bfill()
    resistance_levels = resistance_levels.bfill()
    
    # Jika masih ada NaN, gunakan rolling min/max sebagai fallback
    if support_levels.isna().any():
        support_levels = support_levels.fillna(df['Close'].rolling(window=window).min())
    if resistance_levels.isna().any():
        resistance_levels = resistance_levels.fillna(df['Close'].rolling(window=window).max())
    
    result['Support_Local'] = support_levels
    result['Resistance_Local'] = resistance_levels
    
    # Gabungkan: gunakan yang lebih konservatif (support lebih rendah, resistance lebih tinggi)
    result['Support'] = result[['Support_Pivot', 'Support_Local']].min(axis=1)
    result['Resistance'] = result[['Resistance_Pivot', 'Resistance_Local']].max(axis=1)
    
    return result

# Hitung Support dan Resistance
print("\n📊 Menghitung Support dan Resistance...")
try:
    sr_data = calculate_support_resistance(data, window=max(ma_short_window, ma_long_window), pivot_window=10)
    data['Support'] = sr_data['Support']
    data['Resistance'] = sr_data['Resistance']
    data['Support_Pivot'] = sr_data['Support_Pivot']
    data['Resistance_Pivot'] = sr_data['Resistance_Pivot']
    print("✅ Support dan Resistance berhasil dihitung")
except ImportError:
    print("⚠️  scipy tidak tersedia, menggunakan metode sederhana...")
    # Fallback: gunakan rolling min/max
    window_sr = max(ma_short_window, ma_long_window)
    data['Support'] = data['Low'].rolling(window=window_sr).min() if 'Low' in data.columns else data['Close'].rolling(window=window_sr).min()
    data['Resistance'] = data['High'].rolling(window=window_sr).max() if 'High' in data.columns else data['Close'].rolling(window=window_sr).max()
    data['Support_Pivot'] = data['Support']
    data['Resistance_Pivot'] = data['Resistance']
    print("✅ Support dan Resistance dihitung dengan metode sederhana")
except Exception as e:
    print(f"⚠️  Error menghitung Support/Resistance: {e}")
    # Fallback sederhana
    window_sr = max(ma_short_window, ma_long_window)
    data['Support'] = data['Low'].rolling(window=window_sr).min() if 'Low' in data.columns else data['Close'].rolling(window=window_sr).min()
    data['Resistance'] = data['High'].rolling(window=window_sr).max() if 'High' in data.columns else data['Close'].rolling(window=window_sr).max()
    data['Support_Pivot'] = data['Support']
    data['Resistance_Pivot'] = data['Resistance']

# 3️⃣ Buat sinyal trading berdasarkan 5 indikator wajib
# Sinyal berdasarkan EMA alignment (trend) + MACD + RSI (jika ada)
print("\n📊 Membuat sinyal trading berdasarkan 5 indikator wajib...")
data['Signal'] = 0

# Sinyal berdasarkan EMA alignment (Indikator 1: EMA 20, 50, 200 → trend)
# BULLISH: Price > EMA_20 > EMA_50 > EMA_200
# BEARISH: Price < EMA_20 < EMA_50 < EMA_200
ema_bullish = (data['Close'] > data['EMA_20']) & (data['EMA_20'] > data['EMA_50']) & (data['EMA_50'] > data['EMA_200'])
ema_bearish = (data['Close'] < data['EMA_20']) & (data['EMA_20'] < data['EMA_50']) & (data['EMA_50'] < data['EMA_200'])

# Sinyal MACD (Indikator 3: MACD → perubahan arah)
# BULLISH: MACD > Signal dan Histogram > 0
# BEARISH: MACD < Signal dan Histogram < 0
macd_bullish = (data['MACD'] > data['MACD_Signal']) & (data['MACD_Histogram'] > 0)
macd_bearish = (data['MACD'] < data['MACD_Signal']) & (data['MACD_Histogram'] < 0)

# Kombinasi sinyal: EMA + MACD harus align
# LONG: EMA bullish DAN MACD bullish
# SHORT: EMA bearish DAN MACD bearish
data.loc[ema_bullish & macd_bullish, 'Signal'] = 1   # Beli (LONG)
data.loc[ema_bearish & macd_bearish, 'Signal'] = -1  # Jual (SHORT)

# Fallback: jika tidak ada alignment, gunakan EMA saja
data.loc[(data['Signal'] == 0) & ema_bullish, 'Signal'] = 1   # Beli (LONG) - EMA bullish saja
data.loc[(data['Signal'] == 0) & ema_bearish, 'Signal'] = -1  # Jual (SHORT) - EMA bearish saja

print("✅ Sinyal trading berhasil dibuat")

# Deteksi perubahan sinyal (crossover)
# Crossover beli: berubah dari bukan-beli (0 atau -1) menjadi beli (1)
# Crossover jual: berubah dari bukan-jual (0 atau 1) menjadi jual (-1)
data['Signal_Change'] = data['Signal'].diff()
data['Prev_Signal'] = data['Signal'].shift(1)

# Sinyal beli: berubah dari -1 atau 0 ke 1
data['Buy_Signal'] = (data['Signal'] == 1) & ((data['Prev_Signal'] == -1) | (data['Prev_Signal'] == 0))

# Sinyal jual: berubah dari 1 atau 0 ke -1
data['Sell_Signal'] = (data['Signal'] == -1) & ((data['Prev_Signal'] == 1) | (data['Prev_Signal'] == 0))

# 4️⃣ Hitung return strategi
data['Strategy_Return'] = data['Signal'].shift(1) * data['Return']
data['Cumulative_Strategy'] = (1 + data['Strategy_Return']).cumprod()
data['Cumulative_BuyHold'] = (1 + data['Return']).cumprod()

# 5️⃣ Statistik dan Detail Sinyal
print("\n" + "=" * 50)
print("HASIL ANALISIS STRATEGI")
print("=" * 50)
print(f"📊 Sumber Data: {'CSV' if USE_CSV_DATA else 'yfinance'}")
print(f"Total periode: {len(data)}")
print(f"Periode data: {data.index.min()} sampai {data.index.max()}")

# Hitung rentang hari
data_span_days = (data.index.max() - data.index.min()).days
print(f"Rentang waktu: {data_span_days} hari")

if data_span_days > 30:
    print(f"⚠️  PERINGATAN: Data mencakup {data_span_days} hari!")
    print(f"   Jika CSV hanya 7 hari, mungkin menggunakan data dari yfinance (fallback)")

print(f"Return Buy & Hold: {(data['Cumulative_BuyHold'].iloc[-1] - 1) * 100:.2f}%")
print(f"Return Strategi: {(data['Cumulative_Strategy'].iloc[-1] - 1) * 100:.2f}%")
print()

# Hitung statistik posisi
buy_periods = (data['Signal'] == 1).sum()
sell_periods = (data['Signal'] == -1).sum()
neutral_periods = (data['Signal'] == 0).sum()
crossover_buy = data['Buy_Signal'].sum()
crossover_sell = data['Sell_Signal'].sum()

# Posisi saat ini (data terakhir)
last_idx = data.index[-1]
last_signal = data['Signal'].iloc[-1]
last_close = data['Close'].iloc[-1]  # Fallback price dari klines
last_ma_short = data['MA_short'].iloc[-1] if pd.notna(data['MA_short'].iloc[-1]) else 0
last_ma_long = data['MA_long'].iloc[-1] if pd.notna(data['MA_long'].iloc[-1]) else 0

signal_text = "BELI" if last_signal == 1 else ("JUAL" if last_signal == -1 else "NETRAL")

# Get real-time current price dari ticker endpoint (untuk Futures API)
current_price_realtime = None
price_fetch_error = None
try:
    # Cek apakah menggunakan Binance Futures API
    from src.utils.config import BINANCE_API_TYPE, DATA_SOURCE
    if DATA_SOURCE == "binance" and BINANCE_API_TYPE and BINANCE_API_TYPE.lower() == "futures":
        from src.data.binance_futures_data import get_futures_ticker_price
        
        # Convert symbol format: DOGE-USD -> DOGEUSDT atau XPIN-USD -> XPINUSDT
        if SYMBOL and SYMBOL.endswith("-USD"):
            binance_symbol = SYMBOL.replace("-USD", "") + "USDT"
        elif TRADING_SYMBOL:
            # Handle TRADING_SYMBOL yang mungkin sudah dalam format USDT atau masih -USD
            if TRADING_SYMBOL.endswith("-USD"):
                binance_symbol = TRADING_SYMBOL.replace("-USD", "") + "USDT"
            elif TRADING_SYMBOL.endswith("USDT"):
                binance_symbol = TRADING_SYMBOL
            else:
                binance_symbol = TRADING_SYMBOL + "USDT"
        else:
            binance_symbol = None
        
        if binance_symbol:
            print(f"💰 [REAL-TIME PRICE] Fetching current price from ticker endpoint for {binance_symbol}...")
            # Retry mechanism: coba 3 kali
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    price_data = get_futures_ticker_price(symbol=binance_symbol)
                    
                    if price_data:
                        if isinstance(price_data, dict) and 'price' in price_data:
                            current_price_realtime = float(price_data['price'])
                            print(f"   ✅ Real-time price: {current_price_realtime} (attempt {attempt + 1})")
                            break
                        elif isinstance(price_data, list) and len(price_data) > 0:
                            # Jika return list, cari symbol yang sesuai
                            for item in price_data:
                                if isinstance(item, dict) and item.get('symbol') == binance_symbol.upper():
                                    current_price_realtime = float(item.get('price', 0))
                                    print(f"   ✅ Real-time price: {current_price_realtime} (attempt {attempt + 1})")
                                    break
                            if current_price_realtime:
                                break
                    
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(0.5)  # Wait 0.5 second before retry
                except Exception as retry_error:
                    price_fetch_error = str(retry_error)
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(0.5)  # Wait 0.5 second before retry
                    else:
                        print(f"   ❌ Failed after {max_retries} attempts: {retry_error}")
            
            if current_price_realtime is None:
                print(f"   ⚠️  Failed to get real-time price after {max_retries} attempts")
                if price_fetch_error:
                    print(f"   ⚠️  Error: {price_fetch_error}")
                print(f"   ⚠️  Using klines price as fallback: {last_close}")
    elif DATA_SOURCE == "binance" and BINANCE_API_TYPE and BINANCE_API_TYPE.lower() == "spot":
        # Untuk spot API, juga coba ambil real-time price
        from src.data.binance_data import get_ticker_price
        
        # Convert symbol format
        if SYMBOL and SYMBOL.endswith("-USD"):
            binance_symbol = SYMBOL.replace("-USD", "") + "USDT"
        elif TRADING_SYMBOL:
            if TRADING_SYMBOL.endswith("-USD"):
                binance_symbol = TRADING_SYMBOL.replace("-USD", "") + "USDT"
            elif TRADING_SYMBOL.endswith("USDT"):
                binance_symbol = TRADING_SYMBOL
            else:
                binance_symbol = TRADING_SYMBOL + "USDT"
        else:
            binance_symbol = None
        
        if binance_symbol:
            print(f"💰 [REAL-TIME PRICE] Fetching current price from spot ticker for {binance_symbol}...")
            try:
                current_price_realtime = get_ticker_price(symbol=binance_symbol)
                if current_price_realtime:
                    print(f"   ✅ Real-time price: {current_price_realtime}")
                else:
                    print(f"   ⚠️  Failed to get real-time price, using klines price as fallback")
            except Exception as spot_error:
                print(f"   ⚠️  Error fetching spot price: {spot_error}, using klines price as fallback")
except Exception as e:
    price_fetch_error = str(e)
    print(f"   ⚠️  Error fetching real-time price: {e}, using klines price as fallback")

# Gunakan real-time price jika tersedia, fallback ke last_close
if current_price_realtime is not None and current_price_realtime > 0:
    current_price = current_price_realtime
    price_source = "real-time (ticker)"
    
    # Validasi: cek apakah harga real-time berbeda terlalu jauh dari klines price
    # Jika berbeda lebih dari 5%, mungkin ada masalah dengan data klines (stale)
    if last_close and last_close > 0:
        price_diff_pct = abs((current_price - last_close) / last_close) * 100
        if price_diff_pct > 5.0:
            print(f"   ⚠️  WARNING: Real-time price ({current_price}) berbeda {price_diff_pct:.2f}% dari klines price ({last_close})")
            print(f"   ⚠️  Kemungkinan: data klines sudah lama atau symbol berbeda")
            print(f"   ⚠️  Menggunakan real-time price sebagai sumber utama")
        elif price_diff_pct > 1.0:
            print(f"   ℹ️  Real-time price berbeda {price_diff_pct:.2f}% dari klines price (normal untuk volatile market)")
else:
    current_price = last_close
    price_source = "klines (last close)"
    print(f"   ⚠️  WARNING: Menggunakan harga dari klines (mungkin tidak real-time)")
    print(f"   ⚠️  Harga klines: {last_close} (timestamp: {last_idx})")
    print(f"   ⚠️  Pastikan data klines selalu up-to-date untuk akurasi signal")

print("POSISI TRADING:")
print(f"  - Periode dalam posisi BELI: {buy_periods} ({buy_periods/len(data)*100:.1f}%)")
print(f"  - Periode dalam posisi JUAL: {sell_periods} ({sell_periods/len(data)*100:.1f}%)")
print(f"  - Periode NETRAL: {neutral_periods} ({neutral_periods/len(data)*100:.1f}%)")
print()
# Support dan Resistance saat ini
# Pastikan konversi ke float/scalar
try:
    last_support_val = data['Support'].iloc[-1]
    if pd.notna(last_support_val):
        if isinstance(last_support_val, pd.Series):
            last_support = float(last_support_val.iloc[0])
        else:
            last_support = float(last_support_val)
    else:
        last_support = None
except (IndexError, KeyError, TypeError):
    last_support = None

try:
    last_resistance_val = data['Resistance'].iloc[-1]
    if pd.notna(last_resistance_val):
        if isinstance(last_resistance_val, pd.Series):
            last_resistance = float(last_resistance_val.iloc[0])
        else:
            last_resistance = float(last_resistance_val)
    else:
        last_resistance = None
except (IndexError, KeyError, TypeError):
    last_resistance = None

# Pastikan current_price juga float (gunakan real-time price jika tersedia)
try:
    if isinstance(current_price, pd.Series):
        current_price = float(current_price.iloc[0])
    else:
        current_price = float(current_price)
except (TypeError, ValueError):
    current_price = 0.0

# Keep last_close untuk compatibility dengan code lain
last_close = current_price

# Format waktu dengan timezone info
if isinstance(last_idx, pd.Timestamp):
    # Jika ada timezone info, konversi ke lokal (WIB = UTC+7)
    try:
        if last_idx.tz is not None:
            # Konversi ke WIB (UTC+7)
            last_idx_wib = last_idx.tz_convert('Asia/Jakarta')
            time_display = f"{last_idx_wib.strftime('%Y-%m-%d %H:%M:%S')} WIB (UTC: {last_idx.strftime('%Y-%m-%d %H:%M:%S %Z')})"
        else:
            # Jika tidak ada timezone, asumsikan UTC dan konversi ke WIB
            last_idx_utc = last_idx.tz_localize('UTC')
            last_idx_wib = last_idx_utc.tz_convert('Asia/Jakarta')
            time_display = f"{last_idx_wib.strftime('%Y-%m-%d %H:%M:%S')} WIB (UTC: {last_idx.strftime('%Y-%m-%d %H:%M:%S')})"
    except Exception as e:
        # Fallback jika konversi timezone gagal
        time_display = str(last_idx)
else:
    time_display = str(last_idx)

print(f"POSISI SAAT INI (Data terakhir - {time_display}):")
print(f"  - Posisi: {signal_text}")
print(f"  - Harga: {format_price(current_price)} ({price_source})")
print()
print(f"  📊 5 INDIKATOR WAJIB:")
# Indikator 1: EMA 20, 50, 200
try:
    last_ema_20 = data['EMA_20'].iloc[-1]
    last_ema_50 = data['EMA_50'].iloc[-1]
    last_ema_200 = data['EMA_200'].iloc[-1]
    if pd.notna(last_ema_20):
        print(f"  1️⃣  EMA 20: {format_price(float(last_ema_20))}")
    if pd.notna(last_ema_50):
        print(f"      EMA 50: {format_price(float(last_ema_50))}")
    if pd.notna(last_ema_200):
        print(f"      EMA 200: {format_price(float(last_ema_200))}")
    
    # Trend signal berdasarkan EMA alignment
    if pd.notna(last_ema_20) and pd.notna(last_ema_50) and pd.notna(last_ema_200):
        if current_price > float(last_ema_20) > float(last_ema_50) > float(last_ema_200):
            trend_signal = "🟢 BULLISH (Uptrend kuat)"
        elif current_price < float(last_ema_20) < float(last_ema_50) < float(last_ema_200):
            trend_signal = "🔴 BEARISH (Downtrend kuat)"
        elif float(last_ema_20) > float(last_ema_50):
            trend_signal = "🟡 BULLISH_WEAK (Uptrend lemah)"
        else:
            trend_signal = "🟡 BEARISH_WEAK (Downtrend lemah)"
        print(f"      Trend: {trend_signal}")
except:
    pass

# Indikator 2: RSI (jika ada di enhanced features)
try:
    if 'RSI' in data.columns:
        last_rsi = data['RSI'].iloc[-1]
        if pd.notna(last_rsi):
            rsi_val = float(last_rsi)
            rsi_signal = "OVERSOLD" if rsi_val < 30 else ("OVERBOUGHT" if rsi_val > 70 else "NEUTRAL")
            print(f"  2️⃣  RSI: {rsi_val:.2f} ({rsi_signal})")
except:
    pass

# Indikator 3: MACD
try:
    last_macd = data['MACD'].iloc[-1]
    last_macd_signal = data['MACD_Signal'].iloc[-1]
    last_macd_hist = data['MACD_Histogram'].iloc[-1]
    if pd.notna(last_macd) and pd.notna(last_macd_signal):
        macd_val = float(last_macd)
        macd_sig = float(last_macd_signal)
        macd_hist = float(last_macd_hist) if pd.notna(last_macd_hist) else 0
        macd_signal_text = "🟢 BULLISH" if macd_val > macd_sig and macd_hist > 0 else ("🔴 BEARISH" if macd_val < macd_sig and macd_hist < 0 else "🟡 NEUTRAL")
        print(f"  3️⃣  MACD: {macd_val:.4f} | Signal: {macd_sig:.4f} | Hist: {macd_hist:.4f}")
        print(f"      Signal: {macd_signal_text}")
except:
    pass

# Indikator 4: Volume (jika ada)
try:
    if 'Volume' in data.columns:
        last_volume = data['Volume'].iloc[-1]
        if pd.notna(last_volume):
            print(f"  4️⃣  Volume: {format_price(float(last_volume))}")
except:
    pass

# Indikator 5: Support/Resistance
if last_support is not None and last_resistance is not None:
    support_dist = ((current_price - last_support) / current_price * 100) if current_price > 0 else 0
    resistance_dist = ((last_resistance - current_price) / current_price * 100) if current_price > 0 else 0
    print(f"  5️⃣  Support: {format_price(last_support)} (jarak: {support_dist:.2f}%)")
    print(f"      Resistance: {format_price(last_resistance)} (jarak: {resistance_dist:.2f}%)")
    # Tentukan apakah harga mendekati support atau resistance
    dist_to_support = abs(current_price - last_support) / current_price * 100 if current_price > 0 else 0
    dist_to_resistance = abs(last_resistance - current_price) / current_price * 100 if current_price > 0 else 0
    if dist_to_support < 2:
        print(f"  ⚠️  Harga sangat dekat dengan Support! (kemungkinan bounce atau breakdown)")
    elif dist_to_resistance < 2:
        print(f"  ⚠️  Harga sangat dekat dengan Resistance! (kemungkinan breakout atau rejection)")
print()

# ============================================
# TRADING SETUP (Entry, Stop Loss, Take Profit)
# ============================================
def calculate_fibonacci_levels(support, resistance, current_price):
    """
    Hitung Fibonacci retracement levels berdasarkan support dan resistance
    
    Args:
        support: Support level
        resistance: Resistance level
        current_price: Current market price
    
    Returns:
        Dictionary dengan Fibonacci levels (0.236, 0.382, 0.5, 0.618, 0.786)
    """
    if support is None or resistance is None:
        return None
    
    # Range dari support ke resistance
    price_range = resistance - support
    
    # Fibonacci retracement levels (dari support ke resistance)
    fib_levels = {
        'fib_236': support + (price_range * 0.236),  # 23.6%
        'fib_382': support + (price_range * 0.382),  # 38.2%
        'fib_500': support + (price_range * 0.500),  # 50.0%
        'fib_618': support + (price_range * 0.618),  # 61.8%
        'fib_786': support + (price_range * 0.786),  # 78.6%
    }
    
    return fib_levels


def generate_trading_setup(symbol, current_price, support, resistance, signal, 
                           use_limit_entry=True, risk_percent=2.5, tp_multipliers=None):
    """
    Generate trading setup dengan Multiple Entry Levels, Stop Loss, dan Take Profit levels
    
    Parameters:
    - symbol: Trading symbol (e.g., "BTCUSDT", "ENAUSDT")
    - current_price: Current market price
    - support: Support level
    - resistance: Resistance level
    - signal: Trading signal (1 = BELI/LONG, -1 = JUAL/SHORT)
    - use_limit_entry: True = gunakan limit entry (di support untuk LONG), False = market entry
    - risk_percent: Risk percentage untuk stop loss (default 2.5%)
    - tp_multipliers: List of TP multipliers [tp1, tp2, tp3] (default [1.5, 2.5, 3.5])
    
    Returns:
    - Dictionary dengan entry1, entry2, entry3, stop_loss, tp1, tp2, tp3
    """
    # Default TP multipliers jika tidak diberikan
    if tp_multipliers is None:
        tp_multipliers = [1.5, 2.5, 3.5]
    
    # Hitung Fibonacci levels jika support dan resistance tersedia
    fib_levels = calculate_fibonacci_levels(support, resistance, current_price) if support and resistance else None
    
    if signal == 1:  # LONG/BUY
        direction = "LONG"
        action = "BUY"
        
        # ============================================
        # MULTIPLE ENTRY LEVELS untuk LONG
        # ============================================
        if support is not None and resistance is not None:
            # Entry 1: Paling agresif - dekat current price atau sedikit di atas support
            # Gunakan jika harga sudah di atas support dan momentum kuat
            if current_price >= support * 1.002:  # Harga sudah di atas support
                entry1 = current_price * 1.001  # 0.1% di atas current (agresif)
            else:
                entry1 = support * 1.002  # 0.2% di atas support (agresif)
            
            # Entry 2: Konservatif - di support atau Fibonacci 0.618
            if fib_levels:
                # Gunakan Fibonacci 0.618 jika lebih dekat ke support
                entry2_option1 = support * 1.001  # 0.1% di atas support
                entry2_option2 = fib_levels['fib_618']  # Fibonacci 0.618
                entry2 = max(entry2_option1, entry2_option2)  # Ambil yang lebih tinggi (lebih konservatif)
            else:
                entry2 = support * 1.001  # 0.1% di atas support
            
            # Entry 3: Sangat konservatif - di bawah support atau Fibonacci 0.786 (wait for pullback)
            if fib_levels:
                # Gunakan Fibonacci 0.786 atau sedikit di bawah support
                entry3_option1 = support * 0.998  # 0.2% di bawah support (sangat konservatif)
                entry3_option2 = fib_levels['fib_786']  # Fibonacci 0.786
                entry3 = min(entry3_option1, entry3_option2)  # Ambil yang lebih rendah (sangat konservatif)
            else:
                entry3 = support * 0.998  # 0.2% di bawah support (sangat konservatif)
        else:
            # Fallback jika tidak ada support/resistance
            entry1 = current_price * 1.001  # 0.1% di atas current
            entry2 = current_price * 0.998  # 0.2% di bawah current
            entry3 = current_price * 0.995  # 0.5% di bawah current
        
        # Gunakan entry2 sebagai entry utama (konservatif)
        entry_price = entry2
        
        # Stop Loss (di bawah support atau berdasarkan risk %)
        if support is not None:
            sl_based_on_support = support * 0.995  # 0.5% di bawah support
            sl_based_on_risk = entry_price * (1 - risk_percent / 100)
            stop_loss = min(sl_based_on_support, sl_based_on_risk)  # Ambil yang lebih konservatif
        else:
            stop_loss = entry_price * (1 - risk_percent / 100)
        
        # Calculate risk (distance from entry to stop loss) - gunakan entry2 sebagai referensi
        risk = entry_price - stop_loss
        risk_pct = (risk / entry_price) * 100
        
        # Validasi: Pastikan risk positif (stop_loss < entry_price)
        if risk <= 0:
            print(f"⚠️  [LONG] Warning: risk <= 0, force stop_loss < entry_min")
            entry_min = min(entry1, entry2, entry3)
            stop_loss = entry_min * (1 - risk_percent / 100)
            risk = entry_price - stop_loss
            risk_pct = (risk / entry_price) * 100
        
        # Untuk LONG: TP harus lebih tinggi dari SEMUA entry levels
        # Gunakan entry tertinggi (entry_max) dan terendah (entry_min) sebagai referensi
        entry_min = min(entry1, entry2, entry3)
        entry_max = max(entry1, entry2, entry3)
        
        # Take Profit levels (berdasarkan resistance atau R:R ratio)
        if resistance is not None:
            # TP1: Target pertama (berdasarkan multiplier atau 50% ke resistance)
            # Hitung TP berdasarkan entry_price (entry2) untuk konsistensi
            tp1_option1 = entry_price + (risk * tp_multipliers[0])  # Berdasarkan R:R ratio
            tp1_option2 = entry_price + ((resistance - entry_price) * 0.5)  # 50% ke resistance
            # Untuk LONG: ambil yang lebih TINGGI (lebih agresif untuk TP)
            tp1 = max(tp1_option1, tp1_option2)
            # Validasi: TP1 harus > entry_max untuk memastikan semua entry profit
            if tp1 <= entry_max:
                # Jika TP1 <= entry_max, gunakan entry_max + margin yang cukup
                tp1 = entry_max * (1 + max(risk_percent * tp_multipliers[0] / 100, 0.005))  # Minimal 0.5% di atas entry_max
            
            # TP2: Target kedua (berdasarkan multiplier atau 75% ke resistance)
            tp2_option1 = entry_price + (risk * tp_multipliers[1])
            tp2_option2 = entry_price + ((resistance - entry_price) * 0.75)  # 75% ke resistance
            # Untuk LONG: ambil yang lebih TINGGI
            tp2 = max(tp2_option1, tp2_option2)
            # Validasi: TP2 harus > TP1 dan > entry_max
            if tp2 <= tp1 or tp2 <= entry_max:
                tp2 = max(tp1 * 1.002, entry_max * (1 + max(risk_percent * tp_multipliers[1] / 100, 0.01)))  # Minimal 1% di atas entry_max
            
            # TP3: Target ketiga (berdasarkan multiplier atau resistance)
            tp3_option1 = entry_price + (risk * tp_multipliers[2])
            # Untuk LONG: TP3 bisa di resistance atau sedikit di atas resistance
            tp3_option2 = resistance * 1.002  # 0.2% di atas resistance
            tp3 = min(max(tp3_option1, tp3_option2), resistance * 1.01)  # Maksimal 1% di atas resistance
            # Validasi: TP3 harus > TP2 dan > entry_max
            if tp3 <= tp2 or tp3 <= entry_max:
                tp3 = max(tp2 * 1.002, entry_max * (1 + max(risk_percent * tp_multipliers[2] / 100, 0.015)))  # Minimal 1.5% di atas entry_max
        else:
            # Jika tidak ada resistance, gunakan R:R ratio saja
            tp1 = entry_price + (risk * tp_multipliers[0])
            # Validasi: TP1 harus > entry_max
            if tp1 <= entry_max:
                tp1 = entry_max * (1 + max(risk_percent * tp_multipliers[0] / 100, 0.005))
            
            tp2 = entry_price + (risk * tp_multipliers[1])
            # Validasi: TP2 harus > TP1 dan > entry_max
            if tp2 <= tp1 or tp2 <= entry_max:
                tp2 = max(tp1 * 1.002, entry_max * (1 + max(risk_percent * tp_multipliers[1] / 100, 0.01)))
            
            tp3 = entry_price + (risk * tp_multipliers[2])
            # Validasi: TP3 harus > TP2 dan > entry_max
            if tp3 <= tp2 or tp3 <= entry_max:
                tp3 = max(tp2 * 1.002, entry_max * (1 + max(risk_percent * tp_multipliers[2] / 100, 0.015)))
        
        # Final validation: Pastikan semua TP > entry_max dan stop_loss < entry_min
        if tp1 <= entry_max:
            tp1 = entry_max * 1.005
        if tp2 <= tp1:
            tp2 = tp1 * 1.002
        if tp3 <= tp2:
            tp3 = tp2 * 1.002
        if stop_loss >= entry_min:
            stop_loss = entry_min * (1 - risk_percent / 100)
            risk = entry_price - stop_loss
            risk_pct = (risk / entry_price) * 100
        
    else:  # SHORT/SELL
        direction = "SHORT"
        action = "SELL"
        
        # ============================================
        # MULTIPLE ENTRY LEVELS untuk SHORT
        # ============================================
        # Untuk SHORT: Semua entry harus DI ATAS current price (kita jual di harga tinggi)
        # Entry 1 (Agresif): Paling dekat dengan current price atau di resistance
        # Entry 2 (Konservatif): Di resistance atau sedikit di atas
        # Entry 3 (Sangat Konservatif): Di atas resistance (menunggu pullback)
        if support is not None and resistance is not None:
            # Entry 1: Paling agresif - sedikit di atas current price (dekat dengan current)
            # Untuk SHORT agresif, entry harus dekat dengan current price (bukan di resistance)
            # Gunakan current price + 0.2% sampai 0.5% sebagai entry agresif
            entry1_agresif = current_price * 1.002  # 0.2% di atas current (agresif)
            entry1_resistance = resistance * 0.999  # Di resistance
            # Ambil yang lebih RENDAH (agresif = lebih dekat dengan current price)
            entry1 = min(entry1_agresif, entry1_resistance)
            # Pastikan entry1 >= current_price
            if entry1 < current_price:
                entry1 = current_price * 1.002
            
            # Entry 2: Konservatif - di resistance atau Fibonacci 0.382 (dari atas)
            if fib_levels:
                # Untuk SHORT, Fibonacci dihitung dari atas (resistance)
                # Fibonacci 0.382 dari atas = resistance - (range * 0.382)
                price_range = resistance - support
                fib_382_from_top = resistance - (price_range * 0.382)
                entry2_option1 = resistance * 0.999  # 0.1% di bawah resistance
                entry2_option2 = fib_382_from_top
                # Ambil yang lebih TINGGI (lebih konservatif untuk SHORT = lebih tinggi)
                entry2 = max(entry2_option1, entry2_option2)
            else:
                entry2 = resistance * 0.999  # 0.1% di bawah resistance
            
            # Pastikan entry2 > entry1 (konservatif harus lebih tinggi dari agresif)
            if entry2 <= entry1:
                entry2 = max(entry1 * 1.001, resistance * 0.999)
            
            # Entry 3: Sangat konservatif - di atas resistance atau Fibonacci 0.236 dari atas (wait for pullback)
            if fib_levels:
                # Fibonacci 0.236 dari atas = resistance - (range * 0.236)
                price_range = resistance - support
                fib_236_from_top = resistance - (price_range * 0.236)
                entry3_option1 = resistance * 1.002  # 0.2% di atas resistance (sangat konservatif)
                entry3_option2 = fib_236_from_top
                # Ambil yang lebih TINGGI (sangat konservatif untuk SHORT = lebih tinggi)
                entry3 = max(entry3_option1, entry3_option2)
            else:
                entry3 = resistance * 1.002  # 0.2% di atas resistance (sangat konservatif)
            
            # Validasi: Pastikan semua entry DI ATAS current price untuk SHORT
            # Entry 1 harus >= current price (agresif = dekat current)
            if entry1 < current_price:
                entry1 = current_price * 1.001  # Force di atas current price
            
            # Entry 2 harus >= entry1 (konservatif = lebih tinggi dari agresif)
            if entry2 < entry1:
                entry2 = entry1 * 1.001  # Force lebih tinggi dari entry1
            
            # Entry 3 harus >= entry2 (sangat konservatif = paling tinggi)
            if entry3 < entry2:
                entry3 = entry2 * 1.001  # Force lebih tinggi dari entry2
        else:
            # Fallback jika tidak ada support/resistance
            # Untuk SHORT: semua entry harus DI ATAS current price
            entry1 = current_price * 1.001  # 0.1% di atas current (agresif)
            entry2 = current_price * 1.002  # 0.2% di atas current (konservatif)
            entry3 = current_price * 1.005  # 0.5% di atas current (sangat konservatif)
        
        # Gunakan entry2 sebagai entry utama (konservatif)
        entry_price = entry2
        
        # Untuk SHORT: TP harus lebih rendah dari SEMUA entry levels
        # Gunakan entry terendah (entry_min) dan tertinggi (entry_max) sebagai referensi
        entry_min = min(entry1, entry2, entry3)
        entry_max = max(entry1, entry2, entry3)
        
        # Stop Loss untuk SHORT: HARUS di ATAS entry (harga naik = loss)
        # Stop Loss = entry + risk_percent
        if resistance is not None:
            # Option 1: Berdasarkan resistance (lebih konservatif)
            sl_based_on_resistance = resistance * 1.005  # 0.5% di atas resistance
            # Option 2: Berdasarkan risk percentage dari entry
            sl_based_on_risk = entry_price * (1 + risk_percent / 100)
            # Ambil yang lebih TINGGI (lebih konservatif untuk SHORT = stop loss lebih tinggi)
            stop_loss = max(sl_based_on_resistance, sl_based_on_risk)
            # Pastikan stop_loss > entry_max (harus di atas semua entry)
            if stop_loss <= entry_max:
                stop_loss = entry_max * (1 + risk_percent / 100)
        else:
            stop_loss = entry_price * (1 + risk_percent / 100)
            # Pastikan stop_loss > entry_max
            if stop_loss <= entry_max:
                stop_loss = entry_max * (1 + risk_percent / 100)
        
        # Calculate risk (distance from entry to stop loss) - untuk SHORT: risk = stop_loss - entry_price
        risk = stop_loss - entry_price
        risk_pct = (risk / entry_price) * 100
        
        # Validasi: Pastikan risk positif (stop_loss > entry_price)
        if risk <= 0:
            print(f"⚠️  [SHORT] Warning: risk <= 0, force stop_loss > entry_max")
            stop_loss = entry_max * (1 + risk_percent / 100)
            risk = stop_loss - entry_price
            risk_pct = (risk / entry_price) * 100
        
        # Take Profit levels (berdasarkan support atau R:R ratio)
        # Untuk SHORT: TP harus lebih RENDAH dari entry (harga turun = profit)
        if support is not None:
            # TP1: Target pertama (berdasarkan multiplier atau 50% ke support)
            # Hitung TP berdasarkan entry_price (entry2) untuk konsistensi
            tp1_option1 = entry_price - (risk * tp_multipliers[0])  # Berdasarkan R:R ratio
            # 50% dari entry ke support = entry - (50% dari jarak entry ke support)
            tp1_option2 = entry_price - ((entry_price - support) * 0.5)  # 50% dari entry ke support
            # Untuk SHORT: ambil yang lebih RENDAH (lebih konservatif untuk TP)
            tp1 = min(tp1_option1, tp1_option2)
            # Validasi: TP1 harus < entry_min untuk memastikan semua entry profit
            if tp1 >= entry_min:
                # Jika TP1 >= entry_min, gunakan entry_min - margin kecil
                tp1 = entry_min * 0.998  # 0.2% di bawah entry terendah
            
            # TP2: Target kedua (berdasarkan multiplier atau 75% ke support)
            tp2_option1 = entry_price - (risk * tp_multipliers[1])
            # 75% dari entry ke support = entry - (75% dari jarak entry ke support)
            tp2_option2 = entry_price - ((entry_price - support) * 0.75)  # 75% dari entry ke support
            # Untuk SHORT: ambil yang lebih RENDAH
            tp2 = min(tp2_option1, tp2_option2)
            # Validasi: TP2 harus < TP1 dan < entry_min
            if tp2 >= tp1 or tp2 >= entry_min:
                tp2 = min(tp1 * 0.998, entry_min * 0.995)  # Lebih rendah dari TP1
            
            # TP3: Target ketiga (berdasarkan multiplier atau support)
            tp3_option1 = entry_price - (risk * tp_multipliers[2])
            # Untuk SHORT: TP3 bisa di support atau sedikit di bawah support
            tp3_option2 = support * 0.998  # 0.2% di bawah support
            tp3 = min(tp3_option1, tp3_option2)
            # Validasi: TP3 harus < TP2 dan < entry_min
            if tp3 >= tp2 or tp3 >= entry_min:
                tp3 = min(tp2 * 0.998, entry_min * 0.992)  # Lebih rendah dari TP2
        else:
            # Jika tidak ada support, gunakan R:R ratio saja
            tp1 = entry_price - (risk * tp_multipliers[0])
            # Validasi: TP1 harus < entry_min
            if tp1 >= entry_min:
                tp1 = entry_min * 0.998
            
            tp2 = entry_price - (risk * tp_multipliers[1])
            # Validasi: TP2 harus < TP1 dan < entry_min
            if tp2 >= tp1 or tp2 >= entry_min:
                tp2 = min(tp1 * 0.998, entry_min * 0.995)
            
            tp3 = entry_price - (risk * tp_multipliers[2])
            # Validasi: TP3 harus < TP2 dan < entry_min
            if tp3 >= tp2 or tp3 >= entry_min:
                tp3 = min(tp2 * 0.998, entry_min * 0.992)
        
        # Final validation: Pastikan semua TP < entry_min dan stop_loss > entry_max
        if tp1 >= entry_min:
            tp1 = entry_min * 0.998
        if tp2 >= tp1:
            tp2 = tp1 * 0.998
        if tp3 >= tp2:
            tp3 = tp2 * 0.998
        if stop_loss <= entry_max:
            stop_loss = entry_max * (1 + risk_percent / 100)
            risk = stop_loss - entry_price
            risk_pct = (risk / entry_price) * 100
    
    return {
        'symbol': symbol,
        'direction': direction,
        'action': action,
        'entry': entry_price,  # Entry utama (entry2)
        'entry1': entry1,      # Entry agresif
        'entry2': entry2,      # Entry konservatif (utama)
        'entry3': entry3,      # Entry sangat konservatif
        'stop_loss': stop_loss,
        'risk_pct': risk_pct,
        'tp1': tp1,
        'tp2': tp2,
        'tp3': tp3
    }

# Generate trading setup jika ada support dan resistance
# Gunakan Multiple Timeframe Analysis jika tersedia untuk konfirmasi signal
mtf_trend_consensus = 0
mtf_alignment_score = 0
mtf_confidence = 0

# Cek multiple timeframe analysis dari market_context
if market_context and 'multiple_timeframe' in market_context:
    mtf_analysis = market_context['multiple_timeframe']
    mtf_trend_consensus = mtf_analysis.get('trend_consensus', 0)
    mtf_alignment_score = mtf_analysis.get('alignment_score', 0)
    mtf_confidence = mtf_analysis.get('confidence', 0)
    
    # Gunakan primary support/resistance dari multiple TF jika tersedia
    mtf_sr = mtf_analysis.get('support_resistance', {})
    if mtf_sr.get('primary_support') and mtf_sr['primary_support'].get('level'):
        # Prioritize higher timeframe support
        mtf_support = mtf_sr['primary_support']['level']
        if last_support is None or mtf_sr['primary_support'].get('strength', 0) > 50:
            last_support = mtf_support
            print(f"💡 Menggunakan Primary Support dari Multiple TF: {mtf_support:.6f} (from {mtf_sr['primary_support'].get('timeframe', 'Unknown')})")
    
    if mtf_sr.get('primary_resistance') and mtf_sr['primary_resistance'].get('level'):
        # Prioritize higher timeframe resistance
        mtf_resistance = mtf_sr['primary_resistance']['level']
        if last_resistance is None or mtf_sr['primary_resistance'].get('strength', 0) > 50:
            last_resistance = mtf_resistance
            print(f"💡 Menggunakan Primary Resistance dari Multiple TF: {mtf_resistance:.6f} (from {mtf_sr['primary_resistance'].get('timeframe', 'Unknown')})")

# ============================================
# LOAD ML PREDICTION SIGNAL (jika ada dari run sebelumnya)
# ============================================
ml_signal_for_setup = None
ml_buy_prob = None
ml_sell_prob = None
ml_signal_strength = None

try:
    # Coba load ML prediction dari file JSON (jika ada dari run sebelumnya)
    import json
    import glob
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    json_file = os.path.join(project_root, "ml_prediction_result.json")
    json_file_current = "ml_prediction_result.json"
    
    json_file_to_check = json_file if os.path.exists(json_file) else (json_file_current if os.path.exists(json_file_current) else None)
    
    if json_file_to_check and os.path.exists(json_file_to_check):
        try:
            with open(json_file_to_check, 'r') as f:
                ml_data = json.load(f)
                ml_signal_raw = ml_data.get('signal', '')
                ml_buy_prob = ml_data.get('buy_probability', ml_data.get('buy_prob', 0))
                ml_sell_prob = ml_data.get('sell_probability', ml_data.get('sell_prob', 0))
                ml_signal_strength = ml_data.get('signal_strength', 'UNKNOWN')
                
                # Convert ML signal to numeric: BELI = 1, JUAL = -1, HOLD = 0
                if ml_signal_raw == "BELI":
                    ml_signal_for_setup = 1
                elif ml_signal_raw == "JUAL":
                    ml_signal_for_setup = -1
                else:
                    ml_signal_for_setup = 0
                
                if ml_signal_for_setup != 0:
                    print(f"📊 ML Prediction Signal ditemukan: {ml_signal_raw} ({ml_buy_prob:.1f}% buy, {ml_sell_prob:.1f}% sell, strength: {ml_signal_strength})")
        except Exception as e:
            print(f"⚠️  Error reading ML prediction for setup: {e}")
            ml_signal_for_setup = None
except Exception as e:
    # ML prediction tidak tersedia, lanjutkan dengan technical signal saja
    pass

# Tentukan signal untuk setup: gunakan last_signal jika ada, atau tentukan berdasarkan posisi harga
# PRIORITAS: Multiple TF > ML Prediction (jika kuat) > Technical Signal > Position-based
if last_support is not None and last_resistance is not None:
    # Pastikan last_support dan last_resistance adalah float
    if not isinstance(last_support, (int, float)):
        last_support = float(last_support) if last_support is not None else None
    if not isinstance(last_resistance, (int, float)):
        last_resistance = float(last_resistance) if last_resistance is not None else None
    
    # MULTIPLE TIMEFRAME CONFIRMATION (PRIORITAS TERTINGGI)
    # Jika multiple TF analysis tersedia, gunakan untuk konfirmasi signal
    if mtf_trend_consensus != 0 and mtf_alignment_score >= 66:
        # Strong alignment dari multiple TF - gunakan consensus
        print(f"✅ Multiple TF Alignment: {mtf_alignment_score:.1f}% - Menggunakan trend consensus: {'BULLISH' if mtf_trend_consensus == 1 else 'BEARISH'}")
        setup_signal = mtf_trend_consensus
    # ML PREDICTION SIGNAL (PRIORITAS KEDUA - jika signal kuat)
    elif ml_signal_for_setup != 0 and ml_signal_strength == "STRONG":
        # ML signal kuat - gunakan ML signal
        setup_signal = ml_signal_for_setup
        print(f"✅ Menggunakan ML Prediction Signal: {'LONG' if setup_signal == 1 else 'SHORT'} (strength: STRONG, {ml_buy_prob:.1f}% buy prob)")
    elif last_signal == 0:
        # Jika signal = 0 (NETRAL), prioritaskan ML signal jika ada, lalu tentukan berdasarkan posisi harga
        if ml_signal_for_setup != 0:
            # Gunakan ML signal jika technical signal netral
            setup_signal = ml_signal_for_setup
            print(f"💡 Technical signal NETRAL - Menggunakan ML Prediction Signal: {'LONG' if setup_signal == 1 else 'SHORT'} ({ml_buy_prob:.1f}% buy prob)")
        else:
            # Tentukan berdasarkan posisi harga relatif terhadap support/resistance
            # Jika harga lebih dekat ke support, bias ke LONG
            # Jika harga lebih dekat ke resistance, bias ke SHORT
            if current_price > 0:
                dist_to_support = abs(current_price - last_support) / current_price
                dist_to_resistance = abs(last_resistance - current_price) / current_price
            else:
                dist_to_support = float('inf')
                dist_to_resistance = float('inf')
            
            if dist_to_support < dist_to_resistance:
                setup_signal = 1  # LONG (harga dekat support, kemungkinan bounce)
            else:
                setup_signal = -1  # SHORT (harga dekat resistance, kemungkinan rejection)
    else:
        # Gunakan last_signal, tapi cek alignment dengan multiple TF dan ML prediction
        if mtf_trend_consensus != 0:
            if last_signal == mtf_trend_consensus:
                print(f"✅ Signal align dengan Multiple TF ({mtf_alignment_score:.1f}% alignment)")
                setup_signal = last_signal
            else:
                print(f"⚠️  Signal conflict dengan Multiple TF - Signal: {last_signal}, MTF Consensus: {mtf_trend_consensus}")
                # Jika alignment score tinggi, prioritaskan multiple TF
                if mtf_alignment_score >= 66:
                    print(f"   💡 Menggunakan Multiple TF consensus karena alignment tinggi")
                    setup_signal = mtf_trend_consensus
                else:
                    # Cek ML prediction sebagai tie-breaker
                    if ml_signal_for_setup != 0 and ml_signal_strength == "STRONG":
                        setup_signal = ml_signal_for_setup
                        print(f"   💡 Menggunakan ML Prediction Signal sebagai tie-breaker: {'LONG' if setup_signal == 1 else 'SHORT'}")
                    else:
                        setup_signal = last_signal
        else:
            # Tidak ada multiple TF, cek ML prediction
            if ml_signal_for_setup != 0 and last_signal != ml_signal_for_setup:
                if ml_signal_strength == "STRONG":
                    # ML signal kuat dan berbeda dengan technical signal - gunakan ML signal
                    setup_signal = ml_signal_for_setup
                    print(f"💡 Technical signal ({'LONG' if last_signal == 1 else 'SHORT' if last_signal == -1 else 'NEUTRAL'}) berbeda dengan ML signal - Menggunakan ML Prediction Signal: {'LONG' if setup_signal == 1 else 'SHORT'} (strength: STRONG)")
                else:
                    # ML signal lemah tapi berbeda dengan technical signal - prioritaskan technical signal tapi beri warning
                    setup_signal = last_signal
                    print(f"⚠️  ML Prediction Signal ({'LONG' if ml_signal_for_setup == 1 else 'SHORT'}, {ml_buy_prob:.1f}% prob, WEAK) berbeda dengan Technical Signal ({'LONG' if last_signal == 1 else 'SHORT' if last_signal == -1 else 'NEUTRAL'})")
                    print(f"   💡 Menggunakan Technical Signal karena ML signal lemah - Pertimbangkan konfirmasi dari AI Strategy")
            else:
                setup_signal = last_signal
    
    # Tentukan risk_percent dan tp_multipliers berdasarkan TRADING_STYLE
    if SETUP_RISK_PERCENT is not None:
        setup_risk = SETUP_RISK_PERCENT
    else:
        # Auto berdasarkan TRADING_STYLE
        risk_config = {
            "SCALPING": 0.75,        # 0.75% risk untuk scalping
            "DAY_TRADING": 2.0,      # 2.0% risk untuk day trading
            "INTRADAY_TRADING": 1.75, # 1.75% risk untuk intraday trading
            "SWING_TRADING": 2.5,    # 2.5% risk untuk swing trading
            "POSITION_TRADING": 3.5  # 3.5% risk untuk position trading
        }
        setup_risk = risk_config.get(TRADING_STYLE, 2.5)
    
    if SETUP_TP_MULTIPLIERS is not None:
        setup_tp_mult = SETUP_TP_MULTIPLIERS
    else:
        # Auto berdasarkan TRADING_STYLE
        tp_config = {
            "SCALPING": [1.2, 1.5, 2.0],        # Target kecil untuk scalping
            "DAY_TRADING": [1.5, 2.5, 3.5],    # Target sedang untuk day trading
            "INTRADAY_TRADING": [1.5, 2.5, 3.5], # Target sedang untuk intraday trading
            "SWING_TRADING": [2.0, 3.0, 5.0],  # Target besar untuk swing trading
            "POSITION_TRADING": [3.0, 5.0, 8.0] # Target sangat besar untuk position trading
        }
        setup_tp_mult = tp_config.get(TRADING_STYLE, [1.5, 2.5, 3.5])
    
    setup = generate_trading_setup(
        symbol=TRADING_SYMBOL,
        current_price=float(current_price),  # Gunakan real-time price
        support=float(last_support),
        resistance=float(last_resistance),
        signal=setup_signal,
        use_limit_entry=True,
        risk_percent=setup_risk,
        tp_multipliers=setup_tp_mult
    )
    
    # Tentukan format angka berdasarkan skala harga
    if setup['entry'] < 1:
        price_format = ".4f"  # 4 desimal untuk harga kecil (< 1)
    elif setup['entry'] < 100:
        price_format = ".4f"  # 4 desimal untuk harga menengah
    elif setup['entry'] < 1000:
        price_format = ".2f"  # 2 desimal untuk harga besar
    else:
        price_format = ".0f"  # 0 desimal untuk harga sangat besar
    
    # Hitung persentase kenaikan/penurunan dari setiap entry level untuk setiap TP
    entry1 = setup['entry1']
    entry2 = setup['entry2']
    entry3 = setup['entry3']
    
    if setup['direction'] == "LONG":
        # TP1
        tp1_pct_e1 = ((setup['tp1'] - entry1) / entry1) * 100
        tp1_pct_e2 = ((setup['tp1'] - entry2) / entry2) * 100
        tp1_pct_e3 = ((setup['tp1'] - entry3) / entry3) * 100
        # TP2
        tp2_pct_e1 = ((setup['tp2'] - entry1) / entry1) * 100
        tp2_pct_e2 = ((setup['tp2'] - entry2) / entry2) * 100
        tp2_pct_e3 = ((setup['tp2'] - entry3) / entry3) * 100
        # TP3
        tp3_pct_e1 = ((setup['tp3'] - entry1) / entry1) * 100
        tp3_pct_e2 = ((setup['tp3'] - entry2) / entry2) * 100
        tp3_pct_e3 = ((setup['tp3'] - entry3) / entry3) * 100
    else:  # SHORT
        # TP1
        tp1_pct_e1 = ((entry1 - setup['tp1']) / entry1) * 100
        tp1_pct_e2 = ((entry2 - setup['tp1']) / entry2) * 100
        tp1_pct_e3 = ((entry3 - setup['tp1']) / entry3) * 100
        # TP2
        tp2_pct_e1 = ((entry1 - setup['tp2']) / entry1) * 100
        tp2_pct_e2 = ((entry2 - setup['tp2']) / entry2) * 100
        tp2_pct_e3 = ((entry3 - setup['tp2']) / entry3) * 100
        # TP3
        tp3_pct_e1 = ((entry1 - setup['tp3']) / entry1) * 100
        tp3_pct_e2 = ((entry2 - setup['tp3']) / entry2) * 100
        tp3_pct_e3 = ((entry3 - setup['tp3']) / entry3) * 100
    
    print("\n" + "=" * 60)
    print(f"{setup['symbol']} LIMIT {setup['action']} SETUP - {setup['direction']}")
    print("=" * 60)
    print()
    print("💰 MULTIPLE ENTRY LEVELS:")
    print(f"   Entry 1 (Agresif): {setup['entry1']:{price_format}}")
    print(f"   Entry 2 (Konservatif - Recommended): {setup['entry2']:{price_format}}")
    print(f"   Entry 3 (Sangat Konservatif): {setup['entry3']:{price_format}}")
    print()
    print(f"🛑 Stop Loss: {setup['stop_loss']:{price_format}} (-{setup['risk_pct']:.2f}%)")
    print()
    print("🎯 TARGETS (dengan persentase untuk setiap Entry Level):")
    print(f"   TP1: {setup['tp1']:{price_format}}")
    print(f"      • Entry 1: {tp1_pct_e1:+.2f}%")
    print(f"      • Entry 2: {tp1_pct_e2:+.2f}%")
    print(f"      • Entry 3: {tp1_pct_e3:+.2f}%")
    print()
    print(f"   TP2: {setup['tp2']:{price_format}}")
    print(f"      • Entry 1: {tp2_pct_e1:+.2f}%")
    print(f"      • Entry 2: {tp2_pct_e2:+.2f}%")
    print(f"      • Entry 3: {tp2_pct_e3:+.2f}%")
    print()
    print(f"   TP3: {setup['tp3']:{price_format}}")
    print(f"      • Entry 1: {tp3_pct_e1:+.2f}%")
    print(f"      • Entry 2: {tp3_pct_e2:+.2f}%")
    print(f"      • Entry 3: {tp3_pct_e3:+.2f}%")
    print()
    print("=" * 60)
    print()
    
    # Hitung Risk/Reward ratio
    if setup['direction'] == "LONG":
        rr1 = (setup['tp1'] - setup['entry']) / (setup['entry'] - setup['stop_loss'])
        rr2 = (setup['tp2'] - setup['entry']) / (setup['entry'] - setup['stop_loss'])
        rr3 = (setup['tp3'] - setup['entry']) / (setup['entry'] - setup['stop_loss'])
    else:
        rr1 = (setup['entry'] - setup['tp1']) / (setup['stop_loss'] - setup['entry'])
        rr2 = (setup['entry'] - setup['tp2']) / (setup['stop_loss'] - setup['entry'])
        rr3 = (setup['entry'] - setup['tp3']) / (setup['stop_loss'] - setup['entry'])
    
    print(f"📊 Risk/Reward Ratio:")
    print(f"   TP1: {rr1:.2f}:1")
    print(f"   TP2: {rr2:.2f}:1")
    print(f"   TP3: {rr3:.2f}:1")
    print()
    print("⚠️  CATATAN: Setup ini hanya contoh berdasarkan analisis teknis.")
    print("   Selalu gunakan risk management dan jangan risk lebih dari 1-2% per trade!")
    print()
else:
    # Jika tidak ada support/resistance, beri tahu user
    print("\n" + "=" * 60)
    print("⚠️  TRADING SETUP TIDAK DAPAT DIBUAT")
    print("=" * 60)
    print("   Alasan: Support dan/atau Resistance belum dihitung")
    print("   Pastikan data memiliki kolom High dan Low untuk perhitungan Support/Resistance")
    print()

print("CROSSOVER (Titik Masuk/Keluar):")
print(f"  - Sinyal BELI (crossover): {crossover_buy} kali")
print(f"  - Sinyal JUAL (crossover): {crossover_sell} kali")
print()
print("📌 PENJELASAN:")
print("  • Posisi BELI/JUAL = jumlah periode dimana strategi berada dalam posisi tersebut")
print("  • Crossover = momen spesifik ketika terjadi perubahan posisi (titik masuk/keluar)")
print("  • Crossover lebih penting untuk eksekusi trading aktual")
print("  • Jika tidak ada sinyal baru setelah tanggal tertentu, berarti posisi masih sama")

# Tampilkan detail sinyal beli/jual (DISABLED - terlalu banyak output)
# Uncomment bagian di bawah jika ingin melihat detail sinyal
buy_signals = data[data['Buy_Signal']]
sell_signals = data[data['Sell_Signal']]

# Detail sinyal BELI - DISABLED untuk mengurangi output terminal
# if len(buy_signals) > 0:
if False:  # Disabled - uncomment untuk enable detail sinyal BELI
    print("\n" + "-" * 50)
    print("SINYAL BELI (Crossover):")
    print("-" * 50)
    # Akses langsung dengan .loc untuk mendapatkan nilai yang benar
    for idx in buy_signals.index:
        # Pastikan idx adalah datetime
        if isinstance(idx, pd.Timestamp):
            date_str = idx.strftime('%Y-%m-%d %H:%M:%S')
        else:
            date_str = str(idx)
        
        # Akses nilai langsung dari DataFrame dengan .loc
        try:
            close_val = buy_signals.loc[idx, 'Close']
            ma_short_val = buy_signals.loc[idx, 'MA_short']
            ma_long_val = buy_signals.loc[idx, 'MA_long']
        except KeyError as e:
            # Jika kolom tidak ditemukan, coba dengan nama alternatif
            print(f"  ⚠️  Kolom tidak ditemukan: {e}")
            continue
        
        # Konversi ke float dan format (handle Series jika ada)
        try:
            if isinstance(close_val, pd.Series):
                close_val = float(close_val.iloc[0]) if len(close_val) > 0 else 0
            elif close_val is None or (isinstance(close_val, float) and pd.isna(close_val)):
                close_val = 0
            else:
                close_val = float(close_val)
        except (TypeError, ValueError):
            close_val = 0
        
        try:
            if isinstance(ma_short_val, pd.Series):
                ma_short_val = float(ma_short_val.iloc[0]) if len(ma_short_val) > 0 else 0
            elif ma_short_val is None or (isinstance(ma_short_val, float) and pd.isna(ma_short_val)):
                ma_short_val = 0
            else:
                ma_short_val = float(ma_short_val)
        except (TypeError, ValueError):
            ma_short_val = 0
        
        try:
            if isinstance(ma_long_val, pd.Series):
                ma_long_val = float(ma_long_val.iloc[0]) if len(ma_long_val) > 0 else 0
            elif ma_long_val is None or (isinstance(ma_long_val, float) and pd.isna(ma_long_val)):
                ma_long_val = 0
            else:
                ma_long_val = float(ma_long_val)
        except (TypeError, ValueError):
            ma_long_val = 0
        
        # print(f"  {date_str} - Harga: {close_val:,.0f} | "
        #       f"MA Short: {ma_short_val:,.0f} | MA Long: {ma_long_val:,.0f}")
# else:
#     print("\nTidak ada sinyal BELI (crossover) ditemukan")

# Detail sinyal JUAL - DISABLED untuk mengurangi output terminal
# if len(sell_signals) > 0:
if False:  # Disabled - uncomment untuk enable detail sinyal JUAL
    print("\n" + "-" * 50)
    print("SINYAL JUAL (Crossover):")
    print("-" * 50)
    # Akses langsung dengan .loc untuk mendapatkan nilai yang benar
    for idx in sell_signals.index:
        # Pastikan idx adalah datetime
        if isinstance(idx, pd.Timestamp):
            date_str = idx.strftime('%Y-%m-%d %H:%M:%S')
        else:
            date_str = str(idx)
        
        # Akses nilai langsung dari DataFrame dengan .loc
        try:
            close_val = sell_signals.loc[idx, 'Close']
            ma_short_val = sell_signals.loc[idx, 'MA_short']
            ma_long_val = sell_signals.loc[idx, 'MA_long']
        except KeyError as e:
            # Jika kolom tidak ditemukan, coba dengan nama alternatif
            print(f"  ⚠️  Kolom tidak ditemukan: {e}")
            continue
        
        # Konversi ke float dan format (handle Series jika ada)
        try:
            if isinstance(close_val, pd.Series):
                close_val = float(close_val.iloc[0]) if len(close_val) > 0 else 0
            elif close_val is None or (isinstance(close_val, float) and pd.isna(close_val)):
                close_val = 0
            else:
                close_val = float(close_val)
        except (TypeError, ValueError):
            close_val = 0
        
        try:
            if isinstance(ma_short_val, pd.Series):
                ma_short_val = float(ma_short_val.iloc[0]) if len(ma_short_val) > 0 else 0
            elif ma_short_val is None or (isinstance(ma_short_val, float) and pd.isna(ma_short_val)):
                ma_short_val = 0
            else:
                ma_short_val = float(ma_short_val)
        except (TypeError, ValueError):
            ma_short_val = 0
        
        try:
            if isinstance(ma_long_val, pd.Series):
                ma_long_val = float(ma_long_val.iloc[0]) if len(ma_long_val) > 0 else 0
            elif ma_long_val is None or (isinstance(ma_long_val, float) and pd.isna(ma_long_val)):
                ma_long_val = 0
            else:
                ma_long_val = float(ma_long_val)
        except (TypeError, ValueError):
            ma_long_val = 0
        
        print(f"  {date_str} - Harga: {close_val:,.0f} | "
              f"MA Short: {ma_short_val:,.0f} | MA Long: {ma_long_val:,.0f}")
else:
    print("\nTidak ada sinyal JUAL (crossover) ditemukan")

# 6️⃣ Visualisasi hasil
fig, axes = plt.subplots(3, 1, figsize=(14, 10))

# Plot 1: Harga dan Moving Average dengan Sinyal + Support/Resistance
axes[0].plot(data.index, data['Close'], label='Harga Close', alpha=0.7, linewidth=1, color='blue')
axes[0].plot(data.index, data['MA_short'], label=f'MA Short ({ma_short_window})', linewidth=1.5, color='orange')
axes[0].plot(data.index, data['MA_long'], label=f'MA Long ({ma_long_window})', linewidth=1.5, color='green')

# Tambahkan Support dan Resistance
if 'Support' in data.columns and data['Support'].notna().any():
    axes[0].plot(data.index, data['Support'], label='Support', linewidth=1.5, 
                 color='red', linestyle='--', alpha=0.6)
    # Fill area di bawah support
    axes[0].fill_between(data.index, data['Support'].min(), data['Support'], 
                        alpha=0.1, color='red', label='Support Zone')
    
if 'Resistance' in data.columns and data['Resistance'].notna().any():
    axes[0].plot(data.index, data['Resistance'], label='Resistance', linewidth=1.5, 
                 color='purple', linestyle='--', alpha=0.6)
    # Fill area di atas resistance
    axes[0].fill_between(data.index, data['Resistance'], data['Resistance'].max(), 
                        alpha=0.1, color='purple', label='Resistance Zone')

# Tandai sinyal beli (hijau, panah ke atas)
if len(buy_signals) > 0:
    axes[0].scatter(buy_signals.index, buy_signals['Close'], 
                   color='green', marker='^', s=100, zorder=5, 
                   label=f'Sinyal Beli ({len(buy_signals)})', edgecolors='darkgreen', linewidths=1.5)

# Tandai sinyal jual (merah, panah ke bawah)
if len(sell_signals) > 0:
    axes[0].scatter(sell_signals.index, sell_signals['Close'], 
                   color='red', marker='v', s=100, zorder=5, 
                   label=f'Sinyal Jual ({len(sell_signals)})', edgecolors='darkred', linewidths=1.5)

axes[0].set_title('Harga, Moving Average, dan Sinyal Trading')
axes[0].set_ylabel('Harga')
axes[0].legend(loc='best')
axes[0].grid(True, alpha=0.3)

# Plot 2: Sinyal Trading (untuk melihat posisi)
axes[1].plot(data.index, data['Signal'], label='Sinyal', linewidth=2, color='purple', alpha=0.7)
axes[1].fill_between(data.index, 0, data['Signal'], where=(data['Signal'] > 0), 
                     alpha=0.3, color='green', label='Posisi Beli')
axes[1].fill_between(data.index, 0, data['Signal'], where=(data['Signal'] < 0), 
                     alpha=0.3, color='red', label='Posisi Jual')
axes[1].axhline(y=0, color='black', linestyle='--', linewidth=0.5)
axes[1].set_title('Posisi Trading (1 = Beli, -1 = Jual, 0 = Netral)')
axes[1].set_ylabel('Sinyal')
axes[1].set_ylim(-1.5, 1.5)
axes[1].legend(loc='best')
axes[1].grid(True, alpha=0.3)

# Plot 3: Cumulative Return
axes[2].plot(data.index, data['Cumulative_BuyHold'], label='Buy & Hold', linewidth=2, color='blue')
axes[2].plot(data.index, data['Cumulative_Strategy'], label='Quant Strategy', linewidth=2, color='orange')
axes[2].set_title('Perbandingan Return: Buy & Hold vs Strategi')
axes[2].set_ylabel('Cumulative Return')
axes[2].set_xlabel('Waktu')
axes[2].legend(loc='best')
axes[2].grid(True, alpha=0.3)

plt.tight_layout()

# Simpan chart sebagai file PNG untuk dikirim ke Telegram
chart_filename = None
try:
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    chart_filename = f"trading_chart_{timestamp}.png"
    plt.savefig(chart_filename, dpi=150, bbox_inches='tight')
    print(f"📊 Chart disimpan: {chart_filename}")
except Exception as e:
    print(f"⚠️  Error menyimpan chart: {e}")

# ============================================
# ENHANCED FEATURES OUTPUT
# ============================================
enhanced_metrics = {}
if USE_ENHANCED_FEATURES:
    # Print volume analysis summary
    print_volume_analysis_summary(data)
    
    # Print market context
    if market_context:
        print_market_context(market_context)
    
    # Print advanced features summary
    print_advanced_features_summary(data)
    
    # Calculate and print enhanced validation metrics
    enhanced_metrics = calculate_enhanced_validation_metrics(data)
    if enhanced_metrics:
        print_enhanced_metrics(enhanced_metrics)
    
    # Run enhanced backtesting (Monte Carlo + Transaction Costs)
    try:
        from src.backtesting.enhanced_backtesting import run_enhanced_backtest, print_backtest_results
        backtest_results = run_enhanced_backtest(data, commission_pct=0.001, slippage_pct=0.0005, num_simulations=1000)
        print_backtest_results(backtest_results)
    except ImportError:
        print("ℹ️  Enhanced backtesting tidak tersedia")
    except Exception as e:
        print(f"⚠️  Error dalam enhanced backtesting: {e}")
    
    # Run time series analysis (ARIMA + GARCH)
    try:
        from src.utils.config import ENABLE_TIME_SERIES_MODELS
        if ENABLE_TIME_SERIES_MODELS:
            from src.models.time_series_models import analyze_time_series, print_time_series_results
            ts_results = analyze_time_series(data)
            print_time_series_results(ts_results)
        else:
            print("ℹ️  Time series models dinonaktifkan di config.py (ENABLE_TIME_SERIES_MODELS = False)")
    except ImportError:
        print("ℹ️  Time series models tidak tersedia")
    except Exception as e:
        print(f"⚠️  Error dalam time series analysis: {e}")
    
    # ============================================
    # ADVANCED TRADING STRATEGIES
    # ============================================
    try:
        from src.utils.config import (
            ENABLE_PAIRS_TRADING, ENABLE_STATISTICAL_ARBITRAGE,
            ENABLE_GRID_TRADING, ENABLE_DCA,
            ENABLE_MULTI_STRATEGY_PORTFOLIO,
            PAIRS_ENTRY_THRESHOLD, PAIRS_EXIT_THRESHOLD, PAIRS_STOP_LOSS_PCT,
            STAT_ARB_ENTRY_THRESHOLD, STAT_ARB_EXIT_THRESHOLD, STAT_ARB_MIN_CORRELATION,
            GRID_LEVELS, GRID_SPACING_PCT,
            DCA_INVESTMENT_AMOUNT, DCA_FREQUENCY,
            PORTFOLIO_SELECTION_METHOD, PORTFOLIO_WEIGHTING_METHOD,
            PORTFOLIO_TOP_N, PORTFOLIO_PERFORMANCE_WINDOW
        )
        
        strategy_results = {}
        
        # Pairs Trading (requires 2 assets - skip if only 1 asset available)
        if ENABLE_PAIRS_TRADING:
            try:
                from src.strategies.advanced_strategies import pairs_trading_strategy, print_strategy_results
                from src.utils.config import PAIRS_LONG_ONLY
                # Note: Pairs trading requires 2 assets, so we'll skip for now
                # In production, you would load data for a second asset
                print(f"ℹ️  Pairs Trading: Requires 2 assets. Skipping for single-asset analysis.")
                print(f"   Mode: {'Long-Only (Spot Trading)' if PAIRS_LONG_ONLY else 'Long-Short (Futures)'}")
            except ImportError:
                print("ℹ️  Advanced strategies tidak tersedia")
            except Exception as e:
                print(f"⚠️  Error dalam pairs trading: {e}")
        
        # Statistical Arbitrage (requires multiple assets - skip if only 1 asset)
        if ENABLE_STATISTICAL_ARBITRAGE:
            try:
                from src.strategies.advanced_strategies import statistical_arbitrage_strategy, print_strategy_results
                from src.utils.config import STAT_ARB_LONG_ONLY
                # Note: Statistical arbitrage requires multiple assets
                print(f"ℹ️  Statistical Arbitrage: Requires multiple assets. Skipping for single-asset analysis.")
                print(f"   Mode: {'Long-Only (Spot Trading)' if STAT_ARB_LONG_ONLY else 'Long-Short (Futures)'}")
            except ImportError:
                print("ℹ️  Advanced strategies tidak tersedia")
            except Exception as e:
                print(f"⚠️  Error dalam statistical arbitrage: {e}")
        
        # Grid Trading
        if ENABLE_GRID_TRADING:
            try:
                from src.strategies.advanced_strategies import grid_trading_strategy, print_strategy_results
                grid_results = grid_trading_strategy(
                    data['Close'],
                    grid_levels=GRID_LEVELS,
                    grid_spacing_pct=GRID_SPACING_PCT
                )
                if grid_results:
                    strategy_results['Grid Trading'] = grid_results
                    print_strategy_results(grid_results)
            except ImportError:
                print("ℹ️  Advanced strategies tidak tersedia")
            except Exception as e:
                print(f"⚠️  Error dalam grid trading: {e}")
        
        # Dollar Cost Averaging (DCA)
        if ENABLE_DCA:
            try:
                from src.strategies.advanced_strategies import dca_strategy, print_strategy_results
                dca_results = dca_strategy(
                    data['Close'],
                    investment_amount=DCA_INVESTMENT_AMOUNT,
                    frequency=DCA_FREQUENCY
                )
                if dca_results:
                    strategy_results['DCA'] = dca_results
                    print_strategy_results(dca_results)
            except ImportError:
                print("ℹ️  Advanced strategies tidak tersedia")
            except Exception as e:
                print(f"⚠️  Error dalam DCA: {e}")
        
        # Multi-Strategy Portfolio
        if ENABLE_MULTI_STRATEGY_PORTFOLIO and len(strategy_results) > 0:
            try:
                from src.strategies.strategy_portfolio import (
                    dynamic_strategy_selection,
                    calculate_strategy_weights,
                    combine_strategies,
                    print_portfolio_results
                )
                
                # Add base MA strategy to portfolio
                if 'Strategy_Return' in data.columns:
                    base_strategy = {
                        'strategy_name': 'MA Crossover',
                        'strategy_return': data['Strategy_Return']
                    }
                    strategy_results['MA Crossover'] = base_strategy
                
                # Select best strategies
                selected = dynamic_strategy_selection(
                    strategy_results,
                    selection_method=PORTFOLIO_SELECTION_METHOD,
                    top_n=PORTFOLIO_TOP_N
                )
                
                # Calculate weights
                weights = calculate_strategy_weights(
                    strategy_results,
                    weighting_method=PORTFOLIO_WEIGHTING_METHOD,
                    performance_window=PORTFOLIO_PERFORMANCE_WINDOW
                )
                
                # Combine strategies
                portfolio_results = combine_strategies(
                    strategy_results,
                    weights=weights,
                    selected_strategies=selected
                )
                
                if portfolio_results:
                    print_portfolio_results(portfolio_results)
            except ImportError:
                print("ℹ️  Strategy portfolio tidak tersedia")
            except Exception as e:
                print(f"⚠️  Error dalam multi-strategy portfolio: {e}")
        
    except ImportError:
        print("ℹ️  Advanced strategies configuration tidak tersedia")
    except Exception as e:
        print(f"⚠️  Error dalam advanced strategies: {e}")
    
    # ============================================
    # DERIVATIVES MODELING (Optional)
    # ============================================
    try:
        from src.utils.config import (
            ENABLE_DERIVATIVES_MODELING, ENABLE_OPTIONS_STRATEGIES,
            RISK_FREE_RATE, DEFAULT_VOLATILITY, OPTIONS_CONTRACTS
        )
        
        if ENABLE_DERIVATIVES_MODELING:
            try:
                from src.models.derivatives_modeling import (
                    black_scholes_price, calculate_greeks,
                    covered_call_strategy, protective_put_strategy,
                    straddle_strategy, print_derivatives_results
                )
                
                # Example: Calculate option prices and Greeks for current price
                current_price = float(data['Close'].iloc[-1])
                strike_price = current_price  # At-the-money
                time_to_expiry = 30 / 365  # 30 days
                
                print("\n" + "=" * 70)
                print("📊 DERIVATIVES MODELING (Example)")
                print("=" * 70)
                print(f"\n💰 Current Price: ${current_price:.2f}")
                print(f"🎯 Strike Price: ${strike_price:.2f} (ATM)")
                print(f"⏰ Time to Expiry: {time_to_expiry*365:.0f} days")
                print(f"📈 Volatility: {DEFAULT_VOLATILITY*100:.1f}%")
                print(f"💵 Risk-Free Rate: {RISK_FREE_RATE*100:.1f}%")
                
                # Calculate option prices
                call_price = black_scholes_price(
                    current_price, strike_price, time_to_expiry,
                    RISK_FREE_RATE, DEFAULT_VOLATILITY, 'call'
                )
                put_price = black_scholes_price(
                    current_price, strike_price, time_to_expiry,
                    RISK_FREE_RATE, DEFAULT_VOLATILITY, 'put'
                )
                
                print(f"\n📊 Option Prices:")
                print(f"   Call: ${call_price:.2f}")
                print(f"   Put: ${put_price:.2f}")
                
                # Calculate Greeks
                call_greeks = calculate_greeks(
                    current_price, strike_price, time_to_expiry,
                    RISK_FREE_RATE, DEFAULT_VOLATILITY, 'call'
                )
                
                print(f"\n📈 Call Greeks:")
                print(f"   Delta: {call_greeks['delta']:.4f}")
                print(f"   Gamma: {call_greeks['gamma']:.6f}")
                print(f"   Theta: {call_greeks['theta']:.4f} (per day)")
                print(f"   Vega: {call_greeks['vega']:.4f} (per 1% vol)")
                print(f"   Rho: {call_greeks['rho']:.4f} (per 1% rate)")
                
                # Options Strategies (if enabled)
                if ENABLE_OPTIONS_STRATEGIES:
                    print(f"\n📊 Options Strategies:")
                    
                    # Covered Call
                    covered_call = covered_call_strategy(
                        current_price, strike_price, time_to_expiry,
                        RISK_FREE_RATE, DEFAULT_VOLATILITY, OPTIONS_CONTRACTS * 100
                    )
                    print_derivatives_results(covered_call)
                    
                    # Protective Put
                    protective_put = protective_put_strategy(
                        current_price, strike_price, time_to_expiry,
                        RISK_FREE_RATE, DEFAULT_VOLATILITY, OPTIONS_CONTRACTS * 100
                    )
                    print_derivatives_results(protective_put)
                    
                    # Straddle
                    straddle = straddle_strategy(
                        current_price, strike_price, time_to_expiry,
                        RISK_FREE_RATE, DEFAULT_VOLATILITY, OPTIONS_CONTRACTS
                    )
                    print_derivatives_results(straddle)
                
                print("\n" + "=" * 70)
                
            except ImportError:
                print("ℹ️  Derivatives modeling tidak tersedia")
            except Exception as e:
                print(f"⚠️  Error dalam derivatives modeling: {e}")
    except ImportError:
        pass  # Config tidak tersedia, skip
    except Exception as e:
        print(f"⚠️  Error dalam derivatives modeling config: {e}")

# Store analysis data for DeepSeek (will be used after ML prediction)
analysis_data_for_deepseek = None

# ============================================
# OPSI: Jalankan prediksi SEBELUM menampilkan chart
# (Karena plt.show() akan memblokir eksekusi)
# ============================================
print("\n" + "=" * 70, flush=True)
print("🔍 [PREDICTION CHECK] Checking RUN_PREDICTION configuration...", flush=True)
print("=" * 70, flush=True)
print(f"   RUN_PREDICTION value: {RUN_PREDICTION}", flush=True)
print(f"   RUN_PREDICTION type: {type(RUN_PREDICTION)}", flush=True)
print(f"   RUN_PREDICTION is True: {RUN_PREDICTION is True}", flush=True)
print(f"   RUN_PREDICTION == True: {RUN_PREDICTION == True}", flush=True)
print(f"   bool(RUN_PREDICTION): {bool(RUN_PREDICTION)}", flush=True)
print("=" * 70, flush=True)

# Force flush before if statement
import sys
sys.stdout.flush()

if RUN_PREDICTION:
    print("✅ [PREDICTION CHECK] RUN_PREDICTION is True - WILL EXECUTE PREDICTION", flush=True)
    sys.stdout.flush()
    
    print("\n" + "=" * 60, flush=True)
    print("🚀 LANJUT KE PREDIKSI HARI BERIKUTNYA (MASA DEPAN)", flush=True)
    print("=" * 60, flush=True)
    print(flush=True)
    sys.stdout.flush()
    
    try:
        # Import dan jalankan prediksi secara langsung
        import subprocess
        import sys
        
        # Simpan nama CSV file sebelum menjalankan prediksi
        # (prediksi_next_day.py juga akan menggunakan file CSV yang sama)
        csv_file_for_prediction = used_csv_file if 'used_csv_file' in globals() and used_csv_file else None
        
        # Debug: Pastikan CSV file masih ada sebelum menjalankan prediksi
        print(f"🔍 [DEBUG] Before running prediksi_next_day.py:")
        if csv_file_for_prediction:
            print(f"   CSV file untuk prediksi: {csv_file_for_prediction}")
            if os.path.exists(csv_file_for_prediction):
                print(f"   ✅ CSV file exists: {os.path.getsize(csv_file_for_prediction):,} bytes")
            else:
                print(f"   ❌ ERROR: CSV file tidak ditemukan: {csv_file_for_prediction}")
                # Cari file CSV terbaru sebagai fallback
                import glob
                csv_files = glob.glob("*_historical_*.csv")
                if csv_files:
                    csv_file_for_prediction = max(csv_files, key=os.path.getmtime)
                    print(f"   🔄 Fallback: Menggunakan file terbaru: {csv_file_for_prediction}")
                else:
                    print(f"   ❌ ERROR: Tidak ada file CSV historical ditemukan!")
        else:
            # Cari file CSV terbaru
            import glob
            csv_files = glob.glob("*_historical_*.csv")
            if csv_files:
                csv_file_for_prediction = max(csv_files, key=os.path.getmtime)
                print(f"   📁 Found CSV file: {csv_file_for_prediction}")
            else:
                print(f"   ⚠️  WARNING: Tidak ada CSV file ditemukan untuk prediksi!")
        
        # Jalankan dengan output real-time
        print(f"🚀 [PREDICTION] Running prediksi_next_day.py...", flush=True)
        print(f"   Working directory: {os.getcwd()}", flush=True)
        print(f"   CSV file should be: {csv_file_for_prediction}", flush=True)
        sys.stdout.flush()
        
        # Capture output untuk debugging jika error
        # File prediksi_next_day.py ada di src/, bukan di root
        prediksi_script = "src/prediksi_next_day.py"
        if not os.path.exists(prediksi_script):
            # Fallback: coba cari di current directory
            if os.path.exists("prediksi_next_day.py"):
                prediksi_script = "prediksi_next_day.py"
            else:
                print(f"❌ [PREDICTION ERROR] File prediksi_next_day.py tidak ditemukan!", flush=True)
                print(f"   Mencari di: {os.path.abspath(prediksi_script)}", flush=True)
                print(f"   Current directory: {os.getcwd()}", flush=True)
                sys.stdout.flush()
                raise FileNotFoundError(f"prediksi_next_day.py tidak ditemukan di {prediksi_script} atau current directory")
        
        print(f"   📄 Using script: {prediksi_script}", flush=True)
        sys.stdout.flush()
        
        result = subprocess.run(
            [sys.executable, prediksi_script],
            check=False,
            stdout=subprocess.PIPE,  # Capture stdout untuk debugging
            stderr=subprocess.PIPE,   # Capture stderr untuk debugging
            text=True
        )
        print(f"🔍 [PREDICTION] prediksi_next_day.py completed with returncode: {result.returncode}", flush=True)
        
        # Jika error, tampilkan error output
        if result.returncode != 0:
            print(f"\n❌ [PREDICTION ERROR] prediksi_next_day.py failed with returncode: {result.returncode}", flush=True)
            if result.stderr:
                print(f"   📋 Error output (stderr):", flush=True)
                error_lines = result.stderr.split('\n')
                for line in error_lines[-20:]:  # Last 20 lines
                    if line.strip():
                        print(f"      {line}", flush=True)
            if result.stdout:
                print(f"   📋 Standard output (stdout):", flush=True)
                stdout_lines = result.stdout.split('\n')
                for line in stdout_lines[-20:]:  # Last 20 lines
                    if line.strip():
                        print(f"      {line}", flush=True)
            print(f"   💡 File ml_prediction_result.json TIDAK AKAN dibuat karena error di atas", flush=True)
        else:
            print(f"✅ [PREDICTION] prediksi_next_day.py completed successfully", flush=True)
        
        sys.stdout.flush()
        
        # Tunggu sebentar untuk memastikan file ml_prediction_result.json sudah ter-write
        import time
        time.sleep(1.0)  # Increase delay untuk memastikan file ter-write
        
        # Verifikasi file JSON sudah terbuat (di project root)
        # Get project root
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(script_dir))
        json_file = os.path.join(project_root, "ml_prediction_result.json")
        json_file_current = "ml_prediction_result.json"  # Fallback: current directory
        
        print(f"🔍 [DEBUG] Looking for ml_prediction_result.json:")
        print(f"   Project root path: {json_file}")
        print(f"   Current directory path: {json_file_current}")
        print(f"   Current working directory: {os.getcwd()}")
        
        # Cek di project root dulu, lalu current directory
        json_file_to_check = json_file if os.path.exists(json_file) else (json_file_current if os.path.exists(json_file_current) else None)
        
        if json_file_to_check and os.path.exists(json_file_to_check):
            print(f"✅ File ml_prediction_result.json ditemukan di: {json_file_to_check}")
            try:
                import json
                with open(json_file_to_check, 'r') as f:
                    ml_data = json.load(f)
                    print(f"   📊 ML Results: accuracy={ml_data.get('accuracy')}, sharpe={ml_data.get('sharpe_ratio')}, expected_value={ml_data.get('expected_value')}")
            except Exception as e:
                print(f"   ⚠️  Error reading JSON: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"⚠️  File ml_prediction_result.json belum terbuat")
            print(f"   Checked paths:")
            print(f"   - {json_file} (exists: {os.path.exists(json_file)})")
            print(f"   - {json_file_current} (exists: {os.path.exists(json_file_current)})")
        
        if result.returncode != 0:
            print(f"\n⚠️  Prediksi mengalami error (returncode={result.returncode}), tapi analisis strategi sudah selesai")
            print("   💡 File ml_prediction_result.json mungkin tidak dibuat karena error")
        else:
            print("\n" + "=" * 60)
            print("✅ PREDIKSI SELESAI - Lihat output di atas untuk signal BELI/JUAL masa depan")
            print("=" * 60)
            print(f"   📊 Returncode: {result.returncode}")
            print(f"   📁 File JSON seharusnya sudah dibuat di: {json_file} atau {json_file_current}")
        
        # ============================================
        # DEEPSEEK AI INTEGRATION (After ML Prediction)
        # ============================================
        try:
            from src.utils.config import ENABLE_DEEPSEEK_AI, DEEPSEEK_API_KEY, DEEPSEEK_MODEL
            from src.integration.deepseek_integration import DeepSeekTradingAdvisor, format_recommendation_output
            from src.data.collect_analysis_data import collect_analysis_data, add_trading_setup_to_analysis
            
            if ENABLE_DEEPSEEK_AI and DEEPSEEK_API_KEY:
                # ============================================
                # FILTER BERDASARKAN ML METRICS (Hemat Token DeepSeek)
                # ============================================
                # Baca ML prediction result untuk filter sebelum kirim ke DeepSeek
                ml_result_for_filter = None
                json_file_to_check = json_file if os.path.exists(json_file) else (json_file_current if os.path.exists(json_file_current) else None)
                
                if json_file_to_check and os.path.exists(json_file_to_check):
                    try:
                        import json
                        with open(json_file_to_check, 'r') as f:
                            ml_result_for_filter = json.load(f)
                    except Exception as e:
                        print(f"⚠️  Error reading ML result for filter: {e}")
                
                # Fungsi filter: cek apakah metrics bagus
                def should_send_to_deepseek(ml_result) -> bool:
                    """
                    Filter coin berdasarkan ML metrics sebelum kirim ke DeepSeek
                    Hanya kirim jika metrics bagus untuk hemat token
                    
                    Criteria (Fleksibel - konsisten dengan filter di analyze_screened_coins.py):
                    - Minimal 2 dari 3 metrik harus memenuhi:
                      - Accuracy >= 50%
                      - Sharpe Ratio >= 0.5
                      - Expected Value >= 0%
                    - Atau semua 3 metrik memenuhi kriteria ketat:
                      - Accuracy >= 50%
                      - Sharpe Ratio >= 0.5
                      - Expected Value > 0%
                    
                    Returns:
                    - True jika metrics bagus, False jika tidak
                    """
                    if ml_result is None:
                        # Jika tidak ada ML result, tetap kirim (fallback)
                        print("   ⚠️  ML result tidak ditemukan, tetap kirim ke DeepSeek")
                        return True
                    
                    accuracy = ml_result.get('accuracy')
                    sharpe = ml_result.get('sharpe_ratio')
                    expected_value = ml_result.get('expected_value')
                    
                    # Validasi nilai
                    if accuracy is None or sharpe is None or expected_value is None:
                        print("   ⚠️  ML metrics tidak lengkap, tetap kirim ke DeepSeek")
                        return True
                    
                    try:
                        accuracy = float(accuracy)
                        sharpe = float(sharpe)
                        expected_value = float(expected_value)
                    except (TypeError, ValueError):
                        print("   ⚠️  ML metrics tidak valid, tetap kirim ke DeepSeek")
                        return True
                    
                    # Filter criteria (fleksibel - konsisten dengan analyze_screened_coins.py)
                    min_accuracy_relaxed = 50.0  # Threshold lebih rendah
                    min_sharpe_relaxed = 0.5     # Threshold lebih rendah
                    min_expected_value_relaxed = 0.0  # Boleh 0 atau positif
                    
                    # Kriteria ketat (jika semua memenuhi, pasti lolos)
                    min_accuracy_strict = 50.0
                    min_sharpe_strict = 0.5
                    min_expected_value_strict = 0.0
                    
                    # Cek kriteria ketat (semua harus memenuhi)
                    meets_strict = (
                        accuracy >= min_accuracy_strict and
                        sharpe >= min_sharpe_strict and
                        expected_value > min_expected_value_strict
                    )
                    
                    # Cek kriteria fleksibel (minimal 2 dari 3 harus memenuhi)
                    meets_accuracy = accuracy >= min_accuracy_relaxed
                    meets_sharpe = sharpe >= min_sharpe_relaxed
                    meets_expected = expected_value >= min_expected_value_relaxed
                    
                    score = sum([meets_accuracy, meets_sharpe, meets_expected])
                    meets_criteria = meets_strict or score >= 2
                    
                    if meets_criteria:
                        criteria_type = "STRICT" if meets_strict else "FLEXIBLE"
                        print(f"   ✅ Metrics bagus [{criteria_type}]: Accuracy={accuracy:.1f}%, Sharpe={sharpe:.2f}, EV={expected_value:.2f}% (Score: {score}/3)")
                        print("   ✅ Coin memenuhi kriteria, akan dikirim ke DeepSeek")
                        return True
                    else:
                        print(f"   ❌ Metrics tidak memenuhi kriteria (Score: {score}/3):")
                        print(f"      - Accuracy: {accuracy:.1f}% (min: {min_accuracy_relaxed}%) {'✅' if meets_accuracy else '❌'}")
                        print(f"      - Sharpe: {sharpe:.2f} (min: {min_sharpe_relaxed}) {'✅' if meets_sharpe else '❌'}")
                        print(f"      - Expected Value: {expected_value:.2f}% (min: {min_expected_value_relaxed}%) {'✅' if meets_expected else '❌'}")
                        print("   ⏭️  Skip DeepSeek untuk hemat token (coin ini tidak akan dapat AI recommendation)")
                        return False
                
                # Cek apakah coin memenuhi kriteria
                # Deteksi apakah ini batch request atau single coin request
                is_batch_request = os.environ.get('RUN_FROM_MASTER_SCRIPT') == '1'
                
                should_send = should_send_to_deepseek(ml_result_for_filter)
                
                # Untuk batch request (/analyze), SKIP AI di sini
                # AI akan dipanggil SETELAH filter di analyze_screened_coins.py
                # Ini untuk hemat token - hanya coin yang lolos kriteria ketat yang dapat AI recommendation
                if is_batch_request:
                    if not should_send:
                        print("\n" + "=" * 70)
                        print("⏭️  SKIP DEEPSEEK AI (Batch Request)")
                        print("=" * 70)
                        print("💡 Ini adalah batch request (/analyze)")
                        print("   AI akan dipanggil SETELAH coin lolos filter ketat di analyze_screened_coins.py")
                        print("   Ini untuk hemat token - hanya coin yang memenuhi semua kriteria yang dapat AI recommendation")
                        # Skip AI untuk batch request
                        should_send = False
                    else:
                        print("\n" + "=" * 70)
                        print("⚠️  Batch Request Detected - AI akan dipanggil setelah filter")
                        print("=" * 70)
                        print("💡 Meskipun metrics bagus, untuk batch request:")
                        print("   AI akan dipanggil SETELAH coin lolos semua kriteria ketat (ML + Backtesting)")
                        print("   Ini untuk memastikan hanya coin terbaik yang dapat AI recommendation")
                        # Tetap skip untuk batch request - AI akan dipanggil setelah filter
                        should_send = False
                else:
                    # Untuk single coin request, selalu kirim ke DeepSeek dan Telegram (tidak ada filter)
                    # Filter/threshold hanya berlaku untuk batch request di analyze_screened_coins.py
                    if not should_send:
                        print("\n" + "=" * 70)
                        print("⚠️  Metrics tidak memenuhi kriteria, tapi tetap lanjutkan (single coin request)")
                        print("=" * 70)
                        print("💡 Untuk single coin request, semua hasil akan dikirim ke Telegram dan DeepSeek")
                        print("   Filter/threshold hanya berlaku untuk batch request (/analyze)")
                        # Tetap lanjutkan ke DeepSeek dan Telegram (tidak skip)
                        should_send = True  # Override untuk single coin request
                
                # Lanjutkan ke DeepSeek AI (untuk single coin request, selalu True)
                if should_send:
                    print("\n" + "=" * 70)
                    print("🤖 MENGIRIM DATA KE DEEPSEEK AI...")
                    print("=" * 70)
                    
                    # Get recent trades analysis (untuk market aggression & momentum)
                    recent_trades_analysis = None
                    try:
                        from src.data.binance_futures_data import get_futures_recent_trades, analyze_recent_trades
                        
                        # Convert symbol format: BTC-USD -> BTCUSDT atau langsung gunakan SYMBOL
                        binance_symbol = SYMBOL.replace('-USD', 'USDT').replace('-', '') if SYMBOL else None
                        
                        if binance_symbol:
                            print(f"📊 Mengambil recent trades untuk {binance_symbol}...")
                            trades = get_futures_recent_trades(
                                symbol=binance_symbol,
                                limit=500,  # Ambil 500 recent trades untuk akurasi lebih baik
                                testnet=False
                            )
                            
                            if trades:
                                recent_trades_analysis = analyze_recent_trades(trades)
                                print(f"✅ Recent trades analysis ditemukan")
                                print(f"   Market Aggression: {recent_trades_analysis['market_aggression']:.1f}/100")
                                print(f"   Buyer Dominance: {recent_trades_analysis['buyer_dominance']:.1f}%")
                                print(f"   Momentum: {recent_trades_analysis['momentum']:+.2f}%")
                            else:
                                print(f"⚠️  Recent trades tidak ditemukan untuk {binance_symbol}")
                    except Exception as e:
                        print(f"⚠️  Error mengambil recent trades: {e}")
                        # Continue tanpa recent trades analysis
                    
                    # Get Open Interest analysis (untuk trend strength)
                    open_interest_analysis = None
                    try:
                        from src.data.binance_futures_data import get_futures_open_interest, analyze_open_interest
                        
                        # Convert symbol format: BTC-USD -> BTCUSDT
                        binance_symbol = SYMBOL.replace('-USD', 'USDT').replace('-', '') if SYMBOL else None
                        
                        if binance_symbol:
                            print(f"📊 Mengambil Open Interest untuk {binance_symbol}...")
                            oi_data = get_futures_open_interest(
                                symbol=binance_symbol,
                                testnet=False
                            )
                            
                            if oi_data:
                                # Ambil current price dan previous price untuk analisis
                                current_price_oi = float(current_price) if current_price else None
                                previous_price_oi = None
                                previous_oi = None
                                
                                # Coba ambil previous price dari data (harga 1 periode sebelumnya)
                                if len(data) >= 2:
                                    previous_price_oi = float(data['Close'].iloc[-2]) if 'Close' in data.columns else None
                                
                                # Untuk sekarang, kita tidak punya previous OI, jadi hanya analisis current OI
                                open_interest_analysis = analyze_open_interest(
                                    oi_data,
                                    current_price=current_price_oi,
                                    previous_oi=previous_oi,
                                    previous_price=previous_price_oi
                                )
                                print(f"✅ Open Interest analysis ditemukan")
                                print(f"   Open Interest: {open_interest_analysis['open_interest']:.2f}")
                                if open_interest_analysis.get('oi_change_pct', 0) != 0:
                                    print(f"   OI Change: {open_interest_analysis['oi_change_pct']:+.2f}%")
                                print(f"   Trend Direction: {open_interest_analysis['trend_direction']}")
                                print(f"   Trend Strength: {open_interest_analysis['trend_strength']}")
                            else:
                                print(f"⚠️  Open Interest tidak ditemukan untuk {binance_symbol}")
                    except Exception as e:
                        print(f"⚠️  Error mengambil Open Interest: {e}")
                        # Continue tanpa open interest analysis
                    
                    # Get Orderbook Depth analysis (untuk orderbook imbalance, buy/sell walls, whales)
                    orderbook_analysis = None
                    try:
                        from src.data.binance_futures_data import get_futures_orderbook, analyze_orderbook_depth
                        
                        # Convert symbol format: BTC-USD -> BTCUSDT
                        binance_symbol = SYMBOL.replace('-USD', 'USDT').replace('-', '') if SYMBOL else None
                        
                        if binance_symbol:
                            print(f"📊 Mengambil Orderbook Depth untuk {binance_symbol}...")
                            orderbook_data = get_futures_orderbook(
                                symbol=binance_symbol,
                                limit=100,  # Ambil 100 levels untuk analisis yang lebih baik
                                testnet=False
                            )
                            
                            if orderbook_data:
                                # Ambil current price untuk analisis
                                current_price_ob = float(current_price) if current_price else None
                                
                                orderbook_analysis = analyze_orderbook_depth(
                                    orderbook_data,
                                    current_price=current_price_ob
                                )
                                print(f"✅ Orderbook analysis ditemukan")
                                print(f"   Bid/Ask Ratio: {orderbook_analysis['bid_ask_ratio']:.2f}")
                                print(f"   Orderbook Imbalance: {orderbook_analysis['orderbook_imbalance']:+.2%}")
                                print(f"   Buy Wall: {orderbook_analysis['buy_wall_size']:.2f} @ {orderbook_analysis['buy_wall_price']:.4f}")
                                print(f"   Sell Wall: {orderbook_analysis['sell_wall_size']:.2f} @ {orderbook_analysis['sell_wall_price']:.4f}")
                                print(f"   Big Orders (Whales): {orderbook_analysis['big_orders_count']}")
                                print(f"   Signal: {orderbook_analysis['signal']}")
                            else:
                                print(f"⚠️  Orderbook tidak ditemukan untuk {binance_symbol}")
                    except Exception as e:
                        print(f"⚠️  Error mengambil Orderbook: {e}")
                        # Continue tanpa orderbook analysis
                    
                    # Collect all analysis data
                    analysis_data = collect_analysis_data(
                        data, 
                        market_context, 
                        enhanced_metrics,
                        recent_trades_analysis=recent_trades_analysis,
                        open_interest_analysis=open_interest_analysis,
                        orderbook_analysis=orderbook_analysis
                    )
                    
                    # Update current_price dan price_source di analysis_data dengan real-time price
                    # (price_source sudah didefinisikan sebelumnya di line ~932-952)
                    if 'current_position' in analysis_data:
                        # Update dengan real-time price jika tersedia
                        if 'current_price' in locals() and current_price:
                            analysis_data['current_position']['current_price'] = current_price
                        # Update price_source jika tersedia
                        if 'price_source' in locals() and price_source:
                            analysis_data['current_position']['price_source'] = price_source
                    
                    # Add trading setup if available
                    if 'setup' in locals():
                        add_trading_setup_to_analysis(analysis_data, {
                            'direction': setup.get('direction', 'N/A'),
                            'action': setup.get('action', 'N/A'),
                            'limit_entry': setup.get('entry', 'N/A'),
                            'stop_loss': setup.get('stop_loss', 'N/A'),
                            'stop_loss_pct': f"{setup.get('risk_pct', 0):.2f}%",
                            'targets': [
                                {'price': setup.get('tp1', 0), 'pct': 'N/A'},
                                {'price': setup.get('tp2', 0), 'pct': 'N/A'},
                                {'price': setup.get('tp3', 0), 'pct': 'N/A'}
                            ],
                            'risk_reward_ratios': []
                        })
                    
                    # Note: ML prediction results are already printed above
                    # We can add them to analysis_data if needed, but for now
                    # the AI will see them in the prompt context
                    
                    # Initialize DeepSeek advisor dengan model dari config
                    advisor = DeepSeekTradingAdvisor(api_key=DEEPSEEK_API_KEY)
                    
                    # Get recommendation (model akan digunakan dari config via get_trading_recommendation)
                    recommendation = advisor.get_trading_recommendation(analysis_data, model=DEEPSEEK_MODEL)
                    
                    # Get current price from analysis data (untuk format output)
                    if 'current_position' in analysis_data:
                        current_price = analysis_data['current_position'].get('current_price')
                        support = analysis_data['current_position'].get('support')
                        resistance = analysis_data['current_position'].get('resistance')
                        # Get price_source dari analysis_data jika tersedia, atau dari variable global
                        price_source_from_data = analysis_data['current_position'].get('price_source')
                        if price_source_from_data:
                            price_source = price_source_from_data
                    
                    if 'basic_info' in analysis_data:
                        timeframe = analysis_data['basic_info'].get('interval')
                
                # Get symbol (prioritaskan dari config)
                symbol = SYMBOL if SYMBOL else None
                
                # Get current price, support, resistance jika belum di-set (fallback)
                if current_price is None and 'analysis_data' in locals() and analysis_data and 'current_position' in analysis_data:
                    current_price = analysis_data['current_position'].get('current_price')
                    support = analysis_data['current_position'].get('support')
                    resistance = analysis_data['current_position'].get('resistance')
                
                if timeframe is None and 'analysis_data' in locals() and analysis_data and 'basic_info' in analysis_data:
                    timeframe = analysis_data['basic_info'].get('interval')
                    # Gunakan symbol dari basic_info hanya jika symbol dari config tidak ada
                    if not symbol:
                        symbol = analysis_data['basic_info'].get('symbol')
                
                # Fallback: jika masih None, gunakan TRADING_SYMBOL (convert ke format yfinance)
                if not symbol:
                    if TRADING_SYMBOL:
                        # Convert DOGEUSDT -> DOGE-USD
                        if TRADING_SYMBOL.endswith('USDT'):
                            base = TRADING_SYMBOL.replace('USDT', '')
                            symbol = f"{base}-USD"
                        else:
                            symbol = TRADING_SYMBOL
                
                # Final fallback
                if not symbol:
                    symbol = "BTC-USD"  # Default fallback
                
                print(f"📌 Symbol untuk Telegram: {symbol} (dari config: {SYMBOL if SYMBOL else 'None'})")
                
                # Untuk single coin request, selalu kirim ke Telegram (meskipun recommendation None)
                # Filter/threshold hanya berlaku untuk batch request
                if recommendation:
                    print(format_recommendation_output(
                        recommendation, 
                        current_price,
                        support,
                        resistance,
                        timeframe,
                        symbol
                    ))
            else:
                if not ENABLE_DEEPSEEK_AI:
                    print("ℹ️  DeepSeek AI integration dinonaktifkan di config.py")
                elif not DEEPSEEK_API_KEY:
                    print("ℹ️  DeepSeek API key tidak ditemukan di config.py")
        except ImportError as e:
            print(f"ℹ️  DeepSeek integration tidak tersedia: {e}")
        except Exception as e:
            print(f"⚠️  Error dalam DeepSeek integration: {e}")
            import traceback
            print(f"📋 Traceback:")
            traceback.print_exc()
        
        # ============================================
        # TELEGRAM BOT INTEGRATION
        # ============================================
        # Untuk single coin request, selalu kirim ke Telegram (tidak peduli recommendation ada atau tidak)
        # Dipindahkan keluar dari blok DeepSeek agar selalu dikirim
        try:
            from src.utils.config import ENABLE_TELEGRAM_BOT, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
            from src.integration.telegram_bot import TelegramBot
                
            if ENABLE_TELEGRAM_BOT and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                print("\n" + "=" * 70)
                print("📱 MENGIRIM KE TELEGRAM...")
                print("=" * 70)
                
                bot = TelegramBot(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
                
                # Kumpulkan semua data untuk format simplified
                trading_setup_data = None
                if 'setup' in locals() and setup:
                    trading_setup_data = setup
                
                # Ambil ML prediction results jika ada
                ml_result = None
                try:
                    from src.models.ml_prediction_helper import get_ml_prediction_from_file
                    import time
                    
                    # Retry mechanism: coba baca file beberapa kali dengan delay
                    max_retries = 3
                    retry_delay = 1.0
                    
                    for attempt in range(max_retries):
                        if attempt > 0:
                            print(f"   🔄 Retry {attempt}/{max_retries-1} membaca file JSON...")
                            time.sleep(retry_delay)
                        
                        print(f"🔍 [DEBUG] Mencoba membaca ml_prediction_result.json (attempt {attempt+1}/{max_retries})...")
                        print(f"   Current directory: {os.getcwd()}")
                        
                        ml_result = get_ml_prediction_from_file()
                        if ml_result:
                            print("✅ ML prediction results ditemukan")
                            break
                    
                    if ml_result:
                        # Debug: print metrics yang ditemukan
                        print(f"   📊 Metrics found: accuracy={ml_result.get('accuracy')}, sharpe={ml_result.get('sharpe_ratio')}, expected_value={ml_result.get('expected_value')}")
                        print(f"   🔍 [DEBUG] ml_result type: {type(ml_result)}")
                        print(f"   🔍 [DEBUG] ml_result keys: {list(ml_result.keys()) if isinstance(ml_result, dict) else 'N/A'}")
                        
                        # Validasi: pastikan key yang diperlukan ada
                        if isinstance(ml_result, dict):
                            required_keys = ['accuracy', 'sharpe_ratio', 'expected_value']
                            missing_keys = [key for key in required_keys if key not in ml_result]
                            if missing_keys:
                                print(f"   ⚠️  Key yang tidak ditemukan: {missing_keys}")
                                # Set default values untuk key yang hilang (None, bukan 0, agar bisa ditampilkan sebagai N/A)
                                for key in missing_keys:
                                    ml_result[key] = None
                                    print(f"   💡 Set {key} = None sebagai default")
                        
                        print(f"   🔍 [DEBUG] Full ml_result: {json.dumps(ml_result, indent=2) if isinstance(ml_result, dict) else ml_result}")
                    else:
                        print("⚠️  ML prediction results tidak ditemukan setelah semua retry")
                        print("   💡 Kemungkinan penyebab:")
                        print("      - prediksi_next_day.py belum dijalankan atau gagal")
                        print("      - File ml_prediction_result.json tidak dibuat")
                        print("      - File JSON tidak terbaca dengan benar")
                        print("      - Timing issue: file belum ter-write saat dibaca")
                        
                        # Cek apakah file ada di berbagai lokasi
                        import glob
                        json_files = glob.glob("**/ml_prediction_result.json", recursive=True)
                        if json_files:
                            print(f"   📁 File ditemukan di lokasi lain: {json_files}")
                            print(f"   💡 Coba baca file dari lokasi yang ditemukan...")
                            try:
                                import json
                                with open(json_files[0], 'r') as f:
                                    ml_result = json.load(f)
                                    print(f"   ✅ Berhasil membaca file dari: {json_files[0]}")
                            except Exception as e:
                                print(f"   ⚠️  Gagal membaca file: {e}")
                        else:
                            print("   📁 File tidak ditemukan di manapun")
                        
                        # Cek apakah RUN_PREDICTION diaktifkan
                        if not RUN_PREDICTION:
                            print("   ⚠️  RUN_PREDICTION = False di config.py")
                            print("      Set RUN_PREDICTION = True untuk menjalankan prediksi")
                        else:
                            print("   ⚠️  RUN_PREDICTION = True, tapi file JSON tidak ditemukan")
                            print("      Kemungkinan prediksi_next_day.py error atau tidak membuat file JSON")
                except ImportError as e:
                    print(f"ℹ️  ml_prediction_helper tidak tersedia: {e}")
                except Exception as e:
                    print(f"⚠️  ML prediction results tidak tersedia: {e}")
                    import traceback
                    traceback.print_exc()
                
                # ============================================
                # LOGGING SEBELUM KIRIM KE TELEGRAM
                # ============================================
                print("\n" + "=" * 70)
                print("📋 PRE-TELEGRAM LOGGING - Verifikasi Data")
                print("=" * 70)
                print(f"📌 Symbol: {symbol}")
                print(f"📌 Timeframe: {timeframe}")
                print(f"📌 Current Price: {current_price}")
                print(f"📌 Support: {support}")
                print(f"📌 Resistance: {resistance}")
                print(f"📌 Trading Setup: {trading_setup_data is not None}")
                if trading_setup_data:
                    print(f"   - Direction: {trading_setup_data.get('direction')}")
                    print(f"   - Entry: {trading_setup_data.get('entry')}")
                    print(f"   - Stop Loss: {trading_setup_data.get('stop_loss')}")
                print(f"📌 DeepSeek Recommendation: {recommendation is not None}")
                if recommendation:
                    print(f"   - Action: {recommendation.get('action')}")
                    print(f"   - Confidence: {recommendation.get('confidence')}")
                
                # LOGGING ML PREDICTION / QUANT METRICS
                print(f"\n📊 ML PREDICTION / QUANT METRICS:")
                print(f"   ml_result is None: {ml_result is None}")
                if ml_result:
                    print(f"   ✅ ml_result ditemukan!")
                    print(f"   Type: {type(ml_result)}")
                    if isinstance(ml_result, dict):
                        print(f"   Keys: {list(ml_result.keys())}")
                        print(f"   📈 Accuracy: {ml_result.get('accuracy')} (type: {type(ml_result.get('accuracy'))})")
                        print(f"   📈 Sharpe Ratio: {ml_result.get('sharpe_ratio')} (type: {type(ml_result.get('sharpe_ratio'))})")
                        print(f"   📈 Expected Value: {ml_result.get('expected_value')} (type: {type(ml_result.get('expected_value'))})")
                        
                        # Validasi: pastikan metrics tidak None
                        accuracy = ml_result.get('accuracy')
                        sharpe = ml_result.get('sharpe_ratio')
                        expected_val = ml_result.get('expected_value')
                        
                        print(f"\n   🔍 Validasi Metrics:")
                        print(f"      - accuracy is None: {accuracy is None}")
                        print(f"      - sharpe_ratio is None: {sharpe is None}")
                        print(f"      - expected_value is None: {expected_val is None}")
                        
                        if accuracy is not None:
                            print(f"      ✅ Accuracy valid: {accuracy}")
                        else:
                            print(f"      ❌ Accuracy is None!")
                        
                        if sharpe is not None:
                            print(f"      ✅ Sharpe valid: {sharpe}")
                        else:
                            print(f"      ❌ Sharpe is None!")
                        
                        if expected_val is not None:
                            print(f"      ✅ Expected Value valid: {expected_val}")
                        else:
                            print(f"      ❌ Expected Value is None!")
                        
                        # Full dump untuk debugging
                        import json
                        print(f"\n   📄 Full ml_result JSON:")
                        print(f"   {json.dumps(ml_result, indent=2, default=str)}")
                    else:
                        print(f"   ⚠️  ml_result bukan dict: {ml_result}")
                else:
                    print(f"   ❌ ml_result is None - Quant Metrics TIDAK AKAN muncul di Telegram!")
                    print(f"   💡 Kemungkinan penyebab:")
                    print(f"      - File ml_prediction_result.json tidak ditemukan")
                    print(f"      - File JSON kosong atau corrupt")
                    print(f"      - get_ml_prediction_from_file() return None")
                
                print("=" * 70)
                print()
                
                # Get pullback status jika data tersedia
                pullback_status_data = None
                try:
                    if 'data' in locals() and data is not None and len(data) > 0:
                        from src.utils.pullback_detection import get_current_pullback_status
                        pullback_status_data = get_current_pullback_status(data)
                        if pullback_status_data.get('has_pullback'):
                            print(f"   📊 Pullback detected: {pullback_status_data.get('pullback_type')} - akan ditambahkan ke Telegram")
                except Exception as e:
                    print(f"   ⚠️  Error getting pullback status: {e}")
                
                # Kirim satu pesan dengan format simplified
                print("📤 Mengirim trading signal (format simplified) ke Telegram...")
                # Get price_source dari variable yang sudah di-set sebelumnya
                price_source_info = price_source if 'price_source' in locals() else None
                message = bot.format_simplified_trading_signal(
                    symbol=symbol,
                    timeframe=timeframe,
                    current_price=current_price,
                    support=support,
                    resistance=resistance,
                    trading_setup=trading_setup_data,
                    deepseek_recommendation=recommendation,
                    ml_prediction=ml_result,
                    recent_trades_analysis=recent_trades_analysis if 'recent_trades_analysis' in locals() else None,
                    pullback_status=pullback_status_data,
                    price_source=price_source_info
                )
                
                # Log message sebelum kirim
                print("🔍 [DEBUG] Message yang akan dikirim ke Telegram:")
                print("=" * 70)
                # Tampilkan preview message (max 500 chars untuk tidak spam)
                message_preview = message[:500] + "..." if len(message) > 500 else message
                print(message_preview)
                if "Quant Metrics" in message:
                    print("✅ Quant Metrics DITEMUKAN di message!")
                else:
                    print("❌ Quant Metrics TIDAK DITEMUKAN di message!")
                print("=" * 70)
                
                success = bot.send_message(message)
                
                if success:
                    print("✅ Trading signal berhasil dikirim ke Telegram (format simplified)")
                    # Hapus file temporary ML prediction jika ada
                    if ml_result:
                        try:
                            os.remove('ml_prediction_result.json')
                        except:
                            pass
                else:
                    print("⚠️  Gagal mengirim trading signal ke Telegram")
                
                # Kirim chart ke Telegram jika ada (baik success maupun tidak)
                # DISABLED: Comment untuk tidak mengirim gambar ke Telegram
                # if chart_filename and os.path.exists(chart_filename):
                #     print("📊 Mengirim chart ke Telegram...")
                #     chart_success = bot.send_photo(
                #         chart_filename,
                #         caption=f"📊 Trading Chart - {symbol} ({timeframe})"
                #     )
                #     if chart_success:
                #         print("✅ Chart berhasil dikirim ke Telegram")
                #     else:
                #         print("⚠️  Gagal mengirim chart ke Telegram")
                #     
                #     # SELALU hapus file chart setelah dikirim (berhasil atau gagal)
                #     try:
                #         os.remove(chart_filename)
                #         print(f"🗑️  File chart dihapus: {chart_filename}")
                #     except Exception as e:
                #         print(f"⚠️  Gagal menghapus file chart {chart_filename}: {e}")
                
                # Hapus file chart tanpa mengirim ke Telegram
                if chart_filename and os.path.exists(chart_filename):
                    try:
                        os.remove(chart_filename)
                        print(f"🗑️  File chart dihapus (tidak dikirim ke Telegram): {chart_filename}")
                    except Exception as e:
                        print(f"⚠️  Gagal menghapus file chart {chart_filename}: {e}")
            else:
                if not ENABLE_TELEGRAM_BOT:
                    print("ℹ️  Telegram Bot integration dinonaktifkan di config.py")
                elif not TELEGRAM_BOT_TOKEN:
                    print("ℹ️  Telegram Bot Token tidak ditemukan di config.py")
                elif not TELEGRAM_CHAT_ID:
                    print("ℹ️  Telegram Chat ID tidak ditemukan di config.py")
        except ImportError as e:
            print(f"ℹ️  Telegram Bot integration tidak tersedia: {e}")
        except Exception as e:
            print(f"⚠️  Error dalam Telegram Bot integration: {e}")
    except Exception as e:
        print(f"\n❌ ERROR menjalankan prediksi: {e}")
        print("   Analisis strategi sudah selesai, jalankan prediksi secara manual jika perlu")
        import traceback
        print("   📋 Traceback:")
        traceback.print_exc()
        print(f"   ⚠️  File ml_prediction_result.json TIDAK AKAN dibuat karena error di atas")
else:
    print(f"\n❌ [PREDICTION CHECK] RUN_PREDICTION = {RUN_PREDICTION} - Prediksi TIDAK dijalankan", flush=True)
    print("   💡 Set RUN_PREDICTION = True di config.py untuk menjalankan prediksi", flush=True)
    print("   ⚠️  File ml_prediction_result.json TIDAK AKAN dibuat karena RUN_PREDICTION = False", flush=True)
    sys.stdout.flush()

# SELALU hapus semua file trading_chart_*.png yang mungkin masih ada (cleanup)
# Ini dieksekusi baik jika RUN_PREDICTION = True maupun False
try:
    chart_files = glob.glob("trading_chart_*.png")
    for chart_file in chart_files:
        try:
            if os.path.exists(chart_file):
                os.remove(chart_file)
                print(f"🗑️  File chart dihapus (cleanup): {chart_file}")
        except Exception as e:
            print(f"⚠️  Gagal menghapus file chart {chart_file}: {e}")
except Exception as e:
    print(f"⚠️  Error saat cleanup chart files: {e}")

# Hapus file CSV setelah SEMUA proses selesai (termasuk prediksi dan DeepSeek)
# Ini SELALU dieksekusi setelah semua proses selesai, baik jika RUN_PREDICTION = True maupun False
# TAPI: Jangan hapus jika script ini dipanggil dari run_all_analysis.py
# (run_all_analysis.py akan menghapus file setelah semua step selesai)
if os.environ.get('RUN_FROM_MASTER_SCRIPT') != '1':
    # Tunggu sebentar untuk memastikan semua subprocess sudah selesai menggunakan file
    import time
    time.sleep(2)  # Increase delay untuk memastikan prediksi_next_day.py dan semua proses sudah selesai
    
    if 'used_csv_file' in globals() and used_csv_file and os.path.exists(used_csv_file):
        try:
            os.remove(used_csv_file)
            print(f"\n🗑️  File CSV dihapus: {used_csv_file}")
        except Exception as e:
            print(f"\n⚠️  Gagal menghapus file CSV {used_csv_file}: {e}")
    else:
        # Coba cari file CSV terbaru jika used_csv_file tidak ada
        try:
            import glob
            csv_files = glob.glob("*_historical_*.csv")
            if csv_files:
                # Hapus file CSV terbaru yang dibuat
                latest_csv = max(csv_files, key=os.path.getmtime)
                if os.path.exists(latest_csv):
                    os.remove(latest_csv)
                    print(f"\n🗑️  File CSV dihapus (auto-detect): {latest_csv}")
        except Exception as e:
            print(f"\n⚠️  Gagal menghapus file CSV (auto-detect): {e}")
else:
    print(f"\n💡 File CSV akan dihapus setelah semua proses selesai (dipanggil dari run_all_analysis.py)")
