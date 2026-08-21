# Repository instructions

- Never commit a Home Assistant URL, access token, password, private address, household entity ID, or private family data.
- Keep v0.1.x a pure automation Blueprint: no calendar integration, external API, backend, database, custom integration, or fixed Event/Reminder slots.
- Preserve the dynamic `events -> schedules[] + reminders[]` model and provide defaults for any new optional top-level input.
- Treat “補假” (makeup holiday) separately from makeup classes and school vacations.
- Use official Home Assistant documentation/source as the technical authority.
- Run `python -m yamllint .`, `python -m pytest -q`, and `git diff --check` after Blueprint, test, workflow, or documentation changes.
- Do not push while required validation is failing. Never force-push or rewrite history.
- Keep `BACKUP/` ignored; the pre-push hook must fail closed if backup creation or verification fails.
