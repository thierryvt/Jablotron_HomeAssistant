"""Tests for Jablotron alarm control panel state mapping."""

from __future__ import annotations

from types import SimpleNamespace

from jablopy import (
    FLAG_ENTRY,
    FLAG_EXIT,
    FLAG_INTRUDER_ALARM,
    SECTION_ARMED,
    SECTION_ARMED_PART,
    SECTION_READY,
    JablotronState,
)

from homeassistant.components.alarm_control_panel import AlarmControlPanelState
from homeassistant.const import CONF_HOST, CONF_PORT

from custom_components.jablotron.alarm_control_panel import (
    JablotronAlarmControlPanel,
)


def _entity(state: JablotronState) -> JablotronAlarmControlPanel:
    """Create an alarm entity with a fake hub and config entry."""
    hub = SimpleNamespace(state=state)
    entry = SimpleNamespace(data={CONF_HOST: "127.0.0.1", CONF_PORT: 8899})
    return JablotronAlarmControlPanel(hub, entry, 1)


def test_alarm_state_maps_section_states() -> None:
    """Test section state mapping."""
    state = JablotronState(connected=True, sections={1: SECTION_READY})
    assert _entity(state).alarm_state is AlarmControlPanelState.DISARMED

    state.sections[1] = SECTION_ARMED_PART
    assert _entity(state).alarm_state is AlarmControlPanelState.ARMED_HOME

    state.sections[1] = SECTION_ARMED
    assert _entity(state).alarm_state is AlarmControlPanelState.ARMED_AWAY


def test_alarm_flags_have_priority_over_section_state() -> None:
    """Test flag priority for delay and alarm states."""
    state = JablotronState(
        connected=True,
        sections={1: SECTION_READY},
        flags={FLAG_EXIT: {1}},
    )
    assert _entity(state).alarm_state is AlarmControlPanelState.ARMING

    state.flags = {FLAG_ENTRY: {1}}
    assert _entity(state).alarm_state is AlarmControlPanelState.PENDING

    state.flags = {FLAG_INTRUDER_ALARM: {1}, FLAG_ENTRY: {1}}
    assert _entity(state).alarm_state is AlarmControlPanelState.TRIGGERED
