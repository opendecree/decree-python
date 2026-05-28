"""Tests for gRPC channel factory."""

from unittest.mock import MagicMock, patch

import grpc

from opendecree._channel import create_aio_channel, create_channel


class TestCreateChannel:
    def test_insecure(self):
        with patch("opendecree._channel.grpc.insecure_channel") as mock:
            mock.return_value = MagicMock()
            ch = create_channel("localhost:9090")
            mock.assert_called_once()
            assert ch is mock.return_value

    def test_secure_with_credentials(self):
        creds = MagicMock(spec=grpc.ChannelCredentials)
        with patch("opendecree._channel.grpc.secure_channel") as mock:
            mock.return_value = MagicMock()
            ch = create_channel("host:443", credentials=creds)
            mock.assert_called_once()
            assert ch is mock.return_value

    def test_secure_default(self):
        with (
            patch("opendecree._channel.grpc.secure_channel") as mock_sec,
            patch("opendecree._channel.grpc.ssl_channel_credentials") as mock_ssl,
        ):
            mock_sec.return_value = MagicMock()
            ch = create_channel("host:443", insecure=False)
            mock_ssl.assert_called_once()
            mock_sec.assert_called_once()
            assert ch is mock_sec.return_value

    def test_tls_with_token_uses_composite_credentials(self):
        creds = MagicMock(spec=grpc.ChannelCredentials)
        composite = MagicMock(spec=grpc.ChannelCredentials)
        call_creds = MagicMock(spec=grpc.CallCredentials)
        with (
            patch("opendecree._channel.grpc.secure_channel") as mock_sec,
            patch(
                "opendecree._channel.grpc.metadata_call_credentials",
                return_value=call_creds,
            ),
            patch(
                "opendecree._channel.grpc.composite_channel_credentials",
                return_value=composite,
            ) as mock_comp,
        ):
            mock_sec.return_value = MagicMock()
            create_channel("host:443", credentials=creds, token="tok")
            mock_comp.assert_called_once_with(creds, call_creds)
            args = mock_sec.call_args[0]
            assert args[1] is composite

    def test_insecure_with_token_does_not_use_composite(self):
        with patch("opendecree._channel.grpc.insecure_channel") as mock_insecure:
            with patch("opendecree._channel.grpc.composite_channel_credentials") as mock_comp:
                mock_insecure.return_value = MagicMock()
                create_channel("localhost:9090", insecure=True, token="tok")
                mock_insecure.assert_called_once()
                mock_comp.assert_not_called()

    def test_message_size_options_included_when_set(self):
        with patch("opendecree._channel.grpc.insecure_channel") as mock:
            mock.return_value = MagicMock()
            create_channel(
                "localhost:9090",
                max_send_message_length=16 * 1024 * 1024,
                max_recv_message_length=32 * 1024 * 1024,
            )
            _, kwargs = mock.call_args
            opts = dict(kwargs["options"])
            assert opts["grpc.max_send_message_length"] == 16 * 1024 * 1024
            assert opts["grpc.max_receive_message_length"] == 32 * 1024 * 1024

    def test_message_size_options_absent_by_default(self):
        with patch("opendecree._channel.grpc.insecure_channel") as mock:
            mock.return_value = MagicMock()
            create_channel("localhost:9090")
            _, kwargs = mock.call_args
            keys = [k for k, _ in kwargs["options"]]
            assert "grpc.max_send_message_length" not in keys
            assert "grpc.max_receive_message_length" not in keys

    def test_keepalive_override(self):
        with patch("opendecree._channel.grpc.insecure_channel") as mock:
            mock.return_value = MagicMock()
            create_channel("localhost:9090", keepalive_time_ms=60000, keepalive_timeout_ms=5000)
            _, kwargs = mock.call_args
            opts = dict(kwargs["options"])
            assert opts["grpc.keepalive_time_ms"] == 60000
            assert opts["grpc.keepalive_timeout_ms"] == 5000


