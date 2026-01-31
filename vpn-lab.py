#!/usr/bin/env python3
import click
import subprocess
import os
from pathlib import Path

@click.group()
def cli():
    """VPN Lab - Safe VPN testing environment"""
    pass

@cli.command()
def init():
    """Initialize VPN Lab"""
    click.echo("Initializing VPN Lab...")
    
    # Create directories
    Path("/opt/vpn-lab/keys").mkdir(parents=True, exist_ok=True)
    Path("/opt/vpn-lab/config").mkdir(parents=True, exist_ok=True)
    
    click.echo("✓ Directories created")
    click.echo("  /opt/vpn-lab/keys")
    click.echo("  /opt/vpn-lab/config")

@cli.command()
@click.argument('name', default='vpn1')
def create(name):
    """Create a new VPN namespace"""
    click.echo(f"Creating VPN: {name}")
    
    # Create namespace
    subprocess.run(["sudo", "ip", "netns", "add", name], check=False)
    subprocess.run(["sudo", "ip", "netns", "exec", name, "ip", "link", "set", "lo", "up"])
    
    click.echo(f"✓ Namespace '{name}' created")
    click.echo(f"  Use: sudo ip netns exec {name} <command>")

@cli.command()
def list():
    """List all VPN namespaces"""
    click.echo("Active VPN Namespaces:")
    result = subprocess.run(["sudo", "ip", "netns", "list"], capture_output=True, text=True)
    if result.stdout:
        for ns in result.stdout.strip().split():
            click.echo(f"  • {ns}")
    else:
        click.echo("  No active namespaces")

@cli.command()
@click.argument('name')
def delete(name):
    """Delete a VPN namespace"""
    click.echo(f"Deleting VPN: {name}")
    subprocess.run(["sudo", "ip", "netns", "del", name], check=False)
    click.echo(f"✓ Namespace '{name}' deleted")

@cli.command()
def clean():
    """Clean all VPN namespaces"""
    click.echo("Cleaning all VPN namespaces...")
    result = subprocess.run(["sudo", "ip", "netns", "list"], capture_output=True, text=True)
    if result.stdout:
        for ns in result.stdout.strip().split():
            subprocess.run(["sudo", "ip", "netns", "del", ns], check=False)
            click.echo(f"  Deleted: {ns}")
    click.echo("✓ All namespaces cleaned")

@cli.command()
@click.argument('namespace')
@click.argument('command', nargs=-1)
def exec(namespace, command):
    """Execute command in VPN namespace"""
    cmd = ["sudo", "ip", "netns", "exec", namespace] + list(command)
    subprocess.run(cmd)

@cli.command()
def demo():
    """Run a complete VPN demo"""
    click.echo("🚀 Running VPN Demo...")
    
    # Create demo namespace
    subprocess.run(["sudo", "ip", "netns", "add", "demo-vpn"], check=False)
    subprocess.run(["sudo", "ip", "netns", "exec", "demo-vpn", "ip", "link", "set", "lo", "up"])
    
    click.echo("✓ Created 'demo-vpn' namespace")
    click.echo("\nNow you can:")
    click.echo("  1. Run commands in the namespace:")
    click.echo("     sudo ip netns exec demo-vpn bash")
    click.echo("  2. Create WireGuard interfaces safely")
    click.echo("  3. Test without affecting your main system")
    click.echo("\nTo clean up: sudo ip netns del demo-vpn")

if __name__ == '__main__':
    cli()
