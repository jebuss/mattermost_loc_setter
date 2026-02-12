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

def _fetch_user_id_from_api(retries=3, delay=2):
    """Fetch user_id from Mattermost API using /api/v4/users/me endpoint."""
    if not ACCESS_TOKEN:
        return None
    
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {ACCESS_TOKEN}",
    }
    url = f"{MATTERMOST_URL}/api/v4/users/me"
    
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=10, verify=True)
            if response.status_code == 200:
                user_data = response.json()
                fetched_id = user_data.get("id")
                if fetched_id:
                    return fetched_id
            else:
                logger.debug(f"Failed to fetch user_id: {response.status_code}, {response.text}")
        except Exception as e:
            logger.debug(f"Error fetching user_id on attempt {attempt+1}: {e}")
        
        if attempt < retries - 1:
            import time as time_module
            time_module.sleep(delay)
    
    return None

# Fetch user_id from API if not configured
if not USER_ID:
    USER_ID = _fetch_user_id_from_api()

# Load the list of networks
CONFIGURED_NETWORKS = get_config_value("networks", [])

# Load absence periods
ABSENCE_PERIODS = get_config_value("absence_periods", [])

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

# Allow overriding log level via env var MM_LOG_LEVEL (e.g., DEBUG)
_env_log_level = os.getenv("MM_LOG_LEVEL", "").upper()
if _env_log_level in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
    logger.setLevel(getattr(logging, _env_log_level))


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


def parse_dnd_end_time(time_input):
    """Parse DND end time from various formats to Unix timestamp.
    
    Supported formats:
    - Unix timestamp (integer): 1703001600
    - ISO 8601: "2025-12-18T10:30:00", "2025-12-18T10:30:00Z"
    - Relative time: "10m", "1h", "30s" (from now)
    
    Returns:
        Unix timestamp (int) or None if parsing fails
    """
    if time_input is None:
        return None
    
    try:
        # Try to parse as integer (Unix timestamp)
        if isinstance(time_input, int):
            return time_input
        
        time_input = str(time_input).strip()
        
        # Check for relative time format (e.g., "10m", "1h", "30s")
        if time_input[-1] in ['m', 'h', 's', 'd']:
            unit = time_input[-1]
            value = int(time_input[:-1])
            now = time.time()
            
            if unit == 's':
                return int(now + value)
            elif unit == 'm':
                return int(now + value * 60)
            elif unit == 'h':
                return int(now + value * 3600)
            elif unit == 'd':
                return int(now + value * 86400)
        
        # Try to parse as ISO 8601 format
        # Handle both with and without 'Z' suffix
        iso_str = time_input.replace('Z', '+00:00')
        
        # Try different ISO formats
        for fmt in [
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d"
        ]:
            try:
                if '+' in iso_str or '-' in iso_str.split('T')[-1]:
                    # Has timezone info
                    dt = datetime.fromisoformat(iso_str)
                else:
                    # No timezone info, treat as local time
                    dt = datetime.strptime(time_input, fmt)
                
                # Convert to Unix timestamp
                return int(dt.timestamp())
            except (ValueError, AttributeError):
                continue
        
        # Try to parse as integer (in case it's a string representation)
        return int(time_input)
    
    except (ValueError, TypeError) as e:
        logger.warning(f"⚠️  Failed to parse DND end time '{time_input}': {e}")
        return None


