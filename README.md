# Kids Schedule Voice Reminder Blueprint

![Version](https://img.shields.io/badge/version-v0.2.0-blue)
![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.1.0%2B-41BDF5)

A pure Home Assistant automation Blueprint for fixed weekly family schedules,
automatic Workday/non-workday policy, and multi-player TTS. Children/groups,
Events, Schedules, and Reminders are dynamic; there are no fixed slots.

[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fweihaochiu%2Fhome-assistant-blueprint-kids-schedule-voice-reminder%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fweihaochiu%2Fkids_schedule_voice_reminder.yaml)

Traditional Chinese: [README.zh-TW.md](README.zh-TW.md)

## Requirements and setup

- Home Assistant 2026.1.0+, a `tts.*` entity, and one or more `media_player.*` entities.
- Recommended: configure the Workday integration for Taiwan and select its
  `binary_sensor`. Configure its normal workdays and any desired exclusions in
  the integration; the Blueprint contains no hard-coded holiday table.

Import with the badge, create an automation, select TTS/players/Workday, then add
Children. A Child may also represent a shared group. `spoken_name` overrides the
name in speech. Each Child owns any number of Events; each Event owns weekly
Schedules and independent Reminders. Deleting a Child removes its entire subtree,
while disabling it preserves the data but disables the subtree.

## Workday behavior

Each Event chooses `skip` or `run` for non-workdays. The scheduler first creates
raw due candidates. If none exist it calls neither Workday nor media actions. It
then queries `workday.check_date` once per unique candidate occurrence date
(maximum four dates), always checking the **Event occurrence date**, not the
reminder date. Thus a Monday previous-day reminder for a Tuesday Event checks
Tuesday. A `run` Event never needs a Workday result.

`false` drops a `skip` candidate and `true` keeps it. An unset/unavailable entity,
action error, missing response, wrong key, or malformed response fails open and
keeps the reminder. If filtering removes every candidate, no TTS, snapshot, or
volume action runs.

## Timing, messages, and playback

Five modes are available: previous-day fixed, same-day fixed, before start,
before end, and after end. Offsets are 1–1440 minutes and overnight Events are
supported. Messages support `{event}`, `{participant}`, `{location}`,
`{start_time}`, `{end_time}`, and `{minutes}`. Zero valid messages uses a fallback,
one is fixed, and multiple entries are randomly selected without evaluating user
text as Jinja.

All reminders due in the same minute play. Order is due time, Child input order,
Event input order, then Reminder input order. Home Assistant's Object selector
currently has no reorder control, so reorder by editing/recreating entries or YAML;
there is no fake display-order field. Available players are snapshotted and raised
once, messages play sequentially with bounded waits, and numeric volumes restore
once. Announcement/resume remains player-dependent best effort.

## v0.1 migration

Existing v0.1 automations keep their `events` and optional
`makeup_holiday_entity` inputs in the collapsed compatibility section. If at
least one named Child exists, only Children are used; otherwise legacy Events are
normalized at runtime. A configured Workday entity has priority. If it is blank,
an `on` legacy helper preserves v0.1 `skip` behavior; unavailable/blank fails open.
To migrate, copy each legacy Event under its participant's Child, map participant
to Child name/spoken name, and map `makeup_holiday_behavior` to
`non_workday_behavior`.

## Limitations and validation

- Fixed weekly schedules only: no vacation, one-off date, calendar, GPS, or push logic.
- Deduplication is per heartbeat; there is no persistent reminder ledger.
- Selector UI, TTS completion, speaker synchronization, volume, and resume require
  real-device validation.

```shell
python -m pip install -r requirements-dev.txt
python -m yamllint .
python -m pytest -q
git diff --check
```

See [DESIGN.md](docs/DESIGN.md), the
[manual checklist](docs/MANUAL_TEST_CHECKLIST.zh-TW.md), and
[CHANGELOG.md](CHANGELOG.md). Current version: **v0.2.0**.
