"""Status management module."""
from .absence import get_active_absence_period
from .manager import handle_status_update

__all__ = [
    "get_active_absence_period",
    "handle_status_update",
]
