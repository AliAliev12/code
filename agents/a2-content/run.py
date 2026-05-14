#!/usr/bin/env python3
from __future__ import annotations

import html
import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests


ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT / ".env"
SITE_FACTORY_SPEC = ROOT / "agents" / "prompts" / "cazilla-site-factory-ru.md"

_AGENTS_DIR = ROOT / "agents"
if str(_AGENTS_DIR) not in sys.path:
    sys.path.insert(0, str(_AGENTS_DIR))

from _lib.keywords_bundle import (  # noqa: E402
    KeywordsBundle,
    PageKeywordTarget,
    parse_keywords_file,
    pick_target,
    resolve_site_html,
)

DEFAULT_MODEL = "claude-sonnet-4-20250514"
FALLBACK_MODEL = "claude-sonnet-4-6"

CONTENT_FORMAT_V1 = 1
CONTENT_FORMAT_V2 = 2

HOME_CONTENT_KEYS = [
    "hero_title",
    "hero_subtitle",
    "about_section",
    "bonus_section",
    "games_section",
    "footer_seo_text",
]

# Offerwall home: Cazilla #1 + four fictional brands; images assigned in code (see apply_content_to_offerwall_html).
FICTIONAL_OPERATORS_KEY = "fictional_operators"
OFFERWALL_TOP5_IMAGES = [
    "assets/pictures/casino-feature-visual.png",
    "assets/pictures/slots-showcase.png",
    "assets/pictures/live-tables.jpg",
    "assets/pictures/blackjack-green-table.jpg",
    "assets/pictures/baccarat-live-table.webp",
]
OFFERWALL_GALLERY_IMAGES = [
    "assets/pictures/crazy-time-bonus.jpg",
    "assets/pictures/money-train-4-thumbnail.png",
    "assets/pictures/baccarat-bonus-terms.webp",
    "assets/pictures/rocket-crash-game.png",
    "assets/pictures/big-bass-bonanza-review.avif",
    "assets/pictures/fruit-classic-slot.png",
    "assets/pictures/bonus-promo-artwork.webp",
    "assets/pictures/og-logo.svg",
]


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
    return site_dir or "sites/default-site"


def default_html_path(env: Dict[str, str]) -> Path:
    return ROOT / default_site_dir(env) / "index.html"


def require_locale_lang(env: Dict[str, str]) -> Tuple[str, str]:
    locale = (env.get("TARGET_LOCALE") or os.getenv("TARGET_LOCALE") or "").strip()
    lang = (env.get("TARGET_LANG") or os.getenv("TARGET_LANG") or "").strip()
    if not locale:
        raise SystemExit("Missing TARGET_LOCALE in .env/environment.")
    if not lang:
        raise SystemExit("Missing TARGET_LANG in .env/environment.")
    return locale, lang


def _candidate_keywords_paths() -> List[Path]:
    here = Path(__file__).resolve().parent
    site_dir = os.getenv("SITE_DIR", "").strip()
    site_kw = (ROOT / site_dir / "_output" / "keywords.json") if site_dir else None
    candidates: List[Path] = []
    if site_kw is not None:
        candidates.append(site_kw)
    candidates.extend(
        [
            ROOT / "agents" / "a1-keywords" / "agents" / "a1-keywords" / "output" / "keywords.json",
            here / "output" / "keywords.json",
            ROOT / "output" / "keywords.json",
        ]
    )
    return candidates


def resolve_keywords_json_path(env: Dict[str, str]) -> Path:
    for p in _candidate_keywords_paths():
        if p.exists():
            return p
    raise FileNotFoundError("keywords.json not found. Looked in:\n- " + "\n- ".join(str(p) for p in _candidate_keywords_paths()))


def load_bundle_and_target(env: Dict[str, str], page_id: Optional[str]) -> Tuple[KeywordsBundle, PageKeywordTarget, List[Dict[str, Any]]]:
    path = resolve_keywords_json_path(env)
    bundle = parse_keywords_file(path)
    pid = (page_id or env.get("PAGE_ID") or os.getenv("PAGE_ID") or "").strip() or None
    target = pick_target(bundle, pid)
    return bundle, target, target.rows


def load_keywords() -> List[Dict[str, Any]]:
    """Legacy helper: keyword rows for default target (backward compat)."""
    env = {**load_env(ENV_PATH), **os.environ}
    _, _, rows = load_bundle_and_target(env, page_id=None)
    return rows


