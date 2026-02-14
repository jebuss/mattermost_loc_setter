"""Mattermost API interaction module."""
from .client import (
    fetch_user_id_from_api,
    set_mattermost_custom_status,
    set_mattermost_status,
    clear_mattermost_custom_status,
)

__all__ = [
    "fetch_user_id_from_api",
    "set_mattermost_custom_status",
    "set_mattermost_status",
    "clear_mattermost_custom_status",
]
