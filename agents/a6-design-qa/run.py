#!/usr/bin/env python3
from __future__ import annotations

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
    m = find_first(r"(?is)<title>\s*(.*?)\s*</title>", html)
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


def main() -> int:
    env = {**load_env(ENV_PATH), **os.environ}
    if env.get("A6_DISABLE_KEYWORD_DENSITY_AUTOFIX", "").strip() in ("1", "true", "TRUE", "yes", "YES"):
        env["A6_KEYWORD_DENSITY_AUTOFIX_DONE"] = "1"
    site_html_path = ROOT / "sites" / "cazilla-clone-be-fr" / "index.html"
    keywords_path = ROOT / "output" / "keywords.json"
    report_path = ROOT / "output" / "qa_report.json"

    # Allow overriding via env (but keep defaults)
    site_html_path = Path(env.get("QA_HTML_PATH", str(site_html_path)))
    keywords_path = Path(env.get("QA_KEYWORDS_PATH", str(keywords_path)))
    report_path = Path(env.get("QA_REPORT_PATH", str(report_path)))

    html = read_text(site_html_path)
    body_fragment = extract_body_html(remove_head(html))
    text = visible_plain_text_from_html_fragment(body_fragment).lower()

    results: List[CheckResult] = []

    # --- SEO checklist ---
    title = get_title(html)
    if title and 30 <= len(title) <= 60:
        results.append(ok("seo.title.length", "title присутствует и длина 30-60 символов", length=len(title), title=title))
    elif title:
        results.append(fail("seo.title.length", "title присутствует, но длина вне диапазона 30-60", length=len(title), title=title))
    else:
        results.append(fail("seo.title.length", "title отсутствует"))

    desc = get_meta_content(html, name="description")
    # Practical ranges differ by language and punctuation; keep this as a hygiene WARN, not a hard FAIL.
    if desc and 110 <= len(desc) <= 180:
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

    if has_link_rel(html, "canonical"):
        results.append(ok("seo.canonical", "canonical тег присутствует"))
    else:
        results.append(fail("seo.canonical", "canonical тег отсутствует"))

    results.append(ok("seo.hreflang.fr-be", "hreflang fr-BE присутствует") if has_hreflang(html, "fr-BE") else fail("seo.hreflang.fr-be", "hreflang fr-BE отсутствует"))
    results.append(ok("seo.hreflang.x-default", "hreflang x-default присутствует") if has_hreflang(html, "x-default") else fail("seo.hreflang.x-default", "hreflang x-default отсутствует"))

    h1_count = count_tags(html, "h1")
    if h1_count == 1:
        results.append(ok("seo.h1.single", "h1 присутствует и только один", count=h1_count))
    else:
        results.append(fail("seo.h1.single", "h1 должен быть ровно один", count=h1_count))

    h2_count = count_tags(html, "h2")
    if h2_count >= 3:
        results.append(ok("seo.h2.min3", "h2 теги присутствуют (минимум 3)", count=h2_count))
    else:
        results.append(fail("seo.h2.min3", "h2 тегов меньше 3", count=h2_count))

    results.append(
        ok("seo.schema.organization", "schema.org Organization присутствует")
        if has_schema_type(html, "Organization")
        else warn("seo.schema.organization", "schema.org Organization отсутствует (optional)", note="Recommended but not required.")
    )
    results.append(ok("seo.schema.website", "schema.org WebSite присутствует") if has_schema_type(html, "WebSite") else fail("seo.schema.website", "schema.org WebSite отсутствует"))

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

    # --- Content checklist ---
    # Keywords top-10 (by volume) present in text
    top_keywords: List[str] = []
    kw_rows: List[Dict[str, Any]] = []
    keywords_warned = False
    if keywords_path.exists():
        try:
            kw_data = json.loads(read_text(keywords_path))
            if isinstance(kw_data, list) and kw_data:
                kw_rows = [r for r in kw_data if isinstance(r, dict) and r.get("keyword")]
                # Expect objects with: keyword, search_volume
                rows = []
                for r in kw_data:
                    if isinstance(r, dict) and "keyword" in r:
                        sv = r.get("search_volume", 0) or 0
                        try:
                            sv_int = int(sv)
                        except Exception:
                            sv_int = 0
                        rows.append((sv_int, str(r.get("keyword", "")).strip()))
                rows.sort(key=lambda x: x[0], reverse=True)
                top_keywords = [k for _, k in rows if k][:10]
            else:
                keywords_warned = True
        except Exception as e:
            results.append(warn("content.keywords.load", "Не удалось прочитать keywords.json (пропускаю проверку ключей)", error=str(e)))
            keywords_warned = True
    else:
        keywords_warned = True

    if keywords_warned:
        results.append(warn("content.keywords.top10_present", "keywords.json пустой/отсутствует — нечего проверять по ключам"))
    else:
        missing = [k for k in top_keywords if k.lower() not in text]
        if not missing:
            results.append(ok("content.keywords.top10_present", "Топ-10 ключей по volume присутствуют в тексте", top10=top_keywords))
        else:
            results.append(fail("content.keywords.top10_present", "Некоторые ключи из топ-10 отсутствуют в тексте", missing=missing, top10=top_keywords))

    kd_report: Dict[str, Any] = {
        "status": "PASS",
        "offenders": [],
        "missing": [],
        "warn_over_5_occurrences": [],
        "total_words": 0,
    }
    if keywords_warned:
        kd_report = {
            "status": "PASS",
            "offenders": [],
            "missing": [],
            "warn_over_5_occurrences": [],
            "total_words": 0,
            "note": "keywords.json missing/invalid — keyword_density skipped",
        }
        results.append(warn("keyword_density.skipped", "keyword_density пропущен: нет keywords.json"))
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

    # Primary CTA links should point to cazilla.casino (site policy)
    main_casino_url = env.get("MAIN_CASINO_URL", "https://cazilla.casino").rstrip("/")
    cta_links = extract_links_with_text(html, r"(Accéder au site officiel|Voir l’offre|Jouer)")
    if not cta_links:
        results.append(fail("content.links.cta", "Не найдены CTA-ссылки (Accéder/Voir l’offre/Jouer)"))
    else:
        bad = [(t, h) for (t, h) in cta_links if not (h or "").startswith(main_casino_url)]
        if bad:
            results.append(
                fail(
                    "content.links.cta",
                    "Не все CTA-ссылки ведут на cazilla.casino",
                    bad=bad[:8],
                    expected_prefix=main_casino_url,
                    count=len(cta_links),
                )
            )
        else:
            results.append(ok("content.links.cta", "CTA-ссылки ведут на cazilla.casino", count=len(cta_links)))

    # No broken internal links
    ids = extract_ids(html)
    internal = extract_internal_anchors(html)
    missing_ids = sorted({a for a in internal if a not in ids})
    if not missing_ids:
        results.append(ok("content.links.internal", "Нет битых внутренних ссылок", internal_count=len(internal)))
    else:
        results.append(fail("content.links.internal", "Есть битые внутренние ссылки (href=#... без id)", missing_ids=missing_ids))

    # --- Technical checklist ---
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

    pass_n = sum(1 for r in results if r.status == "PASS")
    warn_n = sum(1 for r in results if r.status == "WARN")
    fail_n = sum(1 for r in results if r.status == "FAIL")

    report: Dict[str, Any] = {
        "meta": {
            "html_path": str(site_html_path),
            "keywords_path": str(keywords_path),
            "report_path": str(report_path),
        },
        "summary": {
            "PASS": pass_n,
            "WARN": warn_n,
            "FAIL": fail_n,
        },
        "results": [
            {"id": r.id, "status": r.status, "message": r.message, "details": r.details}
            for r in results
        ],
        "keyword_density": kd_report,
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    kd_status = (kd_report or {}).get("status")
    autofix_done = os.environ.get("A6_KEYWORD_DENSITY_AUTOFIX_DONE") == "1"
    if kd_status == "FAIL" and (not autofix_done):
        a2 = ROOT / "agents" / "a2-content" / "agents" / "a2-content" / "run.py"
        if a2.exists():
            print("\n=== AUTOFIX: keyword_density FAIL → launching A2 --fix-density ===")
            env_run = os.environ.copy()
            env_run["A6_KEYWORD_DENSITY_AUTOFIX_DONE"] = "1"
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
        for r in results:
            if r.status == "FAIL":
                print(f"- {r.id}: {r.message}")

    if warn_n:
        print("\nWARN checks:")
        for r in results:
            if r.status == "WARN":
                print(f"- {r.id}: {r.message}")

    return 0 if fail_n == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

