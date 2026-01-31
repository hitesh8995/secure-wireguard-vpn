#!/bin/bash
echo "=== SIMPLE VPN DEMO ==="
echo ""

# Clean up any existing namespaces
ip netns delete vpn-demo 2>/dev/null
ip netns delete vpn-client 2>/dev/null

# Create namespaces
echo "1. Creating network namespaces..."
ip netns add vpn-demo
ip netns add vpn-client
ip netns exec vpn-demo ip link set lo up
ip netns exec vpn-client ip link set lo up
echo "✓ Namespaces created"

# Generate keys
echo -e "\n2. Generating WireGuard keys..."
SERVER_PRIV=$(wg genkey)
SERVER_PUB=$(echo $SERVER_PRIV | wg pubkey)
CLIENT_PRIV=$(wg genkey)
CLIENT_PUB=$(echo $CLIENT_PRIV | wg pubkey)
echo "✓ Keys generated"

# Setup server
echo -e "\n3. Setting up VPN server..."
ip netns exec vpn-demo ip link add wg0 type wireguard
echo $SERVER_PRIV > /tmp/server_priv.key
ip netns exec vpn-demo wg set wg0 private-key /tmp/server_priv.key
ip netns exec vpn-demo wg set wg0 listen-port 51820
ip netns exec vpn-demo wg set wg0 peer $CLIENT_PUB allowed-ips 10.8.0.2/32
ip netns exec vpn-demo ip addr add 10.8.0.1/24 dev wg0
ip netns exec vpn-demo ip link set wg0 up
rm /tmp/server_priv.key
echo "✓ Server setup: 10.8.0.1:51820"

# Connect namespaces
echo -e "\n4. Connecting namespaces..."
ip link add veth0 type veth peer name veth1
ip link set veth0 netns vpn-demo
ip link set veth1 netns vpn-client
ip netns exec vpn-demo ip addr add 192.168.100.1/24 dev veth0
ip netns exec vpn-demo ip link set veth0 up
ip netns exec vpn-client ip addr add 192.168.100.2/24 dev veth1
ip netns exec vpn-client ip link set veth1 up
ip netns exec vpn-client ip route add default via 192.168.100.1
echo "✓ Namespaces connected"

# Setup client
echo -e "\n5. Setting up VPN client..."
ip netns exec vpn-client ip link add wg-client type wireguard
echo $CLIENT_PRIV > /tmp/client_priv.key
ip netns exec vpn-client wg set wg-client private-key /tmp/client_priv.key
ip netns exec vpn-client wg set wg-client peer $SERVER_PUB allowed-ips 0.0.0.0/0 endpoint 192.168.100.1:51820
ip netns exec vpn-client ip addr add 10.8.0.2/24 dev wg-client
ip netns exec vpn-client ip link set wg-client up
rm /tmp/client_priv.key
echo "✓ Client setup: 10.8.0.2"

# Test connection
echo -e "\n6. Testing connection..."
sleep 2
echo "Pinging server from client..."
ip netns exec vpn-client ping -c 3 -W 1 10.8.0.1

# Show status
echo -e "\n7. VPN Status:"
echo "Server:"
ip netns exec vpn-demo wg show
echo -e "\nClient:"
ip netns exec vpn-client wg show

# Clean up
echo -e "\n8. Cleaning up..."
ip netns delete vpn-demo
ip netns delete vpn-client
ip link delete veth0 2>/dev/null || true
ip link delete veth1 2>/dev/null || true
echo "✓ Cleanup complete"

echo -e "\n✅ Demo completed successfully!"
