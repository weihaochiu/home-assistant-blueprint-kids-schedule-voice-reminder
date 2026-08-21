"""Static, template, and scheduler reference tests for the Blueprint."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
import importlib
from pathlib import Path
import re
from urllib.parse import parse_qs, quote_plus, urlparse

from jinja2 import Environment
from jinja2.nativetypes import NativeEnvironment
import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
BLUEPRINT_PATH = (
    ROOT
    / "blueprints"
    / "automation"
    / "weihaochiu"
    / "kids_schedule_voice_reminder.yaml"
)
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "events.yaml"
SOURCE_URL = (
    "https://github.com/weihaochiu/"
    "home-assistant-blueprint-kids-schedule-voice-reminder/blob/main/"
    "blueprints/automation/weihaochiu/kids_schedule_voice_reminder.yaml"
)
WEEKDAYS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]
TIMING_CHOICES = {
    "前一天固定時間",
    "當天固定時間",
    "活動／上課前",
    "下課前",
    "下課後",
}


class InputRef(str):
    """Represent a Home Assistant !input reference during static parsing."""


class BlueprintLoader(yaml.SafeLoader):
    """PyYAML loader that understands Home Assistant's !input tag."""


def _input(loader: BlueprintLoader, node: yaml.Node) -> InputRef:
    return InputRef(loader.construct_scalar(node))


BlueprintLoader.add_constructor("!input", _input)


@pytest.fixture(scope="module")
def blueprint_text() -> str:
    return BLUEPRINT_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def blueprint(blueprint_text: str) -> dict:
    return yaml.load(blueprint_text, Loader=BlueprintLoader)


@pytest.fixture(scope="module")
def fixtures() -> dict:
    return yaml.safe_load(FIXTURE_PATH.read_text(encoding="utf-8"))


def flatten_inputs(input_tree: dict) -> dict:
    flattened: dict = {}
    for key, value in input_tree.items():
        if isinstance(value, dict) and "input" in value:
            flattened.update(value["input"])
        else:
            flattened[key] = value
    return flattened


def walk(value):
    yield value
    if isinstance(value, dict):
        for key, item in value.items():
            yield from walk(key)
            yield from walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk(item)


def find_variable_template(value, name: str) -> str:
    if isinstance(value, dict):
        variables = value.get("variables")
        if isinstance(variables, dict) and name in variables:
            return variables[name]
        if name in value and isinstance(value[name], str):
            return value[name]
        for item in value.values():
            try:
                return find_variable_template(item, name)
            except KeyError:
                pass
    elif isinstance(value, list):
        for item in value:
            try:
                return find_variable_template(item, name)
            except KeyError:
                pass
    raise KeyError(name)


def parse_clock(value: object) -> time | None:
    if not isinstance(value, str):
        return None
    try:
        return time.fromisoformat(value)
    except ValueError:
        return None


def timing_kind(timing: dict) -> str:
    mapping = {
        "前一天固定時間": "previous_day_fixed",
        "當天固定時間": "same_day_fixed",
        "活動／上課前": "before_start",
        "下課前": "before_end",
        "下課後": "after_end",
    }
    return mapping.get(timing.get("active_choice", ""), "invalid")


def reminder_due(
    occurrence_date,
    start_value: object,
    end_value: object,
    timing: dict,
) -> datetime | None:
    """Reference model for all five Blueprint reminder calculations."""
    start_clock = parse_clock(start_value)
    end_clock = parse_clock(end_value)
    if start_clock is None or end_clock is None or not isinstance(timing, dict):
        return None
    start = datetime.combine(occurrence_date, start_clock)
    end = datetime.combine(occurrence_date, end_clock)
    if end <= start:
        end += timedelta(days=1)
    active = timing.get("active_choice", "")
    branch = timing.get(active, {})
    if not isinstance(branch, dict):
        return None
    kind = timing_kind(timing)
    if kind in {"previous_day_fixed", "same_day_fixed"}:
        fixed = parse_clock(branch.get("time"))
        if fixed is None:
            return None
        day = occurrence_date - timedelta(days=kind == "previous_day_fixed")
        return datetime.combine(day, fixed).replace(second=0, microsecond=0)
    minutes = branch.get("minutes")
    if isinstance(minutes, bool):
        return None
    try:
        minutes = int(minutes)
    except (TypeError, ValueError):
        return None
    if not 1 <= minutes <= 1440:
        return None
    if kind == "before_start":
        return start - timedelta(minutes=minutes)
    if kind == "before_end":
        return end - timedelta(minutes=minutes)
    if kind == "after_end":
        return end + timedelta(minutes=minutes)
    return None


