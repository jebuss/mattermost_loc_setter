"""Tests for network connectivity checks."""
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from mm_loc_setter.network.connectivity import (
    get_local_ip,
    check_mattermost_reachable,
    check_network_route,
)


class TestGetLocalIp:
    """Test local IP address retrieval."""

    @patch('mm_loc_setter.network.connectivity.sock.getaddrinfo')
    @patch('mm_loc_setter.network.connectivity.sock.gethostname')
    def test_get_local_ip_success(self, mock_gethostname, mock_getaddrinfo):
        """Test successful IP retrieval."""
        mock_gethostname.return_value = "my-host"
        mock_getaddrinfo.return_value = [
            (None, None, None, None, ('127.0.0.1', 0)),
            (None, None, None, None, ('192.168.1.100', 0)),
        ]
        
        result = get_local_ip()
        
        assert result == '192.168.1.100'
        mock_gethostname.assert_called_once_with()
        mock_getaddrinfo.assert_called_once()

    @patch('mm_loc_setter.network.connectivity.sock.getaddrinfo')
    @patch('mm_loc_setter.network.connectivity.sock.gethostname')
    def test_get_local_ip_returns_loopback_on_error(self, mock_gethostname, mock_getaddrinfo):
        """Test that loopback is returned on lookup error."""
        mock_gethostname.return_value = "my-host"
        mock_getaddrinfo.side_effect = OSError("Lookup failed")
        
        result = get_local_ip()
        
        assert result == '127.0.0.1'


class TestCheckMattermostReachable:
    """Test Mattermost server reachability."""

    @patch('mm_loc_setter.network.connectivity.requests.get')
    def test_server_reachable(self, mock_get):
        """Test when server is reachable."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = check_mattermost_reachable(timeout=5, retries=1)
        
        assert result is True

    @patch('mm_loc_setter.network.connectivity.requests.get')
    def test_server_not_reachable(self, mock_get):
        """Test when server is not reachable."""
        mock_get.side_effect = requests.RequestException("Connection failed")
        
        result = check_mattermost_reachable(timeout=5, retries=1)
        
        assert result is False

    @patch('mm_loc_setter.network.connectivity.requests.get')
    @patch('mm_loc_setter.network.connectivity.time.sleep')
    def test_server_retries(self, mock_sleep, mock_get):
        """Test retry behavior."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.side_effect = [requests.RequestException("Fail 1"), mock_response]
        
        result = check_mattermost_reachable(timeout=5, retries=2)
        
        assert result is True
        assert mock_get.call_count == 2
        mock_sleep.assert_called_once_with(3)

    @patch('mm_loc_setter.network.connectivity.requests.get')
    def test_server_wrong_status_code(self, mock_get):
        """Test when server returns wrong status code."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        result = check_mattermost_reachable(timeout=5, retries=1)
        
        assert result is False


class TestCheckNetworkRoute:
    """Test network route checking."""

    @patch('mm_loc_setter.network.connectivity.sock.gethostbyname')
    @patch('mm_loc_setter.network.connectivity.sock.socket')
    def test_route_available(self, mock_socket_class, mock_gethostbyname):
        """Test when network route is available."""
        mock_gethostbyname.return_value = '192.168.1.1'
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 0
        mock_socket_class.return_value = mock_socket
        
        result = check_network_route('example.com', port=443)
        
        assert result is True
        mock_socket.close.assert_called_once()

    @patch('mm_loc_setter.network.connectivity.sock.gethostbyname')
    @patch('mm_loc_setter.network.connectivity.sock.socket')
    def test_route_not_available(self, mock_socket_class, mock_gethostbyname):
        """Test when network route is not available."""
        mock_gethostbyname.return_value = '192.168.1.1'
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 1
        mock_socket_class.return_value = mock_socket
        
        result = check_network_route('example.com', port=443)
        
        assert result is False

    @patch('mm_loc_setter.network.connectivity.sock.gethostbyname')
    def test_route_dns_fails(self, mock_gethostbyname):
        """Test when DNS lookup fails."""
        mock_gethostbyname.side_effect = OSError("DNS failed")
        
        result = check_network_route('invalid.example.com', port=443)
        
        assert result is False

    @patch('mm_loc_setter.network.connectivity.sock.gethostbyname')
    @patch('mm_loc_setter.network.connectivity.sock.socket')
    def test_route_removes_https_prefix(self, mock_socket_class, mock_gethostbyname):
        """Test that https:// prefix is removed from hostname."""
        mock_gethostbyname.return_value = '192.168.1.1'
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 0
        mock_socket_class.return_value = mock_socket
        
        result = check_network_route('https://example.com', port=443)
        
        assert result is True
        mock_gethostbyname.assert_called_once_with('example.com')