def _set_mattermost_custom_status(message, emoji="house", duration=None, expires_at=None, retries=3, delay=5):
    """Internal function to update Mattermost custom status (emoji + text),
    trying compatible payloads across Mattermost versions.

    Args:
        message: Custom status message text
        emoji: Emoji name for the status
        duration: How long the custom status should last (e.g., "today", "four_hours")
        expires_at: When the custom status should expire (Unix timestamp, ISO 8601, or relative like "1h")
        retries: Number of retry attempts
        delay: Delay in seconds between retries
    """
    logger.info(f"🔄 Setting status: {message} (emoji: {emoji})")
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    # Some Mattermost servers require explicit user_id in the URL
    url = f"{MATTERMOST_URL}/api/v4/users/{USER_ID}/status/custom"

    # Build base fields
    def _normalize_emoji_name(name: str) -> str:
        aliases = {
            # Common alias mapping to Twemoji names
            "utensils": "fork_and_knife",
        }
        return aliases.get(name, name)

    base = {"emoji": _normalize_emoji_name(emoji), "text": message}

    # Optional duration as-is (server validates allowed values)
    if duration:
        base["duration"] = duration

    # Parse and format expires_at as ISO string if provided
    if expires_at:
        parsed_expires_at = parse_dnd_end_time(expires_at)
        if parsed_expires_at is None:
            logger.error(f"❌ Failed to parse expires_at: {expires_at}")
            return False
        expires_iso = datetime.utcfromtimestamp(parsed_expires_at).strftime('%Y-%m-%dT%H:%M:%SZ')
        base["expires_at"] = expires_iso
        logger.info(f"   Duration: {duration}, Expires at: {expires_iso}")
    elif duration:
        logger.info(f"   Duration: {duration}")

    payload = dict(base)

    for attempt in range(retries):
        try:
            logger.debug(f"Trying PUT {url} with payload: {payload}")
            response = requests.put(url, json=payload, headers=headers, timeout=10, verify=True)
            if response.status_code in (200, 201):
                logger.info(f"✅ Custom status set to: {message}")
                return True

            # Improve error reporting and guidance
            text = response.text
            try:
                data = response.json()
            except Exception:
                data = {}

            err_id = data.get("id", "")
            if err_id == "api.custom_status.set_custom_statuses.emoji_not_found":
                logger.error("❌ Emoji not found. Try a valid emoji name (e.g., 'fork_and_knife' instead of 'utensils').")
            elif err_id == "api.context.invalid_body_param.app_error":
                logger.error("❌ Server rejected payload. This server expects a root-level custom status payload with fields 'emoji', 'text', and optional 'expires_at' as ISO.")
            else:
                logger.error(f"❌ Failed to set custom status: {response.status_code}, {text}")
        except Exception as e:
            logger.error(f"❗ Unexpected error on attempt {attempt+1} ({type(e).__name__}): {e}")

        if attempt < retries - 1:
            logger.warning(f"⚠️  Retrying in {delay}s...")
            time.sleep(delay)
        else:
            logger.error(f"❌ Failed after {retries} attempts")
            return False

@cli.command('custom')
@click.argument('message')
@click.argument('emoji', default='house')
@click.option('--duration', type=str, default=None, help='How long the custom status should last (e.g., "30m", "1h", "today")')
@click.option('--expires-at', type=str, default=None, help='When the custom status should expire (Unix timestamp, ISO 8601, or relative like "1h")')
def set_mattermost_custom_status(message, emoji, duration, expires_at):
    """Update Mattermost custom status (emoji + text).
    
    Examples:
        mm-status custom "In a meeting" zoom
        mm-status custom "Working from home" house --duration "1h"
        mm-status custom "At lunch" utensils --expires-at "30m"
        mm-status custom "Away" palm_tree --duration "today"
        mm-status custom "Busy" hourglass --expires-at "2025-12-18T17:00:00"
    """
    success = _set_mattermost_custom_status(message, emoji, duration=duration, expires_at=expires_at)
    if not success:
        sys.exit(1)

