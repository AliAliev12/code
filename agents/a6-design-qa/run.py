#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT / ".env"

_AGENTS_DIR = ROOT / "agents"
if str(_AGENTS_DIR) not in sys.path:
    sys.path.insert(0, str(_AGENTS_DIR))

from _lib.keywords_bundle import (  # noqa: E402
    KeywordsBundle,
    PageKeywordTarget,
    parse_keywords_file,
    resolve_site_html,
)
from _lib.repo_env import apply_repo_dotenv  # noqa: E402


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def load_env(path: Path) -> Dict[str, str]:
    env: Dict[str, str] = {}
    if not path.exists():
        return env
    for raw in read_text(path).splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    return env


def default_site_dir(env: Dict[str, str]) -> Path:
    site_dir = (env.get("SITE_DIR") or os.getenv("SITE_DIR") or "").strip()
    if not site_dir:
        raise SystemExit("Missing SITE_DIR in .env/environment.")
    return (ROOT / site_dir).resolve()


def strip_tags(html: str) -> str:
    html = re.sub(r"(?is)<(script|style)\b[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?is)<!--.*?-->", " ", html)
    html = re.sub(r"(?is)<[^>]+>", " ", html)
    html = re.sub(r"\s+", " ", html).strip()
    return html


def find_first(pattern: str, s: str, flags: int = 0) -> Optional[re.Match[str]]:
    return re.search(pattern, s, flags)


def find_all(pattern: str, s: str, flags: int = 0) -> List[re.Match[str]]:
    return list(re.finditer(pattern, s, flags))


def remove_head(html: str) -> str:
    return re.sub(r"(?is)<head\b[^>]*>.*?</head>", " ", html)


def remove_ld_json_scripts(html: str) -> str:
    return re.sub(
        r'(?is)<script\b[^>]*\btype=["\']application/ld\+json["\'][^>]*>.*?</script>',
        " ",
        html,
    )


def extract_body_html(html: str) -> str:
    m = find_first(r"(?is)<body\b[^>]*>(.*)</body>", html)
    return m.group(1) if m else html


def visible_plain_text_from_html_fragment(fragment_html: str) -> str:
    frag = remove_ld_json_scripts(fragment_html)
    return strip_tags(frag)


def count_substrings(haystack_lower: str, needle: str) -> int:
    n = (needle or "").strip().lower()
    if not n:
        return 0
    return haystack_lower.count(n)


def kw_word_len(keyword: str) -> int:
    return len([w for w in re.split(r"\s+", (keyword or "").strip()) if w])


def word_count_visible(s: str) -> int:
    return len(re.findall(r"[0-9A-Za-zÀ-ÖØ-öø-ÿ]+(?:'[0-9A-Za-zÀ-ÖØ-öø-ÿ]+)?", s))


def compute_keyword_density_report(
    *,
    keywords_rows: List[Dict[str, Any]],
    body_text_lower: str,
    top10_keywords: List[str],
) -> Dict[str, Any]:
    total_words = word_count_visible(body_text_lower)
    offenders: List[Dict[str, Any]] = []
    missing: List[str] = []
    density_warn_keywords: List[str] = []

    for row in keywords_rows:
        if not isinstance(row, dict):
            continue
        kw = str(row.get("keyword", "")).strip()
        if not kw:
            continue
        c = count_substrings(body_text_lower, kw)
        kw_len = max(1, kw_word_len(kw))
        density = (c * kw_len / total_words * 100.0) if total_words else 0.0

        if kw in top10_keywords and c == 0:
            missing.append(kw)

        if density > 3.0:
            offenders.append({"keyword": kw, "count": c, "density": f"{density:.1f}%", "action": "reduce"})

        # "Count > N" warnings are a lightweight heuristic. For longer phrases it's normal to repeat
        # a few times (especially when exact-match keywords include common substrings).
        if kw_len <= 2 and c > 5:
            density_warn_keywords.append(kw)
        elif kw_len >= 3 and c > 12:
            density_warn_keywords.append(kw)

    status = "FAIL" if (offenders or missing) else "PASS"
    return {
        "status": status,
        "total_words": total_words,
        "offenders": offenders,
        "missing": missing,
        "warn_over_5_occurrences": density_warn_keywords,
    }


