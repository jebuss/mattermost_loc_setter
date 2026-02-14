"""Status update management and orchestration."""
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
from mm_loc_setter.network import get_local_ip
from .absence import get_active_absence_period


def handle_status_update():
    """Handle automatic status update based on location and meeting state."""
    # Check for active absence periods first (highest priority)
    absence = get_active_absence_period()
    if absence:
        # Use the end_time of the absence period as expires_at
        expires_at = int(absence["end_time"].timestamp())
        set_mattermost_custom_status(absence["status"], absence["emoji"], expires_at=expires_at)
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
        set_mattermost_custom_status("In a Zoom Meeting", "zoom")
    elif teams:
        set_mattermost_custom_status("In a Teams Meeting", "microsoft_teams")
    elif webex:
        set_mattermost_custom_status("In a Webex Meeting", "zoom")
    else:
        location_found = False
        for network in CONFIGURED_NETWORKS:
            if ip.startswith(network.get("ip_prefix", "")):
                set_mattermost_custom_status(network.get("name"), network.get("emoji"))
                location_found = True
                break

        if not location_found:
            logger.info("ℹ️  Unknown location, clearing status")
            clear_mattermost_custom_status()
    
    logger.info("✅ Status update completed")
