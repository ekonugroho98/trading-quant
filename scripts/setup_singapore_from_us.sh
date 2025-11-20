#!/bin/bash
# Script khusus untuk setup VPN ke Singapore dari server US
# Server location: United States - Phoenix

echo "=========================================="
echo "🇸🇬 SETUP VPN KE SINGAPORE (Dari US Server)"
echo "=========================================="
echo ""
echo "📍 Server location: United States - Phoenix"
echo "⚠️  Binance API memblokir akses dari US"
echo "✅ Solusi: Setup VPN ke Singapore"
echo ""

# Cek WARP
if command -v warp-cli &> /dev/null; then
    WARP_STATUS=$(warp-cli status 2>/dev/null | grep -i "connected" || echo "")
    if [ -n "$WARP_STATUS" ]; then
        echo "⚠️  WARP masih aktif - perlu dimatikan dulu"
        read -p "Matikan WARP sekarang? (y/n): " disable_warp
        if [ "$disable_warp" = "y" ]; then
            warp-cli disconnect
            systemctl stop warp-svc 2>/dev/null || true
            echo "✅ WARP sudah dimatikan"
        fi
    fi
fi

echo ""
echo "Pilih metode untuk mendapatkan IP Singapore:"
echo ""
echo "1. SSH Tunnel ke VPS Singapore (PALING MUDAH - jika punya VPS SG)"
echo "2. WireGuard dengan VPN Provider (Mullvad, ProtonVPN - berbayar)"
echo "3. Setup WireGuard server sendiri di VPS Singapore"
echo "4. Proxy Server Singapore (jika punya proxy)"
echo ""
read -p "Pilihan (1-4): " choice

