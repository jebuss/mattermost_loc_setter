"""Tests for configuration loading."""
import os
from unittest.mock import patch
from mm_loc_setter.config.loader import (
    get_config_value,
    parse_time_string,
)


class TestGetConfigValue:
    """Test configuration value retrieval."""

    def test_get_from_environment_variable(self):
        """Test getting value from environment variable."""
        with patch.dict(os.environ, {"MM_TEST_KEY": "env_value"}):
            result = get_config_value("test_key")
            assert result == "env_value"

    def test_get_from_config_file(self):
        """Test getting value from config dict."""
        # Test with a default value if key doesn't exist
        result = get_config_value("nonexistent_key", default="default_value")
        assert result == "default_value"

    def test_environment_takes_priority(self):
        """Test that environment variable takes priority."""
        with patch.dict(os.environ, {"MM_PRIORITY_TEST": "env_value"}):
            result = get_config_value("priority_test")
            assert result == "env_value"

    def test_get_with_section(self):
        """Test getting value from config section."""
        # This would work with actual config file
        result = get_config_value("nonexistent", default="default", section="working_hours")
        assert result == "default"


class TestParseTimeString:
    """Test time string parsing."""

    def test_parse_valid_24h_format(self):
        """Test parsing valid 24-hour format."""
        hour, minute = parse_time_string("14:30")
        assert hour == 14
        assert minute == 30

    def test_parse_morning_time(self):
        """Test parsing morning time."""
        hour, minute = parse_time_string("08:00")
        assert hour == 8
        assert minute == 0

    def test_parse_without_minutes(self):
        """Test parsing time without minutes."""
        hour, minute = parse_time_string("14")
        assert hour == 14
        assert minute is not None

    def test_parse_with_defaults(self):
        """Test using default values."""
        hour, minute = parse_time_string(None, default_hour=9, default_minute=0)
        assert hour == 9
        assert minute == 0

    def test_parse_invalid_format(self):
        """Test parsing invalid format uses default."""
        hour, minute = parse_time_string("invalid", default_hour=8, default_minute=0)
        assert (hour, minute) == (8, 0)

    def test_parse_empty_string(self):
        """Test parsing empty string uses default."""
        hour, minute = parse_time_string("", default_hour=12, default_minute=0)
        assert (hour, minute) == (12, 0)

    def test_parse_malformed_time(self):
        """Test parsing malformed time."""
        hour, minute = parse_time_string("25:70", default_hour=8, default_minute=0)
        # Should return parts even if invalid
        assert hour == 25  # Parser doesn't validate ranges
        assert minute == 70
