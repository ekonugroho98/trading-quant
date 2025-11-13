import pandas as pd
import yfinance as yf
import requests
from datetime import datetime, timedelta
import time

# ============================================
# SCRIPT UNTUK MENGAMBIL DATA HISTORICAL
# Tidak perlu menunggu, langsung dapat data historis
# ============================================

# Import konfigurasi terpusat
try:
    from config import (
        DATA_SOURCE, SYMBOL, DAYS_BACK, TRADING_STYLE, get_interval, 
        COINGECKO_API_KEY, COIN_ID, FREECRYPTOAPI_KEY, FREECRYPTOAPI_SYMBOL
    )
    INTERVAL = get_interval()  # Otomatis berdasarkan TRADING_STYLE
    print(f"📋 Menggunakan konfigurasi dari config.py")
    print(f"   TRADING_STYLE: {TRADING_STYLE}")
    print(f"   INTERVAL: {INTERVAL} (otomatis berdasarkan TRADING_STYLE)")
except ImportError:
    # Fallback jika config.py tidak ada
    print("⚠️  config.py tidak ditemukan, menggunakan konfigurasi default")
    DATA_SOURCE = "yfinance"
    SYMBOL = "BTC-USD"
    DAYS_BACK = 7
    INTERVAL = "15m"
    COINGECKO_API_KEY = None
    COIN_ID = "bitcoin"
    FREECRYPTOAPI_KEY = None
    FREECRYPTOAPI_SYMBOL = "BTC"

def get_data_yfinance(symbol, days_back, interval):
    """
    Mengambil data historical dari Yahoo Finance (yfinance)
    Gratis, tidak perlu API key, data lengkap
    
    Catatan: yfinance memiliki limit untuk interval kecil:
    - 1m: maksimal 7 hari
    - 5m: maksimal 60 hari
    - 15m, 30m: maksimal 60 hari
    - 1h: maksimal 730 hari
    - 1d: tidak ada limit
    """
    print(f"Mengambil data dari Yahoo Finance...")
    print(f"Symbol: {symbol}")
    print(f"Periode: {days_back} hari terakhir")
    print(f"Interval: {interval}")
    
    # Validasi dan auto-adjust DAYS_BACK berdasarkan interval
    max_days_by_interval = {
        "1m": 7,      # yfinance limit: maksimal 7-8 hari untuk 1m
        "2m": 60,    # maksimal 60 hari
        "5m": 60,    # maksimal 60 hari
        "15m": 60,   # maksimal 60 hari
        "30m": 60,   # maksimal 60 hari
        "60m": 730,  # maksimal 730 hari (1h)
        "90m": 60,   # maksimal 60 hari
        "1h": 730,   # maksimal 730 hari
        "1d": None,  # tidak ada limit
        "5d": None,  # tidak ada limit
        "1wk": None, # tidak ada limit
        "1mo": None  # tidak ada limit
    }
    
    max_days = max_days_by_interval.get(interval)
    if max_days is not None and days_back > max_days:
        print(f"\n⚠️  PERINGATAN: Interval {interval} hanya mendukung maksimal {max_days} hari")
        print(f"   DAYS_BACK ({days_back}) akan disesuaikan menjadi {max_days} hari")
        days_back = max_days
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    try:
        ticker = yf.Ticker(symbol)
        # yfinance history() tidak menerima parameter progress
        # Gunakan period sebagai alternatif jika start/end tidak bekerja
        try:
            data = ticker.history(start=start_date, end=end_date, interval=interval)
        except:
            # Fallback: gunakan period
            period_map = {
                7: "7d", 30: "1mo", 90: "3mo", 180: "6mo", 365: "1y"
            }
            period = period_map.get(days_back, f"{days_back}d")
            data = ticker.history(period=period, interval=interval)
        
        if data.empty:
            print("⚠️  Data kosong, coba interval atau periode yang berbeda")
            return None
        
        # Reset index untuk membuat Date menjadi kolom
        # yfinance mengembalikan DataFrame dengan DatetimeIndex
        data.reset_index(inplace=True)
        
        # Cari kolom yang berisi tanggal (bisa 'Date', 'Datetime', atau nama lain)
        date_col = None
        for col in data.columns:
            if col.lower() in ['date', 'datetime'] or 'date' in col.lower():
                date_col = col
                break
        
        # Jika tidak ditemukan, kolom pertama biasanya adalah date setelah reset_index
        if date_col is None and len(data.columns) > 0:
            # Cek apakah kolom pertama adalah datetime
            if pd.api.types.is_datetime64_any_dtype(data[data.columns[0]]):
                date_col = data.columns[0]
        
        # Rename ke 'date'
        if date_col and date_col != 'date':
            data.rename(columns={date_col: 'date'}, inplace=True)
        elif date_col is None:
            # Jika masih tidak ada, buat dari index (seharusnya tidak terjadi)
            raise ValueError("Tidak dapat menemukan kolom tanggal dalam data")
        
        print(f"✅ Data berhasil diambil: {len(data)} records")
        if 'date' in data.columns:
            print(f"Periode: {data['date'].min()} sampai {data['date'].max()}")
        
        return data
    
    except Exception as e:
        print(f"❌ Error mengambil data dari yfinance: {e}")
        return None

