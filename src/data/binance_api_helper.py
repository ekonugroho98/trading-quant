#!/usr/bin/env python3
"""
Binance API Helper
Helper function untuk memilih antara Spot API dan Futures API berdasarkan config
"""

from typing import Optional
import pandas as pd
from datetime import datetime, timedelta

try:
    from src.utils.config import BINANCE_API_TYPE, BINANCE_API_KEY, BINANCE_API_SECRET
except ImportError:
    BINANCE_API_TYPE = "spot"
    BINANCE_API_KEY = None
    BINANCE_API_SECRET = None


def get_binance_data(symbol: str,
                     days_back: int,
                     interval: str,
                     api_key: Optional[str] = None,
                     api_secret: Optional[str] = None) -> Optional[pd.DataFrame]:
    """
    Get data dari Binance (Spot atau Futures) berdasarkan config BINANCE_API_TYPE
    
    Args:
        symbol: Trading symbol (format yfinance: "BTC-USD" atau Binance: "BTCUSDT")
        days_back: Berapa hari ke belakang
        interval: Interval data (1m, 5m, 15m, 1h, 4h, 1d, etc.)
        api_key: Binance API Key (optional, akan gunakan dari config jika None)
        api_secret: Binance API Secret (optional, akan gunakan dari config jika None)
    
    Returns:
        DataFrame dengan kolom: date, Open, High, Low, Close, Volume
    """
    api_type = BINANCE_API_TYPE.lower() if BINANCE_API_TYPE else "spot"
    api_key = api_key or BINANCE_API_KEY
    api_secret = api_secret or BINANCE_API_SECRET
    
    print(f"📡 [BINANCE API] Using {api_type.upper()} API")
    print(f"   Symbol: {symbol}, Days back: {days_back}, Interval: {interval}")
    
    if api_type == "futures":
        # Gunakan Futures API
        print(f"🔵 [FUTURES API] Routing to Futures API")
        try:
            from src.data.binance_futures_data import get_futures_data
            return get_futures_data(
                symbol=symbol,
                days_back=days_back,
                interval=interval,
                api_key=api_key,
                api_secret=api_secret,
                testnet=False
            )
        except ImportError:
            print("⚠️  Futures API module tidak ditemukan, fallback ke Spot API")
            api_type = "spot"
    
    if api_type == "spot":
        # Gunakan Spot API
        print(f"🟢 [SPOT API] Routing to Spot API")
        try:
            from src.data.binance_data import get_data_binance
            return get_data_binance(
                symbol=symbol,
                days_back=days_back,
                interval=interval,
                api_key=api_key,
                api_secret=api_secret
            )
        except ImportError:
            print("❌ Spot API module tidak ditemukan")
            return None
    
    # Default: gunakan spot
    print(f"⚠️  Unknown BINANCE_API_TYPE: {api_type}, menggunakan Spot API")
    try:
        from src.data.binance_data import get_data_binance
        return get_data_binance(
            symbol=symbol,
            days_back=days_back,
            interval=interval,
            api_key=api_key,
            api_secret=api_secret
        )
    except ImportError:
        return None


def _process_futures_coins(coins: list, days: int, interval: str,
                          api_key: Optional[str], api_secret: Optional[str]) -> pd.DataFrame:
    """
    Process coins using Futures API
    
    Returns:
        DataFrame with MultiIndex columns for all coins
    """
    from src.data.binance_futures_data import get_futures_data
    import time
    
    all_data = {}
    successful = 0
    failed = 0
    
    print(f"   📊 Processing {len(coins)} coins...")
    
    for idx, symbol in enumerate(coins, 1):
        try:
            if idx > 1:
                time.sleep(0.2)
            
            print(f"   [{idx}/{len(coins)}] Processing {symbol}...")
            df = get_futures_data(
                symbol=symbol,
                days_back=days,
                interval=interval,
                api_key=api_key,
                api_secret=api_secret
            )
            
            if df is not None and not df.empty:
                from src.data.binance_futures_data import convert_futures_symbol_to_yfinance
                binance_symbol = symbol.replace("-USD", "") + "USDT" if symbol.endswith("-USD") else symbol.upper()
                
                df_multi = pd.DataFrame({
                    (binance_symbol, 'Open'): df['Open'],
                    (binance_symbol, 'High'): df['High'],
                    (binance_symbol, 'Low'): df['Low'],
                    (binance_symbol, 'Close'): df['Close'],
                    (binance_symbol, 'Volume'): df['Volume']
                }, index=df.index)
                
                all_data[binance_symbol] = df_multi
                successful += 1
                print(f"      ✅ {symbol}: Success ({len(df)} records)")
            else:
                failed += 1
                print(f"      ⚠️  {symbol}: Data kosong atau None, skip")
        except Exception as e:
            failed += 1
            error_msg = str(e)[:100]
            print(f"      ⚠️  {symbol}: Error - {error_msg}, skip dan lanjut ke coin berikutnya")
    
    print(f"   📊 Screening summary: {successful} successful, {failed} failed")
    
    if not all_data:
        return pd.DataFrame()
    
    result = pd.concat(all_data.values(), axis=1)
    result.columns = pd.MultiIndex.from_tuples(result.columns)
    return result


