#!/bin/bash
# Script untuk install Cloudflare WARP di Debian Linux
# Mengatasi masalah HTTP 451 (restricted location) dari Binance API

set -e

echo "=========================================="
echo "🔧 INSTALL CLOUDFLARE WARP DI DEBIAN"
echo "=========================================="
echo ""

# Cek apakah sudah root atau menggunakan sudo
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  Script ini memerlukan sudo privileges"
    echo "   Jalankan dengan: sudo bash install_warp_debian.sh"
    exit 1
fi

# Cek OS
if [ ! -f /etc/debian_version ]; then
    echo "❌ Script ini hanya untuk Debian/Ubuntu"
    exit 1
fi

echo "📦 Step 1: Update package list..."
apt update

echo ""
echo "📦 Step 2: Install dependencies..."
apt install -y curl gnupg lsb-release

echo ""
echo "📦 Step 3: Add Cloudflare GPG key..."
curl https://pkg.cloudflareclient.com/pubkey.gpg | gpg --yes --dearmor --output /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg

echo ""
echo "📦 Step 4: Add Cloudflare repository..."
RELEASE=$(lsb_release -cs)
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg] https://pkg.cloudflareclient.com/ ${RELEASE} main" > /etc/apt/sources.list.d/cloudflare-client.list

echo ""
echo "📦 Step 5: Update package list..."
apt update

echo ""
echo "📦 Step 6: Install Cloudflare WARP..."
apt install -y cloudflare-warp

echo ""
echo "✅ Cloudflare WARP terinstall!"
echo ""

# Cek apakah warp-cli tersedia
if command -v warp-cli &> /dev/null; then
    echo "📋 Langkah selanjutnya:"
    echo ""
    echo "1. Register device:"
    echo "   warp-cli register"
    echo ""
    echo "2. Set mode ke WARP:"
    echo "   warp-cli set-mode warp"
    echo ""
    echo "3. Connect:"
    echo "   warp-cli connect"
    echo ""
    echo "4. Cek status:"
    echo "   warp-cli status"
    echo ""
    echo "5. Test koneksi:"
    echo "   curl https://api.binance.com/api/v3/ping"
    echo ""
    echo "6. (Optional) Enable auto-connect:"
    echo "   warp-cli enable-always-on"
    echo ""
    echo "=========================================="
    echo "✅ Install selesai!"
    echo "=========================================="
else
    echo "⚠️  warp-cli tidak ditemukan setelah install"
    echo "   Coba install manual atau cek error di atas"
    exit 1
fi