def normalize_messages(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        raw = item.get("message", "") if isinstance(item, dict) else item
        if isinstance(raw, str) and raw.strip():
            result.append(raw.strip())
    return result


def replace_placeholders(template: str, values: dict[str, object]) -> str:
    for key in ("event", "participant", "location", "start_time", "end_time", "minutes"):
        template = template.replace("{" + key + "}", str(values.get(key, "")))
    return template


def simple_event(
    name: str = "畫畫課",
    *,
    weekday: str = "tuesday",
    start: str = "18:00:00",
    end: str = "19:00:00",
    timing: dict | None = None,
    policy: str = "skip",
) -> dict:
    timing = timing or {"active_choice": "當天固定時間", "當天固定時間": {"time": "17:00:00"}}
    return {
        "name": name,
        "enabled": True,
        "location": "教室",
        "non_workday_behavior": policy,
        "schedules": [{"weekdays": [weekday], "start_time": start, "end_time": end}],
        "reminders": [{"name": "提醒", "enabled": True, "timing": timing, "messages": []}],
    }


def child(name: str, events: list[dict], *, enabled: bool = True, spoken_name: str = "") -> dict:
    return {"name": name, "enabled": enabled, "spoken_name": spoken_name, "events": events}


def find_matches(
    events: object,
    check: datetime,
    holiday_on: bool = False,
    *,
    children: object = None,
    workdays: dict | None = None,
) -> list[dict]:
    """Independent v0.2 reference model, including normalization and policy."""
    valid_children = [
        item for item in (children if isinstance(children, list) else [])
        if isinstance(item, dict) and str(item.get("name", "")).strip()
    ]
    runtime_events: list[dict] = []
    if valid_children:
        for child_index, item in enumerate(valid_children):
            participant = str(item.get("spoken_name", "")).strip() or str(item["name"]).strip()
            child_events = item.get("events", [])
            if not isinstance(child_events, list):
                continue
            for event_index, event in enumerate(child_events):
                if isinstance(event, dict):
                    runtime_events.append(
                        event
                        | {
                            "participant": participant,
                            "child_enabled": item.get("enabled", True),
                            "child_order": child_index,
                            "event_order": event_index,
                            "policy": event.get("non_workday_behavior", "skip"),
                        }
                    )
    elif isinstance(events, list):
        runtime_events = [
            event
            | {
                "child_enabled": True,
                "child_order": 0,
                "event_order": event_index,
                "policy": event.get("makeup_holiday_behavior", "skip"),
            }
            for event_index, event in enumerate(events)
            if isinstance(event, dict)
        ]
    check = check.replace(second=0, microsecond=0)
    matches: list[dict] = []
    keys: set[tuple] = set()
    for event_index, event in enumerate(runtime_events):
        if not event.get("child_enabled", True) or not event.get("enabled", True):
            continue
        name = str(event.get("name", "")).strip()
        if not name:
            continue
        schedules = event.get("schedules")
        reminders = event.get("reminders")
        if not isinstance(schedules, list) or not isinstance(reminders, list):
            continue
        for schedule in schedules:
            if not isinstance(schedule, dict):
                continue
            weekdays = schedule.get("weekdays", [])
            if isinstance(weekdays, str):
                weekdays = [weekdays]
            if not isinstance(weekdays, list):
                continue
            for reminder_index, reminder in enumerate(reminders):
                if not isinstance(reminder, dict) or not reminder.get("enabled", True):
                    continue
                timing = reminder.get("timing", {})
                candidate_dates = [check.date() + timedelta(days=offset) for offset in (-2, -1, 0, 1)]
                for occurrence_date in candidate_dates:
                    if WEEKDAYS[occurrence_date.weekday()] not in weekdays:
                        continue
                    due = reminder_due(
                        occurrence_date,
                        schedule.get("start_time"),
                        schedule.get("end_time"),
                        timing,
                    )
                    if due != check:
                        continue
                    if event["policy"] == "skip":
                        if workdays is not None and workdays.get(occurrence_date, True) is False:
                            continue
                        if workdays is None and holiday_on:
                            continue
                    key = (event_index, occurrence_date, reminder_index, due)
                    if key in keys:
                        continue
                    keys.add(key)
                    matches.append(
                        {
                            "event": name,
                            "child_order": event["child_order"],
                            "event_order": event["event_order"],
                            "reminder_order": reminder_index,
                            "due": due,
                            "messages": normalize_messages(reminder.get("messages", [])),
                        }
                    )
    return sorted(
        matches,
        key=lambda item: (
            item["due"], item["child_order"], item["event_order"], item["reminder_order"]
        ),
    )


def calendar_event_date(value: object) -> date | None:
    """Parse Home Assistant calendar date and date-time response values."""
    if not isinstance(value, str) or len(value.strip()) < 10:
        return None
    try:
        return date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None


def is_google_taiwan_holiday(event: object) -> bool:
    """Independent implementation of the documented ordered classifier."""
    if not isinstance(event, dict):
        return False
    summary = str(event.get("summary") or "")
    description = str(event.get("description") or "")
    if "補行上班" in summary or "補班" in summary:
        return False
    if "國定假日" in description:
        return True
    if "補假" in summary:
        return True
    if "假日節慶" in description:
        return False
    return False


def render_blueprint_matches(
    blueprint: dict,
    events: list[dict],
    check: datetime,
    holiday_on: bool = False,
    *,
    children: list[dict] | None = None,
    holiday_source: str = "workday",
    calendar_entity: str = "calendar.taiwan_holidays",
    calendar_response: object | None = None,
    workday_entity: str = "",
    workday_responses: dict[int, object] | None = None,
) -> list[dict]:
    """Render the actual Blueprint normalization, candidate, and policy templates."""
    epoch = datetime(1970, 1, 1)

    def as_datetime(value):
        return epoch + timedelta(seconds=float(value))

    def as_timestamp(value):
        return (value - epoch).total_seconds()

    def as_bool(value):
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on", "enable"}

    environment = NativeEnvironment(autoescape=False)
    environment.filters["bool"] = as_bool
    environment.globals["timedelta"] = timedelta
    environment.globals["as_datetime"] = as_datetime
    environment.globals["as_timestamp"] = as_timestamp
    environment.globals["as_local"] = lambda value: value
    check_minute = int((check - epoch).total_seconds())
    context = {
        "children_input": children or [],
        "events_input": events,
        "check_minute": check_minute,
        "weekday_names": WEEKDAYS,
    }
    for name in ("valid_children", "runtime_events", "raw_candidates"):
        context[name] = environment.from_string(blueprint["variables"][name]).render(**context)
    context.update(
        {
            "holiday_calendar_entity_input": calendar_entity,
            "effective_holiday_source": (
                "legacy"
                if holiday_source == "workday" and not workday_entity and holiday_on
                else holiday_source
            ),
            "workday_entity_input": workday_entity,
            "workday_configured": holiday_source == "workday" and bool(workday_entity),
            "legacy_holiday_active": holiday_source == "legacy" and holiday_on
            or holiday_source == "workday" and not workday_entity and holiday_on,
        }
    )
    if calendar_response is not None:
        context["holiday_calendar_response"] = calendar_response
    responses = workday_responses or {}
    for offset, variable in {
        -2: "workday_response_minus_2",
        -1: "workday_response_minus_1",
        0: "workday_response_same",
        1: "workday_response_plus_1",
    }.items():
        if offset in responses:
            context[variable] = responses[offset]
    template = find_variable_template(blueprint["actions"], "matched_reminders")
    return environment.from_string(template).render(**context)


def test_yaml_loads_and_metadata_is_correct(blueprint: dict) -> None:
    metadata = blueprint["blueprint"]
    assert metadata["domain"] == "automation"
    assert metadata["author"] == "weihaochiu"
    assert metadata["source_url"] == SOURCE_URL
    assert metadata["homeassistant"]["min_version"] == "2026.1.0"
    assert "v0.3.1" in metadata["name"]
    assert "v0.3.1" in metadata["description"]


def test_version_is_consistent_across_release_surfaces(blueprint: dict) -> None:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert version == "v0.3.1"
    for filename in (
        "README.md",
        "README.zh-TW.md",
        "CHANGELOG.md",
        "docs/DESIGN.md",
        "docs/HA_RESPONSE_VARIABLE_COMPATIBILITY.md",
        "docs/HOLIDAY_CALENDAR_RESEARCH.md",
        "docs/MANUAL_TEST_CHECKLIST.zh-TW.md",
    ):
        assert version in (ROOT / filename).read_text(encoding="utf-8")
    assert version in blueprint["blueprint"]["name"]
    assert version in blueprint["blueprint"]["description"]


def test_input_sections_and_references(blueprint: dict) -> None:
    tree = blueprint["blueprint"]["input"]
    assert list(tree) == [
        "holiday_section",
        "playback_section",
        "children_section",
        "legacy_section",
        "advanced_section",
    ]
    inputs = flatten_inputs(tree)
    references = {str(value) for value in walk(blueprint) if isinstance(value, InputRef)}
    assert references == set(inputs)


def test_dynamic_event_schedule_and_reminder_schema(blueprint: dict) -> None:
    inputs = flatten_inputs(blueprint["blueprint"]["input"])
    children = inputs["children"]["selector"]["object"]
    assert children["multiple"] is True
    assert inputs["children"]["default"] == []
    assert {"name", "enabled", "spoken_name", "events"} == set(children["fields"])
    events = children["fields"]["events"]["selector"]["object"]
    assert events["multiple"] is True
    assert inputs["events"]["default"] == []
    fields = events["fields"]
    assert {"name", "enabled", "location", "non_workday_behavior", "schedules", "reminders"} == set(fields)
    schedules = fields["schedules"]["selector"]["object"]
    reminders = fields["reminders"]["selector"]["object"]
    assert schedules["multiple"] is True
    assert reminders["multiple"] is True
    weekday_select = schedules["fields"]["weekdays"]["selector"]["select"]
    assert weekday_select["multiple"] is True
    assert [item["value"] for item in weekday_select["options"]] == WEEKDAYS


def test_nested_choose_has_five_conditional_timing_forms(blueprint: dict) -> None:
    inputs = flatten_inputs(blueprint["blueprint"]["input"])
    child_fields = inputs["children"]["selector"]["object"]["fields"]
    event_fields = child_fields["events"]["selector"]["object"]["fields"]
    reminder_fields = event_fields["reminders"]["selector"]["object"]["fields"]
    choices = reminder_fields["timing"]["selector"]["choose"]["choices"]
    assert set(choices) == TIMING_CHOICES
    for label in ("前一天固定時間", "當天固定時間"):
        assert set(choices[label]["selector"]["object"]["fields"]) == {"time"}
    for label in ("活動／上課前", "下課前", "下課後"):
        assert set(choices[label]["selector"]["object"]["fields"]) == {"minutes"}
    messages = reminder_fields["messages"]["selector"]["object"]
    assert messages["multiple"] is True
    assert set(messages["fields"]) == {"message"}


def test_player_tts_and_holiday_selectors(blueprint: dict) -> None:
    inputs = flatten_inputs(blueprint["blueprint"]["input"])
    assert inputs["media_players"]["selector"]["entity"] == {
        "multiple": True,
        "filter": [{"domain": "media_player"}],
    }
    assert inputs["tts_entity"]["selector"]["entity"]["filter"] == [{"domain": "tts"}]
    assert inputs["makeup_holiday_entity"]["selector"]["entity"]["filter"] == [{"domain": "input_boolean"}]
    assert inputs["makeup_holiday_entity"]["default"] == ""
    assert inputs["workday_entity"]["default"] == ""
    assert inputs["workday_entity"]["selector"]["entity"]["filter"] == [
        {"integration": "workday", "domain": "binary_sensor"}
    ]
    assert inputs["holiday_source"]["default"] == "workday"
    options = inputs["holiday_source"]["selector"]["select"]["options"]
    assert [item["value"] for item in options] == ["calendar", "workday", "legacy"]
    assert inputs["holiday_calendar_entity"]["default"] == ""
    assert inputs["holiday_calendar_entity"]["selector"]["entity"]["filter"] == [
        {"domain": "calendar"}
    ]


def test_modern_heartbeat_and_fixed_trigger_minute(blueprint: dict, blueprint_text: str) -> None:
    assert blueprint["triggers"] == [{"trigger": "time_pattern", "minutes": "/1", "id": "heartbeat"}]
    assert blueprint["mode"] == "queued"
    assert blueprint["max"] == 20
    assert blueprint["max_exceeded"] == "warning"
    assert "trigger.now" in blueprint["variables"]["check_time"]
    assert "check_minute" in blueprint["variables"]
    assert "platform:" not in blueprint_text
    assert "service:" not in blueprint_text


def test_trigger_now_snapshot_drives_candidates_when_execution_is_delayed(
    blueprint: dict,
) -> None:
    trigger_now = datetime(2026, 8, 18, 17, 30)
    delayed_execution = datetime(2026, 8, 18, 17, 32)
    epoch = datetime(1970, 1, 1)
    fallback_calls: list[datetime] = []

    def fallback_now() -> datetime:
        fallback_calls.append(delayed_execution)
        return delayed_execution

    def as_timestamp(value: datetime) -> float:
        return (value - epoch).total_seconds()

    environment = NativeEnvironment(autoescape=False)
    environment.filters["bool"] = lambda value: bool(value)
    environment.globals.update(
        as_datetime=lambda value: epoch + timedelta(seconds=float(value)),
        as_local=lambda value: value,
        as_timestamp=as_timestamp,
        now=fallback_now,
        timedelta=timedelta,
    )
    context = {"trigger": {"now": trigger_now}}
    for name in ("check_time", "check_minute"):
        context[name] = environment.from_string(blueprint["variables"][name]).render(**context)

    event = simple_event(
        timing={
            "active_choice": "當天固定時間",
            "當天固定時間": {"time": "17:30:00"},
        },
        policy="run",
    )
    context.update(
        children_input=[child("群組", [event])],
        events_input=[],
        weekday_names=WEEKDAYS,
    )
    for name in ("valid_children", "runtime_events", "raw_candidates"):
        context[name] = environment.from_string(blueprint["variables"][name]).render(**context)

    assert context["check_time"] == as_timestamp(trigger_now)
    assert context["check_minute"] == int(as_timestamp(trigger_now))
    assert fallback_calls == []
    assert len(context["raw_candidates"]) == 1


def test_all_templates_are_jinja_syntax_valid(blueprint: dict) -> None:
    environment = Environment(autoescape=False)
    environment.filters["urlencode"] = quote_plus
    environment.filters["bool"] = bool
    for value in walk(blueprint):
        if isinstance(value, str) and any(token in value for token in ("{{", "{%", "{#")):
            environment.parse(value)


@pytest.mark.parametrize(
    ("active", "branch", "expected"),
    [
        ("前一天固定時間", {"time": "20:50:00"}, datetime(2026, 8, 17, 20, 50)),
        ("當天固定時間", {"time": "17:00:00"}, datetime(2026, 8, 18, 17, 0)),
        ("活動／上課前", {"minutes": 30}, datetime(2026, 8, 18, 17, 30)),
        ("下課前", {"minutes": 10}, datetime(2026, 8, 18, 19, 20)),
        ("下課後", {"minutes": 10}, datetime(2026, 8, 18, 19, 40)),
    ],
)
def test_five_reminder_datetime_calculations(active, branch, expected) -> None:
    timing = {"active_choice": active, active: branch}
    assert reminder_due(expected.date() if active != "前一天固定時間" else datetime(2026, 8, 18).date(), "18:00:00", "19:30:00", timing) == expected


def test_fixture_weekday_patterns_and_multiple_schedules(fixtures: dict) -> None:
    school = fixtures["weekday_school"][0]["schedules"]
    art = fixtures["tuesday_art"][0]["schedules"]
    multiple = fixtures["multiple_schedules"][0]["schedules"]
    assert school[0]["weekdays"] == WEEKDAYS[:5]
    assert art[0]["weekdays"] == ["tuesday"]
    assert [item["weekdays"][0] for item in multiple] == ["monday", "wednesday", "friday"]
    assert len(multiple) == 3


def test_same_event_has_multiple_independent_reminders(fixtures: dict) -> None:
    event = fixtures["tuesday_art"][0]
    checks = [
        datetime(2026, 8, 18, 17, 30),
        datetime(2026, 8, 18, 17, 50),
        datetime(2026, 8, 18, 19, 40),
    ]
    assert [len(find_matches([event], check)) for check in checks] == [1, 1, 1]
    messages = [find_matches([event], check)[0]["messages"][0] for check in checks]
    assert len(set(messages)) == 3


@pytest.mark.parametrize(
    ("holiday_on", "policy", "expected"),
    [(False, "skip", 1), (True, "skip", 0), (True, "run", 1)],
)
def test_makeup_holiday_policy(fixtures: dict, holiday_on: bool, policy: str, expected: int) -> None:
    event = fixtures["tuesday_art"][0] | {"makeup_holiday_behavior": policy}
    assert len(find_matches([event], datetime(2026, 8, 18, 17, 30), holiday_on)) == expected


def test_previous_day_reminder_is_blocked_when_switch_is_already_on(fixtures: dict) -> None:
    event = fixtures["tuesday_art"][0] | {"makeup_holiday_behavior": "skip"}
    check = datetime(2026, 8, 17, 20, 50)
    assert len(find_matches([event], check, holiday_on=False)) == 1
    assert find_matches([event], check, holiday_on=True) == []


def test_disabled_event_and_disabled_reminder(fixtures: dict) -> None:
    event = fixtures["tuesday_art"][0]
    check = datetime(2026, 8, 18, 17, 30)
    assert find_matches([event | {"enabled": False}], check) == []
    disabled_reminders = [item | {"enabled": False} for item in event["reminders"]]
    assert find_matches([event | {"reminders": disabled_reminders}], check) == []


def test_duplicate_schedule_deduplicates_one_candidate(fixtures: dict) -> None:
    matches = find_matches(fixtures["duplicate_schedules"], datetime(2026, 8, 18, 17, 30))
    assert len(matches) == 1


@pytest.mark.parametrize(
    ("event_day", "expected_due"),
    [
        (datetime(2026, 8, 17).date(), datetime(2026, 8, 16, 20, 50)),
        (datetime(2026, 8, 23).date(), datetime(2026, 8, 22, 20, 50)),
    ],
)
def test_previous_day_weekday_rollover(event_day, expected_due) -> None:
    timing = {"active_choice": "前一天固定時間", "前一天固定時間": {"time": "20:50:00"}}
    assert reminder_due(event_day, "18:00:00", "19:00:00", timing) == expected_due


def test_relative_offsets_can_cross_midnight() -> None:
    before = {"active_choice": "活動／上課前", "活動／上課前": {"minutes": 30}}
    after = {"active_choice": "下課後", "下課後": {"minutes": 20}}
    day = datetime(2026, 8, 18).date()
    assert reminder_due(day, "00:10:00", "01:00:00", before) == datetime(2026, 8, 17, 23, 40)
    assert reminder_due(day, "23:00:00", "23:50:00", after) == datetime(2026, 8, 19, 0, 10)


def test_blueprint_scans_adjacent_occurrence_days_for_relative_offsets(blueprint: dict) -> None:
    template = blueprint["variables"]["raw_candidates"]
    assert "for offset in [-2, -1, 0, 1]" in template


def test_actual_blueprint_template_previous_day_holiday_and_dedup(
    blueprint: dict, fixtures: dict
) -> None:
    art = fixtures["tuesday_art"]
    previous_day = render_blueprint_matches(
        blueprint, art, datetime(2026, 8, 17, 20, 50)
    )
    assert len(previous_day) == 1
    assert previous_day[0]["message"] == "姐姐，記得準備明天畫畫課要用的用品。"

    blocked_event = art[0] | {"makeup_holiday_behavior": "skip"}
    assert render_blueprint_matches(
        blueprint, [blocked_event], datetime(2026, 8, 17, 20, 50), holiday_on=True
    ) == []

    duplicate = render_blueprint_matches(
        blueprint, fixtures["duplicate_schedules"], datetime(2026, 8, 18, 17, 30)
    )
    assert len(duplicate) == 1


def test_actual_blueprint_template_relative_midnight_and_multiple_matches(
    blueprint: dict,
) -> None:
    event = {
        "name": "夜間活動",
        "enabled": True,
        "participant": "孩子",
        "location": "活動中心",
        "makeup_holiday_behavior": "run",
        "schedules": [
            {
                "weekdays": ["tuesday"],
                "start_time": "00:10:00",
                "end_time": "23:50:00",
            }
        ],
        "reminders": [
            {
                "name": "跨日前提醒",
                "enabled": True,
                "timing": {
                    "active_choice": "活動／上課前",
                    "活動／上課前": {"minutes": 30},
                },
                "messages": [{"message": "{event}還有{minutes}分鐘。"}],
            },
            {
                "name": "跨日後提醒",
                "enabled": True,
                "timing": {
                    "active_choice": "下課後",
                    "下課後": {"minutes": 20},
                },
                "messages": [],
            },
        ],
    }
    before = render_blueprint_matches(blueprint, [event], datetime(2026, 8, 17, 23, 40))
    after = render_blueprint_matches(blueprint, [event], datetime(2026, 8, 19, 0, 10))
    assert [item["message"] for item in before] == ["夜間活動還有30分鐘。"]
    assert [item["message"] for item in after] == ["孩子的夜間活動提醒時間到了。"]

    second = event | {"name": "另一活動"}
    simultaneous = render_blueprint_matches(
        blueprint, [event, second], datetime(2026, 8, 17, 23, 40)
    )
    assert [item["event"] for item in simultaneous] == ["夜間活動", "另一活動"]


def test_message_rules_and_safe_placeholder_replacement() -> None:
    assert normalize_messages([]) == []
    assert normalize_messages([{"message": "固定"}]) == ["固定"]
    assert normalize_messages([{"message": "A"}, {"message": "B"}]) == ["A", "B"]
    template = "再過{minutes}分鐘，{participant}的{event}在{location}開始。{{ unsafe }}"
    rendered = replace_placeholders(template, {"minutes": 30, "participant": "孩子", "event": "畫畫課", "location": "畫室"})
    assert rendered == "再過30分鐘，孩子的畫畫課在畫室開始。{{ unsafe }}"


def test_template_has_runtime_dedup_random_fallback_and_explicit_replacements(blueprint: dict) -> None:
    template = blueprint["variables"]["raw_candidates"]
    assert "key not in ns.keys" in template
    assert "msgs.values | random" in template
    assert "提醒時間到了。" in template
    for placeholder in ("event", "participant", "location", "start_time", "end_time", "minutes"):
        assert f"replace('{{{placeholder}}}'" in template
    assert "from_json" not in template


def test_children_take_priority_over_legacy_events(blueprint: dict) -> None:
    legacy = simple_event("舊事件", policy="run") | {"participant": "舊資料"}
    children = [child("姐姐", [simple_event("新事件", policy="run")])]
    matches = render_blueprint_matches(
        blueprint, [legacy], datetime(2026, 8, 18, 17, 0), children=children
    )
    assert [item["event"] for item in matches] == ["新事件"]


def test_invalid_children_fall_back_to_legacy_events(blueprint: dict) -> None:
    legacy = simple_event("舊事件", policy="run") | {"participant": "舊資料"}
    matches = render_blueprint_matches(
        blueprint,
        [legacy],
        datetime(2026, 8, 18, 17, 0),
        children=[{"name": "", "enabled": True, "events": []}],
    )
    assert [item["event"] for item in matches] == ["舊事件"]


def test_disabled_child_disables_entire_subtree_without_legacy_fallback(blueprint: dict) -> None:
    legacy = simple_event("不應播放", policy="run") | {"participant": "舊資料"}
    children = [child("姐姐", [simple_event(policy="run")], enabled=False)]
    assert render_blueprint_matches(
        blueprint, [legacy], datetime(2026, 8, 18, 17, 0), children=children
    ) == []


@pytest.mark.parametrize(
    ("spoken_name", "expected"),
    [("姊姊大人", "姊姊大人的畫畫課提醒時間到了。"), ("", "姐姐的畫畫課提醒時間到了。")],
)
def test_child_spoken_name_inheritance_and_fallback(
    blueprint: dict, spoken_name: str, expected: str
) -> None:
    matches = render_blueprint_matches(
        blueprint,
        [],
        datetime(2026, 8, 18, 17, 0),
        children=[child("姐姐", [simple_event(policy="run")], spoken_name=spoken_name)],
    )
    assert matches[0]["message"] == expected


def test_same_minute_children_preserve_input_order(blueprint: dict) -> None:
    children = [
        child("乙", [simple_event("Z 事件", policy="run")]),
        child("甲", [simple_event("A 事件", policy="run")]),
    ]
    matches = render_blueprint_matches(
        blueprint, [], datetime(2026, 8, 18, 17, 0), children=children
    )
    assert [item["event"] for item in matches] == ["Z 事件", "A 事件"]


def test_independent_reference_model_children_and_workday() -> None:
    children = [
        child("姐姐", [simple_event("姐姐事件")]),
        child("妹妹", [simple_event("妹妹事件", policy="run")]),
    ]
    matches = find_matches(
        [],
        datetime(2026, 8, 18, 17, 0),
        children=children,
        workdays={datetime(2026, 8, 18).date(): False},
    )
    assert [item["event"] for item in matches] == ["妹妹事件"]


@pytest.mark.parametrize(("is_workday", "expected"), [(True, 1), (False, 0)])
def test_workday_boolean_response_filters_skip_policy(
    blueprint: dict, is_workday: bool, expected: int
) -> None:
    entity = "binary_sensor.taiwan_workday"
    matches = render_blueprint_matches(
        blueprint,
        [],
        datetime(2026, 8, 18, 17, 0),
        children=[child("姐姐", [simple_event()])],
        workday_entity=entity,
        workday_responses={0: {entity: {"workday": is_workday}}},
    )
    assert len(matches) == expected


@pytest.mark.parametrize(
    "response",
    [None, {}, {"wrong.entity": {"workday": False}}, {"binary_sensor.taiwan_workday": {}},
     {"binary_sensor.taiwan_workday": {"workday": "false"}}],
)
def test_workday_missing_malformed_or_wrong_key_fails_open(blueprint: dict, response) -> None:
    entity = "binary_sensor.taiwan_workday"
    responses = {} if response is None else {0: response}
    matches = render_blueprint_matches(
        blueprint,
        [],
        datetime(2026, 8, 18, 17, 0),
        children=[child("姐姐", [simple_event()])],
        workday_entity=entity,
        workday_responses=responses,
    )
    assert len(matches) == 1


def test_run_policy_never_depends_on_workday_result(blueprint: dict) -> None:
    entity = "binary_sensor.taiwan_workday"
    matches = render_blueprint_matches(
        blueprint,
        [],
        datetime(2026, 8, 18, 17, 0),
        children=[child("姐姐", [simple_event(policy="run")])],
        workday_entity=entity,
        workday_responses={0: {entity: {"workday": False}}},
    )
    assert len(matches) == 1


def test_previous_day_reminder_uses_event_date_workday_response(blueprint: dict) -> None:
    entity = "binary_sensor.taiwan_workday"
    timing = {"active_choice": "前一天固定時間", "前一天固定時間": {"time": "20:50:00"}}
    kwargs = dict(
        blueprint=blueprint,
        events=[],
        check=datetime(2026, 8, 17, 20, 50),
        children=[child("姐姐", [simple_event(timing=timing)])],
        workday_entity=entity,
    )
    assert render_blueprint_matches(
        **kwargs, workday_responses={1: {entity: {"workday": False}}}
    ) == []
    assert len(render_blueprint_matches(
        **kwargs, workday_responses={1: {entity: {"workday": True}}}
    )) == 1


@pytest.mark.parametrize("minutes", [1439, 1440])
def test_overnight_after_end_maximum_offsets_are_found(blueprint: dict, minutes: int) -> None:
    timing = {"active_choice": "下課後", "下課後": {"minutes": minutes}}
    event = simple_event(
        "跨夜活動", weekday="monday", start="23:00:00", end="01:00:00",
        timing=timing, policy="run"
    )
    check = (
        datetime(2026, 8, 19, 0, 59)
        if minutes == 1439
        else datetime(2026, 8, 19, 1, 0)
    )
    matches = render_blueprint_matches(
        blueprint, [], check, children=[child("群組", [event])]
    )
    assert len(matches) == 1
    assert matches[0]["occurrence_offset"] == -2


def relative_due(kind: str, minutes: int) -> datetime:
    start = datetime(2026, 8, 18, 18, 0)
    end = datetime(2026, 8, 18, 19, 0)
    if kind == "活動／上課前":
        return start - timedelta(minutes=minutes)
    if kind == "下課前":
        return end - timedelta(minutes=minutes)
    return end + timedelta(minutes=minutes)


@pytest.mark.parametrize("kind", ["活動／上課前", "下課前", "下課後"])
@pytest.mark.parametrize("minutes", [1, 10, 30, 60, 1439, 1440])
def test_actual_blueprint_accepts_relative_minute_boundaries(
    blueprint: dict, kind: str, minutes: int
) -> None:
    timing = {"active_choice": kind, kind: {"minutes": minutes}}
    event = simple_event(timing=timing, policy="run")
    matches = render_blueprint_matches(
        blueprint, [], relative_due(kind, minutes), children=[child("群組", [event])]
    )
    assert len(matches) == 1


@pytest.mark.parametrize("kind", ["活動／上課前", "下課前", "下課後"])
@pytest.mark.parametrize("minutes", [0, -1, 1441, 2000, 9999])
def test_actual_blueprint_rejects_out_of_range_relative_minutes(
    blueprint: dict, kind: str, minutes: int
) -> None:
    timing = {"active_choice": kind, kind: {"minutes": minutes}}
    event = simple_event(timing=timing, policy="run")
    assert render_blueprint_matches(
        blueprint, [], relative_due(kind, minutes), children=[child("群組", [event])]
    ) == []


@pytest.mark.parametrize("kind", ["活動／上課前", "下課前", "下課後"])
@pytest.mark.parametrize("minutes", [None, "", "abc", [], {}, True, False])
def test_actual_blueprint_rejects_malformed_relative_minutes_without_error(
    blueprint: dict, kind: str, minutes: object
) -> None:
    timing = {"active_choice": kind, kind: {"minutes": minutes}}
    event = simple_event(timing=timing, policy="run")
    coerced = 1 if minutes is True else 0
    assert render_blueprint_matches(
        blueprint, [], relative_due(kind, coerced), children=[child("群組", [event])]
    ) == []


def test_runtime_relative_minutes_validation_is_numeric_integer_and_bounded(
    blueprint: dict,
) -> None:
    template = blueprint["variables"]["raw_candidates"]
    assert "raw_minutes is number" in template
    assert "raw_minutes is not boolean" in template
    assert "raw_minutes == raw_minutes | int" in template
    assert "1 <= raw_minutes <= 1440" in template


def test_workday_actions_are_fixed_deduplicated_and_fail_open(blueprint: dict) -> None:
    actions = [item for item in blueprint["actions"] if isinstance(item, dict)]
    checks = [
        step for step in actions if "then" in step
        for action in step["then"] if action.get("action") == "workday.check_date"
        for step in [action]
    ]
    assert len(checks) == 4
    assert len({item["response_variable"] for item in checks}) == 4
    assert all(item["continue_on_error"] is True for item in checks)
    assert "unique" in blueprint["variables"]["workday_query_offsets"]


def test_calendar_classifier_priority_and_fixture_examples(fixtures: dict) -> None:
    events = fixtures["calendar_events"]
    assert is_google_taiwan_holiday(events["national_holiday"]) is True
    assert is_google_taiwan_holiday(events["national_holiday_datetime"]) is True
    assert is_google_taiwan_holiday(events["makeup_workday"]) is False
    assert is_google_taiwan_holiday(events["observance"]) is False
    assert is_google_taiwan_holiday(events["unknown"]) is False


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-02-28", date(2026, 2, 28)),
        ("2026-10-09T00:00:00+08:00", date(2026, 10, 9)),
        ("2026-02-30", None),
        ("bad", None),
        (None, None),
    ],
)
def test_calendar_event_date_accepts_dates_and_datetimes(value, expected) -> None:
    assert calendar_event_date(value) == expected


