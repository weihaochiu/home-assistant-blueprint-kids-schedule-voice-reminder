# Kids Schedule Voice Reminder — Design

Version: v0.1.0

## Goals

This repository contains one pure Home Assistant automation Blueprint for fixed
weekly family schedules. It has no calendar, database, custom integration, or
external backend dependency.

## Data model

`events` is an `object` selector with `multiple: true`. Each event owns its
basic information, holiday policy, zero or more schedules, and zero or more
reminders. Schedules and reminders are nested `object` selectors with
`multiple: true`, so removing an event removes all of its children without
affecting other events.

An event contains:

- `name`, `enabled`, `participant`, and `location`
- `makeup_holiday_behavior`: `skip` or `run`
- `schedules[]`: `weekdays[]`, `start_time`, and `end_time`
- `reminders[]`: `name`, `enabled`, `timing`, and `messages[]`

Reminder timing uses a nested Home Assistant `choose` selector. Its five
choices are previous-day fixed time, same-day fixed time, before start, before
end, and after end. Each choice shows only the time or minute-offset field it
needs. Message entries are repeatable objects containing one text field; at
runtime they become that reminder's private list of message strings.

List positions are never persisted. Runtime indexes exist only inside one
heartbeat and are used to distinguish intentionally separate reminders.

## Holiday policy

The global helper is an `input_boolean`. Only the exact state `on` means a
makeup holiday; `unknown` and `unavailable` fail open as OFF. While ON, an event
with policy `skip` produces no candidate and an event with policy `run`
continues normally.

The helper represents current state, not a future date. To suppress a
previous-day reminder for tomorrow's makeup holiday, it must already be ON
when that reminder is due and remain ON through the holiday.

## Scheduler heartbeat

A `time_pattern` trigger runs every minute. The automation captures
`trigger.now` and truncates it to minute precision, preserving the actual
trigger minute if action execution is delayed. It then:

1. scans enabled, valid events;
2. skips holiday-blocked events;
3. scans valid schedules;
4. uses today as the occurrence date, except previous-day reminders use
   tomorrow;
5. validates the occurrence weekday and schedule times;
6. computes each enabled reminder's due timestamp;
7. compares the due minute with the captured heartbeat minute; and
8. accumulates every match in a Jinja `namespace()` list.

Candidate keys contain the runtime event index, occurrence date, runtime
reminder index, and due minute, but not the schedule index. Consequently,
duplicate schedules collapse while distinct reminders remain independent.
Candidates are sorted by due minute, event name, and reminder order.

The Blueprint uses Home Assistant local time (`as_local`) and supports weekday
rollover, including Sunday-to-Monday previous-day reminders. Seconds are
ignored for matching.

## Messages

Zero valid messages uses a generic event fallback, one always uses that text,
and two or more use Home Assistant's `random` filter for each actual playback.
The placeholders `{event}`, `{participant}`, `{location}`, `{start_time}`,
`{end_time}`, and `{minutes}` are replaced explicitly. User text is never
evaluated as Jinja.

## TTS playback

No match means no media action. For one or more matches, the Blueprint filters
unavailable players, snapshots each available player's volume once, sets the
announcement volume once, and plays all matched messages in deterministic
order. Each service call has independent error continuation.

After each message, a bounded length-based delay avoids immediately lowering
the volume. After all messages, a bounded buffering wait is best effort, then
each numeric original volume is restored once. The `announce` flag exposes
player-dependent media resume behavior; it cannot guarantee restoration on
every integration.

## Defensive behavior

Malformed events, empty child lists, missing names/weekdays/times, invalid
times, non-positive offsets, unavailable helpers, unavailable TTS, unavailable
players, and missing volume attributes are skipped without blocking valid
records. There is no persistent reminder history; duplicate suppression is
limited to one heartbeat execution.
