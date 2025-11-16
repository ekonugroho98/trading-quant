#!/bin/bash
# Script untuk install VPN client di macOS

echo "=========================================="
echo "🔧 INSTALL VPN CLIENT UNTUK AKSES BINANCE"
echo "=========================================="
echo ""

# Cek apakah Homebrew terinstall
if ! command -v brew &> /dev/null; then
    echo "📦 Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

echo ""
echo "Pilih VPN client yang ingin diinstall:"
echo "1. Cloudflare WARP (Free, Recommended)"
echo "2. OpenVPN"
echo "3. WireGuard"
echo "4. Tunnelblick (GUI untuk OpenVPN)"
echo ""
read -p "Pilihan (1-4): " choice

case $choice in
    1)
        echo "📦 Installing Cloudflare WARP..."
        brew install --cask cloudflare-warp
        echo ""
        echo "✅ Cloudflare WARP terinstall!"
        echo "💡 Buka aplikasi Cloudflare WARP dan aktifkan"
        ;;
    2)
        echo "📦 Installing OpenVPN..."
        brew install openvpn
        echo ""
        echo "✅ OpenVPN terinstall!"
        echo "💡 Konfigurasi OpenVPN diperlukan untuk koneksi"
        ;;
    3)
        echo "📦 Installing WireGuard..."
        brew install wireguard-tools
        echo ""
        echo "✅ WireGuard terinstall!"
        echo "💡 Konfigurasi WireGuard diperlukan untuk koneksi"
        ;;
    4)
        echo "📦 Installing Tunnelblick..."
        brew install --cask tunnelblick
        echo ""
        echo "✅ Tunnelblick terinstall!"
        echo "💡 Buka aplikasi Tunnelblick dan import config VPN"
        ;;
    *)
        echo "❌ Pilihan tidak valid"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "✅ Install selesai!"
echo "=========================================="
echo ""
echo "📝 Langkah selanjutnya:"
echo "1. Setup VPN connection sesuai provider VPN Anda"
echo "2. Aktifkan VPN"
echo "3. Test koneksi: python3 test_binance_connection.py"
echo ""

