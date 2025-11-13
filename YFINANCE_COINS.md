# yfinance - Daftar Coin yang Didukung

## Format Symbol
Format symbol yfinance: **COIN-USD**

Contoh: `BTC-USD`, `ETH-USD`, `XRP-USD`, `DOGE-USD`

## Daftar Coin Populer yang Didukung

### Major Cryptocurrencies
- **BTC-USD** - Bitcoin
- **ETH-USD** - Ethereum
- **BNB-USD** - Binance Coin
- **XRP-USD** - Ripple
- **ADA-USD** - Cardano
- **SOL-USD** - Solana
- **DOGE-USD** - Dogecoin
- **DOT-USD** - Polkadot
- **LINK-USD** - Chainlink
- **MATIC-USD** - Polygon (Polygon) - *Note: mungkin perlu dicek*

### Altcoins Lainnya
- **LTC-USD** - Litecoin
- **AVAX-USD** - Avalanche
- **UNI-USD** - Uniswap
- **ATOM-USD** - Cosmos
- **ETC-USD** - Ethereum Classic
- **XLM-USD** - Stellar
- **ALGO-USD** - Algorand
- **VET-USD** - VeChain
- **FIL-USD** - Filecoin
- **TRX-USD** - Tron
- **EOS-USD** - EOS
- **AAVE-USD** - Aave
- **MKR-USD** - Maker
- **COMP-USD** - Compound
- **SUSHI-USD** - SushiSwap
- **YFI-USD** - Yearn Finance

### DeFi Tokens
- **UNI-USD** - Uniswap
- **AAVE-USD** - Aave
- **MKR-USD** - Maker
- **COMP-USD** - Compound
- **SUSHI-USD** - SushiSwap

### Layer 2 & Scaling
- **MATIC-USD** - Polygon
- **ARB-USD** - Arbitrum
- **OP-USD** - Optimism

## Cara Menggunakan di config.py

### Untuk yfinance:
```python
DATA_SOURCE = "yfinance"
SYMBOL = "ETH-USD"  # Ganti dengan coin yang diinginkan
```

### Contoh untuk berbagai coin:
```python
# Ethereum
SYMBOL = "ETH-USD"

# Ripple
SYMBOL = "XRP-USD"

# Dogecoin
SYMBOL = "DOGE-USD"

# Solana
SYMBOL = "SOL-USD"

# Cardano
SYMBOL = "ADA-USD"
```

## Cara Mencari Symbol Coin Lainnya

### 1. Yahoo Finance Website
- Kunjungi: https://finance.yahoo.com/crypto/
- Cari coin yang diinginkan
- Format symbol biasanya: `COIN-USD`

### 2. Test dengan yfinance
```python
import yfinance as yf

# Test apakah coin tersedia
symbol = "COIN-USD"  # Ganti dengan coin yang diinginkan
ticker = yf.Ticker(symbol)
data = ticker.history(period="5d")

if not data.empty:
    print(f"✅ {symbol} tersedia")
    print(f"Harga: ${data['Close'].iloc[-1]:,.2f}")
else:
    print(f"❌ {symbol} tidak tersedia atau data kosong")
```

## Catatan Penting

1. **Format Symbol**: Selalu gunakan format `COIN-USD` (huruf besar)
2. **Ketersediaan Data**: Tidak semua coin tersedia di Yahoo Finance
3. **Data Real-time**: yfinance mengambil data dari Yahoo Finance (bukan real-time exchange)
4. **Limit Interval**: 
   - 1m: maksimal 7 hari
   - 5m, 15m, 30m: maksimal 60 hari
   - 1h: maksimal 730 hari
   - 1d: tidak ada limit

## Contoh Script untuk Test Multiple Coins

```python
import yfinance as yf

coins = [
    "BTC-USD", "ETH-USD", "XRP-USD", "DOGE-USD",
    "BNB-USD", "ADA-USD", "SOL-USD", "DOT-USD"
]

for coin in coins:
    try:
        ticker = yf.Ticker(coin)
        data = ticker.history(period="5d", interval="1d")
        if not data.empty:
            price = data['Close'].iloc[-1]
            print(f"✅ {coin:15s} - ${price:,.2f}")
        else:
            print(f"⚠️  {coin:15s} - Data kosong")
    except Exception as e:
        print(f"❌ {coin:15s} - Error: {e}")
```

## Referensi

- **yfinance Documentation**: https://ranaroussi.github.io/yfinance/
- **Yahoo Finance Crypto**: https://finance.yahoo.com/crypto/
- **GitHub yfinance**: https://github.com/ranaroussi/yfinance

