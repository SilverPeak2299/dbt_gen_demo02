#!/usr/bin/env python3
"""Preflight checks before generating a DBT pipeline package."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


LOCKFILES = [
    ("package-lock.json", "npm", "npm ci", "npm run build"),
    ("yarn.lock", "yarn", "yarn install --frozen-lockfile", "yarn build"),
    ("pnpm-lock.yaml", "pnpm", "pnpm install --frozen-lockfile", "pnpm build"),
    ("bun.lockb", "bun", "bun install --frozen-lockfile", "bun run build"),
]

ADAPTER_DIALECTS = {
    "dbt-snowflake": "snowflake",
    "dbt-bigquery": "bigquery",
    "dbt-databricks": "databricks",
    "dbt-spark": "spark",
    "dbt-redshift": "redshift",
    "dbt-postgres": "postgres",
}

PRIVATE_RUNTIME_PATTERNS = {
    "profiles.yml",
    ".dbt",
    ".dbt/",
    ".env",
    ".env.*",
    "*.duckdb",
    "data/",
    "data/**",
}

PRIVATE_DATA_SUFFIXES = {".duckdb", ".db", ".sqlite", ".sqlite3", ".parquet"}


class Finding:
    def __init__(self, status: str, check: str, detail: str, fix: str = "") -> None:
        self.status = status
        self.check = check
        self.detail = detail
        self.fix = fix

    def as_dict(self) -> dict[str, str]:
        return {
            "status": self.status,
            "check": self.check,
            "detail": self.detail,
            "fix": self.fix,
        }


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def gitignore_patterns(root: Path) -> list[str]:
    patterns: list[str] = []
    for raw in read_text(root / ".gitignore").splitlines():
        stripped = raw.strip()
        if stripped and not stripped.startswith("#"):
            patterns.append(stripped)
    return patterns


def is_git_ignored(root: Path, path: Path) -> bool:
    try:
        relative = str(path.relative_to(root))
    except ValueError:
        return False
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "check-ignore", "-q", "--", relative],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        return False
    return result.returncode == 0


def ignored_runtime_inputs(root: Path) -> list[str]:
    ignored: set[str] = set()
    patterns = gitignore_patterns(root)

    for pattern in patterns:
        normalized = pattern.lstrip("/")
        if normalized in PRIVATE_RUNTIME_PATTERNS or normalized.endswith(".duckdb"):
            ignored.add(f".gitignore:{pattern}")

    candidates = [root / "profiles.yml", root / ".dbt", root / ".env"]
    for path in root.rglob("*"):
        if any(part in {".git", "node_modules", "target", "dbt_packages", "site"} for part in path.relative_to(root).parts):
            continue
        if path.is_file() and path.suffix.lower() in PRIVATE_DATA_SUFFIXES:
            candidates.append(path)

    for path in candidates:
        if path.exists() and is_git_ignored(root, path):
            ignored.add(str(path.relative_to(root)))

    return sorted(ignored)


def load_package_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(read_text(path))
    except json.JSONDecodeError:
        return {"__invalid__": True}
    return value if isinstance(value, dict) else {"__invalid__": True}


def find_lockfile(root: Path) -> tuple[str, str, str, str] | None:
    for filename, package_manager, install_command, build_command in LOCKFILES:
        if (root / filename).is_file():
            return filename, package_manager, install_command, build_command
    return None


def dependencies(package_json: dict[str, Any]) -> dict[str, str]:
    deps: dict[str, str] = {}
    for key in ["dependencies", "devDependencies"]:
        value = package_json.get(key, {})
        if isinstance(value, dict):
            deps.update({str(k): str(v) for k, v in value.items()})
    return deps


def scripts(package_json: dict[str, Any]) -> dict[str, str]:
    value = package_json.get("scripts", {})
    if not isinstance(value, dict):
        return {}
    return {str(k): str(v) for k, v in value.items()}


def infer_dialect(root: Path, package_json: dict[str, Any]) -> tuple[str | None, list[str]]:
    evidence: list[str] = []
    candidates: list[str] = []

    deps = dependencies(package_json)
    for package, dialect in ADAPTER_DIALECTS.items():
        if package in deps:
            candidates.append(dialect)
            evidence.append(f"package.json contains {package}")

    for path in [
        root / "packages.yml",
        root / "requirements.txt",
        root / "pyproject.toml",
        root / "profiles.yml",
        root / "dbt_project.yml",
    ]:
        text = read_text(path).lower()
        if not text:
            continue
        for package, dialect in ADAPTER_DIALECTS.items():
            if package in text or dialect in text:
                candidates.append(dialect)
                evidence.append(f"{path.name} references {dialect}")

    sql_samples = list(root.glob("models/**/*.sql"))[:25]
    for path in sql_samples:
        text = read_text(path).lower()
        if "qualify " in text:
            candidates.append("snowflake/bigquery/databricks")
            evidence.append(f"{path}: uses QUALIFY")
        if "::" in text:
            candidates.append("postgres/redshift/snowflake")
            evidence.append(f"{path}: uses :: casts")
        if "unnest(" in text:
            candidates.append("bigquery/postgres")
            evidence.append(f"{path}: uses UNNEST")

    unique = sorted(set(candidates))
    if len(unique) == 1:
        return unique[0], evidence
    return None, evidence


def docusaurus_config_text(root: Path) -> str:
    parts = []
    for pattern in ["docusaurus.config.*", "sidebars.*"]:
        for path in root.glob(pattern):
            parts.append(read_text(path))
    return "\n".join(parts)


def preflight(root: Path, args: argparse.Namespace) -> tuple[list[Finding], dict[str, Any]]:
    findings: list[Finding] = []
    facts: dict[str, Any] = {"root": str(root)}

    dbt_project = root / "dbt_project.yml"
    if dbt_project.is_file():
        findings.append(Finding("pass", "dbt project", "dbt_project.yml found"))
        facts["dbt_project"] = True
    else:
        findings.append(
            Finding(
                "info",
                "dbt project",
                "dbt_project.yml not found; fresh pipeline package generation is expected",
                "Use assets/dbt/dbt-project.yml if a standalone scaffold is needed.",
            )
        )
        facts["dbt_project"] = False

    private_inputs = ignored_runtime_inputs(root)
    facts["ignored_runtime_inputs"] = private_inputs
    if private_inputs:
        findings.append(
            Finding(
                "warn",
                "private dbt runtime inputs",
                "ignored profiles, credentials, or data detected: " + ", ".join(private_inputs),
                "Prefer static review docs for public Pages publishing unless dbt runtime validation in CI was explicitly requested.",
            )
        )
    else:
        findings.append(Finding("info", "private dbt runtime inputs", "no ignored profiles or private data files detected"))

    package_json_path = root / "package.json"
    package_json = load_package_json(package_json_path)
    if package_json.get("__invalid__"):
        findings.append(
            Finding("fail", "package.json", "package.json is invalid JSON", "Fix package.json before generating docs workflows.")
        )
    elif package_json:
        findings.append(Finding("pass", "package.json", "package.json found"))
    else:
        findings.append(
            Finding(
                "warn",
                "package.json",
                "package.json not found",
                "Required if generating or validating Docusaurus docs.",
            )
        )

    lockfile = find_lockfile(root)
    if lockfile:
        lockfile_name, package_manager, install_command, build_command = lockfile
        facts.update(
            {
                "lockfile": lockfile_name,
                "package_manager": package_manager,
                "install_command": install_command,
                "build_command": build_command,
            }
        )
        findings.append(
            Finding("pass", "package manager", f"{package_manager} inferred from {lockfile_name}")
        )
    else:
        findings.append(
            Finding(
                "warn",
                "package manager",
                "no lockfile found",
                "Choose npm, yarn, pnpm, or bun before generating the publishing workflow.",
            )
        )

    deps = dependencies(package_json)
    package_scripts = scripts(package_json)
    if "@docusaurus/core" in deps:
        findings.append(Finding("pass", "Docusaurus", "@docusaurus/core found"))
        facts["docusaurus"] = True
    else:
        findings.append(
            Finding(
                "warn",
                "Docusaurus",
                "@docusaurus/core not found",
                "Use static docs publishing, or add Docusaurus before generating a Docusaurus workflow.",
            )
        )
        facts["docusaurus"] = False

    build_script = package_scripts.get("build")
    if build_script:
        findings.append(Finding("pass", "docs build command", f"build script: {build_script}"))
        facts["build_command"] = facts.get("build_command") or f"{facts.get('package_manager', 'npm')} run build"
    else:
        findings.append(
            Finding("warn", "docs build command", "package.json has no build script", "Required for Docusaurus publishing; static docs can continue without it.")
        )

    config_text = docusaurus_config_text(root)
    ts_used = (
        (root / "tsconfig.json").is_file()
        or bool(list(root.glob("docusaurus.config.ts")))
        or bool(list(root.glob("src/**/*.tsx")))
        or bool(list(root.glob("src/**/*.ts")))
    )
    facts["typescript"] = ts_used
    if ts_used and "typescript" not in deps:
        findings.append(
            Finding(
                "fail",
                "TypeScript",
                "TypeScript files/config found but package.json does not include typescript",
                "Add typescript or confirm the docs site is JavaScript-only.",
            )
        )
    elif ts_used:
        findings.append(Finding("pass", "TypeScript", "TypeScript support detected"))
    else:
        findings.append(Finding("info", "TypeScript", "no TypeScript usage detected"))

    mermaid_package = "@docusaurus/theme-mermaid" in deps
    mermaid_theme_configured = "@docusaurus/theme-mermaid" in config_text
    mermaid_markdown_enabled = bool(re.search(r"mermaid\s*:\s*true", config_text))
    facts["mermaid_package"] = mermaid_package
    facts["mermaid_theme_configured"] = mermaid_theme_configured
    facts["mermaid_markdown_enabled"] = mermaid_markdown_enabled
    mermaid_supported = mermaid_package and mermaid_theme_configured and mermaid_markdown_enabled
    facts["mermaid"] = mermaid_supported
    if mermaid_supported:
        findings.append(Finding("pass", "Mermaid", "Docusaurus Mermaid package and markdown config detected"))
    else:
        findings.append(
            Finding(
                "warn",
                "Mermaid",
                "Docusaurus Mermaid support not fully detected",
                "For Docusaurus, add @docusaurus/theme-mermaid to dependencies and themes, and set markdown.mermaid: true. Static docs can render Mermaid through scripts/build_static_docs.py.",
            )
        )

    dialect = args.sql_dialect
    evidence: list[str] = []
    if not dialect:
        dialect, evidence = infer_dialect(root, package_json)
    facts["sql_dialect"] = dialect
    facts["sql_dialect_evidence"] = evidence
    if dialect:
        findings.append(Finding("pass", "SQL dialect", f"selected/inferred: {dialect}"))
    else:
        findings.append(
            Finding(
                "warn",
                "SQL dialect",
                "SQL dialect not supplied or confidently inferred",
                "Ask for the warehouse dialect or generate conservative ANSI-style SQL and record this as an open question.",
            )
        )

    workflows = sorted((root / ".github" / "workflows").glob("*.yml")) + sorted(
        (root / ".github" / "workflows").glob("*.yaml")
    )
    facts["workflows"] = [str(path.relative_to(root)) for path in workflows]
    pages_workflows = [
        path
        for path in workflows
        if "deploy-pages" in read_text(path) or "pages: write" in read_text(path)
    ]
    if pages_workflows:
        findings.append(
            Finding(
                "pass",
                "GitHub Pages workflow",
                "existing Pages workflow found: "
                + ", ".join(str(path.relative_to(root)) for path in pages_workflows),
            )
        )
    else:
        findings.append(
            Finding(
                "warn",
                "GitHub Pages workflow",
                "no existing Pages publishing workflow detected",
                "Generate a static docs or Docusaurus workflow based on the selected publishing mode.",
            )
        )

    findings.append(
        Finding(
            "info",
            "GitHub Pages setup",
            "local preflight cannot verify whether Pages is enabled for this repository",
            "Enable Pages once under Settings > Pages > Build and deployment > Source > GitHub Actions.",
        )
    )

    if private_inputs:
        recommended_mode = "static-review-docs"
        mode_detail = "private runtime inputs are ignored"
    elif facts.get("docusaurus"):
        recommended_mode = "docusaurus-site"
        mode_detail = "Docusaurus project detected"
    else:
        recommended_mode = "static-review-docs"
        mode_detail = "no Docusaurus project detected"
    facts["recommended_publish_mode"] = recommended_mode
    findings.append(
        Finding(
            "info",
            "publishing mode recommendation",
            f"{recommended_mode}: {mode_detail}",
        )
    )

    facts["dbt_command"] = shutil.which("dbt") or ""
    if facts["dbt_command"]:
        findings.append(Finding("pass", "dbt command", f"dbt found at {facts['dbt_command']}"))
    else:
        findings.append(
            Finding("warn", "dbt command", "dbt command not found", "Static generation can continue; dbt parse/compile cannot run locally.")
        )

    return findings, facts


def print_markdown(findings: list[Finding], facts: dict[str, Any]) -> None:
    print("## Preflight Check")
    print()
    print("| Status | Check | Detail | Suggested Fix |")
    print("| --- | --- | --- | --- |")
    for item in findings:
        print(
            f"| {item.status} | {item.check} | {item.detail} | {item.fix or '-'} |"
        )
    print()
    print("### Facts")
    for key in sorted(facts):
        value = facts[key]
        if isinstance(value, list):
            value = ", ".join(value) if value else "-"
        print(f"- `{key}`: {value or '-'}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Inspect a consuming repository before generating a pipeline package."
    )
    parser.add_argument("repo_path", help="Path to the consuming repository")
    parser.add_argument("--sql-dialect", help="Explicit target SQL dialect")
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as failures",
    )
    args = parser.parse_args(argv)

    root = Path(args.repo_path).resolve()
    if not root.is_dir():
        print(f"repo path is not a directory: {root}", file=sys.stderr)
        return 1

    findings, facts = preflight(root, args)
    if args.json:
        print(
            json.dumps(
                {
                    "findings": [item.as_dict() for item in findings],
                    "facts": facts,
                },
                indent=2,
            )
        )
    else:
        print_markdown(findings, facts)

    has_failures = any(item.status == "fail" for item in findings)
    has_warnings = any(item.status == "warn" for item in findings)
    if has_failures:
        return 1
    if args.strict and has_warnings:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