def test_calendar_makeup_workday_marker_wins_over_holiday_description() -> None:
    event = {
        "summary": "春節補班",
        "description": "國定假日與假日節慶",
    }
    assert is_google_taiwan_holiday(event) is False


def test_actual_calendar_holiday_filters_occurrence_date(blueprint: dict) -> None:
    entity = "calendar.taiwan_holidays"
    response = {
        entity: {
            "events": [{
                "start": "2026-08-18",
                "end": "2026-08-19",
                "summary": "測試國定假日",
                "description": "國定假日",
            }]
        }
    }
    matches = render_blueprint_matches(
        blueprint,
        [],
        datetime(2026, 8, 18, 17, 0),
        children=[child("姐姐", [simple_event()])],
        holiday_source="calendar",
        calendar_entity=entity,
        calendar_response=response,
    )
    assert matches == []


def test_calendar_previous_day_reminder_uses_event_occurrence_date(blueprint: dict) -> None:
    entity = "calendar.taiwan_holidays"
    timing = {"active_choice": "前一天固定時間", "前一天固定時間": {"time": "20:50:00"}}
    response = {
        entity: {
            "events": [{
                "start": "2026-08-18T00:00:00+08:00",
                "end": "2026-08-19T00:00:00+08:00",
                "summary": "測試補假",
                "description": "國定假日",
            }]
        }
    }
    assert render_blueprint_matches(
        blueprint,
        [],
        datetime(2026, 8, 17, 20, 50),
        children=[child("姐姐", [simple_event(timing=timing)])],
        holiday_source="calendar",
        calendar_entity=entity,
        calendar_response=response,
    ) == []


