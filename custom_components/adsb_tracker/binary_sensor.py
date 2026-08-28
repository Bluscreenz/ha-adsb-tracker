"""Binary sensor platform for ADS-B Aircraft Tracker.

Creates one binary_sensor per tracked tail number. The sensor is 'on'
whenever that aircraft currently appears in the local ADS-B feed, and
fires an event the moment it goes from not-seen to seen, so automations
(e.g. a mobile app notification) can react immediately.
"""
from __future__ import annotations

import logging
import math
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_ALTITUDE,
    ATTR_DISTANCE,
    ATTR_FLIGHT,
    ATTR_GROUND_SPEED,
    ATTR_HEX,
    ATTR_LAT,
    ATTR_LON,
    ATTR_SQUAWK,
    ATTR_TRACK,
    CONF_AIRCRAFT,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_NAME,
    CONF_TAIL_NUMBER,
    DOMAIN,
    EVENT_AIRCRAFT_SEEN,
)
from .coordinator import ADSBDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: ADSBDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    aircraft_list = entry.options.get(CONF_AIRCRAFT, [])

    entities = [
        AircraftSeenBinarySensor(coordinator, entry, ac[CONF_TAIL_NUMBER], ac.get(CONF_NAME))
        for ac in aircraft_list
    ]
    async_add_entities(entities)


def _haversine_nm(lat1, lon1, lat2, lon2) -> float | None:
    if None in (lat1, lon1, lat2, lon2):
        return None
    try:
        r_nm = 3440.065
        p1, p2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = (
            math.sin(dphi / 2) ** 2
            + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
        )
        return round(2 * r_nm * math.asin(math.sqrt(a)), 1)
    except (TypeError, ValueError):
        return None


class AircraftSeenBinarySensor(CoordinatorEntity[ADSBDataUpdateCoordinator], BinarySensorEntity):
    """Binary sensor that is 'on' whenever a specific tail number is currently received."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.PRESENCE

    def __init__(
        self,
        coordinator: ADSBDataUpdateCoordinator,
        entry: ConfigEntry,
        tail_number: str,
        name: str | None,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._tail_number = tail_number
        self._attr_name = name or tail_number
        self._attr_unique_id = f"{entry.entry_id}_{tail_number}"
        self._was_on = False
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="ADS-B Aircraft Tracker",
            manufacturer="Local ADS-B Receiver",
            model=entry.data.get("host"),
        )

    @property
    def _aircraft(self) -> dict[str, Any] | None:
        return self.coordinator.find_aircraft(self._tail_number)

    @property
    def is_on(self) -> bool:
        return self._aircraft is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        ac = self._aircraft
        if not ac:
            return {"tail_number": self._tail_number}

        lat = ac.get("lat")
        lon = ac.get("lon")
        rx_lat = self._entry.data.get(CONF_LATITUDE)
        rx_lon = self._entry.data.get(CONF_LONGITUDE)

        attrs: dict[str, Any] = {
            "tail_number": self._tail_number,
            ATTR_FLIGHT: (ac.get("flight") or "").strip(),
            ATTR_HEX: ac.get("hex"),
            ATTR_ALTITUDE: ac.get("alt_baro"),
            ATTR_GROUND_SPEED: ac.get("gs"),
            ATTR_TRACK: ac.get("track"),
            ATTR_LAT: lat,
            ATTR_LON: lon,
            ATTR_SQUAWK: ac.get("squawk"),
        }
        distance = _haversine_nm(rx_lat, rx_lon, lat, lon)
        if distance is not None:
            attrs[ATTR_DISTANCE] = distance
        return attrs

    @callback
    def _handle_coordinator_update(self) -> None:
        now_on = self.is_on
        if now_on and not self._was_on:
            self.hass.bus.async_fire(
                EVENT_AIRCRAFT_SEEN,
                {
                    "tail_number": self._tail_number,
                    "name": self._attr_name,
                    "entity_id": self.entity_id,
                    **self.extra_state_attributes,
                },
            )
        self._was_on = now_on
        super()._handle_coordinator_update()
