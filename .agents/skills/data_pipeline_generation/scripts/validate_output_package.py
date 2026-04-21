#!/usr/bin/env python3
"""Validate a generated DBT pipeline output package.

This script intentionally uses only the Python standard library so it can run
inside most consuming repositories without installing dependencies.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


PLACEHOLDER_RE = re.compile(r"(?<!\$)\{\{\s*[A-Za-z0-9_.-]+\s*\}\}")
TEXT_SUFFIXES = {
    ".py",
    ".sql",
    ".yml",
    ".yaml",
    ".md",
    ".mdx",
    ".js",
    ".json",
    ".txt",
    ".gitignore",
}
SKIP_DIRS = {".git", "node_modules", "target", "dbt_packages", "build", "site", ".docusaurus"}


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.info: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def note(self, message: str) -> None:
        self.info.append(message)

    def as_dict(self) -> dict[str, list[str]]:
        return {
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info,
        }


def read_text(path: Path, report: Report) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        report.error(f"{path}: file is not valid UTF-8 text")
    except OSError as exc:
        report.error(f"{path}: could not read file: {exc}")
    return ""


def rel(path: Path, root: Path) -> str:
    return str(path.relative_to(root))


def iter_text_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if path.name == ".gitignore" or path.suffix in TEXT_SUFFIXES:
            files.append(path)
    return sorted(files)


def check_required_structure(root: Path, report: Report) -> None:
    for directory in ["models", "docs", "mappings", "design"]:
        path = root / directory
        if not path.is_dir():
            report.error(f"missing required directory: {directory}/")

    gitignore = root / ".gitignore"
    if not gitignore.is_file():
        report.error("missing required .gitignore at package root")


def check_unresolved_placeholders(root: Path, report: Report) -> None:
    for path in iter_text_files(root):
        text = read_text(path, report)
        matches = sorted(set(PLACEHOLDER_RE.findall(text)))
        if matches:
            report.error(
                f"{rel(path, root)}: unresolved placeholders remain: {', '.join(matches)}"
            )


def check_gitignore(root: Path, report: Report) -> None:
    path = root / ".gitignore"
    if not path.is_file():
        return

    lines = []
    for raw in read_text(path, report).splitlines():
        stripped = raw.strip()
        if stripped and not stripped.startswith("#"):
            lines.append(stripped.rstrip("/"))

    dangerous = {
        "*.sql",
        "*.yml",
        "*.yaml",
        "*.md",
        "*.mdx",
        "models",
        "docs",
        "mappings",
        "design",
    }
    blocked = sorted(pattern for pattern in lines if pattern in dangerous)
    if blocked:
        report.error(
            ".gitignore hides generated deliverables: " + ", ".join(blocked)
        )

    if (root / "scripts" / "build_static_docs.py").is_file() and "site" not in lines:
        report.warn(".gitignore should ignore generated static site output: site/")


def check_dbt_files(root: Path, report: Report) -> None:
    models_dir = root / "models"
    sql_files = sorted(models_dir.rglob("*.sql")) if models_dir.is_dir() else []
    if not sql_files:
        report.error("no DBT SQL files found under models/")
    else:
        report.note(f"found {len(sql_files)} DBT SQL file(s)")

    if models_dir.is_dir():
        if not (models_dir / "staging").is_dir():
            report.warn("models/staging/ is missing")
        if not (models_dir / "marts").is_dir():
            report.warn("models/marts/ is missing")

    schema_files = sorted(root.rglob("schema.y*ml"))
    source_files = sorted(root.rglob("sources.y*ml"))

    if not schema_files:
        report.error("missing DBT schema.yml")
    for path in schema_files:
        text = read_text(path, report)
        if "version:" not in text or "models:" not in text:
            report.error(f"{rel(path, root)}: expected version and models keys")

    if not source_files:
        report.warn("missing DBT sources.yml")
    for path in source_files:
        text = read_text(path, report)
        if "version:" not in text or "sources:" not in text:
            report.error(f"{rel(path, root)}: expected version and sources keys")


def check_mdx(root: Path, report: Report) -> None:
    docs_dir = root / "docs"
    doc_files = sorted(docs_dir.rglob("*.mdx")) + sorted(docs_dir.rglob("*.md")) if docs_dir.is_dir() else []
    if not doc_files:
        report.error("no documentation Markdown or MDX file found under docs/")
        return

    mermaid_blocks = 0
    docusaurus_mdx = 0
    for path in doc_files:
        text = read_text(path, report)
        relative = rel(path, root)
        mermaid_blocks += text.count("```mermaid")
        if path.suffix == ".mdx" and ("<Tabs" in text or "<TabItem" in text):
            docusaurus_mdx += 1
            if "@theme/Tabs" not in text:
                report.error(f"{relative}: missing Docusaurus Tabs import")
            if "@theme/TabItem" not in text:
                report.error(f"{relative}: missing Docusaurus TabItem import")

    if mermaid_blocks == 0:
        report.error("generated documentation is missing Mermaid diagram fences")
    elif mermaid_blocks < 2:
        report.warn("generated documentation should include at least two Mermaid diagrams")
    if docusaurus_mdx:
        report.note(f"found {docusaurus_mdx} Docusaurus MDX file(s)")


def normalize_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def check_mapping(root: Path, report: Report) -> None:
    mappings_dir = root / "mappings"
    mapping_files = sorted(mappings_dir.glob("*.md")) if mappings_dir.is_dir() else []
    if not mapping_files:
        report.error("no source-to-target mapping Markdown found under mappings/")
        return

    required = {
        "target model",
        "target column",
        "source table",
        "source column",
        "transformation logic",
    }

    for path in mapping_files:
        text = read_text(path, report)
        header_line = next(
            (
                line
                for line in text.splitlines()
                if line.strip().startswith("|") and "---" not in line
            ),
            "",
        )
        headers = {normalize_header(cell) for cell in header_line.split("|")}
        missing = sorted(required - headers)
        if missing:
            report.error(
                f"{rel(path, root)}: mapping table missing columns: {', '.join(missing)}"
            )


def check_design_doc(root: Path, report: Report) -> None:
    design_dir = root / "design"
    design_files = sorted(design_dir.glob("*.md")) if design_dir.is_dir() else []
    if not design_files:
        report.error("no design document Markdown found under design/")
        return

    for path in design_files:
        text = read_text(path, report).lower()
        relative = rel(path, root)
        for phrase in ["assumption", "test", "quality"]:
            if phrase not in text:
                report.warn(f"{relative}: consider adding {phrase} details")


def check_static_docs_builder(root: Path, report: Report) -> None:
    path = root / "scripts" / "build_static_docs.py"
    if not path.is_file():
        return

    text = read_text(path, report)
    if 'class="mermaid"' not in text and "class='mermaid'" not in text:
        report.error("scripts/build_static_docs.py: Mermaid fences must render to elements with class=\"mermaid\"")
    if "mermaid.run" not in text:
        report.error("scripts/build_static_docs.py: missing explicit mermaid.run rendering call")
    if "querySelector: '.mermaid'" not in text and 'querySelector: ".mermaid"' not in text:
        report.warn("scripts/build_static_docs.py: mermaid.run should target .mermaid elements")


def check_github_actions(root: Path, report: Report) -> None:
    workflows_dir = root / ".github" / "workflows"
    workflows = sorted(workflows_dir.glob("*.yml")) + sorted(workflows_dir.glob("*.yaml"))
    if not workflows:
        report.warn("no GitHub Actions workflow found under .github/workflows/")
        return

    pages_workflows = 0
    for path in workflows:
        text = read_text(path, report)
        relative = rel(path, root)
        is_pages_workflow = (
            "actions/deploy-pages" in text
            or "actions/upload-pages-artifact" in text
            or "pages: write" in text
        )
        if not is_pages_workflow:
            continue

        pages_workflows += 1
        if "pages: write" not in text or "id-token: write" not in text:
            report.error(f"{relative}: missing GitHub Pages permissions")
        if "actions/configure-pages" in text:
            report.warn(f"{relative}: configure-pages requires Pages to be enabled before the workflow runs")
        if "actions/upload-pages-artifact" not in text:
            report.error(f"{relative}: missing upload-pages-artifact action")
        if "actions/upload-pages-artifact@v3" in text:
            report.warn(f"{relative}: upload-pages-artifact@v3 is older than the current GitHub Pages example")
        if "actions/deploy-pages" not in text:
            report.error(f"{relative}: missing deploy-pages action")
        if "dbt build" in text or "dbt docs generate" in text:
            report.warn(f"{relative}: Pages publishing runs dbt; confirm CI has an explicit profile, secrets, and data-access plan")

        static_docs = "build_static_docs.py" in text
        if static_docs:
            if not (root / "scripts" / "build_static_docs.py").is_file():
                report.error(f"{relative}: static docs workflow references missing scripts/build_static_docs.py")
            if "site" not in text:
                report.warn(f"{relative}: static docs workflow should upload the generated site/ directory")
        elif "npm run build" not in text and "yarn build" not in text and "pnpm" not in text and "bun" not in text:
            report.warn(f"{relative}: could not identify Docusaurus build command")

    if pages_workflows == 0:
        report.warn("no GitHub Pages publishing workflow found under .github/workflows/")


def validate(root: Path) -> Report:
    report = Report()
    if not root.exists():
        report.error(f"package path does not exist: {root}")
        return report
    if not root.is_dir():
        report.error(f"package path is not a directory: {root}")
        return report

    check_required_structure(root, report)
    check_unresolved_placeholders(root, report)
    check_gitignore(root, report)
    check_dbt_files(root, report)
    check_mdx(root, report)
    check_mapping(root, report)
    check_design_doc(root, report)
    check_static_docs_builder(root, report)
    check_github_actions(root, report)
    return report


def print_report(report: Report) -> None:
    print("Output package validation")
    print("=========================")

    if report.errors:
        print("\nErrors:")
        for item in report.errors:
            print(f"- {item}")

    if report.warnings:
        print("\nWarnings:")
        for item in report.warnings:
            print(f"- {item}")

    if report.info:
        print("\nInfo:")
        for item in report.info:
            print(f"- {item}")

    if not report.errors and not report.warnings:
        print("\nNo issues found.")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Validate a generated DBT pipeline output package."
    )
    parser.add_argument("package_path", help="Path to the generated output package")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as failures",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON",
    )
    args = parser.parse_args(argv)

    root = Path(args.package_path).resolve()
    report = validate(root)

    if args.json:
        print(json.dumps(report.as_dict(), indent=2))
    else:
        print_report(report)

    if report.errors:
        return 1
    if args.strict and report.warnings:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
