# Home Assistant response-variable compatibility

Version: v0.3.1
Reviewed target: Home Assistant Core 2026.8.1

## Finding

Home Assistant Core issue #178410 reported that a `weather.get_forecasts`
`response_variable` appeared undefined in a following Define Variables action on
2026.8.0. The report was closed by its author with `needs-more-information`; it
does not mention `workday.check_date` or `calendar.get_events`, and it is not
evidence that either integration is broken.

The 2026.8.1 script runner source assigns the service response into the current
script variable mapping before advancing to the next action. The following
Variables action updates that same mapping. Core's tests also register a service
with an optional response, save it as `my_response`, and consume it in the next
action; response scopes are additionally tested in parallel branches.

Sources reviewed:

- https://github.com/home-assistant/core/issues/178410
- https://github.com/home-assistant/core/blob/2026.8.1/homeassistant/helpers/script.py
- https://github.com/home-assistant/core/blob/2026.8.1/homeassistant/helpers/script_variables.py
- https://github.com/home-assistant/core/blob/2026.8.1/tests/helpers/test_script.py

## v0.3.0 decision

The Blueprint retains a single Variables action after the response-producing
actions. This avoids duplicating a large classifier/filter template and follows
the verified Core execution model. Every action has `continue_on_error: true`;
every response is checked with `is defined`, mapping/key/type guards, and malformed
or missing data fails open. Repository tests render the actual Blueprint Jinja for
valid, absent, wrong-key, and malformed Calendar and Workday responses.

This lightweight repository does not vendor Home Assistant Core, so it cannot run
the full Core script engine locally. The release checklist therefore includes a
minimal HA 2026.8.x trace test: one candidate, one response action, the following
Variables step, and confirmation that playback continues or safely fails open.
