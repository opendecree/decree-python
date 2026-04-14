# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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

[0.1.0]: https://github.com/opendecree/decree-python/releases/tag/v0.1.0
