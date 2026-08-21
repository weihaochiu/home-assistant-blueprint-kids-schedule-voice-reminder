# Repository instructions

- Never commit a Home Assistant URL, access token, password, private address, household entity ID, or private family data.
- Keep v0.2.x a pure automation Blueprint: no calendar, GPS, push, external API, backend, database, custom integration, or fixed Child/Event/Reminder slots.
- Preserve `children[] -> events[] -> schedules[] + reminders[]`, plus the collapsed v0.1 compatibility inputs. Provide defaults for optional top-level inputs.
- Use `workday.check_date` for occurrence dates; never add a hard-coded holiday table. Fail open on integration or response failure.
- Preserve scheduler occurrence offsets `[-2, -1, 0, 1]` while relative offsets remain capped at 1440 minutes.
- Treat Workday/non-workday as primary terminology. The old makeup-holiday helper is compatibility-only.
- Use official Home Assistant documentation/source as the technical authority.
- Run `python -m yamllint .`, `python -m pytest -q`, and `git diff --check` after Blueprint, test, workflow, or documentation changes.
- Do not push while required validation is failing. Never force-push or rewrite history.
- Keep `BACKUP/` ignored; the pre-push hook must fail closed if backup creation or verification fails.
