#!/usr/bin/env python3
"""
Get Top Coins from Binance USDⓈ-M Futures
Mengambil top coins dari Binance Futures berdasarkan 24h volume atau market cap
Menggunakan endpoint: GET /fapi/v1/exchangeInfo
"""

import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime
import json
import os
import sys

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from src.data.binance_futures_data import (
        get_futures_exchange_info,
        get_futures_symbols,
        get_futures_ticker_price,
        get_futures_24h_ticker,
        convert_futures_symbol_to_yfinance
    )
    from src.utils.config import BINANCE_API_KEY, BINANCE_API_SECRET
except ImportError as e:
    print(f"⚠️  Error importing modules: {e}")
    sys.exit(1)


def get_futures_top_coins_by_volume(limit: int = 200,
                                    api_key: Optional[str] = None,
                                    api_secret: Optional[str] = None,
                                    testnet: bool = False) -> List[str]:
    """
    Get top coins dari Binance Futures berdasarkan 24h volume
    
    Args:
        limit: Jumlah coins yang diambil (default: 200)
        api_key: Binance API key (optional)
        api_secret: Binance API secret (optional)
        testnet: Use testnet (default: False)
    
    Returns:
        List of symbols dalam format yfinance (e.g., ["BTC-USD", "ETH-USD"])
    """
    api_key = api_key or BINANCE_API_KEY
    api_secret = api_secret or BINANCE_API_SECRET
    
    print(f"📊 Mengambil top {limit} coins dari Binance Futures berdasarkan volume...")
    
    # Get all symbols from exchangeInfo
    symbols = get_futures_symbols(
        quote_asset="USDT",
        api_key=api_key,
        api_secret=api_secret,
        testnet=testnet
    )
    
    if not symbols:
        print("❌ Tidak ada symbols ditemukan")
        return []
    
    print(f"✅ Ditemukan {len(symbols)} trading pairs di Futures")
    
    # Get 24h ticker stats untuk semua symbols (dengan volume data)
    print(f"📡 Mengambil 24h ticker statistics dengan volume...")
    from src.data.binance_futures_data import get_futures_24h_ticker
    
    ticker_df = get_futures_24h_ticker(
        symbol=None,  # Get all symbols
        api_key=api_key,
        api_secret=api_secret,
        testnet=testnet
    )
    
    if ticker_df is None or ticker_df.empty:
        print("❌ Gagal mengambil ticker data")
        return []
    
    # Sort berdasarkan quoteVolume (24h volume dalam USDT) descending
    if 'quoteVolume' in ticker_df.columns:
        ticker_df = ticker_df.sort_values('quoteVolume', ascending=False)
        top_symbols = ticker_df.head(limit)['symbol'].tolist()
    elif 'volume' in ticker_df.columns:
        # Fallback ke volume jika quoteVolume tidak ada
        ticker_df = ticker_df.sort_values('volume', ascending=False)
        top_symbols = ticker_df.head(limit)['symbol'].tolist()
    else:
        # Jika tidak ada volume data, gunakan semua symbols
        print("⚠️  Volume data tidak tersedia, menggunakan semua symbols")
        top_symbols = symbols[:limit]
    
    # Convert ke yfinance format
    result_symbols = []
    for symbol in top_symbols:
        yfinance_symbol = convert_futures_symbol_to_yfinance(symbol)
        result_symbols.append(yfinance_symbol)
    
    print(f"✅ Top {len(result_symbols)} coins (format yfinance):")
    for i, symbol in enumerate(result_symbols[:20], 1):
        print(f"   {i}. {symbol}")
    if len(result_symbols) > 20:
        print(f"   ... dan {len(result_symbols) - 20} coins lainnya")
    
    return result_symbols


def save_futures_coins_to_file(symbols: List[str], filename: str = "data/binance_futures_top_coins.json"):
    """
    Simpan list symbols ke file JSON
    
    Args:
        symbols: List of symbols
        filename: Nama file untuk disimpan
    """
    data = {
        'last_updated': datetime.now().isoformat(),
        'count': len(symbols),
        'symbols': symbols,
        'source': 'binance_futures',
        'endpoint': 'fapi/v1/exchangeInfo'
    }
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✅ Symbols disimpan ke {filename}")
    print(f"   Total: {len(symbols)} symbols")
    print(f"   Last updated: {data['last_updated']}")


def load_futures_coins_from_file(filename: str = "data/binance_futures_top_coins.json") -> List[str]:
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
        symbols = data.get('symbols', [])
        if symbols:
            print(f"✅ Loaded {len(symbols)} coins dari {filename}")
            print(f"   Last updated: {data.get('last_updated', 'Unknown')}")
        return symbols
    except FileNotFoundError:
        print(f"⚠️  File {filename} tidak ditemukan")
        return []
    except Exception as e:
        print(f"⚠️  Error loading file: {e}")
        return []


def main():
    """Main function untuk get dan save futures coins"""
    print("=" * 70)
    print("📊 BINANCE FUTURES - GET TOP COINS")
    print("=" * 70)
    print()
    
    api_key = BINANCE_API_KEY
    api_secret = BINANCE_API_SECRET
    
    if not api_key or not api_secret:
        print("⚠️  API key/secret tidak ditemukan di config")
        print("   Menggunakan public endpoints (rate limit lebih rendah)")
    
    # Get top coins
    top_coins = get_futures_top_coins_by_volume(
        limit=200,
        api_key=api_key,
        api_secret=api_secret,
        testnet=False
    )
    
    if top_coins:
        # Save ke file
        save_futures_coins_to_file(top_coins, "data/binance_futures_top_coins.json")
        
        # Print sample
        print(f"\n📋 Sample top 20 coins:")
        for i, symbol in enumerate(top_coins[:20], 1):
            print(f"   {i}. {symbol}")
    else:
        print("❌ Tidak ada coins yang ditemukan")


if __name__ == "__main__":
    main()

