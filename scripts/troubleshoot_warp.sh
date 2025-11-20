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
if warp-cli get-mode 2>/dev/null | grep -q .; then
    warp-cli get-mode
else
    echo "   ⚠️  Command 'get-mode' tidak tersedia di versi ini"
    echo "   💡 Cek command yang tersedia: warp-cli --help"
    # Coba cek via settings
    if warp-cli settings 2>/dev/null | grep -q .; then
        echo "   Current settings:"
        warp-cli settings 2>/dev/null | head -10
    fi
fi
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

if [ "$CURRENT_MODE" != "unknown" ] && [ "$CURRENT_MODE" != "warp" ]; then
    echo "⚠️  Mode saat ini: $CURRENT_MODE (bukan 'warp')"
    echo "   Mengubah ke mode 'warp' (full VPN)..."
    if warp-cli set-mode warp 2>/dev/null; then
        echo "   ✅ Mode diubah ke 'warp'"
        echo ""
        echo "   🔄 Reconnecting..."
        warp-cli disconnect
        sleep 2
        warp-cli connect
        sleep 3
        echo ""
    else
        echo "   ⚠️  Command 'set-mode' tidak tersedia"
        echo "   💡 Versi WARP ini mungkin sudah full VPN mode"
        echo ""
    fi
elif [ "$CURRENT_MODE" = "unknown" ]; then
    echo "⚠️  Tidak bisa cek mode (command tidak tersedia)"
    echo "   💡 Versi WARP ini mungkin sudah full VPN mode otomatis"
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

# Cek response - prioritas: restricted dulu, baru code 0
if echo "$BINANCE_RESPONSE" | grep -qi "restricted"; then
    echo "❌ ERROR: Masih restricted location meskipun IP sudah Cloudflare"
    echo ""
    echo "🔍 Analisis:"
    echo "   - WARP sudah connected ✅"
    echo "   - IP sudah Cloudflare (US) ✅"
    echo "   - Tapi Binance masih detect sebagai restricted ❌"
    echo ""
    echo "💡 Solusi (coba secara berurutan):"
    echo ""
    echo "   1️⃣  Gunakan WARP+ dengan License Key (RECOMMENDED):"
    echo "      - Daftar gratis di: https://1.1.1.1/"
    echo "      - Download WARP app di mobile, dapatkan license key"
    echo "      - Atau gunakan: https://github.com/ViRb3/wgcf (generate WARP+ key)"
    echo "      - warp-cli set-license YOUR_LICENSE_KEY"
    echo "      - warp-cli disconnect && warp-cli connect"
    echo ""
    echo "   2️⃣  Coba VPN/Proxy Alternatif:"
    echo "      - Install VPN lain (OpenVPN, WireGuard)"
    echo "      - Atau gunakan proxy server"
    echo ""
    echo "   3️⃣  Gunakan Binance Spot API (mungkin tidak di-block):"
    echo "      - Ubah BINANCE_API_TYPE di config.py ke 'spot'"
    echo "      - Spot API mungkin tidak seketat Futures API"
    echo ""
    echo "   4️⃣  Contact Binance Support:"
    echo "      - Jika yakin IP sudah benar (Cloudflare US)"
    echo "      - Mungkin perlu whitelist IP atau account"
    echo ""
elif echo "$BINANCE_RESPONSE" | grep -q '"code":\s*0' && ! echo "$BINANCE_RESPONSE" | grep -qi "restricted"; then
    echo "✅ SUCCESS! Binance API dapat diakses"
    echo "   Response: $BINANCE_RESPONSE"
else
    echo "⚠️  Response tidak dikenali: $BINANCE_RESPONSE"
    echo "   Cek manual: curl https://api.binance.com/api/v3/ping"
fi

echo ""
echo "=========================================="

