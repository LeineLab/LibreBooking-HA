"""Constants for the LibreBooking integration."""
from __future__ import annotations

import logging
from datetime import timedelta

DOMAIN = "librebooking"
LOGGER = logging.getLogger(__package__)

CONF_RESOURCES = "resources"
CONF_TRACK_ALL_RESOURCES = "track_all_resources"
CONF_NAME_FORMAT = "name_format"

NAME_FORMAT_FIRST = "first_name"
NAME_FORMAT_LAST = "last_name"
NAME_FORMAT_FULL = "full_name"
NAME_FORMAT_USERNAME = "username"
NAME_FORMAT_OPTIONS = [
    NAME_FORMAT_FIRST,
    NAME_FORMAT_LAST,
    NAME_FORMAT_FULL,
    NAME_FORMAT_USERNAME,
]
DEFAULT_NAME_FORMAT = NAME_FORMAT_FULL

DEFAULT_SCAN_INTERVAL = 60
MIN_SCAN_INTERVAL = 15
LOOKAHEAD = timedelta(days=14)
LOOKBACK = timedelta(hours=1)

API_PATH = "/Web/Services/index.php"

# LibreBooking resource statusId values
STATUS_HIDDEN = 0
STATUS_AVAILABLE = 1
STATUS_UNAVAILABLE = 2
