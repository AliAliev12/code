#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output"
CFG_PATH = ROOT / "agents" / "chief_qa.config.json"


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists() or path.stat().st_size < 2:
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def load_config() -> Dict[str, Any]:
    cfg = load_json(CFG_PATH)
    if not cfg:
        cfg = {}
    # Defaults
    cfg.setdefault("publishable", {})
    cfg["publishable"].setdefault("max_p1", 5)
    cfg.setdefault("downgrade_to_p2", [])
    cfg.setdefault("severity_overrides", {})
    return cfg


@dataclass
class Finding:
    id: str
    severity: str  # P0 | P1 | P2
    source: str  # smoke | seo | content | design
    message: str
    file: str = ""
    hint: str = ""


def extract_findings() -> List[Finding]:
    cfg = load_config()
    downgrade_to_p2 = set([str(x) for x in (cfg.get("downgrade_to_p2") or [])])
    severity_overrides = cfg.get("severity_overrides") if isinstance(cfg.get("severity_overrides"), dict) else {}

    findings: List[Finding] = []

    smoke = load_json(OUT / "qa_smoke.json")
    for i in smoke.get("issues", []) or []:
        if not isinstance(i, dict):
            continue
        findings.append(
            Finding(
                id=str(i.get("id", "smoke.issue")),
                severity=str(i.get("severity", "P2")),
                source="smoke",
                message=str(i.get("message", "")),
                file=str(i.get("file", "")),
                hint=str(i.get("hint", "")),
            )
        )

    seo = load_json(OUT / "qa_report.json")
    for c in seo.get("results", []) or []:
        if not isinstance(c, dict):
            continue
        st = str(c.get("status", "")).upper()
        if st not in ("FAIL", "WARN"):
            continue
        # Map FAIL->P0, WARN->P1 by default
        sev = "P0" if st == "FAIL" else "P1"
        check_id = str(c.get("id", "seo.check"))

        # Config overrides
        if check_id in severity_overrides:
            sev = str(severity_overrides.get(check_id) or sev)
        if check_id in downgrade_to_p2 and sev == "P1":
            sev = "P2"

        findings.append(
            Finding(
                id=check_id,
                severity=sev,
                source="seo",
                message=str(c.get("message", "")),
                file=str(c.get("details", {}).get("file", "")) if isinstance(c.get("details"), dict) else "",
                hint="See output/qa_report.json details.",
            )
        )

    return findings


def main() -> int:
    cfg = load_config()
    max_p1 = int((cfg.get("publishable") or {}).get("max_p1") or 5)

    findings = extract_findings()
    sev_rank = {"P0": 0, "P1": 1, "P2": 2}
    findings.sort(key=lambda f: (sev_rank.get(f.severity, 9), f.source, f.id))

    p0 = [f for f in findings if f.severity == "P0"]
    p1 = [f for f in findings if f.severity == "P1"]
    p2 = [f for f in findings if f.severity == "P2"]

    # Decision policy:
    # - Any P0 => FAIL
    # - P1 => PASS (non-blocking), but reported for optional polish
    decision = "FAIL" if p0 else "PASS"
    publishable = decision == "PASS" and len(p1) <= max_p1

    report: Dict[str, Any] = {
        "decision": decision,
        "publishable": publishable,
        "counts": {"P0": len(p0), "P1": len(p1), "P2": len(p2), "total": len(findings)},
        "findings": [f.__dict__ for f in findings],
        "weights": {"seo": 0.5, "content": 0.3, "design": 0.2},  # reserved for future
        "config": {"path": str(CFG_PATH), "publishable_max_p1": max_p1},
        "notes": "Gates: P0 blocks publish. P1 is non-blocking; publishable threshold is configurable. Some WARNs may be downgraded to P2 via config.",
    }

    out_path = OUT / "qa_chief.json"
    write_json(out_path, report)
    print(f"Chief QA: {decision} (P0={len(p0)}, P1={len(p1)}, P2={len(p2)})")
    print(f"Report saved to: {out_path}")
    return 0 if decision == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
