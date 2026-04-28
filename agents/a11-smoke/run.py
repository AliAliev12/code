#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


ROOT = Path(__file__).resolve().parents[2]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def strip_tags(html: str) -> str:
    html = re.sub(r"(?is)<(script|style)\b[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?is)<!--.*?-->", " ", html)
    html = re.sub(r"(?is)<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", html).strip()


def find_all(pattern: str, s: str, flags: int = 0) -> List[re.Match[str]]:
    return list(re.finditer(pattern, s, flags))


def extract_ids(html: str) -> Set[str]:
    return {m.group(1) for m in find_all(r'(?is)\bid=["\']([^"\']+)["\']', html)}


def extract_hrefs(html: str) -> List[str]:
    out: List[str] = []
    for m in find_all(r'(?is)<a\b[^>]*\bhref=["\']([^"\']+)["\']', html):
        out.append(m.group(1).strip())
    return out


def get_meta_content(html: str, prop: str) -> Optional[str]:
    m = re.search(rf'(?is)<meta\b[^>]*\bproperty=["\']{re.escape(prop)}["\'][^>]*>', html)
    if not m:
        return None
    tag = m.group(0)
    m2 = re.search(r'(?is)\bcontent=["\'](.*?)["\']', tag)
    return m2.group(1).strip() if m2 else None


@dataclass
class Issue:
    id: str
    severity: str  # P0 | P1 | P2
    file: str
    message: str
    hint: str = ""


def main() -> int:
    ap = argparse.ArgumentParser(description="Static site smoke QA (links/anchors/meta/assets).")
    ap.add_argument("--site-dir", default=str(ROOT / "sites" / "cazilla-clone-be-fr"))
    args = ap.parse_args()

    site_dir = Path(args.site_dir).resolve()
    if not site_dir.exists():
        raise SystemExit(f"site dir not found: {site_dir}")

    html_files = sorted(site_dir.rglob("index.html"))
    if not html_files:
        raise SystemExit("No index.html files found under site dir.")

    issues: List[Issue] = []

    # sitemap + robots existence
    robots = site_dir / "robots.txt"
    sitemap = site_dir / "sitemap.xml"
    if not robots.exists():
        issues.append(Issue("robots.missing", "P0", str(robots.relative_to(ROOT)), "robots.txt missing", "Add robots.txt"))
    if not sitemap.exists():
        issues.append(Issue("sitemap.missing", "P0", str(sitemap.relative_to(ROOT)), "sitemap.xml missing", "Add sitemap.xml"))

    for f in html_files:
        rel = str(f.relative_to(ROOT))
        html = read_text(f)
        ids = extract_ids(html)
        hrefs = extract_hrefs(html)

        # Anchors resolve
        for href in hrefs:
            if href.startswith("#") and len(href) > 1:
                anchor = href[1:]
                if anchor not in ids:
                    issues.append(
                        Issue(
                            "anchor.missing",
                            "P1",
                            rel,
                            f'Anchor target "#{anchor}" not found on page',
                            "Add missing id=... or fix the link href",
                        )
                    )

        # Root-relative internal links should be okay on web, but ensure they aren't malformed
        for href in hrefs:
            if href.startswith("javascript:"):
                issues.append(Issue("link.javascript", "P2", rel, "javascript: link found", "Avoid javascript: in href"))

        # Outbound Cazilla link policy
        if "cazilla.casino/register" in html:
            issues.append(
                Issue(
                    "policy.cazilla_register",
                    "P0",
                    rel,
                    "Found https://cazilla.casino/register but policy requires linking only to homepage.",
                    "Replace with https://cazilla.casino/",
                )
            )

        # OG image should be present
        og_image = get_meta_content(html, "og:image") or ""
        if not og_image:
            issues.append(Issue("og.image.missing", "P1", rel, "Missing og:image", "Add og:image"))
        else:
            # If points to our site assets, check the file exists in local tree
            m = re.search(r"https?://[^/]+/(.+)$", og_image)
            if m:
                path_part = m.group(1)
                # ignore querystrings
                path_part = path_part.split("?", 1)[0]
                candidate = site_dir / path_part
                if og_image.startswith("https://cazilareview.xyz/") and not candidate.exists():
                    issues.append(
                        Issue(
                            "og.image.asset_missing",
                            "P0",
                            rel,
                            f"og:image points to missing asset: {og_image}",
                            f"Add file at {candidate} or change og:image",
                        )
                    )

    # Summarize
    sev_rank = {"P0": 0, "P1": 1, "P2": 2}
    issues.sort(key=lambda x: (sev_rank.get(x.severity, 9), x.id, x.file))
    status = "PASS" if not any(i.severity == "P0" for i in issues) else "FAIL"

    report: Dict[str, Any] = {
        "status": status,
        "issues": [i.__dict__ for i in issues],
        "counts": {
            "P0": sum(1 for i in issues if i.severity == "P0"),
            "P1": sum(1 for i in issues if i.severity == "P1"),
            "P2": sum(1 for i in issues if i.severity == "P2"),
            "total": len(issues),
        },
        "site_dir": str(site_dir),
    }

    out_path = ROOT / "output" / "qa_smoke.json"
    write_json(out_path, report)
    print(f"Smoke QA: {status} (P0={report['counts']['P0']}, P1={report['counts']['P1']}, P2={report['counts']['P2']})")
    print(f"Report saved to: {out_path}")

    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
