# Kids Schedule Voice Reminder Blueprint

![Version](https://img.shields.io/badge/version-v0.3.3-blue)
![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.1.0%2B-41BDF5)

A pure Home Assistant automation Blueprint for fixed weekly family schedules,
Calendar/Workday/legacy holiday policy, and multi-player TTS. Children/groups,
Events, Schedules, and Reminders are dynamic; there are no fixed slots.

[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fweihaochiu%2Fhome-assistant-blueprint-kids-schedule-voice-reminder%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fweihaochiu%2Fkids_schedule_voice_reminder.yaml)

Traditional Chinese: [README.zh-TW.md](README.zh-TW.md)

## Requirements and model

Use Home Assistant 2026.1.0+, a `tts.*` entity, and one or more `media_player.*`
entities. Import the Blueprint, select TTS/players/holiday source, and add Children.
A Child can represent one child or a shared group and owns any number of Events;
each Event owns weekly Schedules and independent Reminders. Disabling a Child
disables its complete subtree. Input list order controls playback order because
Home Assistant's Object selector has no drag-to-reorder control.

## Holiday source modes

The three modes are mutually exclusive. Workday is the upgrade-safe v0.2 default;
Calendar is recommended for new installations.

| Mode | Query | Best fit | Limitation |
| --- | --- | --- | --- |
| Calendar | At most one bounded `calendar.get_events` call per heartbeat with `skip` candidates | New installs using the public Taiwan feed | Events must be classified; synchronization depends on the provider |
| Workday | One `workday.check_date` per unique occurrence date, at most four | Existing v0.2 installs | Accuracy depends on integration configuration |
| Legacy | Current state of the old `input_boolean` | v0.1 compatibility | It is not date-aware |

All modes filter only Events whose policy is `skip`; `run` is always retained.
They check the **Event occurrence date**, not the reminder date. Unset/unavailable
entities, action errors, undefined or malformed responses, wrong keys, and missing
event lists all fail open.

## Google Taiwan feed and Remote Calendar setup

Calendar ID: `zh-tw.taiwan#holiday@group.v.calendar.google.com`

Public ICS (complete URL):
https://calendar.google.com/calendar/ical/zh-tw.taiwan%23holiday%40group.v.calendar.google.com/public/basic.ics

1. Open Home Assistant **Settings → Devices & services → Add integration**.
2. Select **Remote Calendar**.
3. Set Calendar Name, for example `Taiwan Holidays (Google)`.
4. Paste the complete public ICS URL into Calendar URL.
5. Keep Verify SSL certificate enabled.
6. Do not enter Google credentials: this public feed needs no authentication,
   OAuth, username/password, private URL, or token.
7. Open the Home Assistant Calendar dashboard and verify that the entity shows events.
8. In the Blueprint select Calendar mode and that `calendar.*` entity.

Remote Calendar normally refreshes itself every 24 hours; this Blueprint never
calls `homeassistant.update_entity`. An event being present does **not** mean it is
a holiday. The ordered classifier is:

1. summary contains `補行上班` or `補班` → not a holiday;
2. description contains `國定假日` → holiday;
3. summary contains `補假` → holiday;
4. description contains `假日節慶` → not a holiday;
5. unknown/malformed → not a holiday (fail-open).

There is no holiday-name whitelist. Date and date-time starts both use the valid
event occurrence date. The public feed was fetched and parsed for 2025, 2026, and
2027; see [HOLIDAY_CALENDAR_RESEARCH.md](docs/HOLIDAY_CALENDAR_RESEARCH.md).

## Scheduler and playback

The minute heartbeat builds raw candidates first. Candidate-free runs are rejected
before entering the queue, and a secondary action-level guard remains as defensive
runtime protection. Calendar is also skipped when all candidates use `run`.
Automation mode is `queued` with `max: 20`: each admitted run retains its captured
`trigger.now` minute and waits for earlier playback/volume restoration to complete,
preventing overlapping heartbeats from racing speaker volume.
An existing TTS entity's initial `unknown` state is valid and no longer treated as
unavailable; genuinely missing or unavailable TTS entities still stop safely.

Five timing modes are available: previous-day fixed, same-day fixed, before start,
before end, and after end. Offsets are 1–1440 minutes and overnight Events are
supported. Messages support `{event}`, `{participant}`, `{location}`, `{start_time}`,
`{end_time}`, and `{minutes}`. Zero valid messages uses a fallback, one is fixed,
and multiple entries are randomly selected without evaluating user text as Jinja.
All same-minute reminders play in due/Child/Event/Reminder order; player volumes
snapshot/set once and restore once. Consecutive reminders conservatively keep the
estimated speech guard, then use bounded player-state observation when available.
Players that do not report reliable playback states use the deterministic estimate,
so stuck states cannot block the queue indefinitely. Announcement/resume remains
player-dependent.

## v0.2 and v0.1 migration

- v0.2 keeps Workday by default and preserves existing Children, Events, Workday
  entity, TTS, and player inputs. Verify Calendar before explicitly switching modes.
- v0.1 Events and `makeup_holiday_entity` remain in the collapsed section. Select
  Legacy explicitly. The v0.2 bridge is preserved: Workday with an empty Workday
  entity and a configured helper uses Legacy.
- A named Child makes Children authoritative; with none, legacy Events are normalized.
  Nothing modifies Home Assistant `.storage`.

## Limitations and validation

- Fixed weekly schedules only: no school calendar, vacations, one-off event
  scheduling, typhoon days, GPS, or push logic.
- The live Google feed can change; unknown content intentionally fails open.
- Deduplication is per heartbeat; there is no persistent reminder ledger.
- Selector UI, Remote Calendar display, TTS, speaker synchronization, volume, and
  resume need real Home Assistant validation.

```shell
python -m pip install -r requirements-dev.txt
python -m yamllint .
python -m pytest -q
git diff --check
```

See [DESIGN.md](docs/DESIGN.md),
[HA_RESPONSE_VARIABLE_COMPATIBILITY.md](docs/HA_RESPONSE_VARIABLE_COMPATIBILITY.md),
the [manual checklist](docs/MANUAL_TEST_CHECKLIST.zh-TW.md), and
[CHANGELOG.md](CHANGELOG.md). Current version: **v0.3.3**.
