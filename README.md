# Trading Quant - Aplikasi Analisis Trading Kuantitatif

Aplikasi Python untuk analisis trading kuantitatif dengan berbagai strategi dan prediksi menggunakan machine learning.

## 📋 Persyaratan

- Python 3.8 atau lebih baru
- pip (Python package manager)

## 🚀 Cara Menjalankan di Virtual Environment

### Metode 1: Menggunakan Script Helper (Recommended)

1. **Buat dan setup virtual environment:**
```bash
chmod +x run.sh
./run.sh
```

2. **Jalankan aplikasi langsung:**
```bash
./run.sh --run
```

### Metode 2: Manual Setup

1. **Buat virtual environment:**
```bash
python3 -m venv venv
```

2. **Aktifkan virtual environment:**
```bash
# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

4. **Jalankan aplikasi:**
```bash
python run_all_analysis.py
```

## 📁 Struktur Aplikasi

- `config.py` - Konfigurasi terpusat untuk semua script
- `run_all_analysis.py` - Script master untuk menjalankan semua analisis
- `get_historical_data.py` - Mengambil data historis dari berbagai sumber
- `analisis_quant.py` - Analisis strategi trading (Moving Average Crossover)
- `prediksi_next_day.py` - Prediksi harga menggunakan Machine Learning

## ⚙️ Konfigurasi

Edit file `config.py` untuk mengatur:
- **TRADING_STYLE**: Pilih strategi trading (SCALPING, DAY_TRADING, SWING_TRADING, POSITION_TRADING)
- **DATA_SOURCE**: Sumber data (yfinance, coingecko, freecryptoapi)
- **SYMBOL**: Coin yang akan dianalisis (contoh: BTC-USD, ETH-USD)
- **INTERVAL**: Time frame data (otomatis berdasarkan TRADING_STYLE)

## 📊 Workflow

Aplikasi akan menjalankan workflow berikut:

1. **Ambil Data Historical** - Mengambil data historis sesuai konfigurasi
2. **Analisis Strategi** - Menganalisis sinyal trading dengan Moving Average Crossover
3. **Prediksi Hari Berikutnya** - Memprediksi harga menggunakan Machine Learning

## 🔧 Troubleshooting

### Virtual environment tidak aktif
Pastikan venv sudah diaktifkan sebelum menjalankan script:
```bash
source venv/bin/activate
```

### Dependencies tidak terinstall
Install ulang dependencies:
```bash
pip install -r requirements.txt
```

### Error saat mengambil data
- Cek koneksi internet
- Pastikan API key valid (jika menggunakan CoinGecko atau FreeCryptoAPI)
- Cek konfigurasi SYMBOL dan DATA_SOURCE di `config.py`

## 📝 Catatan

- Data historis akan disimpan dalam format CSV
- Hasil analisis akan ditampilkan di terminal dan disimpan sebagai plot/gambar
- Pastikan sudah mengatur konfigurasi di `config.py` sebelum menjalankan

