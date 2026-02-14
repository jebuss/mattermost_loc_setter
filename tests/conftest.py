"""Pytest configuration and shared fixtures."""
import os
from unittest.mock import Mock
import pytest

@pytest.fixture
def mock_config_values():
    """Provide mock configuration values."""
    return {
        'MATTERMOST_URL': 'https://test.example.com',
        'ACCESS_TOKEN': 'test-token-123',
        'USER_ID': 'test-user-123',
        'CONFIGURED_NETWORKS': [
            {'name': 'Home', 'ip_prefix': '192.168.1.', 'emoji': 'house'},
            {'name': 'Office', 'ip_prefix': '10.0.0.', 'emoji': 'office'},
        ],
        'ABSENCE_PERIODS': [],
        'WORKING_DAYS': [0, 1, 2, 3, 4],
        'WORKING_START_HOUR': 8,
        'WORKING_START_MINUTE': 30,
        'WORKING_END_HOUR': 18,
        'WORKING_END_MINUTE': 0,
    }


@pytest.fixture
def mock_absence_periods():
    """Provide sample absence periods."""
    return [
        {
            'name': 'Vacation',
            'start_time': '2026-02-01',
            'end_time': '2026-02-10',
            'status': 'Away',
            'emoji': 'palm_tree',
        },
        {
            'name': 'Conference',
            'start_time': '2026-03-15',
            'end_time': '2026-03-18',
            'status': 'In Conference',
            'emoji': 'microphone',
        }
    ]


@pytest.fixture
def mock_network_connection():
    """Provide mock network connection."""
    conn = Mock()
    conn.raddr = Mock()
    conn.raddr.port = 8801
    return conn


@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary config file for testing."""
    config_content = """
url = "https://test.example.com"
access_token = "test-token"
user_id = "test-user-id"

networks = [
    { name = "Home", ip_prefix = "192.168.1.", emoji = "house" },
    { name = "Office", ip_prefix = "10.0.0.", emoji = "office" }
]

[working_hours]
weekdays = [0, 1, 2, 3, 4]
start_time = "08:30"
end_time = "18:00"
"""
    config_file = tmp_path / "config.toml"
    config_file.write_text(config_content)
    return config_file


@pytest.fixture(autouse=True)
def isolation_fixture():
    """Ensure test isolation by resetting environment variables after each test."""
    original_env = os.environ.copy()
    yield
    # Restore original environment after test
    for key in list(os.environ.keys()):
        if key.startswith('MM_'):
            if key in original_env:
                os.environ[key] = original_env[key]
            else:
                del os.environ[key]
