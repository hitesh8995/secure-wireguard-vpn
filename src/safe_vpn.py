#!/usr/bin/env python3
"""
SAFE VPN MANAGER - Uses network namespaces to avoid system crashes
"""
import os
import sys
import json
import subprocess
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
    dns: str = "8.8.8.8"

class SafeVPN:
    """Main VPN class using network namespaces"""
    
    def __init__(self, config: Optional[VPNConfig] = None):
        self.config = config or VPNConfig()
        self.base_dir = Path("/opt/vpn-lab")
        self.keys_dir = self.base_dir / "keys"
        self.config_dir = self.base_dir / "config"
        self.keys_dir.mkdir(exist_ok=True)
        self.config_dir.mkdir(exist_ok=True)
        
        # Colors for output
        self.GREEN = '\033[92m'
        self.YELLOW = '\033[93m'
        self.RED = '\033[91m'
        self.RESET = '\033[0m'
    
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
            print(f"{self.RED}Command failed: {cmd}{self.RESET}")
            if e.stderr:
                print(f"{self.YELLOW}Error: {e.stderr[:200]}{self.RESET}")
            return e.returncode, e.stdout, e.stderr
    
    def print_status(self, message: str, status: str = "info"):
        """Print colored status messages"""
        if status == "success":
            print(f"{self.GREEN}✓ {message}{self.RESET}")
        elif status == "error":
            print(f"{self.RED}✗ {message}{self.RESET}")
        elif status == "warning":
            print(f"{self.YELLOW}⚠ {message}{self.RESET}")
        else:
            print(f"  {message}")
    
    def create_namespace(self) -> bool:
        """Create isolated network namespace"""
        self.print_status(f"Creating isolated namespace: {self.config.namespace}")
        
        # Clean up any existing namespace
        self.run_cmd(f"ip netns del {self.config.namespace}", check=False)
        
        # Create new namespace
        code, out, err = self.run_cmd(f"ip netns add {self.config.namespace}")
        if code == 0:
            # Bring up loopback
            self.run_cmd(f"ip netns exec {self.config.namespace} ip link set lo up")
            self.print_status(f"Namespace created successfully", "success")
            return True
        else:
            self.print_status(f"Failed to create namespace: {err}", "error")
            return False
    
    def generate_keys(self) -> Dict[str, str]:
        """Generate WireGuard keys"""
        self.print_status("Generating cryptographic keys...")
        
        keys = {}
        
        # Generate server keys
        code, priv, err = self.run_cmd("wg genkey")
        if code == 0:
            keys['server_private'] = priv.strip()
            code2, pub, err2 = self.run_cmd(f"echo '{priv.strip()}' | wg pubkey")
            if code2 == 0:
                keys['server_public'] = pub.strip()
                (self.keys_dir / "server_private.key").write_text(keys['server_private'])
                (self.keys_dir / "server_public.key").write_text(keys['server_public'])
                self.print_status("Server keys generated", "success")
        
        # Generate client keys
        code, priv, err = self.run_cmd("wg genkey")
        if code == 0:
            keys['client_private'] = priv.strip()
            code2, pub, err2 = self.run_cmd(f"echo '{priv.strip()}' | wg pubkey")
            if code2 == 0:
                keys['client_public'] = pub.strip()
                (self.keys_dir / "client_private.key").write_text(keys['client_private'])
                (self.keys_dir / "client_public.key").write_text(keys['client_public'])
                self.print_status("Client keys generated", "success")
        
        return keys
    
    def setup_server(self, keys: Dict[str, str]) -> bool:
        """Setup WireGuard server in namespace"""
        self.print_status("Setting up VPN server...")
        
        # Create WireGuard interface in namespace
        cmds = [
            f"ip netns exec {self.config.namespace} ip link add {self.config.interface} type wireguard",
            f"ip netns exec {self.config.namespace} wg set {self.config.interface} private-key <(echo '{keys['server_private']}')",
            f"ip netns exec {self.config.namespace} wg set {self.config.interface} listen-port {self.config.port}",
            f"ip netns exec {self.config.namespace} wg set {self.config.interface} peer {keys['client_public']} allowed-ips {self.config.client_ip}/32",
            f"ip netns exec {self.config.namespace} ip addr add {self.config.server_ip}/{self.config.subnet} dev {self.config.interface}",
            f"ip netns exec {self.config.namespace} ip link set {self.config.interface} up",
        ]
        
        for cmd in cmds:
            code, out, err = self.run_cmd(cmd)
            if code != 0:
                self.print_status(f"Failed: {cmd}", "error")
                return False
        
        self.print_status(f"Server setup complete: {self.config.server_ip}:{self.config.port}", "success")
        return True
    
    def setup_client(self, keys: Dict[str, str]) -> bool:
        """Setup WireGuard client in separate namespace"""
        client_ns = f"{self.config.namespace}-client"
        
        # Create client namespace
        self.run_cmd(f"ip netns del {client_ns}", check=False)
        code, out, err = self.run_cmd(f"ip netns add {client_ns}")
        if code != 0:
            return False
        
        # Create veth pair to connect namespaces
        veth_cmds = [
            f"ip link add veth0 type veth peer name veth1",
            f"ip link set veth1 netns {client_ns}",
            f"ip link set veth0 netns {self.config.namespace}",
            
            # Configure veth in server namespace
            f"ip netns exec {self.config.namespace} ip addr add 192.168.100.1/24 dev veth0",
            f"ip netns exec {self.config.namespace} ip link set veth0 up",
            
            # Configure veth in client namespace
            f"ip netns exec {client_ns} ip addr add 192.168.100.2/24 dev veth1",
            f"ip netns exec {client_ns} ip link set veth1 up",
            f"ip netns exec {client_ns} ip route add default via 192.168.100.1",
            
            # Setup WireGuard in client namespace
            f"ip netns exec {client_ns} ip link add wg-client type wireguard",
            f"ip netns exec {client_ns} wg set wg-client private-key <(echo '{keys['client_private']}')",
            f"ip netns exec {client_ns} wg set wg-client peer {keys['server_public']} allowed-ips 0.0.0.0/0 endpoint 192.168.100.1:{self.config.port} persistent-keepalive 25",
            f"ip netns exec {client_ns} ip addr add {self.config.client_ip}/{self.config.subnet} dev wg-client",
            f"ip netns exec {client_ns} ip link set wg-client up",
        ]
        
        for cmd in veth_cmds:
            self.run_cmd(cmd, check=False)
        
        self.print_status(f"Client setup complete in namespace: {client_ns}", "success")
        return True
    
    def test_connection(self) -> bool:
        """Test VPN connection"""
        self.print_status("Testing VPN connection...")
        
        client_ns = f"{self.config.namespace}-client"
        
        # Wait for connection
        time.sleep(2)
        
        # Test ping
        self.print_status(f"Pinging server ({self.config.server_ip}) from client...")
        code, out, err = self.run_cmd(
            f"ip netns exec {client_ns} ping -c 3 -W 1 {self.config.server_ip}",
            check=False
        )
        
        if code == 0 and "64 bytes" in out:
            self.print_status("Ping successful! VPN is working.", "success")
            
            # Show statistics
            print("\n" + "="*50)
            print("VPN CONNECTION STATISTICS")
            print("="*50)
            
            print(f"\nServer WireGuard Status:")
            self.run_cmd(f"ip netns exec {self.config.namespace} wg show")
            
            print(f"\nClient WireGuard Status:")
            self.run_cmd(f"ip netns exec {client_ns} wg show")
            
            print(f"\nServer Interface:")
            self.run_cmd(f"ip netns exec {self.config.namespace} ip addr show {self.config.interface}")
            
            print(f"\nClient Interface:")
            self.run_cmd(f"ip netns exec {client_ns} ip addr show wg-client")
            
            return True
        else:
            self.print_status("Ping failed. Check configuration.", "error")
            return False
    
    def cleanup(self):
        """Clean up all namespaces"""
        self.print_status("Cleaning up namespaces...")
        
        namespaces = [self.config.namespace, f"{self.config.namespace}-client"]
        
        for ns in namespaces:
            code, out, err = self.run_cmd(f"ip netns del {ns}", check=False)
            if code == 0:
                self.print_status(f"Removed namespace: {ns}", "success")
        
        # Clean up veth interfaces
        self.run_cmd("ip link del veth0 2>/dev/null || true", check=False)
        self.run_cmd("ip link del veth1 2>/dev/null || true", check=False)
    
    def status(self):
        """Show current VPN status"""
        print(f"\n{self.YELLOW}=== VPN Status ==={self.RESET}")
        
        # Check namespaces
        code, out, err = self.run_cmd(f"ip netns list")
        if self.config.namespace in out:
            print(f"{self.GREEN}✓ Main namespace: {self.config.namespace} (active){self.RESET}")
            
            # Show WireGuard status
            code, wg_out, wg_err = self.run_cmd(f"ip netns exec {self.config.namespace} wg show 2>/dev/null", check=False)
            if wg_out:
                print(f"\nWireGuard Server:")
                print(wg_out)
        else:
            print(f"{self.RED}✗ Main namespace: {self.config.namespace} (not active){self.RESET}")
        
        # Check client namespace
        client_ns = f"{self.config.namespace}-client"
        if client_ns in out:
            print(f"{self.GREEN}✓ Client namespace: {client_ns} (active){self.RESET}")
        else:
            print(f"{self.YELLOW}⚠ Client namespace: {client_ns} (not active){self.RESET}")
        
        print(f"\n{self.YELLOW}Keys directory: {self.keys_dir}{self.RESET}")
        print(f"{self.YELLOW}Config directory: {self.config_dir}{self.RESET}")

