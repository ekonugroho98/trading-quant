#!/bin/bash
# Script untuk troubleshoot WARP connection
# Mengatasi masalah HTTP 451 meskipun WARP sudah connected

echo "=========================================="
echo "🔍 TROUBLESHOOT WARP CONNECTION"
echo "=========================================="
echo ""

# 1. Cek status WARP
echo "1️⃣ Cek status WARP:"
warp-cli status
echo ""

# 2. Cek mode saat ini
echo "2️⃣ Cek mode WARP saat ini:"
warp-cli get-mode
echo ""

# 3. Cek IP address yang digunakan
echo "3️⃣ Cek IP address saat ini:"
echo "   IP Public:"
curl -s https://api.ipify.org
echo ""
echo "   IP Info:"
curl -s https://ipinfo.io/json | grep -E '"ip"|"country"|"org"'
echo ""

# 4. Cek apakah mode adalah "warp" (full VPN)
CURRENT_MODE=$(warp-cli get-mode 2>/dev/null | grep -i "mode" | awk '{print $NF}' || echo "unknown")

if [ "$CURRENT_MODE" != "warp" ]; then
    echo "⚠️  Mode saat ini: $CURRENT_MODE (bukan 'warp')"
    echo "   Mengubah ke mode 'warp' (full VPN)..."
    warp-cli set-mode warp
    echo "   ✅ Mode diubah ke 'warp'"
    echo ""
    echo "   🔄 Reconnecting..."
    warp-cli disconnect
    sleep 2
    warp-cli connect
    sleep 3
    echo ""
else
    echo "✅ Mode sudah benar: $CURRENT_MODE"
    echo ""
fi

# 5. Cek status lagi setelah reconnect
echo "4️⃣ Cek status setelah reconnect:"
warp-cli status
echo ""

# 6. Cek IP address baru
echo "5️⃣ Cek IP address baru:"
NEW_IP=$(curl -s https://api.ipify.org)
echo "   IP Public: $NEW_IP"
echo "   IP Info:"
curl -s https://ipinfo.io/json | grep -E '"ip"|"country"|"org"'
echo ""

# 7. Test koneksi ke Binance
echo "6️⃣ Test koneksi ke Binance API:"
BINANCE_RESPONSE=$(curl -s https://api.binance.com/api/v3/ping)
echo "   Response: $BINANCE_RESPONSE"
echo ""

if echo "$BINANCE_RESPONSE" | grep -q "code.*0"; then
    echo "✅ SUCCESS! Binance API dapat diakses"
elif echo "$BINANCE_RESPONSE" | grep -qi "restricted"; then
    echo "❌ Masih error: Restricted location"
    echo ""
    echo "💡 Solusi tambahan:"
    echo "   1. Coba gunakan WARP+ dengan license key (gratis):"
    echo "      - Daftar di: https://1.1.1.1/"
    echo "      - Dapatkan license key"
    echo "      - warp-cli set-license YOUR_LICENSE_KEY"
    echo "      - warp-cli set-mode warp+"
    echo "      - warp-cli disconnect && warp-cli connect"
    echo ""
    echo "   2. Atau coba restart service:"
    echo "      sudo systemctl restart warp-svc"
    echo "      warp-cli disconnect && warp-cli connect"
    echo ""
    echo "   3. Cek apakah IP sudah berubah:"
    echo "      curl https://api.ipify.org"
    echo "      curl https://ipinfo.io/json"
else
    echo "⚠️  Response tidak dikenali: $BINANCE_RESPONSE"
fi

echo ""
echo "=========================================="

