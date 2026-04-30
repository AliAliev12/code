#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output"
DEFAULT_SITE_DIR = ROOT / "sites" / "cazilla-clone-be-fr"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, s: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(s, encoding="utf-8")


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def run_cmd(argv: List[str], env: Optional[Dict[str, str]] = None) -> int:
    p = subprocess.run(argv, cwd=str(ROOT), env=env if env is not None else os.environ.copy())
    return int(p.returncode or 0)


def resolve_site_dir(site_dir_arg: str) -> Path:
    site_dir = Path(site_dir_arg)
    if not site_dir.is_absolute():
        site_dir = ROOT / site_dir
    return site_dir.resolve()


def resolve_output_dir(site_dir: Path, output_dir_arg: Optional[str]) -> Path:
    if output_dir_arg:
        candidate = Path(output_dir_arg)
        if not candidate.is_absolute():
            candidate = ROOT / candidate
        return candidate.resolve()
    if site_dir.resolve() == DEFAULT_SITE_DIR.resolve():
        return OUTPUT_DIR.resolve()
    return (site_dir / "_output").resolve()


def maybe_init_site(site_dir: Path, init_from_arg: Optional[str]) -> None:
    if site_dir.exists():
        return
    if not init_from_arg:
        raise SystemExit(f"Site dir not found: {site_dir}. Pass --init-from to bootstrap a new site.")
    src = resolve_site_dir(init_from_arg)
    if not src.exists():
        raise SystemExit(f"--init-from directory not found: {src}")
    shutil.copytree(src, site_dir)
    print(f"Initialized site directory: {site_dir} (from {src})")


def build_env_context(site_dir: Path, output_dir: Path) -> Dict[str, str]:
    env = os.environ.copy()
    env["SITE_DIR"] = str(site_dir)
    env["SITE_OUTPUT_DIR"] = str(output_dir)
    env["QA_HTML_PATH"] = str(site_dir / "index.html")
    env["QA_KEYWORDS_PATH"] = str(output_dir / "keywords.json")
    env["QA_REPORT_PATH"] = str(output_dir / "qa_report.json")
    return env


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
    ap.add_argument("--output-dir", default="", help="Output directory for site artifacts.")
    ap.add_argument("--init-from", default="", help="Template site dir to copy when --site-dir does not exist.")
    ap.add_argument("--max-iterations", type=int, default=3)
    ap.add_argument("--run-a1", action="store_true", help="Run A1 keywords before QA loop.")
    ap.add_argument("--run-a2", action="store_true", help="Run A2 content before QA loop.")
    ap.add_argument("--run-a3", action="store_true", help="Run A3 humanizer before QA loop.")
    args = ap.parse_args()

    site_dir = resolve_site_dir(args.site_dir)
    maybe_init_site(site_dir, args.init_from or None)
    if not site_dir.exists():
        raise SystemExit(f"Site dir not found: {site_dir}")
    output_dir = resolve_output_dir(site_dir, args.output_dir or None)

    output_dir.mkdir(parents=True, exist_ok=True)
    env_ctx = build_env_context(site_dir, output_dir)

    history: List[Dict[str, Any]] = []
    for it in range(1, max(1, args.max_iterations) + 1):
        print(f"\n=== ORCHESTRATOR iteration {it}/{args.max_iterations} ===")

        content_stage: Dict[str, Any] = {}
        if args.run_a1:
            rc_a1 = run_cmd([sys.executable, str(ROOT / "agents" / "a1-keywords" / "agents" / "a1-keywords" / "run.py"), "--output-dir", str(output_dir)], env=env_ctx)
            content_stage["a1"] = {"run": True, "rc": rc_a1}
            if rc_a1 != 0:
                raise SystemExit(f"A1 failed (exit {rc_a1})")
        else:
            content_stage["a1"] = {"run": False, "rc": None}

        if args.run_a2:
            rc_a2 = run_cmd(
                [
                    sys.executable,
                    str(ROOT / "agents" / "a2-content" / "agents" / "a2-content" / "run.py"),
                    "--site-dir",
                    str(site_dir),
                    "--output-dir",
                    str(output_dir),
                ],
                env=env_ctx,
            )
            content_stage["a2"] = {"run": True, "rc": rc_a2}
            if rc_a2 != 0:
                raise SystemExit(f"A2 failed (exit {rc_a2})")
        else:
            content_stage["a2"] = {"run": False, "rc": None}

        if args.run_a3:
            rc_a3 = run_cmd(
                [
                    sys.executable,
                    str(ROOT / "agents" / "a3-ai-check" / "agents" / "a3-ai-check" / "run.py"),
                    "--site-dir",
                    str(site_dir),
                    "--output-dir",
                    str(output_dir),
                ],
                env=env_ctx,
            )
            content_stage["a3"] = {"run": True, "rc": rc_a3}
            if rc_a3 != 0:
                raise SystemExit(f"A3 failed (exit {rc_a3})")
        else:
            content_stage["a3"] = {"run": False, "rc": None}

        fixes = autofix_site(site_dir)
        if fixes:
            print("Applied autofixes:", ", ".join([f.id for f in fixes]))
            write_json(output_dir / "autofix_log.json", {"iteration": it, "fixes": [f.__dict__ for f in fixes]})

        # Run smoke QA
        rc_smoke = run_cmd([sys.executable, str(ROOT / "agents" / "a11-smoke" / "run.py"), "--site-dir", str(site_dir), "--output-dir", str(output_dir)], env=env_ctx)
        if rc_smoke != 0:
            raise SystemExit(f"Smoke QA failed to run (exit {rc_smoke}).")

        # Run SEO QA (existing a6-design-qa)
        # SEO QA returns 0 on PASS, 2 on FAIL/WARN. We still want a report, so don't abort here.
        _ = run_cmd([sys.executable, str(ROOT / "agents" / "a6-design-qa" / "run.py")], env=env_ctx)

        # Chief QA decision
        _ = run_cmd([sys.executable, str(ROOT / "agents" / "a12-chief-qa" / "run.py"), "--output-dir", str(output_dir)], env=env_ctx)

        qa_seo = load_json_if_exists(output_dir / "qa_report.json")
        qa_smoke = load_json_if_exists(output_dir / "qa_smoke.json")
        chief = load_json_if_exists(output_dir / "qa_chief.json")

        history.append({"iteration": it, "content_stage": content_stage, "chief": chief, "seo": qa_seo, "smoke": qa_smoke})

        decision = str(chief.get("decision", "")).upper()
        if decision == "PASS" and not qa_has_p0_fail(qa_smoke) and not qa_has_p0_fail(qa_seo):
            print("PASS: QA gates satisfied.")
            write_json(output_dir / "orchestrator_history.json", {"site_dir": str(site_dir), "output_dir": str(output_dir), "history": history})
            return 0

        print("FAIL: issues remain; continuing loop.")

    write_json(output_dir / "orchestrator_history.json", {"site_dir": str(site_dir), "output_dir": str(output_dir), "history": history})
    print("\nFAIL: max iterations reached.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
