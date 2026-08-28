"""Config flow for ADS-B Aircraft Tracker.

Step 1 (config entry): connection details for the local ADS-B server.
Options flow: add / remove tracked tail numbers from the UI, at any time,
without editing YAML or restarting Home Assistant.
"""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_AIRCRAFT,
    CONF_HOST,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME,
    CONF_PATH,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_TAIL_NUMBER,
    DEFAULT_HOST,
    DEFAULT_PATH,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class ADSBTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial setup of the connection to the local ADS-B server."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}

        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(
                title=f"ADS-B Tracker ({user_input[CONF_HOST]})",
                data=user_input,
                options={CONF_AIRCRAFT: []},
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Required(CONF_PATH, default=DEFAULT_PATH): str,
                vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
                vol.Optional(CONF_LATITUDE): vol.Coerce(float),
                vol.Optional(CONF_LONGITUDE): vol.Coerce(float),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "ADSBTrackerOptionsFlow":
        return ADSBTrackerOptionsFlow()


class ADSBTrackerOptionsFlow(config_entries.OptionsFlow):
    """Manage the list of tracked tail numbers from the Home Assistant UI."""

    def __init__(self) -> None:
        # self.config_entry is provided automatically by the base class.
        self._aircraft: list[dict[str, str]] | None = None

    def _load_aircraft(self) -> list[dict[str, str]]:
        if self._aircraft is None:
            self._aircraft = list(self.config_entry.options.get(CONF_AIRCRAFT, []))
        return self._aircraft

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        return self.async_show_menu(
            step_id="init",
            menu_options=["add_aircraft", "remove_aircraft"],
        )

    async def async_step_add_aircraft(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        aircraft = self._load_aircraft()
        if user_input is not None:
            tail = user_input[CONF_TAIL_NUMBER].strip().upper()
            name = user_input.get(CONF_NAME, "").strip() or tail
            if any(a[CONF_TAIL_NUMBER].upper() == tail for a in aircraft):
                errors["base"] = "already_exists"
            else:
                aircraft.append({CONF_TAIL_NUMBER: tail, CONF_NAME: name})
                return self.async_create_entry(title="", data={CONF_AIRCRAFT: aircraft})

        schema = vol.Schema(
            {
                vol.Required(CONF_TAIL_NUMBER): str,
                vol.Optional(CONF_NAME): str,
            }
        )
        return self.async_show_form(step_id="add_aircraft", data_schema=schema, errors=errors)

    async def async_step_remove_aircraft(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        aircraft = self._load_aircraft()
        if not aircraft:
            return self.async_abort(reason="no_aircraft")

        options = {
            a[CONF_TAIL_NUMBER]: f"{a.get(CONF_NAME, a[CONF_TAIL_NUMBER])} ({a[CONF_TAIL_NUMBER]})"
            for a in aircraft
        }

        if user_input is not None:
            selected = set(user_input["tail_numbers"])
            self._aircraft = [a for a in aircraft if a[CONF_TAIL_NUMBER] not in selected]
            return self.async_create_entry(title="", data={CONF_AIRCRAFT: self._aircraft})

        schema = vol.Schema(
            {
                vol.Required("tail_numbers"): cv.multi_select(options),
            }
        )
        return self.async_show_form(step_id="remove_aircraft", data_schema=schema)
