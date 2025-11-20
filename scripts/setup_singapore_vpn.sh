#!/bin/bash
# Script untuk setup VPN ke Singapore
# Mengatasi masalah HTTP 451 dengan IP Singapore

echo "=========================================="
echo "🇸🇬 SETUP VPN KE SINGAPORE"
echo "=========================================="
echo ""

# Cek apakah sudah root
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  Script ini memerlukan sudo privileges"
    echo "   Jalankan dengan: sudo bash setup_singapore_vpn.sh"
    exit 1
fi

# Cek apakah WARP masih aktif
if command -v warp-cli &> /dev/null; then
    WARP_STATUS=$(warp-cli status 2>/dev/null | grep -i "connected" || echo "")
    if [ -n "$WARP_STATUS" ]; then
        echo "⚠️  WARP masih aktif!"
        echo "   Status: $WARP_STATUS"
        echo ""
        echo "💡 WARP perlu dimatikan dulu untuk menghindari konflik dengan VPN Singapore"
        echo ""
        read -p "Matikan WARP sekarang? (y/n): " disable_warp
        
        if [ "$disable_warp" = "y" ]; then
            echo "   Disconnecting WARP..."
            warp-cli disconnect
            sleep 2
            
            echo "   Stopping WARP service..."
            systemctl stop warp-svc 2>/dev/null || true
            
            echo "   ✅ WARP sudah dimatikan"
            echo ""
        else
            echo "   ⚠️  WARP masih aktif - mungkin akan konflik dengan VPN Singapore"
            echo ""
        fi
    fi
fi

echo "Pilih metode VPN ke Singapore:"
echo "1. WireGuard (Recommended - cepat dan modern)"
echo "2. OpenVPN"
echo "3. SSH Tunnel (jika punya server Singapore)"
echo "4. Proxy Server (jika punya proxy Singapore)"
echo ""
read -p "Pilihan (1-4): " choice

case $choice in
    1)
        echo ""
        echo "📦 Installing WireGuard..."
        apt update
        apt install -y wireguard wireguard-tools
        
        echo ""
        echo "✅ WireGuard terinstall!"
        echo ""
        echo "📋 Langkah selanjutnya:"
        echo "   1. Dapatkan WireGuard config untuk Singapore:"
        echo "      - Option A: VPN Provider (Mullvad, ProtonVPN, dll)"
        echo "      - Option B: Setup WireGuard server sendiri di VPS Singapore"
        echo ""
        echo "   2. Copy config ke: /etc/wireguard/wg0.conf"
        echo ""
        echo "   3. Connect:"
        echo "      sudo wg-quick up wg0"
        echo ""
        echo "   4. Test:"
        echo "      curl https://ipinfo.io/json"
        echo "      curl https://api.binance.com/api/v3/ping"
        echo ""
        echo "   5. Enable auto-start:"
        echo "      sudo systemctl enable wg-quick@wg0"
        ;;
    2)
        echo ""
        echo "📦 Installing OpenVPN..."
        apt update
        apt install -y openvpn
        
        echo ""
        echo "✅ OpenVPN terinstall!"
        echo ""
        echo "📋 Langkah selanjutnya:"
        echo "   1. Dapatkan OpenVPN config untuk Singapore:"
        echo "      - Download dari VPN provider"
        echo "      - Atau setup OpenVPN server sendiri"
        echo ""
        echo "   2. Copy config ke: /etc/openvpn/client/singapore.conf"
        echo ""
        echo "   3. Connect:"
        echo "      sudo openvpn --config /etc/openvpn/client/singapore.conf"
        echo ""
        echo "   4. Atau sebagai service:"
        echo "      sudo systemctl start openvpn@singapore"
        ;;
    3)
        echo ""
        echo "📦 Setup SSH Tunnel ke Singapore..."
        echo ""
        read -p "Masukkan user@singapore-server: " ssh_server
        read -p "Masukkan port SSH (default 22): " ssh_port
        ssh_port=${ssh_port:-22}
        
        echo ""
        echo "Membuat SSH tunnel dengan SOCKS5 proxy..."
        echo "Command yang akan dijalankan:"
        echo "  ssh -D 1080 -N -f $ssh_server -p $ssh_port"
        echo ""
        read -p "Lanjutkan? (y/n): " confirm
        
        if [ "$confirm" = "y" ]; then
            # Kill existing tunnel jika ada
            pkill -f "ssh -D 1080"
            
            # Buat tunnel baru
            ssh -D 1080 -N -f $ssh_server -p $ssh_port
            
            if [ $? -eq 0 ]; then
                echo "✅ SSH tunnel berhasil dibuat!"
                echo ""
                echo "📋 Setup proxy environment:"
                echo "   export HTTP_PROXY=\"socks5://127.0.0.1:1080\""
                echo "   export HTTPS_PROXY=\"socks5://127.0.0.1:1080\""
                echo ""
                echo "   Test:"
                echo "   curl https://ipinfo.io/json"
                echo "   curl https://api.binance.com/api/v3/ping"
                echo ""
                
                # Set proxy untuk session ini
                export HTTP_PROXY="socks5://127.0.0.1:1080"
                export HTTPS_PROXY="socks5://127.0.0.1:1080"
                
                echo "✅ Proxy sudah di-set untuk session ini"
            else
                echo "❌ Gagal membuat SSH tunnel"
            fi
        fi
        ;;
    4)
        echo ""
        echo "📦 Setup Proxy Server..."
        echo ""
        read -p "Masukkan proxy server (host:port): " proxy_server
        read -p "Jenis proxy (http/socks5, default http): " proxy_type
        proxy_type=${proxy_type:-http}
        
        echo ""
        echo "📋 Setup proxy environment:"
        echo "   export HTTP_PROXY=\"$proxy_type://$proxy_server\""
        echo "   export HTTPS_PROXY=\"$proxy_type://$proxy_server\""
        echo ""
        
        # Set proxy untuk session ini
        export HTTP_PROXY="$proxy_type://$proxy_server"
        export HTTPS_PROXY="$proxy_type://$proxy_server"
        
        echo "✅ Proxy sudah di-set untuk session ini"
        echo ""
        echo "   Test:"
        echo "   curl https://ipinfo.io/json"
        echo "   curl https://api.binance.com/api/v3/ping"
        ;;
    *)
        echo "❌ Pilihan tidak valid"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "✅ Setup selesai!"
echo "=========================================="
echo ""
echo "💡 Catatan:"
echo "   - Pastikan IP sudah berubah ke Singapore"
echo "   - Test dengan: curl https://ipinfo.io/json"
echo "   - Test Binance: curl https://api.binance.com/api/v3/ping"
echo ""

