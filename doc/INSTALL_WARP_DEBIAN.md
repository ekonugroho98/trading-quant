# Install Cloudflare WARP di Debian Linux

## 📋 Overview

Cloudflare WARP adalah VPN gratis dari Cloudflare yang dapat mengatasi masalah **HTTP 451 (restricted location)** dari Binance API.

## 🚀 Install WARP di Debian

### Method 1: Install via Package Manager (Recommended)

```bash
# 1. Update package list
sudo apt update

# 2. Install dependencies
sudo apt install -y curl gnupg lsb-release

# 3. Add Cloudflare GPG key
curl https://pkg.cloudflareclient.com/pubkey.gpg | sudo gpg --yes --dearmor --output /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg

# 4. Add Cloudflare repository
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg] https://pkg.cloudflareclient.com/ $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/cloudflare-client.list

# 5. Update package list lagi
sudo apt update

# 6. Install WARP
sudo apt install -y cloudflare-warp
```

### Method 2: Install via .deb Package (Alternative)

Jika Method 1 tidak berhasil:

```bash
# 1. Download .deb package untuk Debian
wget https://pkg.cloudflareclient.com/pool/jammy/main/c/cloudflare-warp/cloudflare-warp_2024.8.0-1_amd64.deb

# 2. Install package
sudo dpkg -i cloudflare-warp_2024.8.0-1_amd64.deb

# 3. Fix dependencies jika ada
sudo apt install -f
```

**Note**: Ganti versi dan nama file sesuai dengan versi terbaru dari https://pkg.cloudflareclient.com/

## ⚙️ Setup dan Konfigurasi

### 1. Register Device (Pertama Kali)

```bash
# Register device dengan Cloudflare (versi terbaru)
warp-cli registration new

# Atau jika command di atas tidak ada, coba:
# warp-cli registration
```

### 2. Set Mode WARP

```bash
# Mode 1: WARP (Full VPN) - Recommended untuk bypass restriction
warp-cli set-mode warp

# Mode 2: WARP+ (Jika punya license key)
# warp-cli set-mode warp+
# warp-cli set-license YOUR_LICENSE_KEY
```

### 3. Connect WARP

```bash
# Connect ke WARP
warp-cli connect
```

### 4. Cek Status

```bash
# Cek status koneksi
warp-cli status

# Output yang diharapkan:
# Status update: Connected
# Successfully registered
```

### 5. Test Koneksi

```bash
# Test DNS resolution
nslookup api.binance.com

# Test koneksi ke Binance
curl -I https://api.binance.com/api/v3/ping
```

## 🔧 Konfigurasi Lanjutan

### Auto-connect saat Boot

```bash
# Enable systemd service untuk auto-start
sudo systemctl enable warp-svc
sudo systemctl start warp-svc

# Atau gunakan systemd untuk auto-connect
# Buat service file (jika belum ada)
sudo systemctl enable --now warp-svc
```

### Set DNS (Optional)

```bash
# Set DNS ke Cloudflare
warp-cli set-dns 1.1.1.1
```

### Disable WARP (Jika Perlu)

```bash
# Disconnect
warp-cli disconnect

# Unregister device (versi terbaru)
warp-cli registration delete

# Atau stop service
sudo systemctl stop warp-svc
```

## 🧪 Test Setelah Install

### 1. Test DNS Resolution

```bash
# Sebelum WARP (mungkin di-block)
nslookup api.binance.com

# Setelah WARP (harusnya resolve ke IP Binance)
nslookup api.binance.com
```

### 2. Test Binance API

```bash
# Test ping ke Binance API
curl https://api.binance.com/api/v3/ping

# Test get klines (tanpa API key)
curl "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=1"
```

### 3. Test dari Python Script

```bash
# Test dengan script Python
python3 -c "
import requests
try:
    response = requests.get('https://api.binance.com/api/v3/ping', timeout=10)
    print(f'✅ Status: {response.status_code}')
    print(f'Response: {response.text}')
except Exception as e:
    print(f'❌ Error: {e}')
"
```

## 📝 Troubleshooting

### Error: "unrecognized subcommand 'register'"

Jika muncul error ini, gunakan command yang benar:

```bash
# Cek command yang tersedia
warp-cli --help

# Untuk register, gunakan:
warp-cli registration new

# Atau coba:
warp-cli registration
```

### Error: "unrecognized subcommand 'enable-always-on'"

Command ini tidak ada di versi terbaru. Gunakan systemd service:

```bash
# Enable auto-start via systemd
sudo systemctl enable warp-svc
sudo systemctl start warp-svc

# Cek status
sudo systemctl status warp-svc
```

### Error: "warp-cli: command not found"

```bash
# Pastikan WARP terinstall
which warp-cli

# Jika tidak ada, install ulang
sudo apt install --reinstall cloudflare-warp
```

### Error: "Failed to connect"

```bash
# Cek service status
sudo systemctl status warp-svc

# Restart service
sudo systemctl restart warp-svc

# Cek log
journalctl -u warp-svc -n 50
```

### Error: "Device registration failed"

```bash
# Unregister dan register ulang
warp-cli delete
warp-cli register
warp-cli connect
```

### WARP Tidak Bypass Restriction

```bash
# Pastikan mode WARP aktif
warp-cli status

# Coba disconnect dan connect lagi
warp-cli disconnect
warp-cli connect

# Cek IP address
curl https://api.ipify.org
```

## 🔄 Quick Commands Reference

```bash
# Register device
warp-cli registration new

# Connect
warp-cli connect

# Disconnect
warp-cli disconnect

# Status
warp-cli status

# Set mode
warp-cli set-mode warp

# Enable auto-start via systemd
sudo systemctl enable warp-svc
sudo systemctl start warp-svc

# Check IP
curl https://api.ipify.org

# Cek semua command yang tersedia
warp-cli --help
```

## ✅ Checklist

- [ ] Install cloudflare-warp via apt atau .deb
- [ ] Register device dengan `warp-cli registration new`
- [ ] Set mode ke `warp` dengan `warp-cli set-mode warp`
- [ ] Connect dengan `warp-cli connect`
- [ ] Test DNS: `nslookup api.binance.com`
- [ ] Test API: `curl https://api.binance.com/api/v3/ping`
- [ ] Test Python script untuk Binance API
- [ ] Enable auto-start (optional): `sudo systemctl enable warp-svc`

## 🎯 Setelah WARP Terinstall

Setelah WARP terinstall dan connected, error **HTTP 451** seharusnya hilang karena:
- IP address server akan menggunakan IP Cloudflare
- Traffic akan di-routing melalui Cloudflare network
- Binance tidak akan detect server sebagai restricted location

## 📚 Referensi

- Cloudflare WARP Documentation: https://developers.cloudflare.com/warp-client/
- Cloudflare WARP Linux Guide: https://developers.cloudflare.com/warp-client/get-started/linux/
- Package Repository: https://pkg.cloudflareclient.com/