def get_data_coingecko(days_back, coin_id="bitcoin", api_key=None):
    """
    Mengambil data historical dari CoinGecko API
    Gratis, rate limit: 10-50 calls/minute
    Jika menggunakan API key, rate limit lebih tinggi
    
    Parameters:
    - days_back: Berapa hari ke belakang
    - coin_id: Coin ID CoinGecko (default: "bitcoin" untuk BTC)
    - api_key: API key CoinGecko (opsional)
    """
    print(f"Mengambil data dari CoinGecko...")
    print(f"Coin: {coin_id}")
    print(f"Periode: {days_back} hari terakhir")
    
    # Gunakan Pro API jika ada API key, atau free API jika tidak
    if api_key:
        base_url = "https://pro-api.coingecko.com/api/v3"
        print("🔑 Menggunakan CoinGecko Pro API (dengan API key)")
    else:
        base_url = "https://api.coingecko.com/api/v3"
        print("ℹ️  Menggunakan CoinGecko Free API")
    
    url = f"{base_url}/coins/{coin_id}/market_chart"
    
    params = {
        "vs_currency": "usd",
        "days": days_back,
        "interval": "hourly" if days_back <= 90 else "daily"
    }
    
    # Tambahkan API key jika ada
    if api_key:
        params["x_cg_pro_api_key"] = api_key
    
    # Headers dengan User-Agent (diperlukan untuk beberapa endpoint)
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; TradingBot/1.0)"
    }
    
    # Jika menggunakan Pro API, tambahkan header API key
    if api_key:
        headers["x-cg-pro-api-key"] = api_key
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data_json = response.json()
        
        # CoinGecko mengembalikan data dalam format: [[timestamp, price], ...]
        prices = data_json.get('prices', [])
        
        if not prices:
            print("⚠️  Data kosong dari CoinGecko")
            return None
        
        # Convert ke DataFrame
        df = pd.DataFrame(prices, columns=['timestamp', 'price'])
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Untuk CoinGecko, kita hanya dapat price, jadi buat OHLCV sederhana
        df['Open'] = df['price']
        df['High'] = df['price']
        df['Low'] = df['price']
        df['Close'] = df['price']
        df['Volume'] = 0  # CoinGecko free API tidak menyediakan volume
        
        df = df[['date', 'Open', 'High', 'Low', 'Close', 'Volume']]
        
        print(f"✅ Data berhasil diambil: {len(df)} records")
        print(f"Periode: {df['date'].min()} sampai {df['date'].max()}")
        
        # Rate limiting untuk CoinGecko
        time.sleep(1)
        
        return df
    
    except Exception as e:
        print(f"❌ Error mengambil data dari CoinGecko: {e}")
        return None