def norm_space(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def get_title(html: str) -> Optional[str]:
    m = find_first(r"(?is)<title[^>]*>\s*(.*?)\s*</title>", html)
    return norm_space(m.group(1)) if m else None


def get_meta_content(html: str, name: Optional[str] = None, prop: Optional[str] = None) -> Optional[str]:
    if name:
        pat = rf'(?is)<meta\b[^>]*\bname=["\']{re.escape(name)}["\'][^>]*>'
    elif prop:
        pat = rf'(?is)<meta\b[^>]*\bproperty=["\']{re.escape(prop)}["\'][^>]*>'
    else:
        return None
    m = find_first(pat, html)
    if not m:
        return None
    tag = m.group(0)
    m2 = find_first(r'(?is)\bcontent=["\'](.*?)["\']', tag)
    return norm_space(m2.group(1)) if m2 else None


def has_link_rel(html: str, rel_value: str) -> bool:
    return bool(find_first(rf'(?is)<link\b[^>]*\brel=["\']{re.escape(rel_value)}["\']', html))


def has_hreflang(html: str, value: str) -> bool:
    return bool(
        find_first(
            rf'(?is)<link\b[^>]*\brel=["\']alternate["\'][^>]*\bhreflang=["\']{re.escape(value)}["\']',
            html,
        )
    )


def count_tags(html: str, tag: str) -> int:
    return len(find_all(rf"(?is)<{re.escape(tag)}\b", html))


def extract_ids(html: str) -> set[str]:
    ids = set()
    for m in find_all(r'(?is)\bid=["\']([^"\']+)["\']', html):
        ids.add(m.group(1))
    return ids


def extract_internal_anchors(html: str) -> List[str]:
    anchors: List[str] = []
    for m in find_all(r'(?is)<a\b[^>]*\bhref=["\']([^"\']+)["\']', html):
        href = m.group(1).strip()
        if href.startswith("#") and len(href) > 1:
            anchors.append(href[1:])
    return anchors


def extract_links_with_text(html: str, text_re: str) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    for m in find_all(r'(?is)<a\b([^>]*?)>(.*?)</a>', html):
        attrs = m.group(1)
        inner = norm_space(re.sub(r"(?is)<[^>]+>", " ", m.group(2)))
        if not re.search(text_re, inner, flags=re.I):
            continue
        m_href = find_first(r'(?is)\bhref=["\'](.*?)["\']', attrs)
        href = m_href.group(1).strip() if m_href else ""
        out.append((inner, href))
    return out


def count_inline_styles(html: str) -> int:
    return len(find_all(r'(?is)\sstyle=["\']', html))


def has_schema_type(html: str, schema_type: str) -> bool:
    # Very lightweight: checks JSON-LD blocks containing "@type": "<schema_type>"
    return bool(find_first(rf'(?is)<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>.*?"@type"\s*:\s*"{re.escape(schema_type)}".*?</script>', html))


@dataclass
class CheckResult:
    id: str
    status: str  # PASS | FAIL | WARN
    message: str
    details: Dict[str, Any]


def ok(check_id: str, message: str, **details: Any) -> CheckResult:
    return CheckResult(id=check_id, status="PASS", message=message, details=details)


def fail(check_id: str, message: str, **details: Any) -> CheckResult:
    return CheckResult(id=check_id, status="FAIL", message=message, details=details)


def warn(check_id: str, message: str, **details: Any) -> CheckResult:
    return CheckResult(id=check_id, status="WARN", message=message, details=details)


def _top10_keywords_from_rows(kw_rows: List[Dict[str, Any]]) -> List[str]:
    rows: List[Tuple[int, str]] = []
    for r in kw_rows:
        if not isinstance(r, dict) or "keyword" not in r:
            continue
        sv = r.get("search_volume", 0) or 0
        try:
            sv_int = int(sv)
        except Exception:
            sv_int = 0
        k = str(r.get("keyword", "")).strip()
        if k:
            rows.append((sv_int, k))
    rows.sort(key=lambda x: x[0], reverse=True)
    return [k for _, k in rows][:10]


def audit_single_page(
    html: str,
    env: Dict[str, str],
    *,
    kw_rows: List[Dict[str, Any]],
    qa_profile: str,
) -> Tuple[List[CheckResult], Dict[str, Any], bool]:
    """
    Run full SEO/content/tech checklist for one HTML document.
    Returns (results, keyword_density_report, keywords_warned_skipped).
    """
    body_fragment = extract_body_html(remove_head(html))
    text = visible_plain_text_from_html_fragment(body_fragment).lower()
    results: List[CheckResult] = []

    title = get_title(html)
    if qa_profile == "technical":
        if title and 55 <= len(title) <= 60:
            results.append(
                ok("seo.title.length", "title присутствует и длина 55-60 символов (technical)", length=len(title), title=title)
            )
        elif title:
            results.append(
                fail(
                    "seo.title.length",
                    "title присутствует, но длина вне диапазона 55-60 (technical)",
                    length=len(title),
                    title=title,
                )
            )
        else:
            results.append(fail("seo.title.length", "title отсутствует"))
    elif title and 30 <= len(title) <= 60:
        results.append(ok("seo.title.length", "title присутствует и длина 30-60 символов", length=len(title), title=title))
    elif title:
        results.append(fail("seo.title.length", "title присутствует, но длина вне диапазона 30-60", length=len(title), title=title))
    else:
        results.append(fail("seo.title.length", "title отсутствует"))

    desc = get_meta_content(html, name="description")
    if qa_profile == "technical":
        if desc and len(desc) <= 140:
            results.append(
                ok(
                    "seo.meta_description.length",
                    "meta description присутствует и длина ≤140 символов (technical)",
                    length=len(desc),
                )
            )
        elif desc:
            results.append(
                fail(
                    "seo.meta_description.length",
                    "meta description длиннее 140 символов (technical)",
                    length=len(desc),
                )
            )
        else:
            results.append(fail("seo.meta_description.length", "meta description отсутствует"))
    elif desc and 110 <= len(desc) <= 180:
        results.append(ok("seo.meta_description.length", "meta description присутствует и длина 110-180 символов", length=len(desc)))
    elif desc:
        results.append(
            warn(
                "seo.meta_description.length",
                "meta description присутствует, но длина вне диапазона 110-180 (hygiene warning)",
                length=len(desc),
            )
        )
    else:
        results.append(fail("seo.meta_description.length", "meta description отсутствует"))

    if qa_profile == "technical":
        card_m = re.search(
            r'(?is)<div\s+class="policyCard">([\s\S]*?)</div>\s*<p\s+class="fineprint"',
            html,
        )
        if not card_m:
            card_m = re.search(
                r'(?is)<article\s+class="rb-policyArticle"[^>]*>([\s\S]*?)</article>',
                html,
            )
        if not card_m:
            card_m = re.search(
                r'(?is)<div\s+class="rb-policyCard">([\s\S]*?)</div>\s*</main>',
                html,
            )
        main_frag = card_m.group(1) if card_m else ""
        if not main_frag.strip():
            main_m = re.search(r"(?is)<main\b[^>]*>([\s\S]*?)</main>", html)
            main_frag = main_m.group(1) if main_m else ""
        main_len = len(strip_tags(main_frag))
        if 1500 <= main_len <= 3000:
            results.append(
                ok(
                    "content.technical.main_length",
                    "объём текста в main 1500-3000 символов (technical)",
                    length=main_len,
                )
            )
        else:
            results.append(
                fail(
                    "content.technical.main_length",
                    "объём текста в main вне диапазона 1500-3000 (technical)",
                    length=main_len,
                )
            )

    if has_link_rel(html, "canonical"):
        results.append(ok("seo.canonical", "canonical тег присутствует"))
    else:
        results.append(fail("seo.canonical", "canonical тег отсутствует"))

    hreflang_primary = str(
        env.get("QA_HREFLANG_PRIMARY") or env.get("TARGET_LOCALE") or os.getenv("QA_HREFLANG_PRIMARY") or os.getenv("TARGET_LOCALE") or ""
    ).strip()
    if not hreflang_primary:
        raise SystemExit("Missing hreflang setting: set QA_HREFLANG_PRIMARY or TARGET_LOCALE in .env/environment.")
    hreflang_primary_id = re.sub(r"[^a-z0-9]+", "-", hreflang_primary.lower()).strip("-")
    results.append(
        ok(f"seo.hreflang.{hreflang_primary_id}", f"hreflang {hreflang_primary} присутствует")
        if has_hreflang(html, hreflang_primary)
        else fail(f"seo.hreflang.{hreflang_primary_id}", f"hreflang {hreflang_primary} отсутствует")
    )
    results.append(ok("seo.hreflang.x-default", "hreflang x-default присутствует") if has_hreflang(html, "x-default") else fail("seo.hreflang.x-default", "hreflang x-default отсутствует"))

    h1_count = count_tags(html, "h1")
    if h1_count == 1:
        results.append(ok("seo.h1.single", "h1 присутствует и только один", count=h1_count))
    else:
        results.append(fail("seo.h1.single", "h1 должен быть ровно один", count=h1_count))

    h2_count = count_tags(html, "h2")
    h2_min = 1 if qa_profile == "technical" else 3
    if h2_count >= h2_min:
        results.append(ok("seo.h2.min", f"h2 теги присутствуют (минимум {h2_min})", count=h2_count, profile=qa_profile))
    else:
        results.append(fail("seo.h2.min", f"h2 тегов меньше {h2_min}", count=h2_count, profile=qa_profile))

    results.append(
        ok("seo.schema.organization", "schema.org Organization присутствует")
        if has_schema_type(html, "Organization")
        else warn("seo.schema.organization", "schema.org Organization отсутствует (optional)", note="Recommended but not required.")
    )
    if has_schema_type(html, "WebSite"):
        results.append(ok("seo.schema.website", "schema.org WebSite присутствует"))
    elif qa_profile == "technical":
        results.append(warn("seo.schema.website", "schema.org WebSite отсутствует (optional on technical pages)"))
    else:
        results.append(fail("seo.schema.website", "schema.org WebSite отсутствует"))

    robots = get_meta_content(html, name="robots")
    rl = (robots or "").lower()
    if robots and "noindex" in rl and "nofollow" in rl:
        results.append(warn("seo.robots.noindex_nofollow", "robots meta содержит noindex/nofollow", content=robots))
    elif robots and "index" in rl and "follow" in rl:
        results.append(ok("seo.robots.index_follow", "robots meta index,follow присутствует", content=robots))
    elif robots:
        results.append(warn("seo.robots.unexpected", "robots meta присутствует, но значение нестандартное", content=robots))
    else:
        results.append(fail("seo.robots.index_follow", "robots meta отсутствует"))

    results.append(ok("seo.og.title", "og:title присутствует") if get_meta_content(html, prop="og:title") else fail("seo.og.title", "og:title отсутствует"))
    results.append(ok("seo.og.description", "og:description присутствует") if get_meta_content(html, prop="og:description") else fail("seo.og.description", "og:description отсутствует"))

    top_keywords: List[str] = []
    keywords_warned = False
    if kw_rows:
        top_keywords = _top10_keywords_from_rows(kw_rows)
        missing = [k for k in top_keywords if k.lower() not in text]
        if not missing:
            results.append(ok("content.keywords.top10_present", "Топ-10 ключей по volume присутствуют в тексте", top10=top_keywords))
        else:
            results.append(fail("content.keywords.top10_present", "Некоторые ключи из топ-10 отсутствуют в тексте", missing=missing, top10=top_keywords))
    else:
        keywords_warned = True
        results.append(warn("content.keywords.top10_present", "Нет ключей для страницы — проверка топ-10 пропущена"))

    kd_report: Dict[str, Any]
    if keywords_warned:
        kd_report = {
            "status": "PASS",
            "offenders": [],
            "missing": [],
            "warn_over_5_occurrences": [],
            "total_words": 0,
            "note": "no page keywords — keyword_density skipped",
        }
        results.append(warn("keyword_density.skipped", "keyword_density пропущен: нет ключей для этой страницы"))
    else:
        kd_report = compute_keyword_density_report(
            keywords_rows=kw_rows,
            body_text_lower=text,
            top10_keywords=top_keywords,
        )
        for kw in kd_report.get("warn_over_5_occurrences", []) or []:
            results.append(warn("keyword_density.count_gt_5", "Ключ встречается > 5 раз", keyword=kw))

        if kd_report["status"] == "FAIL":
            details = {"offenders": kd_report.get("offenders", []), "missing": kd_report.get("missing", [])}
            if kd_report.get("offenders"):
                results.append(fail("keyword_density.too_high", "Плотность ключа > 3%", **details))
            if kd_report.get("missing"):
                results.append(fail("keyword_density.missing_top10", "Топ-10 ключ отсутствует в видимом тексте страницы", **details))
        else:
            results.append(ok("keyword_density.ok", "Плотность ключей в норме", total_words=kd_report.get("total_words", 0)))

    main_casino_url = (env.get("MAIN_CASINO_URL") or os.getenv("MAIN_CASINO_URL") or "").strip().rstrip("/")
    if not main_casino_url:
        raise SystemExit("Missing MAIN_CASINO_URL in .env/environment.")
    cta_regex = str(env.get("QA_CTA_REGEX", r"(Official site|Open Cazilla|Play at Cazilla|Accéder au site officiel|Voir l’offre|Jouer)")).strip()
    cta_links = extract_links_with_text(html, cta_regex)
    if not cta_links:
        results.append(fail("content.links.cta", f"Не найдены CTA-ссылки по regex: {cta_regex}"))
    else:
        bad = [(t, h) for (t, h) in cta_links if not (h or "").startswith(main_casino_url)]
        if bad:
            results.append(
                fail(
                    "content.links.cta",
                    "Не все CTA-ссылки ведут на MAIN_CASINO_URL",
                    bad=bad[:8],
                    expected_prefix=main_casino_url,
                    count=len(cta_links),
                )
            )
        else:
            results.append(ok("content.links.cta", "CTA-ссылки ведут на MAIN_CASINO_URL", count=len(cta_links)))

    ids = extract_ids(html)
    internal = extract_internal_anchors(html)
    missing_ids = sorted({a for a in internal if a not in ids})
    if not missing_ids:
        results.append(ok("content.links.internal", "Нет битых внутренних ссылок", internal_count=len(internal)))
    else:
        results.append(fail("content.links.internal", "Есть битые внутренние ссылки (href=#... без id)", missing_ids=missing_ids))

    viewport = get_meta_content(html, name="viewport")
    results.append(ok("tech.meta.viewport", "viewport meta тег присутствует") if viewport else fail("tech.meta.viewport", "viewport meta тег отсутствует"))

    charset_ok = bool(find_first(r'(?is)<meta\b[^>]*\bcharset=["\']utf-8["\']', html))
    results.append(ok("tech.meta.charset", "charset utf-8 присутствует") if charset_ok else fail("tech.meta.charset", "charset utf-8 отсутствует"))

    lang_ok = bool(find_first(r'(?is)<html\b[^>]*\blang=["\'][^"\']+["\']', html))
    results.append(ok("tech.html.lang", "lang атрибут на html теге присутствует") if lang_ok else fail("tech.html.lang", "lang атрибут на html теге отсутствует"))

    inline_styles = count_inline_styles(html)
    if inline_styles > 20:
        results.append(warn("tech.inline_styles.count", "Слишком много inline style атрибутов (> 20)", count=inline_styles, threshold=20))
    else:
        results.append(ok("tech.inline_styles.count", "Inline style атрибутов не больше 20", count=inline_styles, threshold=20))

    return results, kd_report, keywords_warned


def resolve_path(value: Optional[str], *, base: Path = ROOT) -> Optional[Path]:
    if not value:
        return None
    p = Path(value)
    if not p.is_absolute():
        p = (base / p).resolve()
    return p


def load_keywords_bundle(keywords_path: Path, site_dir: Path) -> KeywordsBundle:
    if not keywords_path.exists():
        return KeywordsBundle(
            version=1,
            source_path=keywords_path,
            targets=[
                PageKeywordTarget(
                    page_id="legacy",
                    kind="page",
                    rel_path="index.html",
                    rows=[],
                    qa_profile="standard",
                )
            ],
            reserve_rows=[],
            raw_meta={},
        )
    try:
        return parse_keywords_file(keywords_path)
    except (json.JSONDecodeError, ValueError, OSError) as e:
        raise SystemExit(f"Invalid keywords file {keywords_path}: {e}") from e


def _filter_targets_for_html(site_dir: Path, bundle: KeywordsBundle, forced_html: Optional[Path]) -> List[PageKeywordTarget]:
    if forced_html is None:
        return list(bundle.targets)
    want = forced_html.resolve()
    matched = [t for t in bundle.targets if resolve_site_html(site_dir, t.rel_path).resolve() == want]
    if matched:
        return matched
    try:
        rel = str(want.relative_to(site_dir.resolve()))
    except ValueError:
        rel = "index.html"
    if bundle.targets:
        ft = bundle.targets[0]
        fallback_rows = ft.rows
    else:
        fallback_rows = []
    return [
        PageKeywordTarget(
            page_id="adhoc",
            kind="page",
            rel_path=rel,
            rows=fallback_rows,
            qa_profile="standard",
        )
    ]


def _result_dicts(results: List[CheckResult]) -> List[Dict[str, Any]]:
    return [{"id": r.id, "status": r.status, "message": r.message, "details": r.details} for r in results]


def main() -> int:
    apply_repo_dotenv(ROOT)

    ap = argparse.ArgumentParser(description="SEO QA checks for generated static site.")
    ap.add_argument("--site-dir", help="Site directory that contains index.html and optional _output/keywords.json")
    ap.add_argument("--html-path", help="Override target HTML path (default: <site-dir>/index.html)")
    ap.add_argument("--keywords-path", help="Override keywords.json path")
    ap.add_argument("--report-path", help="Override qa_report.json output path")
    ap.add_argument(
        "--include-technical",
        action="store_true",
        help="Also run SEO checks on keywords.json technical_pages (default: skip them; audit landing pages only).",
    )
    args = ap.parse_args()

    env = {**load_env(ENV_PATH), **os.environ}
    if env.get("A6_DISABLE_KEYWORD_DENSITY_AUTOFIX", "").strip() in ("1", "true", "TRUE", "yes", "YES"):
        env["A6_KEYWORD_DENSITY_AUTOFIX_DONE"] = "1"

    default_site_dir_path = default_site_dir(env)
    cli_site_dir = resolve_path(args.site_dir)
    site_dir = cli_site_dir or default_site_dir_path
    default_index = site_dir / "index.html"
    keywords_path = site_dir / "_output" / "keywords.json"
    report_path = ROOT / "output" / "qa_report.json"

    cli_html_path = resolve_path(args.html_path)
    cli_keywords_path = resolve_path(args.keywords_path)
    cli_report_path = resolve_path(args.report_path)
    env_html_path = resolve_path(env.get("QA_HTML_PATH"))
    env_keywords_path = resolve_path(env.get("QA_KEYWORDS_PATH"))
    env_report_path = resolve_path(env.get("QA_REPORT_PATH"))

    forced_single_html = cli_html_path or env_html_path
    site_html_path = forced_single_html or default_index
    keywords_path = cli_keywords_path or env_keywords_path or keywords_path
    report_path = cli_report_path or env_report_path or report_path

    if not site_html_path.exists():
        raise SystemExit(
            f"HTML path not found: {site_html_path}. "
            "Set SITE_DIR in .env/environment, pass --site-dir, or pass --html-path."
        )

    bundle = load_keywords_bundle(keywords_path, site_dir)
    targets = _filter_targets_for_html(site_dir, bundle, forced_single_html)
    technical_skipped: List[PageKeywordTarget] = []
    if not args.include_technical:
        technical_skipped = [t for t in targets if t.kind == "technical"]
        targets = [t for t in targets if t.kind != "technical"]
    if not targets:
        if forced_single_html and technical_skipped:
            raise SystemExit(
                "The selected HTML matches a technical_pages target; A6 skips technical pages by default. "
                "Re-run with --include-technical to audit it, or choose a non-technical page."
            )
        raise SystemExit("No keyword targets left to audit after excluding technical pages.")
    multi = len(targets) > 1 and forced_single_html is None

    page_reports: List[Dict[str, Any]] = []
    flat_results: List[CheckResult] = []
    primary_kd: Dict[str, Any] = {
        "status": "PASS",
        "offenders": [],
        "missing": [],
        "warn_over_5_occurrences": [],
        "total_words": 0,
        "note": "no pages audited",
    }
    primary_html_for_meta: Path = site_html_path
    primary_page_id = ""

    primary_set = False
    for t in targets:
        html_path = resolve_site_html(site_dir, t.rel_path)
        if not html_path.exists():
            page_reports.append(
                {
                    "page_id": t.page_id,
                    "kind": t.kind,
                    "rel_path": t.rel_path,
                    "html_path": str(html_path),
                    "skipped": True,
                    "error": "HTML file not found",
                }
            )
            continue

        html = read_text(html_path)
        results, kd_report, _kw_skip = audit_single_page(
            html,
            env,
            kw_rows=t.rows,
            qa_profile=t.qa_profile,
        )
        id_prefix = f"{t.page_id}/" if multi else ""
        for r in results:
            rid = f"{id_prefix}{r.id}" if id_prefix else r.id
            det = dict(r.details) if r.details else {}
            det.setdefault("page_id", t.page_id)
            flat_results.append(CheckResult(id=rid, status=r.status, message=r.message, details=det))

        pn = sum(1 for r in results if r.status == "PASS")
        wn = sum(1 for r in results if r.status == "WARN")
        fn = sum(1 for r in results if r.status == "FAIL")
        page_reports.append(
            {
                "page_id": t.page_id,
                "kind": t.kind,
                "rel_path": t.rel_path,
                "html_path": str(html_path),
                "summary": {"PASS": pn, "WARN": wn, "FAIL": fn},
                "results": _result_dicts(results),
                "keyword_density": kd_report,
            }
        )

        if not primary_set:
            primary_kd = kd_report
            primary_html_for_meta = html_path
            primary_page_id = t.page_id
            primary_set = True

    for t in technical_skipped:
        hp = resolve_site_html(site_dir, t.rel_path)
        page_reports.append(
            {
                "page_id": t.page_id,
                "kind": t.kind,
                "rel_path": t.rel_path,
                "html_path": str(hp),
                "skipped": True,
                "error": "technical page excluded from A6 audit (use --include-technical to audit)",
            }
        )

    if not flat_results and page_reports and all(p.get("skipped") for p in page_reports):
        raise SystemExit("No HTML files found for any keywords target under site_dir.")

    pass_n = sum(1 for r in flat_results if r.status == "PASS")
    warn_n = sum(1 for r in flat_results if r.status == "WARN")
    fail_n = sum(1 for r in flat_results if r.status == "FAIL")
    rollup_status = "FAIL" if fail_n else "PASS"

    report: Dict[str, Any] = {
        "version": 2,
        "status": rollup_status,
        "meta": {
            "html_path": str(primary_html_for_meta),
            "keywords_path": str(keywords_path),
            "report_path": str(report_path),
            "keywords_bundle_version": bundle.version,
            "primary_page_id": primary_page_id,
            "pages_audited": len([p for p in page_reports if not p.get("skipped")]),
            "technical_pages_skipped": len(technical_skipped),
        },
        "summary": {"PASS": pass_n, "WARN": warn_n, "FAIL": fail_n},
        "results": _result_dicts(flat_results),
        "pages": page_reports,
        "keyword_density": primary_kd,
        "reserve_keyword_count": len(bundle.reserve_rows),
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    kd_status = (primary_kd or {}).get("status")
    autofix_done = os.environ.get("A6_KEYWORD_DENSITY_AUTOFIX_DONE") == "1"
    if kd_status == "FAIL" and (not autofix_done) and primary_page_id:
        a2 = ROOT / "agents" / "a2-content" / "run.py"
        if a2.exists():
            print("\n=== AUTOFIX: keyword_density FAIL on primary page → launching A2 --fix-density ===")
            env_run = os.environ.copy()
            env_run["A6_KEYWORD_DENSITY_AUTOFIX_DONE"] = "1"
            env_run["QA_HTML_PATH"] = str(primary_html_for_meta)
            env_run["PAGE_ID"] = primary_page_id
            r = subprocess.run(
                [sys.executable, str(a2), "--fix-density"],
                cwd=str(ROOT),
                env=env_run,
                capture_output=True,
                text=True,
            )
            print((r.stdout or "").strip())
            if r.stderr:
                print((r.stderr or "").strip())
            if r.returncode != 0:
                print(f"A2 fix-density failed (exit {r.returncode})")

            print("\n=== Re-running QA after fix ===")
            r2 = subprocess.run([sys.executable, str(Path(__file__).resolve())], cwd=str(ROOT), env=env_run)
            return int(r2.returncode)
        else:
            print(f"WARN: A2 runner not found at {a2} — skipping autofix")

    print(f"✅ PASS: {pass_n} пунктов")
    print(f"⚠️ WARN: {warn_n} пунктов")
    print(f"❌ FAIL: {fail_n} пунктов")
    print(f"Report saved to: {report_path}")

    if fail_n:
        print("\nFAILED checks:")
        for r in flat_results:
            if r.status == "FAIL":
                print(f"- {r.id}: {r.message}")

    if warn_n:
        print("\nWARN checks:")
        for r in flat_results:
            if r.status == "WARN":
                print(f"- {r.id}: {r.message}")

    return 0 if fail_n == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

