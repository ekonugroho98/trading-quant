"""
Coin Screening Module
Screening multiple coins untuk menemukan peluang trading terbaik
Menggunakan quick metrics tanpa ML atau DeepSeek AI (untuk efisiensi)
Support yfinance dan Binance API
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta

# Import config untuk data source
try:
    from config import DATA_SOURCE, BINANCE_API_KEY, BINANCE_API_SECRET, get_interval
except ImportError:
    DATA_SOURCE = "yfinance"
    BINANCE_API_KEY = None
    BINANCE_API_SECRET = None
    def get_interval():
        return "4h"  # Default fallback


# Load coins dari Binance (top 200) jika file tersedia
def load_binance_coins(filename: str = "binance_top_coins.json") -> List[str]:
    """
    Load list coins dari file JSON yang dihasilkan get_binance_coins.py
    
    Args:
        filename: Nama file JSON
    
    Returns:
        List of symbols dalam format yfinance (e.g., ["BTC-USD", "ETH-USD"])
    """
    try:
        import json
        with open(filename, 'r') as f:
            data = json.load(f)
        symbols = data.get('symbols', [])
        if symbols:
            print(f"✅ Loaded {len(symbols)} coins dari {filename}")
            print(f"   Last updated: {data.get('last_updated', 'Unknown')}")
        return symbols
    except FileNotFoundError:
        print(f"⚠️  File {filename} tidak ditemukan, menggunakan DEFAULT_COINS")
        return []
    except Exception as e:
        print(f"⚠️  Error loading {filename}: {e}, menggunakan DEFAULT_COINS")
        return []

# Coba load coins dari Binance, fallback ke DEFAULT_COINS
BINANCE_COINS = load_binance_coins()

# Daftar 150 coin populer untuk screening (fallback jika Binance coins tidak tersedia)
# Semua coin ini telah diverifikasi tersedia di yfinance
DEFAULT_COINS = [
    # Top 20 Major Cryptocurrencies
    "BTC-USD", "ETH-USD", "BNB-USD", "XRP-USD", "DOGE-USD",
    "SOL-USD", "ADA-USD", "DOT-USD", "LINK-USD", "LTC-USD",
    "AVAX-USD", "ATOM-USD", "ETC-USD", "XLM-USD", "ALGO-USD",
    "VET-USD", "FIL-USD", "TRX-USD", "AAVE-USD", "MKR-USD",
    
    # DeFi & Exchange Tokens
    "SUSHI-USD", "YFI-USD", "CRV-USD", "1INCH-USD", "SNX-USD",
    "BAL-USD", "ZRX-USD", "OMG-USD",
    
    # Layer 2 & Scaling Solutions
    "ARB-USD", "OP-USD", "METIS-USD", "BOBA-USD", "LRC-USD",
    "SKL-USD", "POLY-USD", "CELR-USD",
    
    # Gaming & Metaverse
    "AXS-USD", "SAND-USD", "MANA-USD", "ENJ-USD", "GALA-USD",
    "CHZ-USD", "FLOW-USD", "ROSE-USD", "WAXP-USD", "TLM-USD",
    
    # AI & Big Data
    "FET-USD", "AGIX-USD", "OCEAN-USD", "ANKR-USD", "STORJ-USD",
    "BAND-USD", "NMR-USD", "ARKM-USD",
    
    # Infrastructure & Smart Contracts
    "ICP-USD", "NEAR-USD", "EGLD-USD", "HBAR-USD", "QNT-USD",
    "THETA-USD", "ZIL-USD", "ONE-USD", "IOTA-USD", "XTZ-USD",
    
    # Privacy Coins
    "XMR-USD", "DASH-USD", "ZEC-USD", "ZEN-USD", "SCRT-USD",
    
    # Bitcoin Forks
    "BCH-USD", "BSV-USD", "BTG-USD",
    
    # Meme Coins
    "SHIB-USD", "FLOKI-USD", "BONK-USD", "WIF-USD", "BOME-USD",
    "MYRO-USD", "TURBO-USD",
    
    # Real World Assets
    "PAXG-USD", "OXT-USD",
    
    # New & Trending (2024-2025)
    "WLD-USD", "PENDLE-USD", "AEVO-USD", "ENA-USD",
    "TNSR-USD", "REZ-USD", "NOT-USD", "LISTA-USD", "MANTA-USD",
    "XAI-USD",
    
    # Additional Popular Coins
    "WAVES-USD", "EOS-USD", "BAT-USD", "COTI-USD", "DENT-USD",
    "CELO-USD", "KLAY-USD", "AR-USD", "CTSI-USD", "BADGER-USD",
    "FIS-USD", "OM-USD", "POND-USD", "DEGO-USD", "ALICE-USD",
    "PERP-USD", "RAMP-USD", "CFX-USD", "AUTO-USD", "TKO-USD",
    "PROM-USD", "QUICK-USD", "ALPACA-USD", "FARM-USD", "MBOX-USD",
    "FORTH-USD", "CAKE-USD", "BNX-USD", "RGT-USD", "MOVR-USD",
    "ENS-USD", "KP3R-USD", "QI-USD", "PORTO-USD", "POWR-USD",
    "VGX-USD", "JASMY-USD", "AMP-USD", "PYTH-USD", "GFT-USD",
    "HOOK-USD", "LQTY-USD", "RAD-USD", "ID-USD", "AI-USD",
    "JTO-USD", "BIGTIME-USD", "FARTCOIN-USD", "LUNC-USD", "USTC-USD",
    "RUNE-USD", "KAVA-USD", "OSMO-USD", "JUNO-USD", "HUAHUA-USD",
    "INJ-USD", "TIA-USD", "SEI-USD", "BLUR-USD", "DYM-USD",
    "STRK-USD", "MEME-USD"
]


def get_coins_snapshot(coins: List[str], days: int = 90, 
                       data_source: Optional[str] = None,
                       api_key: Optional[str] = None,
                       api_secret: Optional[str] = None,
                       interval: Optional[str] = None) -> pd.DataFrame:
    """
    Ambil data snapshot untuk multiple coins sekaligus
    
    Args:
        coins: List of coin symbols (format: BTC-USD)
        days: Jumlah hari data yang diambil (default: 90)
        data_source: "yfinance" atau "binance" (default: dari config.py)
        api_key: Binance API key (optional, default: dari config.py)
        api_secret: Binance API secret (optional, default: dari config.py)
        interval: Interval/timeframe (default: dari config.py via get_interval())
    
    Returns:
        DataFrame dengan MultiIndex (Ticker, Price) untuk kompatibilitas
    """
    # Gunakan data_source dari parameter atau config
    source = data_source or DATA_SOURCE
    
    # Gunakan interval dari parameter atau config
    if interval is None:
        try:
            interval = get_interval()
        except:
            interval = "4h"  # Fallback default
    
    if source == "binance":
        return get_coins_snapshot_binance(coins, days, api_key, api_secret, interval)
    else:
        return get_coins_snapshot_yfinance(coins, days, interval)


def get_coins_snapshot_yfinance(coins: List[str], days: int = 90, interval: str = "4h") -> pd.DataFrame:
    """
    Ambil data snapshot dari yfinance
    
    Args:
        coins: List of coin symbols
        days: Jumlah hari data
        interval: Interval/timeframe (default: "1d")
    """
    try:
        print(f"📊 Mengambil data snapshot dari yfinance untuk {len(coins)} coins...")
        print(f"   Interval: {interval}")
        # group_by='ticker' akan membuat struktur (Ticker, Price) bukan (Price, Ticker)
        data = yf.download(
            coins,
            period=f"{days}d",
            interval=interval,
            progress=False,
            group_by='ticker',
            auto_adjust=True
        )
        
        if data.empty:
            print("⚠️  Data kosong")
            return pd.DataFrame()
        
        print(f"✅ Data berhasil diambil: {len(data)} records")
        return data
        
    except Exception as e:
        print(f"❌ Error mengambil data snapshot dari yfinance: {e}")
        return pd.DataFrame()


def get_coins_snapshot_binance(coins: List[str], days: int = 90,
                               api_key: Optional[str] = None,
                               api_secret: Optional[str] = None,
                               interval: str = "4h") -> pd.DataFrame:
    """
    Ambil data snapshot dari Binance API untuk multiple coins
    Menggunakan binance_data.download_multiple_symbols untuk batch processing
    
    Args:
        coins: List of coin symbols
        days: Jumlah hari data
        api_key: Binance API key (optional)
        api_secret: Binance API secret (optional)
        interval: Interval/timeframe (default: "1d")
    """
    try:
        from binance_data import download_multiple_symbols
        
        # Gunakan API key dari parameter atau config
        api_key = api_key or BINANCE_API_KEY
        api_secret = api_secret or BINANCE_API_SECRET
        
        print(f"📊 Mengambil data snapshot dari Binance API untuk {len(coins)} coins...")
        print(f"   Periode: {days} hari")
        print(f"   Interval: {interval}")
        
        # Convert days ke period string
        period_map = {
            1: "1d", 7: "7d", 30: "30d", 90: "90d",
            180: "6mo", 365: "1y"
        }
        period = period_map.get(days, "90d")
        
        # Download multiple symbols sekaligus
        data = download_multiple_symbols(
            symbols=coins,
            period=period,
            interval=interval,  # Gunakan interval dari parameter, bukan hardcoded "1d"
            api_key=api_key,
            api_secret=api_secret
        )
        
        if data.empty:
            print("⚠️  Data kosong dari Binance")
            return pd.DataFrame()
        
        print(f"✅ Data berhasil diambil dari Binance: {len(data)} records")
        return data
        
    except ImportError as e:
        print(f"❌ Binance data module tidak tersedia: {e}")
        print("   Fallback ke yfinance...")
        return get_coins_snapshot_yfinance(coins, days, interval)
    except Exception as e:
        print(f"❌ Error mengambil data snapshot dari Binance: {e}")
        print("   Fallback ke yfinance...")
        return get_coins_snapshot_yfinance(coins, days, interval)


def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """
    Hitung Exponential Moving Average (EMA)
    
    Args:
        series: Price series
        period: Period untuk EMA
    
    Returns:
        EMA series
    """
    return series.ewm(span=period, adjust=False).mean()


def calculate_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
    """
    Hitung MACD (Moving Average Convergence Divergence)
    
    Args:
        series: Price series
        fast: Fast EMA period (default: 12)
        slow: Slow EMA period (default: 26)
        signal: Signal line period (default: 9)
    
    Returns:
        Dictionary dengan MACD, Signal, dan Histogram
    """
    ema_fast = calculate_ema(series, fast)
    ema_slow = calculate_ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line
    
    return {
        'macd': macd_line,
        'signal': signal_line,
        'histogram': histogram
    }


def calculate_support_resistance_simple(close_data: pd.Series, window: int = 20) -> Tuple[float, float]:
    """
    Hitung Support dan Resistance sederhana menggunakan rolling min/max
    
    Args:
        close_data: Close price series
        window: Window untuk rolling min/max
    
    Returns:
        Tuple (support, resistance)
    """
    if len(close_data) < window:
        window = len(close_data)
    
    support = float(close_data.rolling(window=window, min_periods=1).min().iloc[-1])
    resistance = float(close_data.rolling(window=window, min_periods=1).max().iloc[-1])
    
    return support, resistance


def calculate_quick_metrics(data: pd.DataFrame, symbol: str) -> Optional[Dict]:
    """
    Hitung quick metrics untuk satu coin menggunakan 5 indikator wajib:
    1. EMA 20, 50, 200 → trend
    2. RSI → momentum
    3. MACD → perubahan arah
    4. Volume → validasi
    5. Support / Resistance → level entry aman
    
    Args:
        data: DataFrame dengan data coin (bisa MultiIndex atau single column)
        symbol: Symbol coin (contoh: BTC-USD)
    
    Returns:
        Dictionary dengan metrics atau None jika error
    """
    try:
        # Handle MultiIndex DataFrame
        if isinstance(data.columns, pd.MultiIndex):
            col_names = data.columns.names
            
            # Cek apakah ini format Binance (BTCUSDT) atau yfinance (BTC-USD)
            # Coba convert symbol ke Binance format
            try:
                from binance_data import convert_symbol_to_binance
                binance_symbol = convert_symbol_to_binance(symbol)
            except:
                binance_symbol = symbol.replace("-", "").upper()  # Fallback: BTC-USD -> BTCUSD
            
            # Cek semua kemungkinan format column
            possible_close_cols = [
                (symbol, 'Close'),           # yfinance format: (BTC-USD, Close)
                (binance_symbol, 'Close'),   # Binance format: (BTCUSDT, Close)
                ('Close', symbol),           # Alternative format: (Close, BTC-USD)
                ('Close', binance_symbol),   # Alternative format: (Close, BTCUSDT)
            ]
            
            possible_volume_cols = [
                (symbol, 'Volume'),
                (binance_symbol, 'Volume'),
                ('Volume', symbol),
                ('Volume', binance_symbol),
            ]
            
            # Cari column yang ada di data
            close_col = None
            volume_col = None
            
            for col in possible_close_cols:
                if col in data.columns:
                    close_col = col
                    break
            
            for col in possible_volume_cols:
                if col in data.columns:
                    volume_col = col
                    break
            
            if close_col is None:
                # Debug: print available columns untuk troubleshooting (hanya untuk beberapa coin pertama)
                # Jangan print terlalu banyak untuk menghindari spam
                if symbol in ['BTC-USD', 'ETH-USD', 'BNB-USD'] or len(data.columns) < 20:
                    available_symbols = set()
                    for col in data.columns:
                        if isinstance(col, tuple) and len(col) == 2:
                            available_symbols.add(col[0])
                    print(f"⚠️  Column tidak ditemukan untuk {symbol} (binance: {binance_symbol})")
                    print(f"   Mencari: {possible_close_cols[:2]}")
                    print(f"   Available symbols: {list(available_symbols)[:10]}")
                return None
            
            close_data = data[close_col].dropna()
            volume_data = data[volume_col].dropna() if volume_col and volume_col in data.columns else None
            
            # Debug: cek apakah data kosong setelah dropna
            if len(close_data) == 0:
                if symbol in ['BTC-USD', 'ETH-USD', 'BNB-USD']:
                    print(f"⚠️  Data kosong setelah dropna untuk {symbol} (column: {close_col})")
                    print(f"   Data shape sebelum dropna: {data[close_col].shape}")
                    print(f"   Data sample: {data[close_col].head()}")
                return None
        else:
            # Single column DataFrame
            if 'Close' not in data.columns:
                return None
            close_data = data['Close'].dropna()
            volume_data = data['Volume'].dropna() if 'Volume' in data.columns else None
        
        if len(close_data) < 2:
            if symbol in ['BTC-USD', 'ETH-USD', 'BNB-USD']:
                print(f"⚠️  Data terlalu sedikit untuk {symbol}: {len(close_data)} records (min: 2)")
            return None
        
        # Current price
        current_price = float(close_data.iloc[-1])
        prev_price = float(close_data.iloc[-2]) if len(close_data) >= 2 else current_price
        
        # Price changes
        price_change_1d = ((current_price - prev_price) / prev_price * 100) if prev_price > 0 else 0
        
        # 7-day change (jika data cukup)
        if len(close_data) >= 7:
            price_7d_ago = float(close_data.iloc[-7])
            price_change_7d = ((current_price - price_7d_ago) / price_7d_ago * 100) if price_7d_ago > 0 else 0
        else:
            price_change_7d = price_change_1d * 7  # Estimasi
        
        # Volume metrics (Indikator 4: Volume → validasi)
        if volume_data is not None and len(volume_data) >= 2:
            current_volume = float(volume_data.iloc[-1])
            avg_volume = float(volume_data.tail(7).mean()) if len(volume_data) >= 7 else float(volume_data.mean())
            volume_ratio = (current_volume / avg_volume) if avg_volume > 0 else 1.0
        else:
            volume_ratio = 1.0
            current_volume = 0
        
        # Indikator 1: EMA 20, 50, 200 → trend
        # Adaptif: gunakan periode yang lebih kecil jika data terbatas
        ema_20 = None
        ema_50 = None
        ema_200 = None
        trend_signal = "NEUTRAL"
        
        # Adaptif: sesuaikan periode EMA berdasarkan jumlah data yang tersedia
        data_length = len(close_data)
        
        # EMA 20 (minimum 10 data points untuk EMA yang reliable)
        if data_length >= 10:
            # Gunakan periode yang lebih kecil jika data terbatas
            ema_period_20 = min(20, max(5, data_length // 2))
            ema_20_series = calculate_ema(close_data, ema_period_20)
            ema_20 = float(ema_20_series.iloc[-1]) if pd.notna(ema_20_series.iloc[-1]) else None
            
            # EMA 50 (minimum 25 data points)
            if data_length >= 25:
                ema_period_50 = min(50, max(10, data_length // 2))
                ema_50_series = calculate_ema(close_data, ema_period_50)
                ema_50 = float(ema_50_series.iloc[-1]) if pd.notna(ema_50_series.iloc[-1]) else None
                
                # EMA 200 (minimum 100 data points)
                if data_length >= 100:
                    ema_period_200 = min(200, max(50, data_length // 2))
                    ema_200_series = calculate_ema(close_data, ema_period_200)
                    ema_200 = float(ema_200_series.iloc[-1]) if pd.notna(ema_200_series.iloc[-1]) else None
                    
                    # Trend signal berdasarkan EMA alignment (3 EMA)
                    if ema_20 and ema_50 and ema_200:
                        if current_price > ema_20 > ema_50 > ema_200:
                            trend_signal = "BULLISH"  # Uptrend kuat
                        elif current_price < ema_20 < ema_50 < ema_200:
                            trend_signal = "BEARISH"  # Downtrend kuat
                        elif ema_20 > ema_50:
                            trend_signal = "BULLISH_WEAK"  # Uptrend lemah
                        elif ema_20 < ema_50:
                            trend_signal = "BEARISH_WEAK"  # Downtrend lemah
                elif ema_20 and ema_50:
                    # Jika tidak cukup data untuk EMA 200, gunakan EMA 20 dan 50
                    if current_price > ema_20 > ema_50:
                        trend_signal = "BULLISH"
                    elif current_price < ema_20 < ema_50:
                        trend_signal = "BEARISH"
                    elif ema_20 > ema_50:
                        trend_signal = "BULLISH_WEAK"
                    else:
                        trend_signal = "BEARISH_WEAK"
            elif ema_20:
                # Jika hanya ada EMA 20, gunakan price vs EMA 20
                if current_price > ema_20:
                    trend_signal = "BULLISH_WEAK"
                else:
                    trend_signal = "BEARISH_WEAK"
        
        # Indikator 2: RSI → momentum
        if len(close_data) >= 3:
            # Gunakan period yang lebih kecil jika data terbatas
            rsi_period = min(14, len(close_data) - 1)
            delta = close_data.diff().dropna()
            if len(delta) >= 2:
                gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period, min_periods=1).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period, min_periods=1).mean()
                
                # Handle division by zero
                rs = gain / loss.replace(0, np.nan)
                rsi = 100 - (100 / (1 + rs.replace(np.inf, 100)))
                rsi = float(rsi.iloc[-1]) if pd.notna(rsi.iloc[-1]) and not np.isinf(rsi.iloc[-1]) else 50
            else:
                rsi = 50
        else:
            rsi = 50
        
        # Indikator 3: MACD → perubahan arah
        macd_value = None
        macd_signal_value = None
        macd_histogram = None
        macd_signal = "NEUTRAL"
        
        if len(close_data) >= 26:  # Minimum untuk MACD (slow period)
            macd_data = calculate_macd(close_data, fast=12, slow=26, signal=9)
            macd_value = float(macd_data['macd'].iloc[-1]) if pd.notna(macd_data['macd'].iloc[-1]) else None
            macd_signal_value = float(macd_data['signal'].iloc[-1]) if pd.notna(macd_data['signal'].iloc[-1]) else None
            macd_histogram = float(macd_data['histogram'].iloc[-1]) if pd.notna(macd_data['histogram'].iloc[-1]) else None
            
            # MACD signal: bullish jika MACD > Signal dan histogram > 0
            if macd_value is not None and macd_signal_value is not None:
                if macd_value > macd_signal_value and macd_histogram and macd_histogram > 0:
                    macd_signal = "BULLISH"
                elif macd_value < macd_signal_value and macd_histogram and macd_histogram < 0:
                    macd_signal = "BEARISH"
        
        # Indikator 5: Support / Resistance → level entry aman
        support, resistance = calculate_support_resistance_simple(close_data, window=20)
        
        # Scoring berdasarkan 5 indikator wajib
        # Normalize semua metrics ke range yang sama untuk akurasi lebih baik
        
        # 1. EMA Trend Score (Indikator 1: EMA 20, 50, 200 → trend)
        # BULLISH = 1, BULLISH_WEAK = 0.5, NEUTRAL = 0, BEARISH_WEAK = -0.5, BEARISH = -1
        if trend_signal == "BULLISH":
            trend_score = 1.0
        elif trend_signal == "BULLISH_WEAK":
            trend_score = 0.5
        elif trend_signal == "BEARISH":
            trend_score = -1.0
        elif trend_signal == "BEARISH_WEAK":
            trend_score = -0.5
        else:
            trend_score = 0.0
        
        # 2. RSI Score (Indikator 2: RSI → momentum)
        # Normalize: 0-100 -> -1 to +1, dengan RSI 50 = 0
        # Untuk LONG: RSI 50-70 = good (momentum positif tapi tidak overbought)
        # Untuk SHORT: RSI 30-50 = good (momentum negatif tapi tidak oversold)
        rsi_score = (rsi - 50) / 50  # -1 to +1
        
        # 3. MACD Score (Indikator 3: MACD → perubahan arah)
        # BULLISH = 1, BEARISH = -1, NEUTRAL = 0
        if macd_signal == "BULLISH":
            macd_score = 1.0
        elif macd_signal == "BEARISH":
            macd_score = -1.0
        else:
            macd_score = 0.0
        
        # 4. Volume Score (Indikator 4: Volume → validasi)
        # Volume ratio 1.0 = score 0, >1.0 = positive, <1.0 = negative
        volume_score = np.clip((volume_ratio - 1) / 2, -0.5, 1)
        
        # 5. Support/Resistance Score (Indikator 5: Support / Resistance → level entry aman)
        # Hitung jarak dari current price ke support/resistance
        # Untuk LONG: dekat support = bagus (entry aman), dekat resistance = kurang bagus
        # Untuk SHORT: dekat resistance = bagus (entry aman), dekat support = kurang bagus
        price_range = resistance - support if resistance > support else current_price * 0.1
        if price_range > 0:
            dist_to_support = ((current_price - support) / price_range) if price_range > 0 else 0.5
            dist_to_resistance = ((resistance - current_price) / price_range) if price_range > 0 else 0.5
            # Score: dekat support = positif untuk LONG (inverse: 1 - dist_to_support)
            #        dekat resistance = positif untuk SHORT (inverse: 1 - dist_to_resistance)
            sr_score_long = 1.0 - dist_to_support  # 1 (di support) to 0 (di resistance)
            sr_score_short = 1.0 - dist_to_resistance  # 1 (di resistance) to 0 (di support)
        else:
            sr_score_long = 0.5
            sr_score_short = 0.5
        
        # Combined score dengan weights yang seimbang untuk 5 indikator
        # Score untuk LONG (bullish)
        long_score = (
            trend_score * 0.30 +           # 30% weight on EMA trend (trend adalah yang terpenting)
            rsi_score * 0.20 +             # 20% weight on RSI momentum
            macd_score * 0.20 +            # 20% weight on MACD perubahan arah
            volume_score * 0.15 +          # 15% weight on Volume validasi
            sr_score_long * 0.15           # 15% weight on Support/Resistance entry level
        )
        
        # Score untuk SHORT (bearish) - inverse logic
        short_score = (
            (-trend_score) * 0.30 +        # 30% weight on EMA trend (inverse)
            (-rsi_score) * 0.20 +          # 20% weight on RSI momentum (inverse)
            (-macd_score) * 0.20 +         # 20% weight on MACD perubahan arah (inverse)
            volume_score * 0.15 +          # 15% weight on Volume validasi (sama)
            sr_score_short * 0.15          # 15% weight on Support/Resistance entry level (inverse)
        )
        
        # Determine best direction
        if long_score > short_score:
            best_direction = "LONG"
            best_score = long_score
        elif short_score > long_score:
            best_direction = "SHORT"
            best_score = short_score
        else:
            best_direction = "NEUTRAL"
            best_score = (long_score + short_score) / 2
        
        return {
            'symbol': symbol,
            'current_price': current_price,
            'price_change_1d': price_change_1d,
            'price_change_7d': price_change_7d,
            # Indikator 1: EMA 20, 50, 200 → trend
            'ema_20': ema_20,
            'ema_50': ema_50,
            'ema_200': ema_200,
            'trend_signal': trend_signal,
            # Indikator 2: RSI → momentum
            'rsi': rsi,
            'rsi_signal': "OVERSOLD" if rsi < 30 else ("OVERBOUGHT" if rsi > 70 else "NEUTRAL"),
            # Indikator 3: MACD → perubahan arah
            'macd': macd_value,
            'macd_signal_line': macd_signal_value,
            'macd_histogram': macd_histogram,
            'macd_signal': macd_signal,
            # Indikator 4: Volume → validasi
            'volume_ratio': volume_ratio,
            'current_volume': current_volume,
            # Indikator 5: Support / Resistance → level entry aman
            'support': support,
            'resistance': resistance,
            # Scores
            'combined_score': best_score,  # Best score (long or short)
            'long_score': long_score,
            'short_score': short_score,
            'best_direction': best_direction  # LONG, SHORT, or NEUTRAL
        }
        
    except Exception as e:
        print(f"⚠️  Error menghitung metrics untuk {symbol}: {e}")
        return None


def screen_coins(
    coins: Optional[List[str]] = None,
    days: int = 90,
    min_volume_ratio: float = 0.3,  # Lebih longgar: 0.3 (was 0.5)
    min_price_change: float = -80.0,  # Lebih longgar: -80% (was -50%)
    max_price_change: float = 200.0,  # Lebih longgar: +200% (was +100%)
    rsi_range: Optional[Tuple[float, float]] = None,
    top_n: int = 10,
    data_source: Optional[str] = None,
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
    use_adaptive_filtering: bool = True,  # Auto-relax filters jika tidak ada hasil
    trade_direction: str = "both"  # "long", "short", atau "both"
) -> List[Dict]:
    """
    Screen multiple coins berdasarkan criteria
    
    Args:
        coins: List of coin symbols (default: DEFAULT_COINS)
        days: Jumlah hari data (default: 90)
        min_volume_ratio: Minimum volume ratio (default: 0.3, lebih longgar)
        min_price_change: Minimum price change % (default: -80, lebih longgar)
        max_price_change: Maximum price change % (default: 200, lebih longgar)
        use_adaptive_filtering: Auto-relax filters jika tidak ada hasil (default: True)
        trade_direction: "long", "short", atau "both" (default: "both")
        rsi_range: RSI range (min, max) atau None untuk semua (default: None)
        top_n: Jumlah top coins yang dikembalikan (default: 10)
        data_source: "yfinance" atau "binance" (default: dari config.py)
        api_key: Binance API key (optional, default: dari config.py)
        api_secret: Binance API secret (optional, default: dari config.py)
    
    Returns:
        List of dictionaries dengan coin metrics, sorted by combined_score
    """
    if coins is None:
        # Gunakan Binance coins jika tersedia, fallback ke DEFAULT_COINS
        coins = BINANCE_COINS if BINANCE_COINS else DEFAULT_COINS
        if BINANCE_COINS:
            print(f"📋 Menggunakan {len(coins)} coins dari Binance (top by volume)")
        else:
            print(f"📋 Menggunakan {len(coins)} coins dari DEFAULT_COINS")
    
    print(f"\n🔍 Screening {len(coins)} coins...")
    print(f"📅 Periode: {days} hari")
    print(f"📊 Filter: Volume ratio >= {min_volume_ratio}, Price change: {min_price_change}% to {max_price_change}%")
    print(f"📈 Trade Direction: {trade_direction.upper()}")
    if rsi_range:
        print(f"📈 RSI range: {rsi_range[0]} - {rsi_range[1]}")
    print()
    
    # Ambil interval dari config
    try:
        from config import get_interval
        interval = get_interval()
    except:
        interval = "4h"  # Fallback default
    
    # Ambil data snapshot untuk semua coins
    data = get_coins_snapshot(coins, days, data_source, api_key, api_secret, interval)
    
    if data.empty:
        print("❌ Tidak ada data untuk screening")
        return []
    
    # Hitung metrics untuk setiap coin
    results = []
    metrics_calculated = 0
    metrics_failed = 0
    filtered_out = 0
    
    for symbol in coins:
        metrics = calculate_quick_metrics(data, symbol)
        if metrics:
            metrics_calculated += 1
            # Apply filters
            if metrics['volume_ratio'] < min_volume_ratio:
                filtered_out += 1
                continue
            if metrics['price_change_7d'] < min_price_change or metrics['price_change_7d'] > max_price_change:
                filtered_out += 1
                continue
            if rsi_range:
                if metrics['rsi'] < rsi_range[0] or metrics['rsi'] > rsi_range[1]:
                    filtered_out += 1
                    continue
            
            # Filter berdasarkan trade_direction
            if trade_direction == "long":
                # Hanya ambil coin dengan long_score lebih tinggi
                if metrics['long_score'] <= metrics['short_score']:
                    filtered_out += 1
                    continue
                # Update combined_score untuk long only
                metrics['combined_score'] = metrics['long_score']
            elif trade_direction == "short":
                # Hanya ambil coin dengan short_score lebih tinggi
                if metrics['short_score'] <= metrics['long_score']:
                    filtered_out += 1
                    continue
                # Update combined_score untuk short only
                metrics['combined_score'] = metrics['short_score']
            # else: "both" - tidak ada filter, gunakan best_score yang sudah dihitung
            
            results.append(metrics)
        else:
            metrics_failed += 1
    
    # Log statistik
    print(f"📊 Statistik Screening:")
    print(f"   ✅ Metrics berhasil dihitung: {metrics_calculated} coins")
    print(f"   ❌ Metrics gagal dihitung: {metrics_failed} coins")
    print(f"   🚫 Terfilter: {filtered_out} coins")
    print(f"   ✅ Lolos filter: {len(results)} coins")
    print()
    
    # Adaptive filtering: jika tidak ada hasil, relax filters
    if use_adaptive_filtering and len(results) == 0:
        print("⚠️  Tidak ada hasil dengan filter ketat, mencoba dengan filter lebih longgar...")
        
        # Relaxed filters
        relaxed_volume_ratio = max(0.1, min_volume_ratio * 0.5)  # 50% dari original
        relaxed_min_change = min_price_change * 1.5  # 50% lebih longgar
        relaxed_max_change = max_price_change * 1.5  # 50% lebih longgar
        
        print(f"   Volume ratio: {relaxed_volume_ratio:.2f} (was {min_volume_ratio:.2f})")
        print(f"   Price change: {relaxed_min_change:.1f}% to {relaxed_max_change:.1f}% (was {min_price_change:.1f}% to {max_price_change:.1f}%)")
        
        for symbol in coins:
            metrics = calculate_quick_metrics(data, symbol)
            if metrics:
                # Apply relaxed filters
                if metrics['volume_ratio'] < relaxed_volume_ratio:
                    continue
                if metrics['price_change_7d'] < relaxed_min_change or metrics['price_change_7d'] > relaxed_max_change:
                    continue
                # RSI range tetap sama (jika ada)
                if rsi_range:
                    if metrics['rsi'] < rsi_range[0] or metrics['rsi'] > rsi_range[1]:
                        continue
                
                results.append(metrics)
        
        if len(results) > 0:
            print(f"✅ Ditemukan {len(results)} coin dengan filter lebih longgar")
    
    # Jika masih tidak ada hasil, return semua coin dengan score terbaik (tanpa filter)
    if len(results) == 0:
        print("⚠️  Masih tidak ada hasil, mengembalikan semua coin dengan score terbaik (tanpa filter)...")
        for symbol in coins:
            metrics = calculate_quick_metrics(data, symbol)
            if metrics:
                results.append(metrics)
    
    # Sort by combined_score (descending)
    results.sort(key=lambda x: x['combined_score'], reverse=True)
    
    # Return top N
    return results[:top_n]


def format_screening_results(results: List[Dict]) -> str:
    """
    Format screening results untuk ditampilkan
    
    Args:
        results: List of coin metrics dictionaries
    
    Returns:
        Formatted string
    """
    if not results:
        return "❌ Tidak ada coin yang memenuhi criteria"
    
    lines = []
    lines.append("=" * 70)
    lines.append("🔍 COIN SCREENING RESULTS")
    lines.append("=" * 70)
    lines.append("")
    
    for i, coin in enumerate(results, 1):
        symbol = coin['symbol']
        price = coin['current_price']
        change_1d = coin['price_change_1d']
        change_7d = coin['price_change_7d']
        score = coin['combined_score']
        
        # Indikator 1: EMA Trend
        trend_signal = coin.get('trend_signal', 'NEUTRAL')
        ema_20 = coin.get('ema_20')
        ema_50 = coin.get('ema_50')
        ema_200 = coin.get('ema_200')
        
        # Indikator 2: RSI
        rsi = coin['rsi']
        rsi_signal = coin['rsi_signal']
        
        # Indikator 3: MACD
        macd_signal = coin.get('macd_signal', 'NEUTRAL')
        macd_histogram = coin.get('macd_histogram')
        
        # Indikator 4: Volume
        volume_ratio = coin['volume_ratio']
        
        # Indikator 5: Support/Resistance
        support = coin.get('support')
        resistance = coin.get('resistance')
        
        # Emoji berdasarkan signal
        trend_emoji = "🟢" if "BULLISH" in trend_signal else "🔴" if "BEARISH" in trend_signal else "🟡"
        macd_emoji = "🟢" if macd_signal == "BULLISH" else "🔴" if macd_signal == "BEARISH" else "🟡"
        change_emoji = "📈" if change_7d > 0 else "📉"
        
        lines.append(f"{i}. {symbol}")
        lines.append(f"   💵 Price: ${price:,.4f}")
        lines.append(f"   {change_emoji} Change: 1d: {change_1d:+.2f}% | 7d: {change_7d:+.2f}%")
        lines.append("")
        lines.append(f"   📊 5 INDIKATOR WAJIB:")
        lines.append(f"   1️⃣  EMA Trend: {trend_emoji} {trend_signal}")
        if ema_20:
            lines.append(f"       EMA 20: ${ema_20:,.4f}" + (f" | EMA 50: ${ema_50:,.4f}" if ema_50 else "") + (f" | EMA 200: ${ema_200:,.4f}" if ema_200 else ""))
        lines.append(f"   2️⃣  RSI: {rsi:.2f} ({rsi_signal})")
        lines.append(f"   3️⃣  MACD: {macd_emoji} {macd_signal}" + (f" (Hist: {macd_histogram:.4f})" if macd_histogram is not None else ""))
        lines.append(f"   4️⃣  Volume Ratio: {volume_ratio:.2f}x")
        if support and resistance:
            lines.append(f"   5️⃣  Support: ${support:,.4f} | Resistance: ${resistance:,.4f}")
        lines.append("")
        
        # Tampilkan direction dan scores jika ada
        if 'best_direction' in coin:
            direction_emoji = "🟢" if coin['best_direction'] == "LONG" else "🔴" if coin['best_direction'] == "SHORT" else "🟡"
            lines.append(f"   {direction_emoji} Direction: {coin['best_direction']}")
            if 'long_score' in coin and 'short_score' in coin:
                lines.append(f"      Long Score: {coin['long_score']:.4f} | Short Score: {coin['short_score']:.4f}")
        
        lines.append(f"   ⭐ Combined Score: {score:.4f}")
        lines.append("")
    
    return "\n".join(lines)


if __name__ == "__main__":
    # Test screening
    print("Testing Coin Screening...")
    print("=" * 70)
    
    results = screen_coins(
        coins=["BTC-USD", "ETH-USD", "XRP-USD", "DOGE-USD", "SOL-USD"],
        days=30,
        top_n=5
    )
    
    print(format_screening_results(results))

