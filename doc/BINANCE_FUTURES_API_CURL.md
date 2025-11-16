# Binance USDⓈ-M Futures API - cURL Examples

## Base URLs

- **Production:** `https://fapi.binance.com`
- **Testnet:** `https://testnet.binancefuture.com`

---

## 1. Get Exchange Info (List All Coins)

Mendapatkan informasi exchange dan daftar semua trading pairs yang tersedia di Futures.

### Endpoint
```
GET /fapi/v1/exchangeInfo
```

### cURL Command

```bash
# Production
curl -X GET "https://fapi.binance.com/fapi/v1/exchangeInfo"

# Testnet
curl -X GET "https://testnet.binancefuture.com/fapi/v1/exchangeInfo"
```

### Response Example
```json
{
  "exchangeFilters": [],
  "rateLimits": [...],
  "serverTime": 1700000000000,
  "symbols": [
    {
      "symbol": "BTCUSDT",
      "status": "TRADING",
      "baseAsset": "BTC",
      "quoteAsset": "USDT",
      "pricePrecision": 2,
      "quantityPrecision": 3,
      ...
    },
    ...
  ]
}
```

### Filter by Quote Asset (USDT only)

```bash
# Get only USDT pairs
curl -X GET "https://fapi.binance.com/fapi/v1/exchangeInfo" | jq '.symbols[] | select(.quoteAsset == "USDT" and .status == "TRADING") | .symbol'
```

---

## 2. Get 24h Ticker Statistics (All Coins)

Mendapatkan statistik 24 jam untuk semua coins atau coin tertentu.

### Endpoint
```
GET /fapi/v1/ticker/24hr
```

### cURL Command

```bash
# All coins (24h statistics)
curl -X GET "https://fapi.binance.com/fapi/v1/ticker/24hr"

# Specific coin (BTCUSDT)
curl -X GET "https://fapi.binance.com/fapi/v1/ticker/24hr?symbol=BTCUSDT"
```

### Response Example
```json
[
  {
    "symbol": "BTCUSDT",
    "priceChange": "1000.00",
    "priceChangePercent": "2.50",
    "weightedAvgPrice": "40000.00",
    "prevClosePrice": "39000.00",
    "lastPrice": "40000.00",
    "lastQty": "0.001",
    "bidPrice": "39999.00",
    "askPrice": "40001.00",
    "openPrice": "39000.00",
    "highPrice": "41000.00",
    "lowPrice": "38500.00",
    "volume": "1000.50",
    "quoteVolume": "40000000.00",
    "openTime": 1700000000000,
    "closeTime": 1700086400000,
    "firstId": 1000000,
    "lastId": 1001000,
    "count": 1000
  },
  ...
]
```

### Get Top Coins by Volume

```bash
# Sort by quoteVolume (24h volume in USDT) descending
curl -X GET "https://fapi.binance.com/fapi/v1/ticker/24hr" | \
  jq 'sort_by(-.quoteVolume) | .[0:10] | .[] | {symbol: .symbol, volume: .quoteVolume, price: .lastPrice}'
```

---

## 3. Get Current Price

Mendapatkan harga saat ini untuk coin tertentu atau semua coins.

### Endpoint
```
GET /fapi/v1/ticker/price
```

### cURL Command

```bash
# All coins
curl -X GET "https://fapi.binance.com/fapi/v1/ticker/price"

# Specific coin (BTCUSDT)
curl -X GET "https://fapi.binance.com/fapi/v1/ticker/price?symbol=BTCUSDT"
```

### Response Example

**All coins:**
```json
[
  {"symbol": "BTCUSDT", "price": "40000.00"},
  {"symbol": "ETHUSDT", "price": "2500.00"},
  ...
]
```

**Specific coin:**
```json
{"symbol": "BTCUSDT", "price": "40000.00"}
```

---

## 4. Get Klines (Candlestick Data)

Mendapatkan data candlestick (OHLC) untuk coin tertentu.

### Endpoint
```
GET /fapi/v1/klines
```

### Parameters
- `symbol` (required): Trading pair, e.g., `BTCUSDT`
- `interval` (required): Kline interval (`1m`, `3m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`, `6h`, `8h`, `12h`, `1d`, `3d`, `1w`, `1M`)
- `limit` (optional): Number of klines (default: 500, max: 1500)
- `startTime` (optional): Start time in milliseconds
- `endTime` (optional): End time in milliseconds

### cURL Command

```bash
# Get last 100 klines (1 hour interval)
curl -X GET "https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=1h&limit=100"

# Get klines with time range
curl -X GET "https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=4h&startTime=1700000000000&endTime=1700086400000&limit=500"
```

### Response Example
```json
[
  [
    1700000000000,      // Open time
    "40000.00",         // Open
    "41000.00",         // High
    "39000.00",         // Low
    "40500.00",         // Close
    "1000.50",          // Volume
    1700036000000,      // Close time
    "40000000.00",      // Quote volume
    1000,               // Trades
    "500.25",           // Taker buy base
    "20000000.00",      // Taker buy quote
    "0"                 // Ignore
  ],
  ...
]
```

