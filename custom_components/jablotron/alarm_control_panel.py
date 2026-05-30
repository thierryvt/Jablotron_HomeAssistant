"""Alarm control panel platform for the Jablotron integration."""

from __future__ import annotations

from typing import Any

from jablopy import (
    FLAG_ENTRY,
    FLAG_EXIT,
    FLAG_FIRE_ALARM,
    FLAG_INTRUDER_ALARM,
    FLAG_PANIC_ALARM,
    SECTION_ARMED,
    SECTION_ARMED_PART,
    SECTION_OFF,
    SECTION_READY,
    JablotronEvent,
)

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
    CodeFormat,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    CONF_PIN,
    CONF_SECTIONS,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SECTION,
    DOMAIN,
)
from .hub import JablotronHub

ALARM_FLAGS = frozenset({FLAG_FIRE_ALARM, FLAG_INTRUDER_ALARM, FLAG_PANIC_ALARM})


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Jablotron alarm control panel entities."""
    hub: JablotronHub = entry.runtime_data
    sections = entry.options.get(
        CONF_SECTIONS,
        entry.data.get(CONF_SECTIONS, [DEFAULT_SECTION]),
    )

    async_add_entities(
        JablotronAlarmControlPanel(hub, entry, int(section)) for section in sections
    )


class JablotronAlarmControlPanel(AlarmControlPanelEntity):
    """Representation of a Jablotron alarm section."""

    _attr_has_entity_name = True
    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_AWAY
        | AlarmControlPanelEntityFeature.ARM_HOME
    )

    def __init__(
        self,
        hub: JablotronHub,
        entry: ConfigEntry,
        section: int,
    ) -> None:
        self._hub = hub
        self._entry = entry
        self._section = section

        host = entry.data[CONF_HOST]
        port = entry.data.get(CONF_PORT, DEFAULT_PORT)

        self._attr_name = f"Section {section}"
        self._attr_translation_key = "section"
        self._attr_unique_id = f"{host}_{port}_section_{section}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{host}:{port}")},
            name=DEFAULT_NAME,
            manufacturer="Jablotron",
        )

    @property
    def available(self) -> bool:
        """Return whether the alarm panel is available."""
        return self._hub.state.connected

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        """Return the alarm state."""
        if any(
            self._hub.state.is_flag_active(flag, self._section)
            for flag in ALARM_FLAGS
        ):
            return AlarmControlPanelState.TRIGGERED

        if self._hub.state.is_flag_active(FLAG_ENTRY, self._section):
            return AlarmControlPanelState.PENDING

        if self._hub.state.is_flag_active(FLAG_EXIT, self._section):
            return AlarmControlPanelState.ARMING

        section_state = self._hub.state.get_section_state(self._section)

        if section_state == SECTION_ARMED:
            return AlarmControlPanelState.ARMED_AWAY

        if section_state == SECTION_ARMED_PART:
            return AlarmControlPanelState.ARMED_HOME

        if section_state in {SECTION_READY, SECTION_OFF}:
            return AlarmControlPanelState.DISARMED

        return None

    @property
    def code_format(self) -> CodeFormat | None:
        """Return the code format."""
        if self._stored_pin:
            return None

        return CodeFormat.NUMBER

    @property
    def code_arm_required(self) -> bool:
        """Return whether a code is required to arm."""
        return not self._stored_pin

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return Jablotron-specific state attributes."""
        return {
            "section": self._section,
            "jablotron_state": self._hub.state.get_section_state(self._section),
            "active_flags": sorted(
                self._hub.state.active_flags_for_section(self._section)
            ),
        }

    @property
    def _stored_pin(self) -> str | None:
        """Return the stored PIN, if configured."""
        pin = self._entry.data.get(CONF_PIN)

        if not pin:
            return None

        return str(pin)

    async def async_added_to_hass(self) -> None:
        """Subscribe to Jablotron push events."""
        self.async_on_remove(self._hub.async_subscribe(self._handle_jablotron_event))

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Disarm the alarm section."""
        await self._hub.client.disarm(self._resolve_pin(code), self._section)

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        """Arm the alarm section in partial mode."""
        await self._hub.client.arm_partial(self._resolve_pin(code), self._section)

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Arm the alarm section fully."""
        await self._hub.client.arm(self._resolve_pin(code), self._section)

    @callback
    def _handle_jablotron_event(self, event: JablotronEvent) -> None:
        """Handle a Jablotron push event."""
        self.async_write_ha_state()

    def _resolve_pin(self, code: str | None) -> str:
        """Return the action PIN from the runtime code or stored config."""
        pin = code or self._stored_pin

        if not pin:
            raise HomeAssistantError("A PIN is required")

        return pin
