#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import html as html_module
import importlib.util
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests


ROOT = Path(__file__).resolve().parents[4]
ENV_PATH = ROOT / ".env"

_AGENTS_DIR = ROOT / "agents"
if str(_AGENTS_DIR) not in sys.path:
    sys.path.insert(0, str(_AGENTS_DIR))

from _lib.keywords_bundle import parse_keywords_file, pick_target, resolve_site_html  # noqa: E402

CONTENT_FORMAT_V2 = 2

HUMANIZE_FIELDS = ["hero_subtitle", "about_section", "bonus_section", "games_section", "footer_seo_text"]


def load_env(path: Path) -> Dict[str, str]:
    env: Dict[str, str] = {}
    if not path.exists():
        return env
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    return env


def default_site_dir(env: Dict[str, str]) -> str:
    site_dir = (env.get("SITE_DIR") or os.getenv("SITE_DIR") or "").strip()
    if not site_dir:
        raise SystemExit("Missing SITE_DIR in .env/environment.")
    return site_dir


def default_html_path(env: Dict[str, str]) -> Path:
    html_path = ROOT / default_site_dir(env) / "index.html"
    if not html_path.exists():
        raise SystemExit(f"HTML path not found: {html_path}")
    return html_path


def resolve_a3_html_path(env: Dict[str, str]) -> Path:
    explicit = (env.get("QA_HTML_PATH") or os.getenv("QA_HTML_PATH") or "").strip()
    if explicit:
        p = Path(explicit)
        if not p.is_absolute():
            p = (ROOT / p).resolve()
        if p.exists():
            return p
    content_path = ROOT / "output" / "content.json"
    if content_path.exists():
        try:
            c = json.loads(content_path.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            c = {}
        if isinstance(c, dict):
            th = str(c.get("target_html_path") or "").strip()
            if th:
                hp = (ROOT / th).resolve()
                if hp.exists():
                    return hp
            if int(c.get("content_format_version") or 1) >= CONTENT_FORMAT_V2:
                pages = c.get("pages")
                if isinstance(pages, dict):
                    home = pages.get("home")
                    if isinstance(home, dict):
                        th2 = str(home.get("target_html_path") or "").strip()
                        if th2:
                            hp = (ROOT / th2).resolve()
                            if hp.exists():
                                return hp
            pid = str(c.get("target_page_id") or "").strip()
            if pid:
                try:
                    kpath = ROOT / default_site_dir(env) / "_output" / "keywords.json"
                    if kpath.exists():
                        b = parse_keywords_file(kpath)
                        t = pick_target(b, pid)
                        hp = resolve_site_html(ROOT / default_site_dir(env), t.rel_path)
                        if hp.exists():
                            return hp
                except SystemExit:
                    raise
                except Exception:
                    pass
    return default_html_path(env)


def content_format_version(content: Dict[str, Any]) -> int:
    return int(content.get("content_format_version") or 1)


def landing_page_block(content: Dict[str, Any], page_id: str) -> Dict[str, Any]:
    if content_format_version(content) >= CONTENT_FORMAT_V2:
        pages = content.get("pages")
        if not isinstance(pages, dict):
            raise SystemExit("v2 content.json requires a pages object.")
        blk = pages.get(page_id)
        if not isinstance(blk, dict):
            raise SystemExit(f"v2 content.json missing pages.{page_id}.")
        return blk
    return content


def landing_home_block(content: Dict[str, Any]) -> Dict[str, Any]:
    if content_format_version(content) >= CONTENT_FORMAT_V2:
        return landing_page_block(content, "home")
    return content


def assert_landing_fields(content: Dict[str, Any], field_names: List[str], *, page_id: Optional[str] = None) -> None:
    pid = (page_id or "home").strip() or "home"
    blk = landing_page_block(content, pid) if content_format_version(content) >= CONTENT_FORMAT_V2 else content
    missing = [f for f in field_names if f not in blk or not str(blk.get(f, "")).strip()]
    if missing:
        loc = f"pages.{pid}" if content_format_version(content) >= CONTENT_FORMAT_V2 else "content.json"
        raise SystemExit(f"Missing fields in {loc}: {missing}")


def merge_landing_field_updates(
    content: Dict[str, Any], updates: Dict[str, str], *, page_id: Optional[str] = None
) -> Dict[str, Any]:
    merged = copy.deepcopy(content)
    pid = (page_id or "home").strip() or "home"
    if content_format_version(merged) >= CONTENT_FORMAT_V2:
        pages = dict(merged.get("pages") or {})
        blk = dict(pages.get(pid) or {})
        for k, v in updates.items():
            blk[k] = v
        pages[pid] = blk
        merged["pages"] = pages
    else:
        merged.update(updates)
    return merged


def humanized_snapshot(merged: Dict[str, Any]) -> Any:
    if content_format_version(merged) >= CONTENT_FORMAT_V2:
        pages_out: Dict[str, Any] = {}
        for pid, pdata in (merged.get("pages") or {}).items():
            if not isinstance(pdata, dict):
                continue
            if pdata.get("page_kind") == "landing":
                pages_out[pid] = {k: str(pdata.get(k, "")) for k in ["hero_title", *HUMANIZE_FIELDS]}
        return {"content_format_version": 2, "pages": pages_out}
    home = landing_home_block(merged)
    return {k: str(home.get(k, "")) for k in ["hero_title", *HUMANIZE_FIELDS]}


def require_locale_lang(env: Dict[str, str]) -> Tuple[str, str]:
    locale = (env.get("TARGET_LOCALE") or os.getenv("TARGET_LOCALE") or "").strip()
    lang = (env.get("TARGET_LANG") or os.getenv("TARGET_LANG") or "").strip()
    if not locale:
        raise SystemExit("Missing TARGET_LOCALE in .env/environment.")
    if not lang:
        raise SystemExit("Missing TARGET_LANG in .env/environment.")
    return locale, lang


def resolve_models(env: Dict[str, str]) -> List[str]:
    primary = (env.get("ANTHROPIC_MODEL") or os.getenv("ANTHROPIC_MODEL") or "").strip()
    fallback = (env.get("ANTHROPIC_FALLBACK_MODEL") or os.getenv("ANTHROPIC_FALLBACK_MODEL") or "").strip()

    models: List[str] = []
    if primary:
        models.append(primary)
    if fallback and fallback not in models:
        models.append(fallback)

    if not models:
        models = ["claude-sonnet-4-6"]
    return models


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def remove_head(html: str) -> str:
    return re.sub(r"(?is)<head\b[^>]*>.*?</head>", " ", html)


def remove_ld_json_scripts(html: str) -> str:
    return re.sub(
        r'(?is)<script\b[^>]*\btype=["\']application/ld\+json["\'][^>]*>.*?</script>',
        " ",
        html,
    )


def strip_tags(html: str) -> str:
    html = re.sub(r"(?is)<(script|style)\b[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?is)<!--.*?-->", " ", html)
    html = re.sub(r"(?is)<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", html).strip()


def extract_body_html(html: str) -> str:
    m = re.search(r"(?is)<body\b[^>]*>(.*)</body>", html)
    return m.group(1) if m else html


def visible_body_text_lower(html: str) -> str:
    frag = extract_body_html(remove_head(html))
    frag = remove_ld_json_scripts(frag)
    return strip_tags(frag).lower()


def count_kw_in_body(html: str, kw: str) -> int:
    hay = visible_body_text_lower(html)
    needle = (kw or "").strip().lower()
    return hay.count(needle) if needle else 0


def replace_first_submatch(html: str, pattern: str, repl: str, flags: int = re.I | re.S) -> str:
    return re.sub(pattern, repl, html, count=1, flags=flags)


def apply_content_to_index_html(html: str, content: Dict[str, Any]) -> str:
    hero_title = str(content.get("hero_title", "")).strip()
    hero_sub = str(content.get("hero_subtitle", "")).strip()
    bonus = str(content.get("bonus_section", "")).strip()
    games = str(content.get("games_section", "")).strip()
    about = str(content.get("about_section", "")).strip()
    footer = str(content.get("footer_seo_text", "")).strip()

    if hero_title:
        html = replace_first_submatch(
            html,
            r'(?is)(<section\b[^>]*aria-label=["\']Hero["\'][^>]*>.*?<h1>)(.*?)(</h1>)',
            r"\g<1>" + hero_title + r"\g<3>",
        )

    if hero_sub:
        html = replace_first_submatch(
            html,
            r'(?is)(<section\b[^>]*aria-label=["\']Hero["\'][^>]*>.*?<p class="subtitle">\s*)([\s\S]*?)(\s*</p>)',
            r"\g<1>\n" + hero_sub + r"\n\g<3>",
        )

    if bonus:
        html = replace_first_submatch(
            html,
            r'(?is)(<section\b[^>]*\bid=["\']bonuses["\'][^>]*>[\s\S]*?<p class="subtitle"[^>]*>)([\s\S]*?)(</p>)',
            r"\g<1>\n" + bonus + r"\n\g<3>",
        )

    if games:
        html = replace_first_submatch(
            html,
            r'(?is)(<section\b[^>]*\bid=["\']games["\'][^>]*>[\s\S]*?<p class="subtitle"[^>]*>)([\s\S]*?)(</p>)',
            r"\g<1>\n" + games + r"\n\g<3>",
        )

    if about:
        html = replace_first_submatch(
            html,
            r'(?is)(<section\b[^>]*\bid=["\']about["\'][^>]*>[\s\S]*?<p class="subtitle"[^>]*>)([\s\S]*?)(</p>)',
            r"\g<1>\n" + about + r"\n\g<3>",
        )

    if footer:
        html = replace_first_submatch(
            html,
            r'(?is)(<footer\b[^>]*>[\s\S]*?<p\b[^>]*>)([\s\S]*?)(</p>[\s\S]*?</footer>)',
            r"\g<1>\n" + footer + r"\n\g<3>",
        )

    return html


_a2_mod: Any = None


def _load_a2_module() -> Any:
    global _a2_mod
    if _a2_mod is None:
        p = ROOT / "agents" / "a2-content" / "run.py"
        spec = importlib.util.spec_from_file_location("a2_content_run", p)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Cannot load A2 module from {p}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _a2_mod = mod
    return _a2_mod


def _main_casino_cta_html(env: Dict[str, str]) -> str:
    url = (env.get("MAIN_CASINO_URL") or os.getenv("MAIN_CASINO_URL") or "").strip().rstrip("/")
    if not url:
        return ""
    esc = html_module.escape(url, quote=True)
    return f' <a href="{esc}" rel="noopener noreferrer" target="_blank">Open Cazilla</a>'


def _is_agg_home(html: str) -> bool:
    return bool(re.search(r'(?i)class="agg-heroLead"', html))


def _is_agg_inner(html: str) -> bool:
    return bool(re.search(r'(?i)class="agg-pageHero"', html))


def _apply_agg_article_three_ps(html: str, about: str, bonus: str, games: str) -> str:
    texts = [about, bonus, games]
    m = re.search(r'(?is)(<article\s+class="agg-article">\s*)([\s\S]*?)(\s*</article>)', html)
    if not m:
        return html
    pre, inner, post = m.group(1), m.group(2), m.group(3)
    pat = re.compile(r"(?is)(<h2[^>]*>.*?</h2>\s*<p[^>]*>)([\s\S]*?)(</p>)")
    pos = 0
    out_chunks: List[str] = []
    im = 0
    for mm in pat.finditer(inner):
        out_chunks.append(inner[pos : mm.start()])
        if im < len(texts):
            g1, g3 = mm.group(1), mm.group(3)
            if str(texts[im] or "").strip():
                out_chunks.append(g1 + html_module.escape(str(texts[im]).strip()) + g3)
            else:
                out_chunks.append(mm.group(0))
            im += 1
        else:
            out_chunks.append(mm.group(0))
        pos = mm.end()
    out_chunks.append(inner[pos:])
    new_inner = "".join(out_chunks)
    return html[: m.start()] + pre + new_inner + post + html[m.end() :]


def apply_landing_content_to_html(html: str, content_block: Dict[str, Any], env: Dict[str, str]) -> str:
    """Apply landing HOME_CONTENT_KEYS-style block to HTML (legacy template or aggregator)."""
    hero_title = str(content_block.get("hero_title", "")).strip()
    hero_sub = str(content_block.get("hero_subtitle", "")).strip()
    bonus = str(content_block.get("bonus_section", "")).strip()
    games = str(content_block.get("games_section", "")).strip()
    about = str(content_block.get("about_section", "")).strip()
    footer = str(content_block.get("footer_seo_text", "")).strip()

    if _is_agg_inner(html):
        if hero_title:
            html = replace_first_submatch(
                html,
                r'(?is)(<header class="agg-pageHero"[^>]*>\s*<h1>)(.*?)(</h1>)',
                r"\g<1>" + html_module.escape(hero_title) + r"\g<3>",
            )
        if hero_sub:
            cta = _main_casino_cta_html(env)
            inner = html_module.escape(hero_sub)
            if cta and "Open Cazilla" not in hero_sub:
                inner = inner + cta
            html = replace_first_submatch(
                html,
                r'(?is)(<p class="agg-pageLead">\s*)([\s\S]*?)(\s*</p>)',
                r"\g<1>" + inner + r"\g<3>",
            )
        html = _apply_agg_article_three_ps(html, about, bonus, games)
        if footer:
            html = replace_first_submatch(
                html,
                r'(?is)(<section[^>]*\bid=["\']footer-legal["\'][^>]*>[\s\S]*?<p class="agg-footerSeo"[^>]*>\s*)([\s\S]*?)(\s*</p>)',
                r"\g<1>\n" + html_module.escape(footer) + r"\n\g<3>",
            )
        return html

    if _is_agg_home(html):
        if hero_title:
            html = replace_first_submatch(
                html,
                r'(?is)(<section\b[^>]*aria-label=["\']Hero["\'][^>]*>.*?<h1>)(.*?)(</h1>)',
                r"\g<1>" + html_module.escape(hero_title) + r"\g<3>",
            )
        if hero_sub:
            html = replace_first_submatch(
                html,
                r'(?is)(<p class="agg-heroLead">\s*)([\s\S]*?)(\s*</p>)',
                r"\g<1>" + html_module.escape(hero_sub) + r"\g<3>",
            )
        if about:
            html = replace_first_submatch(
                html,
                r'(?is)(<section\b[^>]*\bid=["\']listings["\'][^>]*>[\s\S]*?<p class="agg-listIntro"[^>]*>\s*)([\s\S]*?)(\s*</p>)',
                r"\g<1>\n" + html_module.escape(about) + r"\n\g<3>",
            )
        if bonus:
            html = replace_first_submatch(
                html,
                r'(?is)(<section\b[^>]*\bid=["\']bonuses["\'][^>]*>[\s\S]*?<p class="agg-prose"[^>]*>\s*)([\s\S]*?)(\s*</p>)',
                r"\g<1>\n" + html_module.escape(bonus) + r"\n\g<3>",
            )
        if games:
            html = replace_first_submatch(
                html,
                r'(?is)(<p\b[^>]*\bid=["\']seo-keywords["\'][^>]*>\s*)([\s\S]*?)(\s*</p>)',
                r"\g<1>\n" + html_module.escape(games) + r"\n\g<3>",
            )
        if footer:
            html = replace_first_submatch(
                html,
                r'(?is)(<section[^>]*\bid=["\']footer-legal["\'][^>]*>[\s\S]*?<p class="agg-footerSeo"[^>]*>\s*)([\s\S]*?)(\s*</p>)',
                r"\g<1>\n" + html_module.escape(footer) + r"\n\g<3>",
            )
        return html

    if re.search(r'(?is)class="ow-hero"', html) and re.search(r'(?is)class="ow-prose"', html):
        a2 = _load_a2_module()
        fn = getattr(a2, "apply_content_to_offerwall_html", None)
        if callable(fn):
            return fn(html, content_block, env)

    a2 = _load_a2_module()
    if callable(getattr(a2, "is_response_html", None)) and a2.is_response_html(html):
        fn = getattr(a2, "apply_content_to_response_html", None)
        if callable(fn):
            return fn(html, content_block)

    page_apply = getattr(a2, "apply_content_to_page_html", None)
    if callable(page_apply):
        return page_apply(html, content_block, env)

    return apply_content_to_index_html(html, content_block)


def call_anthropic(api_key: str, prompt: str, model: str, max_tokens: int = 1600) -> Dict[str, Any]:
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "content-type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": 0.55,
        "messages": [{"role": "user", "content": prompt}],
    }
    r = requests.post(url, headers=headers, json=payload, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"Anthropic HTTP {r.status_code}: {r.text[:800]}")
    data = r.json()
    parts: List[str] = []
    for block in data.get("content", []) or []:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return {"text": "\n".join([p for p in parts if p]).strip()}


