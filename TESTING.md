# Testing Guide

This document explains how to run and write tests for the Mattermost Location Status Setter project.

## Installation

Install test dependencies:

```bash
pip install -e ".[test]"
```

Or for development:

```bash
pip install -e ".[dev]"
```

## Running Tests

### Run all tests:

```bash
pytest
```

### Run with verbose output:

```bash
pytest -v
```

### Run specific test file:

```bash
pytest tests/test_utils.py
```

### Run specific test class:

```bash
pytest tests/test_utils.py::TestParseDndEndTime
```

### Run specific test function:

```bash
pytest tests/test_utils.py::TestParseDndEndTime::test_parse_unix_timestamp_int
```

## Coverage Reports

### Generate coverage report in terminal:

```bash
pytest --cov=src/mm_loc_setter --cov-report=term-missing
```

### Generate HTML coverage report:

```bash
pytest --cov=src/mm_loc_setter --cov-report=html
open htmlcov/index.html
```

### Generate coverage badge:

```bash
pytest --cov=src/mm_loc_setter --cov-report=term:skip-covered
```

## Test Structure

Tests are organized by module in the `tests/` directory:

- **test_utils.py** - Utility function tests (DND time parsing, absence datetime parsing)
- **test_config.py** - Configuration loading tests
- **test_detectors.py** - Meeting detection tests (Zoom, Teams, Webex)
- **test_network.py** - Network connectivity tests
- **test_status.py** - Status management and absence period tests
- **test_api.py** - Mattermost API client tests
- **conftest.py** - Pytest fixtures and configuration

## Test Coverage Summary

Current coverage: **65.92%**

Module coverage:
- `api/client.py` - 85.12%
- `status/absence.py` - 96.43%
- `utils.py` - 94.34%
- `config/loader.py` - 92.86%
- `detectors/meeting.py` - 92.00%
- `network/connectivity.py` - 85.00%
- `logging_setup.py` - 91.67%
- `commands/cli.py` - 0.00% (integration tests recommended)
- `main.py` - 0.00% (entry point)
- `status/manager.py` - 18.92% (needs more tests)

## Testing Best Practices

### Mocking

Tests use `unittest.mock` for mocking external dependencies:

```python
@patch('mm_loc_setter.api.client.requests.get')
def test_fetch_user_id_success(self, mock_get):
    """Test successful user ID fetch."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'id': 'user123'}
    mock_get.return_value = mock_response
    
    result = fetch_user_id_from_api(retries=3, delay=1)
    assert result == 'user123'
```

### Fixtures

Reusable test data is defined in fixtures in `conftest.py`:

```python
@pytest.fixture
def mock_config_values():
    """Provide mock configuration values."""
    return {
        'MATTERMOST_URL': 'https://test.example.com',
        'ACCESS_TOKEN': 'test-token-123',
        # ...
    }
```

### Assertions

Clear and specific assertions:

```python
assert result == 'expected_value'
assert result is None
assert result is True
assert 'key' in result
assert len(result) == 5
```

## Writing New Tests

1. Create test function with `test_` prefix
2. Use `@patch` decorator for mocking external calls
3. Use fixtures from `conftest.py` for common test data
4. Write clear docstrings explaining what is being tested
5. Use specific assertions

Example:

```python
@patch('mm_loc_setter.api.client.requests.get')
def test_new_feature(self, mock_get):
    """Test description."""
    # Setup
    mock_response = Mock()
    mock_response.status_code = 200
    mock_get.return_value = mock_response
    
    # Execute
    result = my_function()
    
    # Assert
    assert result is True
    mock_get.assert_called_once()
```

## Continuous Integration

To run tests in CI/CD pipeline:

```bash
pytest --cov=src/mm_loc_setter --cov-report=term --cov-report=xml --tb=short
```

## Troubleshooting

### ModuleNotFoundError

Make sure the package is installed in editable mode:

```bash
pip install -e .
```

### Tests fail with import errors

Verify the import paths in mock patches match actual module structure

### Coverage gaps

Check `--cov-report=term-missing` output to see which lines aren't tested
