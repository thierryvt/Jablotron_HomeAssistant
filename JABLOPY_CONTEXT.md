# JabloPy Context for Home Assistant Integration

## Published library

- Package: `jablopy`
- Version: `0.1.0`
- PyPI: https://pypi.org/project/jablopy/
- Source repo: `C:\Users\black\Documents\work\JabloPy`

## Goal

Build a Home Assistant integration that uses `jablopy` as the HA-agnostic protocol and TCP client library.

The Home Assistant repository should contain HA-specific code only. Protocol parsing, TCP reconnect behavior, command builders, and state tracking should stay in `jablopy`.

## Hardware/protocol context

- Alarm panel exposes RS485 through a JA-121T module.
- RS485 is bridged to TCP/IP through a Waveshare RS485-to-Ethernet/WiFi adapter.
- Commands are line-based ASCII.
- Control commands are prefixed with an access code, for example `1234 SETP 1`.
- Events can be responses to commands or unsolicited pushed updates.
- Heartbeat is `OK` every ~10 seconds.
- PRFSTATE is hexadecimal device state, decoded bitwise least-significant-bit first per byte.

## Public library API

Import from `jablopy`:

```python
from jablopy import JablotronClient, JablotronProtocol
```

Important classes/events:

- `JablotronClient`
- `JablotronProtocol`
- `JablotronState`
- `ConnectionEvent`
- `HeartbeatEvent`
- `SectionStateEvent`
- `FlagEvent`
- `PrfStateEvent`
- `CommandErrorEvent`
- `UnknownLineEvent`

Useful constants are also exported from `jablopy`, including section states and flags.

## Client behavior

`JablotronClient.start()` starts a background connection supervisor:

1. Connect to TCP adapter.
2. Emit `ConnectionEvent(connected=True)`.
3. Initial sync: `STATE`, `FLAGS`, `PRFSTATE`.
4. Read incoming lines continuously.
5. On disconnect/error, close connection, emit `ConnectionEvent(connected=False)`, sleep `reconnect_delay`, reconnect.

Commands sent while disconnected raise `RuntimeError("Not connected")`. Commands are intentionally not queued.

## State model

`client.state` exposes current state:

- `sections: dict[int, str]`
- `flags: dict[str, set[int]]`
- `sensors: dict[int, bool]`
- `last_heartbeat`
- `connected`

Helpers:

- `get_section_state(section)`
- `is_flag_active(flag, section)`
- `active_flags_for_section(section)`
- `active_devices()`

## Expected HA integration shape

Recommended HA mapping:

- One coordinator or manager owns a single `JablotronClient`.
- HA entities subscribe to library events through one integration-level listener.
- Section state maps naturally to `alarm_control_panel` entities.
- PRFSTATE devices may become binary sensors, but device names/index mapping should be configurable from the HA integration side.
- Flags like `ENTRY`, `EXIT`, alarms, and warnings may be binary sensors or attributes depending on HA design.

## Important design decisions already made

- `jablopy` remains Home Assistant agnostic.
- Parsing does not depend on knowing which command was sent.
- Pushed updates and command responses are handled the same way.
- Reconnect behavior is internal to the library.
- No command queue across reconnects.
- Sensor/device abstraction was intentionally deferred until the HA side defines configurable metadata mapping.
- Tests were intentionally not prioritized for the first release.

## CLI/library release status

JabloPy `0.1.0` was released on PyPI.

Release checks passed before publication:

- `ruff check .`
- `mypy src`
- `python -m build`
- `python -m twine check dist\*`
- CLI smoke check
