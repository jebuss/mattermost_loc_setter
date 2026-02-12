"""Tests for status management."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from mm_loc_setter.status.absence import get_active_absence_period


class TestGetActiveAbsencePeriod:
    """Test absence period detection."""

    @patch('mm_loc_setter.status.absence.ABSENCE_PERIODS', [])
    def test_no_absence_periods(self):
        """Test when no absence periods are configured."""
        result = get_active_absence_period()
        assert result is None

    @patch('mm_loc_setter.status.absence.ABSENCE_PERIODS', [
        {
            'name': 'Vacation',
            'start_time': '2026-02-01',
            'end_time': '2026-02-05',
            'status': 'Away',
            'emoji': 'palm_tree'
        }
    ])
    @patch('mm_loc_setter.status.absence.datetime')
    def test_within_absence_period(self, mock_datetime):
        """Test when current time is within absence period."""
        # Mock datetime to be within the period
        mock_now = datetime(2026, 2, 3, 12, 0, 0)
        mock_datetime.now.return_value = mock_now
        mock_datetime.strptime = datetime.strptime
        
        result = get_active_absence_period()
        
        assert result is not None
        assert result['name'] == 'Vacation'
        assert result['status'] == 'Away'
        assert result['emoji'] == 'palm_tree'
        assert 'end_time' in result

    @patch('mm_loc_setter.status.absence.ABSENCE_PERIODS', [
        {
            'name': 'Vacation',
            'start_time': '2026-03-01',
            'end_time': '2026-03-05',
            'status': 'Away',
            'emoji': 'palm_tree'
        }
    ])
    @patch('mm_loc_setter.status.absence.datetime')
    def test_outside_absence_period(self, mock_datetime):
        """Test when current time is outside absence period."""
        # Mock datetime to be before the period
        mock_now = datetime(2026, 2, 1, 12, 0, 0)
        mock_datetime.now.return_value = mock_now
        mock_datetime.strptime = datetime.strptime
        
        result = get_active_absence_period()
        
        assert result is None

    @patch('mm_loc_setter.status.absence.ABSENCE_PERIODS', [
        {
            'name': 'Short Break',
            'start_time': '2026-02-12',
            'end_time': '2026-02-12',
        }
    ])
    @patch('mm_loc_setter.status.absence.datetime')
    def test_date_only_format(self, mock_datetime):
        """Test parsing date-only format."""
        # Mock datetime to be on the same day
        mock_now = datetime(2026, 2, 12, 15, 0, 0)
        mock_datetime.now.return_value = mock_now
        mock_datetime.strptime = datetime.strptime
        
        result = get_active_absence_period()
        
        # Should extend end_time to end of day
        assert result is not None

    @patch('mm_loc_setter.status.absence.ABSENCE_PERIODS', [
        {
            'name': 'Invalid Period',
            'start_time': '2026-02-01',
            # Missing end_time
        }
    ])
    def test_missing_end_time(self):
        """Test when absence period is missing end_time."""
        result = get_active_absence_period()
        
        assert result is None

    @patch('mm_loc_setter.status.absence.ABSENCE_PERIODS', [
        {
            'name': 'Vacation 1',
            'start_time': '2026-03-01',
            'end_time': '2026-03-05',
            'status': 'Away',
            'emoji': 'palm_tree'
        },
        {
            'name': 'Vacation 2',
            'start_time': '2026-02-01',
            'end_time': '2026-02-10',
            'status': 'Away',
            'emoji': 'beach'
        }
    ])
    @patch('mm_loc_setter.status.absence.datetime')
    def test_multiple_periods_returns_first_match(self, mock_datetime):
        """Test that first matching period is returned."""
        # Mock datetime to be within second period
        mock_now = datetime(2026, 2, 5, 12, 0, 0)
        mock_datetime.now.return_value = mock_now
        mock_datetime.strptime = datetime.strptime
        
        result = get_active_absence_period()
        
        assert result is not None
        # Should return the second period (first match in loop)
        assert result['emoji'] == 'beach'

    @patch('mm_loc_setter.status.absence.ABSENCE_PERIODS', [
        {
            'name': 'Vacation',
            'start_time': '2026-02-01T09:00:00',
            'end_time': '2026-02-05T17:00:00',
            'status': 'Away',
            'emoji': 'palm_tree'
        }
    ])
    @patch('mm_loc_setter.status.absence.datetime')
    def test_datetime_with_time_component(self, mock_datetime):
        """Test parsing datetime with time component."""
        # Mock datetime to be within the period
        mock_now = datetime(2026, 2, 3, 12, 0, 0)
        mock_datetime.now.return_value = mock_now
        mock_datetime.strptime = datetime.strptime
        
        result = get_active_absence_period()
        
        assert result is not None
        assert result['status'] == 'Away'

    @patch('mm_loc_setter.status.absence.ABSENCE_PERIODS', [
        {
            'name': 'Vacation',
            'start_time': '2026-02-01',
            'end_time': '2026-02-05',
            # Missing status and emoji - should use defaults
        }
    ])
    @patch('mm_loc_setter.status.absence.datetime')
    def test_default_status_and_emoji(self, mock_datetime):
        """Test default status and emoji when not provided."""
        mock_now = datetime(2026, 2, 3, 12, 0, 0)
        mock_datetime.now.return_value = mock_now
        mock_datetime.strptime = datetime.strptime
        
        result = get_active_absence_period()
        
        assert result is not None
        assert result['status'] == 'Away'
        assert result['emoji'] == 'palm_tree'
