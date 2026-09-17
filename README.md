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
3. Choose how the booking person should be shown (**Show the booking person
   as**): first name, last name, first + last name (default), or username.
   Username is resolved via LibreBooking's Users API and falls back to
   first + last name if that lookup fails or has no username for that user
   (e.g. a guest reservation). This is useful if your LibreBooking instance
   only fills in the first name via OIDC/SSO and leaves the last name as a
   placeholder like "not set".

Afterwards, use the integration's **Configure** button to change any of this
at any time, or to change the polling interval (default: 60 seconds). If you
picked a fixed set of resources, a resource added later in LibreBooking will
*not* get entities until you revisit Configure and select it.

## Notes

- Polling queries LibreBooking for reservations in a rolling window (current
  time -1h to +14 days). This is **not** a filter on the reservation's start
  time — LibreBooking's API returns every reservation that *overlaps* that
  window at all (its own SQL matches on start-in-range OR end-in-range OR
  fully spanning the range). A long reservation that started well before
  "-1h" is still returned in full and shown as occupied for its entire
  actual duration; the "-1h" only trims reservations that already ended
  before that point, it never cuts a still-running one short. The calendar
  entity separately fetches whatever range Home Assistant's calendar view
  requests directly from the API.
- If your password changes or the session is rejected, Home Assistant will
  prompt for reauthentication.
- If the LibreBooking server is temporarily unreachable (offline, network
  issue, timeout), entities briefly go unavailable and Home Assistant retries
  automatically on the next poll — this does **not** trigger reauthentication.
  Reauthentication is only requested when LibreBooking actively rejects the
  session (HTTP 401/403), e.g. an expired session or a changed password.
