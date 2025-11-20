# Setup VPN/Proxy ke Singapore untuk Binance API

## 🎯 Tujuan

Mengganti IP address server ke Singapore untuk mengatasi error HTTP 451 dari Binance API.

## ⚠️ Catatan tentang WARP

**Cloudflare WARP tidak bisa pilih location secara manual**. WARP akan otomatis assign IP dari berbagai lokasi (biasanya US, EU). Untuk IP Singapore, perlu gunakan VPN/proxy lain.

## 🚀 Solusi: Setup VPN ke Singapore

### Option 1: WireGuard dengan Server Singapore (Recommended)

WireGuard adalah VPN modern, cepat, dan mudah dikonfigurasi.

#### 1. Install WireGuard

```bash
# Di Debian/Ubuntu
sudo apt update
sudo apt install -y wireguard wireguard-tools

# Cek install
wg --version
```

#### 2. Dapatkan WireGuard Config untuk Singapore

**Option A: Gunakan VPN Provider (Berbayar tapi Reliable)**

- **Mullvad**: https://mullvad.net/ (€5/bulan, support WireGuard, ada server Singapore)
- **ProtonVPN**: https://protonvpn.com/ (ada free tier, tapi Singapore mungkin premium)
- **NordVPN**: https://nordvpn.com/ (support WireGuard, ada server Singapore)

**Option B: Setup WireGuard Server Sendiri di Singapore**

Jika punya VPS di Singapore (AWS, DigitalOcean, Linode, dll):

```bash
# Di server Singapore, install WireGuard
sudo apt install -y wireguard

# Generate keys
wg genkey | sudo tee /etc/wireguard/private.key
sudo chmod 600 /etc/wireguard/private.key
sudo cat /etc/wireguard/private.key | wg pubkey | sudo tee /etc/wireguard/public.key

# Buat config
sudo nano /etc/wireguard/wg0.conf
```

**Config template untuk server:**
```ini
[Interface]
PrivateKey = SERVER_PRIVATE_KEY
Address = 10.0.0.1/24
ListenPort = 51820
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

[Peer]
PublicKey = CLIENT_PUBLIC_KEY
AllowedIPs = 10.0.0.2/32
```

**Config untuk client (di server trading):**
```ini
[Interface]
PrivateKey = CLIENT_PRIVATE_KEY
Address = 10.0.0.2/24
DNS = 1.1.1.1

[Peer]
PublicKey = SERVER_PUBLIC_KEY
Endpoint = YOUR_SINGAPORE_SERVER_IP:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
```

#### 3. Aktifkan WireGuard

```bash
# Di server trading (client)
sudo wg-quick up wg0

# Cek status
sudo wg show

# Cek IP
curl https://api.ipify.org
curl https://ipinfo.io/json
```

#### 4. Test Binance API

```bash
curl https://api.binance.com/api/v3/ping
```

### Option 2: OpenVPN dengan Server Singapore

#### 1. Install OpenVPN

```bash
sudo apt update
sudo apt install -y openvpn
```

#### 2. Dapatkan OpenVPN Config

**Option A: VPN Provider**
- Download config file dari provider VPN (Mullvad, ProtonVPN, dll)
- Pilih server Singapore

**Option B: Setup Sendiri**
- Setup OpenVPN server di VPS Singapore
- Generate config file

#### 3. Connect

```bash
# Connect dengan config file
sudo openvpn --config singapore.ovpn

# Atau sebagai service
sudo systemctl start openvpn@singapore
```

### Option 3: Proxy Server Singapore (Paling Mudah)

Jika punya proxy server di Singapore atau menggunakan proxy service:

#### 1. Setup Proxy via Environment Variables

```bash
# Set proxy di terminal
export HTTP_PROXY="http://proxy-singapore:port"
export HTTPS_PROXY="http://proxy-singapore:port"
export NO_PROXY="localhost,127.0.0.1"

# Test
curl --proxy $HTTP_PROXY https://api.ipify.org
curl --proxy $HTTP_PROXY https://ipinfo.io/json
```

#### 2. Update Python Script untuk Gunakan Proxy

File `binance_data.py` dan `binance_futures_data.py` sudah support proxy via environment variables. Pastikan environment variables sudah di-set sebelum run script.

#### 3. Proxy Service Gratis (Hati-hati dengan Keamanan)

**⚠️ WARNING**: Proxy gratis biasanya tidak aman dan tidak reliable!

