#!/usr/bin/env python3
"""
Binance USDⓈ-M Futures API Integration
Wrapper untuk Binance Futures API yang kompatibel dengan Spot API interface
Menggunakan python-binance library atau direct HTTP requests

Base URL: https://fapi.binance.com
Testnet: https://demo-fapi.binance.com

Reference: https://developers.binance.com/docs/derivatives/usds-margined-futures
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import time
import os
import requests
import json
import hmac
import hashlib
import urllib.parse

try:
    from binance.client import Client
    from binance.exceptions import BinanceAPIException, BinanceRequestException
    HAS_BINANCE_LIB = True
except ImportError:
    HAS_BINANCE_LIB = False
    Client = None

# Import config
try:
    from src.utils.config import BINANCE_API_KEY, BINANCE_API_SECRET, ENABLE_BINANCE_API
except ImportError:
    BINANCE_API_KEY = None
    BINANCE_API_SECRET = None
    ENABLE_BINANCE_API = False

# Binance Futures API Base URL
FUTURES_BASE_URL = "https://fapi.binance.com"
FUTURES_TESTNET_URL = "https://demo-fapi.binance.com"

# Rate limiting: delay minimum antara requests (dalam detik)
# Binance Futures API rate limit: 1200 requests per minute per IP
# Untuk aman, kita gunakan delay 0.1 detik = max 600 requests per minute
MIN_REQUEST_DELAY = 0.1  # 100ms delay minimum antara requests
_last_request_time = 0  # Track waktu request terakhir


def _rate_limit_delay():
    """Delay untuk rate limiting"""
    global _last_request_time
    current_time = time.time()
    time_since_last = current_time - _last_request_time
    if time_since_last < MIN_REQUEST_DELAY:
        sleep_time = MIN_REQUEST_DELAY - time_since_last
        time.sleep(sleep_time)
    _last_request_time = time.time()


def _handle_binance_error(response, endpoint_name: str):
    """
    Handle error response dari Binance API
    
    Args:
        response: requests.Response object
        endpoint_name: Nama endpoint untuk logging
    
    Returns:
        Tuple (should_retry: bool, error_message: str)
    """
    status_code = response.status_code
    
    if status_code == 200:
        return False, None
    
    error_data = None
    try:
        error_data = response.json()
        error_msg = error_data.get('msg', response.text[:200]) if isinstance(error_data, dict) else response.text[:200]
        error_code = error_data.get('code', status_code) if isinstance(error_data, dict) else status_code
    except:
        error_msg = response.text[:200]
        error_code = status_code
    
    # 418: IP banned
    if status_code == 418:
        # Parse ban time dari response jika ada
        ban_until = None
        if error_data and isinstance(error_data, dict) and 'banned until' in error_msg.lower():
            # Extract timestamp dari message jika ada
            import re
            match = re.search(r'until (\d+)', error_msg)
            if match:
                ban_until = int(match.group(1)) / 1000  # Convert dari ms ke seconds
                from datetime import datetime
                ban_until_dt = datetime.fromtimestamp(ban_until)
                print(f"🚫 [RATE LIMIT] IP banned until: {ban_until_dt}")
                print(f"   Current time: {datetime.now()}")
                wait_time = ban_until - time.time()
                if wait_time > 0:
                    print(f"   ⏳ Please wait {int(wait_time / 60)} minutes before retrying")
                else:
                    print(f"   ✅ Ban period should be over, but API still returns 418")
        
        print(f"❌ [RATE LIMIT] IP banned (418) for endpoint: {endpoint_name}")
        print(f"   Error: {error_msg}")
        print(f"   💡 Solutions:")
        print(f"      1. Wait for the ban to expire (check ban_until time above)")
        print(f"      2. Use Binance API key for higher rate limits")
        print(f"      3. Reduce request frequency (add delays between requests)")
        print(f"      4. Use WebSocket for live updates instead of REST API")
        return False, f"IP banned: {error_msg}"
    
    # 429: Rate limit exceeded
    elif status_code == 429:
        print(f"⚠️  [RATE LIMIT] Rate limit exceeded (429) for endpoint: {endpoint_name}")
        print(f"   Error: {error_msg}")
        print(f"   💡 Wait a few seconds before retrying")
        # Bisa retry setelah delay
        return True, f"Rate limit exceeded: {error_msg}"
    
    # 400: Bad request
    elif status_code == 400:
        print(f"❌ [ERROR] Bad request (400) for endpoint: {endpoint_name}")
        print(f"   Error: {error_msg}")
        return False, f"Bad request: {error_msg}"
    
    # 401: Unauthorized
    elif status_code == 401:
        print(f"❌ [ERROR] Unauthorized (401) for endpoint: {endpoint_name}")
        print(f"   Error: {error_msg}")
        return False, f"Unauthorized: {error_msg}"
    
    # Other errors
    else:
        print(f"❌ [ERROR] HTTP {status_code} for endpoint: {endpoint_name}")
        print(f"   Error: {error_msg}")
        return False, f"HTTP {status_code}: {error_msg}"


def get_futures_client(api_key: Optional[str] = None, 
                      api_secret: Optional[str] = None,
                      testnet: bool = False) -> Optional[object]:
    """
    Get Binance Futures client
    
    Args:
        api_key: Binance API Key (optional)
        api_secret: Binance API Secret (optional)
        testnet: Use testnet (default: False)
    
    Returns:
        Binance Futures client atau None jika library tidak tersedia
    """
    if not HAS_BINANCE_LIB:
        return None
    
    api_key = api_key or BINANCE_API_KEY
    api_secret = api_secret or BINANCE_API_SECRET
    
    try:
        if testnet:
            # Note: python-binance mungkin tidak support testnet langsung
            # Akan menggunakan direct HTTP requests untuk testnet
            return None
        
        if api_key and api_secret:
            # Create client with API credentials
            # Note: python-binance Client default untuk spot, perlu modifikasi untuk futures
            # Untuk sekarang, kita akan gunakan direct HTTP requests
            return {"api_key": api_key, "api_secret": api_secret}
        else:
            return {"api_key": None, "api_secret": None}
    except Exception as e:
        print(f"⚠️  Error creating futures client: {e}")
        return None


def get_futures_exchange_info(api_key: Optional[str] = None,
                              api_secret: Optional[str] = None,
                              testnet: bool = False) -> Optional[Dict]:
    """
    Get exchange information for USDⓈ-M Futures
    
    Endpoint: GET /fapi/v1/exchangeInfo
    
    Args:
        api_key: Binance API Key (optional, untuk rate limit lebih tinggi)
        api_secret: Binance API Secret (optional)
        testnet: Use testnet (default: False)
    
    Returns:
        Dictionary dengan exchange info atau None jika error
    """
    base_url = FUTURES_TESTNET_URL if testnet else FUTURES_BASE_URL
    url = f"{base_url}/fapi/v1/exchangeInfo"
    
    print(f"🔵 [FUTURES API] Hitting endpoint: GET /fapi/v1/exchangeInfo")
    print(f"   URL: {url}")
    print(f"   Testnet: {testnet}")
    
    try:
        response = requests.get(url, timeout=30)
        print(f"   ✅ Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            print(f"❌ Error getting futures exchange info: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return None
    except Exception as e:
        print(f"❌ Exception getting futures exchange info: {e}")
        return None


def get_futures_symbols(quote_asset: str = "USDT",
                       api_key: Optional[str] = None,
                       api_secret: Optional[str] = None,
                       testnet: bool = False) -> List[str]:
    """
    Get list of symbols available in USDⓈ-M Futures
    
    Args:
        quote_asset: Quote asset filter (default: "USDT")
        api_key: Binance API Key (optional)
        api_secret: Binance API Secret (optional)
        testnet: Use testnet (default: False)
    
    Returns:
        List of symbols (e.g., ["BTCUSDT", "ETHUSDT", ...])
    """
    exchange_info = get_futures_exchange_info(api_key, api_secret, testnet)
    
    if not exchange_info:
        return []
    
    symbols = []
    for symbol_info in exchange_info.get('symbols', []):
        if symbol_info.get('status') == 'TRADING' and symbol_info.get('quoteAsset') == quote_asset:
            symbols.append(symbol_info.get('symbol'))
    
    return sorted(symbols)


def get_futures_klines(symbol: str,
                      interval: str,
                      start_time: Optional[datetime] = None,
                      end_time: Optional[datetime] = None,
                      limit: int = 500,
                      api_key: Optional[str] = None,
                      api_secret: Optional[str] = None,
                      testnet: bool = False) -> Optional[pd.DataFrame]:
    """
    Get klines (candlestick) data from USDⓈ-M Futures
    
    Endpoint: GET /fapi/v1/klines
    
    Args:
        symbol: Trading symbol (e.g., "BTCUSDT")
        interval: Kline interval (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M)
        start_time: Start time (optional)
        end_time: End time (optional)
        limit: Number of klines to return (default: 500, max: 1500)
        api_key: Binance API Key (optional)
        api_secret: Binance API Secret (optional)
        testnet: Use testnet (default: False)
    
    Returns:
        DataFrame dengan kolom: date, Open, High, Low, Close, Volume
        Format sama dengan spot API untuk kompatibilitas
    """
    base_url = FUTURES_TESTNET_URL if testnet else FUTURES_BASE_URL
    url = f"{base_url}/fapi/v1/klines"
    
    params = {
        'symbol': symbol.upper(),
        'interval': interval,
        'limit': min(limit, 1500)  # Max 1500
    }
    
    if start_time:
        params['startTime'] = int(start_time.timestamp() * 1000)
    if end_time:
        params['endTime'] = int(end_time.timestamp() * 1000)
    
    print(f"🔵 [FUTURES API] Hitting endpoint: GET /fapi/v1/klines")
    print(f"   URL: {url}")
    print(f"   Symbol: {symbol.upper()}, Interval: {interval}, Limit: {params['limit']}")
    if start_time:
        print(f"   Start time: {start_time}")
    if end_time:
        print(f"   End time: {end_time}")
    print(f"   Testnet: {testnet}")
    
    # Rate limiting: delay sebelum request
    _rate_limit_delay()
    
    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"   ✅ Response status: {response.status_code}")
        
        # Handle errors (418, 429, dll)
        if response.status_code != 200:
            should_retry, error_msg = _handle_binance_error(response, "GET /fapi/v1/klines")
            if response.status_code == 418:
                # IP banned - tidak bisa retry, return None
                return None
            elif should_retry and response.status_code == 429:
                # Rate limit - retry setelah delay
                print(f"   ⏳ Waiting 5 seconds before retry...")
                time.sleep(5)
                response = requests.get(url, params=params, timeout=30)
                print(f"   ✅ Retry response status: {response.status_code}")
                if response.status_code != 200:
                    should_retry, error_msg = _handle_binance_error(response, "GET /fapi/v1/klines (retry)")
                    if response.status_code != 200:
                        return None
        
        if response.status_code == 200:
            klines = response.json()
            print(f"   📊 Received {len(klines)} klines")
            
            if not klines:
                print(f"   ⚠️  No klines data returned")
                return pd.DataFrame()
            
            # Convert klines to DataFrame
            # Format: [Open time, Open, High, Low, Close, Volume, Close time, Quote volume, Trades, ...]
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
            
            # Rename columns untuk kompatibilitas dengan spot API
            df = df.rename(columns={
                'Open time': 'date',
                'Open': 'Open',
                'High': 'High',
                'Low': 'Low',
                'Close': 'Close',
                'Volume': 'Volume'
            })
            
            # Pilih kolom yang diperlukan (date sebagai kolom, bukan index untuk kompatibilitas)
            df = df[['date', 'Open', 'High', 'Low', 'Close', 'Volume']]
            
            # Sort by date
            df = df.sort_values('date')
            
            # Reset index untuk memastikan date adalah kolom
            df.reset_index(drop=True, inplace=True)
            
            print(f"   ✅ Successfully converted to DataFrame: {len(df)} rows")
            
            # Debug: Validasi data yang diterima
            print(f"   🔍 [DEBUG] Validating DataFrame:")
            print(f"      - Shape: {df.shape}")
            print(f"      - Columns: {list(df.columns)}")
            print(f"      - Date range: {df['date'].min()} to {df['date'].max()}")
            print(f"      - Price range: Close min={df['Close'].min():.8f}, max={df['Close'].max():.8f}")
            print(f"      - Volume range: min={df['Volume'].min():.2f}, max={df['Volume'].max():.2f}")
            print(f"      - Null values: {df.isnull().sum().to_dict()}")
            print(f"      - Sample data (first 3 rows):")
            for idx, row in df.head(3).iterrows():
                print(f"         Row {idx}: date={row['date']}, Close={row['Close']:.8f}, Volume={row['Volume']:.2f}")
            
            # Validasi: pastikan tidak ada null values di kolom penting
            if df['Close'].isnull().any():
                print(f"   ⚠️  WARNING: Found null values in Close column!")
                df = df.dropna(subset=['Close'])
                print(f"      After dropna: {len(df)} rows")
            
            if len(df) == 0:
                print(f"   ❌ ERROR: DataFrame is empty after processing!")
                return pd.DataFrame()
            
            print(f"   ✅ DataFrame validation passed: {len(df)} valid rows")
            return df
        else:
            # Error sudah di-handle di atas
            return None
    except Exception as e:
        print(f"❌ Exception getting futures klines: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_futures_ticker_price(symbol: Optional[str] = None,
                            api_key: Optional[str] = None,
                            api_secret: Optional[str] = None,
                            testnet: bool = False) -> Optional[Dict]:
    """
    Get current price for symbol(s) in USDⓈ-M Futures
    
    Endpoint: GET /fapi/v1/ticker/price
    
    Args:
        symbol: Trading symbol (e.g., "BTCUSDT"). If None, returns all symbols
        api_key: Binance API Key (optional)
        api_secret: Binance API Secret (optional)
        testnet: Use testnet (default: False)
    
    Returns:
        Dictionary dengan price data atau list of dictionaries jika symbol=None
    """
    base_url = FUTURES_TESTNET_URL if testnet else FUTURES_BASE_URL
    url = f"{base_url}/fapi/v1/ticker/price"
    
    params = {}
    if symbol:
        params['symbol'] = symbol.upper()
    
    print(f"🔵 [FUTURES API] Hitting endpoint: GET /fapi/v1/ticker/price")
    print(f"   URL: {url}")
    if symbol:
        print(f"   Symbol: {symbol.upper()}")
    else:
        print(f"   Getting all symbols")
    print(f"   Testnet: {testnet}")
    
    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"   ✅ Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            print(f"❌ Error getting futures ticker price: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return None
    except Exception as e:
        print(f"❌ Exception getting futures ticker price: {e}")
        return None


def get_futures_24h_ticker(symbol: Optional[str] = None,
                           api_key: Optional[str] = None,
                           api_secret: Optional[str] = None,
                           testnet: bool = False) -> Optional[pd.DataFrame]:
    """
    Get 24h ticker statistics untuk symbol(s) di USDⓈ-M Futures
    
    Endpoint: GET /fapi/v1/ticker/24hr
    
    Args:
        symbol: Trading symbol (optional, if None returns all symbols)
        api_key: Binance API Key (optional)
        api_secret: Binance API Secret (optional)
        testnet: Use testnet (default: False)
    
    Returns:
        DataFrame dengan 24h ticker statistics
    """
    base_url = FUTURES_TESTNET_URL if testnet else FUTURES_BASE_URL
    url = f"{base_url}/fapi/v1/ticker/24hr"
    
    params = {}
    if symbol:
        params['symbol'] = symbol.upper()
    
    print(f"🔵 [FUTURES API] Hitting endpoint: GET /fapi/v1/ticker/24hr")
    print(f"   URL: {url}")
    if symbol:
        print(f"   Symbol: {symbol.upper()}")
    else:
        print(f"   Getting all symbols")
    print(f"   Testnet: {testnet}")
    
    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"   ✅ Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Convert to DataFrame
            if isinstance(data, list):
                df = pd.DataFrame(data)
            else:
                df = pd.DataFrame([data])
            
            # Convert numeric columns
            numeric_columns = ['priceChange', 'priceChangePercent', 'weightedAvgPrice',
                             'prevClosePrice', 'lastPrice', 'bidPrice', 'askPrice',
                             'openPrice', 'highPrice', 'lowPrice', 'volume', 'quoteVolume',
                             'openTime', 'closeTime', 'firstId', 'lastId', 'count']
            
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            return df
        else:
            print(f"❌ Error getting futures 24h ticker: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return None
    except Exception as e:
        print(f"❌ Exception getting futures 24h ticker: {e}")
        return None


def get_futures_orderbook(symbol: str,
                          limit: int = 100,
                          api_key: Optional[str] = None,
                          api_secret: Optional[str] = None,
                          testnet: bool = False) -> Optional[Dict]:
    """
    Get orderbook (depth) for symbol in USDⓈ-M Futures
    
    Endpoint: GET /fapi/v1/depth
    
    Args:
        symbol: Trading symbol (e.g., "BTCUSDT")
        limit: Orderbook depth (default: 100, valid: 5, 10, 20, 50, 100, 500, 1000)
        api_key: Binance API Key (optional)
        api_secret: Binance API Secret (optional)
        testnet: Use testnet (default: False)
    
    Returns:
        Dictionary dengan orderbook data (bids, asks) atau None jika error
    """
    base_url = FUTURES_TESTNET_URL if testnet else FUTURES_BASE_URL
    url = f"{base_url}/fapi/v1/depth"
    
    params = {
        'symbol': symbol.upper(),
        'limit': limit
    }
    
    print(f"🔵 [FUTURES API] Hitting endpoint: GET /fapi/v1/depth")
    print(f"   URL: {url}")
    print(f"   Symbol: {symbol.upper()}, Limit: {limit}")
    print(f"   Testnet: {testnet}")
    
    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"   ✅ Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            print(f"❌ Error getting futures orderbook: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return None
    except Exception as e:
        print(f"❌ Exception getting futures orderbook: {e}")
        return None


def _generate_signature(query_string: str, api_secret: str) -> str:
    """
    Generate HMAC SHA256 signature for Binance API
    
    Args:
        query_string: Query string parameters
        api_secret: Binance API Secret
    
    Returns:
        Signature string (hexadecimal)
    """
    return hmac.new(
        api_secret.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()


def get_futures_position_risk(api_key: str,
                             api_secret: str,
                             symbol: Optional[str] = None,
                             testnet: bool = False,
                             recv_window: int = 5000) -> Optional[List[Dict]]:
    """
    Get position risk information (signed endpoint)
    
    Endpoint: GET /fapi/v2/positionRisk
    
    Args:
        api_key: Binance API Key (required)
        api_secret: Binance API Secret (required)
        symbol: Trading symbol filter (optional, if None returns all positions)
        testnet: Use testnet (default: False)
    
    Returns:
        List of position risk dictionaries atau None jika error
    """
    base_url = FUTURES_TESTNET_URL if testnet else FUTURES_BASE_URL
    url = f"{base_url}/fapi/v2/positionRisk"
    
    # Prepare parameters for signed endpoint
    params = {
        'timestamp': int(time.time() * 1000),
        'recvWindow': recv_window
    }
    
    if symbol:
        params['symbol'] = symbol.upper()
    
    # Create query string (without signature)
    query_string = urllib.parse.urlencode(params)
    
    # Generate HMAC SHA256 signature
    signature = _generate_signature(query_string, api_secret)
    params['signature'] = signature
    
    # Make request with authentication
    headers = {
        'X-MBX-APIKEY': api_key
    }
    
    print(f"🔵 [FUTURES API] Hitting endpoint: GET /fapi/v2/positionRisk (SIGNED)")
    print(f"   URL: {url}")
    if symbol:
        print(f"   Symbol: {symbol.upper()}")
    else:
        print(f"   Getting all positions")
    print(f"   Testnet: {testnet}")
    print(f"   RecvWindow: {recv_window}")
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        print(f"   ✅ Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            # Return as list (even if single position)
            return data if isinstance(data, list) else [data]
        else:
            print(f"❌ Error getting futures position risk: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return None
    except Exception as e:
        print(f"❌ Exception getting futures position risk: {e}")
        import traceback
        traceback.print_exc()
        return None


def convert_futures_symbol_to_yfinance(symbol: str) -> str:
    """
    Convert futures symbol format ke yfinance format
    
    Args:
        symbol: Symbol dalam format Binance Futures (e.g., "BTCUSDT")
    
    Returns:
        Symbol dalam format yfinance (e.g., "BTC-USD")
    """
    if symbol.endswith("USDT"):
        base = symbol.replace("USDT", "")
        return f"{base}-USD"
    elif symbol.endswith("BUSD"):
        base = symbol.replace("BUSD", "")
        return f"{base}-USD"
    else:
        # Jika tidak ada suffix, tambahkan -USD
        return f"{symbol}-USD"


def get_futures_data(symbol: str,
                    days_back: int,
                    interval: str,
                    api_key: Optional[str] = None,
                    api_secret: Optional[str] = None,
                    testnet: bool = False) -> Optional[pd.DataFrame]:
    """
    Get historical data from USDⓈ-M Futures (kompatibel dengan get_data_binance)
    
    Args:
        symbol: Trading symbol (format yfinance: "BTC-USD" atau Binance: "BTCUSDT")
        days_back: Berapa hari ke belakang
        interval: Interval data (1m, 5m, 15m, 1h, 4h, 1d, etc.)
        api_key: Binance API Key (optional)
        api_secret: Binance API Secret (optional)
        testnet: Use testnet (default: False)
    
    Returns:
        DataFrame dengan kolom: date, Open, High, Low, Close, Volume
        Format sama dengan spot API untuk kompatibilitas
    """
    print(f"🚀 [FUTURES API] get_futures_data called")
    print(f"   Input symbol: {symbol}, Days back: {days_back}, Interval: {interval}")
    print(f"   🔍 [DEBUG] Input validation:")
    print(f"      - symbol type: {type(symbol)}, value: {symbol}")
    print(f"      - days_back type: {type(days_back)}, value: {days_back}")
    print(f"      - interval type: {type(interval)}, value: {interval}")
    
    # Convert symbol format
    if symbol.endswith("-USD"):
        binance_symbol = symbol.replace("-USD", "") + "USDT"
    else:
        binance_symbol = symbol.upper()
    
    print(f"   Converted symbol: {symbol} -> {binance_symbol}")
    print(f"   🔍 [DEBUG] Symbol conversion: {symbol} -> {binance_symbol}")
    
    # Calculate time range
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days_back)
    
    print(f"   Time range: {start_time} to {end_time}")
    print(f"   Testnet: {testnet}")
    
    # Get klines
    df = get_futures_klines(
        symbol=binance_symbol,
        interval=interval,
        start_time=start_time,
        end_time=end_time,
        limit=1500,  # Max limit
        api_key=api_key,
        api_secret=api_secret,
        testnet=testnet
    )
    
    if df is not None and not df.empty:
        print(f"✅ [FUTURES API] get_futures_data completed: {len(df)} records")
        print(f"   🔍 [DEBUG] Final DataFrame validation:")
        print(f"      - Total rows: {len(df)}")
        print(f"      - Required columns present: {all(col in df.columns for col in ['date', 'Open', 'High', 'Low', 'Close', 'Volume'])}")
        print(f"      - Date column type: {df['date'].dtype}")
        print(f"      - Date range: {df['date'].min()} to {df['date'].max()}")
        print(f"      - Close price stats: min={df['Close'].min():.8f}, max={df['Close'].max():.8f}, mean={df['Close'].mean():.8f}")
        print(f"      - Any null values: {df.isnull().any().any()}")
        if df.isnull().any().any():
            print(f"      - Null value details: {df.isnull().sum().to_dict()}")
    else:
        print(f"⚠️  [FUTURES API] get_futures_data returned empty DataFrame")
        print(f"   🔍 [DEBUG] df is None: {df is None}")
        if df is not None:
            print(f"      - df.empty: {df.empty}")
            print(f"      - df.shape: {df.shape}")
            print(f"      - df.columns: {list(df.columns) if hasattr(df, 'columns') else 'N/A'}")
    
    # Normalize DataFrame: pastikan 'date' adalah kolom, bukan index (untuk kompatibilitas)
    if df is not None and not df.empty:
        if 'date' not in df.columns and isinstance(df.index, pd.DatetimeIndex):
            # Jika date adalah index, reset menjadi kolom
            df = df.reset_index()
            # Rename index column ke 'date' jika perlu
            if df.index.name == 'date' or (hasattr(df.index, 'name') and df.index.name is None):
                # Cari kolom datetime pertama dan rename ke 'date'
                for col in df.columns:
                    if pd.api.types.is_datetime64_any_dtype(df[col]):
                        df = df.rename(columns={col: 'date'})
                        break
    
    return df

