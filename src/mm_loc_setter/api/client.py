"""Mattermost API client functions."""
import time
from datetime import datetime
from typing import Optional

import requests

from mm_loc_setter.config import MATTERMOST_URL, ACCESS_TOKEN, USER_ID
from mm_loc_setter.logging_setup import logger
from mm_loc_setter.utils import parse_dnd_end_time


def fetch_user_id_from_api(retries=3, delay=2) -> Optional[str]:
    """Fetch user_id from Mattermost API using /api/v4/users/me endpoint.
    
    Args:
        retries: Number of retry attempts
        delay: Delay in seconds between retries
        
    Returns:
        User ID string or None if failed
    """
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
        except requests.RequestException as e:
            logger.debug(f"Error fetching user_id on attempt {attempt+1}: {e}")
        
        if attempt < retries - 1:
            time.sleep(delay)
    
    return None


def set_mattermost_custom_status(
    message: str,
    emoji: str = "house",
    duration: Optional[str] = None,
    expires_at: Optional[str] = None,
    retries: int = 3,
    delay: int = 5
) -> bool:
    """Update Mattermost custom status (emoji + text).
    
    Args:
        message: Custom status message text
        emoji: Emoji name for the status
        duration: How long the custom status should last (e.g., "today", "four_hours")
        expires_at: When the custom status should expire (Unix timestamp, ISO 8601, or relative like "1h")
        retries: Number of retry attempts
        delay: Delay in seconds between retries
        
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"🔄 Setting status: {message} (emoji: {emoji})")
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    url = f"{MATTERMOST_URL}/api/v4/users/{USER_ID}/status/custom"

    def _normalize_emoji_name(name: str) -> str:
        """Normalize emoji name with common aliases."""
        aliases = {
            "utensils": "fork_and_knife",
        }
        return aliases.get(name, name)

    base = {"emoji": _normalize_emoji_name(emoji), "text": message}

    if duration:
        base["duration"] = duration

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

            text = response.text
            try:
                data = response.json()
            except ValueError:
                data = {}

            err_id = data.get("id", "")
            if err_id == "api.custom_status.set_custom_statuses.emoji_not_found":
                logger.error("❌ Emoji not found. Try a valid emoji name (e.g., 'fork_and_knife' instead of 'utensils').")
            elif err_id == "api.context.invalid_body_param.app_error":
                logger.error("❌ Server rejected payload. This server expects a root-level custom status payload with fields 'emoji', 'text', and optional 'expires_at' as ISO.")
            else:
                logger.error(f"❌ Failed to set custom status: {response.status_code}, {text}")
        except requests.RequestException as e:
            logger.error(f"❗ Unexpected error on attempt {attempt+1} ({type(e).__name__}): {e}")

        if attempt < retries - 1:
            logger.warning(f"⚠️  Retrying in {delay}s...")
            time.sleep(delay)
        else:
            logger.error(f"❌ Failed after {retries} attempts")
            return False


def set_mattermost_status(
    status: str,
    dnd_end_time: Optional[str] = None,
    retries: int = 3,
    delay: int = 5
) -> bool:
    """Update Mattermost presence status (online, away, dnd, offline).
    
    Args:
        status: One of 'online', 'away', 'dnd', 'offline'
        dnd_end_time: Optional DND end time in various formats
        retries: Number of retry attempts
        delay: Delay in seconds between retries
        
    Returns:
        True if successful, False otherwise
    """
    valid_statuses = ["online", "away", "dnd", "offline"]
    if status not in valid_statuses:
        logger.error(f"❌ Invalid status '{status}'. Must be one of: {', '.join(valid_statuses)}")
        return False
    
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
        except requests.RequestException as e:
            logger.error(f"❗ Unexpected error on attempt {attempt+1} ({type(e).__name__}): {e}")
            if attempt < retries - 1:
                logger.warning(f"⚠️  Retrying in {delay}s...")
                time.sleep(delay)
            else:
                logger.error(f"❌ Failed after {retries} attempts")
                return False


def clear_mattermost_custom_status() -> bool:
    """Clear Mattermost custom status.
    
    Returns:
        True if successful, False otherwise
    """
    headers = {"Accept": "application/json", "Authorization": f"Bearer {ACCESS_TOKEN}"}
    url = f"{MATTERMOST_URL}/api/v4/users/me/status/custom"
    try:
        response = requests.delete(url, headers=headers, timeout=10)
        if response.status_code == 200:
            logger.info("✅ Custom status cleared")
            return True
        else:
            logger.error(f"❌ Failed to clear custom status: {response.status_code}, {response.text}")
            return False
    except requests.RequestException as e:
        logger.error(f"❌ Failed to clear custom status: {e}")
        return False
