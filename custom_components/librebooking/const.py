"""Constants for the LibreBooking integration."""
from __future__ import annotations

import logging
from datetime import timedelta

DOMAIN = "librebooking"
LOGGER = logging.getLogger(__package__)

CONF_RESOURCES = "resources"
CONF_TRACK_ALL_RESOURCES = "track_all_resources"

DEFAULT_SCAN_INTERVAL = 60
MIN_SCAN_INTERVAL = 15
LOOKAHEAD = timedelta(days=14)
LOOKBACK = timedelta(hours=1)

API_PATH = "/Web/Services/index.php"

# LibreBooking resource statusId values
STATUS_HIDDEN = 0
STATUS_AVAILABLE = 1
STATUS_UNAVAILABLE = 2
