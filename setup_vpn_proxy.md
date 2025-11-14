# Setup VPN/Proxy untuk Akses Binance API

## Masalah yang Ditemukan

Dari test koneksi, ditemukan error:
- **SSL Certificate Error**: `SSL: no alternative certificate subject name matches target host name 'api.binance.com'`
- **Connection Reset**: Connection reset by peer

Ini biasanya disebabkan oleh:
1. VPN/Proxy yang mengintercept SSL connection
2. Firewall/Security software
3. DNS issue
4. Network configuration

## Solusi 1: Install VPN Client (Jika Belum Ada)

### Option A: Install via Homebrew (Recommended)

```bash
# Install OpenVPN
brew install openvpn

# Atau install WireGuard
brew install wireguard-tools

# Atau install Tunnelblick (GUI untuk OpenVPN)
brew install --cask tunnelblick
```

### Option B: Install VPN Client Manual

1. **OpenVPN**: https://openvpn.net/community-downloads/
2. **WireGuard**: https://www.wireguard.com/install/
3. **Tunnelblick** (macOS): https://tunnelblick.net/

## Solusi 2: Setup Proxy untuk Binance API

Jika sudah ada VPN/Proxy, konfigurasi di Python:

### Method 1: Environment Variables

```bash
# Set proxy di terminal sebelum run script
export HTTP_PROXY="http://proxy-server:port"
export HTTPS_PROXY="http://proxy-server:port"
export NO_PROXY="localhost,127.0.0.1"

# Atau untuk SOCKS proxy
export HTTP_PROXY="socks5://proxy-server:port"
export HTTPS_PROXY="socks5://proxy-server:port"
```

### Method 2: Update binance_data.py untuk Support Proxy

File `binance_data.py` sudah diupdate untuk handle SSL issues. Jika perlu proxy, tambahkan:

```python
# Di binance_data.py, update requests_params:
requests_params = {
    'timeout': 30,
    'verify': False,  # Untuk SSL issues
    'proxies': {
        'http': 'http://proxy-server:port',
        'https': 'http://proxy-server:port'
    }  # Jika perlu proxy
}
```

## Solusi 3: Fix SSL Certificate Issue

Error SSL certificate sudah di-handle di `binance_data.py` dengan `verify=False`. 

**⚠️ PERINGATAN**: `verify=False` tidak aman untuk production! Hanya untuk testing.

### Untuk Production (Lebih Aman):

1. **Update CA Certificates**:
```bash
# macOS
brew install ca-certificates
# Atau update via system
```

2. **Gunakan Custom CA Bundle**:
```python
requests_params = {
    'timeout': 30,
    'verify': '/path/to/cacert.pem'  # Custom CA bundle
}
```

## Solusi 4: Test dengan VPN Service

### Option A: Cloudflare WARP (Free)

```bash
# Install Cloudflare WARP
brew install --cask cloudflare-warp

# Atau download dari: https://1.1.1.1/
```

### Option B: Setup SOCKS5 Proxy

Jika punya VPN dengan SOCKS5 support:

```bash
# Contoh dengan SSH tunnel
ssh -D 1080 user@vpn-server

# Lalu set proxy di Python
export HTTP_PROXY="socks5://127.0.0.1:1080"
export HTTPS_PROXY="socks5://127.0.0.1:1080"
```

## Solusi 5: Test Koneksi dengan Fix SSL

File `binance_data.py` sudah diupdate untuk disable SSL verification. Test lagi:

```bash
python3 test_binance_connection.py
```

Atau test langsung:

```bash
python3 -c "
from binance_data import get_data_binance
from config import BINANCE_API_KEY, BINANCE_API_SECRET

data = get_data_binance(
    'BTC-USD',
    days_back=7,
    interval='1h',
    api_key=BINANCE_API_KEY,
    api_secret=BINANCE_API_SECRET
)

if data is not None:
    print(f'✅ Success! Got {len(data)} records')
    print(data.head())
else:
    print('❌ Failed to get data')
"
```

## Troubleshooting

### Error: "Connection timeout"
- Cek koneksi internet
- Cek firewall settings
- Coba dengan VPN/proxy

### Error: "SSL certificate error"
- Sudah di-handle dengan `verify=False` di `binance_data.py`
- Untuk production, update CA certificates

### Error: "Rate limit exceeded"
- Gunakan API key untuk rate limit lebih tinggi
- Tambahkan delay antara requests

## Quick Fix (Sudah Diimplementasikan)

File `binance_data.py` sudah diupdate untuk:
- ✅ Disable SSL verification (untuk testing)
- ✅ Handle connection errors
- ✅ Support timeout configuration

**Coba test lagi dengan:**
```bash
python3 test_binance_connection.py
```

atau

```bash
python3 get_historical_data.py
```

## Catatan Keamanan

⚠️ **PENTING**: 
- `verify=False` hanya untuk testing/development
- Untuk production, gunakan valid SSL certificates
- Jangan commit API keys ke repository
- Gunakan environment variables untuk sensitive data

