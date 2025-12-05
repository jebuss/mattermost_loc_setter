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
from datetime import datetime
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib

# --- CONFIGURATION LOADING ---
CONFIG = {}
CONFIG_PATH = Path.home() / ".config" / "mm-status" / "config.toml"

if CONFIG_PATH.is_file():
    with open(CONFIG_PATH, "rb") as f:
        CONFIG = tomllib.load(f)
else:
    # Create the directory if it doesn't exist for the user's convenience
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

# Helper to get config with priority: Environment Variable > Config File > Default
def get_config_value(key, default=None, section=None):
    env_var = f"MM_{key.upper()}"
    if env_var in os.environ:
        return os.environ[env_var]
    
    if section:
        return CONFIG.get(section, {}).get(key, default)
    
    return CONFIG.get(key, default)

# --- CONFIGURATION VALUES ---
MATTERMOST_URL = get_config_value("url", "https://your-mattermost-server.com")
ACCESS_TOKEN = get_config_value("access_token")
USER_ID = get_config_value("user_id")

# Load the list of networks
CONFIGURED_NETWORKS = get_config_value("networks", [])

# Load working hours configuration
WORKING_DAYS = get_config_value("weekdays", [0, 1, 2, 3, 4], section="working_hours")
start_time_str = get_config_value("start_time", "8:00", section="working_hours")
end_time_str = get_config_value("end_time", "18:00", section="working_hours")

# Helper function to parse time strings
def parse_time_string(time_str, default_hour=0, default_minute=0):
    """Parse a time string in format 'HH:MM' and return (hour, minute) tuple."""
    if not time_str:
        return (default_hour, default_minute)
    
    try:
        parts = time_str.split(':')
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        return (hour, minute)
    except (ValueError, IndexError) as e:
        logger.warning(f"⚠️  Invalid time format '{time_str}', using default {default_hour}:{default_minute:02d}")
        return (default_hour, default_minute)

WORKING_START_HOUR, WORKING_START_MINUTE = parse_time_string(start_time_str, 8, 0)
WORKING_END_HOUR, WORKING_END_MINUTE = parse_time_string(end_time_str, 18, 0)

# Force IPv4 for all connections
_orig_create_connection = connection.create_connection

def patched_create_connection(address, *args, **kwargs):
    """Wrap urllib3's create_connection to force IPv4."""
    host, port = address
    hostname = sock.gethostbyname(host)
    return _orig_create_connection((hostname, port), *args, **kwargs)

connection.create_connection = patched_create_connection

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Mattermost location status setter."""
    if not all([ACCESS_TOKEN, USER_ID]):
        logger.error("❌ Environment variables MM_ACCESS_TOKEN and MM_USER_ID must be set.")
        sys.exit(1)
    pass


def get_local_ip():
    """Get the local IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip


def _set_mattermost_custom_status(message, emoji="house", retries=3, delay=5):
    """Internal function to update Mattermost custom status (emoji + text)."""
    logger.info(f"🔄 Setting status: {message} (emoji: {emoji})")
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    url = f"{MATTERMOST_URL}/api/v4/users/{USER_ID}/status/custom"
    payload = {"emoji": emoji, "text": message, "durartion": "today"}
    for attempt in range(retries):
        try:
            response = requests.put(url, json=payload, headers=headers, timeout=10, verify=True)
            if response.status_code in (200, 201):
                logger.info(f"✅ Custom status set to: {message}")
                return
            else:
                logger.error(f"❌ Failed to set custom status: {response.status_code}, {response.text}")
                return
        except Exception as e:
            logger.error(f"❗ Unexpected error on attempt {attempt+1} ({type(e).__name__}): {e}")
            if attempt < retries - 1:
                logger.warning(f"⚠️  Retrying in {delay}s...")
                time.sleep(delay)
            else:
                logger.error(f"❌ Failed after {retries} attempts")
                return

def set_mattermost_custom_status(message, emoji):
    """Update Mattermost custom status (emoji + text)."""
    _set_mattermost_custom_status(message, emoji)

def _clear_mattermost_custom_status():
    """Internal function to clear Mattermost custom status."""
    headers = {"Accept": "application/json", "Authorization": f"Bearer {ACCESS_TOKEN}"}
    url = f"{MATTERMOST_URL}/api/v4/users/me/status/custom"
    try:
        response = requests.delete(url, headers=headers, timeout=10)
        if response.status_code == 200:
            logger.info("✅ Custom status cleared")
        else:
            logger.error(f"❌ Failed to clear custom status: {response.status_code}, {response.text}")
    except Exception as e:
        logger.error(f"❌ Failed to clear custom status: {e}")