def get_data_freecryptoapi(days_back, symbol="BTC", api_key=None):
    """
    Mengambil data historical dari FreeCryptoAPI
    Gratis dengan API key, menyediakan data real-time
    
    Parameters:
    - days_back: Berapa hari ke belakang (untuk FreeCryptoAPI, kita ambil data real-time)
    - symbol: Symbol crypto (default: "BTC")
    - api_key: API key FreeCryptoAPI (wajib)
    
    Endpoint: GET /api/v1/getData
    Dokumentasi: https://freecryptoapi.com/documentation/
    
    Catatan: FreeCryptoAPI mungkin tidak menyediakan endpoint historis langsung.
    Kita akan menggunakan getData untuk data real-time dan mengumpulkan beberapa data.
    """
    print(f"Mengambil data dari FreeCryptoAPI...")
    print(f"Symbol: {symbol}")
    print(f"Periode: {days_back} hari terakhir")
    
    if not api_key:
        print("❌ Error: FreeCryptoAPI memerlukan API key")
        print("💡 Daftar gratis di: https://freecryptoapi.com/")
        return None
    
    # Base URL yang benar: https://api.freecryptoapi.com/v1
    base_url = "https://api.freecryptoapi.com/v1"
    
    # Coba endpoint getData terlebih dahulu (data real-time)
    # Berdasarkan dokumentasi, parameter menggunakan 'apikey' bukan 'api_key'
    url = f"{base_url}/getData"
    
    # Parameter untuk getData
    params = {
        'symbol': symbol,
        'apikey': api_key  # Gunakan 'apikey' bukan 'api_key'
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; TradingBot/1.0)"
    }
    
    try:
        print(f"🔑 Menggunakan FreeCryptoAPI dengan API key")
        print(f"   Base URL: {base_url}")
        print(f"   Endpoint: {url}")
        print(f"   Parameters: symbol={symbol}, apikey=***")
        
        # Coba request dengan timeout lebih lama
        try:
            response = requests.get(url, params=params, headers=headers, timeout=60)
        except requests.exceptions.Timeout:
            print(f"❌ Request timeout - server tidak merespons")
            print(f"💡 FreeCryptoAPI mungkin sedang down atau overloaded")
            print(f"   Coba lagi nanti atau gunakan DATA_SOURCE lain (yfinance/coingecko)")
            return None
        
        # Debug: print response untuk troubleshooting
        print(f"   Status code: {response.status_code}")
        
        # Handle error 522 (Cloudflare timeout)
        if response.status_code == 522:
            print(f"❌ Error 522: Server timeout - FreeCryptoAPI tidak merespons")
            print(f"💡 Kemungkinan penyebab:")
            print(f"   - Server FreeCryptoAPI sedang down atau overloaded")
            print(f"   - API key tidak valid atau expired")
            print(f"   - Rate limit tercapai")
            print(f"💡 Solusi:")
            print(f"   - Coba lagi dalam beberapa menit")
            print(f"   - Cek API key di https://freecryptoapi.com/")
            print(f"   - Gunakan DATA_SOURCE lain: yfinance atau coingecko")
            return None
        
        # Handle error 404
        if response.status_code == 404:
            print(f"❌ Error 404: Endpoint tidak ditemukan")
            print(f"💡 Mungkin endpoint atau parameter salah")
            return None
        
        response.raise_for_status()
        
        # Debug: print response text untuk melihat format
        print(f"   Response preview: {response.text[:200]}")
        
        try:
            data_json = response.json()
        except ValueError:
            print(f"❌ Response bukan JSON: {response.text[:500]}")
            return None
        
        # Cek apakah response berhasil
        if isinstance(data_json, dict):
            if 'status' in data_json and data_json.get('status') == False:
                print(f"❌ Error dari API: {data_json.get('error', 'Unknown error')}")
                return None
            if 'error' in data_json:
                print(f"❌ Error dari API: {data_json.get('error', 'Unknown error')}")
                return None
        
        # FreeCryptoAPI getData biasanya mengembalikan data real-time
        # Format bisa berupa: {"price": ..., "symbol": ..., ...} atau array
        print(f"   Response structure: {type(data_json)}")
        
        # Jika response adalah dict dengan data price, buat DataFrame dari data real-time
        if isinstance(data_json, dict):
            # Cek apakah ada field price atau data
            if 'price' in data_json or 'Price' in data_json:
                # Data real-time single point
                price = data_json.get('price') or data_json.get('Price') or data_json.get('close') or data_json.get('Close')
                if price:
                    # Buat DataFrame dengan data real-time (gunakan sebagai Close)
                    current_time = datetime.now()
                    df = pd.DataFrame([{
                        'date': current_time,
                        'Open': price,
                        'High': price,
                        'Low': price,
                        'Close': price,
                        'Volume': data_json.get('volume', data_json.get('Volume', 0))
                    }])
                    print(f"⚠️  FreeCryptoAPI hanya menyediakan data real-time (bukan historis)")
                    print(f"   Menggunakan data real-time saat ini sebagai referensi")
            elif 'data' in data_json:
                # Data dalam field 'data'
                data_list = data_json['data']
            else:
                # Coba parse sebagai array of data
                data_list = [data_json]
        elif isinstance(data_json, list):
            data_list = data_json
        else:
            print(f"⚠️  Format response tidak dikenali: {type(data_json)}")
            print(f"   Response: {str(data_json)[:500]}")
            return None
        
        # Jika belum dibuat DataFrame, buat dari data_list
        if 'df' not in locals():
            if not data_list or len(data_list) == 0:
                print("⚠️  Data kosong dari FreeCryptoAPI")
                return None
            
            # Convert ke DataFrame
            if isinstance(data_list[0], dict):
                # Format dictionary
                df = pd.DataFrame(data_list)
                # Normalize nama kolom
                column_mapping = {
                    'date': 'date', 'Date': 'date', 'datetime': 'date', 'time': 'date',
                    'open': 'Open', 'Open': 'Open', 'OPEN': 'Open',
                    'high': 'High', 'High': 'High', 'HIGH': 'High',
                    'low': 'Low', 'Low': 'Low', 'LOW': 'Low',
                    'close': 'Close', 'Close': 'Close', 'CLOSE': 'Close', 'price': 'Close', 'Price': 'Close',
                    'volume': 'Volume', 'Volume': 'Volume', 'VOLUME': 'Volume'
                }
                df.rename(columns=column_mapping, inplace=True)
            elif isinstance(data_list[0], list):
                # Format array/list
                df = pd.DataFrame(data_list, columns=['date', 'Open', 'High', 'Low', 'Close', 'Volume'])
            else:
                print(f"⚠️  Format data tidak dikenali: {type(data_list[0])}")
                return None
        
        # Pastikan kolom date ada dan convert ke datetime
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
        else:
            # Jika tidak ada date, gunakan waktu sekarang
            print("⚠️  Kolom 'date' tidak ditemukan, menggunakan waktu sekarang")
            df['date'] = datetime.now()
        
        # Pastikan kolom OHLC ada, jika tidak buat dari Close
        if 'Close' not in df.columns:
            # Coba cari kolom price
            if 'price' in df.columns:
                df['Close'] = df['price']
            else:
                print("❌ Kolom 'Close' atau 'price' tidak ditemukan")
                return None
        
        # Buat OHLC jika tidak ada
        if 'Open' not in df.columns:
            df['Open'] = df['Close']
        if 'High' not in df.columns:
            df['High'] = df['Close']
        if 'Low' not in df.columns:
            df['Low'] = df['Close']
        
        # Tambahkan Volume jika tidak ada
        if 'Volume' not in df.columns:
            df['Volume'] = 0
        
        # Urutkan berdasarkan tanggal
        df = df.sort_values('date')
        
        # Pilih kolom yang diperlukan
        df = df[['date', 'Open', 'High', 'Low', 'Close', 'Volume']]
        
        print(f"✅ Data berhasil diambil: {len(df)} records")
        if len(df) > 0:
            print(f"Periode: {df['date'].min()} sampai {df['date'].max()}")
        
        # Rate limiting untuk FreeCryptoAPI
        time.sleep(0.5)
        
        return df
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Error mengambil data dari FreeCryptoAPI: {e}")
        if hasattr(e, 'response') and e.response is not None:
            status_code = e.response.status_code
            print(f"   Status code: {status_code}")
            
            if status_code == 522:
                print(f"\n💡 Error 522: Server timeout")
                print(f"   FreeCryptoAPI server tidak merespons")
                print(f"   Kemungkinan server sedang down atau overloaded")
            elif status_code == 401:
                print(f"\n💡 Error 401: Unauthorized")
                print(f"   API key mungkin tidak valid atau expired")
                print(f"   Cek API key di https://freecryptoapi.com/")
            elif status_code == 429:
                print(f"\n💡 Error 429: Too Many Requests")
                print(f"   Rate limit tercapai, tunggu beberapa saat")
            
            try:
                error_detail = e.response.json()
                print(f"   Detail error: {error_detail}")
            except:
                if e.response.text:
                    print(f"   Response: {e.response.text[:200]}")
        
        print(f"\n💡 Saran:")
        print(f"   - Coba lagi dalam beberapa menit")
        print(f"   - Atau gunakan DATA_SOURCE lain di config.py:")
        print(f"     DATA_SOURCE = 'yfinance'  # atau 'coingecko'")
        return None
    except Exception as e:
        print(f"❌ Error memproses data dari FreeCryptoAPI: {e}")
        return None

