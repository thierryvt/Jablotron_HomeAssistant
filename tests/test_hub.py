"""Tests for the Jablotron integration hub."""

from __future__ import annotations

import asyncio
from typing import Any

from custom_components.jablotron.hub import JablotronHub


class FakeHass:
    """Minimal Home Assistant task scheduler."""

    def async_create_task(
        self,
        target: Any,
        name: str,
    ) -> asyncio.Task[None]:
        """Create an asyncio task."""
        return asyncio.create_task(target, name=name)


class FakeClient:
    """Minimal Jablotron client for refresh scheduling."""

    def __init__(self) -> None:
        self.connected = False
        self.connected_event = asyncio.Event()
        self.prfstate_requests = 0

    async def wait_until_connected(self) -> None:
        """Wait until connected."""
        await self.connected_event.wait()

    async def request_prfstate(self) -> None:
        """Record a PRFSTATE request."""
        self.prfstate_requests += 1


def test_schedule_prfstate_refresh_waits_for_connection() -> None:
    """Test one-shot PRFSTATE refresh scheduling."""
    async def test() -> None:
        hub = JablotronHub(FakeHass(), "127.0.0.1", 8899)
        client = FakeClient()
        hub.client = client
        hub._started = True

        hub.async_schedule_prfstate_refresh()
        hub.async_schedule_prfstate_refresh()

        task = hub._prfstate_refresh_task
        assert task is not None
        assert client.prfstate_requests == 0

        client.connected = True
        client.connected_event.set()
        await task

        assert client.prfstate_requests == 1

    asyncio.run(test())
