"""Shared entity base for LibreBooking."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    NAME_FORMAT_FIRST,
    NAME_FORMAT_LAST,
    NAME_FORMAT_USERNAME,
)
from .coordinator import LibreBookingCoordinator, ResourceState


def reservation_booked_by(
    coordinator: LibreBookingCoordinator, reservation: dict[str, Any] | None
) -> str | None:
    """Return a display name for who holds a reservation.

    Follows the integration's configured name_format, falling back to
    first+last name when a username lookup isn't available (e.g. LibreBooking
    Users API unreachable, or a guest reservation with no username).
    """
    if reservation is None:
        return None

    first_name = reservation.get("firstName") or ""
    last_name = reservation.get("lastName") or ""
    full_name = " ".join(part for part in (first_name, last_name) if part) or None

    name_format = coordinator.name_format
    if name_format == NAME_FORMAT_FIRST:
        return first_name or None
    if name_format == NAME_FORMAT_LAST:
        return last_name or None
    if name_format == NAME_FORMAT_USERNAME:
        username = coordinator.usernames.get(reservation.get("userId"))
        return username or full_name
    return full_name


class LibreBookingResourceEntity(CoordinatorEntity[LibreBookingCoordinator]):
    """Base entity representing one LibreBooking resource."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: LibreBookingCoordinator, resource_id: int) -> None:
        super().__init__(coordinator)
        self._resource_id = resource_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{coordinator.entry.entry_id}_{resource_id}")},
            name=self.resource_state.name,
            manufacturer="LibreBooking",
            model="Resource",
            configuration_url=coordinator.entry.data.get(CONF_URL),
        )

    @property
    def resource_state(self) -> ResourceState:
        """Return the current coordinator state for this resource."""
        return self.coordinator.data[self._resource_id]

    @property
    def available(self) -> bool:
        return super().available and self._resource_id in self.coordinator.data


def async_setup_resource_entities(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    entity_factories: list[
        Callable[[LibreBookingCoordinator, int], LibreBookingResourceEntity]
    ],
) -> None:
    """Add entities for every currently known resource, and again for any
    resource that shows up later (e.g. newly created in LibreBooking) so it
    gets entities without requiring a reload of the integration.
    """
    coordinator: LibreBookingCoordinator = hass.data[DOMAIN][entry.entry_id]
    known_resource_ids: set[int] = set()

    @callback
    def _add_new_resources() -> None:
        new_ids = set(coordinator.data) - known_resource_ids
        if not new_ids:
            return
        known_resource_ids.update(new_ids)
        async_add_entities(
            factory(coordinator, resource_id)
            for resource_id in new_ids
            for factory in entity_factories
        )

    _add_new_resources()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_resources))
