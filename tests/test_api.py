"""Tests for Mattermost API client."""
import pytest
from unittest.mock import Mock, patch
import requests
from mm_loc_setter.api.client import (
    fetch_user_id_from_api,
    set_mattermost_custom_status,
    set_mattermost_status,
    clear_mattermost_custom_status,
)


class TestFetchUserIdFromApi:
    """Test user ID fetching."""

    @patch('mm_loc_setter.api.client.ACCESS_TOKEN', 'test-token')
    @patch('mm_loc_setter.api.client.requests.get')
    def test_fetch_user_id_success(self, mock_get):
        """Test successful user ID fetch."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'id': 'user123'}
        mock_get.return_value = mock_response
        
        result = fetch_user_id_from_api(retries=3, delay=1)
        
        assert result == 'user123'

    @patch('mm_loc_setter.api.client.ACCESS_TOKEN', None)
    def test_fetch_user_id_no_token(self):
        """Test when access token is not available."""
        result = fetch_user_id_from_api()
        
        assert result is None

    @patch('mm_loc_setter.api.client.ACCESS_TOKEN', 'test-token')
    @patch('mm_loc_setter.api.client.requests.get')
    def test_fetch_user_id_failed_status(self, mock_get):
        """Test when API returns error status."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_get.return_value = mock_response
        
        result = fetch_user_id_from_api(retries=1, delay=1)
        
        assert result is None

    @patch('mm_loc_setter.api.client.ACCESS_TOKEN', 'test-token')
    @patch('mm_loc_setter.api.client.requests.get')
    @patch('mm_loc_setter.api.client.time.sleep')
    def test_fetch_user_id_retries(self, mock_sleep, mock_get):
        """Test retry behavior."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'id': 'user123'}
        mock_get.side_effect = [requests.RequestException("Network error"), mock_response]
        
        result = fetch_user_id_from_api(retries=2, delay=1)
        
        assert result == 'user123'
        mock_sleep.assert_called_once_with(1)


class TestSetMattermostCustomStatus:
    """Test setting custom status."""

    @patch('mm_loc_setter.api.client.ACCESS_TOKEN', 'test-token')
    @patch('mm_loc_setter.api.client.USER_ID', 'user123')
    @patch('mm_loc_setter.api.client.requests.put')
    def test_set_custom_status_success(self, mock_put):
        """Test successful custom status setting."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_put.return_value = mock_response
        
        result = set_mattermost_custom_status("Working", "laptop", retries=1)
        
        assert result is True
        mock_put.assert_called_once()
        call_args = mock_put.call_args
        assert call_args.kwargs['json']['text'] == 'Working'
        assert call_args.kwargs['json']['emoji'] == 'laptop'

    @patch('mm_loc_setter.api.client.ACCESS_TOKEN', 'test-token')
    @patch('mm_loc_setter.api.client.USER_ID', 'user123')
    @patch('mm_loc_setter.api.client.requests.put')
    def test_set_custom_status_with_duration(self, mock_put):
        """Test setting custom status with duration."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_put.return_value = mock_response
        
        result = set_mattermost_custom_status("In meeting", "calendar", duration="1h", retries=1)
        
        assert result is True
        call_args = mock_put.call_args
        assert call_args.kwargs['json']['duration'] == '1h'

    @patch('mm_loc_setter.api.client.ACCESS_TOKEN', 'test-token')
    @patch('mm_loc_setter.api.client.USER_ID', 'user123')
    @patch('mm_loc_setter.api.client.requests.put')
    def test_set_custom_status_with_expires_at(self, mock_put):
        """Test setting custom status with expires_at."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_put.return_value = mock_response
        
        result = set_mattermost_custom_status("Away", "palm_tree", expires_at=1703001600, retries=1)
        
        assert result is True
        call_args = mock_put.call_args
        assert 'expires_at' in call_args.kwargs['json']

    @patch('mm_loc_setter.api.client.ACCESS_TOKEN', 'test-token')
    @patch('mm_loc_setter.api.client.USER_ID', 'user123')
    @patch('mm_loc_setter.api.client.requests.put')
    def test_set_custom_status_emoji_not_found(self, mock_put):
        """Test when emoji is not found."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {'id': 'api.custom_status.set_custom_statuses.emoji_not_found'}
        mock_response.text = "Emoji not found"
        mock_put.return_value = mock_response
        
        result = set_mattermost_custom_status("Test", "invalid_emoji", retries=1)
        
        assert result is False

    @patch('mm_loc_setter.api.client.ACCESS_TOKEN', 'test-token')
    @patch('mm_loc_setter.api.client.USER_ID', 'user123')
    @patch('mm_loc_setter.api.client.requests.put')
    def test_set_custom_status_network_error(self, mock_put):
        """Test when network error occurs."""
        mock_put.side_effect = requests.RequestException("Network error")
        
        result = set_mattermost_custom_status("Test", "laptop", retries=1)
        
        assert result is False


class TestSetMattermostStatus:
    """Test setting presence status."""

    @patch('mm_loc_setter.api.client.ACCESS_TOKEN', 'test-token')
    @patch('mm_loc_setter.api.client.USER_ID', 'user123')
    @patch('mm_loc_setter.api.client.requests.put')
    def test_set_status_online(self, mock_put):
        """Test setting online status."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_put.return_value = mock_response
        
        result = set_mattermost_status("online", retries=1)
        
        assert result is True
        call_args = mock_put.call_args
        assert call_args.kwargs['json']['status'] == 'online'

    @patch('mm_loc_setter.api.client.ACCESS_TOKEN', 'test-token')
    @patch('mm_loc_setter.api.client.USER_ID', 'user123')
    @patch('mm_loc_setter.api.client.requests.put')
    def test_set_status_dnd_with_end_time(self, mock_put):
        """Test setting DND status with end time."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_put.return_value = mock_response
        
        result = set_mattermost_status("dnd", dnd_end_time="1h", retries=1)
        
        assert result is True
        call_args = mock_put.call_args
        assert call_args.kwargs['json']['status'] == 'dnd'
        assert 'dnd_end_time' in call_args.kwargs['json']

    def test_set_status_invalid_status(self):
        """Test with invalid status value."""
        result = set_mattermost_status("invalid", retries=1)
        
        assert result is False

    @patch('mm_loc_setter.api.client.ACCESS_TOKEN', 'test-token')
    @patch('mm_loc_setter.api.client.USER_ID', 'user123')
    @patch('mm_loc_setter.api.client.requests.put')
    def test_set_status_invalid_dnd_time(self, mock_put):
        """Test with invalid DND end time."""
        result = set_mattermost_status("dnd", dnd_end_time="invalid", retries=1)
        
        assert result is False


class TestClearMattermostCustomStatus:
    """Test clearing custom status."""

    @patch('mm_loc_setter.api.client.ACCESS_TOKEN', 'test-token')
    @patch('mm_loc_setter.api.client.requests.delete')
    def test_clear_custom_status_success(self, mock_delete):
        """Test successful custom status clearing."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_delete.return_value = mock_response
        
        result = clear_mattermost_custom_status()
        
        assert result is True

    @patch('mm_loc_setter.api.client.ACCESS_TOKEN', 'test-token')
    @patch('mm_loc_setter.api.client.requests.delete')
    def test_clear_custom_status_failure(self, mock_delete):
        """Test when clearing fails."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_delete.return_value = mock_response
        
        result = clear_mattermost_custom_status()
        
        assert result is False

    @patch('mm_loc_setter.api.client.ACCESS_TOKEN', 'test-token')
    @patch('mm_loc_setter.api.client.requests.delete')
    def test_clear_custom_status_network_error(self, mock_delete):
        """Test when network error occurs."""
        mock_delete.side_effect = requests.RequestException("Network error")
        
        result = clear_mattermost_custom_status()
        
        assert result is False
