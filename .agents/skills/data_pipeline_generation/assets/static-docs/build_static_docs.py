#!/usr/bin/env python3
"""Build a small static HTML site from generated pipeline docs.

This script is intentionally dependency-free so GitHub Pages demos can publish
review documentation without running dbt, installing Node, or exposing profiles.
"""

from __future__ import annotations

import argparse
import html
import os
import re
from pathlib import Path


DOC_PATTERNS = [
    "docs/**/*.mdx",
    "docs/**/*.md",
    "mappings/**/*.md",
    "design/**/*.md",
]
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def title_from_path(path: Path) -> str:
    return path.stem.replace("_", " ").replace("-", " ").title()


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text

    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta, text[match.end():]


def strip_mdx(text: str) -> str:
    text = re.sub(r"^import\s+.*?;\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"</?Tabs[^>]*>", "", text)

    def tab_heading(match: re.Match[str]) -> str:
        attrs = match.group(1)
        label = re.search(r'label=["\']([^"\']+)["\']', attrs)
        value = re.search(r'value=["\']([^"\']+)["\']', attrs)
        heading = label.group(1) if label else value.group(1) if value else "Section"
        return f"\n\n## {heading}\n\n"

    text = re.sub(r"<TabItem([^>]*)>", tab_heading, text)
    text = re.sub(r"</TabItem>", "", text)
    return text


def inline_markdown(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', escaped)
    return escaped


def render_table(lines: list[str]) -> str:
    rows = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        rows.append(cells)
    if not rows:
        return ""

    header = rows[0]
    body = rows[1:]
    out = ["<table>", "<thead><tr>"]
    out.extend(f"<th>{inline_markdown(cell)}</th>" for cell in header)
    out.append("</tr></thead>")
    if body:
        out.append("<tbody>")
        for row in body:
            out.append("<tr>")
            out.extend(f"<td>{inline_markdown(cell)}</td>" for cell in row)
            out.append("</tr>")
        out.append("</tbody>")
    out.append("</table>")
    return "\n".join(out)


def markdown_to_html(markdown: str) -> str:
    _, markdown = split_frontmatter(markdown)
    markdown = strip_mdx(markdown)
    lines = markdown.splitlines()
    out: list[str] = []
    paragraph: list[str] = []
    table: list[str] = []
    in_code = False
    code_lang = ""
    code_lines: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            out.append(f"<p>{inline_markdown(' '.join(paragraph))}</p>")
            paragraph.clear()

    def flush_table() -> None:
        if table:
            out.append(render_table(table))
            table.clear()

    for line in lines:
        if line.startswith("```"):
            if in_code:
                escaped = html.escape("\n".join(code_lines))
                if code_lang == "mermaid":
                    out.append(f'<div class="mermaid">{escaped}</div>')
                else:
                    klass = f' class="language-{html.escape(code_lang)}"' if code_lang else ""
                    out.append(f"<pre><code{klass}>{escaped}</code></pre>")
                in_code = False
                code_lang = ""
                code_lines = []
            else:
                flush_paragraph()
                flush_table()
                in_code = True
                code_lang = line.removeprefix("```").strip().lower()
            continue

        if in_code:
            code_lines.append(line)
            continue

        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            flush_table()
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            flush_paragraph()
            table.append(stripped)
            continue

        flush_table()
        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            flush_paragraph()
            level = len(heading.group(1))
            out.append(f"<h{level}>{inline_markdown(heading.group(2))}</h{level}>")
            continue

        bullet = re.match(r"^[-*]\s+(.+)$", stripped)
        if bullet:
            flush_paragraph()
            out.append(f"<ul><li>{inline_markdown(bullet.group(1))}</li></ul>")
            continue

        paragraph.append(stripped)

    flush_paragraph()
    flush_table()
    return "\n".join(out)


def collect_docs(root: Path) -> list[Path]:
    docs: list[Path] = []
    for pattern in DOC_PATTERNS:
        docs.extend(path for path in root.glob(pattern) if path.is_file())
    return sorted(set(docs))


def html_target_for_doc(root: Path, path: Path) -> Path:
    return path.relative_to(root).with_suffix(".html")


def relative_href(current: Path, target: Path) -> str:
    start = current.parent.as_posix() or "."
    return os.path.relpath(target.as_posix(), start)


def nav_group_name(path: Path, root: Path) -> str:
    group = path.relative_to(root).parts[0]
    return group.replace("_", " ").replace("-", " ").title()


def render_sidebar(items: list[dict[str, str]], current_target: Path) -> str:
    groups: dict[str, list[dict[str, str]]] = {}
    for item in items:
        groups.setdefault(item["group"], []).append(item)

    parts = ['<nav class="sidebar-nav">']
    for group, group_items in groups.items():
        parts.append(f"<h2>{html.escape(group)}</h2>")
        parts.append("<ul>")
        for item in group_items:
            href = relative_href(current_target, Path(item["target"]))
            current = ' class="current"' if item["target"] == current_target.as_posix() else ""
            parts.append(f'<li{current}><a href="{html.escape(href)}">{html.escape(item["title"])}</a></li>')
        parts.append("</ul>")
    parts.append("</nav>")
    return "\n".join(parts)


def page_shell(title: str, sidebar: str, content: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{ color-scheme: light; --ink: #172026; --muted: #5d6b76; --line: #d8dee4; --fill: #f7f9fb; }}
    body {{ margin: 0; font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: var(--ink); line-height: 1.55; }}
    .layout {{ display: grid; grid-template-columns: 280px minmax(0, 1fr); min-height: 100vh; }}
    aside {{ border-right: 1px solid var(--line); background: var(--fill); padding: 24px 20px; }}
    main {{ max-width: 960px; padding: 32px; }}
    h1, h2, h3 {{ line-height: 1.2; }}
    .sidebar-nav h2 {{ font-size: 0.95rem; margin: 20px 0 8px; }}
    .sidebar-nav ul {{ list-style: none; padding: 0; margin: 0; }}
    .sidebar-nav li {{ margin: 0; }}
    .sidebar-nav a {{ display: block; padding: 6px 10px; color: var(--ink); text-decoration: none; border-radius: 6px; }}
    .sidebar-nav .current a {{ background: #e8eef5; font-weight: 600; }}
    .source {{ color: var(--muted); font-size: 0.9rem; }}
    table {{ border-collapse: collapse; display: block; overflow-x: auto; margin: 16px 0; }}
    th, td {{ border: 1px solid var(--line); padding: 8px 10px; vertical-align: top; }}
    th {{ background: var(--fill); text-align: left; }}
    pre {{ overflow-x: auto; padding: 16px; background: #f3f5f7; border: 1px solid var(--line); border-radius: 8px; }}
    .mermaid {{ overflow-x: auto; margin: 16px 0; padding: 16px; background: #fff; border: 1px solid var(--line); border-radius: 8px; }}
    code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 0.92em; }}
    a {{ color: #0b5cab; }}
    @media (max-width: 900px) {{
      .layout {{ grid-template-columns: 1fr; }}
      aside {{ border-right: 0; border-bottom: 1px solid var(--line); }}
    }}
  </style>
</head>
<body>
  <div class="layout">
    <aside>{sidebar}</aside>
    <main>{content}</main>
  </div>
  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
    mermaid.initialize({{
      startOnLoad: false,
      securityLevel: 'strict',
      theme: 'base',
      themeVariables: {{
        primaryColor: '#1f9d8b',
        primaryTextColor: '#10211d',
        primaryBorderColor: '#176f63',
        lineColor: '#244b5a',
        secondaryColor: '#ffd166',
        tertiaryColor: '#f25f5c',
        clusterBkg: '#eef7f5',
        clusterBorder: '#9ccfc5',
        edgeLabelBackground: '#ffffff',
      }},
    }});
    await mermaid.run({{ querySelector: '.mermaid' }});
  </script>
</body>
</html>
"""


def build_site(root: Path, output_dir: Path) -> None:
    docs = collect_docs(root)
    output_dir.mkdir(parents=True, exist_ok=True)

    items: list[dict[str, str]] = []
    for path in docs:
        raw = read_text(path)
        meta, _ = split_frontmatter(raw)
        items.append(
            {
                "source": str(path.relative_to(root)),
                "target": html_target_for_doc(root, path).as_posix(),
                "title": meta.get("sidebar_label") or meta.get("title") or title_from_path(path),
                "group": nav_group_name(path, root),
                "body": markdown_to_html(raw),
            }
        )

    if not items:
        (output_dir / "index.html").write_text(
            page_shell("Pipeline Documentation", "", "<p>No documentation files found.</p>"),
            encoding="utf-8",
        )
        return

    for item in items:
        target = output_dir / Path(item["target"])
        target.parent.mkdir(parents=True, exist_ok=True)
        body = (
            f'<p class="source">{html.escape(item["source"])}</p>'
            f"{item['body']}"
        )
        target.write_text(
            page_shell(item["title"], render_sidebar(items, Path(item["target"])), body),
            encoding="utf-8",
        )

    first_target = Path(items[0]["target"]).as_posix()
    redirect = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="0; url={html.escape(first_target)}">
  <title>Pipeline Documentation</title>
</head>
<body>
  <p><a href="{html.escape(first_target)}">Open documentation</a></p>
</body>
</html>
"""
    (output_dir / "index.html").write_text(redirect, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build static pipeline documentation.")
    parser.add_argument("root", nargs="?", default=".", help="Generated package root")
    parser.add_argument("output", nargs="?", default="site", help="Output directory")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    build_site(root, output)
    print(f"wrote {output / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
