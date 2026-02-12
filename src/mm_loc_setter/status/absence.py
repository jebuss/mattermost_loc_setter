"""Absence period management."""
from datetime import datetime
from typing import Optional, Dict
from mm_loc_setter.config import ABSENCE_PERIODS
from mm_loc_setter.logging_setup import logger
from mm_loc_setter.utils import parse_absence_datetime


def get_active_absence_period() -> Optional[Dict]:
    """Check if current time falls within any configured absence period.
    
    Returns:
        dict with 'status', 'emoji', 'name', and 'end_time' keys if in absence period, None otherwise
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
