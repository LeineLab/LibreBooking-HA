"""Thin async client for the LibreBooking Web Services API."""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import aiohttp

from .const import API_PATH, LOGGER

REQUEST_TIMEOUT = 15


class LibreBookingError(Exception):
    """Generic error talking to LibreBooking."""


class LibreBookingAuthError(LibreBookingError):
    """Invalid credentials or expired/rejected session."""


class LibreBookingApiDisabledError(LibreBookingError):
    """The LibreBooking Web Services API is disabled on the server.

    LibreBooking returns this (HTTP 503) for every route, including
    Authenticate, when ``["api"]["enabled"]`` is not set to ``true`` in the
    server's config.php.
    """


class LibreBookingClient:
    """Small wrapper around the LibreBooking Web Services API.

    See: https://librebooking.readthedocs.io/en/latest/API.html
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        username: str,
        password: str,
    ) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._username = username
        self._password = password
        self._session_token: str | None = None
        self._user_id: int | None = None

    @property
    def _api_base(self) -> str:
        return f"{self._base_url}{API_PATH}"

    @staticmethod
    async def _raise_for_error_status(resp: aiohttp.ClientResponse) -> None:
        """Raise a specific error for known non-2xx responses.

        LibreBooking's Slim ``slim.before.dispatch`` hook halts with HTTP 503
        and a fixed message for *every* route (including Authenticate) when
        the Web Services API itself is turned off server-side.
        """
        if resp.status == 503:
            text = await resp.text()
            if "disabled" in text.lower():
                raise LibreBookingApiDisabledError(
                    "The LibreBooking Web Services API is disabled on the server. "
                    'An administrator must set ["api"]["enabled"] = true in '
                    "config/config.php."
                )
            raise LibreBookingError(f"LibreBooking returned 503: {text}")

    async def async_authenticate(self) -> None:
        """Authenticate and store the session token / user id."""
        url = f"{self._api_base}/Authentication/Authenticate"
        payload = {"username": self._username, "password": self._password}
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                async with self._session.post(url, json=payload) as resp:
                    await self._raise_for_error_status(resp)
                    if resp.status in (401, 403):
                        raise LibreBookingAuthError("Invalid username or password")
                    if resp.status != 200:
                        text = await resp.text()
                        raise LibreBookingError(
                            f"Authenticate failed with status {resp.status}: {text}"
                        )
                    data = await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise LibreBookingError(f"Cannot connect to LibreBooking: {err}") from err

        if not data.get("isAuthenticated"):
            raise LibreBookingAuthError(data.get("message") or "Authentication failed")

        self._session_token = data["sessionToken"]
        self._user_id = data["userId"]

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        retry_on_auth_error: bool = True,
    ) -> dict[str, Any]:
        if self._session_token is None:
            await self.async_authenticate()

        headers = {
            "X-Booked-SessionToken": self._session_token or "",
            "X-Booked-UserId": str(self._user_id) if self._user_id is not None else "",
        }
        url = f"{self._api_base}{path}"

        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                async with self._session.request(
                    method, url, headers=headers, params=params
                ) as resp:
                    await self._raise_for_error_status(resp)
                    if resp.status in (401, 403) and retry_on_auth_error:
                        LOGGER.debug("LibreBooking session expired, re-authenticating")
                        self._session_token = None
                        await self.async_authenticate()
                        return await self._request(
                            method, path, params, retry_on_auth_error=False
                        )
                    if resp.status in (401, 403):
                        raise LibreBookingAuthError("LibreBooking rejected the session")
                    if resp.status >= 400:
                        text = await resp.text()
                        raise LibreBookingError(
                            f"{method} {path} failed with status {resp.status}: {text}"
                        )
                    return await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise LibreBookingError(f"Cannot connect to LibreBooking: {err}") from err

    async def async_get_resources(self) -> list[dict[str, Any]]:
        """Return all resources visible to the authenticated user."""
        data = await self._request("GET", "/Resources/")
        return data.get("resources", [])

    async def async_get_reservations(
        self,
        start: datetime,
        end: datetime,
        resource_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Return reservations in the given time range, optionally for one resource."""
        params: dict[str, Any] = {
            "startDateTime": start.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "endDateTime": end.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }
        if resource_id is not None:
            params["resourceId"] = resource_id
        data = await self._request("GET", "/Reservations/", params=params)
        return data.get("reservations", [])
