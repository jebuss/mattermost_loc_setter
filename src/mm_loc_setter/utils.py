"""Utility functions."""
import time
from datetime import datetime
from typing import Optional
from mm_loc_setter.logging_setup import logger


def parse_dnd_end_time(time_input: Optional[str]) -> Optional[int]:
    """Parse DND end time from various formats to Unix timestamp.
    
    Supported formats:
    - Unix timestamp (integer): 1703001600
    - ISO 8601: "2025-12-18T10:30:00", "2025-12-18T10:30:00Z"
    - Relative time: "10m", "1h", "30s" (from now)
    
    Args:
        time_input: Time input in various formats
        
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


def parse_absence_datetime(time_str: Optional[str]) -> Optional[datetime]:
    """Parse datetime string for absence periods.
    
    Supports formats:
    - "YYYY-MM-DD" (assumes 00:00:00 for start, 23:59:59 for end)
    - "YYYY-MM-DDTHH:MM:SS"
    - "YYYY-MM-DD HH:MM:SS"
    
    Args:
        time_str: Datetime string
        
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