@pytest.mark.parametrize(
    "response",
    [
        None,
        {},
        {"wrong.entity": {"events": []}},
        {"calendar.taiwan_holidays": {}},
        {"calendar.taiwan_holidays": {"events": "bad"}},
        {"calendar.taiwan_holidays": {"events": [{"start": "bad"}]}},
    ],
)
def test_calendar_missing_malformed_or_wrong_key_fails_open(blueprint: dict, response) -> None:
    matches = render_blueprint_matches(
        blueprint,
        [],
        datetime(2026, 8, 18, 17, 0),
        children=[child("姐姐", [simple_event()])],
        holiday_source="calendar",
        calendar_response=response,
    )
    assert len(matches) == 1


def test_calendar_observance_and_unknown_events_do_not_suppress(blueprint: dict, fixtures: dict) -> None:
    entity = "calendar.taiwan_holidays"
    response = {entity: {"events": [
        fixtures["calendar_events"]["observance"] | {"start": "2026-08-18"},
        fixtures["calendar_events"]["unknown"],
    ]}}
    matches = render_blueprint_matches(
        blueprint,
        [],
        datetime(2026, 8, 18, 17, 0),
        children=[child("姐姐", [simple_event()])],
        holiday_source="calendar",
        calendar_entity=entity,
        calendar_response=response,
    )
    assert len(matches) == 1


