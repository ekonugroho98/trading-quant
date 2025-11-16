# Solusi untuk ISP Blocking Binance (MyRepublic)

## 🔍 Masalah yang Ditemukan

Dari test koneksi, terdeteksi bahwa **ISP MyRepublic memblokir akses ke Binance**:
- `api.binance.com` di-resolve ke `block.myrepublic.co.id`
- IP: `158.140.186.3` (bukan IP Binance yang sebenarnya)
- Error: 404 Not Found dari nginx (ISP blocking page)

## ✅ Solusi: Install VPN

### Option 1: Cloudflare WARP (Gratis, Recommended)

**Install:**
```bash
# Via Homebrew
brew install --cask cloudflare-warp

# Atau download manual dari:
# https://1.1.1.1/
```

**Setup:**
1. Buka aplikasi Cloudflare WARP
2. Klik "Connect"
3. Tunggu sampai connected (ikon hijau)
4. Test: `python3 test_binance_connection.py`

**Keuntungan:**
- ✅ Gratis
- ✅ Mudah digunakan
- ✅ Tidak perlu konfigurasi
- ✅ Cepat dan stabil

### Option 2: VPN Provider Lain

Jika sudah punya VPN provider (ExpressVPN, NordVPN, dll):
1. Install VPN client
2. Connect ke server (pilih server di luar Indonesia)
3. Test koneksi

### Option 3: Setup Proxy Manual

Jika punya proxy server:

```bash
# Set proxy di terminal
export HTTP_PROXY="http://proxy-server:port"
export HTTPS_PROXY="http://proxy-server:port"

# Atau SOCKS5
export HTTP_PROXY="socks5://proxy-server:port"
export HTTPS_PROXY="socks5://proxy-server:port"
```

## 🧪 Test Setelah Install VPN

### 1. Test DNS Resolution
```bash
nslookup api.binance.com
# Harusnya resolve ke IP Binance yang benar, bukan block.myrepublic.co.id
```

### 2. Test Koneksi
```bash
python3 test_binance_connection.py
```

### 3. Test Get Data
```bash
python3 get_historical_data.py
```

## 📝 Quick Install Script

Jalankan script install VPN:
```bash
chmod +x install_vpn.sh
./install_vpn.sh
```

Atau install manual:
```bash
# Cloudflare WARP (Recommended)
brew install --cask cloudflare-warp
```

## ⚠️ Catatan Penting

1. **VPN Wajib**: Karena ISP memblokir, VPN/proxy **WAJIB** untuk akses Binance
2. **SSL Fix**: File `binance_data.py` sudah diupdate untuk handle SSL issues
3. **Proxy Support**: Sudah support proxy dari environment variables
4. **Testnet**: Untuk testing, bisa gunakan Binance Testnet (mungkin tidak di-block)

## 🔧 Alternatif: Gunakan Binance Testnet

Jika VPN tidak tersedia, coba Binance Testnet:

```python
# Di binance_data.py, ganti base_url
client = Client(
    api_key, 
    api_secret,
    testnet=True  # Gunakan testnet
)
```

Testnet URL: `https://testnet.binance.vision`

## 📋 Checklist

- [ ] Install VPN client (Cloudflare WARP recommended)
- [ ] Connect VPN
- [ ] Test DNS: `nslookup api.binance.com`
- [ ] Test koneksi: `python3 test_binance_connection.py`
- [ ] Test get data: `python3 get_historical_data.py`

## 🚀 Langkah Cepat

```bash
# 1. Install Cloudflare WARP
brew install --cask cloudflare-warp

# 2. Buka aplikasi dan connect

# 3. Test
python3 test_binance_connection.py
```

