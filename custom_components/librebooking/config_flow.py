"""Config flow for LibreBooking."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_URL, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    LibreBookingApiDisabledError,
    LibreBookingAuthError,
    LibreBookingClient,
    LibreBookingError,
)
from .const import (
    CONF_RESOURCES,
    CONF_TRACK_ALL_RESOURCES,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def _authenticate_and_list_resources(
    hass, url: str, username: str, password: str
) -> dict[str, str]:
    """Return available resources as {str(resourceId): name}.

    Keys must be strings: cv.multi_select's options dict is sent to the
    frontend as JSON, where object keys are always strings, but validated
    server-side against this same dict. Int keys would make every selection
    round-trip fail with "X is not a valid option" (the option keys the
    frontend sends back are strings, the validator's dict keys are ints).
    """
    session = async_get_clientsession(hass)
    client = LibreBookingClient(session, url, username, password)
    await client.async_authenticate()
    resources = await client.async_get_resources()
    return {
        str(r["resourceId"]): r.get("name", f"Resource {r['resourceId']}")
        for r in resources
    }


class LibreBookingConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for LibreBooking."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._available_resources: dict[str, str] = {}
        self._reauth_entry: config_entries.ConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ask for the LibreBooking URL and credentials."""
        errors: dict[str, str] = {}
        if user_input is not None:
            url = user_input[CONF_URL].rstrip("/")
            try:
                resources = await _authenticate_and_list_resources(
                    self.hass, url, user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
                )
            except LibreBookingApiDisabledError:
                errors["base"] = "api_disabled"
            except LibreBookingAuthError:
                errors["base"] = "invalid_auth"
            except LibreBookingError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(
                    f"{url}_{user_input[CONF_USERNAME]}".lower()
                )
                self._abort_if_unique_id_configured()

                self._data = {
                    CONF_URL: url,
                    CONF_USERNAME: user_input[CONF_USERNAME],
                    CONF_PASSWORD: user_input[CONF_PASSWORD],
                }
                self._available_resources = resources
                return await self.async_step_resources()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )

    async def async_step_resources(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Let the user pick which resources to track."""
        if user_input is not None:
            track_all = user_input[CONF_TRACK_ALL_RESOURCES]
            self._data[CONF_TRACK_ALL_RESOURCES] = track_all
            self._data[CONF_RESOURCES] = (
                None if track_all else [int(r) for r in user_input[CONF_RESOURCES]]
            )
            return self.async_create_entry(title=self._data[CONF_URL], data=self._data)

        schema = vol.Schema(
            {
                vol.Required(CONF_TRACK_ALL_RESOURCES, default=True): bool,
                vol.Optional(
                    CONF_RESOURCES, default=list(self._available_resources)
                ): cv.multi_select(self._available_resources),
            }
        )
        return self.async_show_form(step_id="resources", data_schema=schema)

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> FlowResult:
        """Handle re-authentication after credentials stop working."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        self._data = dict(entry_data)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await _authenticate_and_list_resources(
                    self.hass,
                    self._data[CONF_URL],
                    self._data[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                )
            except LibreBookingApiDisabledError:
                errors["base"] = "api_disabled"
            except LibreBookingAuthError:
                errors["base"] = "invalid_auth"
            except LibreBookingError:
                errors["base"] = "cannot_connect"
            else:
                assert self._reauth_entry is not None
                new_data = {**self._reauth_entry.data, CONF_PASSWORD: user_input[CONF_PASSWORD]}
                self.hass.config_entries.async_update_entry(
                    self._reauth_entry, data=new_data
                )
                await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> LibreBookingOptionsFlow:
        return LibreBookingOptionsFlow(config_entry)


class LibreBookingOptionsFlow(config_entries.OptionsFlow):
    """Let the user change tracked resources and the polling interval."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    def _stored_resource_ids(self) -> list[int] | None:
        """Return the currently stored explicit resource id list, if any."""
        return self._config_entry.options.get(
            CONF_RESOURCES, self._config_entry.data.get(CONF_RESOURCES)
        )

    def _previously_known_resources(self) -> dict[str, str]:
        """Fall back to the last known resource ids when the API is unreachable."""
        resource_ids = self._stored_resource_ids() or []
        return {str(rid): str(rid) for rid in resource_ids}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        try:
            resources = await _authenticate_and_list_resources(
                self.hass,
                self._config_entry.data[CONF_URL],
                self._config_entry.data[CONF_USERNAME],
                self._config_entry.data[CONF_PASSWORD],
            )
        except LibreBookingApiDisabledError:
            resources = self._previously_known_resources()
            errors["base"] = "api_disabled"
        except LibreBookingError:
            resources = self._previously_known_resources()
            errors["base"] = "cannot_connect"

        if user_input is not None and not errors:
            track_all = user_input[CONF_TRACK_ALL_RESOURCES]
            return self.async_create_entry(
                title="",
                data={
                    CONF_TRACK_ALL_RESOURCES: track_all,
                    CONF_RESOURCES: (
                        None if track_all else [int(r) for r in user_input[CONF_RESOURCES]]
                    ),
                    CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                },
            )

        stored_resources = self._stored_resource_ids()
        current_track_all = self._config_entry.options.get(
            CONF_TRACK_ALL_RESOURCES,
            self._config_entry.data.get(CONF_TRACK_ALL_RESOURCES, not stored_resources),
        )
        # cv.multi_select's default must use the same (string) type as its
        # options keys, or the frontend can't pre-check the right boxes.
        current_resources = (
            [str(r) for r in stored_resources] if stored_resources else list(resources)
        )
        current_scan_interval = self._config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        schema = vol.Schema(
            {
                vol.Required(CONF_TRACK_ALL_RESOURCES, default=current_track_all): bool,
                vol.Optional(
                    CONF_RESOURCES, default=current_resources
                ): cv.multi_select(resources),
                vol.Required(
                    CONF_SCAN_INTERVAL, default=current_scan_interval
                ): vol.All(int, vol.Range(min=MIN_SCAN_INTERVAL)),
            }
        )
        return self.async_show_form(
            step_id="init", data_schema=schema, errors=errors
        )
