#!/usr/bin/env python3
"""
Get Top Coins from Binance
Mengambil top coins dari Binance berdasarkan 24h volume atau market cap
"""

import os
import sys

# Add project root to Python path to enable src imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime
import json

try:
    from binance.client import Client
    from binance.exceptions import BinanceAPIException, BinanceRequestException
except ImportError:
    print("⚠️  Library python-binance tidak ditemukan!")
    print("📦 Install dengan: pip install python-binance")
    Client = None

try:
    from src.utils.config import BINANCE_API_KEY, BINANCE_API_SECRET
except ImportError:
    BINANCE_API_KEY = None
    BINANCE_API_SECRET = None


def get_all_binance_symbols(api_key: Optional[str] = None, 
                           api_secret: Optional[str] = None,
                           quote_asset: str = "USDT") -> List[Dict]:
    """
    Get all trading pairs dari Binance
    
    Args:
        api_key: Binance API key (optional)
        api_secret: Binance API secret (optional)
        quote_asset: Quote asset untuk filter (default: USDT)
    
    Returns:
        List of dictionaries dengan symbol info
    """
    if Client is None:
        print("❌ Library python-binance tidak terinstall")
        return []
    
    try:
        import urllib3
        import os
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        requests_params = {
            'timeout': 30,
            'verify': False
        }
        
        # Support proxy
        proxies = {}
        if os.environ.get('HTTP_PROXY'):
            proxies['http'] = os.environ.get('HTTP_PROXY')
        if os.environ.get('HTTPS_PROXY'):
            proxies['https'] = os.environ.get('HTTPS_PROXY')
        if proxies:
            requests_params['proxies'] = proxies
        
        if api_key and api_secret:
            client = Client(api_key, api_secret, requests_params=requests_params)
        else:
            client = Client(requests_params=requests_params)
        
        print(f"📡 Mengambil semua trading pairs dari Binance...")
        print(f"   Filter: Quote asset = {quote_asset}")
        
        # Get exchange info
        exchange_info = client.get_exchange_info()
        
        # Filter symbols dengan quote asset yang diinginkan
        symbols = []
        for symbol_info in exchange_info['symbols']:
            if symbol_info['status'] == 'TRADING' and symbol_info['quoteAsset'] == quote_asset:
                symbols.append({
                    'symbol': symbol_info['symbol'],
                    'baseAsset': symbol_info['baseAsset'],
                    'quoteAsset': symbol_info['quoteAsset'],
                    'status': symbol_info['status']
                })
        
        print(f"✅ Ditemukan {len(symbols)} trading pairs dengan {quote_asset}")
        return symbols
        
    except BinanceAPIException as e:
        print(f"❌ Binance API Error: {e.status_code} - {e.message}")
        return []
    except Exception as e:
        print(f"❌ Error: {e}")
        return []


def get_24h_ticker_stats(api_key: Optional[str] = None,
                         api_secret: Optional[str] = None) -> pd.DataFrame:
    """
    Get 24h ticker statistics untuk semua trading pairs
    
    Args:
        api_key: Binance API key (optional)
        api_secret: Binance API secret (optional)
    
    Returns:
        DataFrame dengan 24h stats (volume, price change, dll)
    """
    if Client is None:
        print("❌ Library python-binance tidak terinstall")
        return pd.DataFrame()
    
    try:
        import urllib3
        import os
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        requests_params = {
            'timeout': 30,
            'verify': False
        }
        
        # Support proxy
        proxies = {}
        if os.environ.get('HTTP_PROXY'):
            proxies['http'] = os.environ.get('HTTP_PROXY')
        if os.environ.get('HTTPS_PROXY'):
            proxies['https'] = os.environ.get('HTTPS_PROXY')
        if proxies:
            requests_params['proxies'] = proxies
        
        if api_key and api_secret:
            client = Client(api_key, api_secret, requests_params=requests_params)
        else:
            client = Client(requests_params=requests_params)
        
        print(f"📊 Mengambil 24h ticker statistics...")
        
        # Get 24h ticker untuk semua symbols
        tickers = client.get_ticker()
        
        # Convert ke DataFrame
        df = pd.DataFrame(tickers)
        
        # Convert numeric columns
        numeric_cols = ['priceChange', 'priceChangePercent', 'weightedAvgPrice', 
                       'prevClosePrice', 'lastPrice', 'bidPrice', 'askPrice',
                       'openPrice', 'highPrice', 'lowPrice', 'volume', 'quoteVolume', 'count']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        print(f"✅ Mendapatkan stats untuk {len(df)} trading pairs")
        return df
        
    except BinanceAPIException as e:
        print(f"❌ Binance API Error: {e.status_code} - {e.message}")
        return pd.DataFrame()
    except Exception as e:
        print(f"❌ Error: {e}")
        return pd.DataFrame()


