#!/usr/bin/env python3
"""
Binance Data Wrapper
Wrapper untuk Binance API yang kompatibel dengan yfinance interface
Menggunakan python-binance library untuk mengakses Binance API
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import time

try:
    from binance.client import Client
    from binance.exceptions import BinanceAPIException, BinanceRequestException
except ImportError:
    print("⚠️  Library python-binance tidak ditemukan!")
    print("📦 Install dengan: pip install python-binance")
    Client = None

# Import config
try:
    from config import BINANCE_API_KEY, BINANCE_API_SECRET, ENABLE_BINANCE_API
except ImportError:
    BINANCE_API_KEY = None
    BINANCE_API_SECRET = None
    ENABLE_BINANCE_API = False


def convert_symbol_to_binance(symbol: str) -> str:
    """
    Convert symbol format dari yfinance ke Binance
    
    Args:
        symbol: Symbol dalam format yfinance (e.g., "BTC-USD", "ETH-USD")
    
    Returns:
        Symbol dalam format Binance (e.g., "BTCUSDT", "ETHUSDT")
    """
    # Remove -USD suffix dan tambahkan USDT
    if symbol.endswith("-USD"):
        base = symbol.replace("-USD", "")
        return f"{base}USDT"
    elif symbol.endswith("/USD"):
        base = symbol.replace("/USD", "")
        return f"{base}USDT"
    else:
        # Jika sudah format Binance, return as is
        return symbol.upper()


def convert_interval_to_binance(interval: str) -> str:
    """
    Convert interval format dari yfinance ke Binance
    
    Args:
        interval: Interval dalam format yfinance (e.g., "1m", "5m", "15m", "1h", "1d")
    
    Returns:
        Interval dalam format Binance (e.g., "1m", "5m", "15m", "1h", "1d")
    """
    if Client is None:
        # Fallback jika Client tidak tersedia
        interval_map_str = {
            "1m": "1m", "2m": "3m", "5m": "5m", "15m": "15m",
            "30m": "30m", "60m": "1h", "90m": "1h",
            "1h": "1h", "4h": "4h", "1d": "1d",
            "1w": "1w", "1mo": "1M"
        }
        return interval_map_str.get(interval.lower(), "1h")
    
    # Mapping interval yfinance ke Binance
    interval_map = {
        "1m": Client.KLINE_INTERVAL_1MINUTE,
        "2m": Client.KLINE_INTERVAL_3MINUTE,  # Binance tidak punya 2m, gunakan 3m
        "5m": Client.KLINE_INTERVAL_5MINUTE,
        "15m": Client.KLINE_INTERVAL_15MINUTE,
        "30m": Client.KLINE_INTERVAL_30MINUTE,
        "60m": Client.KLINE_INTERVAL_1HOUR,
        "90m": Client.KLINE_INTERVAL_1HOUR,  # Binance tidak punya 90m, gunakan 1h
        "1h": Client.KLINE_INTERVAL_1HOUR,
        "4h": Client.KLINE_INTERVAL_4HOUR,
        "1d": Client.KLINE_INTERVAL_1DAY,
        "1w": Client.KLINE_INTERVAL_1WEEK,
        "1mo": Client.KLINE_INTERVAL_1MONTH,
    }
    
    # Jika interval sudah dalam format Binance constant, return as is
    if hasattr(Client, 'KLINE_INTERVAL_1MINUTE') and interval.startswith('KLINE_INTERVAL'):
        return interval
    
    # Convert dari yfinance format
    return interval_map.get(interval.lower(), Client.KLINE_INTERVAL_1HOUR)


def get_max_days_by_interval(interval: str) -> Optional[int]:
    """
    Get maksimal days yang didukung berdasarkan interval (untuk Binance)
    
    Args:
        interval: Interval dalam format yfinance
    
    Returns:
        Maksimal days atau None jika tidak ada limit
    """
    # Binance memiliki limit berbeda dari yfinance
    # Binance bisa fetch lebih banyak data untuk interval yang sama
    max_days_by_interval = {
        "1m": 7,      # Binance limit: maksimal 7 hari untuk 1m
        "2m": 30,    # Gunakan 3m, maksimal 30 hari
        "5m": 30,    # Maksimal 30 hari
        "15m": 30,   # Maksimal 30 hari
        "30m": 30,   # Maksimal 30 hari
        "60m": 365,  # Maksimal 365 hari (1h)
        "90m": 365,  # Gunakan 1h, maksimal 365 hari
        "1h": 365,   # Maksimal 365 hari
        "4h": 365,   # Maksimal 365 hari
        "1d": None,  # Tidak ada limit (bisa sampai 1000+ hari)
        "1w": None,  # Tidak ada limit
        "1mo": None  # Tidak ada limit
    }
    
    return max_days_by_interval.get(interval.lower())


def get_data_binance(symbol: str, days_back: int, interval: str, 
                     api_key: Optional[str] = None, 
                     api_secret: Optional[str] = None) -> Optional[pd.DataFrame]:
    """
    Mengambil data historical dari Binance API
    Kompatibel dengan interface yfinance
    
    Args:
        symbol: Trading symbol (format yfinance: "BTC-USD" atau Binance: "BTCUSDT")
        days_back: Berapa hari ke belakang
        interval: Interval data (format yfinance: "1m", "5m", "15m", "1h", "1d")
        api_key: Binance API Key (optional, bisa dari config)
        api_secret: Binance API Secret (optional, bisa dari config)
    
    Returns:
        DataFrame dengan kolom: date, Open, High, Low, Close, Volume
        Format sama dengan yfinance untuk kompatibilitas
    """
    if Client is None:
        print("❌ Library python-binance tidak terinstall")
        print("📦 Install dengan: pip install python-binance")
        return None
    
    # Gunakan API key dari parameter atau config
    api_key = api_key or BINANCE_API_KEY
    api_secret = api_secret or BINANCE_API_SECRET
    
    print(f"Mengambil data dari Binance API...")
    print(f"Symbol: {symbol}")
    print(f"Periode: {days_back} hari terakhir")
    print(f"Interval: {interval}")
    
    # Convert symbol format
    binance_symbol = convert_symbol_to_binance(symbol)
    print(f"Binance Symbol: {binance_symbol}")
    
    # Convert interval format
    try:
        binance_interval = convert_interval_to_binance(interval)
    except Exception as e:
        print(f"⚠️  Error converting interval: {e}")
        print(f"   Menggunakan default interval: 1h")
        binance_interval = Client.KLINE_INTERVAL_1HOUR
    
    # Validasi dan auto-adjust DAYS_BACK berdasarkan interval
    max_days = get_max_days_by_interval(interval)
    if max_days is not None and days_back > max_days:
        print(f"\n⚠️  PERINGATAN: Interval {interval} hanya mendukung maksimal {max_days} hari")
        print(f"   DAYS_BACK ({days_back}) akan disesuaikan menjadi {max_days} hari")
        days_back = max_days
    
    # Calculate start and end time
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days_back)
    
    try:
        # Initialize Binance client
        # Untuk public endpoints (klines), tidak perlu API key
        # Tapi lebih baik gunakan API key untuk rate limit yang lebih tinggi
        # Handle SSL verification issues (untuk testing, bisa disable)
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Setup requests params dengan support proxy dan SSL fix
        requests_params = {
            'timeout': 30,
            'verify': False  # Disable SSL verification untuk testing (tidak aman untuk production!)
        }
        
        # Support proxy dari environment variables
        proxies = {}
        if os.environ.get('HTTP_PROXY'):
            proxies['http'] = os.environ.get('HTTP_PROXY')
        if os.environ.get('HTTPS_PROXY'):
            proxies['https'] = os.environ.get('HTTPS_PROXY')
        if proxies:
            requests_params['proxies'] = proxies
            print(f"🔗 Menggunakan proxy: {proxies}")
        
        if api_key and api_secret:
            print("🔑 Menggunakan Binance API dengan autentikasi")
            client = Client(api_key, api_secret, requests_params=requests_params)
        else:
            print("ℹ️  Menggunakan Binance API tanpa autentikasi (public endpoints)")
            print("   ⚠️  Rate limit lebih rendah, gunakan API key untuk rate limit lebih tinggi")
            client = Client(requests_params=requests_params)
        
        # Get klines (candlestick data)
        print(f"📡 Mengambil klines dari Binance...")
        print(f"   Start: {start_time}")
        print(f"   End: {end_time}")
        print(f"   Interval: {binance_interval}")
        
        klines = client.get_historical_klines(
            symbol=binance_symbol,
            interval=binance_interval,
            start_str=start_time.strftime("%d %b %Y %H:%M:%S"),
            end_str=end_time.strftime("%d %b %Y %H:%M:%S")
        )
        
        if not klines or len(klines) == 0:
            print("⚠️  Data kosong dari Binance")
            return None
        
        print(f"✅ Menerima {len(klines)} klines dari Binance")
        
        # Convert klines ke DataFrame
        # Format klines: [Open time, Open, High, Low, Close, Volume, Close time, Quote volume, Trades, ...]
        df = pd.DataFrame(klines, columns=[
            'Open time', 'Open', 'High', 'Low', 'Close', 'Volume',
            'Close time', 'Quote volume', 'Trades',
            'Taker buy base', 'Taker buy quote', 'Ignore'
        ])
        
        # Convert data types
        df['Open time'] = pd.to_datetime(df['Open time'], unit='ms')
        df['Close time'] = pd.to_datetime(df['Close time'], unit='ms')
        
        # Convert price columns to float
        price_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in price_columns:
            df[col] = df[col].astype(float)
        
        # Rename columns untuk kompatibilitas dengan yfinance
        df.rename(columns={
            'Open time': 'date',
            'Open': 'Open',
            'High': 'High',
            'Low': 'Low',
            'Close': 'Close',
            'Volume': 'Volume'
        }, inplace=True)
        
        # Pilih kolom yang diperlukan (sama dengan yfinance)
        df = df[['date', 'Open', 'High', 'Low', 'Close', 'Volume']]
        
        # Sort by date
        df = df.sort_values('date')
        
        # Reset index
        df.reset_index(drop=True, inplace=True)
        
        print(f"✅ Data berhasil diambil: {len(df)} records")
        if 'date' in df.columns:
            print(f"Periode: {df['date'].min()} sampai {df['date'].max()}")
        
        # Rate limiting untuk Binance API
        time.sleep(0.1)  # Small delay untuk menghindari rate limit
        
        return df
        
    except BinanceAPIException as e:
        error_msg = f"Binance API Error: {e.status_code} - {e.message}"
        print(f"❌ {error_msg}")
        
        if e.status_code == 400:
            print(f"💡 Symbol '{binance_symbol}' mungkin tidak valid di Binance")
            print(f"   Cek daftar trading pairs di: https://www.binance.com/en/trade")
        elif e.status_code == 429:
            print(f"💡 Rate limit tercapai - tunggu beberapa saat")
        elif e.status_code == 418:
            print(f"💡 IP banned - tunggu beberapa saat atau gunakan API key")
        
        return None
        
    except BinanceRequestException as e:
        error_msg = f"Binance Request Error: {e.status_code} - {e.message}"
        print(f"❌ {error_msg}")
        return None
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error mengambil data dari Binance: {error_msg}")
        
        if "timeout" in error_msg.lower():
            print(f"💡 Request timeout - coba lagi nanti")
        elif "connection" in error_msg.lower():
            print(f"💡 Connection error - cek koneksi internet")
        
        return None


def get_ticker_price(symbol: str, api_key: Optional[str] = None, 
                     api_secret: Optional[str] = None) -> Optional[float]:
    """
    Get current price untuk symbol tertentu (kompatibel dengan yfinance)
    
    Args:
        symbol: Trading symbol (format yfinance: "BTC-USD" atau Binance: "BTCUSDT")
        api_key: Binance API Key (optional)
        api_secret: Binance API Secret (optional)
    
    Returns:
        Current price atau None jika error
    """
    if Client is None:
        return None
    
    try:
        binance_symbol = convert_symbol_to_binance(symbol)
        
        if api_key and api_secret:
            client = Client(api_key, api_secret)
        else:
            client = Client()
        
        ticker = client.get_symbol_ticker(symbol=binance_symbol)
        return float(ticker['price'])
        
    except Exception as e:
        print(f"⚠️  Error getting ticker price: {e}")
        return None


def download_multiple_symbols(symbols: List[str], period: str = "90d", 
                              interval: str = "1d",
                              api_key: Optional[str] = None,
                              api_secret: Optional[str] = None) -> pd.DataFrame:
    """
    Download data untuk multiple symbols sekaligus (kompatibel dengan yfinance.download)
    
    Args:
        symbols: List of symbols (format yfinance: ["BTC-USD", "ETH-USD"])
        period: Period string (e.g., "7d", "30d", "90d", "1y")
        interval: Interval (e.g., "1d", "1h", "15m")
        api_key: Binance API Key (optional)
        api_secret: Binance API Secret (optional)
    
    Returns:
        DataFrame dengan MultiIndex (Ticker, Price Type) seperti yfinance.download
    """
    if Client is None:
        return pd.DataFrame()
    
    # Convert period string ke days
    period_map = {
        "1d": 1, "7d": 7, "30d": 30, "90d": 90,
        "1mo": 30, "3mo": 90, "6mo": 180, "1y": 365
    }
    days_back = period_map.get(period.lower(), 90)
    
    all_data = {}
    
    for symbol in symbols:
        try:
            df = get_data_binance(symbol, days_back, interval, api_key, api_secret)
            if df is not None and not df.empty:
                # Convert ke format MultiIndex seperti yfinance
                binance_symbol = convert_symbol_to_binance(symbol)
                df_multi = pd.DataFrame({
                    (binance_symbol, 'Open'): df['Open'],
                    (binance_symbol, 'High'): df['High'],
                    (binance_symbol, 'Low'): df['Low'],
                    (binance_symbol, 'Close'): df['Close'],
                    (binance_symbol, 'Volume'): df['Volume']
                }, index=df['date'])
                all_data[binance_symbol] = df_multi
        except Exception as e:
            print(f"⚠️  Error downloading {symbol}: {e}")
            continue
    
    if not all_data:
        return pd.DataFrame()
    
    # Combine all dataframes
    result = pd.concat(all_data.values(), axis=1)
    result.columns = pd.MultiIndex.from_tuples(result.columns)
    
    return result


# Class wrapper untuk kompatibilitas dengan yfinance.Ticker
class Ticker:
    """
    Wrapper class untuk kompatibilitas dengan yfinance.Ticker
    """
    
    def __init__(self, symbol: str, api_key: Optional[str] = None, 
                 api_secret: Optional[str] = None):
        """
        Initialize Ticker (kompatibel dengan yfinance.Ticker)
        
        Args:
            symbol: Trading symbol (format yfinance: "BTC-USD")
            api_key: Binance API Key (optional)
            api_secret: Binance API Secret (optional)
        """
        self.symbol = symbol
        self.binance_symbol = convert_symbol_to_binance(symbol)
        self.api_key = api_key or BINANCE_API_KEY
        self.api_secret = api_secret or BINANCE_API_SECRET
        
        if Client is None:
            raise ImportError("python-binance library tidak terinstall")
        
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Setup requests params dengan support proxy
        requests_params = {
            'timeout': 30,
            'verify': False  # Disable SSL verification untuk testing
        }
        
        # Support proxy dari environment variables
        proxies = {}
        if os.environ.get('HTTP_PROXY'):
            proxies['http'] = os.environ.get('HTTP_PROXY')
        if os.environ.get('HTTPS_PROXY'):
            proxies['https'] = os.environ.get('HTTPS_PROXY')
        if proxies:
            requests_params['proxies'] = proxies
        
        if self.api_key and self.api_secret:
            self.client = Client(self.api_key, self.api_secret, requests_params=requests_params)
        else:
            self.client = Client(requests_params=requests_params)
    
    def history(self, period: Optional[str] = None, 
                start: Optional[datetime] = None,
                end: Optional[datetime] = None,
                interval: str = "1d",
                **kwargs) -> pd.DataFrame:
        """
        Get historical data (kompatibel dengan yfinance.Ticker.history)
        
        Args:
            period: Period string (e.g., "7d", "30d", "1y") - alternative to start/end
            start: Start datetime
            end: End datetime
            interval: Interval (e.g., "1d", "1h", "15m")
            **kwargs: Additional arguments (ignored for compatibility)
        
        Returns:
            DataFrame dengan DatetimeIndex dan kolom: Open, High, Low, Close, Volume
        """
        # Convert period ke days_back
        if period:
            period_map = {
                "1d": 1, "7d": 7, "30d": 30, "90d": 90,
                "1mo": 30, "3mo": 90, "6mo": 180, "1y": 365
            }
            days_back = period_map.get(period.lower(), 90)
        elif start and end:
            days_back = (end - start).days
        else:
            days_back = 90  # Default
        
        # Get data
        df = get_data_binance(self.symbol, days_back, interval, 
                             self.api_key, self.api_secret)
        
        if df is None or df.empty:
            return pd.DataFrame()
        
        # Set date sebagai index (seperti yfinance)
        df.set_index('date', inplace=True)
        
        return df


# Alias untuk kompatibilitas
download = download_multiple_symbols

