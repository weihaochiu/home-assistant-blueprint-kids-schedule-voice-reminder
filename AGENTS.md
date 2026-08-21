# Repository instructions

- Never commit a Home Assistant URL, access token, password, private address, household entity ID, or private family data.
- Keep v0.3.x a pure automation Blueprint: no GPS, push, backend, database, custom integration, school/vacation calendar, or fixed Child/Event/Reminder slots.
- Preserve `children[] -> events[] -> schedules[] + reminders[]`, plus the collapsed v0.1 compatibility inputs. Provide defaults for optional top-level inputs.
- Keep Calendar, Workday, and Legacy holiday sources mutually exclusive. Use occurrence dates, never reminder dates or a hard-coded holiday-name table. Fail open on integration or response failure.
- Calendar mode may call `calendar.get_events` at most once per heartbeat and must not call `homeassistant.update_entity`.
- Preserve scheduler occurrence offsets `[-2, -1, 0, 1]` while relative offsets remain capped at 1440 minutes.
- Keep Workday as the backward-compatible default, recommend Calendar for new installs, and keep the old makeup-holiday helper compatibility-only.
- Preserve queued playback (`max: 20`) and the action-level no-candidate gate so overlapping heartbeats cannot race player volume restore.
- Use official Home Assistant documentation/source as the technical authority.
- Run `python -m yamllint .`, `python -m pytest -q`, and `git diff --check` after Blueprint, test, workflow, or documentation changes.
- Do not push while required validation is failing. Never force-push or rewrite history.
- Keep `BACKUP/` ignored; the pre-push hook must fail closed if backup creation or verification fails.