def pick_keywords(kws: List[Dict[str, Any]]) -> Tuple[str, List[str], List[str]]:
    if not kws:
        raise ValueError("No keywords loaded")

    main = kws[0]["keyword"]
    remaining = [k["keyword"] for k in kws[1:]]

    about: List[str] = []
    for kw in remaining:
        if len(about) >= 7:
            break
        about.append(kw)
    if len(about) < 5:
        about = remaining[:5]

    footer = [kw for kw in remaining if kw not in set(about)]
    return main, about, footer


def anthropic_api_key(env: Dict[str, str]) -> str:
    return env.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or ""


def model_name(env: Dict[str, str]) -> str:
    return env.get("ANTHROPIC_MODEL") or os.getenv("ANTHROPIC_MODEL") or DEFAULT_MODEL


def site_factory_spec_enabled(env: Dict[str, str], *, cli_flag: bool) -> bool:
    if cli_flag:
        return True
    v = (env.get("A2_WITH_SITE_FACTORY_SPEC") or os.getenv("A2_WITH_SITE_FACTORY_SPEC") or "").strip().lower()
    return v in ("1", "true", "yes", "on")


def site_factory_spec_block(*, enabled: bool) -> str:
    if not enabled:
        return ""
    if not SITE_FACTORY_SPEC.exists():
        return (
            "\n\n(NOTE: Site factory spec file not found at "
            + str(SITE_FACTORY_SPEC)
            + "; continue without it.)\n"
        )
    body = SITE_FACTORY_SPEC.read_text(encoding="utf-8", errors="replace").strip()
    if not body:
        return ""
    return (
        "\n\n=== SITE FACTORY SPEC (full project rules; Russian) ===\n"
        + body
        + "\n=== END SITE FACTORY SPEC ===\n"
        "\nThe spec above applies to full multi-page HTML sites. For THIS API call you must still "
        "return ONLY the JSON object in the exact schema below (no markdown, no prose outside JSON). "
        "Within each string field: follow natural keyword use, locale tone, and constraints from the spec "
        "where they fit these fields; do not invent legal claims.\n"
    )


def extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    text = text.strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def call_anthropic(
    *,
    api_key: str,
    prompt: str,
    max_tokens: int = 1600,
    model: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    env = env or {}
    chosen = model or model_name(env)
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": chosen,
        "max_tokens": max_tokens,
        "temperature": 0.55,
        "messages": [{"role": "user", "content": prompt}],
    }
    r = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload, timeout=120)
    if r.status_code != 200:
        if r.status_code == 404 and chosen == DEFAULT_MODEL:
            try:
                err = r.json().get("error", {})
            except Exception:
                err = {}
            if isinstance(err, dict) and err.get("type") == "not_found_error" and "model" in str(err.get("message", "")):
                return call_anthropic(api_key=api_key, prompt=prompt, max_tokens=max_tokens, model=FALLBACK_MODEL, env=env)
        raise RuntimeError(f"Anthropic HTTP {r.status_code}: {r.text[:800]}")
    data = r.json()
    parts: List[str] = []
    for block in data.get("content", []) or []:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    text = "\n".join([p for p in parts if p]).strip()
    obj = extract_json_object(text)
    if not obj:
        raise RuntimeError("Model response was not valid JSON. Raw text:\n" + text[:1200])
    return obj


