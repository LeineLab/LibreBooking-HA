"""Calendar platform exposing LibreBooking reservations per resource."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
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
    """Set up one calendar entity per configured LibreBooking resource."""
    async_setup_resource_entities(hass, entry, async_add_entities, [LibreBookingCalendar])


def _reservation_to_event(
    coordinator: LibreBookingCoordinator, reservation: dict
) -> CalendarEvent:
    booked_by = reservation_booked_by(coordinator, reservation)
    summary = reservation.get("title") or reservation.get("resourceName") or "Reservation"
    if booked_by:
        summary = f"{summary} ({booked_by})"
    return CalendarEvent(
        start=dt_util.parse_datetime(reservation["startDate"]),
        end=dt_util.parse_datetime(reservation["endDate"]),
        summary=summary,
        description=reservation.get("description"),
        uid=reservation.get("referenceNumber"),
    )


class LibreBookingCalendar(LibreBookingResourceEntity, CalendarEntity):
    """Calendar of reservations for a single LibreBooking resource."""

    # Explicit name instead of has_entity_name's "<device> <entity>" pattern,
    # so calendars sort together as "Bookings: ..." rather than scattering
    # alphabetically under each resource's own name.
    _attr_has_entity_name = False

    def __init__(self, coordinator: LibreBookingCoordinator, resource_id: int) -> None:
        super().__init__(coordinator, resource_id)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{resource_id}_calendar"
        self._attr_name = f"Bookings: {self.resource_state.name}"

    @property
    def event(self) -> CalendarEvent | None:
        state = self.resource_state
        reservation = state.current or state.next
        return _reservation_to_event(self.coordinator, reservation) if reservation else None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        reservations = await self.coordinator.client.async_get_reservations(
            start_date, end_date, resource_id=self._resource_id
        )
        return [_reservation_to_event(self.coordinator, r) for r in reservations]
