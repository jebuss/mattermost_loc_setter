"""Network connectivity checks and utilities."""
import socket as sock
import time
import requests
from mm_loc_setter.config import MATTERMOST_URL
from mm_loc_setter.logging_setup import logger
from urllib3.util import connection


def get_local_ip() -> str:
    """Get the local IP address.
    
    Returns:
        Local IPv4 address
    """
    s = sock.socket(sock.AF_INET, sock.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip


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
