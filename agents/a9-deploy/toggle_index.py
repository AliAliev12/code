#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SITE_DIR = ROOT / "sites" / "cazilla-clone-be-fr"
INDEX_HTML = SITE_DIR / "index.html"
ROBOTS_TXT = ROOT / "sites" / "cazilla-clone-be-fr" / "robots.txt"
SITEMAP_XML = ROOT / "sites" / "cazilla-clone-be-fr" / "sitemap.xml"


SITE_ORIGIN = "https://cazilareview.xyz"

OPEN_ROBOTS = "\n".join(["User-agent: *", "Allow: /", f"Sitemap: {SITE_ORIGIN}/sitemap.xml", ""])

EXPECTED_PAGES = [
    SITE_DIR / "index.html",
    SITE_DIR / "bonus-casino-belgique" / "index.html",
    SITE_DIR / "casino-en-ligne-belgique-legal" / "index.html",
    SITE_DIR / "meilleurs-jeux-casino-belgique" / "index.html",
]


def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def write_text(p: Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")


def iter_html_pages() -> list[Path]:
    pages: list[Path] = []
    pages.append(SITE_DIR / "index.html")
    pages.extend(sorted([p for p in SITE_DIR.glob("*/index.html") if p.is_file()]))
    return pages


def verify_expected_pages() -> None:
    missing = [str(p) for p in EXPECTED_PAGES if not p.exists()]
    if missing:
        msg = ["Build verification failed. Missing required page files:"]
        msg.extend([f"- {p}" for p in missing])
        raise SystemExit("\n".join(msg))


def toggle_index_html(mode: str) -> None:
    want = 'content="noindex, nofollow"' if mode == "close" else 'content="index, follow"'

    # allow replacing multiple formatting variants
    candidates = [
        'content="index, follow"',
        'content="index,follow"',
        'content="noindex, nofollow"',
        'content="noindex,nofollow"',
    ]

    for html_path in iter_html_pages():
        html = read_text(html_path)
        html2 = html
        for c in candidates:
            if c != want:
                html2 = html2.replace(c, want)
        if html2 != html:
            write_text(html_path, html2)


def link_mode_from_env() -> str:
    v = os.getenv("LINK_MODE", "").strip().lower()
    if v in {"local", "production", "prod"}:
        return "local" if v == "local" else "production"
    return "production"


def rewrite_internal_links(link_mode: str) -> None:
    if link_mode == "production":
        return

    # In local mode, avoid root-relative links which break under file://
    # Use relative, trailing-slash directory links as requested.
    for html_path in iter_html_pages():
        is_root = html_path.parent == SITE_DIR
        base = "./" if is_root else "../"

        replacements = {
            'href="/bonus-casino-belgique/"': f'href="{base}bonus-casino-belgique/"',
            'href="/casino-en-ligne-belgique-legal/"': f'href="{base}casino-en-ligne-belgique-legal/"',
            'href="/meilleurs-jeux-casino-belgique/"': f'href="{base}meilleurs-jeux-casino-belgique/"',
            'href="/"': f'href="{base}"',
        }

        html = read_text(html_path)
        html2 = html
        for old, new in replacements.items():
            html2 = html2.replace(old, new)
        if html2 != html:
            write_text(html_path, html2)


def toggle_robots(mode: str) -> None:
    # Per requirements: always ship production-friendly robots.txt (Allow:/ + Sitemap)
    # Predeploy noindex is controlled via meta robots in HTML pages.
    write_text(ROBOTS_TXT, OPEN_ROBOTS)


def write_sitemap() -> None:
    urls = [
        f"{SITE_ORIGIN}/",
        f"{SITE_ORIGIN}/bonus-casino-belgique/",
        f"{SITE_ORIGIN}/casino-en-ligne-belgique-legal/",
        f"{SITE_ORIGIN}/meilleurs-jeux-casino-belgique/",
    ]

    today = "2026-04-23"
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
        '        xmlns:xhtml="http://www.w3.org/1999/xhtml">',
    ]
    for i, u in enumerate(urls):
        priority = "1.0" if i == 0 else ("0.8" if i == 1 else "0.7")
        parts.extend(
            [
                "  <url>",
                f"    <loc>{u}</loc>",
                f'    <xhtml:link rel="alternate" hreflang="fr-BE" href="{u}"/>',
                f'    <xhtml:link rel="alternate" hreflang="x-default" href="{u}"/>',
                f"    <lastmod>{today}</lastmod>",
                "    <changefreq>weekly</changefreq>",
                f"    <priority>{priority}</priority>",
                "  </url>",
            ]
        )
    parts.append("</urlset>\n")
    write_text(SITEMAP_XML, "\n".join(parts))


def mode_from_env() -> str | None:
    v = os.getenv("PREDEPLOY_NOINDEX", "").strip().lower()
    if v in {"1", "true", "yes", "on"}:
        return "close"
    if v in {"0", "false", "no", "off"}:
        return "open"
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["open", "close"], required=False)
    args = ap.parse_args()

    mode = args.mode or mode_from_env() or "open"
    link_mode = link_mode_from_env()

    verify_expected_pages()
    toggle_index_html(mode)
    rewrite_internal_links(link_mode)
    toggle_robots(mode)
    write_sitemap()

    if mode == "close":
        print("🔒 Site closed for indexing")
    else:
        print("🌐 Site opened for indexing")
    if link_mode == "local":
        print("🔗 LINK_MODE=local (relative internal links)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