def _set_mattermost_status(status, dnd_end_time=None, retries=3, delay=5):
    """Internal function to update Mattermost presence status (online, away, dnd, offline).
    
    Args:
        status: One of 'online', 'away', 'dnd', 'offline'
        dnd_end_time: Optional DND end time in various formats:
            - Unix timestamp (int): 1703001600
            - ISO 8601: "2025-12-18T10:30:00" or "2025-12-18T10:30:00Z"
            - Relative time: "10m", "1h", "30s", "1d" (from now)
        retries: Number of retry attempts
        delay: Delay in seconds between retries
    """
    valid_statuses = ["online", "away", "dnd", "offline"]
    if status not in valid_statuses:
        logger.error(f"❌ Invalid status '{status}'. Must be one of: {', '.join(valid_statuses)}")
        return False
    
    # Parse dnd_end_time if provided
    parsed_dnd_end_time = None
    if dnd_end_time and status == "dnd":
        parsed_dnd_end_time = parse_dnd_end_time(dnd_end_time)
        if parsed_dnd_end_time is None:
            logger.error(f"❌ Failed to parse DND end time: {dnd_end_time}")
            return False
    
    log_msg = f"🔄 Setting status: {status}"
    if parsed_dnd_end_time and status == "dnd":
        dnd_dt = datetime.fromtimestamp(parsed_dnd_end_time)
        log_msg += f" (DND end time: {dnd_dt.isoformat()})"
    logger.info(log_msg)
    
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    url = f"{MATTERMOST_URL}/api/v4/users/{USER_ID}/status"
    payload = {"user_id": USER_ID, "status": status}
    
    if parsed_dnd_end_time and status == "dnd":
        payload["dnd_end_time"] = parsed_dnd_end_time
    
    for attempt in range(retries):
        try:
            response = requests.put(url, json=payload, headers=headers, timeout=10, verify=True)
            if response.status_code in (200, 201):
                logger.info(f"✅ Status set to: {status}")
                return True
            else:
                logger.error(f"❌ Failed to set status: {response.status_code}, {response.text}")
                return False
        except Exception as e:
            logger.error(f"❗ Unexpected error on attempt {attempt+1} ({type(e).__name__}): {e}")
            if attempt < retries - 1:
                logger.warning(f"⚠️  Retrying in {delay}s...")
                time.sleep(delay)
            else:
                logger.error(f"❌ Failed after {retries} attempts")
                return False

@cli.command('set')
@click.argument('status', type=click.Choice(['online', 'away', 'dnd', 'offline']))
@click.option('--dnd-end-time', type=str, default=None, help='DND end time (Unix timestamp, ISO 8601, or relative like "1h", "30m")')
def set_mattermost_status_command(status, dnd_end_time):
    """Update Mattermost presence status (online, away, dnd, offline).
    
    Examples:
        mm-status set online
        mm-status set dnd --dnd-end-time 1703001600
        mm-status set dnd --dnd-end-time "2025-12-18T10:30:00"
        mm-status set dnd --dnd-end-time "1h"
        mm-status set dnd --dnd-end-time "30m"
    """
    success = _set_mattermost_status(status, dnd_end_time=dnd_end_time)
    if not success:
        sys.exit(1)

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


@cli.command('userid')
def fetch_user_id_command():
    """Fetch and display the user_id from Mattermost API."""
    if not ACCESS_TOKEN:
        logger.error("❌ MM_ACCESS_TOKEN must be set.")
        sys.exit(1)
    
    fetched_id = _fetch_user_id_from_api(retries=3, delay=2)
    if fetched_id:
        logger.info(f"✅ User ID fetched successfully: {fetched_id}")
        click.echo(fetched_id)
    else:
        logger.error("❌ Failed to fetch user ID from Mattermost API")
        sys.exit(1)


def are_ports_connected_any(connections, ports=[8801]):
    """Check if any connection uses one of the specified ports."""
    return any(
        getattr(getattr(conn, 'raddr', None), 'port', None) in ports
        for conn in connections
    )

def is_in_meeting(process_name, ports):
    """Generic function to check if a process is in a meeting based on network connections."""
    try:
        for proc in psutil.process_iter(['name']):
            proc_name = proc.info.get('name', '').lower()
            if process_name in proc_name:
                try:
                    conns = proc.net_connections(kind='inet')
                    if are_ports_connected_any(conns, ports=ports):
                        return True
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    continue
    except Exception as e:
        logger.debug(f"Error checking {process_name} meeting status: {e}")
    return False

