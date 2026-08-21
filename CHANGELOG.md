# Changelog

All notable changes to this project are documented here.

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
