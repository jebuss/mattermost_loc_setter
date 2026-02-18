"""Configuration loading from config file and environment variables."""
import os
from pathlib import Path
from datetime import datetime
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


def parse_date_string(date_str):
    """Parse a date string in format 'YYYY-MM-DD' and return a date object.
    
    Args:
        date_str: Date string in format 'YYYY-MM-DD'
        
    Returns:
        datetime.date object or None if parsing fails
    """
    if not date_str:
        return None
    
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        logger.warning(f"⚠️  Invalid date format '{date_str}', expected 'YYYY-MM-DD'")
        return None


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

# Load daily working hours (optional overrides)
DAILY_WORKING_HOURS = CONFIG.get("working_hours", {}).get("daily", {})

# Load workday exceptions (specific dates with custom working hours)
WORKDAY_EXCEPTIONS = CONFIG.get("working_hours", {}).get("exceptions", [])


def get_working_hours_for_day(weekday, date=None):
    """Get working hours for a specific weekday or date.
    
    Priority:
    1. Workday exception for the specific date
    2. Daily override for the weekday
    3. Global default
    
    Args:
        weekday: Weekday number (0=Monday, 6=Sunday)
        date: Optional datetime.date object to check for exceptions
        
    Returns:
        Dict with 'start_hour', 'start_minute', 'end_hour', 'end_minute'
    """
    # Check for workday exceptions first
    if date:
        for exception in WORKDAY_EXCEPTIONS:
            exception_date = parse_date_string(exception.get("date"))
            if exception_date == date:
                # Found a matching exception
                if exception.get("is_non_working_day"):
                    # This day is marked as non-working
                    return None
                
                # Get custom working hours for this exception
                start_str = exception.get("start_time")
                end_str = exception.get("end_time")
                start_h, start_m = parse_time_string(start_str, WORKING_START_HOUR, WORKING_START_MINUTE)
                end_h, end_m = parse_time_string(end_str, WORKING_END_HOUR, WORKING_END_MINUTE)
                
                return {
                    "start_hour": start_h,
                    "start_minute": start_m,
                    "end_hour": end_h,
                    "end_minute": end_m,
                }
    
    day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    day_name = day_names[weekday]
    
    # Check if there's a specific configuration for this weekday
    if day_name in DAILY_WORKING_HOURS:
        day_config = DAILY_WORKING_HOURS[day_name]
        start_str = day_config.get("start_time")
        end_str = day_config.get("end_time")
        
        start_h, start_m = parse_time_string(start_str, WORKING_START_HOUR, WORKING_START_MINUTE)
        end_h, end_m = parse_time_string(end_str, WORKING_END_HOUR, WORKING_END_MINUTE)
        
        return {
            "start_hour": start_h,
            "start_minute": start_m,
            "end_hour": end_h,
            "end_minute": end_m,
        }
    
    # Fall back to global default
    return {
        "start_hour": WORKING_START_HOUR,
        "start_minute": WORKING_START_MINUTE,
        "end_hour": WORKING_END_HOUR,
        "end_minute": WORKING_END_MINUTE,
    }

def get_exception_for_date(date):
    """Get the workday exception for a specific date.
    
    Args:
        date: datetime.date object
        
    Returns:
        Dict with exception data or None if no exception for this date
    """
    for exception in WORKDAY_EXCEPTIONS:
        exception_date = parse_date_string(exception.get("date"))
        if exception_date == date:
            return exception
    
    return None