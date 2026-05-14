#!/usr/bin/env python3
"""Replace hardcoded preview host and operator URL in site HTML from repo .env."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV = ROOT / ".env"


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


def main() -> int:
    env = load_env(ENV)
    site_url = (env.get("SITE_URL") or "").strip().rstrip("/")
    casino = (env.get("MAIN_CASINO_URL") or "").strip().rstrip("/")
    if not site_url or not casino:
        print("Missing SITE_URL or MAIN_CASINO_URL in .env", file=sys.stderr)
        return 1
    rel = (env.get("SITE_DIR") or "").strip().lstrip("/")
    site_dir = ROOT / rel
    if not site_dir.is_dir():
        print(f"SITE_DIR not a directory: {site_dir}", file=sys.stderr)
        return 1

    files = [site_dir / "index.html", site_dir / "cookie-policy" / "index.html"]
    for fp in files:
        if not fp.exists():
            print(f"Skip missing: {fp}", file=sys.stderr)
            continue
        s = fp.read_text(encoding="utf-8", errors="replace")
        orig = s
        s = s.replace("https://cazilla-offerwall2-en-ie.invalid", site_url)
        s = s.replace("https://cazilla.casino", casino)
        if s != orig:
            fp.write_text(s, encoding="utf-8")
            print("Updated URLs:", fp.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
