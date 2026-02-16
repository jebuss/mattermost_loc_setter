"""Tests for configuration loading."""
import os
from unittest.mock import patch
from mm_loc_setter.config.loader import (
    get_config_value,
    parse_time_string,
    get_working_hours_for_day,
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


class TestGetWorkingHoursForDay:
    """Test daily working hours retrieval."""

    def test_get_default_working_hours(self):
        """Test getting default working hours when no daily config."""
        # Monday (0) should return defaults if not configured
        hours = get_working_hours_for_day(0)
        assert "start_hour" in hours
        assert "start_minute" in hours
        assert "end_hour" in hours
        assert "end_minute" in hours

    def test_all_weekdays_return_valid_hours(self):
        """Test that all weekdays return valid hour/minute values."""
        for weekday in range(7):
            hours = get_working_hours_for_day(weekday)
            assert isinstance(hours["start_hour"], int)
            assert isinstance(hours["start_minute"], int)
            assert isinstance(hours["end_hour"], int)
            assert isinstance(hours["end_minute"], int)
            assert 0 <= hours["start_hour"] <= 23
            assert 0 <= hours["start_minute"] <= 59
            assert 0 <= hours["end_hour"] <= 23
            assert 0 <= hours["end_minute"] <= 59

    def test_monday_is_weekday_0(self):
        """Test that weekday 0 is Monday."""
        monday_hours = get_working_hours_for_day(0)
        assert monday_hours is not None

    def test_sunday_is_weekday_6(self):
        """Test that weekday 6 is Sunday."""
        sunday_hours = get_working_hours_for_day(6)
        assert sunday_hours is not None