def zoom_in_meeting():
    """Check if Zoom is actively connected (likely in a meeting)."""
    return is_in_meeting('zoom', ports=[8801, 8802, 8803])

def teams_in_meeting():
    """Check if MS Teams is actively connected (likely in a meeting)."""
    return is_in_meeting('teams', ports=[3478, 3479, 3480, 3481])

def webex_in_meeting():
    """Check if Webex is actively connected (likely in a meeting)."""
    return is_in_meeting('webex', ports=[5004, 5005, 9000, 9001])

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

def parse_absence_datetime(time_str):
    """Parse datetime string for absence periods.
    
    Supports formats:
    - "YYYY-MM-DD" (assumes 00:00:00 for start, 23:59:59 for end)
    - "YYYY-MM-DDTHH:MM:SS"
    - "YYYY-MM-DD HH:MM:SS"
    
    Returns:
        datetime object or None if parsing fails
    """
    if not time_str:
        return None
    
    try:
        time_str = str(time_str).strip()
        
        # Try different formats
        for fmt in [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ]:
            try:
                return datetime.strptime(time_str, fmt)
            except ValueError:
                continue
        
        logger.warning(f"⚠️  Could not parse datetime: {time_str}")
        return None
    except Exception as e:
        logger.warning(f"⚠️  Error parsing datetime '{time_str}': {e}")
        return None

def get_active_absence_period():
    """Check if current time falls within any configured absence period.
    
    Returns:
        dict with 'status' and 'emoji' keys if in absence period, None otherwise
    """
    if not ABSENCE_PERIODS:
        return None
    
    now = datetime.now()
    
    for period in ABSENCE_PERIODS:
        start_str = period.get("start_time")
        end_str = period.get("end_time")
        
        if not start_str or not end_str:
            logger.warning(f"⚠️  Absence period '{period.get('name', 'unnamed')}' missing start_time or end_time")
            continue
        
        start_time = parse_absence_datetime(start_str)
        end_time = parse_absence_datetime(end_str)
        
        if not start_time or not end_time:
            continue
        
        # If only date is provided for end_time, set to end of day
        if end_str and 'T' not in end_str and ' ' not in end_str:
            end_time = end_time.replace(hour=23, minute=59, second=59)
        
        # Check if current time is within the period
        if start_time <= now <= end_time:
            status = period.get("status", "Away")
            emoji = period.get("emoji", "palm_tree")
            name = period.get("name", "Absence")
            logger.info(f"📅 Active absence period: {name} ({start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')})")
            return {"status": status, "emoji": emoji, "name": name, "end_time": end_time}
    
    return None

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
    
    # Check for active absence periods first (highest priority)
    absence = get_active_absence_period()
    if absence:
        # Use the end_time of the absence period as expires_at
        expires_at = int(absence["end_time"].timestamp())
        _set_mattermost_custom_status(absence["status"], absence["emoji"], expires_at=expires_at)
        logger.info("✅ Status update completed (absence period)")
        return
    
    ip = get_local_ip()
    zoom = zoom_in_meeting()
    teams = teams_in_meeting()
    webex = webex_in_meeting()

    logger.info(f"🌐 My local IP: {ip}")
    logger.info(f'{"📹" if zoom else "❌"} Zoom meeting: {"Yes" if zoom else "No"}')
    logger.info(f'{"💼" if teams else "❌"} Teams meeting: {"Yes" if teams else "No"}')
    logger.info(f'{"📞" if webex else "❌"} Webex meeting: {"Yes" if webex else "No"}')

    if zoom:
        _set_mattermost_custom_status("In a Zoom Meeting", "zoom")
    elif teams:
        _set_mattermost_custom_status("In a Teams Meeting", "microsoft_teams")
    elif webex:
        _set_mattermost_custom_status("In a Webex Meeting", "zoom")
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