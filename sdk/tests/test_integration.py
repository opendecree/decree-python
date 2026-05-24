"""Integration tests — require a live server (set DECREE_TEST_ADDR)."""

from __future__ import annotations

import pytest

import opendecree
from opendecree.errors import NotFoundError
from opendecree.types import FieldUpdate

# ---------------------------------------------------------------------------
# Sync client
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestConfigClientIntegration:
    @pytest.fixture(autouse=True)
    def _client(self, decree_addr: str, live_tenant: str) -> None:
        self.tenant = live_tenant
        self.client = opendecree.ConfigClient(
            decree_addr,
            subject="pytest",
            role="superadmin",
            insecure=True,
        )

    def teardown_method(self) -> None:
        self.client.close()

    def test_set_and_get_string(self) -> None:
        self.client.set(self.tenant, "greeting", "hello")
        assert self.client.get(self.tenant, "greeting") == "hello"

    def test_set_and_get_int(self) -> None:
        self.client.set(self.tenant, "count", 42)
        assert self.client.get(self.tenant, "count", int) == 42

    def test_set_and_get_bool(self) -> None:
        self.client.set(self.tenant, "enabled", True)
        assert self.client.get(self.tenant, "enabled", bool) is True

    def test_set_and_get_float(self) -> None:
        self.client.set(self.tenant, "ratio", 1.5)
        assert self.client.get(self.tenant, "ratio", float) == pytest.approx(1.5)

    def test_get_all_returns_set_fields(self) -> None:
        self.client.set(self.tenant, "greeting", "world")
        self.client.set(self.tenant, "count", 7)
        result = self.client.get_all(self.tenant)
        assert "greeting" in result
        assert "count" in result

    def test_set_many(self) -> None:
        self.client.set_many(
            self.tenant,
            [
                FieldUpdate("greeting", "batch"),
                FieldUpdate("count", 99),
            ],
        )
        assert self.client.get(self.tenant, "greeting") == "batch"
        assert self.client.get(self.tenant, "count", int) == 99

    def test_set_null_clears_field(self) -> None:
        self.client.set(self.tenant, "ratio", 3.14)
        self.client.set_null(self.tenant, "ratio")
        result = self.client.get_all(self.tenant)
        assert result.get("ratio") is None

    def test_get_missing_field_raises_not_found(self) -> None:
        with pytest.raises(NotFoundError):
            self.client.get(self.tenant, "greeting.nonexistent")

    def test_context_manager(self, decree_addr: str, live_tenant: str) -> None:
        with opendecree.ConfigClient(
            decree_addr, subject="pytest", role="superadmin", insecure=True
        ) as c:
            c.set(live_tenant, "greeting", "ctx")
            assert c.get(live_tenant, "greeting") == "ctx"


# ---------------------------------------------------------------------------
# Async client
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestAsyncConfigClientIntegration:
    @pytest.fixture(autouse=True)
    def _client(self, decree_addr: str, live_tenant: str) -> None:
        self.tenant = live_tenant
        self.addr = decree_addr

    async def test_set_and_get_string(self) -> None:
        async with opendecree.AsyncConfigClient(
            self.addr, subject="pytest", role="superadmin", insecure=True
        ) as c:
            await c.set(self.tenant, "greeting", "async-hello")
            assert await c.get(self.tenant, "greeting") == "async-hello"

    async def test_set_and_get_int(self) -> None:
        async with opendecree.AsyncConfigClient(
            self.addr, subject="pytest", role="superadmin", insecure=True
        ) as c:
            await c.set(self.tenant, "count", 10)
            assert await c.get(self.tenant, "count", int) == 10

    async def test_get_all(self) -> None:
        async with opendecree.AsyncConfigClient(
            self.addr, subject="pytest", role="superadmin", insecure=True
        ) as c:
            await c.set(self.tenant, "greeting", "async-all")
            result = await c.get_all(self.tenant)
            assert "greeting" in result

    async def test_get_missing_raises_not_found(self) -> None:
        async with opendecree.AsyncConfigClient(
            self.addr, subject="pytest", role="superadmin", insecure=True
        ) as c:
            with pytest.raises(NotFoundError):
                await c.get(self.tenant, "no.such.field")
