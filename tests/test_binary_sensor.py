"""Tests for Jablotron binary sensors."""

from __future__ import annotations

from types import SimpleNamespace

from jablopy import FLAG_ENTRY, JablotronState

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import CONF_HOST, CONF_PORT

from custom_components.jablotron.binary_sensor import (
    JablotronFlagBinarySensor,
    JablotronPrfStateBinarySensor,
    _device_class_from_mapping,
)


def _entry() -> SimpleNamespace:
    """Create a fake config entry."""
    return SimpleNamespace(data={CONF_HOST: "127.0.0.1", CONF_PORT: 8899})


def test_flag_binary_sensor_reads_flag_state() -> None:
    """Test flag binary sensor state."""
    hub = SimpleNamespace(
        state=JablotronState(connected=True, flags={FLAG_ENTRY: {1}})
    )
    entity = JablotronFlagBinarySensor(
        hub=hub,
        entry=_entry(),
        section=1,
        key="entry_delay",
        name="Entry Delay",
        flag=FLAG_ENTRY,
        device_class=BinarySensorDeviceClass.PROBLEM,
    )

    assert entity.available is True
    assert entity.is_on is True
    assert entity.translation_key == "entry_delay"


def test_prfstate_binary_sensor_reads_mapped_device_state() -> None:
    """Test PRFSTATE binary sensor state."""
    hub = SimpleNamespace(
        state=JablotronState(connected=True, sensors={0: False, 1: True})
    )
    entity = JablotronPrfStateBinarySensor(
        hub=hub,
        entry=_entry(),
        device_number=1,
        name="Front Door",
        device_class=BinarySensorDeviceClass.DOOR,
    )

    assert entity.available is True
    assert entity.is_on is True


def test_device_class_from_mapping() -> None:
    """Test PRFSTATE device class mapping."""
    assert _device_class_from_mapping({"device_class": "door"}) is (
        BinarySensorDeviceClass.DOOR
    )
    assert _device_class_from_mapping({}) is BinarySensorDeviceClass.PROBLEM
    assert _device_class_from_mapping({"device_class": "not-valid"}) is (
        BinarySensorDeviceClass.PROBLEM
    )
