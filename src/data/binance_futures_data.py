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
from datetime import datetime, timedelta, timezone
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

# Column name constants for klines DataFrame
COL_OPEN_TIME = 'Open time'
COL_CLOSE_TIME = 'Close time'


def _rate_limit_delay():
    """Delay untuk rate limiting"""
    global _last_request_time
    current_time = time.time()
    time_since_last = current_time - _last_request_time
    if time_since_last < MIN_REQUEST_DELAY:
        sleep_time = MIN_REQUEST_DELAY - time_since_last
        time.sleep(sleep_time)
    _last_request_time = time.time()


def _parse_error_response(response) -> Tuple[Optional[dict], str, int]:
    """
    Parse error response dari Binance API
    
    Returns:
        Tuple (error_data: dict or None, error_msg: str, error_code: int)
    """
    try:
        error_data = response.json()
        error_msg = error_data.get('msg', response.text[:200]) if isinstance(error_data, dict) else response.text[:200]
        error_code = error_data.get('code', response.status_code) if isinstance(error_data, dict) else response.status_code
        return error_data, error_msg, error_code
    except Exception:
        return None, response.text[:200], response.status_code


def _parse_ban_time(error_msg: str) -> Optional[float]:
    """
    Parse ban time dari error message
    
    Returns:
        Ban timestamp in seconds atau None jika tidak ditemukan
    """
    if 'banned until' not in error_msg.lower():
        return None
    
    import re
    match = re.search(r'until (\d+)', error_msg)
    if not match:
        return None
    
    ban_until = int(match.group(1)) / 1000  # Convert dari ms ke seconds
    return ban_until


def _handle_ip_ban(error_msg: str, endpoint_name: str) -> Tuple[bool, str]:
    """
    Handle IP ban error (418)
    
    Returns:
        Tuple (should_retry: bool, error_message: str)
    """
    ban_until = _parse_ban_time(error_msg)
    
    if ban_until:
        ban_until_dt = datetime.fromtimestamp(ban_until)
        print(f"🚫 [RATE LIMIT] IP banned until: {ban_until_dt}")
        print(f"   Current time: {datetime.now()}")
        wait_time = ban_until - time.time()
        if wait_time > 0:
            print(f"   ⏳ Please wait {int(wait_time / 60)} minutes before retrying")
        else:
            print("   ✅ Ban period should be over, but API still returns 418")
    
    print(f"❌ [RATE LIMIT] IP banned (418) for endpoint: {endpoint_name}")
    print(f"   Error: {error_msg}")
    print("   💡 Solutions:")
    print("      1. Wait for the ban to expire (check ban_until time above)")
    print("      2. Use Binance API key for higher rate limits")
    print("      3. Reduce request frequency (add delays between requests)")
    print("      4. Use WebSocket for live updates instead of REST API")
    return False, f"IP banned: {error_msg}"


def _handle_rate_limit(error_msg: str, endpoint_name: str) -> Tuple[bool, str]:
    """Handle rate limit error (429)"""
    print(f"⚠️  [RATE LIMIT] Rate limit exceeded (429) for endpoint: {endpoint_name}")
    print(f"   Error: {error_msg}")
    print("   💡 Wait a few seconds before retrying")
    return True, f"Rate limit exceeded: {error_msg}"


def _handle_bad_request(error_msg: str, endpoint_name: str) -> Tuple[bool, str]:
    """Handle bad request error (400)"""
    print(f"❌ [ERROR] Bad request (400) for endpoint: {endpoint_name}")
    print(f"   Error: {error_msg}")
    return False, f"Bad request: {error_msg}"


def _handle_unauthorized(error_msg: str, endpoint_name: str) -> Tuple[bool, str]:
    """Handle unauthorized error (401)"""
    print(f"❌ [ERROR] Unauthorized (401) for endpoint: {endpoint_name}")
    print(f"   Error: {error_msg}")
    return False, f"Unauthorized: {error_msg}"


