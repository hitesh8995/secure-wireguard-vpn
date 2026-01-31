#!/usr/bin/env python3
"""
FIXED SAFE VPN - No process substitution errors
"""
import os
import sys
import json
import subprocess
import tempfile
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class VPNConfig:
    """VPN configuration"""
    namespace: str = "vpn-lab"
    server_ip: str = "10.8.0.1"
    client_ip: str = "10.8.0.2"
    subnet: str = "24"
    port: int = 51820
    interface: str = "wg0"

class SafeVPNFixed:
    """Fixed VPN class - no process substitution"""
    
    def __init__(self, config: Optional[VPNConfig] = None):
        self.config = config or VPNConfig()
        self.base_dir = Path("/opt/vpn-lab")
        self.keys_dir = self.base_dir / "keys"
        self.config_dir = self.base_dir / "config"
        self.keys_dir.mkdir(exist_ok=True)
        self.config_dir.mkdir(exist_ok=True)
    
    def run_cmd(self, cmd: str, check: bool = True, capture: bool = True) -> tuple:
        """Run shell command safely"""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=capture,
                text=True,
                check=check
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.CalledProcessError as e:
            print(f"Command failed: {cmd}")
            if e.stderr:
                print(f"Error: {e.stderr[:200]}")
            return e.returncode, e.stdout, e.stderr
    
    def write_temp_key(self, key: str) -> str:
        """Write key to temporary file and return path"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write(key.strip())
            return f.name
    
    def create_namespace(self) -> bool:
        """Create isolated network namespace"""
        print(f"Creating isolated namespace: {self.config.namespace}")
        
        # Delete if exists
        self.run_cmd(f"ip netns del {self.config.namespace}", check=False)
        
        # Create namespace
        code, out, err = self.run_cmd(f"ip netns add {self.config.namespace}")
        if code == 0:
            self.run_cmd(f"ip netns exec {self.config.namespace} ip link set lo up")
            print("✓ Namespace created")
            return True
        return False
    
    def generate_keys(self) -> Dict[str, str]:
        """Generate WireGuard keys"""
        print("Generating cryptographic keys...")
        
        keys = {}
        
        # Generate server keys
        code, priv, err = self.run_cmd("wg genkey")
        if code == 0:
            keys['server_private'] = priv.strip()
            # Create temp file for private key
            temp_file = self.write_temp_key(keys['server_private'])
            code2, pub, err2 = self.run_cmd(f"wg pubkey < {temp_file}")
            os.unlink(temp_file)
            if code2 == 0:
                keys['server_public'] = pub.strip()
                (self.keys_dir / "server_private.key").write_text(keys['server_private'])
                (self.keys_dir / "server_public.key").write_text(keys['server_public'])
                print("✓ Server keys generated")
        
        # Generate client keys
        code, priv, err = self.run_cmd("wg genkey")
        if code == 0:
            keys['client_private'] = priv.strip()
            temp_file = self.write_temp_key(keys['client_private'])
            code2, pub, err2 = self.run_cmd(f"wg pubkey < {temp_file}")
            os.unlink(temp_file)
            if code2 == 0:
                keys['client_public'] = pub.strip()
                (self.keys_dir / "client_private.key").write_text(keys['client_private'])
                (self.keys_dir / "client_public.key").write_text(keys['client_public'])
                print("✓ Client keys generated")
        
        return keys
    
    def setup_server(self, keys: Dict[str, str]) -> bool:
        """Setup WireGuard server in namespace - FIXED VERSION"""
        print("Setting up VPN server...")
        
        # Create interface
        cmds = [
            f"ip netns exec {self.config.namespace} ip link add {self.config.interface} type wireguard",
        ]
        
        for cmd in cmds:
            code, out, err = self.run_cmd(cmd)
            if code != 0:
                print(f"Failed: {cmd}")
                print(f"Error: {err}")
                return False
        
        # Set private key using echo and pipe
        priv_key_file = self.write_temp_key(keys['server_private'])
        cmd = f"ip netns exec {self.config.namespace} wg set {self.config.interface} private-key {priv_key_file}"
        code, out, err = self.run_cmd(cmd)
        os.unlink(priv_key_file)
        
        if code != 0:
            print("Failed to set private key")
            return False
        
        # Set listen port and peer
        cmds = [
            f"ip netns exec {self.config.namespace} wg set {self.config.interface} listen-port {self.config.port}",
            f"ip netns exec {self.config.namespace} wg set {self.config.interface} peer {keys['client_public']} allowed-ips {self.config.client_ip}/32",
            f"ip netns exec {self.config.namespace} ip addr add {self.config.server_ip}/{self.config.subnet} dev {self.config.interface}",
            f"ip netns exec {self.config.namespace} ip link set {self.config.interface} up",
        ]
        
        for cmd in cmds:
            code, out, err = self.run_cmd(cmd)
            if code != 0:
                print(f"Failed: {cmd}")
                print(f"Error: {err}")
                return False
        
        print(f"✓ Server setup complete: {self.config.server_ip}:{self.config.port}")
        return True
    
    def setup_client(self, keys: Dict[str, str]) -> bool:
        """Setup WireGuard client in separate namespace - FIXED VERSION"""
        client_ns = f"{self.config.namespace}-client"
        
        # Create client namespace
        self.run_cmd(f"ip netns del {client_ns}", check=False)
        code, out, err = self.run_cmd(f"ip netns add {client_ns}")
        if code != 0:
            return False
        
        # Bring up loopback
        self.run_cmd(f"ip netns exec {client_ns} ip link set lo up")
        
        # Create veth pair to connect namespaces
        veth_cmds = [
            f"ip link add veth0 type veth peer name veth1",
            f"ip link set veth1 netns {client_ns}",
            f"ip link set veth0 netns {self.config.namespace}",
            f"ip netns exec {self.config.namespace} ip addr add 192.168.100.1/24 dev veth0",
            f"ip netns exec {self.config.namespace} ip link set veth0 up",
            f"ip netns exec {client_ns} ip addr add 192.168.100.2/24 dev veth1",
            f"ip netns exec {client_ns} ip link set veth1 up",
            f"ip netns exec {client_ns} ip route add default via 192.168.100.1",
        ]
        
        for cmd in veth_cmds:
            code, out, err = self.run_cmd(cmd, check=False)
        
        # Create WireGuard interface in client namespace
        self.run_cmd(f"ip netns exec {client_ns} ip link add wg-client type wireguard", check=False)
        
        # Set private key using temp file
        priv_key_file = self.write_temp_key(keys['client_private'])
        self.run_cmd(f"ip netns exec {client_ns} wg set wg-client private-key {priv_key_file}", check=False)
        os.unlink(priv_key_file)
        
        # Configure client
        client_cmds = [
            f"ip netns exec {client_ns} wg set wg-client peer {keys['server_public']} allowed-ips 0.0.0.0/0 endpoint 192.168.100.1:{self.config.port}",
            f"ip netns exec {client_ns} ip addr add {self.config.client_ip}/{self.config.subnet} dev wg-client",
            f"ip netns exec {client_ns} ip link set wg-client up",
        ]
        
        for cmd in client_cmds:
            self.run_cmd(cmd, check=False)
        
        print(f"✓ Client setup complete in namespace: {client_ns}")
        return True
    
    def test_connection(self) -> bool:
        """Test VPN connection"""
        print("Testing VPN connection...")
        
        client_ns = f"{self.config.namespace}-client"
        
        # Wait for connection
        time.sleep(2)
        
        # Test ping
        print(f"Pinging server ({self.config.server_ip}) from client...")
        code, out, err = self.run_cmd(
            f"ip netns exec {client_ns} ping -c 3 -W 2 {self.config.server_ip}",
            check=False
        )
        
        if code == 0 and "64 bytes" in out:
            print("✓ Ping successful! VPN is working.")
            print(out)
            
            # Show statistics
            print("\n" + "="*50)
            print("VPN CONNECTION STATISTICS")
            print("="*50)
            
            print(f"\nServer WireGuard Status:")
            self.run_cmd(f"ip netns exec {self.config.namespace} wg show")
            
            print(f"\nClient WireGuard Status:")
            self.run_cmd(f"ip netns exec {client_ns} wg show")
            
            return True
        else:
            print("✗ Ping failed. Check configuration.")
            print(f"Output: {out}")
            print(f"Error: {err}")
            return False
    
    def cleanup(self):
        """Clean up all namespaces"""
        print("Cleaning up namespaces...")
        
        namespaces = [self.config.namespace, f"{self.config.namespace}-client"]
        
        for ns in namespaces:
            code, out, err = self.run_cmd(f"ip netns del {ns}", check=False)
            if code == 0:
                print(f"✓ Removed namespace: {ns}")
        
        # Clean up veth interfaces
        self.run_cmd("ip link del veth0 2>/dev/null || true", check=False)
        self.run_cmd("ip link del veth1 2>/dev/null || true", check=False)
    
    def status(self):
        """Show current VPN status"""
        print("\n=== VPN Status ===")
        
        # Check namespaces
        code, out, err = self.run_cmd(f"ip netns list")
        if self.config.namespace in out:
            print(f"✓ Main namespace: {self.config.namespace} (active)")
            
            # Show WireGuard status
            code, wg_out, wg_err = self.run_cmd(f"ip netns exec {self.config.namespace} wg show 2>/dev/null", check=False)
            if wg_out:
                print(f"\nWireGuard Server:")
                print(wg_out)
        else:
            print(f"✗ Main namespace: {self.config.namespace} (not active)")
        
        # Check client namespace
        client_ns = f"{self.config.namespace}-client"
        if client_ns in out:
            print(f"✓ Client namespace: {client_ns} (active)")
        else:
            print(f"⚠ Client namespace: {client_ns} (not active)")
        
        print(f"\nKeys directory: {self.keys_dir}")
        print(f"Config directory: {self.config_dir}")

def main():
    """Main function"""
    print("\n" + "="*60)
    print("SAFE VPN LAB FIXED - No Process Substitution Errors")
    print("="*60)
    
    if len(sys.argv) < 2:
        print("\nUsage: python safe_vpn_fixed.py <command>")
        print("\nCommands:")
        print("  setup     - Create namespace and generate keys")
        print("  start     - Start VPN server and client")
        print("  test      - Test VPN connection")
        print("  status    - Show current status")
        print("  cleanup   - Remove all namespaces")
        print("  demo      - Complete setup + test + demo")
        return
    
    vpn = SafeVPNFixed()
    command = sys.argv[1]
    
    try:
        if command == "setup":
            vpn.create_namespace()
            keys = vpn.generate_keys()
            print(f"\nGenerated Keys:")
            print(f"  Server Public:  {keys.get('server_public', '')[:30]}...")
            print(f"  Client Public:  {keys.get('client_public', '')[:30]}...")
        
        elif command == "start":
            # Load existing keys
            server_priv = (vpn.keys_dir / "server_private.key").read_text().strip()
            server_pub = (vpn.keys_dir / "server_public.key").read_text().strip()
            client_priv = (vpn.keys_dir / "client_private.key").read_text().strip()
            client_pub = (vpn.keys_dir / "client_public.key").read_text().strip()
            
            keys = {
                'server_private': server_priv,
                'server_public': server_pub,
                'client_private': client_priv,
                'client_public': client_pub
            }
            
            vpn.create_namespace()
            vpn.setup_server(keys)
            vpn.setup_client(keys)
            print(f"\n✓ VPN Started!")
            print(f"  Server: {vpn.config.server_ip}:{vpn.config.port}")
            print(f"  Client: {vpn.config.client_ip}")
        
        elif command == "test":
            vpn.test_connection()
        
        elif command == "status":
            vpn.status()
        
        elif command == "cleanup":
            vpn.cleanup()
        
        elif command == "demo":
            print("\n🚀 Running Complete VPN Demo...")
            vpn.create_namespace()
            keys = vpn.generate_keys()
            vpn.setup_server(keys)
            vpn.setup_client(keys)
            time.sleep(1)
            vpn.test_connection()
            print(f"\n✅ Demo Complete! VPN is working in isolated namespaces.")
        
        else:
            print(f"Unknown command: {command}")
    
    except KeyboardInterrupt:
        print(f"\n⚠ Interrupted by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
    finally:
        if command != "cleanup":
            print(f"\nTip: Run 'python safe_vpn_fixed.py cleanup' to remove namespaces")

if __name__ == "__main__":
    main()
