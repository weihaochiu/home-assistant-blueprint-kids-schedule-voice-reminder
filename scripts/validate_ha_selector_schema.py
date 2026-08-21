"""Check repository selector shapes against Home Assistant Core 2026.8.1."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BLUEPRINT_PATH = (
    ROOT
    / "blueprints"
    / "automation"
    / "weihaochiu"
    / "kids_schedule_voice_reminder.yaml"
)
OBJECT_SELECTOR_FIELD_ALLOWED_KEYS = {"label", "required", "selector"}
OBJECT_SELECTOR_CONFIG_ALLOWED_KEYS = {
    "fields",
    "multiple",
    "label_field",
    "description_field",
    "translation_key",
    "read_only",
}
CHOOSE_SELECTOR_CONFIG_ALLOWED_KEYS = {"choices", "translation_key", "read_only"}
CHOOSE_SELECTOR_CHOICE_ALLOWED_KEYS = {"selector"}
SUPPORTED_SELECTOR_TYPES = {
    "boolean",
    "choose",
    "entity",
    "number",
    "object",
    "select",
    "text",
    "time",
}


class BlueprintLoader(yaml.SafeLoader):
    """Load Home Assistant Blueprint YAML without resolving inputs."""


BlueprintLoader.add_constructor(
    "!input", lambda loader, node: loader.construct_scalar(node)
)


def validate_selector(selector: Any, path: str) -> list[str]:
    """Return repository-scoped structural errors from one selector tree."""
    errors: list[str] = []
    if not isinstance(selector, dict):
        return [f"{path} must be a mapping with exactly one selector type"]
    if len(selector) != 1:
        return [
            f"{path} must contain exactly one selector type; "
            f"found keys: {sorted(selector)}"
        ]

    selector_type, config = next(iter(selector.items()))
    if selector_type not in SUPPORTED_SELECTOR_TYPES:
        return [f"{path} uses unknown or unsupported selector type: {selector_type}"]

    if selector_type == "object" and config is not None and not isinstance(config, dict):
        errors.append(f"{path}.object config must be a mapping or null")
        return errors

    if selector_type == "object" and isinstance(config, dict):
        unsupported_config = set(config) - OBJECT_SELECTOR_CONFIG_ALLOWED_KEYS
        if unsupported_config:
            errors.append(
                f"{path}.object has unsupported config keys: "
                f"{sorted(unsupported_config)}"
            )

        fields = config.get("fields", {})
        if not isinstance(fields, dict):
            errors.append(f"{path}.object.fields must be a mapping")
            return errors
        for field_name, field_config in fields.items():
            field_path = f"{path}.object.fields.{field_name}"
            if not isinstance(field_config, dict):
                errors.append(f"{field_path} must be a mapping")
                continue
            unsupported_field = (
                set(field_config) - OBJECT_SELECTOR_FIELD_ALLOWED_KEYS
            )
            if unsupported_field:
                errors.append(
                    f"{field_path} has unsupported metadata keys: "
                    f"{sorted(unsupported_field)}"
                )
            if "selector" not in field_config:
                errors.append(f"{field_path} is missing required selector")
                continue
            errors.extend(
                validate_selector(field_config["selector"], f"{field_path}.selector")
            )

    if selector_type != "choose":
        return errors
    if not isinstance(config, dict):
        errors.append(f"{path}.choose config must be a mapping")
        return errors

    unsupported_config = set(config) - CHOOSE_SELECTOR_CONFIG_ALLOWED_KEYS
    if unsupported_config:
        errors.append(
            f"{path}.choose has unsupported config keys: {sorted(unsupported_config)}"
        )
    if "choices" not in config:
        errors.append(f"{path}.choose is missing required choices")
        return errors

    choices = config["choices"]
    if not isinstance(choices, dict):
        errors.append(f"{path}.choose.choices must be a mapping")
        return errors
    for choice_name, choice_config in choices.items():
        choice_path = f"{path}.choose.choices.{choice_name}"
        if not isinstance(choice_config, dict):
            errors.append(f"{choice_path} must be a mapping")
            continue
        unsupported_choice = (
            set(choice_config) - CHOOSE_SELECTOR_CHOICE_ALLOWED_KEYS
        )
        if unsupported_choice:
            errors.append(
                f"{choice_path} has unsupported metadata keys: "
                f"{sorted(unsupported_choice)}"
            )
        if "selector" not in choice_config:
            errors.append(f"{choice_path} is missing required selector")
            continue

        choice_selector_path = f"{choice_path}.selector"
        choice_selector = choice_config["selector"]
        errors.extend(validate_selector(choice_selector, choice_selector_path))
        if (
            isinstance(choice_selector, dict)
            and len(choice_selector) == 1
            and "choose" in choice_selector
        ):
            errors.append(
                f"{choice_selector_path}: nested choose selectors are not allowed"
            )
    return errors


def validate_blueprint_selectors(blueprint: dict[str, Any]) -> list[str]:
    """Return Object selector schema errors from every Blueprint input."""
    errors: list[str] = []

    def visit_inputs(inputs: Any, path: str) -> None:
        if not isinstance(inputs, dict):
            return
        for input_name, input_config in inputs.items():
            input_path = f"{path}.{input_name}"
            if not isinstance(input_config, dict):
                continue
            if "input" in input_config:
                visit_inputs(input_config["input"], f"{input_path}.input")
            elif "selector" in input_config:
                errors.extend(
                    validate_selector(input_config["selector"], f"{input_path}.selector")
                )

    visit_inputs(blueprint.get("blueprint", {}).get("input", {}), "blueprint.input")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "blueprint",
        nargs="?",
        type=Path,
        default=DEFAULT_BLUEPRINT_PATH,
        help=f"Blueprint YAML path (default: {DEFAULT_BLUEPRINT_PATH})",
    )
    args = parser.parse_args()
    try:
        with args.blueprint.open(encoding="utf-8") as stream:
            blueprint = yaml.load(stream, Loader=BlueprintLoader)
    except OSError as error:
        print(f"Unable to read {args.blueprint}: {error}", file=sys.stderr)
        return 2
    except yaml.YAMLError as error:
        print(f"Unable to parse {args.blueprint}: {error}", file=sys.stderr)
        return 2
    if not isinstance(blueprint, dict):
        print(f"{args.blueprint}: Blueprint root must be a mapping", file=sys.stderr)
        return 1

    errors = validate_blueprint_selectors(blueprint)
    if errors:
        for error in errors:
            print(error)
        return 1
    print("HA Core 2026.8.1 repository selector shapes: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
