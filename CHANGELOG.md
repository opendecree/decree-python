# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.3.0a1] - 2026-04-27

### Added

- `TimeoutError` (DEADLINE\_EXCEEDED), `ResourceExhaustedError`, `CancelledError`, and
  `UnimplementedError` exception types extending the existing error hierarchy
- `DecreeError` captures `trailing_metadata` from gRPC errors, preserving `google.rpc.RetryInfo`
  and `ErrorInfo` trailers
- `description`, `value_description`, and `expected_checksum` keyword arguments on `set()` and
  `set_many()` for all sync and async client types
- `datetime`, `dict`, `list`, and URL type coercion in value conversion (`convert.py`)
- Dependabot configuration for automated dependency management (Python + GitHub Actions)
- Community health: YAML bug report template and first-interaction welcome bot
- Social preview image and PyPI downloads / repostatus badges in README
- Codecov coverage upload and per-PR coverage reporting

### Changed

- Proto stubs regenerated for decree v0.8.0-alpha.1 and v0.10.0-alpha.1
- Repository migrated from personal GitHub to the [opendecree](https://github.com/opendecree) org
- `server_version` property replaced by `get_server_version()` method on all client classes
  (property was not async-safe)
- CI upgraded: GitHub Actions checkout v6, setup-python v6; CodeQL migrated to advanced setup

### Fixed

- Auth metadata now forwarded to `GetConfig` and `Subscribe` in `AsyncConfigWatcher`
- Insecure Bearer tokens on TLS channels now log a warning; composite channel credentials used
- Sync stream closing without an error now triggers exponential backoff before reconnect
- `ConfigWatcher.stop()` cancels the gRPC stream to prevent thread leaks on shutdown
- `py.typed` marker and `.pyi` stubs now included in the published wheel
- Write operations (`set`, `set_many`, `delete`) no longer retried on `DEADLINE_EXCEEDED`
- Generated proto imports use absolute package paths instead of `sys.path` injection
- `spec_version` field name corrected in example seed (was `syntax`)

## [0.2.0] - 2026-04-14

### Added

- End-to-end examples with seed data, proto generation, and multi-tenant usage
- Multi-tenant usage documentation
- Alpha status disclaimer in README and package classifiers

## [0.1.0] - 2026-04-12

### Added

- ConfigClient (sync) with `@overload` typed `get()` returning str/int/float/bool/timedelta
- AsyncConfigClient mirroring the sync API with async/await
- ConfigWatcher with `WatchedField[T]` for live config subscriptions (background thread)
- AsyncConfigWatcher for asyncio-native subscriptions (background task)
- Error hierarchy mapping gRPC status codes to typed Python exceptions
- Exponential backoff retry with jitter for transient gRPC errors
- Auth metadata interceptors (x-subject, x-role, x-tenant-id, Bearer token)
- Context managers for all client and watcher lifecycles
- `on_change` callbacks and `changes()` iterators on watched fields
- Auto-reconnect with backoff on subscription stream failures

[0.3.0a1]: https://github.com/opendecree/decree-python/releases/tag/v0.3.0a1
[0.2.0]: https://github.com/opendecree/decree-python/releases/tag/v0.2.0
[0.1.0]: https://github.com/opendecree/decree-python/releases/tag/v0.1.0
