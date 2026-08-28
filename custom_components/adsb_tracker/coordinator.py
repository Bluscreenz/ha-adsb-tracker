"""Data update coordinator for ADS-B Aircraft Tracker."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from aiohttp import ClientError

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_HOST,
    CONF_PATH,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    DEFAULT_HOST,
    DEFAULT_PATH,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


def _normalize(value: str | None) -> str:
    """Normalize a tail number / registration / callsign for comparison."""
    if not value:
        return ""
    return value.strip().upper().replace("-", "").replace(" ", "")


class ADSBDataUpdateCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Poll a local dump1090 / readsb / tar1090-style aircraft.json feed."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        host = entry.data.get(CONF_HOST, DEFAULT_HOST)
        port = entry.data.get(CONF_PORT, DEFAULT_PORT)
        path = entry.data.get(CONF_PATH, DEFAULT_PATH)
        self.url = f"http://{host}:{port}{path}"
        scan_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

        self.by_reg: dict[str, dict[str, Any]] = {}
        self.by_flight: dict[str, dict[str, Any]] = {}

        super().__init__(
            hass,
            _LOGGER,
            name="ADS-B Tracker",
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        session = async_get_clientsession(self.hass)
        try:
            async with asyncio.timeout(10):
                resp = await session.get(self.url)
                resp.raise_for_status()
                payload = await resp.json(content_type=None)
        except (ClientError, asyncio.TimeoutError) as err:
            raise UpdateFailed(
                f"Error communicating with ADS-B server at {self.url}: {err}"
            ) from err
        except ValueError as err:
            raise UpdateFailed(f"Invalid JSON received from {self.url}: {err}") from err

        aircraft_list = payload.get("aircraft", [])
        result: dict[str, dict[str, Any]] = {}
        by_reg: dict[str, dict[str, Any]] = {}
        by_flight: dict[str, dict[str, Any]] = {}

        for ac in aircraft_list:
            hex_id = _normalize(ac.get("hex"))
            reg = _normalize(ac.get("r"))
            flight = _normalize(ac.get("flight"))

            entry_data = dict(ac)
            entry_data["_norm_hex"] = hex_id
            entry_data["_norm_reg"] = reg
            entry_data["_norm_flight"] = flight

            if not hex_id:
                continue

            result[hex_id] = entry_data
            if reg:
                by_reg[reg] = entry_data
            if flight:
                by_flight[flight] = entry_data

        self.by_reg = by_reg
        self.by_flight = by_flight
        return result

    def find_aircraft(self, tail_number: str) -> dict[str, Any] | None:
        """Look up an aircraft in the latest poll by tail number / registration.

        Falls back to matching the callsign or raw ICAO hex, in case the
        feeder doesn't have a registration database loaded.
        """
        norm = _normalize(tail_number)
        if not norm:
            return None
        if norm in self.by_reg:
            return self.by_reg[norm]
        if norm in self.by_flight:
            return self.by_flight[norm]
        if self.data and norm in self.data:
            return self.data[norm]
        return None