def test_calendar_run_policy_ignores_holiday(blueprint: dict) -> None:
    entity = "calendar.taiwan_holidays"
    response = {entity: {"events": [{
        "start": "2026-08-18", "summary": "假日", "description": "國定假日"
    }]}}
    matches = render_blueprint_matches(
        blueprint,
        [],
        datetime(2026, 8, 18, 17, 0),
        children=[child("姐姐", [simple_event(policy="run")])],
        holiday_source="calendar",
        calendar_entity=entity,
        calendar_response=response,
    )
    assert len(matches) == 1


def test_three_holiday_source_modes_are_mutually_exclusive(blueprint: dict) -> None:
    entity = "binary_sensor.taiwan_workday"
    calendar_entity = "calendar.taiwan_holidays"
    event = simple_event()
    calendar_nonholiday = {calendar_entity: {"events": [{
        "start": "2026-08-18", "summary": "節慶", "description": "假日節慶"
    }]}}
    common = dict(
        blueprint=blueprint,
        events=[],
        check=datetime(2026, 8, 18, 17, 0),
        children=[child("姐姐", [event])],
        calendar_entity=calendar_entity,
        calendar_response=calendar_nonholiday,
        workday_entity=entity,
        workday_responses={0: {entity: {"workday": False}}},
    )
    # Calendar ignores the conflicting Workday=false and legacy=on signals.
    assert len(render_blueprint_matches(**common, holiday_source="calendar", holiday_on=True)) == 1
    # Workday ignores the non-holiday calendar and legacy signal.
    assert render_blueprint_matches(**common, holiday_source="workday", holiday_on=True) == []
    # Legacy=off ignores both external sources.
    assert len(render_blueprint_matches(**common, holiday_source="legacy", holiday_on=False)) == 1


