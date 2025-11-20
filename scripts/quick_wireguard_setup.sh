#!/bin/bash
# Quick setup WireGuard untuk Singapore
# Script interaktif untuk setup WireGuard config

echo "=========================================="
echo "🇸🇬 QUICK WIREGUARD SETUP UNTUK SINGAPORE"
echo "=========================================="
echo ""

# Cek apakah WireGuard terinstall
if ! command -v wg &> /dev/null; then
    echo "❌ WireGuard belum terinstall"
    echo "   Install dulu: sudo apt install -y wireguard wireguard-tools"
    exit 1
fi

echo "Pilih cara mendapatkan WireGuard config:"
echo "1. Punya VPS/Server di Singapore (setup WireGuard server sendiri)"
echo "2. Punya WireGuard config file dari provider VPN"
echo "3. Ingin setup WireGuard server di VPS Singapore (panduan)"
echo "4. Gunakan SSH Tunnel ke Singapore (lebih mudah)"
echo ""
read -p "Pilihan (1-4): " choice

case $choice in
    1)
        echo ""
        echo "📋 Setup WireGuard Client untuk Server Singapore yang sudah ada"
        echo ""
        read -p "Masukkan Public Key dari server Singapore: " server_pubkey
        read -p "Masukkan IP server Singapore: " server_ip
        read -p "Masukkan port WireGuard (default 51820): " server_port
        server_port=${server_port:-51820}
        read -p "Masukkan IP client di WireGuard network (contoh: 10.0.0.2/24): " client_ip
        
        # Generate client keys
        echo ""
        echo "🔑 Generating client keys..."
        CLIENT_PRIVATE_KEY=$(wg genkey)
        CLIENT_PUBLIC_KEY=$(echo "$CLIENT_PRIVATE_KEY" | wg pubkey)
        
        echo "✅ Client keys generated!"
        echo "   Public Key: $CLIENT_PUBLIC_KEY"
        echo ""
        echo "📋 Copy Public Key ini ke server Singapore (tambahkan sebagai peer)"
        echo ""
        read -p "Tekan Enter setelah menambahkan peer di server..."
        
        # Create config
        CONFIG_FILE="/etc/wireguard/wg0.conf"
        echo "📝 Creating WireGuard config..."
        
        sudo tee "$CONFIG_FILE" > /dev/null <<EOF
[Interface]
PrivateKey = $CLIENT_PRIVATE_KEY
Address = $client_ip
DNS = 1.1.1.1