def build_prompt(
    main_kw: str,
    about_kws: List[str],
    footer_kws: List[str],
    kws: List[Dict[str, Any]],
    *,
    locale: str,
    lang: str,
    reserve_phrases: List[str],
    include_site_factory_spec: bool = False,
    home_offerwall_aggregator: bool = False,
) -> str:
    top = kws[:20]
    kw_lines = "\n".join(
        [f'- "{k["keyword"]}" (vol {k["search_volume"]}, KD {k["keyword_difficulty"]}, CPC {k["cpc"]})' for k in top]
    )
    spec = site_factory_spec_block(enabled=include_site_factory_spec)
    reserve_block = ""
    if reserve_phrases:
        reserve_block = (
            "\nReserve / supplemental phrases (site-wide list; use only where they fit the section intent).\n"
            "Do NOT place any reserve phrase in: hero_title, hero_subtitle, or any string that reads like a document title.\n"
            "Prefer weaving reserves into about_section / bonus_section / games_section / footer_seo_text only.\n"
            "Reserve list (exact wording when used):\n"
            + json.dumps(reserve_phrases[:40], ensure_ascii=False)
            + "\n"
        )
    role = (
        f"You are an SEO copywriter for locale {locale} (language: {lang}). Write original, natural copy for a Cazilla review-style casino site."
    )
    if home_offerwall_aggregator:
        role = (
            f"You are an SEO copywriter for locale {locale} (language: {lang}). "
            "This HOME page is an independent editorial aggregator that compares online casino options for Irish readers. "
            "Cazilla is always the featured #1 partner (do not demote it). "
            "You must invent exactly FOUR clearly fictional casino brand names for ranks #2–#5 (not real trademarks, not impersonations); "
            "short neutral summaries only—no fake licences, no 'official regulator' claims for those placeholders."
        )
    agg_block = ""
    json_tail = """Exact output format (JSON):
{{
  "hero_title": "...",
  "hero_subtitle": "...",
  "about_section": "...",
  "bonus_section": "...",
  "games_section": "...",
  "footer_seo_text": "..."
}}"""
    if home_offerwall_aggregator:
        agg_block = (
            "\nAdditionally output fictional_operators: an array of EXACTLY four objects for ranks #2–#5 (in rank order), each with:\n"
            '- "brand_name": short invented brand (clearly fictional, two–four words).\n'
            '- "tagline": one line, <= 90 chars.\n'
            '- "summary_sentence": one sentence, <= 220 chars; neutral editorial tone; no legal claims.\n'
        )
        json_tail = """Exact output format (JSON):
{{
  "hero_title": "...",
  "hero_subtitle": "...",
  "about_section": "...",
  "bonus_section": "...",
  "games_section": "...",
  "footer_seo_text": "...",
  "fictional_operators": [
    {{"brand_name": "...", "tagline": "...", "summary_sentence": "..."}},
    {{"brand_name": "...", "tagline": "...", "summary_sentence": "..."}},
    {{"brand_name": "...", "tagline": "...", "summary_sentence": "..."}},
    {{"brand_name": "...", "tagline": "...", "summary_sentence": "..."}}
  ]
}}"""
    return f"""
{role}
{spec}
Strict constraints:
- Return ONLY a valid JSON object (no markdown, no extra text).
- No misleading promises, no unverifiable legal/regulator claims.
- Neutral, informative, user-focused tone.
- Integrate keywords naturally; avoid stuffing.
- Length targets:
  - hero_title: H1 (<= 70 chars) and must contain main keyword.
  - hero_subtitle: 2-3 sentences.
  - about_section: 150-200 words, include 5-7 provided keywords.
  - bonus_section: 100-150 words.
  - games_section: 100-150 words.
  - footer_seo_text: 100-150 words, include as many remaining keywords as natural.
{reserve_block}
{agg_block}
Main keyword (H1): "{main_kw}"

Keywords for about_section (5-7):
{json.dumps(about_kws, ensure_ascii=False)}

Keywords for footer_seo_text (remaining):
{json.dumps(footer_kws, ensure_ascii=False)}

Keyword context (top 20 with metrics):
{kw_lines}

{json_tail}
""".strip()


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


def is_offerwall_html(html: str) -> bool:
    """CasinoRank IE static offerwall shell (sites/cazilla-offerwall*-en-ie)."""
    return bool(re.search(r'(?is)class="ow-hero"', html)) and bool(re.search(r'(?is)class="ow-prose"', html))


def site_dir_is_offerwall_aggregator(site_dir: Path) -> bool:
    s = str(site_dir).lower()
    if "offerwall" not in s:
        return False
    return (site_dir / "assets" / "pictures").is_dir()


def asset_href_for_html_page(page_rel: str, asset_site_rel: str) -> str:
    pr = str(page_rel or "").replace("\\", "/").lstrip("/")
    pdir = os.path.dirname(pr) or "."
    ar = str(asset_site_rel).replace("\\", "/").lstrip("/")
    return os.path.relpath(ar, pdir).replace("\\", "/")


def normalize_fictional_operators(raw: Any) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    if isinstance(raw, list):
        for it in raw:
            if not isinstance(it, dict):
                continue
            name = str(it.get("brand_name") or "").strip()
            tag = str(it.get("tagline") or "").strip()
            summ = str(it.get("summary_sentence") or "").strip()
            if not name or not summ:
                continue
            out.append({"brand_name": name, "tagline": tag, "summary_sentence": summ})
    idx = 1
    while len(out) < 4:
        out.append(
            {
                "brand_name": f"Sample operator {idx}",
                "tagline": "Editorial placeholder",
                "summary_sentence": "Fictional row for layout comparison only; not a licensed brand offer.",
            }
        )
        idx += 1
    return out[:4]