def test_calendar_action_is_single_bounded_fail_open_call(blueprint: dict, blueprint_text: str) -> None:
    calendar_calls = [
        node for node in walk(blueprint["actions"])
        if isinstance(node, dict) and node.get("action") == "calendar.get_events"
    ]
    assert len(calendar_calls) == 1
    call = calendar_calls[0]
    assert call["response_variable"] == "holiday_calendar_response"
    assert call["continue_on_error"] is True
    assert call["data"] == {
        "start_date_time": "{{ calendar_range_start }}",
        "end_date_time": "{{ calendar_range_end }}",
    }
    assert "timedelta(days=2)" in blueprint["variables"]["calendar_range_start"]
    assert "timedelta(days=2)" in blueprint["variables"]["calendar_range_end"]
    assert "skip_candidate_count" in blueprint["variables"]["calendar_query_enabled"]
    assert "homeassistant.update_entity" not in blueprint_text


@pytest.mark.parametrize(
    ("raw_candidates", "entity_state", "expected"),
    [
        ([], "off", False),
        ([{"non_workday_behavior": "run"}], "off", False),
        ([{"non_workday_behavior": "skip"}], "off", True),
        ([{"non_workday_behavior": "skip"}], "unavailable", False),
    ],
)
def test_actual_calendar_query_gate_only_allows_available_skip_candidates(
    blueprint: dict, raw_candidates: list[dict], entity_state: str, expected: bool
) -> None:
    environment = NativeEnvironment(autoescape=False)
    environment.globals["states"] = lambda _entity: entity_state
    context = {
        "raw_candidates": raw_candidates,
        "effective_holiday_source": "calendar",
        "holiday_calendar_entity_input": "calendar.taiwan_holidays",
    }
    for name in ("skip_candidate_count", "calendar_configured", "calendar_query_enabled"):
        context[name] = environment.from_string(blueprint["variables"][name]).render(**context)
    assert context["calendar_query_enabled"] is expected


