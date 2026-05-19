#!/usr/bin/env python3
"""Replace hardcoded preview host and operator URL in site HTML from repo .env."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV = ROOT / ".env"
SITES = ROOT / "sites"

# Legacy operator hosts replaced by MAIN_CASINO_URL from .env
LEGACY_CASINO_HOSTS = (
    "https://cazilla.online",
    "https://cazilla.online/",
)

# Legacy preview hosts replaced by SITE_URL from .env
LEGACY_SITE_URLS = (
    "https://cazilla-offerwall2-en-ie.invalid",
    "https://cazilla-response-en-ie.invalid",
    "https://cazilla.tmp.invalid",
    "https://cazilla.invalid.tmp.domain",
    "https://cazilla.eu",
    "https://cazilla.eu/",
)


def load_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def apply_casino_urls(text: str, casino: str) -> str:
    for old in LEGACY_CASINO_HOSTS:
        text = text.replace(old, casino)
    # Normalize trailing slash variants of the target URL
    if casino.endswith("/"):
        bare = casino.rstrip("/")
        text = text.replace(bare, casino)
    return text


def main() -> int:
    env = load_env(ENV)
    site_url = (env.get("SITE_URL") or "").strip().rstrip("/")
    casino = (env.get("MAIN_CASINO_URL") or "").strip().rstrip("/")
    if not casino:
        print("Missing MAIN_CASINO_URL in .env", file=sys.stderr)
        return 1

    site_dirs: list[Path]
    rel = (env.get("SITE_DIR") or "").strip().lstrip("/")
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        site_dirs = sorted(p for p in SITES.iterdir() if p.is_dir() and not p.name.endswith(".zip"))
    elif rel:
        site_dirs = [ROOT / rel]
    else:
        site_dirs = sorted(p for p in SITES.iterdir() if p.is_dir() and not p.name.endswith(".zip"))

    updated = 0
    for site_dir in site_dirs:
        if not site_dir.is_dir():
            print(f"Skip missing: {site_dir}", file=sys.stderr)
            continue
        for fp in sorted(site_dir.rglob("*.html")):
            s = fp.read_text(encoding="utf-8", errors="replace")
            orig = s
            if site_url:
                for old in LEGACY_SITE_URLS:
                    if old.rstrip("/") == site_url.rstrip("/"):
                        continue
                    s = s.replace(old, site_url)
                    bare = old.rstrip("/")
                    if bare != old:
                        s = s.replace(bare, site_url.rstrip("/"))
            s = apply_casino_urls(s, casino)
            if s != orig:
                fp.write_text(s, encoding="utf-8")
                print("Updated URLs:", fp.relative_to(ROOT))
                updated += 1

    if updated == 0:
        print("No HTML files needed URL updates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