[Peer]
PublicKey = $server_pubkey
Endpoint = $server_ip:$server_port
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
EOF
        
        sudo chmod 600 "$CONFIG_FILE"
        
        echo "✅ Config created: $CONFIG_FILE"
        echo ""
        echo "🔌 Connecting..."
        sudo wg-quick up wg0
        
        if [ $? -eq 0 ]; then
            echo "✅ WireGuard connected!"
            echo ""
            echo "🧪 Testing connection..."
            sleep 2
            NEW_IP=$(curl -s https://api.ipify.org)
            IP_INFO=$(curl -s https://ipinfo.io/json)
            
            echo "   IP: $NEW_IP"
            echo "   Info: $IP_INFO"
            echo ""
            
            if echo "$IP_INFO" | grep -qi "singapore\|SG"; then
                echo "✅ IP sudah Singapore!"
            else
                echo "⚠️  IP belum Singapore, cek config"
            fi
            
            echo ""
            echo "🧪 Test Binance API..."
            BINANCE_RESPONSE=$(curl -s https://api.binance.com/api/v3/ping)
            echo "   Response: $BINANCE_RESPONSE"
            
            if echo "$BINANCE_RESPONSE" | grep -qi "restricted"; then
                echo "❌ Masih restricted"
            else
                echo "✅ Binance API dapat diakses!"
            fi
        else
            echo "❌ Gagal connect WireGuard"
            echo "   Cek config: sudo cat $CONFIG_FILE"
        fi
        ;;
    2)
        echo ""
        echo "📋 Import WireGuard Config File"
        echo ""
        read -p "Masukkan path ke config file (atau paste config): " config_path
        
        if [ -f "$config_path" ]; then
            # Copy file
            sudo cp "$config_path" /etc/wireguard/wg0.conf
            sudo chmod 600 /etc/wireguard/wg0.conf
            echo "✅ Config copied to /etc/wireguard/wg0.conf"
        else
            echo "📝 Paste config (tekan Ctrl+D setelah selesai):"
            sudo tee /etc/wireguard/wg0.conf > /dev/null
            sudo chmod 600 /etc/wireguard/wg0.conf
        fi
        
        echo ""
        echo "🔌 Connecting..."
        sudo wg-quick up wg0
        
        if [ $? -eq 0 ]; then
            echo "✅ WireGuard connected!"
            echo ""
            echo "🧪 Testing..."
            sleep 2
            curl https://ipinfo.io/json
            curl https://api.binance.com/api/v3/ping
        fi
        ;;
    3)
        echo ""
        echo "📚 Panduan Setup WireGuard Server di VPS Singapore"
        echo ""
        echo "Langkah-langkah:"
        echo ""
        echo "1. Di VPS Singapore, install WireGuard:"
        echo "   sudo apt install -y wireguard"
        echo ""
        echo "2. Generate server keys:"
        echo "   sudo wg genkey | sudo tee /etc/wireguard/private.key"
        echo "   sudo chmod 600 /etc/wireguard/private.key"
        echo "   sudo cat /etc/wireguard/private.key | wg pubkey | sudo tee /etc/wireguard/public.key"
        echo ""
        echo "3. Buat config server (/etc/wireguard/wg0.conf):"
        echo "   [Interface]"
        echo "   PrivateKey = SERVER_PRIVATE_KEY"
        echo "   Address = 10.0.0.1/24"
        echo "   ListenPort = 51820"
        echo "   PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE"
        echo "   PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE"
        echo ""
        echo "4. Enable IP forwarding:"
        echo "   echo 'net.ipv4.ip_forward=1' | sudo tee -a /etc/sysctl.conf"
        echo "   sudo sysctl -p"
        echo ""
        echo "5. Start WireGuard server:"
        echo "   sudo wg-quick up wg0"
        echo "   sudo systemctl enable wg-quick@wg0"
        echo ""
        echo "6. Kembali ke server ini, pilih option 1 untuk setup client"
        echo ""
        echo "📚 Dokumentasi lengkap: doc/SETUP_VPN_SINGAPORE.md"
        ;;
    4)
        echo ""
        echo "📋 Setup SSH Tunnel ke Singapore (Paling Mudah)"
        echo ""
        read -p "Masukkan user@singapore-server: " ssh_server
        read -p "Masukkan port SSH (default 22): " ssh_port
        ssh_port=${ssh_port:-22}
        
        echo ""
        echo "🔌 Creating SSH tunnel..."
        
        # Kill existing tunnel
        pkill -f "ssh -D 1080" 2>/dev/null
        
        # Create tunnel
        ssh -D 1080 -N -f $ssh_server -p $ssh_port
        
        if [ $? -eq 0 ]; then
            echo "✅ SSH tunnel created!"
            echo ""
            echo "📋 Setup proxy environment..."
            echo ""
            echo "Tambahkan ke ~/.bashrc atau ~/.zshrc:"
            echo "   export HTTP_PROXY=\"socks5://127.0.0.1:1080\""
            echo "   export HTTPS_PROXY=\"socks5://127.0.0.1:1080\""
            echo ""
            echo "Atau set untuk session ini:"
            export HTTP_PROXY="socks5://127.0.0.1:1080"
            export HTTPS_PROXY="socks5://127.0.0.1:1080"
            echo "   ✅ Proxy sudah di-set"
            echo ""
            echo "🧪 Testing..."
            sleep 2
            curl https://ipinfo.io/json
            echo ""
            curl https://api.binance.com/api/v3/ping
        else
            echo "❌ Gagal membuat SSH tunnel"
            echo "   Pastikan SSH key sudah di-setup"
        fi
        ;;
    *)
        echo "❌ Pilihan tidak valid"
        exit 1
        ;;
esac

echo ""
echo "=========================================="

