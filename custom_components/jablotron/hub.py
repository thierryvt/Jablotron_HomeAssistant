"""Runtime hub for the Jablotron integration."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import suppress
import logging

from jablopy import JablotronClient, JablotronEvent, JablotronState

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback

from .const import DEFAULT_RECONNECT_DELAY

_LOGGER = logging.getLogger(__name__)

JablotronEventCallback = Callable[[JablotronEvent], None]


class JablotronHub:
    """Own the Jablotron client and distribute push updates to HA entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        reconnect_delay: float = DEFAULT_RECONNECT_DELAY,
    ) -> None:
        self.hass = hass
        self.host = host
        self.port = port

        self.client = JablotronClient(
            host=host,
            port=port,
            reconnect_delay=reconnect_delay,
        )
        self._listeners: set[JablotronEventCallback] = set()
        self._prfstate_refresh_task: asyncio.Task[None] | None = None
        self._started = False

    @property
    def state(self) -> JablotronState:
        """Return the latest Jablotron state snapshot."""
        return self.client.state

    async def async_start(self) -> None:
        """Start the Jablotron client."""
        if self._started:
            return

        self.client.add_listener(self._handle_jablotron_event)
        await self.client.start()
        self._started = True
        _LOGGER.debug("Started Jablotron client for %s:%s", self.host, self.port)

    async def async_stop(self) -> None:
        """Stop the Jablotron client."""
        if not self._started:
            return

        self._started = False
        if self._prfstate_refresh_task:
            self._prfstate_refresh_task.cancel()

            with suppress(asyncio.CancelledError):
                await self._prfstate_refresh_task

            self._prfstate_refresh_task = None

        self.client.remove_listener(self._handle_jablotron_event)
        await self.client.stop()
        self._listeners.clear()
        _LOGGER.debug("Stopped Jablotron client for %s:%s", self.host, self.port)

    @callback
    def async_schedule_prfstate_refresh(self) -> None:
        """Schedule a one-shot PRFSTATE refresh once connected."""
        if self._prfstate_refresh_task and not self._prfstate_refresh_task.done():
            return

        self._prfstate_refresh_task = self.hass.async_create_task(
            self._async_request_prfstate_when_connected(),
            "jablotron prfstate refresh",
        )

    async def _async_request_prfstate_when_connected(self) -> None:
        """Request current PRFSTATE once the client is connected."""
        try:
            await self.client.wait_until_connected()

            if self._started:
                await self.client.request_prfstate()
        except RuntimeError:
            _LOGGER.debug("Skipped PRFSTATE refresh while disconnected")

    @callback
    def async_subscribe(
        self,
        listener: JablotronEventCallback,
    ) -> CALLBACK_TYPE:
        """Subscribe to Jablotron push events."""
        self._listeners.add(listener)

        @callback
        def unsubscribe() -> None:
            self._listeners.discard(listener)

        return unsubscribe

    @callback
    def _handle_jablotron_event(self, event: JablotronEvent) -> None:
        """Forward a Jablotron event to subscribed HA entities."""
        for listener in set(self._listeners):
            try:
                listener(event)
            except Exception:
                _LOGGER.exception("Jablotron HA listener failed")