def _handle_other_error(status_code: int, error_msg: str, endpoint_name: str) -> Tuple[bool, str]:
    """Handle other HTTP errors"""
    print(f"❌ [ERROR] HTTP {status_code} for endpoint: {endpoint_name}")
    print(f"   Error: {error_msg}")
    return False, f"HTTP {status_code}: {error_msg}"


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
    
    _, error_msg, _ = _parse_error_response(response)
    
    # Status code handlers
    handlers = {
        418: lambda: _handle_ip_ban(error_msg, endpoint_name),
        429: lambda: _handle_rate_limit(error_msg, endpoint_name),
        400: lambda: _handle_bad_request(error_msg, endpoint_name),
        401: lambda: _handle_unauthorized(error_msg, endpoint_name),
    }
    
    if status_code in handlers:
        return handlers[status_code]()
    
    return _handle_other_error(status_code, error_msg, endpoint_name)


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


def get_futures_exchange_info(testnet: bool = False) -> Optional[Dict]:
    """
    Get exchange information for USDⓈ-M Futures
    
    Endpoint: GET /fapi/v1/exchangeInfo
    
    Args:
        testnet: Use testnet (default: False)
    
    Returns:
        Dictionary dengan exchange info atau None jika error
    """
    base_url = FUTURES_TESTNET_URL if testnet else FUTURES_BASE_URL
    url = f"{base_url}/fapi/v1/exchangeInfo"
    
    print("🔵 [FUTURES API] Hitting endpoint: GET /fapi/v1/exchangeInfo")
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
                       testnet: bool = False) -> List[str]:
    """
    Get list of symbols available in USDⓈ-M Futures
    
    Args:
        quote_asset: Quote asset filter (default: "USDT")
        testnet: Use testnet (default: False)
    
    Returns:
        List of symbols (e.g., ["BTCUSDT", "ETHUSDT", ...])
    """
    exchange_info = get_futures_exchange_info(testnet)
    
    if not exchange_info:
        return []
    
    symbols = []
    for symbol_info in exchange_info.get('symbols', []):
        if symbol_info.get('status') == 'TRADING' and symbol_info.get('quoteAsset') == quote_asset:
            symbols.append(symbol_info.get('symbol'))
    
    return sorted(symbols)


def _make_klines_request(url: str, params: dict, max_retries: int = 1) -> Optional[requests.Response]:
    """
    Make klines API request with retry logic for rate limits
    
    Returns:
        Response object or None if failed
    """
    _rate_limit_delay()
    
    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"   ✅ Response status: {response.status_code}")
        
        if response.status_code != 200:
            should_retry, _ = _handle_binance_error(response, "GET /fapi/v1/klines")
            if response.status_code == 418:
                return None
            elif should_retry and response.status_code == 429 and max_retries > 0:
                print("   ⏳ Waiting 5 seconds before retry...")
                time.sleep(5)
                return _make_klines_request(url, params, max_retries - 1)
            return None
        
        return response
    except requests.exceptions.RequestException as e:
        print(f"❌ Request Error: {e}")
        return None


def _convert_klines_to_dataframe(klines: List) -> pd.DataFrame:
    """
    Convert klines JSON data to pandas DataFrame
    
    Returns:
        DataFrame with columns: date, Open, High, Low, Close, Volume
    """
    if not klines:
        print("   ⚠️  No klines data returned")
        return pd.DataFrame()
    
    df = pd.DataFrame(klines, columns=[
        COL_OPEN_TIME, 'Open', 'High', 'Low', 'Close', 'Volume',
        COL_CLOSE_TIME, 'Quote volume', 'Trades',
        'Taker buy base', 'Taker buy quote', 'Ignore'
    ])
    
    df[COL_OPEN_TIME] = pd.to_datetime(df[COL_OPEN_TIME], unit='ms')
    df[COL_CLOSE_TIME] = pd.to_datetime(df[COL_CLOSE_TIME], unit='ms')
    
    price_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
    for col in price_columns:
        df[col] = df[col].astype(float)
    
    df = df.rename(columns={COL_OPEN_TIME: 'date'})
    df = df[['date', 'Open', 'High', 'Low', 'Close', 'Volume']]
    df = df.sort_values('date')
    df.reset_index(drop=True, inplace=True)
    
    return df