def build_offerwall_aggregator_sections_html(
    *,
    page_rel: str,
    env: Dict[str, str],
    fictional: List[Dict[str, str]],
) -> str:
    cta = _main_casino_cta_fragment(env) or ""
    cards_html: List[str] = []
    # #1 Cazilla
    img0 = html.escape(asset_href_for_html_page(page_rel, OFFERWALL_TOP5_IMAGES[0]))
    cards_html.append(
        '<article class="ow-topCard ow-topCard--featured">'
        '<div class="ow-topCardRank" aria-hidden="true">#1</div>'
        f'<div class="ow-topCardMedia"><img src="{img0}" alt="" width="480" height="300" loading="eager" decoding="async" /></div>'
        "<h3>Cazilla</h3>"
        '<p class="ow-topCardTag">Featured partner · Ireland-facing lobby</p>'
        "<p>Primary pick on this page: transparent promos, live tables, and cashier flows we can screenshot for readers.</p>"
        f'<p class="ow-topCardCta">{cta}</p>'
        "</article>"
    )
    for i in range(4):
        img = html.escape(asset_href_for_html_page(page_rel, OFFERWALL_TOP5_IMAGES[i + 1]))
        row = fictional[i]
        name = html.escape(row["brand_name"])
        tag = html.escape(row["tagline"]) if row.get("tagline") else ""
        summ = html.escape(row["summary_sentence"])
        tagline_html = f'<p class="ow-topCardTag">{tag}</p>' if tag else ""
        cards_html.append(
            f'<article class="ow-topCard">'
            f'<div class="ow-topCardRank" aria-hidden="true">#{i + 2}</div>'
            f'<div class="ow-topCardMedia"><img src="{img}" alt="" width="480" height="300" loading="lazy" decoding="async" /></div>'
            f"<h3>{name}</h3>"
            f"{tagline_html}"
            f"<p>{summ}</p>"
            "</article>"
        )

    gallery_items: List[str] = []
    for rel in OFFERWALL_GALLERY_IMAGES:
        href = html.escape(asset_href_for_html_page(page_rel, rel))
        base = rel.rsplit("/", 1)[-1]
        cap = html.escape(base.replace("-", " ").rsplit(".", 1)[0].title())
        gallery_items.append(
            f'<figure class="ow-galleryCell"><img src="{href}" alt="" width="360" height="220" loading="lazy" decoding="async" /><figcaption>{cap}</figcaption></figure>'
        )

    return (
        '<p class="ow-aggDisclaimer">Editorial shortlist for Ireland. <strong>#1 Cazilla</strong> is the featured outbound partner. '
        "Ranks #2–#5 are fictional placeholder brands used only to compare layout and copy patterns—they are not real licensed offers on this domain.</p>\n"
        '<div class="ow-topGrid">\n' + "\n".join(cards_html) + "\n</div>\n"
        '<h2 class="ow-galleryTitle">Lobby &amp; games reference art</h2>\n'
        '<div class="ow-galleryGrid">\n' + "\n".join(gallery_items) + "\n</div>\n"
    )


def _main_casino_cta_fragment(env: Dict[str, str]) -> str:
    url = (env.get("MAIN_CASINO_URL") or os.getenv("MAIN_CASINO_URL") or "").strip().rstrip("/")
    if not url:
        return ""
    esc = html.escape(url, quote=True)
    return f'<a href="{esc}" rel="noopener noreferrer" target="_blank">Open Cazilla</a>'