---

## 5. Get Orderbook (Depth)

Mendapatkan orderbook (depth) untuk coin tertentu.

### Endpoint
```
GET /fapi/v1/depth
```

### Parameters
- `symbol` (required): Trading pair
- `limit` (optional): Orderbook depth (5, 10, 20, 50, 100, 500, 1000, default: 100)

### cURL Command

```bash
# Get orderbook for BTCUSDT (default limit: 100)
curl -X GET "https://fapi.binance.com/fapi/v1/depth?symbol=BTCUSDT"

# Get orderbook with limit 50
curl -X GET "https://fapi.binance.com/fapi/v1/depth?symbol=BTCUSDT&limit=50"
```

### Response Example
```json
{
  "lastUpdateId": 1000000,
  "bids": [
    ["39999.00", "0.5"],
    ["39998.00", "1.0"],
    ...
  ],
  "asks": [
    ["40001.00", "0.3"],
    ["40002.00", "0.8"],
    ...
  ]
}
```

---

## 6. Get Position Risk (Signed Endpoint - Requires API Key)

Mendapatkan informasi risiko posisi. **Membutuhkan autentikasi.**

### Endpoint
```
GET /fapi/v2/positionRisk
```

### cURL Command (with API Key)

```bash
# Get all positions
curl -X GET "https://fapi.binance.com/fapi/v2/positionRisk" \
  -H "X-MBX-APIKEY: YOUR_API_KEY"

# Get specific symbol position
curl -X GET "https://fapi.binance.com/fapi/v2/positionRisk?symbol=BTCUSDT" \
  -H "X-MBX-APIKEY: YOUR_API_KEY"
```

**Note:** Endpoint ini memerlukan HMAC signature. Untuk penggunaan production, gunakan library atau implementasi signature yang proper.

---

## 7. Get Top Coins by Volume (Combined Query)

Script untuk mendapatkan top coins berdasarkan volume 24h:

```bash
#!/bin/bash

# Get exchange info and filter USDT pairs
echo "📊 Getting USDT trading pairs..."
curl -s "https://fapi.binance.com/fapi/v1/exchangeInfo" | \
  jq -r '.symbols[] | select(.quoteAsset == "USDT" and .status == "TRADING") | .symbol' > /tmp/futures_symbols.txt

# Get 24h ticker and sort by volume
echo "📈 Getting 24h ticker statistics..."
curl -s "https://fapi.binance.com/fapi/v1/ticker/24hr" | \
  jq -r '.[] | select(.symbol | endswith("USDT")) | {symbol: .symbol, volume: .quoteVolume, price: .lastPrice} | @json' | \
  jq -s 'sort_by(-.volume) | .[0:20] | .[] | "\(.symbol) - Volume: \(.volume) - Price: \(.price)"'
```

---

## 8. Rate Limits

Binance Futures API memiliki rate limits:
- **Weight limits:** Berdasarkan endpoint
- **Order rate limits:** Berdasarkan IP dan API key
- **Request rate limits:** 2400 requests per minute per IP

### Check Rate Limits

```bash
curl -X GET "https://fapi.binance.com/fapi/v1/exchangeInfo" | jq '.rateLimits'
```

---

## 9. Error Handling

### Common Error Codes

- `400` - Bad Request (invalid parameters)
- `401` - Unauthorized (invalid API key)
- `429` - Too Many Requests (rate limit exceeded)
- `500` - Internal Server Error

### Example Error Response

```json
{
  "code": -1121,
  "msg": "Invalid symbol."
}
```

---

## 10. Complete Example: Get Top 20 Coins

```bash
#!/bin/bash

BASE_URL="https://fapi.binance.com"
LIMIT=20

echo "🔍 Getting top $LIMIT coins by 24h volume..."

# Get 24h ticker statistics
curl -s "$BASE_URL/fapi/v1/ticker/24hr" | \
  jq -r --argjson limit $LIMIT '
    [.[] | select(.symbol | endswith("USDT"))] |
    sort_by(-.quoteVolume) |
    .[0:$limit] |
    .[] |
    "\(.symbol) | Volume: \(.quoteVolume) | Price: \(.lastPrice) | Change: \(.priceChangePercent)%"
  '
```

---

## Notes

1. **No Authentication Required:** Endpoints di atas (kecuali positionRisk) tidak memerlukan API key
2. **Rate Limits:** Perhatikan rate limits untuk menghindari IP ban
3. **Testnet:** Gunakan testnet URL untuk testing tanpa risiko
4. **Symbol Format:** Gunakan format `BTCUSDT`, bukan `BTC-USDT` atau `BTC/USDT`
5. **Time Format:** Gunakan Unix timestamp dalam milliseconds untuk `startTime` dan `endTime`

---

## References

- [Binance Futures API Documentation](https://developers.binance.com/docs/derivatives/usds-margined-futures)
- [Rate Limits](https://developers.binance.com/docs/derivatives/usds-margined-futures/rate-limits)