def _validate_klines_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validate and clean klines DataFrame
    
    Returns:
        Validated DataFrame
    """
    print("   🔍 [DEBUG] Validating DataFrame:")
    print(f"      - Shape: {df.shape}")
    print(f"      - Columns: {list(df.columns)}")
    print(f"      - Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"      - Price range: Close min={df['Close'].min():.8f}, max={df['Close'].max():.8f}")
    print(f"      - Volume range: min={df['Volume'].min():.2f}, max={df['Volume'].max():.2f}")
    print(f"      - Null values: {df.isnull().sum().to_dict()}")
    print("      - Sample data (first 3 rows):")
    for idx, row in df.head(3).iterrows():
        print(f"         Row {idx}: date={row['date']}, Close={row['Close']:.8f}, Volume={row['Volume']:.2f}")
    
    if df['Close'].isnull().any():
        print(f"   ⚠️  WARNING: Found null values in Close column!")
        df = df.dropna(subset=['Close'])
        print(f"      After dropna: {len(df)} rows")
    
    if len(df) == 0:
        print(f"   ❌ ERROR: DataFrame is empty after processing!")
        return pd.DataFrame()
    
    print(f"   ✅ DataFrame validation passed: {len(df)} valid rows")
    return df


def _print_klines_request_info(url: str, symbol: str, interval: str, limit: int,
                               start_time: Optional[datetime], end_time: Optional[datetime],
                               testnet: bool):
    """Print request information for klines API call"""
    print(f"🔵 [FUTURES API] Hitting endpoint: GET /fapi/v1/klines")
    print(f"   URL: {url}")
    print(f"   Symbol: {symbol.upper()}, Interval: {interval}, Limit: {limit}")
    if start_time:
        print(f"   Start time: {start_time}")
    if end_time:
        current_time = datetime.now(timezone.utc)
        if end_time > current_time:
            print(f"   ⚠️  WARNING: End time ({end_time}) di masa depan! Current time: {current_time}")
            print(f"   End time: {end_time} (INVALID - di masa depan)")
        else:
            print(f"   End time: {end_time} (current_time: {current_time})")
    print(f"   Testnet: {testnet}")


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
        'limit': min(limit, 1500)
    }
    
    if start_time:
        params['startTime'] = int(start_time.timestamp() * 1000)
    if end_time:
        params['endTime'] = int(end_time.timestamp() * 1000)
    
    _print_klines_request_info(url, symbol, interval, params['limit'], start_time, end_time, testnet)
    
    try:
        response = _make_klines_request(url, params)
        if not response:
            return None
        
        klines = response.json()
        print(f"   📊 Received {len(klines)} klines")
        
        df = _convert_klines_to_dataframe(klines)
        if df.empty:
            return df
        
        print(f"   ✅ Successfully converted to DataFrame: {len(df)} rows")
        df = _validate_klines_dataframe(df)
        return df
        
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection Error: Cannot connect to Binance Futures API")
        print(f"   Error: {e}")
        print(f"   💡 Possible causes:")
        print(f"      - No internet connection")
        print(f"      - DNS resolution failed (cannot resolve fapi.binance.com)")
        print(f"      - Firewall blocking connection")
        print(f"      - Binance API is down")
        return None
    except requests.exceptions.Timeout as e:
        print(f"❌ Timeout Error: Request to Binance Futures API timed out")
        print(f"   Error: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Request Error: Failed to get data from Binance Futures API")
        print(f"   Error: {e}")
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
    
    # Validate limit
    valid_limits = [5, 10, 20, 50, 100, 500, 1000]
    if limit not in valid_limits:
        limit = 100  # Default to 100
    
    params = {
        'symbol': symbol.upper(),
        'limit': limit
    }
    
    print(f"🔵 [FUTURES API] Hitting endpoint: GET /fapi/v1/depth")
    print(f"   URL: {url}")
    print(f"   Symbol: {symbol.upper()}, Limit: {limit}")
    print(f"   Testnet: {testnet}")
    
    # Rate limiting: delay sebelum request
    _rate_limit_delay()
    
    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"   ✅ Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            should_retry, error_msg = _handle_binance_error(response, "get_futures_orderbook")
            if should_retry:
                print(f"   ⏳ Retrying after delay...")
                time.sleep(2)
                _rate_limit_delay()
                response = requests.get(url, params=params, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    return data
            
            print(f"❌ Error getting futures orderbook: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return None
    except Exception as e:
        print(f"❌ Exception getting futures orderbook: {e}")
        import traceback
        traceback.print_exc()
        return None


def analyze_orderbook_depth(orderbook_data: Dict, current_price: Optional[float] = None) -> Dict:
    """
    Analisis orderbook depth untuk mendapatkan market insights
    
    Args:
        orderbook_data: Dictionary dari get_futures_orderbook dengan bids dan asks
        current_price: Current price (optional, untuk analisis relatif terhadap price)
    
    Returns:
        Dictionary dengan:
        - total_bid_volume: Total volume dari bids (buy orders)
        - total_ask_volume: Total volume dari asks (sell orders)
        - bid_ask_ratio: Ratio bid/ask volume (1.0 = balanced, >1.0 = more bids, <1.0 = more asks)
        - orderbook_imbalance: Imbalance score (-1 to 1, positive = more bids, negative = more asks)
        - buy_wall_size: Size of largest buy wall (biggest bid cluster)
        - sell_wall_size: Size of largest sell wall (biggest ask cluster)
        - buy_wall_price: Price level of largest buy wall
        - sell_wall_price: Price level of largest sell wall
        - liquidity_clusters: List of liquidity clusters (big orders/whales)
        - big_orders_count: Count of big orders (whales)
        - signal: Trading signal berdasarkan orderbook analysis
        - interpretation: Interpretasi dari orderbook analysis
    """
    if not orderbook_data:
        return {
            'total_bid_volume': 0,
            'total_ask_volume': 0,
            'bid_ask_ratio': 1.0,
            'orderbook_imbalance': 0,
            'buy_wall_size': 0,
            'sell_wall_size': 0,
            'buy_wall_price': 0,
            'sell_wall_price': 0,
            'liquidity_clusters': [],
            'big_orders_count': 0,
            'signal': 'NEUTRAL',
            'interpretation': 'No orderbook data available'
        }
    
    bids = orderbook_data.get('bids', [])
    asks = orderbook_data.get('asks', [])
    
    if not bids or not asks:
        return {
            'total_bid_volume': 0,
            'total_ask_volume': 0,
            'bid_ask_ratio': 1.0,
            'orderbook_imbalance': 0,
            'buy_wall_size': 0,
            'sell_wall_size': 0,
            'buy_wall_price': 0,
            'sell_wall_price': 0,
            'liquidity_clusters': [],
            'big_orders_count': 0,
            'signal': 'NEUTRAL',
            'interpretation': 'Insufficient orderbook data'
        }
    
    # Calculate total volumes
    total_bid_volume = sum(float(bid[1]) for bid in bids)  # bid[1] = quantity
    total_ask_volume = sum(float(ask[1]) for ask in asks)  # ask[1] = quantity
    
    # Calculate bid/ask ratio
    total_volume = total_bid_volume + total_ask_volume
    bid_ask_ratio = total_bid_volume / total_ask_volume if total_ask_volume > 0 else 1.0
    
    # Calculate orderbook imbalance (-1 to 1)
    # Positive = more bids (buy pressure), Negative = more asks (sell pressure)
    orderbook_imbalance = (total_bid_volume - total_ask_volume) / total_volume if total_volume > 0 else 0
    
    # Find buy walls and sell walls (large orders at specific price levels)
    # Buy wall = large bid order
    # Sell wall = large ask order
    buy_wall_size = 0
    buy_wall_price = 0
    sell_wall_size = 0
    sell_wall_price = 0
    
    # Threshold untuk "big order" (whale): 1% dari total volume atau minimum threshold
    big_order_threshold = max(total_volume * 0.01, 1000)  # At least 1% or 1000 units
    
    liquidity_clusters = []
    big_orders_count = 0
    
    # Analyze bids (buy orders)
    for bid in bids:
        price = float(bid[0])
        qty = float(bid[1])
        volume = price * qty
        
        if qty > buy_wall_size:
            buy_wall_size = qty
            buy_wall_price = price
        
        if volume >= big_order_threshold:
            big_orders_count += 1
            liquidity_clusters.append({
                'type': 'BUY',
                'price': price,
                'quantity': qty,
                'volume': volume,
                'size_category': 'WHALE' if volume >= big_order_threshold * 5 else 'BIG'
            })
    
    # Analyze asks (sell orders)
    for ask in asks:
        price = float(ask[0])
        qty = float(ask[1])
        volume = price * qty
        
        if qty > sell_wall_size:
            sell_wall_size = qty
            sell_wall_price = price
        
        if volume >= big_order_threshold:
            big_orders_count += 1
            liquidity_clusters.append({
                'type': 'SELL',
                'price': price,
                'quantity': qty,
                'volume': volume,
                'size_category': 'WHALE' if volume >= big_order_threshold * 5 else 'BIG'
            })
    
    # Determine signal based on orderbook analysis
    signal = 'NEUTRAL'
    interpretation = ''
    
    # Jika buy wall besar → potensi Long
    if buy_wall_size > sell_wall_size * 1.5 and orderbook_imbalance > 0.1:
        signal = 'LONG'
        interpretation = f'Buy wall besar ({buy_wall_size:.2f} vs sell wall {sell_wall_size:.2f}) + orderbook imbalance positif → potensi Long'
    # Jika sell wall besar → potensi Short
    elif sell_wall_size > buy_wall_size * 1.5 and orderbook_imbalance < -0.1:
        signal = 'SHORT'
        interpretation = f'Sell wall besar ({sell_wall_size:.2f} vs buy wall {buy_wall_size:.2f}) + orderbook imbalance negatif → potensi Short'
    # Jika balanced
    elif abs(orderbook_imbalance) < 0.05:
        signal = 'NEUTRAL'
        interpretation = 'Orderbook balanced, tidak ada tekanan signifikan'
    # Jika slight imbalance
    elif orderbook_imbalance > 0.05:
        signal = 'WEAK_LONG'
        interpretation = f'Slight buy pressure (imbalance: {orderbook_imbalance:.2%}), buy wall: {buy_wall_size:.2f}'
    else:
        signal = 'WEAK_SHORT'
        interpretation = f'Slight sell pressure (imbalance: {orderbook_imbalance:.2%}), sell wall: {sell_wall_size:.2f}'
    
    return {
        'total_bid_volume': total_bid_volume,
        'total_ask_volume': total_ask_volume,
        'bid_ask_ratio': bid_ask_ratio,
        'orderbook_imbalance': orderbook_imbalance,
        'buy_wall_size': buy_wall_size,
        'sell_wall_size': sell_wall_size,
        'buy_wall_price': buy_wall_price,
        'sell_wall_price': sell_wall_price,
        'liquidity_clusters': liquidity_clusters[:10],  # Limit to top 10
        'big_orders_count': big_orders_count,
        'signal': signal,
        'interpretation': interpretation
    }


def get_futures_recent_trades(symbol: str,
                              limit: int = 100,
                              api_key: Optional[str] = None,
                              api_secret: Optional[str] = None,
                              testnet: bool = False) -> Optional[List[Dict]]:
    """
    Get recent trades from USDⓈ-M Futures
    
    Endpoint: GET /fapi/v1/trades
    
    Args:
        symbol: Trading symbol (e.g., "BTCUSDT")
        limit: Number of trades to return (default: 100, max: 1000)
        api_key: Binance API Key (optional, not needed for public endpoint)
        api_secret: Binance API Secret (optional, not needed for public endpoint)
        testnet: Use testnet (default: False)
    
    Returns:
        List of trade dictionaries dengan fields:
        - id: Trade ID
        - price: Price
        - qty: Quantity
        - quoteQty: Quote quantity (price * qty)
        - time: Trade time (timestamp in ms)
        - isBuyerMaker: True if buyer is maker, False if buyer is taker
    """
    base_url = FUTURES_TESTNET_URL if testnet else FUTURES_BASE_URL
    url = f"{base_url}/fapi/v1/trades"
    
    params = {
        'symbol': symbol.upper(),
        'limit': min(limit, 1000)  # Max 1000
    }
    
    print(f"🔵 [FUTURES API] Hitting endpoint: GET /fapi/v1/trades")
    print(f"   URL: {url}")
    print(f"   Symbol: {symbol.upper()}, Limit: {params['limit']}")
    print(f"   Testnet: {testnet}")
    
    # Rate limiting: delay sebelum request
    _rate_limit_delay()
    
    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"   ✅ Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            should_retry, error_msg = _handle_binance_error(response, "get_futures_recent_trades")
            if should_retry:
                print(f"   ⏳ Retrying after delay...")
                time.sleep(2)
                _rate_limit_delay()
                response = requests.get(url, params=params, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    return data
            
            print(f"❌ Error getting futures recent trades: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return None
    except Exception as e:
        print(f"❌ Exception getting futures recent trades: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_futures_open_interest(symbol: str,
                               api_key: Optional[str] = None,
                               api_secret: Optional[str] = None,
                               testnet: bool = False) -> Optional[Dict]:
    """
    Get open interest for symbol in USDⓈ-M Futures
    
    Endpoint: GET /fapi/v1/openInterest
    
    Args:
        symbol: Trading symbol (e.g., "BTCUSDT")
        api_key: Binance API Key (optional, not needed for public endpoint)
        api_secret: Binance API Secret (optional, not needed for public endpoint)
        testnet: Use testnet (default: False)
    
    Returns:
        Dictionary dengan:
        - openInterest: Open interest value
        - symbol: Trading symbol
    """
    base_url = FUTURES_TESTNET_URL if testnet else FUTURES_BASE_URL
    url = f"{base_url}/fapi/v1/openInterest"
    
    params = {
        'symbol': symbol.upper()
    }
    
    print(f"🔵 [FUTURES API] Hitting endpoint: GET /fapi/v1/openInterest")
    print(f"   URL: {url}")
    print(f"   Symbol: {symbol.upper()}")
    print(f"   Testnet: {testnet}")
    
    # Rate limiting: delay sebelum request
    _rate_limit_delay()
    
    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"   ✅ Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            should_retry, error_msg = _handle_binance_error(response, "get_futures_open_interest")
            if should_retry:
                print(f"   ⏳ Retrying after delay...")
                time.sleep(2)
                _rate_limit_delay()
                response = requests.get(url, params=params, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    return data
            
            print(f"❌ Error getting futures open interest: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return None
    except Exception as e:
        print(f"❌ Exception getting futures open interest: {e}")
        import traceback
        traceback.print_exc()
        return None


def analyze_open_interest(oi_data: Dict, current_price: Optional[float] = None, 
                          previous_oi: Optional[float] = None,
                          previous_price: Optional[float] = None) -> Dict:
    """
    Analisis Open Interest untuk mendapatkan trend strength
    
    Args:
        oi_data: Dictionary dari get_futures_open_interest
        current_price: Current price (optional, untuk analisis OI vs Price)
        previous_oi: Previous OI value (optional, untuk menghitung perubahan)
        previous_price: Previous price (optional, untuk menghitung perubahan)
    
    Returns:
        Dictionary dengan:
        - open_interest: Current open interest value
        - oi_change: Perubahan OI (jika previous_oi tersedia)
        - oi_change_pct: Persentase perubahan OI
        - trend_strength: Trend strength analysis
        - trend_direction: "BULLISH", "BEARISH", atau "NEUTRAL"
        - signal: Trading signal berdasarkan OI analysis
        - interpretation: Interpretasi dari OI analysis
    """
    if not oi_data:
        return {
            'open_interest': 0,
            'oi_change': 0,
            'oi_change_pct': 0,
            'trend_strength': 'UNKNOWN',
            'trend_direction': 'NEUTRAL',
            'signal': 'NEUTRAL',
            'interpretation': 'No OI data available'
        }
    
    current_oi = float(oi_data.get('openInterest', 0))
    
    # Calculate OI change jika previous_oi tersedia
    oi_change = 0
    oi_change_pct = 0
    if previous_oi is not None and previous_oi > 0:
        oi_change = current_oi - previous_oi
        oi_change_pct = (oi_change / previous_oi) * 100
    
    # Analyze trend strength berdasarkan OI dan price movement
    trend_strength = 'UNKNOWN'
    trend_direction = 'NEUTRAL'
    signal = 'NEUTRAL'
    interpretation = 'Insufficient data for OI analysis'
    
    # Jika ada previous_oi dan previous_price, lakukan analisis lengkap
    if previous_oi is not None and previous_oi > 0 and current_price and previous_price:
        price_change = ((current_price - previous_price) / previous_price) * 100
        
        # OI naik + harga naik → trend bullish kuat (Long)
        if oi_change > 0 and price_change > 0:
            trend_direction = 'BULLISH'
            if oi_change_pct > 5 and price_change > 1:
                trend_strength = 'VERY_STRONG'
                signal = 'STRONG_LONG'
                interpretation = 'OI naik + harga naik → trend bullish sangat kuat (posisi long bertambah banyak)'
            elif oi_change_pct > 2 and price_change > 0.5:
                trend_strength = 'STRONG'
                signal = 'LONG'
                interpretation = 'OI naik + harga naik → trend bullish kuat (posisi long bertambah)'
            else:
                trend_strength = 'MODERATE'
                signal = 'WEAK_LONG'
                interpretation = 'OI naik + harga naik → trend bullish sedang (posisi long bertambah sedikit)'
        
        # OI naik + harga turun → trend bearish kuat (Short)
        elif oi_change > 0 and price_change < 0:
            trend_direction = 'BEARISH'
            if oi_change_pct > 5 and price_change < -1:
                trend_strength = 'VERY_STRONG'
                signal = 'STRONG_SHORT'
                interpretation = 'OI naik + harga turun → trend bearish sangat kuat (posisi short bertambah banyak)'
            elif oi_change_pct > 2 and price_change < -0.5:
                trend_strength = 'STRONG'
                signal = 'SHORT'
                interpretation = 'OI naik + harga turun → trend bearish kuat (posisi short bertambah)'
            else:
                trend_strength = 'MODERATE'
                signal = 'WEAK_SHORT'
                interpretation = 'OI naik + harga turun → trend bearish sedang (posisi short bertambah sedikit)'
        
        # OI turun + harga naik → long liquidation atau profit taking
        elif oi_change < 0 and price_change > 0:
            trend_direction = 'BULLISH'
            trend_strength = 'WEAK'
            signal = 'CAUTION_LONG'
            interpretation = 'OI turun + harga naik → profit taking atau short covering (trend melemah, caution)'
        
        # OI turun + harga turun → short liquidation atau profit taking
        elif oi_change < 0 and price_change < 0:
            trend_direction = 'BEARISH'
            trend_strength = 'WEAK'
            signal = 'CAUTION_SHORT'
            interpretation = 'OI turun + harga turun → profit taking atau long liquidation (trend melemah, caution)'
        
        # OI stabil
        else:
            trend_direction = 'NEUTRAL'
            trend_strength = 'NEUTRAL'
            signal = 'NEUTRAL'
            interpretation = 'OI stabil, tidak ada perubahan signifikan'
    
    # Jika hanya ada current OI tanpa previous data, hanya return current OI
    elif current_oi > 0:
        interpretation = f'Current OI: {current_oi:.2f} (tidak ada data perubahan untuk analisis trend)'
    
    return {
        'open_interest': current_oi,
        'oi_change': oi_change,
        'oi_change_pct': oi_change_pct,
        'trend_strength': trend_strength,
        'trend_direction': trend_direction,
        'signal': signal,
        'interpretation': interpretation
    }


def analyze_recent_trades(trades: List[Dict]) -> Dict:
    """
    Analisis recent trades untuk mendapatkan market insights
    
    Args:
        trades: List of trade dictionaries dari get_futures_recent_trades
    
    Returns:
        Dictionary dengan:
        - total_volume: Total volume dalam quote currency
        - buy_volume: Volume dari buyer (taker buys)
        - sell_volume: Volume dari seller (taker sells)
        - buy_ratio: Ratio buyer volume (0-1)
        - sell_ratio: Ratio seller volume (0-1)
        - trade_count: Jumlah trades
        - avg_trade_size: Average trade size
        - market_aggression: Market aggression score (0-100)
        - buyer_dominance: Buyer dominance score (0-100, >50 = buyer dominant)
        - momentum: Short-term momentum (positive = bullish, negative = bearish)
        - price_trend: Price trend dari trades pertama ke terakhir
    """
    if not trades or len(trades) == 0:
        return {
            'total_volume': 0,
            'buy_volume': 0,
            'sell_volume': 0,
            'buy_ratio': 0.5,
            'sell_ratio': 0.5,
            'trade_count': 0,
            'avg_trade_size': 0,
            'market_aggression': 0,
            'buyer_dominance': 50,
            'momentum': 0,
            'price_trend': 0
        }
    
    total_volume = 0
    buy_volume = 0
    sell_volume = 0
    trade_count = len(trades)
    prices = []
    
    for trade in trades:
        price = float(trade.get('price', 0))
        qty = float(trade.get('qty', 0))
        quote_qty = float(trade.get('quoteQty', price * qty))
        is_buyer_maker = trade.get('isBuyerMaker', False)
        
        total_volume += quote_qty
        prices.append(price)
        
        # isBuyerMaker = True berarti buyer adalah maker (sell order)
        # isBuyerMaker = False berarti buyer adalah taker (buy order)
        if is_buyer_maker:
            # Buyer adalah maker = seller adalah taker = sell order
            sell_volume += quote_qty
        else:
            # Buyer adalah taker = buy order
            buy_volume += quote_qty
    
    # Calculate ratios
    buy_ratio = buy_volume / total_volume if total_volume > 0 else 0.5
    sell_ratio = sell_volume / total_volume if total_volume > 0 else 0.5
    
    # Average trade size
    avg_trade_size = total_volume / trade_count if trade_count > 0 else 0
    
    # Market aggression: berdasarkan volume dan frequency
    # Semakin tinggi volume dan frequency, semakin tinggi aggression
    volume_score = min(total_volume / 1000000, 1.0) * 50  # Normalize to 0-50
    frequency_score = min(trade_count / 100, 1.0) * 50  # Normalize to 0-50
    market_aggression = volume_score + frequency_score
    
    # Buyer dominance: 0-100, >50 = buyer dominant, <50 = seller dominant
    buyer_dominance = buy_ratio * 100
    
    # Short-term momentum: berdasarkan price trend
    if len(prices) >= 2:
        first_price = prices[0]
        last_price = prices[-1]
        price_change = ((last_price - first_price) / first_price) * 100
        momentum = price_change
    else:
        momentum = 0
    
    # Price trend: positive = uptrend, negative = downtrend
    price_trend = momentum
    
    return {
        'total_volume': total_volume,
        'buy_volume': buy_volume,
        'sell_volume': sell_volume,
        'buy_ratio': buy_ratio,
        'sell_ratio': sell_ratio,
        'trade_count': trade_count,
        'avg_trade_size': avg_trade_size,
        'market_aggression': market_aggression,
        'buyer_dominance': buyer_dominance,
        'momentum': momentum,
        'price_trend': price_trend
    }


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
    
    print(f"   🧪 Testnet: {testnet}")
    print(f"   📊 Mengambil 1500 klines terbaru (tanpa time range)")
    
    # Sederhana: hanya ambil 1500 klines terbaru tanpa startTime/endTime
    # Ini akan mengambil 1500 klines terbaru dari Binance API
    df = get_futures_klines(
        symbol=binance_symbol,
        interval=interval,
        start_time=None,  # Tidak gunakan startTime
        end_time=None,    # Tidak gunakan endTime
        limit=1500,        # Max limit: 1500 klines terbaru
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

