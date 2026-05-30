"""Home Assistant integration for Jablotron alarm panels."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant

from .const import CONF_RECONNECT_DELAY, DEFAULT_PORT, DEFAULT_RECONNECT_DELAY
from .hub import JablotronHub

PLATFORMS: list[Platform] = [Platform.ALARM_CONTROL_PANEL, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Jablotron from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)
    reconnect_delay = entry.options.get(
        CONF_RECONNECT_DELAY,
        DEFAULT_RECONNECT_DELAY,
    )

    hub = JablotronHub(hass, host, port, reconnect_delay)
    await hub.async_start()

    entry.runtime_data = hub
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Jablotron config entry."""
    hub: JablotronHub = entry.runtime_data
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        await hub.async_stop()

    return unload_ok
