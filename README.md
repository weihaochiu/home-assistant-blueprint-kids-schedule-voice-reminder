# Kids Schedule Voice Reminder Blueprint

![Version](https://img.shields.io/badge/version-v0.1.0-blue)
![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.1.0%2B-41BDF5)

A pure Home Assistant automation Blueprint for fixed weekly kids' schedules,
pickup reminders, per-event makeup-holiday policy, and multi-player TTS. It has
dynamic Events, dynamic Schedules, and dynamic Reminders—there are no fixed
Event01 or Reminder01 slots.

[![Open your Home Assistant instance and import this Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fweihaochiu%2Fhome-assistant-blueprint-kids-schedule-voice-reminder%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fweihaochiu%2Fkids_schedule_voice_reminder.yaml)

Traditional Chinese documentation: [README.zh-TW.md](README.zh-TW.md)

## Features

- Add, edit, disable, and delete any number of Events.
- Add or delete multiple weekly Schedules inside one Event.
- Add, edit, disable, and delete any number of independent Reminders.
- Five timing modes: previous-day fixed, same-day fixed, before start, before
  end, and after end.
- A private message list per Reminder: zero uses a fallback, one is fixed, and
  multiple are randomly selected on actual playback.
- Safe explicit placeholders: `{event}`, `{participant}`, `{location}`,
  `{start_time}`, `{end_time}`, and `{minutes}`.
- Global makeup-holiday `input_boolean` plus per-event `skip` or `run` policy.
- Multiple media players, independent error handling, one volume snapshot/set
  per heartbeat, bounded TTS waits, and one final per-player volume restore.
- Best-effort `announce`/media resume behavior.

## Requirements and installation

- Home Assistant 2026.1.0 or newer.
- A configured `tts.*` entity.
- One or more `media_player.*` entities.
- One `input_boolean` helper for makeup-holiday mode.

Use the badge above, or paste this URL into **Settings → Automations & scenes →
Blueprints → Import Blueprint**:

```text
https://github.com/weihaochiu/home-assistant-blueprint-kids-schedule-voice-reminder/blob/main/blueprints/automation/weihaochiu/kids_schedule_voice_reminder.yaml
```

Then create an automation from **Kids Schedule Voice Reminder**, select the
holiday helper, TTS entity, players, and add Events.

## Create the makeup-holiday helper

In Home Assistant, open **Settings → Devices & services → Helpers → Create
helper → Toggle**. Give it a generic name such as “Makeup holiday mode,” then
select that helper in the Blueprint. The entity ID is never hard-coded.

Only the exact `on` state means holiday mode. `unknown` or `unavailable` is
treated as OFF so a temporarily unavailable helper does not silently suppress
important reminders.

## Configure Events, Schedules, and Reminders

An Event owns its schedules and reminders. Press **Add** in the Events selector,
enter a name, participant/location if useful, enable it, choose `skip` or `run`,
and add weekly schedules. One Event can contain Monday 17:00, Wednesday 17:30,
and Friday 17:00 schedules; it does not need to become three Events.

Inside each Event, add any number of Reminders. Choose one timing form and fill
only the field shown for it. Each Reminder has its own message entries. For
example, one Tuesday 18:00–19:30 Event can contain:

- previous day at 20:50 — prepare tomorrow's supplies;
- 30 minutes before start — prepare to leave;
- 10 minutes before start — leave now;
- 10 minutes before end — prepare for pickup; and
- 10 minutes after end — pickup reminder.

Use the selector's delete control to remove one Reminder. Use the Event delete
control to remove the whole Event and all its child schedules/reminders. Other
items do not depend on persistent list positions and remain unaffected.

## Message behavior and placeholders

An empty valid-message list uses a generic event fallback. One non-empty entry
is always used. Two or more entries use Home Assistant's random filter on each
actual playback; consecutive repeats are possible.

Example:

```text
In {minutes} minutes, {participant}'s {event} starts at {location}.
```

Placeholders are replaced as literal strings. Message text is never evaluated
again as Jinja, so text such as `{{ states('sensor.example') }}` remains text.

## TTS, players, volume, and media resume

Select the TTS language (default `zh-tw`), announcement volume (default 0.75),
and one or more players. When no reminder matches, the automation performs no
volume or media action. When reminders match, it:

1. filters `unknown`/`unavailable` players and snapshots individual volumes;
2. sets announcement volume once per available player;
3. plays every matched reminder in deterministic order;
4. waits a bounded estimate based on each message length;
5. performs a best-effort buffering wait; and
6. restores each numeric original volume once after all messages.

One failed player does not block the others. A missing `volume_level` is simply
not restored. `attempt_media_resume` sends `announce: true`; pause/resume and
queue restoration depend on the player integration and are not guaranteed.

## Makeup-holiday behavior

With the helper OFF, every enabled Event follows its schedule. With it ON,
Events set to `skip` produce no reminders and Events set to `run` continue.

Important: an `input_boolean` represents current state and cannot predict
tomorrow. To cancel a **previous-day fixed-time** reminder for tomorrow's makeup
holiday, turn the helper ON before that previous-day reminder runs and keep it
ON through the holiday.

## Scheduler behavior

A local-time heartbeat runs every minute and compares minute precision using
the trigger's captured timestamp. It scans all valid Events, Schedules, and
Reminders, including tomorrow's weekday for previous-day reminders. Duplicate
schedules collapse within that heartbeat, while separate reminders and
separate Events due in the same minute all play in stable order.

## Current limitations

- Fixed weekly schedules only; no one-off dates or external calendars.
- The holiday helper cannot infer future dates.
- No persistent reminder ledger: duplicate suppression covers one heartbeat,
  not duplicate external triggers or restarts.
- TTS completion, multi-speaker synchronization, volume restore, and media
  resume remain player-dependent best effort.
- Runtime behavior and selector UX still require testing on a real Home
  Assistant instance and the target speakers.

## Troubleshooting

- **No sound:** verify the `tts.*` entity, local Home Assistant URL, player
  availability, supported language, and player access to Home Assistant media.
- **No reminder:** check automation status, Event/Reminder enabled toggles,
  weekday, timing form, holiday policy, and automation trace.
- **Previous-day reminder still played:** the helper was not ON when it ran.
- **Volume not restored:** the player may omit `volume_level`, take longer than
  the configured wait, or not expose reliable playback state.
- **Media did not resume:** disable the resume option if the player does not
  implement announcements correctly.
- **One bad record:** malformed records are ignored; inspect the neighboring
  valid Events in the trace because they continue independently.

## Development and validation

```shell
python -m pip install -r requirements-dev.txt
python -m yamllint .
python -m pytest -q
git diff --check
```

Real-device coverage is listed in
[docs/MANUAL_TEST_CHECKLIST.zh-TW.md](docs/MANUAL_TEST_CHECKLIST.zh-TW.md), and
the runtime/data design is in [docs/DESIGN.md](docs/DESIGN.md).

## Roadmap

Future versions may add winter/summer vacation policy, specified no-class
dates, and Google/school calendar sources. These are intentionally absent from
v0.1.0.

## Version

Current version: **v0.1.0**. See [CHANGELOG.md](CHANGELOG.md).
