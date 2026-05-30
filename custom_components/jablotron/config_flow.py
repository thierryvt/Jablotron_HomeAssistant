"""Config flow for the Jablotron integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN


class JablotronConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Jablotron."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, object] | None = None,
    ) -> FlowResult:
        """Handle the initial setup step."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
            errors={},
        )