def get_data_indodax(days_back):
    """
    Mengambil data historical dari Indodax API
    Note: Indodax API mungkin tidak menyediakan endpoint historical langsung
    Ini adalah implementasi alternatif
    """
    print("⚠️  Indodax API tidak menyediakan endpoint historical langsung")
    print("💡 Gunakan yfinance, coingecko, atau freecryptoapi untuk data historical")
    return None

def main():
    print("=" * 60)
    print("PENGAMBILAN DATA HISTORICAL CRYPTOCURRENCY")
    print("=" * 60)
    print()
    
    data = None
    
    if DATA_SOURCE == "yfinance":
        data = get_data_yfinance(SYMBOL, DAYS_BACK, INTERVAL)
    elif DATA_SOURCE == "coingecko":
        data = get_data_coingecko(DAYS_BACK, coin_id=COIN_ID, api_key=COINGECKO_API_KEY)
    elif DATA_SOURCE == "freecryptoapi":
        data = get_data_freecryptoapi(DAYS_BACK, symbol=FREECRYPTOAPI_SYMBOL, api_key=FREECRYPTOAPI_KEY)
    elif DATA_SOURCE == "indodax":
        data = get_data_indodax(DAYS_BACK)
    else:
        print(f"❌ Data source tidak dikenal: {DATA_SOURCE}")
        print(f"   Pilihan yang tersedia: yfinance, coingecko, freecryptoapi, indodax")
        return
    
    if data is None or data.empty:
        print("\n❌ Gagal mengambil data")
        return
    
    # Statistik
    print("\n" + "=" * 60)
    print("STATISTIK DATA")
    print("=" * 60)
    print(f"Total records: {len(data)}")
    print(f"Periode: {data['date'].min()} sampai {data['date'].max()}")
    
    if 'Close' in data.columns:
        print(f"Harga tertinggi: {data['Close'].max():,.2f}")
        print(f"Harga terendah: {data['Close'].min():,.2f}")
        print(f"Harga rata-rata: {data['Close'].mean():,.2f}")
        print(f"Perubahan: {((data['Close'].iloc[-1] / data['Close'].iloc[0]) - 1) * 100:.2f}%")
    
    # Simpan ke CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Tentukan nama coin untuk filename
    if DATA_SOURCE == "yfinance":
        coin_name = SYMBOL.replace("-", "").lower()  # BTC-USD -> btcusd
    elif DATA_SOURCE == "coingecko":
        coin_name = COIN_ID.replace("-", "_")  # bitcoin -> bitcoin, hype-token -> hype_token
    elif DATA_SOURCE == "freecryptoapi":
        coin_name = FREECRYPTOAPI_SYMBOL.lower()  # BTC -> btc
    else:
        coin_name = "crypto"
    filename = f"{coin_name}_historical_{DATA_SOURCE}_{timestamp}.csv"
    data.to_csv(filename, index=False)
    print(f"\n✅ Data disimpan ke: {filename}")
    
    # Tampilkan preview
    print("\n" + "=" * 60)
    print("PREVIEW DATA (5 baris terbaru)")
    print("=" * 60)
    print(data.tail())
    
    print("\n" + "=" * 60)
    print("SELESAI!")
    print("=" * 60)
    print(f"\n💡 Data siap digunakan untuk analisis dengan analisis_quant.py")
    print(f"   Set USE_CSV_DATA = True dan CSV_FILE = '{filename}'")

if __name__ == "__main__":
    main()