def apply_content_to_offerwall_html(html_doc: str, content: Dict[str, Any], env: Dict[str, str]) -> str:
    """
    Map A2 HOME_CONTENT_KEYS into offerwall layout: ow-hero, ow-prose, footer-legal.
    Preserves shell outside <article class="ow-prose">. Optional #ow-aggregator-top5 from fictional_operators.
    """
    hero_title = str(content.get("hero_title", "")).strip()
    hero_sub = str(content.get("hero_subtitle", "")).strip()
    bonus = str(content.get("bonus_section", "")).strip()
    games = str(content.get("games_section", "")).strip()
    about = str(content.get("about_section", "")).strip()
    footer = str(content.get("footer_seo_text", "")).strip()
    page_rel = str(content.get("site_rel_path") or "index.html").strip().lstrip("/")

    if FICTIONAL_OPERATORS_KEY in content:
        fict = normalize_fictional_operators(content.get(FICTIONAL_OPERATORS_KEY))
        inner = build_offerwall_aggregator_sections_html(page_rel=page_rel, env=env, fictional=fict)
        m_agg = re.search(r'(?is)<section\b[^>]*\bid=["\']ow-aggregator-top5["\'][^>]*>[\s\S]*?</section>', html_doc)
        block = (
            f'<section id="ow-aggregator-top5" class="ow-aggregatorTop5" aria-label="Top five picks">\n{inner}</section>'
        )
        if m_agg:
            html_doc = html_doc[: m_agg.start()] + block + html_doc[m_agg.end() :]
        else:
            html_doc = replace_first_submatch(
                html_doc,
                r'(?is)(<article\s+class="ow-prose"\s*>)',
                block + "\n" + r"\1",
            )

    if hero_title:
        html_doc = replace_first_submatch(
            html_doc,
            r'(?is)(<section\b[^>]*class="ow-hero"[^>]*>\s*<h1>)(.*?)(</h1>)',
            r"\g<1>" + html.escape(hero_title) + r"\g<3>",
        )

    if hero_sub:
        inner = html.escape(hero_sub)
        cta = _main_casino_cta_fragment(env)
        if cta and "Open Cazilla" not in hero_sub:
            inner = inner + " " + cta
        html_doc = replace_first_submatch(
            html_doc,
            r'(?is)(<section\b[^>]*class="ow-hero"[^>]*>[\s\S]*?<p class="ow-lead">\s*)([\s\S]*?)(\s*</p>)',
            r"\g<1>" + inner + r"\g<3>",
        )

    if about or bonus or games:
        parts: List[str] = []
        if about:
            parts.append(f"<h2>Overview</h2>\n<p>{about}</p>")
        if bonus:
            parts.append(f"<h2>Bonuses &amp; payments</h2>\n<p>{bonus}</p>")
        if games:
            parts.append(f"<h2>Games &amp; lobby</h2>\n<p>{games}</p>")
        parts.append(
            '<h2>Operator link</h2>\n'
            "<p>When you are ready to verify offers live, continue on the official site: "
            + (_main_casino_cta_fragment(env) or "")
            + "</p>"
        )
        article_body = "\n".join(parts) + "\n"
        html_doc = replace_first_submatch(
            html_doc,
            r'(?is)(<article\s+class="ow-prose"\s*>)([\s\S]*?)(</article>)',
            r"\g<1>\n" + article_body + r"\g<3>",
        )

    if footer:
        html_doc = replace_first_submatch(
            html_doc,
            r'(?is)(<section\s+id="footer-legal"\s*>\s*<p>\s*)([\s\S]*?)(\s*</p>\s*</section>)',
            r"\g<1>" + footer + r"\g<3>",
        )

    return html_doc


def apply_content_to_index_html(html: str, content: Dict[str, Any]) -> str:
    """
    Updates visible copy blocks in target site index.html using stable section anchors.
    """
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


def build_density_fix_prompt(
    *,
    full_html: str,
    offenders: List[Dict[str, Any]],
    current_content: Dict[str, Any],
    locale: str,
    lang: str,
    include_site_factory_spec: bool = False,
) -> str:
    off_lines = []
    for o in offenders:
        if not isinstance(o, dict):
            continue
        kw = str(o.get("keyword", "")).strip()
        if not kw:
            continue
        off_lines.append(f'- "{kw}"')
    off_block = "\n".join(off_lines) if off_lines else "- (none)"
    spec = site_factory_spec_block(enabled=include_site_factory_spec)

    return f"""
You are an SEO copywriter for locale {locale} (language: {lang}).
{spec}
Goal:
- Reduce repetition for keywords listed below in section texts.
- For EACH listed keyword: appear at MOST 3 times in all visible body text (excluding <head> and JSON-LD).
- Replace repetitions with natural rewrites/synonyms.
- Do not over-edit unrelated SEO keywords.
- Do not change HTML structure: return text fields only (no HTML).

Keywords to fix (QA offenders):
{off_block}

Current text (content.json):
{json.dumps({k: current_content.get(k, "") for k in ["hero_title","hero_subtitle","about_section","bonus_section","games_section","footer_seo_text"]}, ensure_ascii=False, indent=2)}

Full HTML page for context (do not output HTML):
{full_html}

Return ONLY valid JSON with exactly these keys:
{{
  "hero_title": "...",
  "hero_subtitle": "...",
  "about_section": "...",
  "bonus_section": "...",
  "games_section": "...",
  "footer_seo_text": "..."
}}
""".strip()


