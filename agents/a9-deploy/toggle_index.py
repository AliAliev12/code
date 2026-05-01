#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SITE_ORIGIN_DEFAULT = "https://cazilla.live"

def resolve_site_dir(site_dir_arg: str | None) -> Path:
    default = ROOT / "sites" / "cazilla-clone-be-fr"
    raw = site_dir_arg or ""
    p = Path(raw) if raw else default
    if not p.is_absolute():
        p = ROOT / p
    return p.resolve()


def site_origin_from_env() -> str:
    origin = (
        os.getenv("SITE_ORIGIN", "").strip()
        or os.getenv("SITE_URL", "").strip()
        or SITE_ORIGIN_DEFAULT
    )
    return origin.rstrip("/")


def section_dirs(site_dir: Path) -> list[Path]:
    return sorted([p for p in site_dir.iterdir() if p.is_dir() and p.name != "_output" and (p / "index.html").exists()])


def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def write_text(p: Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")


def iter_html_pages(site_dir: Path) -> list[Path]:
    pages: list[Path] = []
    pages.append(site_dir / "index.html")
    pages.extend(sorted([p for p in site_dir.glob("*/index.html") if p.is_file()]))
    return pages


def verify_expected_pages(site_dir: Path) -> None:
    expected = [site_dir / "index.html"]
    expected.extend([p / "index.html" for p in section_dirs(site_dir)])
    missing = [str(p) for p in expected if not p.exists()]
    if missing:
        msg = ["Build verification failed. Missing required page files:"]
        msg.extend([f"- {p}" for p in missing])
        raise SystemExit("\n".join(msg))
    if len(expected) < 4:
        raise SystemExit(f"Build verification failed. Expected at least 4 pages (root + 3 sections), found {len(expected)}.")


def toggle_index_html(site_dir: Path, mode: str) -> None:
    want = 'content="noindex, nofollow"' if mode == "close" else 'content="index, follow"'

    # allow replacing multiple formatting variants
    candidates = [
        'content="index, follow"',
        'content="index,follow"',
        'content="noindex, nofollow"',
        'content="noindex,nofollow"',
    ]

    for html_path in iter_html_pages(site_dir):
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


def rewrite_internal_links(site_dir: Path, link_mode: str) -> None:
    if link_mode == "production":
        return

    # In local mode, avoid root-relative links which break under file://
    # Use relative, trailing-slash directory links as requested.
    for html_path in iter_html_pages(site_dir):
        is_root = html_path.parent == site_dir
        base = "./" if is_root else "../"

        replacements = {'href="/"': f'href="{base}"'}
        for d in section_dirs(site_dir):
            replacements[f'href="/{d.name}/"'] = f'href="{base}{d.name}/"'

        html = read_text(html_path)
        html2 = html
        for old, new in replacements.items():
            html2 = html2.replace(old, new)
        if html2 != html:
            write_text(html_path, html2)


def toggle_robots(site_dir: Path, mode: str) -> None:
    # Per requirements: always ship production-friendly robots.txt (Allow:/ + Sitemap)
    # Predeploy noindex is controlled via meta robots in HTML pages.
    site_origin = site_origin_from_env()
    open_robots = "\n".join(["User-agent: *", "Allow: /", f"Sitemap: {site_origin}/sitemap.xml", ""])
    write_text(site_dir / "robots.txt", open_robots)


def write_sitemap(site_dir: Path) -> None:
    site_origin = site_origin_from_env()
    hreflang_primary = os.getenv("QA_HREFLANG_PRIMARY", "").strip() or ("fr-BE" if "cazilla-clone-be-fr" in str(site_dir) else "en-IE")
    urls = [f"{site_origin}/"]
    urls.extend([f"{site_origin}/{d.name}/" for d in section_dirs(site_dir)])

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
                f'    <xhtml:link rel="alternate" hreflang="{hreflang_primary}" href="{u}"/>',
                f'    <xhtml:link rel="alternate" hreflang="x-default" href="{u}"/>',
                f"    <lastmod>{today}</lastmod>",
                "    <changefreq>weekly</changefreq>",
                f"    <priority>{priority}</priority>",
                "  </url>",
            ]
        )
    parts.append("</urlset>\n")
    write_text(site_dir / "sitemap.xml", "\n".join(parts))


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
    ap.add_argument("--site-dir", default="")
    args = ap.parse_args()

    mode = args.mode or mode_from_env() or "open"
    link_mode = link_mode_from_env()
    site_dir = resolve_site_dir(args.site_dir or os.getenv("SITE_DIR", ""))

    verify_expected_pages(site_dir)
    toggle_index_html(site_dir, mode)
    rewrite_internal_links(site_dir, link_mode)
    toggle_robots(site_dir, mode)
    write_sitemap(site_dir)

    if mode == "close":
        print("🔒 Site closed for indexing")
    else:
        print("🌐 Site opened for indexing")
    if link_mode == "local":
        print("🔗 LINK_MODE=local (relative internal links)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

