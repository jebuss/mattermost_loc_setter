"""Configuration management module."""
from .loader import (
    CONFIG,
    CONFIG_PATH,
    MATTERMOST_URL,
    ACCESS_TOKEN,
    USER_ID,
    CONFIGURED_NETWORKS,
    ABSENCE_PERIODS,
    WORKING_DAYS,
    WORKING_START_HOUR,
    WORKING_START_MINUTE,
    WORKING_END_HOUR,
    WORKING_END_MINUTE,
    WORKDAY_EXCEPTIONS,
    get_config_value,
    get_working_hours_for_day,
    get_exception_for_date
)

__all__ = [
    "CONFIG",
    "CONFIG_PATH",
    "MATTERMOST_URL",
    "ACCESS_TOKEN",
    "USER_ID",
    "CONFIGURED_NETWORKS",
    "ABSENCE_PERIODS",
    "WORKING_DAYS",
    "WORKING_START_HOUR",
    "WORKING_START_MINUTE",
    "WORKING_END_HOUR",
    "WORKING_END_MINUTE",
    "WORKDAY_EXCEPTIONS",
    "get_config_value",
    "get_working_hours_for_day",
    "get_exception_for_date"
]