def run_generate(env: Dict[str, str], *, include_site_factory_spec: bool, page_id: Optional[str]) -> None:
    print("=== A2 Content Agent ===")
    if include_site_factory_spec:
        print("Site factory spec:", SITE_FACTORY_SPEC)

    bundle, target, kws = load_bundle_and_target(env, page_id)
    site_dir_s = default_site_dir(env)
    site_dir = ROOT / site_dir_s
    out_path = ROOT / "output" / "content.json"
    filter_pid = (page_id or env.get("PAGE_ID") or os.getenv("PAGE_ID") or "").strip() or None

    api_key = anthropic_api_key(env)
    if not api_key:
        raise SystemExit("Missing ANTHROPIC_API_KEY in .env or environment.")
    locale, lang = require_locale_lang(env)
    reserve_phrases = [r["keyword"] for r in bundle.reserve_rows]

    if bundle.version < 2:
        main_kw, about_kws, footer_kws = pick_keywords(kws)
        print("Keywords file:", bundle.source_path)
        print("Target page_id:", target.page_id, "path:", target.rel_path)
        print("Main keyword:", main_kw)
        print("About keywords:", len(about_kws))
        print("Footer keywords:", len(footer_kws))
        print("Reserve phrases:", len(bundle.reserve_rows))
        prompt = build_prompt(
            main_kw,
            about_kws,
            footer_kws,
            kws,
            locale=locale,
            lang=lang,
            reserve_phrases=reserve_phrases,
            include_site_factory_spec=include_site_factory_spec,
        )
        max_tokens = 4096 if include_site_factory_spec else 1800
        last_err: Optional[Exception] = None
        for attempt in range(1, 4):
            try:
                content = call_anthropic(api_key=api_key, prompt=prompt, max_tokens=max_tokens, env=env)
                missing = [k for k in HOME_CONTENT_KEYS if k not in content or not str(content.get(k, "")).strip()]
                if missing:
                    raise RuntimeError("Missing fields in response: " + ", ".join(missing))
                html_path = resolve_site_html(site_dir, target.rel_path)
                out_payload: Dict[str, Any] = {
                    "content_format_version": CONTENT_FORMAT_V1,
                    "keywords_bundle_version": bundle.version,
                    "target_page_id": target.page_id,
                    "target_html_path": str(html_path.relative_to(ROOT)),
                }
                for k in HOME_CONTENT_KEYS:
                    out_payload[k] = content[k]
                write_json(out_path, out_payload)
                print("Saved:", out_path)
                return
            except Exception as e:
                last_err = e
                time.sleep(1.5 * attempt)
                print(f"Attempt {attempt} failed: {e}")
        raise SystemExit(f"Failed after retries: {last_err}")

    # v2 bundle: per-target generation, content.json pages map
    pages_out: Dict[str, Any] = {}
    if out_path.exists():
        try:
            ex = read_json(out_path)
            if isinstance(ex, dict) and int(ex.get("content_format_version") or 0) == CONTENT_FORMAT_V2:
                po = ex.get("pages")
                if isinstance(po, dict):
                    pages_out = {k: dict(v) for k, v in po.items() if isinstance(v, dict)}
        except Exception:
            pass

    targets_run = list(bundle.targets)
    if filter_pid:
        targets_run = [t for t in bundle.targets if t.page_id == filter_pid]
        if not targets_run:
            raise SystemExit(f"PAGE_ID / --page-id={filter_pid!r} not found in keywords bundle targets.")

    print("Keywords file:", bundle.source_path, "(bundle v2)")
    print("Targets to generate:", ", ".join(f"{t.page_id}({t.rel_path})" for t in targets_run))
    print("Reserve phrases:", len(bundle.reserve_rows))

    last_err: Optional[Exception] = None
    for attempt in range(1, 4):
        try:
            for t in targets_run:
                print("--- Generating page_id:", t.page_id, "---")
                rows = t.rows
                main_kw, about_kws, footer_kws = pick_keywords(rows)
                print("  Main keyword:", main_kw)
                hp_probe = resolve_site_html(site_dir, t.rel_path)
                agg_home = (
                    t.page_id == "home"
                    and site_dir_is_offerwall_aggregator(site_dir)
                    and hp_probe.exists()
                    and is_offerwall_html(hp_probe.read_text(encoding="utf-8", errors="replace"))
                )
                prompt = build_prompt(
                    main_kw,
                    about_kws,
                    footer_kws,
                    rows,
                    locale=locale,
                    lang=lang,
                    reserve_phrases=reserve_phrases,
                    include_site_factory_spec=include_site_factory_spec,
                    home_offerwall_aggregator=agg_home,
                )
                if include_site_factory_spec and agg_home:
                    max_tokens = 6000
                elif include_site_factory_spec:
                    max_tokens = 4096
                elif agg_home:
                    max_tokens = 2400
                else:
                    max_tokens = 1800
                content = call_anthropic(api_key=api_key, prompt=prompt, max_tokens=max_tokens, env=env)
                missing = [k for k in HOME_CONTENT_KEYS if k not in content or not str(content.get(k, "")).strip()]
                if missing:
                    raise RuntimeError(f"page {t.page_id}: missing fields: " + ", ".join(missing))
                hp = resolve_site_html(site_dir, t.rel_path)
                page_obj: Dict[str, Any] = {k: content[k] for k in HOME_CONTENT_KEYS}
                page_obj["target_html_path"] = str(hp.relative_to(ROOT))
                page_obj["page_kind"] = "landing"
                page_obj["site_rel_path"] = str(t.rel_path or "").strip().lstrip("/")
                if agg_home:
                    page_obj[FICTIONAL_OPERATORS_KEY] = normalize_fictional_operators(
                        content.get(FICTIONAL_OPERATORS_KEY)
                    )
                pages_out[t.page_id] = page_obj

            out_payload = {
                "content_format_version": CONTENT_FORMAT_V2,
                "keywords_bundle_version": bundle.version,
                "pages": pages_out,
            }
            write_json(out_path, out_payload)
            print("Saved:", out_path)

            for t in targets_run:
                pdata = pages_out.get(t.page_id)
                if not isinstance(pdata, dict):
                    continue
                hp = resolve_site_html(site_dir, t.rel_path)
                html_in = hp.read_text(encoding="utf-8", errors="replace")
                if is_offerwall_html(html_in):
                    html_out = apply_content_to_offerwall_html(html_in, pdata, env)
                else:
                    html_out = apply_content_to_index_html(html_in, pdata)
                hp.write_text(html_out, encoding="utf-8")
                print("Updated:", hp)
            return
        except Exception as e:
            last_err = e
            time.sleep(1.5 * attempt)
            print(f"Attempt {attempt} failed: {e}")
    raise SystemExit(f"Failed after retries: {last_err}")


