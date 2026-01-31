#!/usr/bin/env python3
"""
WireGuard Config Generator
"""
import os
import subprocess
from pathlib import Path

def generate_key_pair(name="server"):
"""Generate WireGuard key pair"""
priv = subprocess.run(["wg", "genkey"], capture_output=True, text=True).stdout.strip()
pub = subprocess.run(["wg", "pubkey"], input=priv, capture_output=True, text=True).stdout.strip()
text

keys_dir = Path("/opt/vpn-lab/keys")
keys_dir.mkdir(exist_ok=True)

(keys_dir / f"{name}.priv").write_text(priv)
(keys_dir / f"{name}.pub").write_text(pub)

return priv, pub

def create_server_config(server_priv, client_pub, interface="wg0", port=51820):
"""Create server configuration"""
config = f"""[Interface]
Address = 10.8.0.1/24
ListenPort = {port}
PrivateKey = {server_priv}
SaveConfig = true
Client configuration

[Peer]
PublicKey = {client_pub}
AllowedIPs = 10.8.0.2/32
"""
return config

def create_client_config(client_priv, server_pub, server_ip="SERVER_IP_HERE"):
"""Create client configuration"""
config = f"""[Interface]
Address = 10.8.0.2/24
PrivateKey = {client_priv}
DNS = 8.8.8.8, 8.8.4.4

[Peer]
PublicKey = {server_pub}
Endpoint = {server_ip}:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""
return config

if name == "main":
print("Generating WireGuard configurations...")
text

# Generate keys
server_priv, server_pub = generate_key_pair("server")
client_priv, client_pub = generate_key_pair("client")

# Create configs
server_config = create_server_config(server_priv, client_pub)
client_config = create_client_config(client_priv, server_pub)

# Save configs
config_dir = Path("/opt/vpn-lab/config")
config_dir.mkdir(exist_ok=True)

(config_dir / "server.conf").write_text(server_config)
(config_dir / "client.conf").write_text(client_config)

print("✓ Configurations generated")
print(f"  Server config: {config_dir}/server.conf")
print(f"  Client config: {config_dir}/client.conf")
print(f"  Server Public Key: {server_pub[:30]}...")

