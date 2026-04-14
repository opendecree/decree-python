"""Tests for auth interceptors."""

from unittest.mock import MagicMock

from opendecree._interceptors import AuthInterceptor, _build_metadata, _inject_metadata


class TestBuildMetadata:
    def test_subject_and_role(self):
        md = _build_metadata(subject="alice", role="admin", tenant_id=None, token=None)
        assert ("x-subject", "alice") in md
        assert ("x-role", "admin") in md

    def test_with_tenant(self):
        md = _build_metadata(subject="alice", role="admin", tenant_id="t1", token=None)
        assert ("x-tenant-id", "t1") in md

    def test_token_overrides_metadata(self):
        md = _build_metadata(subject="alice", role="admin", tenant_id="t1", token="tok123")
        assert md == [("authorization", "Bearer tok123")]

    def test_empty_when_nothing_set(self):
        md = _build_metadata(subject=None, role="", tenant_id=None, token=None)
        assert md == []


class TestAuthInterceptor:
    def test_unary_unary(self):
        interceptor = AuthInterceptor([("x-subject", "test")])
        continuation = MagicMock()
        details = MagicMock()
        details.metadata = []
        request = MagicMock()

        interceptor.intercept_unary_unary(continuation, details, request)
        continuation.assert_called_once()
        new_details = continuation.call_args[0][0]
        assert ("x-subject", "test") in list(new_details.metadata)

    def test_unary_stream(self):
        interceptor = AuthInterceptor([("x-role", "admin")])
        continuation = MagicMock()
        details = MagicMock()
        details.metadata = [("existing", "header")]
        request = MagicMock()

        interceptor.intercept_unary_stream(continuation, details, request)
        continuation.assert_called_once()
        new_details = continuation.call_args[0][0]
        metadata = list(new_details.metadata)
        assert ("existing", "header") in metadata
        assert ("x-role", "admin") in metadata


class TestInjectMetadata:
    def test_appends_to_existing(self):
        details = MagicMock()
        details.metadata = [("a", "1")]
        details.method = "test"
        details.timeout = 5.0
        details.credentials = None

        result = _inject_metadata(details, [("b", "2")])
        assert ("a", "1") in list(result.metadata)
        assert ("b", "2") in list(result.metadata)

    def test_handles_none_metadata(self):
        details = MagicMock()
        details.metadata = None
        details.method = "test"
        details.timeout = None
        details.credentials = None

        result = _inject_metadata(details, [("x", "y")])
        assert list(result.metadata) == [("x", "y")]