def extract_json_from_text(s: str) -> Dict[str, Any]:
    try:
        obj = json.loads(s)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = s[start : end + 1]
        obj = json.loads(candidate)
        if isinstance(obj, dict):
            return obj
    raise ValueError("Could not parse JSON object from model output.")


def summarize_diff(before: str, after: str, limit: int = 420) -> Tuple[str, str]:
    b = before.strip()
    a = after.strip()
    return (b[:limit] + ("…" if len(b) > limit else ""), a[:limit] + ("…" if len(a) > limit else ""))


def offender_keywords_from_qa(qa: Dict[str, Any]) -> List[str]:
    kd = qa.get("keyword_density") if isinstance(qa, dict) else None
    if not isinstance(kd, dict):
        return []
    out: List[str] = []
    for o in kd.get("offenders", []) or []:
        if isinstance(o, dict) and o.get("keyword"):
            out.append(str(o["keyword"]).strip())
    # de-dupe, keep order
    seen = set()
    deduped: List[str] = []
    for k in out:
        kl = k.lower()
        if not k or kl in seen:
            continue
        seen.add(kl)
        deduped.append(k)
    return deduped


def offender_keywords_for_page(qa: Dict[str, Any], page_id: str) -> List[str]:
    for p in qa.get("pages") or []:
        if not isinstance(p, dict):
            continue
        if str(p.get("page_id", "")).strip() != page_id:
            continue
        kd = p.get("keyword_density") or {}
        if not isinstance(kd, dict):
            return []
        out: List[str] = []
        for o in kd.get("offenders", []) or []:
            if isinstance(o, dict) and o.get("keyword"):
                out.append(str(o["keyword"]).strip())
        seen = set()
        deduped: List[str] = []
        for k in out:
            kl = k.lower()
            if not k or kl in seen:
                continue
            seen.add(kl)
            deduped.append(k)
        return deduped
    return []


