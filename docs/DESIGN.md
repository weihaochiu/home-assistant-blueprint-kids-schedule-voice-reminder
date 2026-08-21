# Kids Schedule Voice Reminder — Design

Version: v0.3.3

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

Nested Object selector fields use only `label`, `required`, and `selector`, matching
Core 2026.8.1. Selector-level options such as `multiple`, `label_field`, and
`description_field` remain on the Object selector config rather than its fields.
Children and Legacy deliberately share the `reminders_selector` YAML anchor, so the
same validated Messages schema serves both paths. An offline recursive validator and
positive/negative pytest regressions enforce this schema before release.
Schema source:
https://github.com/home-assistant/core/blob/2026.8.1/homeassistant/helpers/selector.py

## Queued two-phase scheduler

The minute heartbeat captures `trigger.now` while rendering automation variables.
A top-level no-candidate condition rejects empty heartbeats before queued admission;
the same condition remains the first action as defensive runtime protection.
Automation mode is `queued`, `max: 20`, serializing player snapshot, playback, and
volume restoration while each admitted run retains its trigger-time minute.

Phase A scans each Event at occurrence offsets `[-2, -1, 0, 1]` for all five timing
modes. D-2 covers an overnight Event plus a 1440-minute after-end reminder. A key
containing runtime Child/Event identity, occurrence date, Reminder index, and due
minute collapses duplicate Schedules. Candidates sort by due, Child, Event, Reminder.
Relative minute values must be non-boolean integer numbers from 1 through 1440 at
runtime; malformed and out-of-range values produce no candidate.

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
player volumes snapshot/set once, all reminders play sequentially, and numeric
volumes restore once after every reminder completes.

Each reminder keeps the existing length estimate, clamped to the normalized minimum
and maximum, as a non-shortening guard. During that guard a bounded `wait_template`
observes `buffering` or `playing` on targets that were not already active at snapshot.
`wait.remaining` completes the full estimate even when activity appears early. If
activity was observed, a second bounded wait may extend completion until no observed
target remains active, but the combined per-reminder wait never exceeds the maximum.
No activity uses the original estimate as deterministic fallback; stuck active states
time out and continue. The final buffering wait remains as a separately bounded
post-playback settle guard before one-time volume restoration.

This is intentionally best effort. Core defines `playing`, `buffering`, `paused`,
`idle`, and `off`, but integrations need not emit every transition. In Apple TV
2026.8.1, pyatv `Loading` maps to `idle`, and `announce` is accepted by the generic
`play_media` schema but resume behavior remains integration-dependent. Initially
active players are therefore excluded from completion observation so resumed media
cannot hold the queue until every maximum timeout. Sources reviewed:

- https://github.com/home-assistant/core/blob/2026.8.1/homeassistant/components/media_player/__init__.py
- https://github.com/home-assistant/core/blob/2026.8.1/homeassistant/components/media_player/const.py
- https://github.com/home-assistant/core/blob/2026.8.1/homeassistant/components/apple_tv/media_player.py
- https://github.com/home-assistant/core/blob/2026.8.1/homeassistant/helpers/script.py
- https://github.com/home-assistant/core/blob/2026.8.1/homeassistant/components/tts/media_source.py

The existing `media-source://tts/<entity>?message=...&language=...` format and
`media_content_type: music` remain aligned with Core. Media announcement/resume
remains best effort.

An existing TTS entity with initial state `unknown` is usable; a missing entity is
distinguished through `states[entity_id]`, while `unavailable` remains blocked.
Runtime wait inputs accept only non-boolean integer values inside their selector
ranges, fall back to defaults when malformed, and sort valid minimum/maximum values.

## Scope boundaries

This is a weekly reminder Blueprint, not a general calendar scheduler. It does not
model school calendars, vacations, one-off calendar Events, typhoon days, GPS,
push notifications, storage migration, or persistent deduplication.
