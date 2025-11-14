# Binance Data API - Usage Guide

## Overview
`binance_data.py` menyediakan wrapper untuk Binance API yang **100% kompatibel** dengan interface yfinance. Semua logic dan format data sama dengan yfinance, sehingga bisa digunakan sebagai drop-in replacement.

## Kompatibilitas dengan yfinance

### ✅ Format Symbol
- **yfinance**: `BTC-USD`, `ETH-USD`, `BNB-USD`
- **Binance**: Otomatis convert ke `BTCUSDT`, `ETHUSDT`, `BNBUSDT`
- **Support**: Format yfinance atau Binance langsung

### ✅ Format Interval
- **yfinance**: `1m`, `5m`, `15m`, `30m`, `1h`, `4h`, `1d`, `1w`, `1mo`
- **Binance**: Otomatis convert ke format Binance
- **Mapping**: Semua interval yfinance didukung

### ✅ Format Output
- **Kolom**: `date`, `Open`, `High`, `Low`, `Close`, `Volume`
- **Index**: DatetimeIndex (seperti yfinance)
- **Format**: DataFrame pandas dengan struktur identik

### ✅ Auto-adjust Logic
- **Days Back**: Otomatis adjust berdasarkan interval limit
- **Interval Limits**: Sama seperti yfinance (1m=7d, 5m=30d, 1h=365d, 1d=unlimited)

## Cara Menggunakan

### 1. Basic Usage (Sama seperti yfinance)

```python
from binance_data import get_data_binance

# Sama seperti yfinance
data = get_data_binance(
    symbol="BTC-USD",  # Format yfinance
    days_back=30,
    interval="1h"
)

# Output: DataFrame dengan kolom date, Open, High, Low, Close, Volume
print(data.head())
```

### 2. Menggunakan Ticker Class (Sama seperti yfinance.Ticker)

```python
from binance_data import Ticker

# Sama seperti yf.Ticker("BTC-USD")
ticker = Ticker("BTC-USD")

# Sama seperti ticker.history()
data = ticker.history(period="30d", interval="1h")
# atau
data = ticker.history(start=start_date, end=end_date, interval="1h")

# Output: DataFrame dengan DatetimeIndex
print(data.head())
```

### 3. Download Multiple Symbols (Sama seperti yfinance.download)

```python
from binance_data import download

# Sama seperti yf.download(["BTC-USD", "ETH-USD"], period="30d")
data = download(
    symbols=["BTC-USD", "ETH-USD"],
    period="30d",
    interval="1d"
)

# Output: DataFrame dengan MultiIndex (Ticker, Price Type)
print(data.head())
```

### 4. Menggunakan di get_historical_data.py

Edit `config.py`:
```python
DATA_SOURCE = "binance"  # Ganti dari "yfinance" ke "binance"
BINANCE_API_KEY = "your_api_key"  # Optional, untuk rate limit lebih tinggi
BINANCE_API_SECRET = "your_api_secret"  # Optional
```

Jalankan:
```bash
python3 get_historical_data.py
```

### 5. Menggunakan di analisis_quant.py

Data dari Binance akan otomatis kompatibel karena format output sama dengan yfinance. Tidak perlu perubahan di `analisis_quant.py`!

## Keuntungan Binance vs yfinance

### ✅ Kelebihan Binance
1. **Data Real-time**: Data langsung dari exchange, lebih akurat
2. **Rate Limit Lebih Tinggi**: Dengan API key, rate limit lebih tinggi
3. **Lebih Banyak Trading Pairs**: Semua trading pairs di Binance tersedia
4. **Data Volume Akurat**: Volume data dari exchange asli
5. **Interval 4h**: Support interval 4h yang tidak ada di yfinance

### ⚠️ Kekurangan Binance
1. **Perlu API Key**: Untuk rate limit optimal (tapi bisa tanpa API key untuk public endpoints)
2. **Network Dependency**: Perlu koneksi internet stabil ke Binance API

## API Key (Optional)

### Tanpa API Key
- ✅ Bisa digunakan untuk public endpoints (klines)
- ⚠️ Rate limit lebih rendah (1200 requests/minute)
- ✅ Cukup untuk penggunaan normal

### Dengan API Key
- ✅ Rate limit lebih tinggi (2400 requests/minute)
- ✅ Lebih stabil untuk high-frequency requests
- ✅ Bisa akses private endpoints (jika diperlukan)

**Cara mendapatkan API Key:**
1. Login ke Binance: https://www.binance.com
2. Settings → API Management: https://www.binance.com/en/my/settings/api-management
3. Create API Key
4. **PENTING**: Untuk testing, gunakan Testnet: https://testnet.binance.vision

## Contoh Penggunaan Lengkap

```python
from binance_data import get_data_binance, Ticker, download
from config import BINANCE_API_KEY, BINANCE_API_SECRET

# Method 1: Direct function call
data1 = get_data_binance(
    symbol="BTC-USD",
    days_back=30,
    interval="1h",
    api_key=BINANCE_API_KEY,
    api_secret=BINANCE_API_SECRET
)

# Method 2: Ticker class (yfinance style)
ticker = Ticker("ETH-USD", BINANCE_API_KEY, BINANCE_API_SECRET)
data2 = ticker.history(period="7d", interval="15m")

# Method 3: Multiple symbols (yfinance.download style)
data3 = download(
    symbols=["BTC-USD", "ETH-USD", "BNB-USD"],
    period="90d",
    interval="1d",
    api_key=BINANCE_API_KEY,
    api_secret=BINANCE_API_SECRET
)

# Semua output format sama dengan yfinance!
print(data1.head())
print(data2.head())
print(data3.head())
```

## Troubleshooting

### Error: "Library python-binance tidak terinstall"
```bash
pip install python-binance
```

### Error: "Connection timeout"
- Cek koneksi internet
- Cek firewall/proxy settings
- Coba lagi beberapa saat kemudian

### Error: "Rate limit exceeded"
- Gunakan API key untuk rate limit lebih tinggi
- Tambahkan delay antara requests
- Kurangi frekuensi requests

### Error: "Symbol tidak valid"
- Pastikan symbol format benar (BTC-USD atau BTCUSDT)
- Cek apakah trading pair tersedia di Binance
- Gunakan format Binance langsung jika perlu (BTCUSDT)

## Migration dari yfinance ke Binance

### Step 1: Install library
```bash
pip install python-binance
```

### Step 2: Update config.py
```python
DATA_SOURCE = "binance"  # Ganti dari "yfinance"
BINANCE_API_KEY = "your_key"  # Optional
BINANCE_API_SECRET = "your_secret"  # Optional
```

### Step 3: Test
```bash
python3 get_historical_data.py
```

### Step 4: Verify
- Cek format output sama dengan yfinance
- Cek data lengkap dan akurat
- Cek interval dan period sesuai

**Tidak perlu perubahan di `analisis_quant.py` atau script lain!** Semua kompatibel karena format output identik dengan yfinance.