def build_humanize_subset_prompt(fields: List[str], subset: Dict[str, Any], offender_kws: List[str], env: Dict[str, str]) -> str:
    offenders = ", ".join([f'"{k}"' for k in offender_kws]) if offender_kws else "(none)"
    locale, lang = require_locale_lang(env)
    must_phrase = os.getenv("A3_MUST_INCLUDE_PHRASE", "").strip()
    must_phrase_rule = ""
    if must_phrase:
        must_phrase_rule = f'- Include this phrase exactly once across the subset: "{must_phrase}".\n'

    return f"""
You are an SEO copywriter and anti-AI-detection editor for locale {locale} (language: {lang}).

Rewrite ONLY the provided fields so they sound natural and human, without mechanical repetition.
Constraints:
- keep original meaning and casino vocabulary relevant to locale {locale}
- vary sentence length and rhythm
- each offender keyword listed below must appear AT LEAST once across the rewritten subset, naturally
{must_phrase_rule}- return ONLY valid JSON with exactly the same keys as the subset

Offender keywords (minimum presence required in subset):
[{offenders}]

Subset JSON:
{json.dumps(subset, ensure_ascii=False, indent=2)}
""".strip()


def run_full_humanize(env: Dict[str, str]) -> int:
    print("=== A3 Content Humanizer ===")
    locale, lang = require_locale_lang(env)
    must_phrase = (env.get("A3_MUST_INCLUDE_PHRASE") or "").strip()
    api_key = env.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("Missing ANTHROPIC_API_KEY in .env or env var.")

    in_path = ROOT / "output" / "content.json"
    if not in_path.exists():
        fallback = ROOT / "agents" / "a2-content" / "agents" / "a2-content" / "output" / "content.json"
        if fallback.exists():
            in_path.parent.mkdir(parents=True, exist_ok=True)
            in_path.write_text(fallback.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
        else:
            raise SystemExit(f"Input content.json not found at {in_path} (and fallback missing).")

    out_path = ROOT / "output" / "content_humanized.json"
    content = read_json(in_path)
    if not isinstance(content, dict):
        raise SystemExit("output/content.json must be a JSON object.")

    fields = HUMANIZE_FIELDS
    must_phrase_rule = ""
    if must_phrase:
        must_phrase_rule = f'- Include this phrase exactly once across rewritten fields: "{must_phrase}".\n'

    if content_format_version(content) < CONTENT_FORMAT_V2:
        assert_landing_fields(content, ["hero_title", *fields])
        home = landing_home_block(content)
        prompt = f"""
You are an SEO copywriter and anti-AI-detection editor for locale {locale} (language: {lang}).

Rewrite these texts so they sound genuinely human:
- natural style, varied sentence lengths, concrete vocabulary
- keep meaning and language aligned with locale {locale}
- avoid mechanical repetition and robotic marketing phrasing
- preserve relevant keywords already present
{must_phrase_rule}- do not add new sections; keep fluent paragraph style

Return ONLY valid JSON (no markdown) with exactly these keys:
{fields}

Input texts (JSON):
{json.dumps({k: home[k] for k in fields}, ensure_ascii=False, indent=2)}
""".strip()
        models = resolve_models(env)
        last_err: Optional[Exception] = None
        for model in models:
            try:
                res = call_anthropic(api_key=api_key, prompt=prompt, model=model, max_tokens=1800)
                obj = extract_json_from_text(res["text"])
                for k in fields:
                    if not isinstance(obj.get(k), str) or not obj[k].strip():
                        raise ValueError(f"Field {k} missing/empty in model output.")
                merged = merge_landing_field_updates(content, {k: obj[k] for k in fields})
                write_json(in_path, merged)
                write_json(out_path, humanized_snapshot(merged))
                html_path = resolve_a3_html_path(env)
                html = html_path.read_text(encoding="utf-8", errors="replace")
                html_path.write_text(apply_landing_content_to_html(html, landing_home_block(merged), env), encoding="utf-8")
                print(f"Saved: {out_path}")
                print("\n=== Comparison (original vs humanized, truncated) ===")
                for k in fields:
                    b, a = summarize_diff(str(home[k]), str(obj[k]))
                    print(f"\n[{k}]")
                    print("ORIG:", b)
                    print("NEW :", a)
                return 0
            except Exception as e:
                last_err = e
                time.sleep(0.4)
        raise SystemExit(str(last_err))

    models = resolve_models(env)
    last_err: Optional[Exception] = None
    for attempt in range(1, 4):
        try:
            merged = copy.deepcopy(content)
            pages_in = dict(merged.get("pages") or {})
            site_rel = default_site_dir(env).strip().strip("/").replace("\\", "/")
            site_prefix = site_rel + "/"

            def _page_belongs_to_site_dir(pdata: Any) -> bool:
                if not isinstance(pdata, dict):
                    return False
                th = str(pdata.get("target_html_path") or "").strip().replace("\\", "/")
                return bool(th) and th.startswith(site_prefix)

            pages_in = {pid: v for pid, v in pages_in.items() if _page_belongs_to_site_dir(v)}
            if not pages_in:
                raise SystemExit(
                    f"No v2 content pages with target_html_path under {site_prefix!r} — "
                    "check output/content.json and SITE_DIR."
                )

            def _page_order(pid: str) -> Tuple[int, str]:
                return (0, pid) if pid == "home" else (1, pid)

            for page_id in sorted(pages_in.keys(), key=_page_order):
                pdata = pages_in[page_id]
                if not isinstance(pdata, dict):
                    continue
                pk = str(pdata.get("page_kind") or "")
                if pk == "landing":
                    assert_landing_fields(merged, ["hero_title", *fields], page_id=page_id)
                    blk = landing_page_block(merged, page_id)
                    prompt = f"""
You are an SEO copywriter and anti-AI-detection editor for locale {locale} (language: {lang}).

Page id: {page_id}
Rewrite these texts so they sound genuinely human:
- natural style, varied sentence lengths, concrete vocabulary
- keep meaning and language aligned with locale {locale}
- avoid mechanical repetition and robotic marketing phrasing
- preserve relevant keywords already present
{must_phrase_rule}- do not add new sections; keep fluent paragraph style

Return ONLY valid JSON (no markdown) with exactly these keys:
{fields}

Input texts (JSON):
{json.dumps({k: blk[k] for k in fields}, ensure_ascii=False, indent=2)}
""".strip()
                    obj: Optional[Dict[str, Any]] = None
                    for model in models:
                        try:
                            res = call_anthropic(api_key=api_key, prompt=prompt, model=model, max_tokens=2400)
                            obj = extract_json_from_text(res["text"])
                            break
                        except Exception as e:
                            last_err = e
                            time.sleep(0.35)
                    if not obj:
                        raise RuntimeError(str(last_err or "model failed"))
                    for k in fields:
                        if not isinstance(obj.get(k), str) or not obj[k].strip():
                            raise ValueError(f"{page_id}: field {k} missing/empty in model output.")
                    merged = merge_landing_field_updates(merged, {k: obj[k] for k in fields}, page_id=page_id)
                    print(f"--- Humanized landing: {page_id} ---")
                    for k in fields:
                        b, a = summarize_diff(str(blk[k]), str(obj[k]))
                        print(f"[{page_id}.{k}] ORIG:", b, "\nNEW :", a)

            write_json(in_path, merged)
            write_json(out_path, humanized_snapshot(merged))

            for page_id, pdata in (merged.get("pages") or {}).items():
                if not isinstance(pdata, dict):
                    continue
                if not _page_belongs_to_site_dir(pdata):
                    continue
                th = str(pdata.get("target_html_path") or "").strip()
                if not th:
                    continue
                hp = (ROOT / th).resolve()
                if not hp.exists():
                    print(f"WARN: skip missing HTML for {page_id}: {th}")
                    continue
                doc = hp.read_text(encoding="utf-8", errors="replace")
                pk = str(pdata.get("page_kind") or "")
                if pk == "landing":
                    doc2 = apply_landing_content_to_html(doc, pdata, env)
                else:
                    doc2 = doc
                hp.write_text(doc2, encoding="utf-8")
                print(f"Updated HTML: {hp.relative_to(ROOT)}")

            print(f"Saved: {out_path}")
            return 0
        except Exception as e:
            last_err = e
            print(f"Attempt {attempt} failed: {e}")
            time.sleep(0.5 * attempt)

    raise SystemExit(str(last_err))


def run_recheck(env: Dict[str, str]) -> int:
    print("=== A3 Humanizer (recheck) ===")
    api_key = env.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("Missing ANTHROPIC_API_KEY in .env or env var.")

    content_path = ROOT / "output" / "content.json"
    prev_path = ROOT / "output" / "content_humanized.json"
    qa_path = ROOT / "output" / "qa_report.json"

    content = read_json(content_path)
    if not isinstance(content, dict):
        raise SystemExit("output/content.json must be a JSON object.")

    prev = read_json(prev_path) if prev_path.exists() and prev_path.stat().st_size > 2 else {}
    if not isinstance(prev, dict):
        prev = {}

    qa: Dict[str, Any] = read_json(qa_path) if qa_path.exists() else {}
    if not isinstance(qa, dict):
        qa = {}

    fields = HUMANIZE_FIELDS

    if content_format_version(content) < CONTENT_FORMAT_V2:
        offender_kws = offender_keywords_from_qa(qa)
        assert_landing_fields(content, ["hero_title", *fields])
        home = landing_home_block(content)
        changed_fields = [f for f in fields if str(home.get(f, "")).strip() != str(prev.get(f, "")).strip()]
        if not changed_fields:
            changed_fields = fields[:]
        subset = {k: home[k] for k in changed_fields}
        prompt = build_humanize_subset_prompt(changed_fields, subset, offender_kws, env)
        models = resolve_models(env)
        last_err: Optional[Exception] = None
        obj: Dict[str, Any] = {}
        for model in models:
            try:
                res = call_anthropic(api_key=api_key, prompt=prompt, model=model, max_tokens=2000)
                obj = extract_json_from_text(res["text"])
                for k in changed_fields:
                    if not isinstance(obj.get(k), str) or not obj[k].strip():
                        raise ValueError(f"Field {k} missing/empty in model output.")
                break
            except Exception as e:
                last_err = e
                time.sleep(0.4)
                obj = {}
        if not obj:
            raise SystemExit(str(last_err))
        merged = merge_landing_field_updates(content, {k: obj[k] for k in changed_fields})
        write_json(content_path, merged)
        out_path = ROOT / "output" / "content_humanized.json"
        write_json(out_path, humanized_snapshot(merged))
        html_path = resolve_a3_html_path(env)
        html_before = html_path.read_text(encoding="utf-8", errors="replace")
        counts_before = {k: count_kw_in_body(html_before, k) for k in offender_kws}
        html_path.write_text(apply_landing_content_to_html(html_before, landing_home_block(merged), env), encoding="utf-8")
        html_after = html_path.read_text(encoding="utf-8", errors="replace")
        counts_after = {k: count_kw_in_body(html_after, k) for k in offender_kws}
        for kw in offender_kws:
            if counts_after.get(kw, 0) < 1:
                raise SystemExit(f"Recheck validation failed: offender keyword missing after humanize: {kw}")
        for kw in offender_kws:
            b = int(counts_before.get(kw, 0))
            a = int(counts_after.get(kw, 0))
            print(f"✅ Density fixed: {kw}: было {b} раз → стало {a} раз")
        return 0

    prev_pages: Dict[str, Any] = {}
    if isinstance(prev.get("pages"), dict):
        prev_pages = prev["pages"]
    elif prev and any(k in prev for k in fields):
        prev_pages["home"] = prev

    merged = copy.deepcopy(content)
    models = resolve_models(env)
    last_err: Optional[Exception] = None

    for page_id, pdata in list((merged.get("pages") or {}).items()):
        if not isinstance(pdata, dict):
            continue
        pk = str(pdata.get("page_kind") or "")
        if pk != "landing":
            continue
        assert_landing_fields(merged, ["hero_title", *fields], page_id=page_id)
        blk = landing_page_block(merged, page_id)
        prev_blk = prev_pages.get(page_id) if isinstance(prev_pages.get(page_id), dict) else {}
        changed_fields = [f for f in fields if str(blk.get(f, "")).strip() != str(prev_blk.get(f, "")).strip()]
        if not changed_fields:
            changed_fields = fields[:]
        subset = {k: blk[k] for k in changed_fields}
        off = offender_keywords_for_page(qa, page_id)
        if not off and page_id == str(qa.get("meta", {}).get("primary_page_id") or ""):
            off = offender_keywords_from_qa(qa)
        prompt = build_humanize_subset_prompt(changed_fields, subset, off, env)
        obj: Dict[str, Any] = {}
        for model in models:
            try:
                res = call_anthropic(api_key=api_key, prompt=prompt, model=model, max_tokens=2400)
                obj = extract_json_from_text(res["text"])
                for k in changed_fields:
                    if not isinstance(obj.get(k), str) or not obj[k].strip():
                        raise ValueError(f"{page_id}: field {k} missing/empty in model output.")
                break
            except Exception as e:
                last_err = e
                time.sleep(0.4)
                obj = {}
        if not obj:
            raise SystemExit(f"{page_id}: {last_err!s}")
        merged = merge_landing_field_updates(merged, {k: obj[k] for k in changed_fields}, page_id=page_id)
        print(f"--- Recheck landing: {page_id} ---")

    write_json(content_path, merged)
    out_path = ROOT / "output" / "content_humanized.json"
    write_json(out_path, humanized_snapshot(merged))

    for page_id, pdata in (merged.get("pages") or {}).items():
        if not isinstance(pdata, dict):
            continue
        th = str(pdata.get("target_html_path") or "").strip()
        if not th:
            continue
        hp = (ROOT / th).resolve()
        if not hp.exists():
            continue
        doc = hp.read_text(encoding="utf-8", errors="replace")
        pk = str(pdata.get("page_kind") or "")
        if pk == "landing":
            hp.write_text(apply_landing_content_to_html(doc, pdata, env), encoding="utf-8")

    for p in qa.get("pages") or []:
        if not isinstance(p, dict):
            continue
        pid = str(p.get("page_id", "")).strip()
        if not pid:
            continue
        pdata = (merged.get("pages") or {}).get(pid)
        if not isinstance(pdata, dict):
            continue
        th = str(pdata.get("target_html_path") or "").strip()
        if not th:
            continue
        hp = (ROOT / th).resolve()
        if not hp.exists():
            continue
        html_after = hp.read_text(encoding="utf-8", errors="replace")
        for kw in offender_keywords_for_page(qa, pid):
            if count_kw_in_body(html_after, kw) < 1:
                raise SystemExit(f"Recheck validation failed on {pid}: offender keyword missing: {kw}")
            print(f"✅ {pid}: retained offender keyword {kw!r}")

    return 0


def main(argv: List[str]) -> int:
    env = load_env(ENV_PATH)
    for k, v in env.items():
        os.environ.setdefault(k, v)

    p = argparse.ArgumentParser()
    p.add_argument("--recheck", action="store_true")
    args = p.parse_args(argv)

    if args.recheck:
        return run_recheck(env)
    return run_full_humanize(env)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
