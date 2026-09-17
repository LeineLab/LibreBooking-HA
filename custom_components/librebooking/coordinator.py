"""DataUpdateCoordinator for LibreBooking."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import homeassistant.util.dt as dt_util

from .api import LibreBookingAuthError, LibreBookingClient, LibreBookingError
from .const import LOGGER, LOOKAHEAD, LOOKBACK, NAME_FORMAT_USERNAME


@dataclass
class ResourceState:
    """Current/next reservation state for a single resource."""

    resource_id: int
    name: str
    status_id: int | None
    current: dict[str, Any] | None
    next: dict[str, Any] | None


class LibreBookingCoordinator(DataUpdateCoordinator[dict[int, ResourceState]]):
    """Polls LibreBooking for resources and their reservations."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: LibreBookingClient,
        resource_ids: list[int] | None,
        scan_interval: int,
        name_format: str,
    ) -> None:
        super().__init__(
            hass,
            LOGGER,
            name="librebooking",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.entry = entry
        self.client = client
        self.resource_ids = resource_ids  # None/empty means "all resources"
        self.name_format = name_format
        self.usernames: dict[int, str] = {}

    async def _async_update_data(self) -> dict[int, ResourceState]:
        try:
            resources = await self.client.async_get_resources()
        except LibreBookingAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except LibreBookingError as err:
            raise UpdateFailed(str(err)) from err

        if self.resource_ids:
            resources = [r for r in resources if r["resourceId"] in self.resource_ids]

        if self.name_format == NAME_FORMAT_USERNAME:
            try:
                users = await self.client.async_get_users()
                self.usernames = {
                    user["id"]: user["userName"]
                    for user in users
                    if user.get("userName")
                }
            except (LibreBookingAuthError, LibreBookingError) as err:
                LOGGER.warning(
                    "Could not load LibreBooking users for username lookup, "
                    "falling back to full name: %s",
                    err,
                )

        now = dt_util.utcnow()

        try:
            reservations = await self.client.async_get_reservations(
                now - LOOKBACK, now + LOOKAHEAD
            )
        except LibreBookingAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except LibreBookingError as err:
            raise UpdateFailed(str(err)) from err

        by_resource: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for reservation in reservations:
            by_resource[reservation["resourceId"]].append(reservation)

        data: dict[int, ResourceState] = {}
        for resource in resources:
            resource_id = resource["resourceId"]
            items = sorted(
                by_resource.get(resource_id, []),
                key=lambda r: r["startDate"],
            )

            current: dict[str, Any] | None = None
            next_reservation: dict[str, Any] | None = None
            for item in items:
                start = dt_util.parse_datetime(item["startDate"])
                end = dt_util.parse_datetime(item["endDate"])
                if start is None or end is None:
                    continue
                if start <= now < end:
                    current = item
                elif start > now and next_reservation is None:
                    next_reservation = item

            data[resource_id] = ResourceState(
                resource_id=resource_id,
                name=resource.get("name", f"Resource {resource_id}"),
                status_id=resource.get("statusId"),
                current=current,
                next=next_reservation,
            )

        return data
