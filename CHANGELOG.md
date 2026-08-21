# Changelog

All notable changes to this project are documented here.

## v0.3.0 - 2026-08-21

### Added

- Mutually exclusive Calendar, Workday, and Legacy holiday-source modes; Workday remains the upgrade default and Calendar is recommended for new installations.
- One bounded `calendar.get_events` query per heartbeat with Google Taiwan holiday classification based on event metadata and occurrence date.
- Google public ICS research, Remote Calendar setup instructions, and Home Assistant 2026.8.1 response-variable compatibility evidence.

### Fixed

- Playback concurrency changed from parallel to a 20-run queue, with the raw-candidate guard moved into actions so admitted trigger context is preserved.
- Calendar and Workday responses now share explicit undefined, wrong-key, malformed-response, unavailable-entity, and action-error fail-open behavior.

### Changed

- Holiday filtering is source-selective and only evaluates `skip` Events; `run` Events remain independent of holiday data.
- Documentation and tests now distinguish actual national holidays, makeup workdays, cultural observances, and unknown calendar events.

## v0.2.0 - 2026-08-21

### Added

- Dynamic Children/shared groups with inherited spoken names and nested Events.
- Automatic occurrence-date Workday checks with per-Event non-workday policy.
- v0.1 legacy Events/helper compatibility bridge and documented migration path.

### Fixed

- Uniform D-2 through D+1 occurrence scan, including overnight +1439/+1440 reminders.
- Stable same-minute ordering by due, Child, Event, and Reminder input order.
- Workday query deduplication, no-candidate short circuit, and fail-open responses.
- GitHub Actions upgraded to Node 24-based checkout/setup-python releases.

### Changed

- Primary terminology and policy changed from manual makeup-holiday mode to Workday/non-workday.
- New-model participant values are inherited from the parent Child/Group.

## v0.1.0 - 2026-08-21

### Added

- Initial Kids Schedule Voice Reminder automation Blueprint.
- Dynamic Events with nested dynamic weekly Schedules and Reminders.
- Previous-day fixed, same-day fixed, before-start, before-end, and after-end timing.
- Per-reminder random message lists, explicit safe placeholders, and fallback messages.
- Makeup-holiday `input_boolean` with per-event `skip`/`run` behavior.
- Minute heartbeat with local-time weekday rollover, multi-match collection, and runtime deduplication.
- Multi-player TTS, individual volume snapshots/restoration, bounded waits, and best-effort announcement resume.
- Pytest/yamllint validation, GitHub Actions, bilingual documentation, manual checklist, and pre-push backups.