def _process_spot_coins(coins: list, days: int, interval: str,
                        api_key: Optional[str], api_secret: Optional[str]) -> pd.DataFrame:
    """
    Process coins using Spot API
    
    Returns:
        DataFrame with coin data
    """
    from src.screening.coin_screening import get_coins_snapshot_binance
    return get_coins_snapshot_binance(
        coins=coins,
        days=days,
        interval=interval,
        api_key=api_key,
        api_secret=api_secret
    )


def get_binance_coins_snapshot(coins: list,
                               days: int = 90,
                               interval: str = "4h",
                               api_key: Optional[str] = None,
                               api_secret: Optional[str] = None) -> pd.DataFrame:
    """
    Get coins snapshot dari Binance (Spot atau Futures) berdasarkan config BINANCE_API_TYPE
    
    Args:
        coins: List of coin symbols
        days: Jumlah hari data
        interval: Interval/timeframe
        api_key: Binance API Key (optional)
        api_secret: Binance API Secret (optional)
    
    Returns:
        DataFrame dengan data untuk semua coins
    """
    api_type = BINANCE_API_TYPE.lower()
    api_key = api_key or BINANCE_API_KEY
    api_secret = api_secret or BINANCE_API_SECRET
    
    if api_type == "futures":
        try:
            return _process_futures_coins(coins, days, interval, api_key, api_secret)
        except ImportError:
            print("⚠️  Futures API module tidak ditemukan, fallback ke Spot API")
            api_type = "spot"
    
    if api_type == "spot":
        try:
            return _process_spot_coins(coins, days, interval, api_key, api_secret)
        except ImportError:
            print("❌ Spot API module tidak ditemukan")
            return pd.DataFrame()
    
    # Default: gunakan spot
    print(f"⚠️  Unknown BINANCE_API_TYPE: {api_type}, menggunakan Spot API")
    try:
        return _process_spot_coins(coins, days, interval, api_key, api_secret)
    except ImportError:
        return pd.DataFrame()


def get_binance_symbols(quote_asset: str = "USDT",
                       api_key: Optional[str] = None,
                       api_secret: Optional[str] = None) -> list:
    """
    Get list of symbols dari Binance (Spot atau Futures) berdasarkan config BINANCE_API_TYPE
    
    Args:
        quote_asset: Quote asset filter (default: "USDT")
        api_key: Binance API Key (optional)
        api_secret: Binance API Secret (optional)
    
    Returns:
        List of symbols
    """
    api_type = BINANCE_API_TYPE.lower()
    api_key = api_key or BINANCE_API_KEY
    api_secret = api_secret or BINANCE_API_SECRET
    
    if api_type == "futures":
        # Gunakan Futures API
        try:
            from src.data.binance_futures_data import get_futures_symbols, convert_futures_symbol_to_yfinance
            symbols = get_futures_symbols(
                quote_asset=quote_asset
            )
            # Convert ke yfinance format
            return [convert_futures_symbol_to_yfinance(s) for s in symbols]
        except ImportError:
            print("⚠️  Futures API module tidak ditemukan, fallback ke Spot API")
            api_type = "spot"
    
    if api_type == "spot":
        # Gunakan Spot API
        try:
            from src.data.get_binance_coins import get_all_binance_symbols
            symbols_data = get_all_binance_symbols(
                api_key=api_key,
                api_secret=api_secret,
                quote_asset=quote_asset
            )
            # Convert ke yfinance format
            result = []
            for symbol_info in symbols_data:
                symbol = symbol_info.get('symbol', '')
                if symbol.endswith('USDT'):
                    base = symbol.replace('USDT', '')
                    result.append(f"{base}-USD")
            return result
        except ImportError:
            print("❌ Spot API module tidak ditemukan")
            return []
    
    # Default: gunakan spot
    print(f"⚠️  Unknown BINANCE_API_TYPE: {api_type}, menggunakan Spot API")
    try:
        from src.data.get_binance_coins import get_all_binance_symbols
        symbols_data = get_all_binance_symbols(
            api_key=api_key,
            api_secret=api_secret,
            quote_asset=quote_asset
        )
        result = []
        for symbol_info in symbols_data:
            symbol = symbol_info.get('symbol', '')
            if symbol.endswith('USDT'):
                base = symbol.replace('USDT', '')
                result.append(f"{base}-USD")
        return result
    except ImportError:
        return []

