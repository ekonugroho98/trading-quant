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
    from config import DATA_SOURCE, BINANCE_API_KEY, BINANCE_API_SECRET
except ImportError:
    DATA_SOURCE = "yfinance"
    BINANCE_API_KEY = None
    BINANCE_API_SECRET = None


# Daftar 150 coin populer untuk screening (terutama dari Binance)
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
                       api_secret: Optional[str] = None) -> pd.DataFrame:
    """
    Ambil data snapshot untuk multiple coins sekaligus
    
    Args:
        coins: List of coin symbols (format: BTC-USD)
        days: Jumlah hari data yang diambil (default: 90)
        data_source: "yfinance" atau "binance" (default: dari config.py)
        api_key: Binance API key (optional, default: dari config.py)
        api_secret: Binance API secret (optional, default: dari config.py)
    
    Returns:
        DataFrame dengan MultiIndex (Ticker, Price) untuk kompatibilitas
    """
    # Gunakan data_source dari parameter atau config
    source = data_source or DATA_SOURCE
    
    if source == "binance":
        return get_coins_snapshot_binance(coins, days, api_key, api_secret)
    else:
        return get_coins_snapshot_yfinance(coins, days)


def get_coins_snapshot_yfinance(coins: List[str], days: int = 90) -> pd.DataFrame:
    """
    Ambil data snapshot dari yfinance
    """
    try:
        print(f"📊 Mengambil data snapshot dari yfinance untuk {len(coins)} coins...")
        # group_by='ticker' akan membuat struktur (Ticker, Price) bukan (Price, Ticker)
        data = yf.download(
            coins,
            period=f"{days}d",
            interval="1d",
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
                               api_secret: Optional[str] = None) -> pd.DataFrame:
    """
    Ambil data snapshot dari Binance API untuk multiple coins
    Menggunakan binance_data.download_multiple_symbols untuk batch processing
    """
    try:
        from binance_data import download_multiple_symbols
        
        # Gunakan API key dari parameter atau config
        api_key = api_key or BINANCE_API_KEY
        api_secret = api_secret or BINANCE_API_SECRET
        
        print(f"📊 Mengambil data snapshot dari Binance API untuk {len(coins)} coins...")
        print(f"   Periode: {days} hari")
        
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
            interval="1d",
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
        return get_coins_snapshot_yfinance(coins, days)
    except Exception as e:
        print(f"❌ Error mengambil data snapshot dari Binance: {e}")
        print("   Fallback ke yfinance...")
        return get_coins_snapshot_yfinance(coins, days)


