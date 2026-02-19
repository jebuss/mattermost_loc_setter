# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.2] - 2026-02-19

### Added
- `get_current_mattermost_status` function in `api/client.py` to fetch the current Mattermost presence status.
- Workday exception handling and retrieval in `config/loader.py` and `commands/cli.py`, allowing specific dates to be marked as non-working days.
- `auto_update` now sets offline status on non-working days and outside working hours.
- `set_status` supports an optional DND end time parameter.

### Changed
- `get_local_ip` now uses Python's `socket` module instead of `ifconfig` for more reliable, cross-platform IP retrieval.
- GitHub Actions workflow event triggers simplified.
- Improved mocking and error handling in local IP retrieval tests.

### Fixed
- Removed unused patch for `get_current_mattermost_status` in status tests.

## [1.0.1] - 2026-02-16

### Added
- Configurable daily working hours via `get_working_hours_for_day` in `config/loader.py`, allowing different start and end times for each weekday.
- Optional `[working_hours.daily]` section in `config.toml.example` to specify per-day working hours. Days not specified fall back to global defaults.
- `TestGetWorkingHoursForDay` test class in `tests/test_config.py` covering default and per-day working hour retrieval.
- GitHub Actions workflows for automated linting (`pylint`) and testing.

### Changed
- Refactored `commands/cli.py` and `config/__init__.py` to use `get_working_hours_for_day` instead of fixed global start/end hour variables.
- `auto_update` now uses per-day working hours for accurate schedule checks.

### Removed
- Unused global working hour variables from the CLI module.

[Unreleased]: https://github.com/jebuss/mattermost_loc_setter/compare/v1.0.2...HEAD
[1.0.2]: https://github.com/jebuss/mattermost_loc_setter/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/jebuss/mattermost_loc_setter/releases/tag/v1.0.1
