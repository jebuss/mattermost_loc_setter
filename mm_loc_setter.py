# %%
import socket
import requests
import psutil
import logging
import click
import time
import sys
import os
import socket as sock
from requests.adapters import HTTPAdapter
from urllib3.util import connection

# Force IPv4 for all connections
_orig_create_connection = connection.create_connection

def patched_create_connection(address, *args, **kwargs):
    """Wrap urllib3's create_connection to force IPv4."""
    host, port = address
    # Force IPv4 by resolving to IPv4 address only
    hostname = sock.gethostbyname(host)
    return _orig_create_connection((hostname, port), *args, **kwargs)

connection.create_connection = patched_create_connection

# Debug: Log environment when running
logger_early = logging.getLogger(__name__)
if os.environ.get('PYTHONUNBUFFERED'):  # Typically set by some cron setups
    logger_early.info(f"Running in non-interactive mode")
    logger_early.info(f"HOME: {os.environ.get('HOME', 'NOT SET')}")
    logger_early.info(f"USER: {os.environ.get('USER', 'NOT SET')}")


# %%
# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

logger.info("🔧 Forced IPv4 connections for all HTTP requests")

# %%
# === CONFIGURATION ===
MATTERMOST_URL = "https://chat.lamarr-institute.org"  # Your Mattermost server
ACCESS_TOKEN = ""
USER_ID = ""  # You can get this via /api/v4/users/me

# Define IP ranges for office vs home
OFFICE_SUBNET = "129.217.30."   # Example office LAN prefix
TUDO_SUBNET = "172.31.118."   # Example home LAN prefix
HOME_SUBNET = "192.168.178."   # Example home LAN prefix

# Status messages
STATUS_HOME = {"status": "online", "dnd_end_time": 0, "manual": True, "message": "Home Office"}
STATUS_OFFICE = {"status": "online", "dnd_end_time": 0, "manual": True, "message": "In Office"}


# %%
@click.group()
def cli():
    """Mattermost location status setter."""
    pass