def get_top_coins_from_binance(top_n: int = 200,
                               sort_by: str = "volume",
                               quote_asset: str = "USDT",
                               api_key: Optional[str] = None,
                               api_secret: Optional[str] = None) -> List[str]:
    """
    Get top N coins dari Binance berdasarkan volume atau market cap
    
    Args:
        top_n: Jumlah top coins (default: 200)
        sort_by: "volume" atau "quoteVolume" (default: "volume")
        quote_asset: Quote asset untuk filter (default: USDT)
        api_key: Binance API key (optional)
        api_secret: Binance API secret (optional)
    
    Returns:
        List of symbols dalam format yfinance (e.g., ["BTC-USD", "ETH-USD"])
    """
    print(f"\n🔍 Mengambil Top {top_n} Coins dari Binance...")
    print(f"   Sort by: {sort_by}")
    print(f"   Quote asset: {quote_asset}")
    print("=" * 60)
    
    # Get all symbols
    symbols = get_all_binance_symbols(api_key, api_secret, quote_asset)
    
    if not symbols:
        print("❌ Tidak ada symbols ditemukan")
        return []
    
    # Get 24h ticker stats
    ticker_df = get_24h_ticker_stats(api_key, api_secret)
    
    if ticker_df.empty:
        print("❌ Tidak ada ticker stats")
        return []
    
    # Filter untuk USDT pairs dan merge dengan symbol info
    ticker_df = ticker_df[ticker_df['symbol'].str.endswith(quote_asset)]
    
    # Sort berdasarkan volume atau quoteVolume
    if sort_by == "volume":
        sort_col = 'volume'
    elif sort_by == "quoteVolume":
        sort_col = 'quoteVolume'
    else:
        sort_col = 'volume'
    
    # Sort descending
    ticker_df = ticker_df.sort_values(sort_col, ascending=False)
    
    # Get top N
    top_df = ticker_df.head(top_n)
    
    print(f"\n✅ Top {len(top_df)} coins berdasarkan {sort_by}:")
    print(f"   Total volume: {top_df[sort_col].sum():,.0f} {quote_asset}")
    print()
    
    # Convert ke format yfinance (BASE-USD)
    result_symbols = []
    for symbol in top_df['symbol']:
        # Remove quote asset (e.g., BTCUSDT -> BTC)
        base_asset = symbol.replace(quote_asset, "")
        # Convert ke format yfinance (BTC -> BTC-USD)
        yfinance_symbol = f"{base_asset}-USD"
        result_symbols.append(yfinance_symbol)
    
    return result_symbols


def save_coins_to_file(symbols: List[str], filename: str = "data/binance_top_coins.json"):
    """
    Simpan list symbols ke file JSON
    
    Args:
        symbols: List of symbols
        filename: Nama file untuk disimpan
    """
    data = {
        'last_updated': datetime.now().isoformat(),
        'count': len(symbols),
        'symbols': symbols
    }
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✅ Symbols disimpan ke {filename}")
    print(f"   Total: {len(symbols)} symbols")
    print(f"   Last updated: {data['last_updated']}")


def load_coins_from_file(filename: str = "data/binance_top_coins.json") -> List[str]:
    """
    Load list symbols dari file JSON
    
    Args:
        filename: Nama file untuk dibaca
    
    Returns:
        List of symbols
    """
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
        
        print(f"✅ Symbols dimuat dari {filename}")
        print(f"   Total: {len(data['symbols'])} symbols")
        print(f"   Last updated: {data.get('last_updated', 'Unknown')}")
        
        return data['symbols']
    except FileNotFoundError:
        print(f"⚠️  File {filename} tidak ditemukan")
        return []
    except Exception as e:
        print(f"❌ Error membaca file: {e}")
        return []


if __name__ == "__main__":
    # Get top 200 coins dari Binance
    top_coins = get_top_coins_from_binance(
        top_n=200,
        sort_by="quoteVolume",  # Sort by USDT volume
        quote_asset="USDT",
        api_key=BINANCE_API_KEY,
        api_secret=BINANCE_API_SECRET
    )
    
    if top_coins:
        # Save ke file
        save_coins_to_file(top_coins, "data/binance_top_coins.json")
        
        # Print sample
        print(f"\n📋 Sample top 20 coins:")
        for i, symbol in enumerate(top_coins[:20], 1):
            print(f"   {i}. {symbol}")
        
        print(f"\n✅ Total: {len(top_coins)} coins")
    else:
        print("❌ Gagal mengambil coins dari Binance")

