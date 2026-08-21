"""Validate Blueprint Object selectors against Home Assistant 2026.8.1."""

from __future__ import annotations

import argparse
from pathlib import Path
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


class BlueprintLoader(yaml.SafeLoader):
    """Load Home Assistant Blueprint YAML without resolving inputs."""


BlueprintLoader.add_constructor(
    "!input", lambda loader, node: loader.construct_scalar(node)
)


def validate_selector(selector: Any, path: str) -> list[str]:
    """Return Object selector schema errors from one recursive selector tree."""
    errors: list[str] = []
    if not isinstance(selector, dict):
        return [f"{path} must be a mapping with exactly one selector type"]
    if len(selector) != 1:
        return [
            f"{path} must contain exactly one selector type; "
            f"found keys: {sorted(selector)}"
        ]

    selector_type, config = next(iter(selector.items()))
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

    if selector_type == "choose" and not isinstance(config, dict):
        errors.append(f"{path}.choose config must be a mapping")
    elif selector_type == "choose":
        choices = config.get("choices", {})
        if not isinstance(choices, dict):
            errors.append(f"{path}.choose.choices must be a mapping")
        else:
            for choice_name, choice_config in choices.items():
                choice_path = f"{path}.choose.choices.{choice_name}"
                if not isinstance(choice_config, dict) or "selector" not in choice_config:
                    errors.append(f"{choice_path} must contain selector")
                    continue
                errors.extend(
                    validate_selector(
                        choice_config["selector"],
                        f"{choice_path}.selector",
                    )
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
    with args.blueprint.open(encoding="utf-8") as stream:
        blueprint = yaml.load(stream, Loader=BlueprintLoader)
    errors = validate_blueprint_selectors(blueprint)
    if errors:
        for error in errors:
            print(error)
        return 1
    print("Home Assistant 2026.8.1 Object selector schema: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