- **ProxyScrape**: https://proxyscrape.com/ (free proxy list)
- **Free Proxy List**: https://free-proxy-list.net/

**Contoh penggunaan:**
```bash
# Dapatkan proxy Singapore dari list
# Set proxy
export HTTP_PROXY="http://PROXY_IP:PORT"
export HTTPS_PROXY="http://PROXY_IP:PORT"

# Test
curl --proxy $HTTP_PROXY https://api.binance.com/api/v3/ping
```

### Option 4: SSH Tunnel ke Server Singapore

Jika punya server/VPS di Singapore:

```bash
# Buat SSH tunnel dengan SOCKS5 proxy
ssh -D 1080 -N -f user@singapore-server-ip

# Set proxy
export HTTP_PROXY="socks5://127.0.0.1:1080"
export HTTPS_PROXY="socks5://127.0.0.1:1080"

# Test
curl https://api.ipify.org
curl https://api.binance.com/api/v3/ping
```

## 🧪 Test Setelah Setup

### 1. Cek IP Address

```bash
# Harusnya menunjukkan IP Singapore
curl https://api.ipify.org
curl https://ipinfo.io/json

# Output harus menunjukkan:
# "country": "SG"
# "city": "Singapore"
```

### 2. Test Binance API

```bash
# Test ping
curl https://api.binance.com/api/v3/ping

# Response yang benar:
# {} atau {"code":0}

# Response yang SALAH:
# {"code":0,"msg":"Service unavailable from a restricted location..."}
```

### 3. Test dari Python

```bash
# Test dengan Python
python3 -c "
import requests
import os

# Gunakan proxy jika ada
proxies = None
if 'HTTP_PROXY' in os.environ:
    proxies = {
        'http': os.environ['HTTP_PROXY'],
        'https': os.environ['HTTPS_PROXY']
    }

try:
    response = requests.get('https://api.binance.com/api/v3/ping', proxies=proxies, timeout=10)
    print(f'Status: {response.status_code}')
    print(f'Response: {response.text}')
    if 'restricted' not in response.text.lower():
        print('✅ SUCCESS! Binance API dapat diakses')
    else:
        print('❌ Masih restricted')
except Exception as e:
    print(f'❌ Error: {e}')
"
```

## 📋 Rekomendasi

### Untuk Production (Reliable):

1. **Mullvad VPN** (€5/bulan)
   - Support WireGuard
   - Ada server Singapore
   - No-log policy
   - Mudah setup

2. **VPS Singapore + WireGuard** (Sendiri)
   - Kontrol penuh
   - Biaya: ~$5-10/bulan (DigitalOcean, Linode, dll)
   - Setup lebih kompleks

### Untuk Testing (Quick):

1. **SSH Tunnel** (jika punya server Singapore)
   - Gratis
   - Mudah setup
   - Cukup untuk testing

2. **Proxy Service** (hati-hati)
   - Bisa gratis
   - Tidak reliable
   - Tidak aman untuk production

## 🔧 Auto-start VPN

### WireGuard

```bash
# Enable service
sudo systemctl enable wg-quick@wg0
sudo systemctl start wg-quick@wg0
```

### OpenVPN

```bash
# Enable service
sudo systemctl enable openvpn@singapore
sudo systemctl start openvpn@singapore
```

### SSH Tunnel (via systemd)

Buat service file:
```bash
sudo nano /etc/systemd/system/singapore-tunnel.service
```

```ini
[Unit]
Description=SSH Tunnel to Singapore
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/bin/ssh -D 1080 -N user@singapore-server
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl enable singapore-tunnel
sudo systemctl start singapore-tunnel
```

## ✅ Checklist

- [ ] Install VPN client (WireGuard/OpenVPN) atau setup proxy
- [ ] Connect ke server Singapore
- [ ] Cek IP: `curl https://ipinfo.io/json` (harus SG)
- [ ] Test Binance: `curl https://api.binance.com/api/v3/ping`
- [ ] Test dari Python script
- [ ] Enable auto-start (optional)

## 🚀 Quick Start (WireGuard dengan Mullvad)

```bash
# 1. Daftar di Mullvad: https://mullvad.net/
# 2. Login dan generate WireGuard key
# 3. Download config untuk Singapore server
# 4. Install WireGuard
sudo apt install -y wireguard

# 5. Copy config
sudo cp singapore.conf /etc/wireguard/wg0.conf

# 6. Connect
sudo wg-quick up wg0

# 7. Test
curl https://ipinfo.io/json
curl https://api.binance.com/api/v3/ping
```