case $choice in
    1)
        echo ""
        echo "📋 Setup SSH Tunnel ke Singapore"
        echo ""
        read -p "Masukkan user@singapore-server-ip: " ssh_server
        read -p "Masukkan port SSH (default 22): " ssh_port
        ssh_port=${ssh_port:-22}
        
        echo ""
        echo "🔌 Creating SSH tunnel dengan SOCKS5 proxy..."
        
        # Kill existing tunnel
        pkill -f "ssh -D 1080" 2>/dev/null
        
        # Create tunnel
        ssh -D 1080 -N -f $ssh_server -p $ssh_port
        
        if [ $? -eq 0 ]; then
            echo "✅ SSH tunnel created!"
            echo ""
            
            # Set proxy
            export HTTP_PROXY="socks5://127.0.0.1:1080"
            export HTTPS_PROXY="socks5://127.0.0.1:1080"
            
            echo "📋 Proxy sudah di-set untuk session ini"
            echo ""
            echo "💡 Untuk permanent, tambahkan ke ~/.bashrc:"
            echo "   export HTTP_PROXY=\"socks5://127.0.0.1:1080\""
            echo "   export HTTPS_PROXY=\"socks5://127.0.0.1:1080\""
            echo ""
            
            echo "🧪 Testing connection..."
            sleep 2
            
            IP_INFO=$(curl -s --proxy $HTTP_PROXY https://ipinfo.io/json)
            IP_COUNTRY=$(echo "$IP_INFO" | grep -o '"country": "[^"]*' | cut -d'"' -f4)
            IP_CITY=$(echo "$IP_INFO" | grep -o '"city": "[^"]*' | cut -d'"' -f4)
            
            echo "   IP Info: $IP_INFO"
            echo ""
            
            if [ "$IP_COUNTRY" = "SG" ]; then
                echo "✅ IP sudah Singapore ($IP_CITY)!"
                echo ""
                echo "🧪 Test Binance API..."
                BINANCE_RESPONSE=$(curl -s --proxy $HTTP_PROXY https://api.binance.com/api/v3/ping)
                echo "   Response: $BINANCE_RESPONSE"
                
                if echo "$BINANCE_RESPONSE" | grep -qi "restricted"; then
                    echo "❌ Masih restricted"
                else
                    echo "✅ Binance API dapat diakses!"
                fi
            else
                echo "⚠️  IP belum Singapore (Country: $IP_COUNTRY)"
            fi
            
            echo ""
            echo "📝 Untuk auto-start SSH tunnel, buat systemd service:"
            echo "   sudo nano /etc/systemd/system/singapore-tunnel.service"
            echo ""
            echo "   [Unit]"
            echo "   Description=SSH Tunnel to Singapore"
            echo "   After=network.target"
            echo ""
            echo "   [Service]"
            echo "   Type=simple"
            echo "   ExecStart=/usr/bin/ssh -D 1080 -N $ssh_server -p $ssh_port"
            echo "   Restart=always"
            echo ""
            echo "   [Install]"
            echo "   WantedBy=multi-user.target"
            echo ""
            echo "   Lalu: sudo systemctl enable singapore-tunnel && sudo systemctl start singapore-tunnel"
        else
            echo "❌ Gagal membuat SSH tunnel"
            echo "   Pastikan:"
            echo "   - SSH key sudah di-setup"
            echo "   - Server Singapore dapat diakses"
            echo "   - Port SSH benar"
        fi
        ;;
    2)
        echo ""
        echo "📋 Setup WireGuard dengan VPN Provider"
        echo ""
        echo "Rekomendasi VPN Provider dengan server Singapore:"
        echo "  1. Mullvad (€5/bulan) - https://mullvad.net/"
        echo "  2. ProtonVPN (ada free tier) - https://protonvpn.com/"
        echo "  3. NordVPN - https://nordvpn.com/"
        echo ""
        echo "Langkah:"
        echo "  1. Daftar di provider VPN"
        echo "  2. Download WireGuard config untuk Singapore server"
        echo "  3. Copy config ke: /etc/wireguard/wg0.conf"
        echo "  4. Connect: sudo wg-quick up wg0"
        echo ""
        echo "Atau jalankan: sudo bash scripts/quick_wireguard_setup.sh"
        ;;
    3)
        echo ""
        echo "📋 Setup WireGuard Server di VPS Singapore"
        echo ""
        echo "Jika punya VPS di Singapore, setup WireGuard server:"
        echo ""
        echo "Di VPS Singapore:"
        echo "  1. sudo apt install -y wireguard"
        echo "  2. sudo wg genkey | sudo tee /etc/wireguard/private.key"
        echo "  3. sudo chmod 600 /etc/wireguard/private.key"
        echo "  4. sudo cat /etc/wireguard/private.key | wg pubkey | sudo tee /etc/wireguard/public.key"
        echo ""
        echo "Buat config server (/etc/wireguard/wg0.conf):"
        echo "  [Interface]"
        echo "  PrivateKey = SERVER_PRIVATE_KEY"
        echo "  Address = 10.0.0.1/24"
        echo "  ListenPort = 51820"
        echo "  PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE"
        echo "  PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE"
        echo ""
        echo "Enable IP forwarding:"
        echo "  echo 'net.ipv4.ip_forward=1' | sudo tee -a /etc/sysctl.conf"
        echo "  sudo sysctl -p"
        echo ""
        echo "Start server:"
        echo "  sudo wg-quick up wg0"
        echo "  sudo systemctl enable wg-quick@wg0"
        echo ""
        echo "Kembali ke server ini, jalankan: sudo bash scripts/quick_wireguard_setup.sh"
        ;;
    4)
        echo ""
        echo "📋 Setup Proxy Server Singapore"
        echo ""
        read -p "Masukkan proxy server (host:port): " proxy_server
        read -p "Jenis proxy (http/socks5, default http): " proxy_type
        proxy_type=${proxy_type:-http}
        
        export HTTP_PROXY="$proxy_type://$proxy_server"
        export HTTPS_PROXY="$proxy_type://$proxy_server"
        
        echo "✅ Proxy sudah di-set"
        echo ""
        echo "🧪 Testing..."
        curl --proxy $HTTP_PROXY https://ipinfo.io/json
        curl --proxy $HTTP_PROXY https://api.binance.com/api/v3/ping
        ;;
    *)
        echo "❌ Pilihan tidak valid"
        exit 1
        ;;
esac

echo ""
echo "=========================================="

