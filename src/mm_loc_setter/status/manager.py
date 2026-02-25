"""Status update management and orchestration."""
from datetime import datetime
from mm_loc_setter.logging_setup import logger
from mm_loc_setter.api import (
    set_mattermost_custom_status,
    clear_mattermost_custom_status,
)
from mm_loc_setter.config import CONFIGURED_NETWORKS
from mm_loc_setter.detectors import (
    zoom_in_meeting,
    teams_in_meeting,
    webex_in_meeting,
)
from mm_loc_setter.network import get_local_ip, get_all_local_ips
from .absence import get_active_absence_period


def handle_status_update(exception_end_time=None):
    """Handle automatic status update based on location and meeting state.
    
    Args:
        exception_end_time: Optional end time string (HH:MM format) for a workday exception
    """
    # Check for active absence periods first (highest priority)
    absence = get_active_absence_period()
    if absence:
        # Use the end_time of the absence period as expires_at
        expires_at = int(absence["end_time"].timestamp())
        set_mattermost_custom_status(absence["status"], absence["emoji"], expires_at=expires_at)
        logger.info("✅ Status update completed (absence period)")
        return
    
    ip = get_local_ip()
    all_ips = get_all_local_ips()
    zoom = zoom_in_meeting()
    teams = teams_in_meeting()
    webex = webex_in_meeting()

    if len(all_ips) > 0:
        logger.info(f"🌐 All local IPs: {', '.join(all_ips)}")

    logger.info(f'{"📹" if zoom else "❌"} Zoom meeting: {"Yes" if zoom else "No"}')
    logger.info(f'{"💼" if teams else "❌"} Teams meeting: {"Yes" if teams else "No"}')
    logger.info(f'{"📞" if webex else "❌"} Webex meeting: {"Yes" if webex else "No"}')

    # Calculate expires_at if exception_end_time is provided
    expires_at = None
    if exception_end_time:
        try:
            now = datetime.now()
            end_h, end_m = map(int, exception_end_time.split(':'))
            exception_end = now.replace(hour=end_h, minute=end_m, second=0, microsecond=0)
            expires_at = int(exception_end.timestamp())
            logger.info(f"ℹ️  Workday exception end time: {exception_end_time} (expires at {exception_end.strftime('%H:%M')})")
        except (ValueError, AttributeError):
            logger.warning(f"⚠️  Could not parse exception end time: {exception_end_time}")

    if zoom:
        set_mattermost_custom_status("In a Zoom Meeting", "zoom")
    elif teams:
        set_mattermost_custom_status("In a Teams Meeting", "microsoft_teams")
    elif webex:
        set_mattermost_custom_status("In a Webex Meeting", "zoom")
    else:
        location_found = False
        # Sort networks by priority (lower number = higher priority)
        # Networks without priority default to 999
        sorted_networks = sorted(CONFIGURED_NETWORKS, key=lambda n: n.get("priority", 999))
        
        for network in sorted_networks:
            ip_prefix = network.get("ip_prefix", "")
            # Check if any of the IPs match this network
            for ip in all_ips:
                if ip.startswith(ip_prefix):
                    logger.info(f"✅ Detected location: {network.get('name')} (IP: {ip})")
                    set_mattermost_custom_status(network.get("name"), network.get("emoji"), expires_at=expires_at)
                    location_found = True
                    break
            if location_found:
                break

        if not location_found:
            logger.info("ℹ️  Unknown location, clearing status")
            clear_mattermost_custom_status()
    
    logger.info("✅ Status update completed")
