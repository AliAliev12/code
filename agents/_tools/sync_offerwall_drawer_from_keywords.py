#!/usr/bin/env python3
"""
Rewrite offerwall site drawer <nav class="ow-drawerNav"> from _output/keywords.json:
  - pages[].path + pages[].menu_label
  - technical_pages[].path + menu_label (or title-cased id)

Usage:
  python3 agents/_tools/sync_offerwall_drawer_from_keywords.py --site-dir sites/cazilla-offerwall1-en-ie
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _nice_label_from_id(page_id: str) -> str:
    return page_id.replace("-", " ").strip().title()


def _collect_menu_items(data: dict) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for page in data.get("pages") or []:
        if not isinstance(page, dict):
            continue
        rel = str(page.get("path") or "").strip().lstrip("/")
        if not rel:
            continue
        label = str(page.get("menu_label") or "").strip() or _nice_label_from_id(str(page.get("id") or "page"))
        out.append((rel, label))
    for page in data.get("technical_pages") or []:
        if not isinstance(page, dict):
            continue
        rel = str(page.get("path") or "").strip().lstrip("/")
        if not rel:
            continue
        label = str(page.get("menu_label") or "").strip() or _nice_label_from_id(str(page.get("id") or "page"))
        out.append((rel, label))
    return out


def _rel_href(*, from_rel: str, to_rel: str) -> str:
    base = os.path.dirname(from_rel)
    if not base:
        base = "."
    r = os.path.relpath(to_rel, base).replace("\\", "/")
    if r == ".":
        return Path(to_rel).name
    return r


def _drawer_nav_inner(*, from_rel: str, items: list[tuple[str, str]], current_rel: str) -> str:
    lines: list[str] = []
    cur_norm = Path(current_rel).as_posix()
    for to_rel, label in items:
        href = _rel_href(from_rel=from_rel, to_rel=to_rel)
        is_here = Path(to_rel).as_posix() == cur_norm
        cls = "ow-navAnchor" + (" is-current" if is_here else "")
        cur_attr = ' aria-current="page"' if is_here else ""
        lines.append(f'          <a class="{cls}" href="{href}"{cur_attr}>{label}</a>')
    return "\n".join(lines)


_NAV_RE = re.compile(
    r'(<nav\s+class="ow-drawerNav"[^>]*>)([\s\S]*?)(</nav>)',
    re.IGNORECASE,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site-dir", type=Path, required=True)
    args = ap.parse_args()
    site_dir = (ROOT / args.site_dir).resolve() if not args.site_dir.is_absolute() else args.site_dir
    kw_path = site_dir / "_output" / "keywords.json"
    if not kw_path.is_file():
        print(f"Missing {kw_path}", file=sys.stderr)
        return 1

    data = json.loads(kw_path.read_text(encoding="utf-8"))
    items = _collect_menu_items(data)
    if not items:
        print("No pages in keywords.json", file=sys.stderr)
        return 1

    html_files = sorted(site_dir.rglob("*.html"))
    for fp in html_files:
        rel_site = str(fp.relative_to(site_dir)).replace("\\", "/")
        text = fp.read_text(encoding="utf-8", errors="replace")
        m = _NAV_RE.search(text)
        if not m:
            continue
        inner = _drawer_nav_inner(from_rel=rel_site, items=items, current_rel=rel_site)
        new_nav = m.group(1) + "\n" + inner + "\n        " + m.group(3)
        new_text = text[: m.start()] + new_nav + text[m.end() :]
        new_text = new_text.replace('aria-label="Approved interlink anchors"', 'aria-label="Site pages"')
        if new_text != text:
            fp.write_text(new_text, encoding="utf-8")
            print("Drawer:", fp.relative_to(ROOT))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