# %%
def get_local_ip():
    """Get the local IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # connect to a dummy address just to get the IP
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip

# %%
def _set_mattermost_custom_status(message, emoji="house", retries=3, delay=5):
    """Internal function to update Mattermost custom status (emoji + text)."""
    logger.info(f"🔄 Setting status: {message} (emoji: {emoji})")
    
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    url = f"{MATTERMOST_URL}/api/v4/users/{USER_ID}/status/custom"
    payload = {
        "emoji": emoji,
        "text": message,
        "durartion": "today",
    }
    
    for attempt in range(retries):
        try:
            logger.debug(f"🔍 Attempt {attempt + 1}/{retries} - Connecting to {url}")
            response = requests.put(url, json=payload, headers=headers, timeout=10, verify=True)
            logger.debug(f"🔍 Response: {response.status_code}")
            
            if response.status_code in (200, 201):
                logger.info(f"✅ Custom status set to: {message}")
                return
            else:
                logger.error(f"❌ Failed to set custom status: {response.status_code}, {response.text}")
                return
        except requests.exceptions.SSLError as e:
            logger.error(f"🔐 SSL Error: {e}. This might be a certificate issue in cron environment.")
            if attempt < retries - 1:
                logger.warning(f"⚠️  Retrying in {delay}s...")
                time.sleep(delay)
            else:
                logger.error(f"❌ Failed after {retries} attempts due to SSL errors")
                return
        except requests.exceptions.ConnectionError as e:
            logger.error(f"🌐 Connection Error: {e}")
            if attempt < retries - 1:
                logger.warning(f"⚠️  Retrying in {delay}s...")
                time.sleep(delay)
            else:
                logger.error(f"❌ Failed after {retries} attempts: Cannot connect to server")
                return
        except Exception as e:
            logger.error(f"❗ Unexpected error ({type(e).__name__}): {e}")
            if attempt < retries - 1:
                logger.warning(f"⚠️  Retrying in {delay}s...")
                time.sleep(delay)
            else:
                logger.error(f"❌ Failed after {retries} attempts")
                return

@cli.command('set')
@click.argument('message')
@click.argument('emoji', default='house')
def set_mattermost_custom_status(message, emoji):
    """Update Mattermost custom status (emoji + text)."""
    _set_mattermost_custom_status(message, emoji)

@cli.command('clear')
def clear_mattermost_custom_status():
    """Clear Mattermost custom status."""
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {ACCESS_TOKEN}",
    }
    url = f"{MATTERMOST_URL}/api/v4/users/me/status/custom"
    
    for attempt in range(3):
        try:
            response = requests.delete(url, headers=headers, timeout=10)
            if response.status_code == 200:
                logger.info("✅ Custom status cleared")
                return
            else:
                logger.error(f"❌ Failed to clear custom status: {response.status_code}, {response.text}")
                return
        except (OSError, requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            if attempt < 2:
                logger.warning(f"⚠️  Attempt {attempt + 1}/3 failed: {type(e).__name__}. Retrying in 5s...")
                time.sleep(5)
            else:
                logger.error(f"❌ Failed to clear custom status after 3 attempts: {type(e).__name__}")
                return


def are_ports_connected_any(connections, ports=[8801]):
    def find_ports_in_connection(connection):
        try:
            return connection.raddr.port in ports
        except AttributeError:
            return
    for c in connections:
        if find_ports_in_connection(c):
            return True
    return False

ps=[]
def zoom_in_meeting():
    """Check if Zoom is actively connected (likely in a meeting)."""
    for proc in psutil.process_iter(['name']):
        ps.append(proc)
        try:
            if proc.info['name'] and "zoom" in proc.info['name'].lower():
                conns = proc.net_connections(kind='inet')
                if are_ports_connected_any(conns, ports=[8801]):
                    return True
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
    return False

def teams_in_meeting():
    """Check if MS Teams is actively connected (likely in a meeting)."""
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] and "teams" in proc.info['name'].lower():
                conns = proc.net_connections(kind='inet')
                # Teams uses various ports, commonly 3478-3481 for media
                if are_ports_connected_any(conns, ports=[3478, 3479, 3480, 3481]):
                    return True
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
    return False

# %%
def check_mattermost_reachable(timeout=5, retries=3):
    """Check if Mattermost server is reachable with retries."""
    # First, check DNS resolution
    try:
        hostname = MATTERMOST_URL.replace('https://', '').replace('http://', '')
        ip_address = sock.gethostbyname(hostname)
        logger.info(f"🔍 DNS resolved {hostname} to {ip_address}")
    except sock.gaierror as e:
        logger.error(f"❌ DNS resolution failed for {hostname}: {e}")
        return False
    
    for attempt in range(retries):
        try:
            logger.info(f"🔍 Attempt {attempt + 1}/{retries} - Testing connection to {MATTERMOST_URL}")
            response = requests.get(f"{MATTERMOST_URL}/api/v4/system/ping", timeout=timeout, verify=True)
            logger.info(f"🔍 Response status: {response.status_code}")
            if response.status_code == 200:
                return True
        except requests.exceptions.SSLError as e:
            logger.error(f"🔐 SSL Error: {e}")
            if attempt < retries - 1:
                logger.warning(f"⚠️  Retrying in 3s...")
                time.sleep(3)
        except requests.exceptions.ConnectionError as e:
            logger.error(f"🌐 Connection Error: {e}")
            if attempt < retries - 1:
                logger.warning(f"⚠️  Retrying in 3s...")
                time.sleep(3)
        except requests.exceptions.Timeout as e:
            logger.error(f"⏱️  Timeout Error: {e}")
            if attempt < retries - 1:
                logger.warning(f"⚠️  Retrying in 3s...")
                time.sleep(3)
        except Exception as e:
            logger.error(f"❗ Unexpected error ({type(e).__name__}): {e}")
            if attempt < retries - 1:
                logger.warning(f"⚠️  Retrying in 3s...")
                time.sleep(3)
    return False

# %%
def check_network_route(hostname, port=443):
    """Check if we can establish a basic TCP connection using IPv4."""
    try:
        hostname_clean = hostname.replace('https://', '').replace('http://', '')
        logger.info(f"🔍 Testing raw TCP connection to {hostname_clean}:{port}")
        
        # Force IPv4 resolution
        try:
            ipv4_address = sock.gethostbyname(hostname_clean)
            logger.info(f"🔍 Resolved to IPv4: {ipv4_address}")
        except Exception as e:
            logger.error(f"❌ IPv4 resolution failed: {e}")
            return False
        
        # Create IPv4 socket explicitly
        s = sock.socket(sock.AF_INET, sock.SOCK_STREAM)
        s.settimeout(5)
        
        try:
            result = s.connect_ex((ipv4_address, port))
            s.close()
            
            if result == 0:
                logger.info(f"✅ TCP connection successful to {ipv4_address}")
                return True
            else:
                logger.error(f"❌ TCP connection failed with error code: {result}")
                return False
        except Exception as e:
            logger.error(f"❌ Socket connect failed: {e}")
            s.close()
            return False
            
    except Exception as e:
        logger.error(f"❌ TCP connection test failed: {e}")
        return False

@cli.command('auto')
def auto_update():
    """Automatically update status based on location and meeting state."""
    logger.info("=" * 60)
    logger.info("🚀 Starting automatic status update")
    logger.info(f"🔍 Running as user: {os.environ.get('USER', 'UNKNOWN')}")
    logger.info(f"🔍 Home directory: {os.environ.get('HOME', 'UNKNOWN')}")
    logger.info(f"🔍 Python executable: {sys.executable}")
    
    # Get local IP first
    try:
        ip = get_local_ip()
        logger.info(f"🌐 My local IP: {ip}")
    except Exception as e:
        logger.error(f"❌ Failed to get local IP: {e}")
        sys.exit(1)
    
    # Check basic TCP connectivity
    hostname = MATTERMOST_URL.replace('https://', '').replace('http://', '')
    if not check_network_route(hostname):
        logger.warning("⚠️  Cannot establish TCP connection to Mattermost server.")
        logger.info("💡 This suggests a firewall or network restriction. Skipping status update.")
        sys.exit(0)
    
    # First check if we can reach Mattermost
    logger.info("🔍 Checking Mattermost server reachability...")
    if not check_mattermost_reachable():
        logger.warning("⚠️  Mattermost server not reachable. Skipping status update.")
        logger.info("💡 TCP works but HTTPS fails - might be a certificate or proxy issue.")
        sys.exit(0)
    
    logger.info("✅ Mattermost server is reachable")
    
    zoom = zoom_in_meeting()
    teams = teams_in_meeting()

    logger.info(f'{"📹" if zoom else "❌"} I am in{" not " if not zoom else " "}a zoom meeting')
    logger.info(f'{"💼" if teams else "❌"} I am in{" not " if not teams else " "}a teams meeting')

    if zoom:
        _set_mattermost_custom_status("In a Zoom Meeting", "zoom")
    elif teams:
        _set_mattermost_custom_status("In a Teams Meeting", "microsoft_teams")
    elif ip.startswith(OFFICE_SUBNET):
        _set_mattermost_custom_status("At the Lamarr Institute", "lamarr")
    elif ip.startswith(TUDO_SUBNET):
        _set_mattermost_custom_status("At TU Dortmund", "tu")
    elif ip.startswith(HOME_SUBNET):
        _set_mattermost_custom_status("Home Office", "house")
    else:
        logger.info("ℹ️  Unknown location, clearing status")
        clear_mattermost_custom_status()
    
    logger.info("✅ Status update completed")
    logger.info("=" * 60)
# %%
@cli.command('test')
def test_connection():
    """Test connection to Mattermost server."""
    logger.info("=" * 60)
    logger.info("🧪 Testing connection")
    
    # Test DNS resolution
    hostname = MATTERMOST_URL.replace('https://', '').replace('http://', '')
    try:
        ipv4 = sock.gethostbyname(hostname)
        logger.info(f"✅ DNS IPv4: {hostname} -> {ipv4}")
    except Exception as e:
        logger.error(f"❌ DNS failed: {e}")
        return
    
    # Test TCP
    if check_network_route(hostname):
        logger.info("✅ TCP connection works")
    else:
        logger.error("❌ TCP connection failed")
        return
    
    # Test HTTPS
    if check_mattermost_reachable(retries=1):
        logger.info("✅ HTTPS connection works")
    else:
        logger.error("❌ HTTPS connection failed")
    
    logger.info("=" * 60)
# %%
if __name__ == "__main__":
    cli()
