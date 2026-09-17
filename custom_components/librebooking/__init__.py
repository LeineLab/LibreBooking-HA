"""The LibreBooking integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_URL, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LibreBookingAuthError, LibreBookingClient, LibreBookingError
from .const import (
    CONF_NAME_FORMAT,
    CONF_RESOURCES,
    DEFAULT_NAME_FORMAT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import LibreBookingCoordinator

PLATFORMS = ["binary_sensor", "sensor", "calendar"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up LibreBooking from a config entry."""
    session = async_get_clientsession(hass)
    client = LibreBookingClient(
        session,
        entry.data[CONF_URL],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
    )

    try:
        await client.async_authenticate()
    except LibreBookingAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except LibreBookingError as err:
        raise ConfigEntryNotReady(str(err)) from err

    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    resource_ids = entry.options.get(CONF_RESOURCES, entry.data.get(CONF_RESOURCES))
    name_format = entry.options.get(
        CONF_NAME_FORMAT, entry.data.get(CONF_NAME_FORMAT, DEFAULT_NAME_FORMAT)
    )

    coordinator = LibreBookingCoordinator(
        hass, entry, client, resource_ids, scan_interval, name_format
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when options change (resource selection, scan interval)."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded
