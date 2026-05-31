"""Tests for OTel opt-in instrumentation flag."""

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest


def _fake_otel_modules() -> dict[str, ModuleType]:
    """Build a minimal fake opentelemetry-instrumentation-grpc module tree."""
    fake_interceptor = MagicMock(name="OpenTelemetryClientInterceptor")
    fake_aio_interceptor = MagicMock(name="OpenTelemetryAioClientInterceptor")

    grpc_mod = ModuleType("opentelemetry.instrumentation.grpc")
    grpc_mod.OpenTelemetryClientInterceptor = fake_interceptor  # type: ignore[attr-defined]

    aio_client_mod = ModuleType("opentelemetry.instrumentation.grpc._aio_client")
    aio_client_mod.OpenTelemetryAioClientInterceptor = fake_aio_interceptor  # type: ignore[attr-defined]

    otel_mod = ModuleType("opentelemetry")
    instr_mod = ModuleType("opentelemetry.instrumentation")

    return {
        "opentelemetry": otel_mod,
        "opentelemetry.instrumentation": instr_mod,
        "opentelemetry.instrumentation.grpc": grpc_mod,
        "opentelemetry.instrumentation.grpc._aio_client": aio_client_mod,
    }


class TestMakeSyncInterceptor:
    def test_returns_interceptor_when_package_installed(self):
        from opendecree._otel import make_sync_interceptor

        with patch.dict(sys.modules, _fake_otel_modules()):
            result = make_sync_interceptor()
        assert result is not None

    def test_raises_import_error_when_not_installed(self):
        from opendecree._otel import make_sync_interceptor

        blocked = {k: None for k in _fake_otel_modules()}  # type: ignore[assignment]
        with patch.dict(sys.modules, blocked):
            with pytest.raises(ImportError, match="opendecree\\[otel\\]"):
                make_sync_interceptor()


class TestMakeAioInterceptors:
    def test_returns_list_when_package_installed(self):
        from opendecree._otel import make_aio_interceptors

        with patch.dict(sys.modules, _fake_otel_modules()):
            result = make_aio_interceptors()
        assert isinstance(result, list)
        assert len(result) == 1

    def test_raises_import_error_when_not_installed(self):
        from opendecree._otel import make_aio_interceptors

        blocked = {k: None for k in _fake_otel_modules()}  # type: ignore[assignment]
        with patch.dict(sys.modules, blocked):
            with pytest.raises(ImportError, match="opendecree\\[otel\\]"):
                make_aio_interceptors()


class TestSyncClientOtel:
    def test_otel_false_does_not_call_make_interceptor(self):
        with patch("opendecree.client.create_channel") as mock_ch:
            mock_ch.return_value = MagicMock()
            with patch("opendecree.client.grpc.intercept_channel"):
                with patch("opendecree._otel.make_sync_interceptor") as mock_otel:
                    import opendecree

                    opendecree.ConfigClient("localhost:9090")
                    mock_otel.assert_not_called()

    def test_otel_true_prepends_interceptor(self):
        fake_otel_interceptor = MagicMock(name="otel_interceptor")

        with patch("opendecree.client.create_channel") as mock_ch:
            mock_ch.return_value = MagicMock()
            with patch("opendecree.client.grpc.intercept_channel") as mock_intercept:
                mock_intercept.return_value = MagicMock()
                with patch.dict(sys.modules, _fake_otel_modules()):
                    # Make make_sync_interceptor return our fake
                    with patch(
                        "opendecree._otel.make_sync_interceptor",
                        return_value=fake_otel_interceptor,
                    ):
                        import opendecree

                        opendecree.ConfigClient("localhost:9090", otel=True)

                interceptors_used = mock_intercept.call_args[0][1:]
                assert interceptors_used[0] is fake_otel_interceptor

    def test_otel_true_otel_before_user_interceptors(self):
        fake_otel_interceptor = MagicMock(name="otel_interceptor")
        user_interceptor = MagicMock(name="user_interceptor")

        with patch("opendecree.client.create_channel") as mock_ch:
            mock_ch.return_value = MagicMock()
            with patch("opendecree.client.grpc.intercept_channel") as mock_intercept:
                mock_intercept.return_value = MagicMock()
                with patch(
                    "opendecree._otel.make_sync_interceptor",
                    return_value=fake_otel_interceptor,
                ):
                    import opendecree

                    opendecree.ConfigClient(
                        "localhost:9090", otel=True, interceptors=[user_interceptor]
                    )

                interceptors_used = mock_intercept.call_args[0][1:]
                otel_idx = list(interceptors_used).index(fake_otel_interceptor)
                user_idx = list(interceptors_used).index(user_interceptor)
                assert otel_idx < user_idx


class TestAsyncClientOtel:
    def test_otel_false_does_not_call_make_interceptors(self):
        with patch("opendecree.async_client.create_aio_channel") as mock_ch:
            mock_ch.return_value = MagicMock()
            with patch("opendecree._otel.make_aio_interceptors") as mock_otel:
                import opendecree

                opendecree.AsyncConfigClient("localhost:9090")
                mock_otel.assert_not_called()

    def test_otel_true_passes_interceptors_to_channel(self):
        fake_otel_interceptor = MagicMock(name="aio_otel_interceptor")

        with patch("opendecree.async_client.create_aio_channel") as mock_ch:
            mock_ch.return_value = MagicMock()
            with patch(
                "opendecree._otel.make_aio_interceptors",
                return_value=[fake_otel_interceptor],
            ):
                import opendecree

                opendecree.AsyncConfigClient("localhost:9090", otel=True)

            interceptors_passed = mock_ch.call_args.kwargs.get("interceptors")
            assert interceptors_passed is not None
            assert fake_otel_interceptor in interceptors_passed

    def test_otel_true_otel_before_user_interceptors(self):
        fake_otel_interceptor = MagicMock(name="aio_otel_interceptor")
        user_interceptor = MagicMock(name="user_interceptor")

        with patch("opendecree.async_client.create_aio_channel") as mock_ch:
            mock_ch.return_value = MagicMock()
            with patch(
                "opendecree._otel.make_aio_interceptors",
                return_value=[fake_otel_interceptor],
            ):
                import opendecree

                opendecree.AsyncConfigClient(
                    "localhost:9090", otel=True, interceptors=[user_interceptor]
                )

            interceptors_passed = mock_ch.call_args.kwargs.get("interceptors")
            otel_idx = interceptors_passed.index(fake_otel_interceptor)
            user_idx = interceptors_passed.index(user_interceptor)
            assert otel_idx < user_idx
