#!/bin/bash

echo "=== Setting Up VPN for Phone ==="
echo ""

# Detect Kali local IP (used by phone)
LOCAL_IP=$(ip route | awk '/default/ {print $9}')
echo "Your Kali IP: $LOCAL_IP"
echo "Phone will connect to: $LOCAL_IP:51820"
echo ""

# Stop any existing WireGuard instance
systemctl stop wg-quick@wg0 2>/dev/null
wg-quick down wg0 2>/dev/null

# Enable IP forwarding (runtime, no duplication)
sysctl -w net.ipv4.ip_forward=1

# Create working directory
mkdir -p /opt/vpn-lab/phone-keys
cd /opt/vpn-lab/phone-keys || exit 1

# Generate keys
echo "Generating keys for phone VPN..."
SERVER_PRIV=$(wg genkey)
SERVER_PUB=$(echo "$SERVER_PRIV" | wg pubkey)
PHONE_PRIV=$(wg genkey)
PHONE_PUB=$(echo "$PHONE_PRIV" | wg pubkey)

echo "$SERVER_PRIV" > server.priv
echo "$SERVER_PUB"  > server.pub
echo "$PHONE_PRIV"  > phone.priv
echo "$PHONE_PUB"   > phone.pub

echo "✓ Keys generated"
echo ""

# Create WireGuard server config
echo "Creating server configuration..."

cat > /etc/wireguard/wg0.conf << EOF
[Interface]
Address = 10.8.0.1/24
ListenPort = 51820
PrivateKey = $SERVER_PRIV

MTU = 1280

PostUp   = iptables -A FORWARD -i wg0 -o wlan0 -j ACCEPT; \
           iptables -A FORWARD -i wlan0 -o wg0 -m state --state RELATED,ESTABLISHED -j ACCEPT; \
           iptables -t nat -A POSTROUTING -s 10.8.0.0/24 -o wlan0 -j MASQUERADE

PostDown = iptables -D FORWARD -i wg0 -o wlan0 -j ACCEPT; \
           iptables -D FORWARD -i wlan0 -o wg0 -m state --state RELATED,ESTABLISHED -j ACCEPT; \
           iptables -t nat -D POSTROUTING -s 10.8.0.0/24 -o wlan0 -j MASQUERADE

[Peer]
PublicKey = $PHONE_PUB
AllowedIPs = 10.8.0.2/32
EOF

chmod 600 /etc/wireguard/wg0.conf
echo "✓ Server config created: /etc/wireguard/wg0.conf"
echo ""

# Create phone configuration
echo "Creating phone configuration..."

cat > phone.conf << EOF
[Interface]
Address = 10.8.0.2/24
PrivateKey = $PHONE_PRIV
DNS = 8.8.8.8, 8.8.4.4
MTU = 1280

[Peer]
PublicKey = $SERVER_PUB
Endpoint = $LOCAL_IP:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
EOF

echo "✓ Phone config created: phone.conf"
echo ""

# Start WireGuard
echo "Starting WireGuard server..."
wg-quick up wg0
echo "✓ WireGuard server started"
echo ""

# Generate QR code (optional)
echo "Generating QR code for phone..."
if command -v qrencode >/dev/null 2>&1; then
    qrencode -t ansiutf8 < phone.conf
    qrencode -t png -o phone-vpn.png < phone.conf
    echo "✓ QR code generated: phone-vpn.png"
else
    echo "⚠ Install qrencode for QR code: apt install qrencode"
fi

echo ""
echo "========================================"
echo "📱 PHONE VPN SETUP COMPLETE!"
echo "========================================"
echo ""
echo "Server:"
echo "  IP: $LOCAL_IP"
echo "  Port: 51820"
echo ""
echo "Client:"
echo "  Import phone.conf OR scan QR code"
echo ""
echo "Test:"
echo "  Phone → ping 10.8.0.1"
echo "  Kali  → wg show"
echo "========================================"

