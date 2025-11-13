import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
import glob
import os
import sys
from datetime import datetime, timedelta

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
try:
    from config import (
        TRADING_STYLE, USE_CSV_DATA, CSV_FILE, FILTER_YEAR,
        TRADING_SYMBOL, SETUP_RISK_PERCENT, SETUP_TP_MULTIPLIERS,
        RUN_PREDICTION, SYMBOL, DATA_SOURCE
    )
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

def load_data_from_csv(csv_file=None):
    """Load data dari CSV yang dihasilkan get_data.py atau get_historical_data.py"""
    if csv_file is None:
        # Cari file CSV terbaru (prioritas: historical, lalu data real-time)
        # Pattern lebih fleksibel: btc_*.csv, btcusd_*.csv, atau *_historical_*.csv
        csv_files = []
        # Cari file historical dulu (prioritas)
        csv_files.extend(glob.glob("*_historical_*.csv"))
        # Cari file dengan pattern btc
        csv_files.extend(glob.glob("btc*.csv"))
        # Cari file dengan pattern umum
        if not csv_files:
            csv_files.extend(glob.glob("*_*.csv"))  # Fallback: semua file dengan underscore
        
        if not csv_files:
            raise FileNotFoundError("Tidak ada file CSV ditemukan. Jalankan get_data.py atau get_historical_data.py terlebih dahulu.")
        csv_file = max(csv_files, key=os.path.getctime)
        print(f"Menggunakan file: {csv_file}")
    
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
    data = yf.download("BTC-USD", start=start_str, end=end_str, progress=False)
    
    # Filter tambahan: pastikan hanya data tahun target
    if not data.empty and FILTER_YEAR is not None:
        data = data[data.index.year == FILTER_YEAR]
        print(f"Data setelah filter tahun {FILTER_YEAR}: {len(data)} records")
    
    return data

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
            
    except Exception as e:
        print(f"\n❌ Error memuat data CSV: {e}")
        print("⚠️  Fallback ke yfinance...")
        print("   PERINGATAN: Ini akan mengambil data lebih lama (1 tahun), mungkin tidak sesuai dengan data CSV!")
        print("   Jika ingin menggunakan data CSV, perbaiki error di atas atau set USE_CSV_DATA = False")
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
    from enhanced_analysis import (
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

# 3️⃣ Buat sinyal trading
data['Signal'] = 0
data.loc[data['MA_short'] > data['MA_long'], 'Signal'] = 1   # Beli
data.loc[data['MA_short'] < data['MA_long'], 'Signal'] = -1  # Jual

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
last_close = data['Close'].iloc[-1]
last_ma_short = data['MA_short'].iloc[-1] if pd.notna(data['MA_short'].iloc[-1]) else 0
last_ma_long = data['MA_long'].iloc[-1] if pd.notna(data['MA_long'].iloc[-1]) else 0

signal_text = "BELI" if last_signal == 1 else ("JUAL" if last_signal == -1 else "NETRAL")

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

# Pastikan last_close juga float
try:
    if isinstance(last_close, pd.Series):
        last_close = float(last_close.iloc[0])
    else:
        last_close = float(last_close)
except (TypeError, ValueError):
    last_close = 0.0

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
print(f"  - Harga: {format_price(last_close)}")
print(f"  - MA Short: {format_price(float(last_ma_short))}")
print(f"  - MA Long: {format_price(float(last_ma_long))}")
if last_support is not None and last_resistance is not None:
    support_dist = ((last_close - last_support) / last_close * 100) if last_close > 0 else 0
    resistance_dist = ((last_resistance - last_close) / last_close * 100) if last_close > 0 else 0
    print(f"  - Support: {format_price(last_support)} (jarak: {support_dist:.2f}%)")
    print(f"  - Resistance: {format_price(last_resistance)} (jarak: {resistance_dist:.2f}%)")
    # Tentukan apakah harga mendekati support atau resistance
    dist_to_support = abs(last_close - last_support) / last_close * 100 if last_close > 0 else 0
    dist_to_resistance = abs(last_resistance - last_close) / last_close * 100 if last_close > 0 else 0
    if dist_to_support < 2:
        print(f"  ⚠️  Harga sangat dekat dengan Support! (kemungkinan bounce atau breakdown)")
    elif dist_to_resistance < 2:
        print(f"  ⚠️  Harga sangat dekat dengan Resistance! (kemungkinan breakout atau rejection)")
print()

# ============================================
# TRADING SETUP (Entry, Stop Loss, Take Profit)
# ============================================
def generate_trading_setup(symbol, current_price, support, resistance, signal, 
                           use_limit_entry=True, risk_percent=2.5, tp_multipliers=None):
    """
    Generate trading setup dengan Entry, Stop Loss, dan Take Profit levels
    
    Parameters:
    - symbol: Trading symbol (e.g., "BTCUSDT", "ENAUSDT")
    - current_price: Current market price
    - support: Support level
    - resistance: Resistance level
    - signal: Trading signal (1 = BELI/LONG, -1 = JUAL/SHORT)
    - use_limit_entry: True = gunakan limit entry (di support untuk LONG), False = market entry
    - risk_percent: Risk percentage untuk stop loss (default 2.5%)
    - tp_multipliers: List of TP multipliers [tp1, tp2, tp3] (default [1.5, 2.5, 3.5])
    """
    # Default TP multipliers jika tidak diberikan
    if tp_multipliers is None:
        tp_multipliers = [1.5, 2.5, 3.5]
    if signal == 1:  # LONG/BUY
        direction = "LONG"
        action = "BUY"
        
        # Entry Price
        if use_limit_entry and support is not None:
            # Limit entry sedikit di atas support untuk LONG
            entry_price = support * 1.001  # 0.1% di atas support
        else:
            entry_price = current_price
        
        # Stop Loss (di bawah support atau berdasarkan risk %)
        if support is not None:
            sl_based_on_support = support * 0.995  # 0.5% di bawah support
            sl_based_on_risk = entry_price * (1 - risk_percent / 100)
            stop_loss = min(sl_based_on_support, sl_based_on_risk)  # Ambil yang lebih konservatif
        else:
            stop_loss = entry_price * (1 - risk_percent / 100)
        
        # Calculate risk (distance from entry to stop loss)
        risk = entry_price - stop_loss
        risk_pct = (risk / entry_price) * 100
        
        # Take Profit levels (berdasarkan resistance atau R:R ratio)
        if resistance is not None:
            # TP1: Target pertama (berdasarkan multiplier atau 50% ke resistance)
            tp1_option1 = entry_price + (risk * tp_multipliers[0])
            tp1_option2 = entry_price + ((resistance - entry_price) * 0.5)
            tp1 = min(tp1_option1, tp1_option2)
            
            # TP2: Target kedua (berdasarkan multiplier atau 75% ke resistance)
            tp2_option1 = entry_price + (risk * tp_multipliers[1])
            tp2_option2 = entry_price + ((resistance - entry_price) * 0.75)
            tp2 = min(tp2_option1, tp2_option2)
            
            # TP3: Target ketiga (berdasarkan multiplier atau resistance)
            tp3_option1 = entry_price + (risk * tp_multipliers[2])
            tp3 = min(tp3_option1, resistance)
        else:
            # Jika tidak ada resistance, gunakan R:R ratio saja
            tp1 = entry_price + (risk * tp_multipliers[0])
            tp2 = entry_price + (risk * tp_multipliers[1])
            tp3 = entry_price + (risk * tp_multipliers[2])
        
    else:  # SHORT/SELL
        direction = "SHORT"
        action = "SELL"
        
        # Entry Price
        if use_limit_entry and resistance is not None:
            # Limit entry sedikit di bawah resistance untuk SHORT
            entry_price = resistance * 0.999  # 0.1% di bawah resistance
        else:
            entry_price = current_price
        
        # Stop Loss (di atas resistance atau berdasarkan risk %)
        if resistance is not None:
            sl_based_on_resistance = resistance * 1.005  # 0.5% di atas resistance
            sl_based_on_risk = entry_price * (1 + risk_percent / 100)
            stop_loss = max(sl_based_on_resistance, sl_based_on_risk)  # Ambil yang lebih konservatif
        else:
            stop_loss = entry_price * (1 + risk_percent / 100)
        
        # Calculate risk (distance from entry to stop loss)
        risk = stop_loss - entry_price
        risk_pct = (risk / entry_price) * 100
        
        # Take Profit levels (berdasarkan support atau R:R ratio)
        if support is not None:
            # TP1: Target pertama (berdasarkan multiplier atau 50% ke support)
            tp1_option1 = entry_price - (risk * tp_multipliers[0])
            tp1_option2 = entry_price - ((entry_price - support) * 0.5)
            tp1 = max(tp1_option1, tp1_option2)
            
            # TP2: Target kedua (berdasarkan multiplier atau 75% ke support)
            tp2_option1 = entry_price - (risk * tp_multipliers[1])
            tp2_option2 = entry_price - ((entry_price - support) * 0.75)
            tp2 = max(tp2_option1, tp2_option2)
            
            # TP3: Target ketiga (berdasarkan multiplier atau support)
            tp3_option1 = entry_price - (risk * tp_multipliers[2])
            tp3 = max(tp3_option1, support)
        else:
            # Jika tidak ada support, gunakan R:R ratio saja
            tp1 = entry_price - (risk * tp_multipliers[0])
            tp2 = entry_price - (risk * tp_multipliers[1])
            tp3 = entry_price - (risk * tp_multipliers[2])
    
    return {
        'symbol': symbol,
        'direction': direction,
        'action': action,
        'entry': entry_price,
        'stop_loss': stop_loss,
        'risk_pct': risk_pct,
        'tp1': tp1,
        'tp2': tp2,
        'tp3': tp3
    }

# Generate trading setup jika ada support dan resistance
# Tentukan signal untuk setup: gunakan last_signal jika ada, atau tentukan berdasarkan posisi harga
if last_support is not None and last_resistance is not None:
    # Pastikan last_support dan last_resistance adalah float
    if not isinstance(last_support, (int, float)):
        last_support = float(last_support) if last_support is not None else None
    if not isinstance(last_resistance, (int, float)):
        last_resistance = float(last_resistance) if last_resistance is not None else None
    
    # Jika signal = 0 (NETRAL), tentukan berdasarkan posisi harga relatif terhadap support/resistance
    if last_signal == 0:
        # Jika harga lebih dekat ke support, bias ke LONG
        # Jika harga lebih dekat ke resistance, bias ke SHORT
        if last_close > 0:
            dist_to_support = abs(last_close - last_support) / last_close
            dist_to_resistance = abs(last_resistance - last_close) / last_close
        else:
            dist_to_support = float('inf')
            dist_to_resistance = float('inf')
        
        if dist_to_support < dist_to_resistance:
            setup_signal = 1  # LONG (harga dekat support, kemungkinan bounce)
        else:
            setup_signal = -1  # SHORT (harga dekat resistance, kemungkinan rejection)
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
            "SWING_TRADING": [2.0, 3.0, 5.0],  # Target besar untuk swing trading
            "POSITION_TRADING": [3.0, 5.0, 8.0] # Target sangat besar untuk position trading
        }
        setup_tp_mult = tp_config.get(TRADING_STYLE, [1.5, 2.5, 3.5])
    
    setup = generate_trading_setup(
        symbol=TRADING_SYMBOL,
        current_price=float(last_close),
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
    
    # Hitung persentase kenaikan/penurunan dari entry untuk setiap TP
    if setup['direction'] == "LONG":
        tp1_pct = ((setup['tp1'] - setup['entry']) / setup['entry']) * 100
        tp2_pct = ((setup['tp2'] - setup['entry']) / setup['entry']) * 100
        tp3_pct = ((setup['tp3'] - setup['entry']) / setup['entry']) * 100
    else:  # SHORT
        tp1_pct = ((setup['entry'] - setup['tp1']) / setup['entry']) * 100
        tp2_pct = ((setup['entry'] - setup['tp2']) / setup['entry']) * 100
        tp3_pct = ((setup['entry'] - setup['tp3']) / setup['entry']) * 100
    
    print("\n" + "=" * 60)
    print(f"{setup['symbol']} LIMIT {setup['action']} SETUP - {setup['direction']}")
    print("=" * 60)
    print()
    print(f"LIMIT ENTRY: {setup['entry']:{price_format}}")
    print()
    print(f"Stop Loss: {setup['stop_loss']:{price_format}} (-{setup['risk_pct']:.2f}%)")
    print()
    # Tampilkan persentase dengan tanda yang sesuai (LONG = +, SHORT = + karena profit)
    sign = "+" if setup['direction'] == "LONG" else "+"
    print(f"TP1: {setup['tp1']:{price_format}} ({sign}{tp1_pct:.2f}%)")
    print()
    print(f"TP 2: {setup['tp2']:{price_format}} ({sign}{tp2_pct:.2f}%)")
    print()
    print(f"TP 3: {setup['tp3']:{price_format}} ({sign}{tp3_pct:.2f}%)")
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

# Store analysis data for DeepSeek (will be used after ML prediction)
analysis_data_for_deepseek = None

# ============================================
# OPSI: Jalankan prediksi SEBELUM menampilkan chart
# (Karena plt.show() akan memblokir eksekusi)
# ============================================
if RUN_PREDICTION:
    print("\n" + "=" * 60)
    print("🚀 LANJUT KE PREDIKSI HARI BERIKUTNYA (MASA DEPAN)")
    print("=" * 60)
    print()
    
    try:
        # Import dan jalankan prediksi secara langsung
        import subprocess
        import sys
        
        # Jalankan dengan output real-time
        result = subprocess.run(
            [sys.executable, "prediksi_next_day.py"],
            check=False,
            stdout=None,  # Tampilkan output langsung
            stderr=None   # Tampilkan error langsung
        )
        
        if result.returncode != 0:
            print("\n⚠️  Prediksi mengalami error, tapi analisis strategi sudah selesai")
        else:
            print("\n" + "=" * 60)
            print("✅ PREDIKSI SELESAI - Lihat output di atas untuk signal BELI/JUAL masa depan")
            print("=" * 60)
        
        # ============================================
        # DEEPSEEK AI INTEGRATION (After ML Prediction)
        # ============================================
        try:
            from config import ENABLE_DEEPSEEK_AI, DEEPSEEK_API_KEY, DEEPSEEK_MODEL
            from deepseek_integration import DeepSeekTradingAdvisor, format_recommendation_output
            from collect_analysis_data import collect_analysis_data, add_trading_setup_to_analysis
            
            if ENABLE_DEEPSEEK_AI and DEEPSEEK_API_KEY:
                print("\n" + "=" * 70)
                print("🤖 MENGIRIM DATA KE DEEPSEEK AI...")
                print("=" * 70)
                
                # Collect all analysis data
                analysis_data = collect_analysis_data(data, market_context, enhanced_metrics)
                
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
                
                # Initialize DeepSeek advisor
                advisor = DeepSeekTradingAdvisor(api_key=DEEPSEEK_API_KEY)
                
                # Get recommendation
                recommendation = advisor.get_trading_recommendation(analysis_data)
                
                # Get current price from analysis data
                current_price = None
                support = None
                resistance = None
                timeframe = None
                symbol = None
                
                if 'current_position' in analysis_data:
                    current_price = analysis_data['current_position'].get('current_price')
                    support = analysis_data['current_position'].get('support')
                    resistance = analysis_data['current_position'].get('resistance')
                
                if 'basic_info' in analysis_data:
                    timeframe = analysis_data['basic_info'].get('interval')
                    symbol = analysis_data['basic_info'].get('symbol')
                
                if recommendation:
                    print(format_recommendation_output(
                        recommendation, 
                        current_price,
                        support,
                        resistance,
                        timeframe,
                        symbol
                    ))
                    
                    # ============================================
                    # TELEGRAM BOT INTEGRATION
                    # ============================================
                    try:
                        from config import ENABLE_TELEGRAM_BOT, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
                        from telegram_bot import TelegramBot
                        
                        if ENABLE_TELEGRAM_BOT and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                            print("\n" + "=" * 70)
                            print("📱 MENGIRIM KE TELEGRAM...")
                            print("=" * 70)
                            
                            bot = TelegramBot(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
                            success = bot.send_trading_recommendation(
                                recommendation=recommendation,
                                current_price=current_price,
                                support=support,
                                resistance=resistance,
                                timeframe=timeframe,
                                symbol=symbol
                            )
                            
                            if success:
                                print("✅ Rekomendasi berhasil dikirim ke Telegram")
                                
                                # Kirim trading setup ke Telegram jika ada
                                if 'setup' in locals() and setup:
                                    print("📋 Mengirim trading setup ke Telegram...")
                                    setup_success = bot.send_trading_setup(setup, symbol)
                                    if setup_success:
                                        print("✅ Trading setup berhasil dikirim ke Telegram")
                                    else:
                                        print("⚠️  Gagal mengirim trading setup ke Telegram")
                                
                                # Kirim ML prediction results ke Telegram jika ada
                                try:
                                    from ml_prediction_helper import get_ml_prediction_from_file
                                    ml_result = get_ml_prediction_from_file()
                                    if ml_result:
                                        print("🤖 Mengirim ML prediction results ke Telegram...")
                                        ml_success = bot.send_ml_prediction(ml_result)
                                        if ml_success:
                                            print("✅ ML prediction results berhasil dikirim ke Telegram")
                                            # Hapus file temporary
                                            try:
                                                os.remove('ml_prediction_result.json')
                                            except:
                                                pass
                                        else:
                                            print("⚠️  Gagal mengirim ML prediction results ke Telegram")
                                except Exception as e:
                                    print(f"ℹ️  ML prediction results tidak tersedia: {e}")
                                
                                # Kirim chart ke Telegram jika ada
                                if chart_filename and os.path.exists(chart_filename):
                                    print("📊 Mengirim chart ke Telegram...")
                                    chart_success = bot.send_photo(
                                        chart_filename,
                                        caption=f"📊 Trading Chart - {symbol} ({timeframe})"
                                    )
                                    if chart_success:
                                        print("✅ Chart berhasil dikirim ke Telegram")
                                        # Hapus file temporary
                                        try:
                                            os.remove(chart_filename)
                                            print(f"🗑️  File temporary dihapus: {chart_filename}")
                                        except:
                                            pass
                                    else:
                                        print("⚠️  Gagal mengirim chart ke Telegram")
                            else:
                                print("⚠️  Gagal mengirim ke Telegram")
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
                else:
                    print("⚠️  Tidak dapat mendapatkan rekomendasi dari DeepSeek AI")
            else:
                if not ENABLE_DEEPSEEK_AI:
                    print("ℹ️  DeepSeek AI integration dinonaktifkan di config.py")
                elif not DEEPSEEK_API_KEY:
                    print("ℹ️  DeepSeek API key tidak ditemukan di config.py")
        except ImportError as e:
            print(f"ℹ️  DeepSeek integration tidak tersedia: {e}")
        except Exception as e:
            print(f"⚠️  Error dalam DeepSeek integration: {e}")
    except Exception as e:
        print(f"\n⚠️  Error menjalankan prediksi: {e}")
        print("   Analisis strategi sudah selesai, jalankan prediksi secara manual jika perlu")
    
       # Chart sudah dikirim ke Telegram, tidak perlu ditampilkan di terminal
       # plt.show()  # Disabled - chart hanya dikirim ke Telegram