class TestCreateAioChannel:
    def test_insecure(self):
        with patch("opendecree._channel.grpc.aio.insecure_channel") as mock:
            mock.return_value = MagicMock()
            ch = create_aio_channel("localhost:9090")
            mock.assert_called_once()
            assert ch is mock.return_value

    def test_secure_with_credentials(self):
        creds = MagicMock(spec=grpc.ChannelCredentials)
        with patch("opendecree._channel.grpc.aio.secure_channel") as mock:
            mock.return_value = MagicMock()
            ch = create_aio_channel("host:443", credentials=creds)
            mock.assert_called_once()
            assert ch is mock.return_value

    def test_secure_default(self):
        with (
            patch("opendecree._channel.grpc.aio.secure_channel") as mock_sec,
            patch("opendecree._channel.grpc.ssl_channel_credentials") as mock_ssl,
        ):
            mock_sec.return_value = MagicMock()
            ch = create_aio_channel("host:443", insecure=False)
            mock_ssl.assert_called_once()
            mock_sec.assert_called_once()
            assert ch is mock_sec.return_value

    def test_tls_with_token_uses_composite_credentials(self):
        creds = MagicMock(spec=grpc.ChannelCredentials)
        composite = MagicMock(spec=grpc.ChannelCredentials)
        call_creds = MagicMock(spec=grpc.CallCredentials)
        with (
            patch("opendecree._channel.grpc.aio.secure_channel") as mock_sec,
            patch(
                "opendecree._channel.grpc.metadata_call_credentials",
                return_value=call_creds,
            ),
            patch(
                "opendecree._channel.grpc.composite_channel_credentials",
                return_value=composite,
            ) as mock_comp,
        ):
            mock_sec.return_value = MagicMock()
            create_aio_channel("host:443", credentials=creds, token="tok")
            mock_comp.assert_called_once_with(creds, call_creds)
            args = mock_sec.call_args[0]
            assert args[1] is composite

    def test_insecure_with_token_does_not_use_composite(self):
        with patch("opendecree._channel.grpc.aio.insecure_channel") as mock_insecure:
            with patch("opendecree._channel.grpc.composite_channel_credentials") as mock_comp:
                mock_insecure.return_value = MagicMock()
                create_aio_channel("localhost:9090", insecure=True, token="tok")
                mock_insecure.assert_called_once()
                mock_comp.assert_not_called()

    def test_message_size_options_included_when_set(self):
        with patch("opendecree._channel.grpc.aio.insecure_channel") as mock:
            mock.return_value = MagicMock()
            create_aio_channel(
                "localhost:9090",
                max_send_message_length=16 * 1024 * 1024,
                max_recv_message_length=32 * 1024 * 1024,
            )
            _, kwargs = mock.call_args
            opts = dict(kwargs["options"])
            assert opts["grpc.max_send_message_length"] == 16 * 1024 * 1024
            assert opts["grpc.max_receive_message_length"] == 32 * 1024 * 1024

    def test_message_size_options_absent_by_default(self):
        with patch("opendecree._channel.grpc.aio.insecure_channel") as mock:
            mock.return_value = MagicMock()
            create_aio_channel("localhost:9090")
            _, kwargs = mock.call_args
            keys = [k for k, _ in kwargs["options"]]
            assert "grpc.max_send_message_length" not in keys
            assert "grpc.max_receive_message_length" not in keys

    def test_keepalive_override(self):
        with patch("opendecree._channel.grpc.aio.insecure_channel") as mock:
            mock.return_value = MagicMock()
            create_aio_channel("localhost:9090", keepalive_time_ms=60000, keepalive_timeout_ms=5000)
            _, kwargs = mock.call_args
            opts = dict(kwargs["options"])
            assert opts["grpc.keepalive_time_ms"] == 60000
            assert opts["grpc.keepalive_timeout_ms"] == 5000


def test_token_call_credentials_callback_injects_bearer():
    from opendecree._channel import _token_call_credentials

    captured = []

    def fake_metadata_call_creds(fn):
        captured.append(fn)
        return MagicMock(spec=grpc.CallCredentials)

    with patch(
        "opendecree._channel.grpc.metadata_call_credentials",
        side_effect=fake_metadata_call_creds,
    ):
        _token_call_credentials("secret-tok")

    # Invoke the captured inner callback directly
    received = []
    captured[0](None, lambda meta, err: received.append((meta, err)))
    assert received[0][0] == [("authorization", "Bearer secret-tok")]
    assert received[0][1] is None
