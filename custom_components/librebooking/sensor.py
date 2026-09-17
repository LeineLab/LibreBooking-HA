"""Sensors for the next reservation and the current 'booked until' time."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import homeassistant.util.dt as dt_util

from .coordinator import LibreBookingCoordinator
from .entity import (
    LibreBookingResourceEntity,
    async_setup_resource_entities,
    reservation_booked_by,
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up LibreBooking timestamp sensors."""
    async_setup_resource_entities(
        hass,
        entry,
        async_add_entities,
        [LibreBookingBookedUntilSensor, LibreBookingNextReservationSensor],
    )


def _parse(value: str | None) -> datetime | None:
    if not value:
        return None
    return dt_util.parse_datetime(value)


class LibreBookingBookedUntilSensor(LibreBookingResourceEntity, SensorEntity):
    """Timestamp of when the current reservation (if any) ends."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_translation_key = "booked_until"

    def __init__(self, coordinator: LibreBookingCoordinator, resource_id: int) -> None:
        super().__init__(coordinator, resource_id)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{resource_id}_booked_until"

    @property
    def native_value(self) -> datetime | None:
        current = self.resource_state.current
        return _parse(current.get("endDate")) if current else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        current = self.resource_state.current
        return {
            "resource_id": self._resource_id,
            "booked_by": reservation_booked_by(self.coordinator, current),
            "title": current.get("title") if current else None,
        }


class LibreBookingNextReservationSensor(LibreBookingResourceEntity, SensorEntity):
    """Timestamp of the next upcoming reservation for this resource."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_translation_key = "next_reservation"

    def __init__(self, coordinator: LibreBookingCoordinator, resource_id: int) -> None:
        super().__init__(coordinator, resource_id)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{resource_id}_next_reservation"

    @property
    def native_value(self) -> datetime | None:
        next_reservation = self.resource_state.next
        return _parse(next_reservation.get("startDate")) if next_reservation else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        next_reservation = self.resource_state.next
        return {
            "resource_id": self._resource_id,
            "booked_by": reservation_booked_by(self.coordinator, next_reservation),
            "title": next_reservation.get("title") if next_reservation else None,
            "ends": next_reservation.get("endDate") if next_reservation else None,
            "reference_number": (
                next_reservation.get("referenceNumber") if next_reservation else None
            ),
        }
