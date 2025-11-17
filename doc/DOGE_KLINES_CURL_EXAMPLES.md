# Binance Futures API - Klines/Candlestick Data untuk DOGE

## Endpoint
```
GET /fapi/v1/klines
```

## Base URL
```
https://fapi.binance.com
```

## Parameter
- `symbol` (required): Trading pair, e.g., `DOGEUSDT`
- `interval` (required): Kline interval
  - Minutes: `1m`, `3m`, `5m`, `15m`, `30m`
  - Hours: `1h`, `2h`, `4h`, `6h`, `8h`, `12h`
  - Days: `1d`, `3d`
  - Weeks: `1w`
  - Months: `1M`
- `startTime` (optional): Start time in milliseconds (Unix timestamp)
- `endTime` (optional): End time in milliseconds (Unix timestamp)
- `limit` (optional): Number of klines to return (default: 500, max: 1500)

---

## Contoh Curl Commands

### 1. Get Recent 100 Klines (1 Hour Interval)
```bash
curl -X GET "https://fapi.binance.com/fapi/v1/klines?symbol=DOGEUSDT&interval=1h&limit=100"
```

### 2. Get Recent 500 Klines (4 Hour Interval)
```bash
curl -X GET "https://fapi.binance.com/fapi/v1/klines?symbol=DOGEUSDT&interval=4h&limit=500"
```

### 3. Get Daily Klines (30 Days)
```bash
curl -X GET "https://fapi.binance.com/fapi/v1/klines?symbol=DOGEUSDT&interval=1d&limit=30"
```

### 4. Get Klines dengan Time Range (Last 7 Days, 4h Interval)
```bash
# Calculate timestamps (Unix timestamp in milliseconds)
# Start: 7 days ago
# End: now

curl -X GET "https://fapi.binance.com/fapi/v1/klines?symbol=DOGEUSDT&interval=4h&startTime=1700000000000&endTime=1700604800000&limit=500"
```

**Atau menggunakan bash untuk menghitung timestamp otomatis:**
```bash
END_TIME=$(date +%s)000
START_TIME=$((END_TIME - 7*24*60*60*1000))
curl -X GET "https://fapi.binance.com/fapi/v1/klines?symbol=DOGEUSDT&interval=4h&startTime=${START_TIME}&endTime=${END_TIME}&limit=500"
```

### 5. Get 15-Minute Klines (Last 24 Hours)
```bash
END_TIME=$(date +%s)000
START_TIME=$((END_TIME - 24*60*60*1000))
curl -X GET "https://fapi.binance.com/fapi/v1/klines?symbol=DOGEUSDT&interval=15m&startTime=${START_TIME}&endTime=${END_TIME}&limit=1500"
```

### 6. Get 5-Minute Klines (Last 6 Hours)
```bash
END_TIME=$(date +%s)000
START_TIME=$((END_TIME - 6*60*60*1000))
curl -X GET "https://fapi.binance.com/fapi/v1/klines?symbol=DOGEUSDT&interval=5m&startTime=${START_TIME}&endTime=${END_TIME}&limit=1500"
```

### 7. Get Weekly Klines (Last 52 Weeks)
```bash
curl -X GET "https://fapi.binance.com/fapi/v1/klines?symbol=DOGEUSDT&interval=1w&limit=52"
```

### 8. Get Monthly Klines (Last 12 Months)
```bash
curl -X GET "https://fapi.binance.com/fapi/v1/klines?symbol=DOGEUSDT&interval=1M&limit=12"
```

---

## Response Format

Response adalah array of arrays, setiap array berisi:
```json
[
  [
    1499040000000,      // Open time
    "0.01634790",       // Open
    "0.80000000",       // High
    "0.01575800",       // Low
    "0.01577100",       // Close
    "148976.11427815",  // Volume
    1499644799999,      // Close time
    "2434.19055334",    // Quote asset volume
    308,                // Number of trades
    "1756.87402397",    // Taker buy base asset volume
    "28.46694368",      // Taker buy quote asset volume
    "17928899.62484339" // Ignore
  ]
]
```

### Field Description
- **Open time**: Timestamp in milliseconds
- **Open**: Opening price
- **High**: Highest price
- **Low**: Lowest price
- **Close**: Closing price
- **Volume**: Trading volume
- **Close time**: Closing timestamp in milliseconds
- **Quote asset volume**: Quote asset trading volume
- **Number of trades**: Number of trades
- **Taker buy base asset volume**: Taker buy base asset volume
- **Taker buy quote asset volume**: Taker buy quote asset volume
- **Ignore**: Ignore field

---

## Pretty Print dengan jq

Jika `jq` tersedia, gunakan untuk format output:

```bash
curl -s -X GET "https://fapi.binance.com/fapi/v1/klines?symbol=DOGEUSDT&interval=1h&limit=10" | jq '.[0:3]'
```

---

## Contoh dengan Python

```python
import requests
from datetime import datetime, timedelta

BASE_URL = "https://fapi.binance.com"
SYMBOL = "DOGEUSDT"

# Get recent 100 klines (1 hour interval)
url = f"{BASE_URL}/fapi/v1/klines"
params = {
    'symbol': SYMBOL,
    'interval': '1h',
    'limit': 100
}

response = requests.get(url, params=params)
klines = response.json()

print(f"Received {len(klines)} klines")
for kline in klines[:3]:  # Print first 3
    open_time = datetime.fromtimestamp(kline[0] / 1000)
    print(f"{open_time}: Open={kline[1]}, High={kline[2]}, Low={kline[3]}, Close={kline[4]}, Volume={kline[5]}")
```

---

## Rate Limits

- **Request Weight**: Berdasarkan parameter `limit`
  - `[1,100)`: weight 1
  - `[100, 500)`: weight 2
  - `[500, 1000]`: weight 5
  - `> 1000`: weight 10

- **Rate Limit**: 2400 requests per minute (untuk IP)

---

## Error Handling

Jika terjadi error, response akan berisi:
```json
{
  "code": -1121,
  "msg": "Invalid symbol."
}
```

**Common Errors:**
- `-1121`: Invalid symbol
- `-1100`: Illegal characters found in parameter
- `-1022`: Signature verification failed (untuk signed endpoints)

---

## Testing

Test dengan curl:
```bash
# Test connectivity
curl -X GET "https://fapi.binance.com/fapi/v1/klines?symbol=DOGEUSDT&interval=1h&limit=1"
```

Jika berhasil, akan mengembalikan array dengan 1 kline data.

