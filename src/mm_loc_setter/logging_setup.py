"""Logging configuration setup."""
import logging
import os


def setup_logger():
    """Setup and return configured logger."""
    _logger = logging.getLogger("mm_loc_setter")

    # Only configure if not already configured
    if not _logger.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    _logger = logging.getLogger("mm_loc_setter")

    # Allow overriding log level via env var MM_LOG_LEVEL (e.g., DEBUG)
    _env_log_level = os.getenv("MM_LOG_LEVEL", "").upper()
    if _env_log_level in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        _logger.setLevel(getattr(logging, _env_log_level))

    return _logger


# Get the logger for use in other modules
logger = setup_logger()
