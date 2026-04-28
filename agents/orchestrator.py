#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, s: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(s, encoding="utf-8")


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def run_cmd(argv: List[str]) -> int:
    p = subprocess.run(argv, cwd=str(ROOT))
    return int(p.returncode or 0)


@dataclass
class AutoFix:
    id: str
    changed_files: List[str]


def autofix_site(site_dir: Path) -> List[AutoFix]:
    """
    Minimal, deterministic autofixes (no model calls):
    - normalize cazilla outbound links to https://cazilla.casino/
    - normalize OG image to an existing asset
    """
    html_files = sorted(site_dir.rglob("index.html"))
    fixes: List[AutoFix] = []

    # Fix 1: /register -> /
    changed: List[str] = []
    for f in html_files:
        s = read_text(f)
        if "https://cazilla.casino/register" not in s:
            continue
        s2 = s.replace("https://cazilla.casino/register", "https://cazilla.casino/")
        if s2 != s:
            write_text(f, s2)
            changed.append(str(f.relative_to(ROOT)))
    if changed:
        fixes.append(AutoFix(id="autofix.cazilla_register_to_root", changed_files=changed))

    # Fix 2: OG image fallback to an existing asset shipped with the repo.
    og_bad = 'content="https://cazilareview.xyz/images/og-image.jpg"'
    og_good = 'content="https://cazilareview.xyz/assets/bass.svg"'
    changed = []
    for f in html_files:
        s = read_text(f)
        if og_bad not in s:
            continue
        s2 = s.replace(og_bad, og_good)
        if s2 != s:
            write_text(f, s2)
            changed.append(str(f.relative_to(ROOT)))
    if changed:
        fixes.append(AutoFix(id="autofix.og_image_to_existing_asset", changed_files=changed))

    return fixes


def load_json_if_exists(path: Path) -> Dict[str, Any]:
    if not path.exists() or path.stat().st_size < 2:
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def qa_has_p0_fail(qa_report: Dict[str, Any]) -> bool:
    # a6-design-qa format: { "status": "PASS|FAIL", "checks": [...] }
    status = str(qa_report.get("status", "")).upper()
    if status == "FAIL":
        return True
    checks = qa_report.get("checks")
    if isinstance(checks, list):
        return any(str(c.get("status", "")).upper() == "FAIL" for c in checks if isinstance(c, dict))
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description="SEO site factory orchestrator (QA → fix → QA).")
    ap.add_argument("--site-dir", default="sites/cazilla-clone-be-fr", help="Site directory (static output).")
    ap.add_argument("--max-iterations", type=int, default=3)
    args = ap.parse_args()

    site_dir = (ROOT / args.site_dir).resolve()
    if not site_dir.exists():
        raise SystemExit(f"Site dir not found: {site_dir}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    history: List[Dict[str, Any]] = []
    for it in range(1, max(1, args.max_iterations) + 1):
        print(f"\n=== ORCHESTRATOR iteration {it}/{args.max_iterations} ===")

        fixes = autofix_site(site_dir)
        if fixes:
            print("Applied autofixes:", ", ".join([f.id for f in fixes]))
            write_json(OUTPUT_DIR / "autofix_log.json", {"iteration": it, "fixes": [f.__dict__ for f in fixes]})

        # Run smoke QA
        rc_smoke = run_cmd([sys.executable, str(ROOT / "agents" / "a11-smoke" / "run.py"), "--site-dir", str(site_dir)])
        if rc_smoke != 0:
            raise SystemExit(f"Smoke QA failed to run (exit {rc_smoke}).")

        # Run SEO QA (existing a6-design-qa)
        # SEO QA returns 0 on PASS, 2 on FAIL/WARN. We still want a report, so don't abort here.
        _ = run_cmd([sys.executable, str(ROOT / "agents" / "a6-design-qa" / "run.py")])

        # Chief QA decision
        _ = run_cmd([sys.executable, str(ROOT / "agents" / "a12-chief-qa" / "run.py")])

        qa_seo = load_json_if_exists(OUTPUT_DIR / "qa_report.json")
        qa_smoke = load_json_if_exists(OUTPUT_DIR / "qa_smoke.json")
        chief = load_json_if_exists(OUTPUT_DIR / "qa_chief.json")

        history.append({"iteration": it, "chief": chief, "seo": qa_seo, "smoke": qa_smoke})

        decision = str(chief.get("decision", "")).upper()
        if decision == "PASS" and not qa_has_p0_fail(qa_smoke) and not qa_has_p0_fail(qa_seo):
            print("PASS: QA gates satisfied.")
            write_json(OUTPUT_DIR / "orchestrator_history.json", {"history": history})
            return 0

        print("FAIL: issues remain; continuing loop.")

    write_json(OUTPUT_DIR / "orchestrator_history.json", {"history": history})
    print("\nFAIL: max iterations reached.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
