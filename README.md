# Jablotron Home Assistant

Home Assistant custom integration for Jablotron alarm panels exposed over an
RS485-to-TCP bridge. The integration uses `jablopy` for the protocol, TCP client,
state tracking, and command building.

The integration is local push: one client connection is kept open to the TCP
adapter, alarm events update Home Assistant entities as they arrive, and entities
do not poll the panel.

## Requirements

- Home Assistant 2026.5 or newer
- A Jablotron panel exposed through a JA-121T RS485 interface
- An RS485-to-Ethernet/WiFi TCP adapter, such as a Waveshare adapter
- Network reachability from Home Assistant to the TCP adapter

Default TCP port: `8899`

## Installation

### HACS

This repository is structured for HACS as a custom repository.

1. In Home Assistant, open HACS.
2. Open the three-dot menu and choose **Custom repositories**.
3. Add this repository URL.
4. Select category **Integration**.
5. Install **Jablotron**.
6. Restart Home Assistant.

### Manual

Copy `custom_components/jablotron` into your Home Assistant configuration
directory:

```text
config/
  custom_components/
    jablotron/
      __init__.py
      manifest.json
      ...
```

Restart Home Assistant after copying the files.

## Initial Configuration

Configure the integration from the Home Assistant UI:

1. Go to **Settings**.
2. Open **Devices & services**.
3. Click **Add integration**.
4. Search for **Jablotron**.
5. Fill in the setup form.

Setup fields:

- `Host`: IP address or hostname of the RS485-to-TCP adapter.
- `Port`: TCP port of the adapter. Default is `8899`.
- `Sections`: Comma-separated alarm section numbers to expose. Examples:
  - `1`
  - `1,2`
  - `1,2,3`
- `PIN`: Optional Jablotron access code.

If `PIN` is configured, Home Assistant can arm/disarm without asking for a code
at action time. If `PIN` is left empty, the alarm entity requires a numeric code
when arming or disarming.

During setup, the integration attempts a short TCP connection check. The setup
will fail if Home Assistant cannot connect to the adapter.

## Options

After setup, open the integration options from:

**Settings** -> **Devices & services** -> **Jablotron** -> **Configure**

Options fields:

- `Sections`: Comma-separated section numbers to expose as alarm panels and
  section-scoped binary sensors.
- `Reconnect delay`: Seconds to wait before reconnecting after a TCP disconnect.
  Default is `5`.
- `PRFSTATE device mappings`: JSON mapping from Jablotron PRFSTATE device number
  to Home Assistant binary sensor metadata.

Changing options reloads the integration.

## Alarm Panel Entities

The integration creates one `alarm_control_panel` entity per configured section.

Example entity names:

- `alarm_control_panel.jablotron_section_1`
- `alarm_control_panel.jablotron_section_2`

Supported actions:

- Arm away: fully arms the section.
- Arm home: partially arms the section.
- Disarm: disarms the section.

Jablotron state mapping:

| Jablotron state or flag | Home Assistant alarm state |
| --- | --- |
| `ARMED` | `armed_away` |
| `ARMED_PART` | `armed_home` |
| `READY` | `disarmed` |
| `OFF` | `disarmed` |
| `EXIT` flag active | `arming` |
| `ENTRY` flag active | `pending` |
| `FIRE_ALARM`, `INTRUDER_ALARM`, or `PANIC_ALARM` active | `triggered` |

Alarm entities expose these extra attributes:

- `section`: Jablotron section number.
- `jablotron_state`: Raw section state from the panel.
- `active_flags`: Active Jablotron flags for that section.

## Binary Sensor Entities

The integration creates these binary sensors automatically.

### Connection

One connection sensor is created for the TCP adapter:

- `binary_sensor.jablotron_connection`

Device class: `connectivity`

This sensor is `on` when the integration is connected to the TCP adapter.

### Section Flags

For each configured section, the integration creates section-scoped flag sensors:

