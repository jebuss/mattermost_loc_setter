"""Network connectivity checks and utilities."""
import socket as sock
import subprocess
import time
import requests
from urllib3.util import connection
from mm_loc_setter.config import MATTERMOST_URL


def get_local_ip() -> str:
    """Get the local network IP address (excludes VPN).
    
    Returns:
        Local network IPv4 address
    """
    try:
        # Use ifconfig to get all network interfaces
        result = subprocess.run(
            ["ifconfig"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False
        )
        
        lines = result.stdout.split('\n')
        
        for line in lines:
            # Extract IPv4 address from inet lines
            if 'inet ' in line:
                parts = line.strip().split()
                if len(parts) >= 2 and parts[0] == 'inet':
                    ip = parts[1]
                    # Skip loopback addresses
                    if not ip.startswith('127.'):
                        return ip
        
        return "127.0.0.1"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return "127.0.0.1"


def check_mattermost_reachable(timeout: int = 5, retries: int = 1) -> bool:
    """Check if Mattermost server is reachable.
    
    Args:
        timeout: Timeout in seconds
        retries: Number of retry attempts
        
    Returns:
        True if server is reachable
    """
    for attempt in range(retries):
        try:
            response = requests.get(f"{MATTERMOST_URL}/api/v4/system/ping", timeout=timeout, verify=True)
            if response.status_code == 200:
                return True
        except (requests.RequestException, OSError):
            if attempt < retries - 1:
                time.sleep(3)
    return False


def check_network_route(hostname: str, port: int = 443) -> bool:
    """Check if we can establish a basic TCP connection using IPv4.
    
    Args:
        hostname: Hostname or URL
        port: Port to connect to
        
    Returns:
        True if connection is possible
    """
    try:
        ipv4_address = sock.gethostbyname(hostname.replace('https://', ''))
        s = sock.socket(sock.AF_INET, sock.SOCK_STREAM)
        s.settimeout(5)
        result = s.connect_ex((ipv4_address, port))
        s.close()
        return result == 0
    except (OSError, ValueError):
        return False


def setup_ipv4_enforcement():
    """Force IPv4 for all connections (useful to avoid IPv6 issues)."""
    _orig_create_connection = connection.create_connection

    def patched_create_connection(address, *args, **kwargs):
        """Wrap urllib3's create_connection to force IPv4."""
        host, port = address
        hostname = sock.gethostbyname(host)
        return _orig_create_connection((hostname, port), *args, **kwargs)

    connection.create_connection = patched_create_connection