def calculate_quick_metrics(data: pd.DataFrame, symbol: str) -> Optional[Dict]:
    """
    Hitung quick metrics untuk satu coin
    
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
        
        # Volume metrics
        if volume_data is not None and len(volume_data) >= 2:
            current_volume = float(volume_data.iloc[-1])
            avg_volume = float(volume_data.tail(7).mean()) if len(volume_data) >= 7 else float(volume_data.mean())
            volume_ratio = (current_volume / avg_volume) if avg_volume > 0 else 1.0
        else:
            volume_ratio = 1.0
            current_volume = 0
        
        # Simple Moving Averages
        if len(close_data) >= 10:
            ma_short = float(close_data.tail(5).mean())  # 5-day MA
            ma_long = float(close_data.tail(10).mean())  # 10-day MA
            ma_signal = "BUY" if ma_short > ma_long else "SELL" if ma_short < ma_long else "NEUTRAL"
        else:
            ma_short = current_price
            ma_long = current_price
            ma_signal = "NEUTRAL"
        
        # RSI (simplified, adaptive period based on available data)
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
        
        # Momentum score (simple)
        if len(close_data) >= 5:
            momentum = ((close_data.iloc[-1] - close_data.iloc[-5]) / close_data.iloc[-5] * 100) if close_data.iloc[-5] > 0 else 0
        else:
            momentum = price_change_1d
        
        # Volatility (standard deviation of returns)
        if len(close_data) >= 7:
            returns = close_data.pct_change().dropna()
            volatility = float(returns.std() * 100) if len(returns) > 0 else 0
        else:
            volatility = 0
        
        # Combined score (untuk ranking) - Improved formula
        # Normalize semua metrics ke range yang sama untuk akurasi lebih baik
        
        # 1. Price change score (normalize: -100% to +100% -> -1 to +1)
        price_score = np.clip(price_change_7d / 100, -1, 1)
        
        # 2. Volume score (normalize: 0 to 3x -> -0.5 to +1)
        # Volume ratio 1.0 = score 0, >1.0 = positive, <1.0 = negative
        volume_score = np.clip((volume_ratio - 1) / 2, -0.5, 1)
        
        # 3. Momentum score (normalize: -50% to +50% -> -1 to +1)
        momentum_score = np.clip(momentum / 50, -1, 1)
        
        # 4. RSI score (normalize: 0-100 -> -1 to +1, dengan RSI 50 = 0)
        rsi_score = (rsi - 50) / 50  # -1 to +1
        
        # 5. MA signal score (BUY=1, SELL=-1, NEUTRAL=0)
        ma_score = 1 if ma_signal == "BUY" else (-1 if ma_signal == "SELL" else 0)
        
        # 6. Volatility score (inverse: volatility rendah = score tinggi)
        # Normalize: 0-10% -> 1 to 0 (volatility rendah = bagus untuk trading)
        volatility_score = max(0, 1 - (volatility / 10)) if volatility > 0 else 0.5
        
        # Combined score dengan weights yang lebih seimbang
        # Score untuk LONG (bullish)
        long_score = (
            price_score * 0.25 +           # 25% weight on price change (positive = good)
            volume_score * 0.20 +          # 20% weight on volume (higher = good)
            momentum_score * 0.20 +        # 20% weight on momentum (positive = good)
            rsi_score * 0.15 +             # 15% weight on RSI (50-70 = good for long)
            ma_score * 0.10 +              # 10% weight on MA signal (BUY = good)
            volatility_score * 0.10        # 10% weight on volatility (lower = good)
        )
        
        # Score untuk SHORT (bearish) - inverse logic
        # Untuk short: price drop = good, negative momentum = good, RSI > 70 = good, MA SELL = good
        short_score = (
            (-price_score) * 0.25 +        # 25% weight on price change (negative = good for short)
            volume_score * 0.20 +          # 20% weight on volume (higher = good, same)
            (-momentum_score) * 0.20 +     # 20% weight on momentum (negative = good for short)
            (-rsi_score) * 0.15 +          # 15% weight on RSI (70-100 = good for short, inverse)
            (-ma_score) * 0.10 +           # 10% weight on MA signal (SELL = good for short)
            volatility_score * 0.10        # 10% weight on volatility (lower = good, same)
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
            'volume_ratio': volume_ratio,
            'current_volume': current_volume,
            'ma_short': ma_short,
            'ma_long': ma_long,
            'ma_signal': ma_signal,
            'rsi': rsi,
            'rsi_signal': "OVERSOLD" if rsi < 30 else ("OVERBOUGHT" if rsi > 70 else "NEUTRAL"),
            'momentum': momentum,
            'volatility': volatility,
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
        coins = DEFAULT_COINS
    
    print(f"\n🔍 Screening {len(coins)} coins...")
    print(f"📅 Periode: {days} hari")
    print(f"📊 Filter: Volume ratio >= {min_volume_ratio}, Price change: {min_price_change}% to {max_price_change}%")
    print(f"📈 Trade Direction: {trade_direction.upper()}")
    if rsi_range:
        print(f"📈 RSI range: {rsi_range[0]} - {rsi_range[1]}")
    print()
    
    # Ambil data snapshot untuk semua coins
    data = get_coins_snapshot(coins, days, data_source, api_key, api_secret)
    
    if data.empty:
        print("❌ Tidak ada data untuk screening")
        return []
    
    # Hitung metrics untuk setiap coin
    results = []
    for symbol in coins:
        metrics = calculate_quick_metrics(data, symbol)
        if metrics:
            # Apply filters
            if metrics['volume_ratio'] < min_volume_ratio:
                continue
            if metrics['price_change_7d'] < min_price_change or metrics['price_change_7d'] > max_price_change:
                continue
            if rsi_range:
                if metrics['rsi'] < rsi_range[0] or metrics['rsi'] > rsi_range[1]:
                    continue
            
            # Filter berdasarkan trade_direction
            if trade_direction == "long":
                # Hanya ambil coin dengan long_score lebih tinggi
                if metrics['long_score'] <= metrics['short_score']:
                    continue
                # Update combined_score untuk long only
                metrics['combined_score'] = metrics['long_score']
            elif trade_direction == "short":
                # Hanya ambil coin dengan short_score lebih tinggi
                if metrics['short_score'] <= metrics['long_score']:
                    continue
                # Update combined_score untuk short only
                metrics['combined_score'] = metrics['short_score']
            # else: "both" - tidak ada filter, gunakan best_score yang sudah dihitung
            
            results.append(metrics)
    
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
        volume_ratio = coin['volume_ratio']
        rsi = coin['rsi']
        rsi_signal = coin['rsi_signal']
        ma_signal = coin['ma_signal']
        score = coin['combined_score']
        
        # Emoji berdasarkan signal
        signal_emoji = "🟢" if ma_signal == "BUY" else "🔴" if ma_signal == "SELL" else "🟡"
        change_emoji = "📈" if change_7d > 0 else "📉"
        
        lines.append(f"{i}. {symbol}")
        lines.append(f"   💵 Price: ${price:,.4f}")
        lines.append(f"   {change_emoji} Change: 1d: {change_1d:+.2f}% | 7d: {change_7d:+.2f}%")
        lines.append(f"   📊 Volume Ratio: {volume_ratio:.2f}x")
        lines.append(f"   📈 RSI: {rsi:.2f} ({rsi_signal})")
        lines.append(f"   {signal_emoji} MA Signal: {ma_signal}")
        lines.append(f"   ⭐ Score: {score:.4f}")
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

