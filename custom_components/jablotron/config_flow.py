"""Config flow for the Jablotron integration."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers import selector

from jablopy import JablotronClient

from .const import (
    CONF_DEVICE_MAPPINGS,
    CONF_PIN,
    CONF_RECONNECT_DELAY,
    CONF_SECTIONS,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_RECONNECT_DELAY,
    DEFAULT_SECTION,
    DEFAULT_SETUP_TIMEOUT,
    DOMAIN,
)


class CannotConnectError(Exception):
    """Error to indicate we cannot connect."""


class InvalidDeviceMappingsError(Exception):
    """Error to indicate the device mapping JSON is invalid."""


def _parse_sections(value: str) -> list[int]:
    """Parse a comma-separated section list."""
    sections: list[int] = []

    for raw_section in value.split(","):
        raw_section = raw_section.strip()

        if not raw_section:
            continue

        section = int(raw_section)

        if section <= 0:
            raise ValueError("Section numbers must be positive")

        if section not in sections:
            sections.append(section)

    if not sections:
        raise ValueError("At least one section is required")

    return sections


def _format_sections(sections: list[int]) -> str:
    """Format sections for display in a form field."""
    return ",".join(str(section) for section in sections)


def _parse_device_mappings(value: str) -> dict[str, dict[str, str]]:
    """Parse PRFSTATE device mappings from JSON text."""
    if not value.strip():
        return {}

    try:
        raw_mappings = json.loads(value)
    except json.JSONDecodeError as ex:
        raise InvalidDeviceMappingsError from ex

    if not isinstance(raw_mappings, dict):
        raise InvalidDeviceMappingsError

    mappings: dict[str, dict[str, str]] = {}

    for raw_device, raw_config in raw_mappings.items():
        try:
            device_number = int(raw_device)
        except (TypeError, ValueError) as ex:
            raise InvalidDeviceMappingsError from ex

        if device_number < 0 or not isinstance(raw_config, dict):
            raise InvalidDeviceMappingsError

        name = raw_config.get("name")
        device_class = raw_config.get("device_class")

        if not isinstance(name, str) or not name.strip():
            raise InvalidDeviceMappingsError

        mapping: dict[str, str] = {"name": name.strip()}

        if device_class is not None:
            if not isinstance(device_class, str) or not device_class.strip():
                raise InvalidDeviceMappingsError

            mapping["device_class"] = device_class.strip()

        mappings[str(device_number)] = mapping

    return mappings


def _format_device_mappings(mappings: dict[str, dict[str, str]]) -> str:
    """Format PRFSTATE device mappings for display in a form field."""
    if not mappings:
        return ""

    return json.dumps(mappings, indent=2, sort_keys=True)


async def _async_validate_connection(host: str, port: int) -> None:
    """Validate that the Jablotron TCP adapter can be reached."""
    client = JablotronClient(host=host, port=port)

    try:
        await client.start()
        await client.wait_until_connected(timeout=DEFAULT_SETUP_TIMEOUT)
    except (TimeoutError, OSError, RuntimeError, asyncio.TimeoutError) as ex:
        raise CannotConnectError from ex
    finally:
        await client.stop()


def _user_schema(
    *,
    host: str | None = None,
    port: int = DEFAULT_PORT,
    sections: str = str(DEFAULT_SECTION),
    pin: str = "",
) -> vol.Schema:
    """Return the config flow user step schema."""
    host_key = (
        vol.Required(CONF_HOST, default=host)
        if host
        else vol.Required(CONF_HOST)
    )

    return vol.Schema(
        {
            host_key: selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
            ),
            vol.Required(CONF_PORT, default=port): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=65535,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Required(CONF_SECTIONS, default=sections): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
            ),
            vol.Optional(CONF_PIN, default=pin): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
        }
    )


def _options_schema(
    *,
    sections: str,
    reconnect_delay: float,
    device_mappings: str,
) -> vol.Schema:
    """Return the options flow schema."""
    return vol.Schema(
        {
            vol.Required(CONF_SECTIONS, default=sections): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
            ),
            vol.Required(
                CONF_RECONNECT_DELAY,
                default=reconnect_delay,
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=300,
                    step=1,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="s",
                )
            ),
            vol.Optional(
                CONF_DEVICE_MAPPINGS,
                default=device_mappings,
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    multiline=True,
                    type=selector.TextSelectorType.TEXT,
                )
            ),
        }
    )


class JablotronConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Jablotron."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> JablotronOptionsFlow:
        """Create the options flow."""
        return JablotronOptionsFlow()

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = str(user_input[CONF_HOST]).strip()
            port = int(user_input[CONF_PORT])
            pin = str(user_input.get(CONF_PIN, "")).strip()

            try:
                sections = _parse_sections(str(user_input[CONF_SECTIONS]))
            except ValueError:
                errors[CONF_SECTIONS] = "invalid_sections"
            else:
                self._async_abort_entries_match(
                    {
                        CONF_HOST: host,
                        CONF_PORT: port,
                    }
                )

                try:
                    await _async_validate_connection(host, port)
                except CannotConnectError:
                    errors["base"] = "cannot_connect"
                except Exception:
                    errors["base"] = "unknown"
                else:
                    data: dict[str, Any] = {
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_SECTIONS: sections,
                    }

                    if pin:
                        data[CONF_PIN] = pin

                    return self.async_create_entry(title=DEFAULT_NAME, data=data)

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(
                host=user_input.get(CONF_HOST) if user_input else None,
                port=int(user_input.get(CONF_PORT, DEFAULT_PORT))
                if user_input
                else DEFAULT_PORT,
                sections=str(user_input.get(CONF_SECTIONS, DEFAULT_SECTION))
                if user_input
                else str(DEFAULT_SECTION),
                pin=str(user_input.get(CONF_PIN, "")) if user_input else "",
            ),
            errors=errors,
        )


class JablotronOptionsFlow(config_entries.OptionsFlowWithReload):
    """Handle options for Jablotron."""

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Manage Jablotron options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                sections = _parse_sections(str(user_input[CONF_SECTIONS]))
            except ValueError:
                errors[CONF_SECTIONS] = "invalid_sections"
            else:
                try:
                    device_mappings = _parse_device_mappings(
                        str(user_input.get(CONF_DEVICE_MAPPINGS, ""))
                    )
                except InvalidDeviceMappingsError:
                    errors[CONF_DEVICE_MAPPINGS] = "invalid_device_mappings"
                else:
                    return self.async_create_entry(
                        data={
                            CONF_SECTIONS: sections,
                            CONF_RECONNECT_DELAY: float(
                                user_input[CONF_RECONNECT_DELAY]
                            ),
                            CONF_DEVICE_MAPPINGS: device_mappings,
                        }
                    )

        current_sections = self.config_entry.options.get(
            CONF_SECTIONS,
            self.config_entry.data.get(CONF_SECTIONS, [DEFAULT_SECTION]),
        )
        current_reconnect_delay = self.config_entry.options.get(
            CONF_RECONNECT_DELAY,
            DEFAULT_RECONNECT_DELAY,
        )
        current_device_mappings = self.config_entry.options.get(CONF_DEVICE_MAPPINGS, {})

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(
                sections=_format_sections(current_sections),
                reconnect_delay=float(current_reconnect_delay),
                device_mappings=_format_device_mappings(current_device_mappings),
            ),
            errors=errors,
        )
