# Kids Schedule Voice Reminder — Design

Version: v0.2.0

## Model and compatibility

The primary model is `children[] -> events[] -> schedules[] + reminders[]`.
Children inherit `spoken_name || name` into each normalized Event participant.
Child/Event/Reminder enabled flags apply at their own subtree. A named Child
makes the primary model authoritative—even when disabled—so legacy data cannot
unexpectedly play. With no named Child, v0.1 `events[]` is normalized once into
the same `runtime_events` representation. Runtime IDs contain source, Child index,
and Event index; indexes are ephemeral and are not persisted identifiers.

The nested Object selectors match the Home Assistant 2026.8.x selector schema:
Object fields may contain any selector and `multiple: true` produces lists.
Object selectors expose no reorder option, so source list order is authoritative.

## Two-phase scheduler and boundaries

The minute heartbeat captures `trigger.now`. Phase A scans every valid runtime
Event using occurrence offsets `[-2, -1, 0, 1]`, uniformly for all five timing
modes. D-2 is required for a Monday 23:00–Tuesday 01:00 overnight Event whose
after-end offset is 1440 minutes and is due Wednesday 01:00. A key of runtime
Child/Event identity, occurrence date, Reminder index, and due minute collapses
duplicate Schedules while retaining independent items. Candidates sort by due,
Child order, Event order, and Reminder order.

If Phase A is empty execution stops before Workday and media. Otherwise only
unique occurrence offsets belonging to `skip` candidates are queried, through
four fixed `workday.check_date` actions and response variables. This bounds calls
at four and queries each occurrence date once. Phase B keeps `run`, keeps `skip`
on boolean true, drops it on boolean false, and fails open for every missing,
unavailable, error, wrong-key, or malformed response. If Phase B empties the list,
execution stops before player snapshot, volume, and TTS.

A configured Workday entity takes priority. Only when blank does the legacy
helper bridge apply v0.1 current-state `on + skip` behavior; unavailable is off.

## Migration

No script touches Home Assistant storage. Users first select a Taiwan Workday
sensor, then manually recreate legacy Events beneath named Children/Groups.
During migration, named Children are authoritative and legacy Events remain a
non-executing fallback; removing all named Children re-enables the legacy adapter.

## Messages and media

Reminder messages are private lists: zero valid entries uses fallback, one is
fixed, and many use `random`. Six placeholders are replaced literally and never
re-evaluated as Jinja. Available player volumes snapshot/set once, all reminders
play sequentially, bounded waits reduce overlap, and numeric volumes restore once.
Media announcement/resume remains best effort.
