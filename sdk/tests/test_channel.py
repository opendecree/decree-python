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
