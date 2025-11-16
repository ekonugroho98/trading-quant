# Binance API Integration Setup

## Overview
Integrasi dengan Binance API untuk mendapatkan data real-time dan melakukan trading operations.

## Prerequisites

### 1. Install Library
```bash
pip install python-binance
```

### 2. Dapatkan API Key dan Secret
1. Login ke Binance: https://www.binance.com
2. Buka Settings → API Management: https://www.binance.com/en/my/settings/api-management
3. Create API Key baru
4. **PENTING**: Untuk testing, gunakan **Testnet** terlebih dahulu:
   - Testnet: https://testnet.binance.vision
   - Testnet API Key: https://testnet.binance.vision/api/v3

### 3. Konfigurasi

Edit `config.py`:
```python
ENABLE_BINANCE_API = True
BINANCE_API_KEY = "your_api_key_here"
BINANCE_API_SECRET = "your_api_secret_here"
```

**⚠️ KEAMANAN**: 
- Jangan commit API key dan secret ke repository!
- Gunakan environment variables atau file `.env` untuk production
- Untuk testing, gunakan Binance Testnet

## Testing Koneksi

### Test Public Endpoints (Tidak Perlu API Key)
```bash
python3 test_binance_connection.py
```

Script ini akan test:
1. ✅ Get Server Time
2. ✅ Get Exchange Info
3. ✅ Get BTC Price

### Test Private Endpoints (Perlu API Key)
Setelah menambahkan API key di `config.py`, script akan otomatis test:
1. ✅ Get Account Info
2. ✅ Get Balances
3. ✅ Get Trading Permissions

## Troubleshooting

### SSL Certificate Error
Jika mendapat error SSL certificate:
- Pastikan koneksi internet stabil
- Cek firewall/proxy settings
- Untuk testing, bisa disable SSL verification (tidak disarankan untuk production)

### Connection Timeout
Jika mendapat connection timeout:
- Cek koneksi internet
- Cek firewall/proxy settings
- Coba lagi beberapa saat kemudian (mungkin Binance API sedang maintenance)

### API Key Invalid
- Pastikan API key dan secret benar
- Pastikan API key masih aktif (tidak expired)
- Cek IP whitelist di Binance API settings (jika ada)

## Next Steps

Setelah koneksi berhasil, fitur yang akan ditambahkan:
1. ✅ Get real-time price data
2. ✅ Get historical klines (OHLCV)
3. ✅ Place orders (market, limit, stop-loss)
4. ✅ Get order status
5. ✅ Get account balances
6. ✅ WebSocket streaming untuk real-time updates

## References

- Binance API Documentation: https://binance-docs.github.io/apidocs/spot/en/
- Python-Binance Library: https://python-binance.readthedocs.io/
- Binance Testnet: https://testnet.binance.vision/

