#!/usr/bin/env python3
"""
Shared keywords file parsing for SEO agents.

Supports:
  - Legacy v1: JSON array of { keyword, search_volume, ... }
  - v2: JSON object with version>=2, pages[], optional technical_pages[], reserve[].
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class PageKeywordTarget:
    """One HTML file + keyword rows used for QA / generation."""

    page_id: str
    kind: str  # "page" | "technical"
    rel_path: str  # relative to site root, e.g. index.html
    rows: List[Dict[str, Any]]
    qa_profile: str = "standard"  # standard | technical


@dataclass
class KeywordsBundle:
    version: int
    source_path: Path
    targets: List[PageKeywordTarget]
    reserve_rows: List[Dict[str, Any]] = field(default_factory=list)
    raw_meta: Dict[str, Any] = field(default_factory=dict)


def _normalize_row(x: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(x, dict) or "keyword" not in x:
        return None
    kw = str(x.get("keyword", "")).strip()
    if not kw:
        return None
    return {
        "keyword": kw,
        "search_volume": int(x.get("search_volume") or 0),
        "keyword_difficulty": float(x.get("keyword_difficulty") or 0),
        "cpc": float(x.get("cpc") or 0),
        "competition": str(x.get("competition") or ""),
    }


def normalize_keyword_rows(items: List[Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for x in items or []:
        r = _normalize_row(x)
        if r:
            out.append(r)
    out.sort(key=lambda k: (k["search_volume"], k["keyword_difficulty"]), reverse=True)
    return out


def _parse_page_entry(
    obj: Any,
    *,
    kind: str,
    default_qa: str,
) -> Optional[PageKeywordTarget]:
    if not isinstance(obj, dict):
        return None
    pid = str(obj.get("id") or "").strip()
    rel = str(obj.get("path") or obj.get("html") or "").strip().lstrip("/")
    if not pid or not rel:
        return None
    kws = obj.get("keywords")
    if not isinstance(kws, list):
        kws = []
    profile = str(obj.get("qa_profile") or default_qa).strip().lower()
    if profile not in ("standard", "technical"):
        profile = default_qa
    return PageKeywordTarget(
        page_id=pid,
        kind=kind,
        rel_path=rel,
        rows=normalize_keyword_rows(kws),
        qa_profile=profile,
    )


def parse_keywords_file(path: Path) -> KeywordsBundle:
    raw = json.loads(path.read_text(encoding="utf-8", errors="replace"))

    if isinstance(raw, list):
        rows = normalize_keyword_rows(raw)
        return KeywordsBundle(
            version=1,
            source_path=path,
            targets=[
                PageKeywordTarget(
                    page_id="legacy",
                    kind="page",
                    rel_path="index.html",
                    rows=rows,
                    qa_profile="standard",
                )
            ],
            reserve_rows=[],
            raw_meta={},
        )

    if not isinstance(raw, dict):
        raise ValueError(f"keywords.json must be a list or object, got {type(raw).__name__}")

    ver = int(raw.get("version") or 1)
    if ver < 2:
        kws = raw.get("keywords")
        if isinstance(kws, list):
            rows = normalize_keyword_rows(kws)
            rel = str(raw.get("path") or "index.html").strip().lstrip("/") or "index.html"
            pid = str(raw.get("id") or "legacy").strip() or "legacy"
            return KeywordsBundle(
                version=1,
                source_path=path,
                targets=[
                    PageKeywordTarget(
                        page_id=pid,
                        kind="page",
                        rel_path=rel,
                        rows=rows,
                        qa_profile="standard",
                    )
                ],
                reserve_rows=normalize_keyword_rows(raw.get("reserve") or []) if isinstance(raw.get("reserve"), list) else [],
                raw_meta={k: v for k, v in raw.items() if k not in ("keywords", "reserve", "anchors")},
            )
        raise ValueError("keywords.json object must include version>=2 or a top-level keywords array")

    targets: List[PageKeywordTarget] = []
    for p in raw.get("pages") or []:
        t = _parse_page_entry(p, kind="page", default_qa="standard")
        if t:
            targets.append(t)
    for p in raw.get("technical_pages") or []:
        t = _parse_page_entry(p, kind="technical", default_qa="technical")
        if t:
            targets.append(t)

    if not targets:
        raise ValueError("keywords.json v2 must include non-empty pages and/or technical_pages")

    reserve: List[Dict[str, Any]] = []
    if isinstance(raw.get("reserve"), list):
        reserve = normalize_keyword_rows(raw.get("reserve"))

    return KeywordsBundle(
        version=ver,
        source_path=path,
        targets=targets,
        reserve_rows=reserve,
        raw_meta={k: v for k, v in raw.items() if k not in ("pages", "technical_pages", "reserve", "anchors", "version")},
    )


def pick_target(bundle: KeywordsBundle, page_id: Optional[str]) -> PageKeywordTarget:
    if page_id:
        for t in bundle.targets:
            if t.page_id == page_id:
                return t
        raise SystemExit(f"PAGE_ID / --page-id={page_id!r} not found in keywords bundle.")
    for t in bundle.targets:
        if t.kind == "page":
            return t
    return bundle.targets[0]


def resolve_site_html(site_dir: Path, rel_path: str) -> Path:
    p = (site_dir / rel_path).resolve()
    try:
        p.relative_to(site_dir.resolve())
    except ValueError as e:
        raise SystemExit(f"Invalid keywords path escapes site_dir: {rel_path}") from e
    return p
