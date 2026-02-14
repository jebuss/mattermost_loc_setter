"""Configuration loading from config file and environment variables."""
import os
from pathlib import Path
import logging

try:
    import tomllib
except ImportError:
    import tomli as tomllib

logger = logging.getLogger(__name__)

# --- CONFIGURATION LOADING ---
CONFIG = {}
CONFIG_PATH = Path.home() / ".config" / "mm-status" / "config.toml"

if CONFIG_PATH.is_file():
    with open(CONFIG_PATH, "rb") as f:
        CONFIG = tomllib.load(f)
else:
    # Create the directory if it doesn't exist for the user's convenience
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_config_value(key, default=None, section=None):
    """Get config value with priority: Environment Variable > Config File > Default.
    
    Args:
        key: Config key name
        default: Default value if not found
        section: Optional section in config file
        
    Returns:
        Config value from environment, file, or default
    """
    env_var = f"MM_{key.upper()}"
    if env_var in os.environ:
        return os.environ[env_var]
    
    if section:
        return CONFIG.get(section, {}).get(key, default)
    
    return CONFIG.get(key, default)


def parse_time_string(time_str, default_hour=0, default_minute=0):
    """Parse a time string in format 'HH:MM' and return (hour, minute) tuple.
    
    Args:
        time_str: Time string in format 'HH:MM'
        default_hour: Default hour if parsing fails
        default_minute: Default minute if parsing fails
        
    Returns:
        Tuple of (hour, minute)
    """
    if not time_str:
        return (default_hour, default_minute)
    
    try:
        parts = time_str.split(':')
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        return (hour, minute)
    except (ValueError, IndexError):
        logger.warning(f"⚠️  Invalid time format '{time_str}', using default {default_hour}:{default_minute:02d}")
        return (default_hour, default_minute)


# --- CONFIGURATION VALUES ---
MATTERMOST_URL = get_config_value("url", "https://your-mattermost-server.com")
ACCESS_TOKEN = get_config_value("access_token")
USER_ID = get_config_value("user_id")

# Load the list of networks
CONFIGURED_NETWORKS = get_config_value("networks", [])

# Load absence periods
ABSENCE_PERIODS = get_config_value("absence_periods", [])

# Load working hours configuration
WORKING_DAYS = get_config_value("weekdays", [0, 1, 2, 3, 4], section="working_hours")
start_time_str = get_config_value("start_time", "8:00", section="working_hours")
end_time_str = get_config_value("end_time", "18:00", section="working_hours")

WORKING_START_HOUR, WORKING_START_MINUTE = parse_time_string(start_time_str, 8, 0)
WORKING_END_HOUR, WORKING_END_MINUTE = parse_time_string(end_time_str, 18, 0)