def run_fix_density(env: Dict[str, str], *, include_site_factory_spec: bool) -> None:
    print("=== A2 Content Agent (fix-density) ===")
    if include_site_factory_spec:
        print("Site factory spec:", SITE_FACTORY_SPEC)
    api_key = anthropic_api_key(env)
    if not api_key:
        raise SystemExit("Missing ANTHROPIC_API_KEY in .env or environment.")

    qa_path = ROOT / "output" / "qa_report.json"
    if not qa_path.exists():
        raise SystemExit(f"qa_report.json not found: {qa_path}")
    qa = read_json(qa_path)
    if not isinstance(qa, dict):
        raise SystemExit("qa_report.json must be an object")

    kd = qa.get("keyword_density") or {}
    offenders = kd.get("offenders") if isinstance(kd, dict) else None
    if not isinstance(offenders, list) or not offenders:
        print("No offenders in qa_report.keyword_density — nothing to do.")
        return

    content_path = ROOT / "output" / "content.json"
    if not content_path.exists():
        fallback = Path(__file__).resolve().parent / "output" / "content.json"
        if fallback.exists():
            content_path.write_text(fallback.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
        else:
            raise SystemExit(f"content.json not found at {content_path} (and fallback missing).")

    current = read_json(content_path)
    if not isinstance(current, dict):
        raise SystemExit("content.json must be an object")

    ver = int(current.get("content_format_version") or CONTENT_FORMAT_V1)
    home_block: Dict[str, Any]
    if ver >= CONTENT_FORMAT_V2:
        pages = current.get("pages")
        if not isinstance(pages, dict):
            raise SystemExit("v2 content.json must have a pages object.")
        hb = pages.get("home")
        if not isinstance(hb, dict):
            raise SystemExit("fix-density for v2 requires pages.home (landing) in content.json.")
        home_block = hb
        current_content = {k: str(home_block.get(k, "")) for k in HOME_CONTENT_KEYS}
    else:
        home_block = current
        current_content = {k: str(current.get(k, "")) for k in HOME_CONTENT_KEYS}

    qa_html_path = str((qa.get("meta") or {}).get("html_path") or "").strip()
    html_path: Optional[Path] = Path(qa_html_path) if qa_html_path else None
    if html_path is None or not html_path.exists():
        th = str(home_block.get("target_html_path") or current.get("target_html_path") or "").strip()
        if th:
            html_path = (ROOT / th).resolve()
    if html_path is None or not html_path.exists():
        html_path = default_html_path(env)
    if not html_path.exists():
        raise SystemExit(
            f"HTML path not found: {html_path}. "
            "Set SITE_DIR in .env/environment or provide qa_report.meta.html_path."
        )
    full_html = html_path.read_text(encoding="utf-8", errors="replace")

    locale, lang = require_locale_lang(env)
    prompt = build_density_fix_prompt(
        full_html=full_html,
        offenders=offenders,
        current_content=current_content,
        locale=locale,
        lang=lang,
        include_site_factory_spec=include_site_factory_spec,
    )
    max_tokens = 4500 if include_site_factory_spec else 2200
    fixed = call_anthropic(api_key=api_key, prompt=prompt, max_tokens=max_tokens, env=env)

    required = HOME_CONTENT_KEYS
    missing = [k for k in required if k not in fixed or not str(fixed.get(k, "")).strip()]
    if missing:
        raise SystemExit("Missing fields in fix-density response: " + ", ".join(missing))

    merged = dict(current)
    if ver >= CONTENT_FORMAT_V2:
        pages = dict(current.get("pages") or {})
        home = dict(pages.get("home") or {})
        for k in required:
            home[k] = fixed[k]
        pages["home"] = home
        merged["pages"] = pages
    else:
        merged.update({k: fixed[k] for k in required})
    for mk in ("content_format_version", "keywords_bundle_version", "target_page_id", "target_html_path"):
        if mk in current:
            merged[mk] = current[mk]
    write_json(content_path, merged)
    print("Updated:", content_path)

    if ver >= CONTENT_FORMAT_V2:
        apply_src = dict((merged.get("pages") or {}).get("home") or {})
    else:
        apply_src = merged
    new_html = apply_content_to_index_html(full_html, apply_src)
    html_path.write_text(new_html, encoding="utf-8")
    print("Updated:", html_path)

    a3 = ROOT / "agents" / "a3-ai-check" / "agents" / "a3-ai-check" / "run.py"
    print("\n=== Launching A3 --recheck ===")
    r = subprocess.run([sys.executable, str(a3), "--recheck"], cwd=str(ROOT), env=os.environ.copy())
    if r.returncode != 0:
        raise SystemExit(f"A3 recheck failed (exit {r.returncode})")


def main(argv: List[str]) -> int:
    env = load_env(ENV_PATH)
    # allow os.environ overrides too
    for k, v in env.items():
        os.environ.setdefault(k, v)

    p = argparse.ArgumentParser()
    p.add_argument("--fix-density", action="store_true")
    p.add_argument(
        "--with-site-factory-spec",
        action="store_true",
        help=f"Append {SITE_FACTORY_SPEC.relative_to(ROOT)} to the model prompt (or set A2_WITH_SITE_FACTORY_SPEC=1).",
    )
    p.add_argument(
        "--page-id",
        default="",
        help="keywords.json v2 page id (or set PAGE_ID). Defaults to first content page.",
    )
    args = p.parse_args(argv)

    use_factory = site_factory_spec_enabled(env, cli_flag=bool(args.with_site_factory_spec))
    page_id_arg = (args.page_id or "").strip() or None

    if args.fix_density:
        run_fix_density(env, include_site_factory_spec=use_factory)
        return 0

    run_generate(env, include_site_factory_spec=use_factory, page_id=page_id_arg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
