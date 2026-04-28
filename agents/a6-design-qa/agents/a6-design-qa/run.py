#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


ROOT = Path(__file__).resolve().parents[4]
ENV_PATH = ROOT / ".env"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def load_env(path: Path) -> Dict[str, str]:
    env: Dict[str, str] = {}
    if not path.exists():
        return env
    for raw in read_text(path).splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    return env


def norm_space(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def strip_tags(html: str) -> str:
    html = re.sub(r"(?is)<(script|style)\b[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?is)<!--.*?-->", " ", html)
    html = re.sub(r"(?is)<[^>]+>", " ", html)
    return norm_space(html)


def remove_head(html: str) -> str:
    return re.sub(r"(?is)<head\b[^>]*>.*?</head>", " ", html)


def remove_ld_json_scripts(html: str) -> str:
    # schema.org JSON-LD should not influence keyword density checks
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


def find_first(pattern: str, s: str) -> Optional[re.Match[str]]:
    return re.search(pattern, s, flags=re.I | re.S)


def find_all(pattern: str, s: str) -> List[re.Match[str]]:
    return list(re.finditer(pattern, s, flags=re.I | re.S))


def get_title(html: str) -> Optional[str]:
    m = find_first(r"<title>\s*(.*?)\s*</title>", html)
    return norm_space(m.group(1)) if m else None


def get_h1_text(html: str) -> Optional[str]:
    m = find_first(r"<h1\b[^>]*>\s*(.*?)\s*</h1>", html)
    if not m:
        return None
    inner = re.sub(r"(?is)<[^>]+>", " ", m.group(1))
    return norm_space(inner)


def get_meta_content(html: str, name: Optional[str] = None, prop: Optional[str] = None) -> Optional[str]:
    if name:
        pat = rf'<meta\b[^>]*\bname=["\']{re.escape(name)}["\'][^>]*>'
    elif prop:
        pat = rf'<meta\b[^>]*\bproperty=["\']{re.escape(prop)}["\'][^>]*>'
    else:
        return None
    m = find_first(pat, html)
    if not m:
        return None
    tag = m.group(0)
    m2 = find_first(r'\bcontent=["\'](.*?)["\']', tag)
    return norm_space(m2.group(1)) if m2 else None


def has_link_rel(html: str, rel_value: str) -> bool:
    return bool(find_first(rf'<link\b[^>]*\brel=["\']{re.escape(rel_value)}["\']', html))


def has_hreflang(html: str, value: str) -> bool:
    return bool(
        find_first(
            rf'<link\b[^>]*\brel=["\']alternate["\'][^>]*\bhreflang=["\']{re.escape(value)}["\']',
            html,
        )
    )


def count_tags(html: str, tag: str) -> int:
    return len(find_all(rf"<{re.escape(tag)}\b", html))


def extract_ids_with_counts(html: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for m in find_all(r'\bid=["\']([^"\']+)["\']', html):
        _id = m.group(1).strip()
        if not _id:
            continue
        counts[_id] = counts.get(_id, 0) + 1
    return counts


def extract_internal_anchors(html: str) -> List[str]:
    anchors: List[str] = []
    for m in find_all(r'<a\b[^>]*\bhref=["\']([^"\']+)["\']', html):
        href = (m.group(1) or "").strip()
        if href.startswith("#") and len(href) > 1:
            anchors.append(href[1:])
    return anchors


def extract_a_tags(html: str) -> List[Tuple[str, str]]:
    """Returns list of (attrs, href)."""
    out: List[Tuple[str, str]] = []
    for m in find_all(r"<a\b([^>]*?)>", html):
        attrs = m.group(1) or ""
        mh = find_first(r'\bhref=["\'](.*?)["\']', attrs)
        href = (mh.group(1) if mh else "").strip()
        out.append((attrs, href))
    return out


def extract_links_with_text(html: str, text_re: str) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    for m in find_all(r"<a\b([^>]*?)>(.*?)</a>", html):
        attrs = m.group(1) or ""
        inner = norm_space(re.sub(r"(?is)<[^>]+>", " ", m.group(2) or ""))
        if not re.search(text_re, inner, flags=re.I):
            continue
        mh = find_first(r'\bhref=["\'](.*?)["\']', attrs)
        href = (mh.group(1) if mh else "").strip()
        out.append((inner, href))
    return out


def extract_img_tags(html: str) -> List[str]:
    return [m.group(0) for m in find_all(r"<img\b[^>]*>", html)]


def has_schema_type(html: str, schema_type: str) -> bool:
    return bool(
        find_first(
            rf'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>.*?"@type"\s*:\s*"{re.escape(schema_type)}".*?</script>',
            html,
        )
    )


def get_footer_text(html: str) -> str:
    m = find_first(r"<footer\b[^>]*>.*?</footer>", html)
    if not m:
        return ""
    return strip_tags(m.group(0))


def word_count(s: str) -> int:
    # Count "words" as letter/digit tokens (keeps French apostrophes inside tokens)
    return len(re.findall(r"[0-9A-Za-zÀ-ÖØ-öø-ÿ]+(?:'[0-9A-Za-zÀ-ÖØ-öø-ÿ]+)?", s))


def compute_keyword_density_report(
    *,
    keywords_rows: List[Dict[str, Any]],
    body_text_lower: str,
    top10_keywords: List[str],
) -> Dict[str, Any]:
    total_words = word_count(body_text_lower)
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
            offenders.append(
                {
                    "keyword": kw,
                    "count": c,
                    "density": f"{density:.1f}%",
                    "action": "reduce",
                }
            )

        if c > 5:
            density_warn_keywords.append(kw)

    status = "PASS"
    if offenders or missing:
        status = "FAIL"

    return {
        "status": status,
        "total_words": total_words,
        "offenders": offenders,
        "missing": missing,
        "warn_over_5_occurrences": density_warn_keywords,
    }


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
    site_html_path = Path(env.get("QA_HTML_PATH", str(ROOT / "sites" / "cazilla-clone-be-fr" / "index.html")))
    keywords_path = Path(env.get("QA_KEYWORDS_PATH", str(ROOT / "output" / "keywords.json")))
    report_path = Path(env.get("QA_REPORT_PATH", str(ROOT / "output" / "qa_report.json")))

    html = read_text(site_html_path)
    body_fragment = extract_body_html(remove_head(html))
    page_text_lower = visible_plain_text_from_html_fragment(body_fragment).lower()

    site_url = (env.get("SITE_URL") or "").rstrip("/")
    main_casino_url = (env.get("MAIN_CASINO_URL") or "https://cazilla.casino").rstrip("/")

    results: List[CheckResult] = []

    # -------------------
    # SEO checklist (existing)
    # -------------------
    title = get_title(html)
    if title and 30 <= len(title) <= 60:
        results.append(ok("seo.title.length", "title присутствует и длина 30-60 символов", length=len(title), title=title))
    elif title:
        results.append(fail("seo.title.length", "title присутствует, но длина вне диапазона 30-60", length=len(title), title=title))
    else:
        results.append(fail("seo.title.length", "title отсутствует"))

    desc = get_meta_content(html, name="description")
    if desc and 120 <= len(desc) <= 160:
        results.append(ok("seo.meta_description.length", "meta description присутствует и длина 120-160 символов", length=len(desc)))
    elif desc:
        results.append(fail("seo.meta_description.length", "meta description присутствует, но длина вне диапазона 120-160", length=len(desc)))
    else:
        results.append(fail("seo.meta_description.length", "meta description отсутствует"))

    results.append(ok("seo.canonical", "canonical тег присутствует") if has_link_rel(html, "canonical") else fail("seo.canonical", "canonical тег отсутствует"))
    results.append(ok("seo.hreflang.fr-be", "hreflang fr-BE присутствует") if has_hreflang(html, "fr-BE") else fail("seo.hreflang.fr-be", "hreflang fr-BE отсутствует"))
    results.append(ok("seo.hreflang.x-default", "hreflang x-default присутствует") if has_hreflang(html, "x-default") else fail("seo.hreflang.x-default", "hreflang x-default отсутствует"))

    h1_count = count_tags(html, "h1")
    results.append(ok("seo.h1.single", "h1 присутствует и только один", count=h1_count) if h1_count == 1 else fail("seo.h1.single", "h1 должен быть ровно один", count=h1_count))

    h2_count = count_tags(html, "h2")
    results.append(ok("seo.h2.min3", "h2 теги присутствуют (минимум 3)", count=h2_count) if h2_count >= 3 else fail("seo.h2.min3", "h2 тегов меньше 3", count=h2_count))

    results.append(ok("seo.schema.organization", "schema.org Organization присутствует") if has_schema_type(html, "Organization") else fail("seo.schema.organization", "schema.org Organization отсутствует"))
    results.append(ok("seo.schema.website", "schema.org WebSite присутствует") if has_schema_type(html, "WebSite") else fail("seo.schema.website", "schema.org WebSite отсутствует"))

    robots = get_meta_content(html, name="robots")
    rl = (robots or "").lower()
    if robots and "noindex" in rl and "nofollow" in rl:
        # Satellite/review pages are often intentionally noindex — don't fail the whole QA for that.
        results.append(warn("seo.robots.noindex_nofollow", "robots meta содержит noindex/nofollow", content=robots))
    elif robots and "index" in rl and "follow" in rl:
        results.append(ok("seo.robots.index_follow", "robots meta index,follow присутствует", content=robots))
    elif robots:
        results.append(warn("seo.robots.unexpected", "robots meta присутствует, но значение нестандартное", content=robots))
    else:
        results.append(fail("seo.robots.index_follow", "robots meta отсутствует"))

    results.append(ok("seo.og.title", "og:title присутствует") if get_meta_content(html, prop="og:title") else fail("seo.og.title", "og:title отсутствует"))
    results.append(ok("seo.og.description", "og:description присутствует") if get_meta_content(html, prop="og:description") else fail("seo.og.description", "og:description отсутствует"))

    # -------------------
    # SEO QUALITY (new)
    # -------------------
    main_kw = "casino en ligne belgique"
    if title and main_kw.lower() in title.lower():
        results.append(ok("seo_quality.title.contains_main_kw", 'Главный ключ присутствует в title ("casino en ligne belgique")'))
    else:
        results.append(fail("seo_quality.title.contains_main_kw", 'Главный ключ "casino en ligne belgique" отсутствует в title', title=title or ""))

    h1_text = get_h1_text(html)
    if h1_text and main_kw.lower() in h1_text.lower():
        results.append(ok("seo_quality.h1.contains_main_kw", 'Главный ключ присутствует в h1 ("casino en ligne belgique")', h1=h1_text))
    else:
        results.append(fail("seo_quality.h1.contains_main_kw", 'Главный ключ "casino en ligne belgique" отсутствует в h1', h1=h1_text or ""))

    if desc and "cazilla" in desc.lower():
        results.append(ok("seo_quality.meta_description.contains_brand", 'Meta description содержит слово "Cazilla"'))
    else:
        results.append(fail("seo_quality.meta_description.contains_brand", 'Meta description не содержит слово "Cazilla"', description=desc or ""))

    if get_meta_content(html, prop="og:image"):
        results.append(ok("seo_quality.og.image", "og:image тег присутствует"))
    else:
        results.append(warn("seo_quality.og.image", "og:image тег отсутствует"))

    # -------------------
    # Content checklist (existing)
    # -------------------
    top_keywords: List[str] = []
    kw_rows: List[Dict[str, Any]] = []
    keywords_warned = False
    if keywords_path.exists():
        try:
            kw_data = json.loads(read_text(keywords_path))
            if isinstance(kw_data, list) and kw_data:
                kw_rows = [r for r in kw_data if isinstance(r, dict) and r.get("keyword")]
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
        missing = [k for k in top_keywords if k.lower() not in page_text_lower]
        if not missing:
            results.append(ok("content.keywords.top10_present", "Топ-10 ключей по volume присутствуют в тексте", top10=top_keywords))
        else:
            results.append(fail("content.keywords.top10_present", "Некоторые ключи из топ-10 отсутствуют в тексте", missing=missing, top10=top_keywords))

    # -------------------
    # KEYWORD DENSITY (new)
    # -------------------
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
            body_text_lower=page_text_lower,
            top10_keywords=top_keywords,
        )
        for kw in kd_report.get("warn_over_5_occurrences", []) or []:
            results.append(warn("keyword_density.count_gt_5", "Ключ встречается > 5 раз", keyword=kw))

        if kd_report["status"] == "FAIL":
            details: Dict[str, Any] = {"offenders": kd_report.get("offenders", []), "missing": kd_report.get("missing", [])}
            if kd_report.get("offenders"):
                results.append(fail("keyword_density.too_high", "Плотность ключа > 3%", **details))
            if kd_report.get("missing"):
                results.append(fail("keyword_density.missing_top10", "Топ-10 ключ отсутствует в видимом тексте страницы", **details))
        else:
            results.append(ok("keyword_density.ok", "Плотность ключей в норме", total_words=kd_report.get("total_words", 0)))

    sign_in_links = extract_links_with_text(html, r"\bSign\s*In\b")
    if sign_in_links and all(href.startswith(main_casino_url) for _, href in sign_in_links if href):
        results.append(ok("content.links.signin", "Ссылки Sign In ведут на cazilla.casino", count=len(sign_in_links)))
    else:
        bad = [(t, h) for (t, h) in sign_in_links if not (h or "").startswith(main_casino_url)]
        results.append(fail("content.links.signin", "Не все ссылки Sign In ведут на cazilla.casino", bad=bad, expected_prefix=main_casino_url) if sign_in_links else fail("content.links.signin", "Не найдены ссылки Sign In"))

    sign_up_links = extract_links_with_text(html, r"\bSign\s*Up\b")
    if sign_up_links and all(href.startswith(main_casino_url) for _, href in sign_up_links if href):
        results.append(ok("content.links.signup", "Ссылки Sign Up ведут на cazilla.casino", count=len(sign_up_links)))
    else:
        bad = [(t, h) for (t, h) in sign_up_links if not (h or "").startswith(main_casino_url)]
        results.append(fail("content.links.signup", "Не все ссылки Sign Up ведут на cazilla.casino", bad=bad, expected_prefix=main_casino_url) if sign_up_links else fail("content.links.signup", "Не найдены ссылки Sign Up"))

    ids_counts = extract_ids_with_counts(html)
    ids_set = set(ids_counts.keys())
    internal = extract_internal_anchors(html)
    missing_ids = sorted({a for a in internal if a not in ids_set})
    results.append(ok("content.links.internal", "Нет битых внутренних ссылок", internal_count=len(internal)) if not missing_ids else fail("content.links.internal", "Есть битые внутренние ссылки (href=#... без id)", missing_ids=missing_ids))

    # -------------------
    # Technical checklist (existing)
    # -------------------
    viewport = get_meta_content(html, name="viewport")
    results.append(ok("tech.meta.viewport", "viewport meta тег присутствует") if viewport else fail("tech.meta.viewport", "viewport meta тег отсутствует"))

    charset_ok = bool(find_first(r'<meta\b[^>]*\bcharset=["\']utf-8["\']', html))
    results.append(ok("tech.meta.charset", "charset utf-8 присутствует") if charset_ok else fail("tech.meta.charset", "charset utf-8 отсутствует"))

    lang_ok = bool(find_first(r'<html\b[^>]*\blang=["\'][^"\']+["\']', html))
    results.append(ok("tech.html.lang", "lang атрибут на html теге присутствует") if lang_ok else fail("tech.html.lang", "lang атрибут на html теге отсутствует"))

    inline_styles = len(find_all(r'\sstyle=["\']', html))
    results.append(warn("tech.inline_styles.count", "Слишком много inline style атрибутов (> 20)", count=inline_styles, threshold=20) if inline_styles > 20 else ok("tech.inline_styles.count", "Inline style атрибутов не больше 20", count=inline_styles, threshold=20))

    # -------------------
    # IMAGES (new)
    # -------------------
    img_tags = extract_img_tags(html)
    imgs_missing_alt: List[str] = []
    imgs_empty_alt: List[str] = []
    for tag in img_tags:
        malt = find_first(r'\balt=["\'](.*?)["\']', tag)
        if not malt:
            imgs_missing_alt.append(tag[:160])
            continue
        alt_val = (malt.group(1) or "").strip()
        if alt_val == "":
            imgs_empty_alt.append(tag[:160])

    if imgs_missing_alt:
        results.append(fail("images.img.alt_present", "Не все img теги имеют alt атрибут", missing_count=len(imgs_missing_alt), samples=imgs_missing_alt[:5]))
    else:
        results.append(ok("images.img.alt_present", "Все img теги имеют alt атрибут", img_count=len(img_tags)))

    if imgs_empty_alt:
        results.append(warn("images.img.alt_nonempty", "Есть img с пустым alt", empty_count=len(imgs_empty_alt), samples=imgs_empty_alt[:5]))
    else:
        results.append(ok("images.img.alt_nonempty", "Alt атрибуты не пустые", img_count=len(img_tags)))

    # -------------------
    # LINKS (new)
    # -------------------
    a_tags = extract_a_tags(html)
    bad_localhost = [href for _, href in a_tags if "localhost" in href.lower() or "127.0.0.1" in href.lower()]
    results.append(ok("links.no_localhost", "Нет ссылок на localhost/127.0.0.1") if not bad_localhost else fail("links.no_localhost", "Есть ссылки на localhost/127.0.0.1", bad=bad_localhost[:10]))

    hash_only = [href for _, href in a_tags if href.strip() == "#"]
    results.append(warn("links.href_hash_only", 'Есть ссылки с href="#"', count=len(hash_only), samples=hash_only[:5]) if hash_only else ok("links.href_hash_only", 'Нет ссылок с href="#"'))

    # External links should have rel="noopener" (WARN)
    external_missing_noopener: List[str] = []
    for attrs, href in a_tags:
        if not href.lower().startswith(("http://", "https://")):
            continue
        # consider external if not the same SITE_URL (if known)
        if site_url and href.startswith(site_url):
            continue
        rel_m = find_first(r'\brel=["\'](.*?)["\']', attrs)
        rel_val = (rel_m.group(1) if rel_m else "").lower()
        if "noopener" not in rel_val:
            external_missing_noopener.append(href)
    results.append(
        warn("links.external.noopener", "Не все внешние ссылки имеют rel=noopener", bad=external_missing_noopener[:10])
        if external_missing_noopener
        else ok("links.external.noopener", "Все внешние ссылки имеют rel=noopener")
    )

    # -------------------
    # FILES (new)
    # -------------------
    site_dir = site_html_path.parent
    sitemap_path = site_dir / "sitemap.xml"
    robots_path = site_dir / "robots.txt"
    results.append(ok("files.sitemap.exists", "sitemap.xml существует") if sitemap_path.exists() else warn("files.sitemap.exists", "sitemap.xml не найден", path=str(sitemap_path)))
    results.append(ok("files.robots.exists", "robots.txt существует") if robots_path.exists() else warn("files.robots.exists", "robots.txt не найден", path=str(robots_path)))

    size_b = site_html_path.stat().st_size
    if size_b < 30 * 1024:
        results.append(fail("files.index.size_min", "Размер index.html меньше 30KB", bytes=size_b))
    else:
        results.append(ok("files.index.size_min", "Размер index.html больше 30KB", bytes=size_b))
    if size_b > 5 * 1024 * 1024:
        results.append(fail("files.index.size_max", "Размер index.html больше 5MB", bytes=size_b))
    else:
        results.append(ok("files.index.size_max", "Размер index.html меньше 5MB", bytes=size_b))

    # -------------------
    # STRUCTURE (new)
    # -------------------
    footer_text = get_footer_text(html)
    wc = word_count(footer_text)
    results.append(ok("structure.footer.seo_text", "Footer содержит SEO текст (>= 100 слов)", words=wc) if wc >= 100 else fail("structure.footer.seo_text", "В footer меньше 100 слов", words=wc))

    has_form = bool(find_first(r"<form\b", html))
    has_cta = bool(find_first(rf'<a\b[^>]*\bhref=["\']{re.escape(main_casino_url)}', html)) or bool(find_first(rf'<a\b[^>]*\bhref=["\']{re.escape(main_casino_url)}/', html))
    results.append(ok("structure.form_or_cta", "Есть форма или CTA кнопка ведущая на cazilla.casino", has_form=has_form, has_cta=has_cta) if (has_form or has_cta) else fail("structure.form_or_cta", "Нет формы и нет CTA на cazilla.casino", has_form=has_form, has_cta=has_cta))

    dup_ids = sorted([_id for _id, c in ids_counts.items() if c > 1])
    results.append(ok("structure.no_duplicate_ids", "Нет дублирующихся id атрибутов") if not dup_ids else fail("structure.no_duplicate_ids", "Найдены дублирующиеся id атрибуты", duplicate_ids=dup_ids))

    # -------------------
    # Summary + output
    # -------------------
    pass_n = sum(1 for r in results if r.status == "PASS")
    warn_n = sum(1 for r in results if r.status == "WARN")
    fail_n = sum(1 for r in results if r.status == "FAIL")

    report: Dict[str, Any] = {
        "meta": {
            "html_path": str(site_html_path),
            "keywords_path": str(keywords_path),
            "report_path": str(report_path),
        },
        "summary": {"PASS": pass_n, "WARN": warn_n, "FAIL": fail_n},
        "results": [{"id": r.id, "status": r.status, "message": r.message, "details": r.details} for r in results],
        "keyword_density": kd_report,
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # Auto-fix chain (one shot) if keyword density fails
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

    # Full report output
    print(f"✅ PASS: {pass_n} пунктов")
    print(f"⚠️ WARN: {warn_n} пунктов")
    print(f"❌ FAIL: {fail_n} пунктов")
    print(f"Report saved to: {report_path}")
    print("\n=== FULL REPORT ===")
    for r in results:
        print(f"[{r.status}] {r.id} — {r.message}")
        if r.details:
            print(f"  details: {json.dumps(r.details, ensure_ascii=False)}")

    return 0 if fail_n == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