@pytest.mark.parametrize(
    ("timing", "check", "response_offset"),
    [
        ({"active_choice": "活動／上課前", "活動／上課前": {"minutes": 30}},
         datetime(2026, 8, 17, 23, 40), 1),
        ({"active_choice": "下課前", "下課前": {"minutes": 10}},
         datetime(2026, 8, 18, 0, 50), 0),
        ({"active_choice": "下課後", "下課後": {"minutes": 20}},
         datetime(2026, 8, 18, 1, 20), 0),
    ],
)
def test_relative_modes_filter_by_occurrence_date(
    blueprint: dict, timing: dict, check: datetime, response_offset: int
) -> None:
    entity = "binary_sensor.taiwan_workday"
    event = simple_event(start="00:10:00", end="01:00:00", timing=timing)
    matches = render_blueprint_matches(
        blueprint,
        [],
        check,
        children=[child("姐姐", [event])],
        workday_entity=entity,
        workday_responses={response_offset: {entity: {"workday": False}}},
    )
    assert matches == []


def test_nested_selectors_follow_official_recursive_shape(blueprint: dict) -> None:
    """Object fields recursively contain exactly one registered selector type."""
    known = {"object", "text", "boolean", "select", "time", "number", "choose", "entity"}

    def validate(selector: dict) -> None:
        assert isinstance(selector, dict) and len(selector) == 1
        kind, config = next(iter(selector.items()))
        assert kind in known
        if kind == "object" and isinstance(config, dict):
            for field in config.get("fields", {}).values():
                validate(field["selector"])
        if kind == "choose":
            for choice in config["choices"].values():
                validate(choice["selector"])

    inputs = flatten_inputs(blueprint["blueprint"]["input"])
    for item in inputs.values():
        validate(item["selector"])


@pytest.mark.parametrize(("raw_candidates", "expected"), [([], False), ([{"key": "due"}], True)])
def test_top_level_queue_admission_condition_renders_candidate_presence(
    blueprint: dict, raw_candidates: list[dict], expected: bool
) -> None:
    condition = blueprint["conditions"][0]
    rendered = NativeEnvironment(autoescape=False).from_string(
        condition["value_template"]
    ).render(raw_candidates=raw_candidates)
    assert rendered is expected


def test_candidate_guards_cover_queue_admission_and_defensive_action(blueprint: dict) -> None:
    assert blueprint["mode"] == "queued"
    assert blueprint["max"] == 20
    assert blueprint["max_exceeded"] == "warning"
    assert blueprint["conditions"] == [
        {
            "condition": "template",
            "value_template": "{{ raw_candidates | count > 0 }}",
        }
    ]
    assert blueprint["actions"][0] == {
        "alias": "Phase A 沒有候選時不查假日來源、不改音量、不播放",
        "condition": "template",
        "value_template": "{{ raw_candidates | count > 0 }}",
    }
    assert "假日來源篩選後沒有提醒時不碰播放器或 TTS" in str(blueprint["actions"])


