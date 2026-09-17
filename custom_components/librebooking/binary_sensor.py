"""Binary sensor showing whether a LibreBooking resource is currently occupied."""
from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import LibreBookingCoordinator
from .entity import (
    LibreBookingResourceEntity,
    async_setup_resource_entities,
    reservation_booked_by,
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up LibreBooking occupancy binary sensors."""
    async_setup_resource_entities(
        hass, entry, async_add_entities, [LibreBookingOccupancyBinarySensor]
    )


class LibreBookingOccupancyBinarySensor(LibreBookingResourceEntity, BinarySensorEntity):
    """True while a resource has an active reservation."""

    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY
    _attr_translation_key = "occupied"

    def __init__(self, coordinator: LibreBookingCoordinator, resource_id: int) -> None:
        super().__init__(coordinator, resource_id)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{resource_id}_occupied"

    @property
    def is_on(self) -> bool:
        return self.resource_state.current is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        current = self.resource_state.current
        return {
            "resource_id": self._resource_id,
            "booked_by": reservation_booked_by(self.coordinator, current),
            "title": current.get("title") if current else None,
            "reference_number": current.get("referenceNumber") if current else None,
            "until": current.get("endDate") if current else None,
        }
