#!/usr/bin/env python3
"""Render skill asset templates that use {{placeholder}} tokens."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


PLACEHOLDER_RE = re.compile(
    r"(?P<indent>^[ \t]*)?(?<!\$)\{\{\s*(?P<key>[A-Za-z0-9_.-]+)\s*\}\}",
    re.MULTILINE,
)


def load_json(path: str) -> dict[str, Any]:
    try:
        text = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
        value = json.loads(text)
    except OSError as exc:
        raise SystemExit(f"could not read vars JSON: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid vars JSON: {exc}") from exc

    if not isinstance(value, dict):
        raise SystemExit("vars JSON must be an object")
    return value


def parse_vars(items: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"--var must be key=value, got: {item}")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise SystemExit(f"--var key is empty: {item}")
        values[key] = value
    return values


def stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(value, indent=2, sort_keys=True)


def indent_multiline(value: str, indent: str | None) -> str:
    if not indent or "\n" not in value:
        return value
    lines = value.splitlines()
    if not lines:
        return value
    return "\n".join([lines[0], *[indent + line if line else line for line in lines[1:]]])


def placeholders(template: str) -> list[str]:
    return sorted({match.group("key") for match in PLACEHOLDER_RE.finditer(template)})


def render(template: str, values: dict[str, Any], allow_unresolved: bool) -> tuple[str, list[str]]:
    missing: set[str] = set()

    def replace(match: re.Match[str]) -> str:
        key = match.group("key")
        if key not in values:
            missing.add(key)
            return match.group(0)
        return indent_multiline(stringify(values[key]), match.group("indent"))

    output = PLACEHOLDER_RE.sub(replace, template)
    unresolved = placeholders(output)
    if allow_unresolved:
        return output, sorted(missing)
    return output, sorted(set(unresolved) | missing)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Render a {{placeholder}} template.")
    parser.add_argument("template", help="Template file to render")
    parser.add_argument("-o", "--output", help="Output file. Defaults to stdout")
    parser.add_argument(
        "--vars-json",
        action="append",
        default=[],
        help="JSON object file containing placeholder values. Use '-' for stdin",
    )
    parser.add_argument(
        "--var",
        action="append",
        default=[],
        help="Placeholder value as key=value. May be repeated",
    )
    parser.add_argument(
        "--list-placeholders",
        action="store_true",
        help="List placeholders in the template and exit",
    )
    parser.add_argument(
        "--allow-unresolved",
        action="store_true",
        help="Allow unresolved placeholders in rendered output",
    )
    args = parser.parse_args(argv)

    template_path = Path(args.template)
    try:
        template = template_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SystemExit(f"could not read template: {exc}") from exc

    if args.list_placeholders:
        for key in placeholders(template):
            print(key)
        return 0

    values: dict[str, Any] = {}
    for path in args.vars_json:
        values.update(load_json(path))
    values.update(parse_vars(args.var))

    output, unresolved = render(template, values, args.allow_unresolved)
    if unresolved:
        print(
            "unresolved placeholders: " + ", ".join(unresolved),
            file=sys.stderr,
        )
        return 1

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding="utf-8")
    else:
        print(output, end="")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