def test_runtime_candidate_key_contains_child_event_occurrence_reminder_and_due(
    blueprint: dict,
) -> None:
    template = blueprint["variables"]["raw_candidates"]
    for fragment in ("event.runtime_id", "day.date()", "ri", "due_minute"):
        assert fragment in template
    for field in ("'child':", "'participant':", "'event':", "'occurrence_date':"):
        assert field in template


def test_playback_snapshots_once_plays_all_then_restores_once(blueprint: dict, blueprint_text: str) -> None:
    assert "raw_candidates | count > 0" in blueprint["actions"][0]["value_template"]
    assert "matched_reminders | count > 0" in blueprint_text
    assert "for player in media_players_input" in blueprint_text
    assert "states(player) not in ['unknown', 'unavailable']" in blueprint_text
    assert "repeat.item.volume is number" in blueprint_text
    assert "player_snapshots if restore_original_volume_input else []" in blueprint_text
    assert "continue_on_error: true" in blueprint_text
    assert blueprint_text.count("action: media_player.volume_set") == 2
    play_position = blueprint_text.index("依序播放本分鐘全部提醒")
    restore_position = blueprint_text.index("全部訊息後只恢復一次")
    assert play_position < restore_position


def test_tts_media_source_wait_and_announce_wiring(blueprint_text: str) -> None:
    assert "'media-source://tts/' ~ tts_entity_input" in blueprint_text
    assert "announcement_message | urlencode" in blueprint_text
    assert "tts_language_input | urlencode" in blueprint_text
    assert "media_content_type: music" in blueprint_text
    assert 'announce: "{{ attempt_media_resume_input }}"' in blueprint_text
    assert "minimum_tts_wait_input" in blueprint_text
    assert "maximum_tts_wait_input" in blueprint_text
    assert "buffering_timeout_input" in blueprint_text


@pytest.mark.parametrize("bad_events", [None, {}, "bad", [], [None], [{"name": ""}]])
def test_invalid_or_empty_event_data_fails_safe(bad_events) -> None:
    assert find_matches(bad_events, datetime(2026, 8, 18, 12, 0)) == []


def test_scope_and_privacy_scan(blueprint_text: str) -> None:
    for forbidden in ("AmazingTalker", "OpenData", "OAuth", "寒假", "暑假", "颱風假", "補課"):
        assert forbidden not in blueprint_text
    assert not re.search(r"(?:token|password)\s*:", blueprint_text, re.IGNORECASE)
    assert not re.search(r"input_boolean\.[a-z0-9_]", blueprint_text)
    assert not re.search(
        r"media_player\.(?!volume_set\b|play_media\b)[a-z0-9_]", blueprint_text
    )


def test_my_home_assistant_import_links_are_correctly_encoded() -> None:
    for filename in ("README.md", "README.zh-TW.md"):
        text = (ROOT / filename).read_text(encoding="utf-8")
        match = re.search(r"https://my\.home-assistant\.io/redirect/blueprint_import/\?blueprint_url=[^)]+", text)
        assert match, filename
        parsed = urlparse(match.group(0))
        assert parse_qs(parsed.query)["blueprint_url"] == [SOURCE_URL]


def test_repository_text_is_utf8_without_bom() -> None:
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in {".git", ".venv", "BACKUP", ".pytest_cache", "__pycache__"} for part in path.parts):
            continue
        if path.suffix.lower() not in {".md", ".yaml", ".yml", ".py", ".txt", ""}:
            continue
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), path
        raw.decode("utf-8")


def test_github_actions_runs_all_required_validation() -> None:
    workflow = (ROOT / ".github" / "workflows" / "validate.yaml").read_text(encoding="utf-8")
    assert "actions/checkout@v6" in workflow
    assert "actions/setup-python@v6" in workflow
    assert "actions/checkout@v4" not in workflow
    assert "actions/setup-python@v5" not in workflow
    assert "python -m pip install -r requirements-dev.txt" in workflow
    assert "python -m yamllint ." in workflow
    assert "python -m pytest -q" in workflow
    assert "git diff --check" in workflow


def test_response_variables_are_guarded_and_compatibility_is_documented(
    blueprint: dict, blueprint_text: str
) -> None:
    response_variables = [
        node["response_variable"] for node in walk(blueprint["actions"])
        if isinstance(node, dict) and "response_variable" in node
    ]
    assert response_variables == [
        "holiday_calendar_response",
        "workday_response_minus_2",
        "workday_response_minus_1",
        "workday_response_same",
        "workday_response_plus_1",
    ]
    assert "is defined" in find_variable_template(blueprint["actions"], "matched_reminders")
    assert blueprint_text.count("continue_on_error: true") >= len(response_variables)
    compatibility = ROOT / "docs" / "HA_RESPONSE_VARIABLE_COMPATIBILITY.md"
    assert compatibility.exists()
    text = compatibility.read_text(encoding="utf-8")
    for needle in ("2026.8.1", "#178410", "workday.check_date", "calendar.get_events"):
        assert needle in text


def test_backup_zip_manifest_exclusions_verification_and_retention(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backup_module = importlib.import_module("scripts.create_backup")
    monkeypatch.setattr(backup_module, "ROOT", tmp_path)
    monkeypatch.setattr(backup_module, "BACKUP_DIR", tmp_path / "BACKUP")
    monkeypatch.setattr(
        backup_module,
        "git",
        lambda *args: {
            ("branch", "--show-current"): "main",
            ("rev-parse", "HEAD"): "0123456789abcdef0123456789abcdef01234567",
            ("status", "--short"): "clean",
        }[args],
    )
    (tmp_path / "source.txt").write_text("source", encoding="utf-8")
    for excluded in (".git", "BACKUP", ".venv", "venv", "__pycache__", ".pytest_cache"):
        directory = tmp_path / excluded
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "secret.txt").write_text("excluded", encoding="utf-8")
    (tmp_path / "ignored.pyc").write_bytes(b"excluded")

    created = [backup_module.create_backup() for _ in range(12)]
    backups = sorted((tmp_path / "BACKUP").glob("*.zip"))
    assert len({path.name for path in created}) == 12
    assert len(backups) == backup_module.KEEP_LATEST == 10

    import zipfile

    with zipfile.ZipFile(backups[-1]) as archive:
        assert archive.testzip() is None
        names = archive.namelist()
        assert "source.txt" in names
        assert "BACKUP_MANIFEST.txt" in names
        assert all("secret.txt" not in name for name in names)
        assert all(not name.endswith(".pyc") for name in names)
        manifest = archive.read("BACKUP_MANIFEST.txt").decode("utf-8")
        assert "repository:" in manifest
        assert "branch: main" in manifest
        assert "HEAD SHA: 0123456789abcdef" in manifest
        assert "git status:" in manifest