@cli.command('clear')
def clear_mattermost_custom_status_command():
    """Clear Mattermost custom status."""
    _clear_mattermost_custom_status()


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

def zoom_in_meeting():
    """Check if Zoom is actively connected (likely in a meeting)."""
    for proc in psutil.process_iter(['name']):
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
                if are_ports_connected_any(conns, ports=[3478, 3479, 3480, 3481]):
                    return True
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
    return False

def check_mattermost_reachable(timeout=5, retries=1):
    """Check if Mattermost server is reachable."""
    for attempt in range(retries):
        try:
            response = requests.get(f"{MATTERMOST_URL}/api/v4/system/ping", timeout=timeout, verify=True)
            if response.status_code == 200:
                return True
        except Exception:
            if attempt < retries - 1:
                time.sleep(3)
    return False

def check_network_route(hostname, port=443):
    """Check if we can establish a basic TCP connection using IPv4."""
    try:
        ipv4_address = sock.gethostbyname(hostname.replace('https://', ''))
        s = sock.socket(sock.AF_INET, sock.SOCK_STREAM)
        s.settimeout(5)
        result = s.connect_ex((ipv4_address, port))
        s.close()
        return result == 0
    except Exception:
        return False

@cli.command('auto')
def auto_update():
    """Automatically update status based on location and meeting state."""
    now = datetime.now()
    
    if now.weekday() not in WORKING_DAYS:
        logger.debug(f"⏸️  Today ({now.strftime('%A')}) is not a working day - skipping.")
        sys.exit(0)
    
    # Check working hours with minutes
    start_time = now.replace(hour=WORKING_START_HOUR, minute=WORKING_START_MINUTE, second=0, microsecond=0)
    end_time = now.replace(hour=WORKING_END_HOUR, minute=WORKING_END_MINUTE, second=0, microsecond=0)
    
    if now < start_time or now >= end_time:
        logger.debug(f"⏸️  Outside working hours ({start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}) - skipping.")
        sys.exit(0)

    logger.info("=" * 60)
    logger.info("🚀 Starting automatic status update")

    if not check_network_route(MATTERMOST_URL):
        logger.warning("⚠️  Cannot establish TCP connection to Mattermost server. Skipping.")
        sys.exit(0)

    if not check_mattermost_reachable():
        logger.warning("⚠️  Mattermost server not reachable. Skipping.")
        sys.exit(0)

    logger.info("✅ Mattermost server is reachable")
    ip = get_local_ip()
    zoom = zoom_in_meeting()
    teams = teams_in_meeting()

    logger.info(f"🌐 My local IP: {ip}")
    logger.info(f'{"📹" if zoom else "❌"} Zoom meeting: {"Yes" if zoom else "No"}')
    logger.info(f'{"💼" if teams else "❌"} Teams meeting: {"Yes" if teams else "No"}')

    if zoom:
        _set_mattermost_custom_status("In a Zoom Meeting", "zoom")
    elif teams:
        _set_mattermost_custom_status("In a Teams Meeting", "microsoft_teams")
    else:
        location_found = False
        for network in CONFIGURED_NETWORKS:
            if ip.startswith(network.get("ip_prefix", "")):
                _set_mattermost_custom_status(network.get("name"), network.get("emoji"))
                location_found = True
                break

        if not location_found:
            logger.info("ℹ️  Unknown location, clearing status")
            _clear_mattermost_custom_status()
    
    logger.info("✅ Status update completed")

@cli.command('test')
def test_connection():
    """Test connection to Mattermost server."""
    logger.info("=" * 60)
    logger.info("🧪 Testing connection")
    hostname = MATTERMOST_URL.replace('https://', '')
    
    try:
        ipv4 = sock.gethostbyname(hostname)
        logger.info(f"✅ DNS IPv4: {hostname} -> {ipv4}")
    except Exception as e:
        logger.error(f"❌ DNS failed: {e}")
        return

    if check_network_route(hostname):
        logger.info("✅ TCP connection works")
    else:
        logger.error("❌ TCP connection failed")
        return

    if check_mattermost_reachable(retries=1):
        logger.info("✅ HTTPS connection works")
    else:
        logger.error("❌ HTTPS connection failed")