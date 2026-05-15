#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]

_AGENTS_DIR = ROOT / "agents"
if str(_AGENTS_DIR) not in sys.path:
    sys.path.insert(0, str(_AGENTS_DIR))

from _lib.keywords_bundle import parse_keywords_file, resolve_site_html  # noqa: E402
from _lib.repo_env import apply_repo_dotenv  # noqa: E402

_SKIP_HTML_PARTS = {"_output", "assets", "node_modules"}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


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


def _path_has_skipped_part(path: Path, site_dir: Path) -> bool:
    try:
        rel = path.relative_to(site_dir)
    except ValueError:
        return True
    return any(part in _SKIP_HTML_PARTS for part in rel.parts)


def collect_html_files(site_dir: Path) -> List[Path]:
    """All auditable HTML: **/index.html (except skipped dirs), root *.html, keywords.json targets."""
    site_dir = site_dir.resolve()
    found: Dict[str, Path] = {}

    for p in sorted(site_dir.rglob("index.html")):
        if _path_has_skipped_part(p, site_dir):
            continue
        found[str(p.resolve())] = p

    for p in sorted(site_dir.glob("*.html")):
        if p.name == "index.html":
            continue
        found[str(p.resolve())] = p

    kw_path = site_dir / "_output" / "keywords.json"
    if kw_path.is_file():
        try:
            bundle = parse_keywords_file(kw_path)
            for t in bundle.targets:
                hp = resolve_site_html(site_dir, t.rel_path)
                if hp.is_file() and not _path_has_skipped_part(hp, site_dir):
                    found[str(hp.resolve())] = hp
        except (json.JSONDecodeError, SystemExit, OSError):
            pass

    return sorted(found.values(), key=lambda p: str(p.relative_to(site_dir)))


def resolve_internal_href(href: str, *, page_path: Path, site_dir: Path) -> Optional[Path]:
    """Resolve a relative internal href to a file under site_dir, or None if not a local file check."""
    h = (href or "").strip()
    if not h or h.startswith("#"):
        return None
    if h.startswith(("http://", "https://", "mailto:", "tel:", "javascript:", "data:")):
        return None

    parsed = urlparse(h)
    if parsed.scheme or parsed.netloc:
        return None

    path_part = h.split("?", 1)[0].split("#", 1)[0].strip()
    if not path_part:
        return None

    base = page_path.parent if page_path.name else site_dir
    target = (base / path_part).resolve()
    if target.is_dir():
        target = target / "index.html"
    if not target.is_file() and path_part.endswith("/"):
        target = (base / path_part / "index.html").resolve()
    try:
        target.relative_to(site_dir.resolve())
    except ValueError:
        return None
    return target


@dataclass
class Issue:
    id: str
    severity: str  # P0 | P1 | P2
    file: str
    message: str
    hint: str = ""


def main() -> int:
    apply_repo_dotenv(ROOT)

    ap = argparse.ArgumentParser(description="Static site smoke QA (links/anchors/meta/assets).")
    ap.add_argument("--site-dir", default="", help="Path to site directory.")
    args = ap.parse_args()

    site_dir_raw = (args.site_dir or os.getenv("SITE_DIR") or "").strip()
    if not site_dir_raw:
        raise SystemExit("Missing site dir: pass --site-dir or set SITE_DIR in environment/.env.")

    site_dir = Path(site_dir_raw)
    if not site_dir.is_absolute():
        site_dir = (ROOT / site_dir).resolve()
    else:
        site_dir = site_dir.resolve()

    if not site_dir.exists():
        raise SystemExit(f"site dir not found: {site_dir}")

    html_files = collect_html_files(site_dir)
    if not html_files:
        raise SystemExit("No HTML files found under site dir (index.html, root *.html, or keywords targets).")

    issues: List[Issue] = []

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

        for href in hrefs:
            if href.startswith("#") and len(href) > 1:
                anchor = href[1:].split("?", 1)[0].split("&", 1)[0]
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

        for href in hrefs:
            if href.startswith("javascript:"):
                issues.append(Issue("link.javascript", "P2", rel, "javascript: link found", "Avoid javascript: in href"))

            target = resolve_internal_href(href, page_path=f, site_dir=site_dir)
            if target is not None and not target.is_file():
                issues.append(
                    Issue(
                        "link.target_missing",
                        "P1",
                        rel,
                        f'Internal link target not found: "{href}"',
                        f"Create {target.relative_to(site_dir)} or fix href",
                    )
                )

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

        og_image = get_meta_content(html, "og:image") or ""
        if not og_image:
            issues.append(Issue("og.image.missing", "P1", rel, "Missing og:image", "Add og:image"))
        else:
            m = re.search(r"https?://[^/]+/(.+)$", og_image)
            if m:
                path_part = m.group(1).split("?", 1)[0]
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

    sev_rank = {"P0": 0, "P1": 1, "P2": 2}
    issues.sort(key=lambda x: (sev_rank.get(x.severity, 9), x.id, x.file))
    status = "PASS" if not any(i.severity == "P0" for i in issues) else "FAIL"

    audited = [str(p.relative_to(site_dir)) for p in html_files]
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
        "html_files_audited": audited,
    }

    out_path = ROOT / "output" / "qa_smoke.json"
    write_json(out_path, report)
    print(f"Smoke QA: {status} (P0={report['counts']['P0']}, P1={report['counts']['P1']}, P2={report['counts']['P2']})")
    print(f"HTML files audited: {len(audited)}")
    print(f"Report saved to: {out_path}")

    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
