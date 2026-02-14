"""Tests for utility functions."""
import pytest
import time
from datetime import datetime
from mm_loc_setter.utils import parse_dnd_end_time, parse_absence_datetime


class TestParseDndEndTime:
    """Test DND end time parsing."""

    def test_parse_unix_timestamp_int(self):
        """Test parsing Unix timestamp as integer."""
        timestamp = 1703001600
        result = parse_dnd_end_time(timestamp)
        assert result == timestamp

    def test_parse_unix_timestamp_string(self):
        """Test parsing Unix timestamp as string."""
        timestamp_str = "1703001600"
        result = parse_dnd_end_time(timestamp_str)
        assert result == 1703001600

    def test_parse_relative_seconds(self):
        """Test parsing relative time in seconds."""
        before = int(time.time())
        result = parse_dnd_end_time("30s")
        after = int(time.time())
        
        assert result is not None
        assert before + 30 <= result <= after + 30

    def test_parse_relative_minutes(self):
        """Test parsing relative time in minutes."""
        before = int(time.time())
        result = parse_dnd_end_time("30m")
        after = int(time.time())
        
        assert result is not None
        assert before + 30 * 60 <= result <= after + 30 * 60

    def test_parse_relative_hours(self):
        """Test parsing relative time in hours."""
        before = int(time.time())
        result = parse_dnd_end_time("2h")
        after = int(time.time())
        
        assert result is not None
        assert before + 2 * 3600 <= result <= after + 2 * 3600

    def test_parse_relative_days(self):
        """Test parsing relative time in days."""
        before = int(time.time())
        result = parse_dnd_end_time("1d")
        after = int(time.time())
        
        assert result is not None
        assert before + 86400 <= result <= after + 86400

    def test_parse_iso_8601_datetime(self):
        """Test parsing ISO 8601 datetime."""
        iso_str = "2025-12-18T10:30:00"
        result = parse_dnd_end_time(iso_str)
        
        assert result is not None
        dt = datetime.fromisoformat(iso_str)
        assert result == int(dt.timestamp())

    def test_parse_iso_8601_with_z(self):
        """Test parsing ISO 8601 with Z suffix."""
        iso_str = "2025-12-18T10:30:00Z"
        result = parse_dnd_end_time(iso_str)
        
        assert result is not None
        # Should parse successfully
        assert isinstance(result, int)

    def test_parse_iso_8601_date_only(self):
        """Test parsing ISO 8601 date only."""
        date_str = "2025-12-18"
        result = parse_dnd_end_time(date_str)
        
        assert result is not None
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        assert result == int(dt.timestamp())

    def test_parse_invalid_format(self):
        """Test parsing invalid format."""
        result = parse_dnd_end_time("invalid")
        assert result is None

    def test_parse_none(self):
        """Test parsing None."""
        result = parse_dnd_end_time(None)
        assert result is None

    def test_parse_empty_string(self):
        """Test parsing empty string."""
        result = parse_dnd_end_time("")
        assert result is None


class TestParseAbsenceDatetime:
    """Test absence datetime parsing."""

    def test_parse_iso_format(self):
        """Test parsing ISO format with time."""
        dt_str = "2025-12-18T10:30:00"
        result = parse_absence_datetime(dt_str)
        
        assert result is not None
        assert result.year == 2025
        assert result.month == 12
        assert result.day == 18
        assert result.hour == 10
        assert result.minute == 30

    def test_parse_space_format(self):
        """Test parsing format with space separator."""
        dt_str = "2025-12-18 10:30:00"
        result = parse_absence_datetime(dt_str)
        
        assert result is not None
        assert result.year == 2025
        assert result.month == 12
        assert result.day == 18

    def test_parse_date_only(self):
        """Test parsing date only."""
        dt_str = "2025-12-18"
        result = parse_absence_datetime(dt_str)
        
        assert result is not None
        assert result.year == 2025
        assert result.month == 12
        assert result.day == 18
        assert result.hour == 0
        assert result.minute == 0

    def test_parse_invalid_format(self):
        """Test parsing invalid format."""
        result = parse_absence_datetime("18/12/2025")
        assert result is None

    def test_parse_none(self):
        """Test parsing None."""
        result = parse_absence_datetime(None)
        assert result is None

    def test_parse_empty_string(self):
        """Test parsing empty string."""
        result = parse_absence_datetime("")
        assert result is None
