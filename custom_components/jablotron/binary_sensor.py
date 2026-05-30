"""Binary sensor platform for the Jablotron integration."""

from __future__ import annotations

from typing import Any

from jablopy import (
    FLAG_ENTRY,
    FLAG_EXIT,
    FLAG_EXTERNAL_WARNING,
    FLAG_FIRE_ALARM,
    FLAG_INTERNAL_WARNING,
    FLAG_INTRUDER_ALARM,
    FLAG_PANIC_ALARM,
    JablotronEvent,
)

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    CONF_DEVICE_MAPPINGS,
    CONF_SECTIONS,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SECTION,
    DOMAIN,
)
from .hub import JablotronHub

FLAG_BINARY_SENSORS: tuple[tuple[str, str, str, BinarySensorDeviceClass], ...] = (
    ("entry_delay", "Entry Delay", FLAG_ENTRY, BinarySensorDeviceClass.PROBLEM),
    ("exit_delay", "Exit Delay", FLAG_EXIT, BinarySensorDeviceClass.PROBLEM),
    (
        "internal_warning",
        "Internal Warning",
        FLAG_INTERNAL_WARNING,
        BinarySensorDeviceClass.PROBLEM,
    ),
    (
        "external_warning",
        "External Warning",
        FLAG_EXTERNAL_WARNING,
        BinarySensorDeviceClass.PROBLEM,
    ),
    ("fire_alarm", "Fire Alarm", FLAG_FIRE_ALARM, BinarySensorDeviceClass.SMOKE),
    (
        "intruder_alarm",
        "Intruder Alarm",
        FLAG_INTRUDER_ALARM,
        BinarySensorDeviceClass.SAFETY,
    ),
    ("panic_alarm", "Panic Alarm", FLAG_PANIC_ALARM, BinarySensorDeviceClass.SAFETY),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Jablotron binary sensor entities."""
    hub: JablotronHub = entry.runtime_data
    sections = entry.options.get(
        CONF_SECTIONS,
        entry.data.get(CONF_SECTIONS, [DEFAULT_SECTION]),
    )
    device_mappings = entry.options.get(CONF_DEVICE_MAPPINGS, {})

    entities: list[BinarySensorEntity] = [
        JablotronConnectionBinarySensor(hub, entry),
    ]

    for section in sections:
        section = int(section)

        entities.extend(
            JablotronFlagBinarySensor(
                hub=hub,
                entry=entry,
                section=section,
                key=key,
                name=name,
                flag=flag,
                device_class=device_class,
            )
            for key, name, flag, device_class in FLAG_BINARY_SENSORS
        )

    entities.extend(
        JablotronPrfStateBinarySensor(
            hub=hub,
            entry=entry,
            device_number=int(device_number),
            name=str(mapping["name"]),
            device_class=_device_class_from_mapping(mapping),
        )
        for device_number, mapping in device_mappings.items()
    )

    async_add_entities(entities)


class JablotronBinarySensorEntity(BinarySensorEntity):
    """Base class for Jablotron binary sensors."""

    _attr_has_entity_name = True

    def __init__(self, hub: JablotronHub, entry: ConfigEntry) -> None:
        self._hub = hub
        self._entry = entry

        host = entry.data[CONF_HOST]
        port = entry.data.get(CONF_PORT, DEFAULT_PORT)

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{host}:{port}")},
            name=DEFAULT_NAME,
            manufacturer="Jablotron",
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to Jablotron push events."""
        self.async_on_remove(self._hub.async_subscribe(self._handle_jablotron_event))

    @callback
    def _handle_jablotron_event(self, event: JablotronEvent) -> None:
        """Handle a Jablotron push event."""
        self.async_write_ha_state()


class JablotronConnectionBinarySensor(JablotronBinarySensorEntity):
    """Binary sensor for Jablotron client connectivity."""

    _attr_name = "Connection"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, hub: JablotronHub, entry: ConfigEntry) -> None:
        super().__init__(hub, entry)
        host = entry.data[CONF_HOST]
        port = entry.data.get(CONF_PORT, DEFAULT_PORT)
        self._attr_unique_id = f"{host}_{port}_connection"

    @property
    def is_on(self) -> bool:
        """Return whether the TCP adapter is connected."""
        return self._hub.state.connected


class JablotronFlagBinarySensor(JablotronBinarySensorEntity):
    """Binary sensor for a section-scoped Jablotron flag."""

    def __init__(
        self,
        hub: JablotronHub,
        entry: ConfigEntry,
        section: int,
        key: str,
        name: str,
        flag: str,
        device_class: BinarySensorDeviceClass,
    ) -> None:
        super().__init__(hub, entry)
        self._section = section
        self._flag = flag

        host = entry.data[CONF_HOST]
        port = entry.data.get(CONF_PORT, DEFAULT_PORT)

        self._attr_name = f"Section {section} {name}"
        self._attr_unique_id = f"{host}_{port}_section_{section}_{key}"
        self._attr_device_class = device_class

    @property
    def available(self) -> bool:
        """Return whether the alarm panel is available."""
        return self._hub.state.connected

    @property
    def is_on(self) -> bool:
        """Return whether the flag is active for the section."""
        return self._hub.state.is_flag_active(self._flag, self._section)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return Jablotron-specific state attributes."""
        return {
            "section": self._section,
            "flag": self._flag,
        }


class JablotronPrfStateBinarySensor(JablotronBinarySensorEntity):
    """Binary sensor for a mapped PRFSTATE device bit."""

    def __init__(
        self,
        hub: JablotronHub,
        entry: ConfigEntry,
        device_number: int,
        name: str,
        device_class: BinarySensorDeviceClass | None,
    ) -> None:
        super().__init__(hub, entry)
        self._device_number = device_number

        host = entry.data[CONF_HOST]
        port = entry.data.get(CONF_PORT, DEFAULT_PORT)

        self._attr_name = name
        self._attr_unique_id = f"{host}_{port}_prfstate_{device_number}"
        self._attr_device_class = device_class

    @property
    def available(self) -> bool:
        """Return whether the mapped device state is available."""
        return (
            self._hub.state.connected
            and self._device_number in self._hub.state.sensors
        )

    @property
    def is_on(self) -> bool | None:
        """Return whether the PRFSTATE device bit is active."""
        return self._hub.state.sensors.get(self._device_number)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return Jablotron-specific state attributes."""
        return {
            "device_number": self._device_number,
        }


def _device_class_from_mapping(
    mapping: dict[str, str],
) -> BinarySensorDeviceClass | None:
    """Return a HA binary sensor device class from a mapping config."""
    device_class = mapping.get("device_class")

    if not device_class:
        return BinarySensorDeviceClass.PROBLEM

    try:
        return BinarySensorDeviceClass(device_class)
    except ValueError:
        return BinarySensorDeviceClass.PROBLEM
