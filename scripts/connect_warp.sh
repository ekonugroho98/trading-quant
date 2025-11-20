#!/bin/bash
# Script untuk connect WARP dengan mudah

echo "=========================================="
echo "🔵 CONNECT CLOUDFLARE WARP"
echo "=========================================="
echo ""

# Cek apakah WARP terinstall
if ! command -v warp-cli &> /dev/null; then
    echo "❌ WARP belum terinstall"
    echo ""
    echo "Install dulu dengan:"
    echo "   sudo bash scripts/install_warp_debian.sh"
    exit 1
fi

# Cek status saat ini
echo "📊 Status WARP saat ini:"
warp-cli status
echo ""

# Cek apakah sudah registered
REGISTRATION=$(warp-cli registration 2>/dev/null | grep -i "registered\|not registered" || echo "")

if echo "$REGISTRATION" | grep -qi "not registered"; then
    echo "⚠️  Device belum terdaftar"
    echo ""
    echo "📋 Register device dulu:"
    echo "   warp-cli registration new"
    echo ""
    read -p "Register sekarang? (y/n): " register_now
    
    if [ "$register_now" = "y" ]; then
        echo ""
        echo "🔐 Registering device..."
        warp-cli registration new
        
        if [ $? -eq 0 ]; then
            echo "✅ Device terdaftar!"
        else
            echo "❌ Gagal register device"
            exit 1
        fi
    else
        echo "   Jalankan manual: warp-cli registration new"
        exit 0
    fi
fi

echo ""
echo "🔌 Connecting WARP..."
warp-cli connect

if [ $? -eq 0 ]; then
    echo "✅ WARP connecting..."
    echo ""
    echo "⏳ Tunggu 3-5 detik untuk koneksi stabil..."
    sleep 5
    
    echo ""
    echo "📊 Status setelah connect:"
    warp-cli status
    echo ""
    
    echo "🌐 Cek IP address:"
    NEW_IP=$(curl -s https://api.ipify.org)
    IP_INFO=$(curl -s https://ipinfo.io/json)
    
    echo "   IP: $NEW_IP"
    echo "   Info: $IP_INFO"
    echo ""
    
    IP_COUNTRY=$(echo "$IP_INFO" | grep -o '"country": "[^"]*' | cut -d'"' -f4 || echo "")
    
    echo "🧪 Test Binance API:"
    BINANCE_RESPONSE=$(curl -s https://api.binance.com/api/v3/ping)
    echo "   Response: $BINANCE_RESPONSE"
    echo ""
    
    if echo "$BINANCE_RESPONSE" | grep -qi "restricted"; then
        echo "❌ Masih error: Restricted location"
        echo ""
        echo "⚠️  CATATAN PENTING:"
        echo "   WARP tidak bisa pilih location secara manual."
        echo "   IP Anda saat ini: $IP_COUNTRY"
        echo ""
        if [ "$IP_COUNTRY" = "US" ]; then
            echo "   Server Anda di US, dan Binance memblokir akses dari US."
            echo "   WARP tidak akan solve masalah ini karena IP masih US."
            echo ""
            echo "💡 SOLUSI: Setup VPN ke Singapore"
            echo "   Jalankan: sudo bash scripts/setup_singapore_from_us.sh"
        else
            echo "   Coba gunakan WARP+ dengan license key untuk IP yang lebih baik."
            echo "   Atau setup VPN ke Singapore."
        fi
    else
        echo "✅ Binance API dapat diakses!"
    fi
else
    echo "❌ Gagal connect WARP"
    echo ""
    echo "💡 Troubleshooting:"
    echo "   1. Cek status: warp-cli status"
    echo "   2. Cek service: sudo systemctl status warp-svc"
    echo "   3. Restart service: sudo systemctl restart warp-svc"
    echo "   4. Coba lagi: warp-cli connect"
fi

echo ""
echo "=========================================="
echo ""
echo "📋 Command WARP yang berguna:"
echo "   warp-cli status          - Cek status"
echo "   warp-cli connect         - Connect"
echo "   warp-cli disconnect      - Disconnect"
echo "   warp-cli registration    - Cek registration"
echo "   warp-cli --help          - Lihat semua command"
echo ""

