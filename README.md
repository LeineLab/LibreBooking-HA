# LibreBooking Home Assistant Integration

Custom Home Assistant integration for [LibreBooking](https://www.librebooking.com/)
(the open-source resource scheduling system). It talks to LibreBooking's
[Web Services API](https://librebooking.readthedocs.io/en/latest/API.html)
and, per selected resource, provides:

- **`binary_sensor.<resource>_occupied`** — on when the resource currently has
  an active reservation. Attributes: `booked_by`, `title`, `reference_number`, `until`.
- **`sensor.<resource>_booked_until`** — timestamp of when the current
  reservation ends (unavailable when the resource is free).
- **`sensor.<resource>_next_reservation`** — timestamp of the next upcoming
  reservation. Attributes: `booked_by`, `title`, `ends`, `reference_number`.
- **`calendar.<resource>_reservations`** — a Home Assistant calendar entity
  showing that resource's reservations, viewable/synced like any other HA calendar.

## Requirements

The LibreBooking Web Services API must be enabled on your installation. By
default it is **off**; the server responds to every API call, including
login, with HTTP 503 and:

```
LibreBooking API is disabled. Set ["api"]["enabled"] = true
```

An administrator has to enable it in the server's `config/config.php`:

```php
return [
    'settings' => [
        'api' => [
            'enabled' => true,
        ],
    ],
];
```

You also need a LibreBooking username/password that has a **local password**
set and access to the resources you want to track. If your instance only
uses OIDC/OAuth2 login, an account that was auto-provisioned through that
flow has a random, unknown local password and can't authenticate against the
API — set/reset a password for it (or a dedicated technical account) via
LibreBooking's admin *Manage Users* page first. You can verify both
requirements independently of Home Assistant with:

```bash
curl -s -X POST "https://your-librebooking-url/Web/Services/index.php/Authentication/Authenticate" \
  -H "Content-Type: application/json" \
  -d '{"username": "your-user", "password": "your-password"}'
```

A successful response contains `"isAuthenticated": true`.

## Installation

### HACS (custom repository)

1. HACS → Integrations → menu → *Custom repositories* → add
   `https://github.com/LeineLab/LibreBooking-HA`.
2. Install "LibreBooking", restart Home Assistant.

### Manual

Copy `custom_components/librebooking` into your Home Assistant `config/custom_components/`
directory and restart Home Assistant.

## Setup

Settings → Devices & Services → Add Integration → **LibreBooking**.

1. Enter your LibreBooking base URL (e.g. `https://booking.example.com`), username
   and password.
2. Either leave **Track all resources** on (default) — every resource gets
   entities automatically, including ones created in LibreBooking later, no
   reconfiguration needed — or turn it off and pick a fixed set of resources
   from the list.

Afterwards, use the integration's **Configure** button to change this at any
time, or to change the polling interval (default: 60 seconds). If you picked
a fixed set of resources, a resource added later in LibreBooking will *not*
get entities until you revisit Configure and select it.

## Notes

- Polling only covers a rolling window (current time -1h to +14 days) to
  determine "current" and "next" reservation state; the calendar entity fetches
  whatever range Home Assistant's calendar view requests directly from the API.
- If your password changes or the session is rejected, Home Assistant will
  prompt for reauthentication.
