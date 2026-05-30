# Jablotron Home Assistant

Home Assistant custom integration for Jablotron alarm panels exposed over a
TCP bridge, using `jablopy` for the HA-independent protocol/client layer.

## Development

This project targets Home Assistant 2026.5 or newer.

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```
