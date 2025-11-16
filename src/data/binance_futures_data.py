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
    
    try:
        response = requests.get(url, timeout=30)
        
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
    
    try:
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            klines = response.json()
            
            if not klines:
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
            
            # Set date as index
            df = df.set_index('date')
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
            
            return df
        else:
            print(f"❌ Error getting futures klines: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return None
    except Exception as e:
        print(f"❌ Exception getting futures klines: {e}")
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
    
    try:
        response = requests.get(url, params=params, timeout=30)
        
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
    
    try:
        response = requests.get(url, params=params, timeout=30)
        
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
    
    try:
        response = requests.get(url, params=params, timeout=30)
        
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
    
    # This is a signed endpoint, requires HMAC signature
    # For now, return None and note that this needs proper signature implementation
    print("⚠️  get_futures_position_risk requires signed endpoint (HMAC signature)")
    print("   This function needs proper signature implementation")
    print("   Reference: https://developers.binance.com/docs/derivatives/usds-margined-futures")
    
    # TODO: Implement HMAC signature for signed endpoints
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
    # Convert symbol format
    if symbol.endswith("-USD"):
        binance_symbol = symbol.replace("-USD", "") + "USDT"
    else:
        binance_symbol = symbol.upper()
    
    # Calculate time range
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days_back)
    
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
    
    return df

