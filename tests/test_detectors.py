"""Tests for meeting detection."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from mm_loc_setter.detectors.meeting import (
    are_ports_connected_any,
    is_in_meeting,
    zoom_in_meeting,
    teams_in_meeting,
    webex_in_meeting,
)


class TestArePortsConnectedAny:
    """Test port connection checking."""

    def test_no_connections(self):
        """Test with no connections."""
        connections = []
        result = are_ports_connected_any(connections, ports=[8801])
        assert result is False

    def test_port_in_connections(self):
        """Test with port in connections."""
        mock_conn1 = Mock()
        mock_conn1.raddr.port = 8801
        
        connections = [mock_conn1]
        result = are_ports_connected_any(connections, ports=[8801])
        assert result is True

    def test_port_not_in_connections(self):
        """Test with port not in connections."""
        mock_conn1 = Mock()
        mock_conn1.raddr.port = 443
        
        connections = [mock_conn1]
        result = are_ports_connected_any(connections, ports=[8801])
        assert result is False

    def test_multiple_ports_any_match(self):
        """Test with multiple ports where one matches."""
        mock_conn1 = Mock()
        mock_conn1.raddr.port = 8802
        
        connections = [mock_conn1]
        result = are_ports_connected_any(connections, ports=[8801, 8802, 8803])
        assert result is True

    def test_multiple_connections_any_match(self):
        """Test with multiple connections where one matches."""
        mock_conn1 = Mock()
        mock_conn1.raddr.port = 443
        
        mock_conn2 = Mock()
        mock_conn2.raddr.port = 8801
        
        connections = [mock_conn1, mock_conn2]
        result = are_ports_connected_any(connections, ports=[8801])
        assert result is True

    def test_none_raddr(self):
        """Test with connection having None raddr."""
        mock_conn1 = Mock()
        mock_conn1.raddr = None
        
        connections = [mock_conn1]
        result = are_ports_connected_any(connections, ports=[8801])
        assert result is False


class TestIsInMeeting:
    """Test generic meeting detection."""

    @patch('mm_loc_setter.detectors.meeting.psutil.process_iter')
    def test_no_process_found(self, mock_process_iter):
        """Test when process is not found."""
        mock_process_iter.return_value = []
        
        result = is_in_meeting('zoom', ports=[8801])
        assert result is False

    @patch('mm_loc_setter.detectors.meeting.psutil.process_iter')
    def test_process_found_no_connections(self, mock_process_iter):
        """Test when process is found but has no connections."""
        mock_proc = Mock()
        mock_proc.info = {'name': 'zoom'}
        mock_proc.net_connections.return_value = []
        
        mock_process_iter.return_value = [mock_proc]
        
        result = is_in_meeting('zoom', ports=[8801])
        assert result is False

    @patch('mm_loc_setter.detectors.meeting.psutil.process_iter')
    def test_process_found_with_matching_port(self, mock_process_iter):
        """Test when process is found with matching port."""
        mock_proc = Mock()
        mock_proc.info = {'name': 'zoom.exe'}
        
        mock_conn = Mock()
        mock_conn.raddr.port = 8801
        mock_proc.net_connections.return_value = [mock_conn]
        
        mock_process_iter.return_value = [mock_proc]
        
        result = is_in_meeting('zoom', ports=[8801])
        assert result is True

    @patch('mm_loc_setter.detectors.meeting.psutil.process_iter')
    def test_access_denied_ignored(self, mock_process_iter):
        """Test that AccessDenied exception is handled."""
        import psutil
        
        mock_proc = Mock()
        mock_proc.info = {'name': 'zoom'}
        mock_proc.net_connections.side_effect = psutil.AccessDenied()
        
        mock_process_iter.return_value = [mock_proc]
        
        result = is_in_meeting('zoom', ports=[8801])
        assert result is False


class TestZoomInMeeting:
    """Test Zoom meeting detection."""

    @patch('mm_loc_setter.detectors.meeting.is_in_meeting')
    def test_zoom_in_meeting(self, mock_is_in_meeting):
        """Test Zoom meeting detection."""
        mock_is_in_meeting.return_value = True
        
        result = zoom_in_meeting()
        assert result is True
        mock_is_in_meeting.assert_called_once_with('zoom', ports=[8801, 8802, 8803])

    @patch('mm_loc_setter.detectors.meeting.is_in_meeting')
    def test_zoom_not_in_meeting(self, mock_is_in_meeting):
        """Test Zoom not in meeting."""
        mock_is_in_meeting.return_value = False
        
        result = zoom_in_meeting()
        assert result is False


class TestTeamsInMeeting:
    """Test Teams meeting detection."""

    @patch('mm_loc_setter.detectors.meeting.is_in_meeting')
    def test_teams_in_meeting(self, mock_is_in_meeting):
        """Test Teams meeting detection."""
        mock_is_in_meeting.return_value = True
        
        result = teams_in_meeting()
        assert result is True
        mock_is_in_meeting.assert_called_once_with('teams', ports=[3478, 3479, 3480, 3481])

    @patch('mm_loc_setter.detectors.meeting.is_in_meeting')
    def test_teams_not_in_meeting(self, mock_is_in_meeting):
        """Test Teams not in meeting."""
        mock_is_in_meeting.return_value = False
        
        result = teams_in_meeting()
        assert result is False


class TestWebexInMeeting:
    """Test Webex meeting detection."""

    @patch('mm_loc_setter.detectors.meeting.is_in_meeting')
    def test_webex_in_meeting(self, mock_is_in_meeting):
        """Test Webex meeting detection."""
        mock_is_in_meeting.return_value = True
        
        result = webex_in_meeting()
        assert result is True
        mock_is_in_meeting.assert_called_once_with('webex', ports=[5004, 5005, 9000, 9001])

    @patch('mm_loc_setter.detectors.meeting.is_in_meeting')
    def test_webex_not_in_meeting(self, mock_is_in_meeting):
        """Test Webex not in meeting."""
        mock_is_in_meeting.return_value = False
        
        result = webex_in_meeting()
        assert result is False
