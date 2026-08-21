# Kids Schedule Voice Reminder — Design

Version: v0.3.0

## Model and compatibility

The primary model remains `children[] -> events[] -> schedules[] + reminders[]`.
Children inherit `spoken_name || name` into normalized Events. A named Child makes
the primary model authoritative—even when disabled—so legacy data cannot play
unexpectedly. With no named Child, v0.1 `events[]` is normalized into the same
`runtime_events` representation. Runtime indexes are ephemeral, not persisted IDs.

Object selectors follow the Home Assistant 2026.8.x recursive schema. The holiday
source uses a normal select because Blueprint input sections cannot conditionally
hide sibling inputs based on another input. Calendar entities are filtered by
`domain: calendar`, deliberately not `integration: remote_calendar`, so other
standards-compatible providers remain selectable.

## Queued two-phase scheduler

The minute heartbeat captures `trigger.now`; automation mode is `queued`, `max: 20`.
The no-candidate condition is the first action, not a top-level automation condition.
This lets each admitted run retain its trigger context while serializing player
snapshot, playback, and volume restoration.

Phase A scans each Event at occurrence offsets `[-2, -1, 0, 1]` for all five timing
modes. D-2 covers an overnight Event plus a 1440-minute after-end reminder. A key
containing runtime Child/Event identity, occurrence date, Reminder index, and due
minute collapses duplicate Schedules. Candidates sort by due, Child, Event, Reminder.

If Phase A is empty, execution stops before holiday and media actions. `run`
candidates never need holiday data. Phase B filters only `skip` candidates against
exactly one effective source and stops before media if the list becomes empty.

## Holiday source architecture

`holiday_source` exposes `calendar`, `workday`, and `legacy`, with Workday as the
upgrade default. A v0.2 compatibility adapter maps Workday + blank sensor + configured
legacy helper to Legacy; otherwise sources do not read each other's state.

Calendar path:

1. Only when at least one raw candidate uses `skip`, the configured entity is
   available, and Calendar is effective, call `calendar.get_events` once.
2. Query local D-2 00:00 through D+2 00:00 (exclusive), enough for all candidate
   occurrence dates.
3. Read only the selected entity's `events` list. Parse date and date-time starts.
4. Apply the ordered Google Taiwan classifier without a name whitelist.
5. Drop a `skip` candidate only when its occurrence date is classified holiday.

Workday path uses four fixed optional `workday.check_date` actions, one per unique
candidate occurrence offset. A boolean `workday: false` drops `skip`; true keeps it.
Legacy reads the helper's current `on` state. Every unavailable/action-error/
undefined/wrong-key/malformed path fails open. The automation never invokes
`homeassistant.update_entity`.

## Response variables

Service responses are consumed by one following Variables action with explicit
`is defined`, mapping, key, collection, and boolean guards. This matches Home
Assistant Core 2026.8.1 script execution; see
[HA_RESPONSE_VARIABLE_COMPATIBILITY.md](HA_RESPONSE_VARIABLE_COMPATIBILITY.md).

## Messages and media

Zero valid messages uses fallback, one is fixed, and many use `random`. Six
placeholders are replaced literally and never re-evaluated as Jinja. Available
player volumes snapshot/set once, all reminders play sequentially, waits are bounded,
and numeric volumes restore once. Media announcement/resume remains best effort.

## Scope boundaries

This is a weekly reminder Blueprint, not a general calendar scheduler. It does not
model school calendars, vacations, one-off calendar Events, typhoon days, GPS,
push notifications, storage migration, or persistent deduplication.
