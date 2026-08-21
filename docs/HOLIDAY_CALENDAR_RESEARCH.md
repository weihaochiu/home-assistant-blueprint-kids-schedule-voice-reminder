# Google Taiwan Holiday Calendar research

Version: v0.3.1
Checked: 2026-08-21 (Asia/Taipei)

## Feed and verification

- Calendar ID: `zh-tw.taiwan#holiday@group.v.calendar.google.com`
- Public ICS: https://calendar.google.com/calendar/ical/zh-tw.taiwan%23holiday%40group.v.calendar.google.com/public/basic.ics
- Retrieval result: HTTP 200, UTF-8, 119,960 bytes, 330 VEVENT blocks at verification time.
- Years parsed: 2025, 2026, and 2027.

The feed was downloaded directly, folded ICS lines were unfolded, and every VEVENT
in the three target years was classified. Results at verification time:

| Year | Holiday | Makeup workday | Observance | Unknown | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2025 | 21 | 0 | 10 | 0 | 31 |
| 2026 | 24 | 0 | 9 | 0 | 33 |
| 2027 | 23 | 0 | 9 | 0 | 32 |

This is a live Google-owned feed, so future content can change. The Blueprint does
not ship a holiday-name whitelist or cache this research table.

## Ordered classifier

The first matching rule wins:

1. Summary contains `補行上班` or `補班` → not a holiday.
2. Description contains `國定假日` → holiday.
3. Summary contains `補假` → holiday.
4. Description contains `假日節慶` → not a holiday.
5. Anything else or malformed → unknown and not a holiday (fail-open).

Both `YYYY-MM-DD` and date-time start values use their first valid ISO date as the
event occurrence date. A calendar event is not automatically a holiday: the feed
contains cultural observances such as `假日節慶`, which must not suppress reminders.

## Home Assistant integration decision

Home Assistant's entity selector officially supports both `domain` and
`integration` filters. v0.3.0 filters only `domain: calendar`: constraining it to
`integration: remote_calendar` would hide compatible entities supplied by Google
Calendar, CalDAV, or another calendar provider. Remote Calendar is the documented
and recommended reproducible path, not a runtime requirement.

The official Remote Calendar integration reads public ICS and supports optional
HTTP Basic Authentication. This public Google feed needs no username, password,
OAuth, token, or private URL. Remote Calendar normally refreshes every 24 hours;
the Blueprint deliberately does not call `homeassistant.update_entity`.

References:

- https://www.home-assistant.io/integrations/remote_calendar/
- https://www.home-assistant.io/integrations/calendar/
- https://www.home-assistant.io/docs/blueprint/selectors/#entity-selector

An actual Home Assistant Remote Calendar configuration and Calendar dashboard
render still require the manual device test in the release checklist.