def main():
    """Main function"""
    print("\n" + "="*60)
    print("SAFE VPN LAB - Network Namespace Isolation")
    print("="*60)
    
    if len(sys.argv) < 2:
        print("\nUsage: python safe_vpn.py <command>")
        print("\nCommands:")
        print("  setup     - Create namespace and generate keys")
        print("  start     - Start VPN server and client")
        print("  test      - Test VPN connection")
        print("  status    - Show current status")
        print("  cleanup   - Remove all namespaces")
        print("  demo      - Complete setup + test + demo")
        return
    
    vpn = SafeVPN()
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
            print(f"\n{vpn.GREEN}✓ VPN Started!{vpn.RESET}")
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
            print(f"\n{vpn.GREEN}✅ Demo Complete! VPN is working in isolated namespaces.{vpn.RESET}")
        
        else:
            print(f"Unknown command: {command}")
    
    except KeyboardInterrupt:
        print(f"\n{vpn.YELLOW}⚠ Interrupted by user{vpn.RESET}")
    except Exception as e:
        print(f"\n{vpn.RED}✗ Error: {e}{vpn.RESET}")
    finally:
        if command != "cleanup":
            print(f"\n{vpn.YELLOW}Tip: Run 'python safe_vpn.py cleanup' to remove namespaces{vpn.RESET}")

if __name__ == "__main__":
    main()