| Sensor name | Jablotron flag | Device class |
| --- | --- | --- |
| `Section N Entry Delay` | `ENTRY` | `problem` |
| `Section N Exit Delay` | `EXIT` | `problem` |
| `Section N Internal Warning` | `INTERNAL_WARNING` | `problem` |
| `Section N External Warning` | `EXTERNAL_WARNING` | `problem` |
| `Section N Fire Alarm` | `FIRE_ALARM` | `smoke` |
| `Section N Intruder Alarm` | `INTRUDER_ALARM` | `safety` |
| `Section N Panic Alarm` | `PANIC_ALARM` | `safety` |

Each flag sensor exposes:

- `section`: Jablotron section number.
- `flag`: Raw Jablotron flag name.

### PRFSTATE Device Sensors

PRFSTATE devices are only exposed when you map a device number in integration
options. These are binary sensors backed by the PRFSTATE bitfield.

PRFSTATE values mean:

- `off`: device state is `0`, meaning OK/not triggered.
- `on`: device state is `1`, meaning triggered/active.

Each mapped PRFSTATE sensor exposes:

- `device_number`: Raw PRFSTATE device number.

## PRFSTATE Device Mapping

Configure PRFSTATE mappings in the integration options field
`PRFSTATE device mappings`.

The value must be a JSON object. Keys are PRFSTATE device numbers. Each value
must contain a `name` and may contain a Home Assistant binary sensor
`device_class`.

Example:

```json
{
  "0": {
    "name": "Front Door",
    "device_class": "door"
  },
  "1": {
    "name": "Hall Motion",
    "device_class": "motion"
  },
  "5": {
    "name": "Garage Contact",
    "device_class": "garage_door"
  },
  "9": {
    "name": "Utility Room Sensor"
  }
}
```

If `device_class` is missing or invalid, the integration falls back to
`problem`.

Common useful binary sensor device classes:

- `door`
- `window`
- `motion`
- `garage_door`
- `opening`
- `smoke`
- `safety`
- `problem`

## Finding PRFSTATE Device Numbers

The integration exposes only mapped PRFSTATE devices. To build the mapping:

1. Trigger one physical sensor at a time.
2. Observe the raw PRFSTATE device number from `jablopy`, logs, or temporary
   debugging.
3. Add that device number to the `PRFSTATE device mappings` JSON.
4. Reload or save the integration options.

Device numbering comes from the Jablotron PRFSTATE bitfield decoded by
`jablopy`.

## Example Configuration

Initial setup:

- `Host`: `192.168.1.140`
- `Port`: `8899`
- `Sections`: `1,2`
- `PIN`: leave empty if you want Home Assistant to ask for the code

Options:

- `Sections`: `1,2`
- `Reconnect delay`: `5`
- `PRFSTATE device mappings`:

```json
{
  "0": {
    "name": "Front Door",
    "device_class": "door"
  },
  "1": {
    "name": "Living Room Motion",
    "device_class": "motion"
  }
}
```

Expected entities:

- `alarm_control_panel.jablotron_section_1`
- `alarm_control_panel.jablotron_section_2`
- `binary_sensor.jablotron_connection`
- `binary_sensor.jablotron_section_1_entry_delay`
- `binary_sensor.jablotron_section_1_exit_delay`
- `binary_sensor.jablotron_section_2_entry_delay`
- `binary_sensor.jablotron_section_2_exit_delay`
- `binary_sensor.jablotron_front_door`
- `binary_sensor.jablotron_living_room_motion`

Entity IDs can vary if Home Assistant has already used the same name.

## Development

This project targets Home Assistant 2026.5 or newer.

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

Current development dependency baseline:

- Python 3.14
- Home Assistant 2026.5.4
- `jablopy==0.1.0`

Run validation:

```powershell
.\.venv\Scripts\python.exe -m compileall custom_components tests
.\.venv\Scripts\python.exe -m pytest
```
