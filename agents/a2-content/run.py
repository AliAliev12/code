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
from _lib.locale_context import (  # noqa: E402
    LocaleContext,
    locale_context_from_env,
    require_locale_lang,
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

RESPONSE_CONTENT_KEYS = [
    "hero_title",
    "hero_subtitle",
    "intro_meta",
    "pros",
    "cons",
    "overview_section",
    "licence_section",
    "design_section",
    "bonus_section",
    "vip_section",
    "payments_section",
    "games_section",
    "comparison_section",
    "summary_section",
    "faq_section",
    "author_bio",
    "footer_seo_text",
]

CLONE_CONTENT_KEYS = [
    "meta_title",
    "meta_description",
    "page_h1",
    "page_lead",
    "main_seo_html",
    "footer_note",
]

OFFERWALL_SLOTS_CONTENT_KEYS = list(CLONE_CONTENT_KEYS)
PAGE_KIND_OFFERWALL_SLOTS = "offerwall_slots"

OFFERWALL_BONUS_EXTRA_KEYS = ["expert_callout", "faq_section"]
OFFERWALL_BONUS_CONTENT_KEYS = list(CLONE_CONTENT_KEYS) + OFFERWALL_BONUS_EXTRA_KEYS
PAGE_KIND_OFFERWALL_BONUS = "offerwall_bonus"

OFFERWALL_ABOUT_CONTENT_KEYS = list(CLONE_CONTENT_KEYS)
PAGE_KIND_OFFERWALL_ABOUT = "offerwall_about"

REVIEW_LOBBY_CONTENT_KEYS = list(CLONE_CONTENT_KEYS)
PAGE_KIND_REVIEW_LOBBY = "review_lobby"

CLONE_SEO_MIN_CHARS = 1800
CLONE_SEO_MAX_CHARS = 3200
OFFERWALL_SLOTS_SEO_MIN_CHARS = 1600
OFFERWALL_SLOTS_SEO_MAX_CHARS = 2800
OFFERWALL_BONUS_SEO_MIN_CHARS = 1400
OFFERWALL_BONUS_SEO_MAX_CHARS = 2600
OFFERWALL_ABOUT_SEO_MIN_CHARS = 1400
OFFERWALL_ABOUT_SEO_MAX_CHARS = 2800

TECHNICAL_CONTENT_KEYS = [
    "meta_title",
    "meta_description",
    "hero_h1",
    "hero_subtitle",
    "body_html",
]

TECHNICAL_BODY_MIN_CHARS = 1500
TECHNICAL_BODY_MAX_CHARS = 3000
TECHNICAL_META_TITLE_MIN = 55
TECHNICAL_META_TITLE_MAX = 60
TECHNICAL_META_DESC_MAX = 140

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


def _candidate_keywords_paths(env: Optional[Dict[str, str]] = None) -> List[Path]:
    here = Path(__file__).resolve().parent
    e = env or {}
    site_dir = (e.get("SITE_DIR") or os.getenv("SITE_DIR") or "").strip()
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
    for p in _candidate_keywords_paths(env):
        if p.exists():
            return p
    raise FileNotFoundError(
        "keywords.json not found. Looked in:\n- " + "\n- ".join(str(p) for p in _candidate_keywords_paths(env))
    )


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


def pick_keywords_offerwall_sections(
    kws: List[Dict[str, Any]],
) -> Tuple[str, List[str], List[str], List[str], List[str]]:
    """Split page keywords across about / bonus / games for offerwall HOME hub."""
    if not kws:
        raise ValueError("No keywords loaded")
    main = kws[0]["keyword"]
    remaining = [k["keyword"] for k in kws[1:]]
    about: List[str] = []
    bonus: List[str] = []
    games: List[str] = []
    for i, kw in enumerate(remaining):
        bucket = i % 3
        if bucket == 0:
            about.append(kw)
        elif bucket == 1:
            bonus.append(kw)
        else:
            games.append(kw)
    return main, about, bonus, games, []


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
    if text.startswith("```"):
        text = re.sub(r"(?is)^```(?:json)?\s*", "", text)
        text = re.sub(r"(?is)\s*```\s*$", "", text).strip()
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
    lc: LocaleContext,
    reserve_phrases: List[str],
    include_site_factory_spec: bool = False,
    home_offerwall_aggregator: bool = False,
    home_offerwall_hub: bool = False,
    bonus_kws: Optional[List[str]] = None,
    games_kws: Optional[List[str]] = None,
    home_response: bool = False,
) -> str:
    locale, lang = lc.locale, lc.lang
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
    if home_response:
        role = (
            f"You are an SEO copywriter for locale {locale} (language: {lang}). "
            "Write an independent expert test-drive review of the Cazilla online casino for readers in the target region. "
            "Tone: methodical, fair, safety-first; mention licence checks, bonus wagering, payments, and game catalogue."
        )
    length_constraints = """- Length targets:
  - hero_title: H1 (<= 70 chars) and must contain main keyword.
  - hero_subtitle: 2-3 sentences.
  - about_section: 150-200 words, include 5-7 provided keywords.
  - bonus_section: 100-150 words.
  - games_section: 100-150 words.
  - footer_seo_text: 100-150 words, include as many remaining keywords as natural."""
    if include_site_factory_spec:
        length_constraints = f"""- Length targets (site factory; {lc.region_name} {lc.locale} editorial player review of Cazilla):
  - hero_title: plain text only, <= 70 chars, must start with the main keyword (capital first letter).
  - hero_subtitle: 650-950 characters. State that this page is an independent player review focused on Cazilla. Allowed inline HTML: <strong>exact keyword phrases</strong>, <br><br> between short paragraphs only.
  - about_section: 1400-2000 characters. Include EVERY keyword from the full Keyword context list at least once as exact wording. Wrap each keyword phrase in <strong>...</strong> on its first occurrence only. Separate keyword mentions by at least one full sentence; aim for roughly 250-400 characters between occurrences when practical.
  - bonus_section: 950-1400 characters. Cover any keywords not yet used in prior fields with the same <strong> and sentence-spacing rules; if all are already used, deepen {lc.player_context_phrase} without stuffing.
  - games_section: 950-1400 characters; same rules; distribute any remaining keywords.
  - footer_seo_text: 750-1100 characters; independent review disclaimer; weave any keywords not yet used at least once if still missing from earlier fields."""
    if home_response:
        length_constraints = """- Length targets (expert single-page Cazilla response review):
  - hero_title: plain text, <= 70 chars, must start with the main keyword (capital first letter).
  - hero_subtitle: 650-950 characters. Independent expert test-drive of Cazilla. Allowed inline HTML: <strong>exact keyword phrases</strong>, <br><br> between short paragraphs only.
  - intro_meta: 120-220 characters plain text (launch year, platform type, licence jurisdiction) — no HTML.
  - pros: JSON array of 3-5 short strings (advantages), each <= 120 chars, no HTML.
  - cons: JSON array of 2-4 short strings (drawbacks), each <= 120 chars, no HTML.
  - overview_section, licence_section, design_section, bonus_section, vip_section, payments_section, games_section, comparison_section, summary_section: each 900-1400 characters. Include EVERY keyword from the list at least once; wrap first occurrence of each keyword in <strong>...</strong>; separate keyword mentions by at least one full sentence.
  - faq_section: JSON array of 3-5 objects with "question" and "answer" keys; answers 80-180 chars each; distribute remaining keywords naturally.
  - author_bio: 280-450 characters plain text about the lead reviewer (no fake credentials).
  - footer_seo_text: 750-1100 characters; independent review disclaimer; weave any keywords not yet used."""
    if home_offerwall_aggregator:
        role = (
            f"You are an SEO copywriter for locale {locale} (language: {lang}). "
            f"This HOME page is an independent editorial aggregator that compares online casino options for {lc.audience_phrase}. "
            "Cazilla is always the featured #1 partner (do not demote it). "
            "You must invent exactly FOUR clearly fictional casino brand names for ranks #2–#5 (not real trademarks, not impersonations); "
            "short neutral summaries only—no fake licences, no 'official regulator' claims for those placeholders."
        )
    if home_offerwall_hub:
        length_constraints = f"""- Length targets (offerwall HOME hub, {lc.region_name}):
  - hero_title: plain text, <= 70 chars, must contain main keyword.
  - hero_subtitle: 450-700 characters. Independent editorial aggregator; allowed HTML: <strong>exact keyword phrases</strong>, <br><br> between short paragraphs only.
  - about_section: 900-1300 characters. H2 theme: positioning / why Cazilla leads. Include EVERY keyword listed for about_section at least once; wrap first occurrence in <strong>...</strong>.
  - bonus_section: 700-1000 characters. H2 theme: bonuses and payments. Include EVERY keyword listed for bonus_section at least once with the same <strong> rule.
  - games_section: 700-1000 characters. H2 theme: games lobby and slots. Include EVERY keyword listed for games_section at least once with the same <strong> rule.
  - faq_section: JSON array of 5-6 objects with "question" and "answer" keys; answers 90-200 chars; neutral editorial tone.
  - footer_seo_text: 120-220 characters; short independent-review disclaimer only (no keyword stuffing)."""
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
        if home_offerwall_hub:
            json_tail = """Exact output format (JSON):
{{
  "hero_title": "...",
  "hero_subtitle": "...",
  "about_section": "...",
  "bonus_section": "...",
  "games_section": "...",
  "footer_seo_text": "...",
  "faq_section": [
    {{"question": "...", "answer": "..."}}
  ],
  "fictional_operators": [
    {{"brand_name": "...", "tagline": "...", "summary_sentence": "..."}},
    {{"brand_name": "...", "tagline": "...", "summary_sentence": "..."}},
    {{"brand_name": "...", "tagline": "...", "summary_sentence": "..."}},
    {{"brand_name": "...", "tagline": "...", "summary_sentence": "..."}}
  ]
}}"""
        else:
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
    if home_response:
        json_tail = """Exact output format (JSON):
{{
  "hero_title": "...",
  "hero_subtitle": "...",
  "intro_meta": "...",
  "pros": ["...", "..."],
  "cons": ["...", "..."],
  "overview_section": "...",
  "licence_section": "...",
  "design_section": "...",
  "bonus_section": "...",
  "vip_section": "...",
  "payments_section": "...",
  "games_section": "...",
  "comparison_section": "...",
  "summary_section": "...",
  "faq_section": [
    {{"question": "...", "answer": "..."}},
    {{"question": "...", "answer": "..."}}
  ],
  "author_bio": "...",
  "footer_seo_text": "..."
}}"""
    hub_kw_block = ""
    if home_offerwall_hub:
        hub_kw_block = (
            "\nKeywords for bonus_section:\n"
            + json.dumps(bonus_kws or [], ensure_ascii=False)
            + "\nKeywords for games_section:\n"
            + json.dumps(games_kws or [], ensure_ascii=False)
        )
    return f"""
{role}
{spec}
Strict constraints:
- Return ONLY a valid JSON object (no markdown, no extra text).
- No misleading promises, no unverifiable legal/regulator claims.
- Neutral, informative, user-focused tone.
- Integrate keywords naturally; avoid stuffing.
{length_constraints}
{reserve_block}
{agg_block}
Main keyword (H1): "{main_kw}"

Keywords for about_section (5-7):
{json.dumps(about_kws, ensure_ascii=False)}

Keywords for footer_seo_text (remaining):
{json.dumps(footer_kws, ensure_ascii=False)}
{hub_kw_block}

Keyword context (top 20 with metrics):
{kw_lines}

{json_tail}
""".strip()


def clone_page_focus(page_id: str, lc: LocaleContext) -> str:
    region, aud = lc.region_name, lc.audience_phrase
    templates: Dict[str, str] = {
        "home": f"casino lobby home hub for {region} — overview, mobile play, real-money context, links to sections",
        "slots": "online slots lobby — slot providers, RTP context, welcome spins, mobile play",
        "live-games": f"live dealer roulette, blackjack, baccarat and game shows for {aud}",
        "live-casino": f"live casino online — roulette, blackjack, baccarat, game shows for {aud}",
        "casino-games": "table games and video poker — roulette, blackjack, poker variants",
        "about": f"about this editorial hub — independence, reviews, payouts, safer play for {region}",
        "bonus": "active bonuses, promo codes, wagering and free spins on licensed sites",
        "welcome-bonus": (
            f"welcome bonus for {region} — match offers, free spins, wagering rules, "
            "min deposit, how to claim on licensed sites"
        ),
        "bonuses-promo": "promotions hub — welcome packages, reload, cashback, tournaments, VIP",
    }
    return templates.get(page_id, page_id.replace("-", " "))


def _clone_kw_lines(rows: List[Dict[str, Any]]) -> Tuple[str, str, List[Dict[str, Any]]]:
    kws = [str(r.get("keyword", "")).strip() for r in rows if str(r.get("keyword", "")).strip()]
    if not kws:
        raise ValueError("clone page: no keywords")
    main_kw = kws[0]
    kw_lines = "\n".join(
        f'- "{r["keyword"]}" (vol {r.get("search_volume", 0)}, KD {r.get("keyword_difficulty", 0)})'
        for r in rows
        if str(r.get("keyword", "")).strip()
    )
    return main_kw, kw_lines, rows


def build_clone_meta_prompt(
    *,
    page_id: str,
    menu_label: str,
    rows: List[Dict[str, Any]],
    lc: LocaleContext,
    site_voice: str = "",
) -> str:
    main_kw, kw_lines, _ = _clone_kw_lines(rows)
    focus = clone_page_focus(page_id, lc)
    voice = site_voice or f"Cazilla lobby clone — independent editorial for {lc.region_name}"
    return f"""
You are an SEO copywriter for locale {lc.locale} (language: {lc.lang}).
Site voice: {voice}
Casino-lobby STYLE editorial hub (not the real cashier). Page: {menu_label} ({page_id}). Focus: {focus}.

Return ONLY valid JSON (no markdown fences):
{{
  "meta_title": "...",
  "meta_description": "...",
  "page_h1": "...",
  "page_lead": "...",
  "footer_note": "..."
}}

- meta_title: 55-60 chars, period at end, main keyword near start.
- meta_description: <= 140 chars, period at end, must not repeat meta_title opening.
- page_h1: plain text <= 70 chars, contains main keyword.
- page_lead: 280-450 chars; HTML allowed: <strong>, <br><br> only.
- footer_note: 80-160 chars plain text, 18+ responsible gambling disclaimer for {lc.audience_phrase}.

Main keyword: "{main_kw}"
Keywords (for lead only): {kw_lines}
""".strip()


def build_clone_seo_prompt(
    *,
    page_id: str,
    menu_label: str,
    rows: List[Dict[str, Any]],
    lc: LocaleContext,
    include_site_factory_spec: bool = False,
    site_voice: str = "",
) -> str:
    main_kw, kw_lines, _ = _clone_kw_lines(rows)
    focus = clone_page_focus(page_id, lc)
    spec = site_factory_spec_block(enabled=include_site_factory_spec)
    voice = site_voice or f"Cazilla lobby clone — independent editorial for {lc.region_name}"
    return f"""
You are an SEO copywriter for locale {lc.locale} (language: {lc.lang}).
Site voice: {voice}
{spec}
Page: {menu_label} ({page_id}). Focus: {focus}.

Return ONLY valid JSON (no markdown fences):
{{"main_seo_html": "..."}}

main_seo_html rules:
- 1900-3000 visible characters of HTML inside the JSON string (escape quotes as \\" ).
- Use <h2>, <p>, <ul><li>; no <h1>.
- Include EVERY keyword below at least once (exact wording). First occurrence of each in <strong>...</strong>.
- At least one full sentence between keyword mentions. {lc.player_context_phrase}. 18+ responsible play. No false licence claims.

Main keyword: "{main_kw}"

Keyword list:
{kw_lines}
""".strip()


def build_offerwall_slots_meta_prompt(
    *,
    menu_label: str,
    rows: List[Dict[str, Any]],
    lc: LocaleContext,
    site_voice: str = "",
) -> str:
    main_kw, kw_lines, _ = _clone_kw_lines(rows)
    voice = site_voice or f"Cazilla Belgique — catalogue slots éditorial pour {lc.region_name}"
    if lc.lang != "fr":
        voice = site_voice or f"Cazilla offerwall — slots catalogue for {lc.region_name}"
    return f"""
You are an SEO copywriter for locale {lc.locale} (language: {lc.lang}).
Site voice: {voice}
Page: {menu_label} (slots catalogue with finder UI and editorial guide).

Return ONLY valid JSON (no markdown fences):
{{
  "meta_title": "...",
  "meta_description": "...",
  "page_h1": "...",
  "page_lead": "...",
  "footer_note": "..."
}}

- meta_title: 55-60 chars, period at end, main keyword near start.
- meta_description: <= 140 chars, period at end.
- page_h1: plain text <= 72 chars, must contain main keyword.
- page_lead: 450-750 chars; independent editorial slots hub for {lc.audience_phrase}; HTML: <strong>, <br><br> only; weave page keywords naturally.
- footer_note: 80-180 chars plain text, 21+ responsible play for {lc.audience_phrase}.

Main keyword: "{main_kw}"
Keywords (lead + SEO): {kw_lines}
""".strip()


def build_offerwall_slots_seo_prompt(
    *,
    menu_label: str,
    rows: List[Dict[str, Any]],
    lc: LocaleContext,
    include_site_factory_spec: bool = False,
    site_voice: str = "",
) -> str:
    main_kw, kw_lines, _ = _clone_kw_lines(rows)
    spec = site_factory_spec_block(enabled=include_site_factory_spec)
    voice = site_voice or f"Cazilla Belgique — hub machines à sous pour {lc.region_name}"
    if lc.lang != "fr":
        voice = site_voice or f"Cazilla offerwall slots hub for {lc.region_name}"
    if lc.lang == "fr":
        h2_guide = """
Required <h2> sections (use these titles exactly, in this order):
1. Comment fonctionne une machine à sous en ligne ?
2. Symboles, wilds et scatters sur les slots
3. Bonus, free spins et achat de bonus
4. Types de machines : lignes, Megaways et cluster pays
5. Jouer gratuitement ou en argent réel sur Cazilla
"""
    else:
        h2_guide = """
Required <h2> sections (exact titles, in order):
1. How does an online slot work?
2. Symbols, wilds and scatters
3. Bonuses, free spins and buy-a-bonus
4. Slot types: paylines, Megaways and cluster pays
5. Free play vs real money on Cazilla
"""
    return f"""
You are an SEO copywriter for locale {lc.locale} (language: {lc.lang}).
Site voice: {voice}
{spec}
Page: {menu_label} — slots finder catalogue (editorial, not a live game database).

Return ONLY valid JSON:
{{"main_seo_html": "..."}}

main_seo_html rules:
- {OFFERWALL_SLOTS_SEO_MIN_CHARS}-{OFFERWALL_SLOTS_SEO_MAX_CHARS} visible characters.
- HTML: <h2>, <p>, optional <ul><li>; no <h1>.
- Include EVERY keyword below at least once (exact wording). First occurrence of each in <strong>...</strong>.
- At least one full sentence between keyword mentions. No false licence claims. 21+ responsible play for Belgium when relevant.
{h2_guide}

Main keyword: "{main_kw}"

Keyword list:
{kw_lines}
""".strip()


def generate_offerwall_slots_page_content(
    *,
    api_key: str,
    menu_label: str,
    rows: List[Dict[str, Any]],
    lc: LocaleContext,
    include_site_factory_spec: bool,
    site_voice: str,
    env: Dict[str, str],
) -> Dict[str, Any]:
    meta = call_anthropic(
        api_key=api_key,
        prompt=build_offerwall_slots_meta_prompt(
            menu_label=menu_label, rows=rows, lc=lc, site_voice=site_voice
        ),
        max_tokens=1200,
        env=env,
    )
    seo = call_anthropic(
        api_key=api_key,
        prompt=build_offerwall_slots_seo_prompt(
            menu_label=menu_label,
            rows=rows,
            lc=lc,
            include_site_factory_spec=include_site_factory_spec,
            site_voice=site_voice,
        ),
        max_tokens=6000 if include_site_factory_spec else 3200,
        env=env,
    )
    out = {**meta, **seo}
    normalize_offerwall_slots_content(out, rows, lc)
    return out


def normalize_offerwall_slots_content(
    content: Dict[str, Any], rows: List[Dict[str, Any]], lc: LocaleContext
) -> None:
    normalize_clone_content(content, rows, lc)
    content["main_seo_html"] = fit_clone_seo_html(str(content.get("main_seo_html", "")))
    content["main_seo_html"] = inject_missing_clone_keywords(
        str(content.get("main_seo_html", "")), rows, lc
    )


def validate_offerwall_slots_content(
    content: Dict[str, Any], rows: List[Dict[str, Any]], lc: LocaleContext
) -> None:
    normalize_offerwall_slots_content(content, rows, lc)
    missing = missing_clone_fields(content)
    if missing:
        raise RuntimeError("Missing offerwall_slots fields: " + ", ".join(missing))
    n = visible_text_len(str(content.get("main_seo_html", "")))
    if n < OFFERWALL_SLOTS_SEO_MIN_CHARS:
        raise RuntimeError(f"main_seo_html too short: {n} < {OFFERWALL_SLOTS_SEO_MIN_CHARS}")


def build_offerwall_bonus_meta_prompt(
    *,
    menu_label: str,
    rows: List[Dict[str, Any]],
    lc: LocaleContext,
    site_voice: str = "",
) -> str:
    main_kw, kw_lines, _ = _clone_kw_lines(rows)
    voice = site_voice or f"Cazilla Belgique — hub bonus casino pour {lc.region_name}"
    if lc.lang != "fr":
        voice = site_voice or f"Cazilla offerwall — bonus hub for {lc.region_name}"
    return f"""
You are an SEO copywriter for locale {lc.locale} (language: {lc.lang}).
Site voice: {voice}
Page: {menu_label} (bonus catalogue hub with comparison table and editorial guide).

Return ONLY valid JSON (no markdown fences):
{{
  "meta_title": "...",
  "meta_description": "...",
  "page_h1": "...",
  "page_lead": "...",
  "footer_note": "...",
  "expert_callout": "...",
  "faq_section": [
    {{"question": "...", "answer": "..."}}
  ]
}}

- meta_title: 55-60 chars, period at end, main keyword near start.
- meta_description: <= 140 chars, period at end.
- page_h1: plain text <= 72 chars, must contain main keyword.
- page_lead: 450-750 chars; independent editorial bonus hub for {lc.audience_phrase}; HTML: <strong>, <br><br> only; weave page keywords naturally.
- footer_note: 80-180 chars plain text, 21+ responsible play for {lc.audience_phrase}.
- expert_callout: 220-420 chars plain text (one editorial paragraph, no HTML); warn that headline bonus size is not the only metric — mention wagering, max bet, eligible games.
- faq_section: JSON array of 5-6 objects; answers 90-200 chars; neutral editorial tone; distribute remaining keywords where natural.

Main keyword: "{main_kw}"
Keywords (lead + SEO + FAQ): {kw_lines}
""".strip()


def build_offerwall_bonus_seo_prompt(
    *,
    menu_label: str,
    rows: List[Dict[str, Any]],
    lc: LocaleContext,
    include_site_factory_spec: bool = False,
    site_voice: str = "",
) -> str:
    main_kw, kw_lines, _ = _clone_kw_lines(rows)
    spec = site_factory_spec_block(enabled=include_site_factory_spec)
    voice = site_voice or f"Cazilla Belgique — guide bonus pour {lc.region_name}"
    if lc.lang != "fr":
        voice = site_voice or f"Cazilla offerwall bonus guide for {lc.region_name}"
    if lc.lang == "fr":
        h2_guide = """
Required structure (exact <h2> titles and id attributes):
1. <h2 id="ow-bonus-welcome">Conditions et wagering des bonus casino en ligne</h2> — explain playthrough, max bet, expiry; 2-3 <p>.
2. <h2 id="ow-bonus-nodeposit">Types de bonus : bienvenue, sans dépôt, cashback et fidélité</h2> — then three <h3 id="ow-bonus-reload">Bonus reload et promotions récurrentes</h3>, <h3 id="ow-bonus-cashback">Cashback et programme VIP</h3>, <h3 id="ow-bonus-vip">Fidélité et tours gratuits</h3> with <p> under each.
"""
    else:
        h2_guide = """
Required structure (exact <h2> titles and id attributes):
1. <h2 id="ow-bonus-welcome">Online casino bonus terms and wagering</h2> — 2-3 <p>.
2. <h2 id="ow-bonus-nodeposit">Bonus types: welcome, no deposit, cashback and loyalty</h2> — then <h3 id="ow-bonus-reload">Reload promos</h3>, <h3 id="ow-bonus-cashback">Cashback and VIP</h3>, <h3 id="ow-bonus-vip">Loyalty and free spins</h3> with <p> under each.
"""
    return f"""
You are an SEO copywriter for locale {lc.locale} (language: {lc.lang}).
Site voice: {voice}
{spec}
Page: {menu_label} — bonus hub (editorial, not a live promo feed).

Return ONLY valid JSON:
{{"main_seo_html": "..."}}

main_seo_html rules:
- {OFFERWALL_BONUS_SEO_MIN_CHARS}-{OFFERWALL_BONUS_SEO_MAX_CHARS} visible characters.
- HTML: <h2>, <h3>, <p>, optional <ul><li>; no <h1>.
- Include EVERY keyword below at least once (exact wording). First occurrence of each in <strong>...</strong>.
- At least one full sentence between keyword mentions. No false licence claims. 21+ responsible play for Belgium when relevant.
{h2_guide}

Main keyword: "{main_kw}"

Keyword list:
{kw_lines}
""".strip()


def generate_offerwall_bonus_page_content(
    *,
    api_key: str,
    menu_label: str,
    rows: List[Dict[str, Any]],
    lc: LocaleContext,
    include_site_factory_spec: bool,
    site_voice: str,
    env: Dict[str, str],
) -> Dict[str, Any]:
    meta = call_anthropic(
        api_key=api_key,
        prompt=build_offerwall_bonus_meta_prompt(
            menu_label=menu_label, rows=rows, lc=lc, site_voice=site_voice
        ),
        max_tokens=2000,
        env=env,
    )
    seo = call_anthropic(
        api_key=api_key,
        prompt=build_offerwall_bonus_seo_prompt(
            menu_label=menu_label,
            rows=rows,
            lc=lc,
            include_site_factory_spec=include_site_factory_spec,
            site_voice=site_voice,
        ),
        max_tokens=6000 if include_site_factory_spec else 3200,
        env=env,
    )
    out = {**meta, **seo}
    normalize_offerwall_bonus_content(out, rows, lc)
    return out


def normalize_offerwall_bonus_content(
    content: Dict[str, Any], rows: List[Dict[str, Any]], lc: LocaleContext
) -> None:
    normalize_clone_content(content, rows, lc)
    content["main_seo_html"] = fit_clone_seo_html(str(content.get("main_seo_html", "")))
    content["main_seo_html"] = inject_missing_clone_keywords(
        str(content.get("main_seo_html", "")), rows, lc
    )
    content["expert_callout"] = str(content.get("expert_callout", "")).strip()


def missing_offerwall_bonus_fields(content: Dict[str, Any]) -> List[str]:
    missing = missing_clone_fields(content)
    if not str(content.get("expert_callout", "")).strip():
        missing.append("expert_callout")
    faq = content.get("faq_section")
    if not isinstance(faq, list) or len(faq) < 5:
        missing.append("faq_section")
    else:
        ok = sum(
            1
            for it in faq
            if isinstance(it, dict)
            and str(it.get("question", "")).strip()
            and str(it.get("answer", "")).strip()
        )
        if ok < 5:
            missing.append("faq_section")
    return missing


def validate_offerwall_bonus_content(
    content: Dict[str, Any], rows: List[Dict[str, Any]], lc: LocaleContext
) -> None:
    normalize_offerwall_bonus_content(content, rows, lc)
    missing = missing_offerwall_bonus_fields(content)
    if missing:
        raise RuntimeError("Missing offerwall_bonus fields: " + ", ".join(missing))
    n = visible_text_len(str(content.get("main_seo_html", "")))
    if n < OFFERWALL_BONUS_SEO_MIN_CHARS:
        raise RuntimeError(f"main_seo_html too short: {n} < {OFFERWALL_BONUS_SEO_MIN_CHARS}")


def build_offerwall_about_meta_prompt(
    *,
    menu_label: str,
    rows: List[Dict[str, Any]],
    lc: LocaleContext,
    site_voice: str = "",
) -> str:
    main_kw, kw_lines, _ = _clone_kw_lines(rows)
    voice = site_voice or f"Cazilla Belgique — page transparence et confiance pour {lc.region_name}"
    if lc.lang != "fr":
        voice = site_voice or f"Cazilla offerwall — about/trust page for {lc.region_name}"
    h1_rule = (
        '- page_h1: use exactly "À propos de Cazilla" (plain text).'
        if lc.lang == "fr"
        else '- page_h1: use exactly "About Cazilla" (plain text).'
    )
    return f"""
You are an SEO copywriter for locale {lc.locale} (language: {lc.lang}).
Site voice: {voice}
Page: {menu_label} (editorial trust / about hub — independent reviews, not a casino operator).

Return ONLY valid JSON (no markdown fences):
{{
  "meta_title": "...",
  "meta_description": "...",
  "page_h1": "...",
  "page_lead": "...",
  "footer_note": "..."
}}

- meta_title: 55-60 chars, period at end, main keyword near start.
- meta_description: <= 140 chars, period at end.
{h1_rule}
- page_lead: 500-800 chars. Brand manifest: why Cazilla Belgique exists as an independent comparator (not industry cheerleaders); hunt for fine print and honest downsides. Allowed HTML: <strong>exact keyword phrases</strong>, <br><br> only. Weave page keywords naturally.
- footer_note: 80-180 chars plain text, 21+ responsible play for {lc.audience_phrase}.

Main keyword: "{main_kw}"
Keywords (lead + SEO): {kw_lines}
""".strip()


def build_offerwall_about_seo_prompt(
    *,
    menu_label: str,
    rows: List[Dict[str, Any]],
    lc: LocaleContext,
    include_site_factory_spec: bool = False,
    site_voice: str = "",
) -> str:
    main_kw, kw_lines, _ = _clone_kw_lines(rows)
    spec = site_factory_spec_block(enabled=include_site_factory_spec)
    voice = site_voice or f"Cazilla Belgique — méthodologie et transparence pour {lc.region_name}"
    if lc.lang != "fr":
        voice = site_voice or f"Cazilla offerwall about guide for {lc.region_name}"
    fair_rel = "fair-play.html"
    resp_rel = "responsible-gambling.html"
    if lc.lang == "fr":
        h2_guide = f"""
Required <h2> sections (exact titles and id attributes, in this order):
1. <h2 id="ow-about-method">Comment nous évaluons les casinos en ligne</h2> — methodology, real-money tests, licence checks; 2-3 <p>.
2. <h2 id="ow-about-transparency">Transparence : affiliation et indépendance</h2> — affiliate disclosure: casinos may pay for traffic but cannot buy a higher score; include a link <a href="{fair_rel}">notre charte éditoriale (fair play)</a>; 2 <p>.
3. <h2 id="ow-about-team">L'équipe éditoriale</h2> — generic editorial team (no fake names or credentials); years in iGaming; 2 <p>.
4. <h2 id="ow-about-responsible">Jeu responsable en Belgique</h2> — 21+, EPIS / gamblingtherapy.org; link <a href="{resp_rel}">jeu responsable</a>; 2 <p>.
Do NOT add a contact form or complaint form section.
"""
    else:
        h2_guide = f"""
Required <h2> sections (exact titles and id attributes, in this order):
1. <h2 id="ow-about-method">How we review online casinos</h2> — 2-3 <p>.
2. <h2 id="ow-about-transparency">Transparency: affiliates and independence</h2> — include <a href="{fair_rel}">editorial fair play charter</a>; 2 <p>.
3. <h2 id="ow-about-team">Editorial team</h2> — generic team, no fake names; 2 <p>.
4. <h2 id="ow-about-responsible">Responsible gambling</h2> — 21+; link <a href="{resp_rel}">responsible gambling</a>; 2 <p>.
No contact or complaint form section.
"""
    return f"""
You are an SEO copywriter for locale {lc.locale} (language: {lc.lang}).
Site voice: {voice}
{spec}
Page: {menu_label} — about / trust content (values grid is static in HTML; write ONLY the long-form article).

Return ONLY valid JSON:
{{"main_seo_html": "..."}}

main_seo_html rules:
- {OFFERWALL_ABOUT_SEO_MIN_CHARS}-{OFFERWALL_ABOUT_SEO_MAX_CHARS} visible characters.
- HTML: <h2>, <p>, optional <ul><li>; no <h1>.
- Include EVERY keyword below at least once (exact wording). First occurrence of each in <strong>...</strong>.
- At least one full sentence between keyword mentions. No false licence claims. 21+ for Belgium when relevant.
{h2_guide}

Main keyword: "{main_kw}"

Keyword list:
{kw_lines}
""".strip()


def generate_offerwall_about_page_content(
    *,
    api_key: str,
    menu_label: str,
    rows: List[Dict[str, Any]],
    lc: LocaleContext,
    include_site_factory_spec: bool,
    site_voice: str,
    env: Dict[str, str],
) -> Dict[str, Any]:
    meta = call_anthropic(
        api_key=api_key,
        prompt=build_offerwall_about_meta_prompt(
            menu_label=menu_label, rows=rows, lc=lc, site_voice=site_voice
        ),
        max_tokens=1200,
        env=env,
    )
    seo = call_anthropic(
        api_key=api_key,
        prompt=build_offerwall_about_seo_prompt(
            menu_label=menu_label,
            rows=rows,
            lc=lc,
            include_site_factory_spec=include_site_factory_spec,
            site_voice=site_voice,
        ),
        max_tokens=6000 if include_site_factory_spec else 3200,
        env=env,
    )
    out = {**meta, **seo}
    normalize_offerwall_about_content(out, rows, lc)
    return out


def normalize_offerwall_about_content(
    content: Dict[str, Any], rows: List[Dict[str, Any]], lc: LocaleContext
) -> None:
    normalize_clone_content(content, rows, lc)
    if lc.lang == "fr":
        content["page_h1"] = "À propos de Cazilla"
    else:
        content["page_h1"] = "About Cazilla"
    content["main_seo_html"] = fit_clone_seo_html(str(content.get("main_seo_html", "")))
    content["main_seo_html"] = inject_missing_clone_keywords(
        str(content.get("main_seo_html", "")), rows, lc
    )


def validate_offerwall_about_content(
    content: Dict[str, Any], rows: List[Dict[str, Any]], lc: LocaleContext
) -> None:
    normalize_offerwall_about_content(content, rows, lc)
    missing = missing_clone_fields(content)
    if missing:
        raise RuntimeError("Missing offerwall_about fields: " + ", ".join(missing))
    n = visible_text_len(str(content.get("main_seo_html", "")))
    if n < OFFERWALL_ABOUT_SEO_MIN_CHARS:
        raise RuntimeError(f"main_seo_html too short: {n} < {OFFERWALL_ABOUT_SEO_MIN_CHARS}")


def generate_clone_page_content(
    *,
    api_key: str,
    page_id: str,
    menu_label: str,
    rows: List[Dict[str, Any]],
    lc: LocaleContext,
    include_site_factory_spec: bool,
    site_voice: str,
    env: Dict[str, str],
) -> Dict[str, Any]:
    meta = call_anthropic(
        api_key=api_key,
        prompt=build_clone_meta_prompt(
            page_id=page_id,
            menu_label=menu_label,
            rows=rows,
            lc=lc,
            site_voice=site_voice,
        ),
        max_tokens=2048,
        env=env,
    )
    seo = call_anthropic(
        api_key=api_key,
        prompt=build_clone_seo_prompt(
            page_id=page_id,
            menu_label=menu_label,
            rows=rows,
            lc=lc,
            include_site_factory_spec=include_site_factory_spec,
            site_voice=site_voice,
        ),
        max_tokens=16384,
        env=env,
    )
    content: Dict[str, Any] = {}
    for k in ("meta_title", "meta_description", "page_h1", "page_lead", "footer_note"):
        content[k] = meta.get(k, "")
    content["main_seo_html"] = seo.get("main_seo_html", "")
    return content


def technical_page_focus(page_id: str, lc: LocaleContext) -> str:
    aud, region = lc.audience_phrase, lc.region_name
    templates: Dict[str, str] = {
        "user-agreement": "terms of use, eligibility, IP, liability, relationship to the main review",
        "cookie-policy": "cookies, consent categories, retention, browser controls",
        "fair-play": "editorial independence, methodology, corrections, conflicts of interest",
        "payments-withdrawals": (
            f"payment methods overview for {aud}, payout timing, operator cashier facts (not advice)"
        ),
        "privacy-policy": f"personal data, GDPR/{region} context, retention, user rights",
        "responsible-gambling": "18+, self-exclusion, helplines, safer play tools",
        "aml-kyc": "verification, AML obligations, source of funds, identity checks",
    }
    return templates.get(page_id, f"legal information for {aud}")


_SITE_EDITORIAL_VOICE: Dict[str, str] = {
    "cazilla-review1-en-ie": "Cazilla Review — straightforward consumer review tone",
    "cazilla-review1-fr-be": "Cazilla Review — avis consommateur clair et méthodique (Belgique)",
    "cazilla-review2-en-ie": "Cazilla Insight — analytical, methodical expert-test tone",
    "cazilla-review3-en-ie": "Cazilla Player Voices — reader/community editorial tone",
    "cazilla-offerwall1-en-ie": "CasinoRank IE — brand-list hub, comparison-first tone",
    "cazilla-offerwall2-en-ie": "Cazilla IE offerwall — concise directory tone",
    "cazilla-offerwall1-fr-be": "Cazilla Belgique — hub comparatif, ton éditorial concis",
    "cazilla-clone1-en-ie": "Cazilla lobby clone — catalogue-style editorial hub",
    "cazilla-clone2-en-ie": "Cazilla Live hub — catalogue editorial with home, live casino, slots",
    "cazilla-clone3-en-ie": "Cazilla Bonus hub — welcome offers, slots and live casino guides",
}


def technical_site_voice(site_dir: Path, lc: LocaleContext) -> str:
    slug = site_dir.name
    if slug in _SITE_EDITORIAL_VOICE:
        return _SITE_EDITORIAL_VOICE[slug]
    return f"{slug} — independent Cazilla editorial site for {lc.region_name}"


def build_technical_prompt(
    *,
    page_id: str,
    rel_path: str,
    menu_label: str,
    rows: List[Dict[str, Any]],
    lc: LocaleContext,
    include_site_factory_spec: bool = False,
    site_slug: str = "",
    site_voice: str = "",
) -> str:
    kws = [str(r.get("keyword", "")).strip() for r in rows if str(r.get("keyword", "")).strip()]
    if not kws:
        raise ValueError(f"technical page {page_id}: no keywords")
    main_kw = kws[0]
    kw_lines = "\n".join(
        f'- "{r["keyword"]}" (vol {r.get("search_volume", 0)}, KD {r.get("keyword_difficulty", 0)})'
        for r in rows
        if str(r.get("keyword", "")).strip()
    )
    spec = site_factory_spec_block(enabled=include_site_factory_spec)
    other_kws = kws[1:]
    page_focus = technical_page_focus(page_id, lc)
    site_path = ROOT / "sites" / site_slug if site_slug else None
    voice = site_voice or (
        technical_site_voice(site_path, lc) if site_path else f"independent Cazilla review site for {lc.region_name}"
    )
    example_meta = fit_technical_meta_title(f"{main_kw} Cazilla review.", rows, lc)
    return f"""
You are an SEO copywriter for locale {lc.locale} (language: {lc.lang}).
Write content for a LEGAL / POLICY footer page on an independent Cazilla expert review site ({lc.region_name}, {lc.locale}).
Site series id: {site_slug or "response"}
Editorial voice for THIS site only: {voice}
Page id: {page_id}
File: {rel_path}
Menu label: {menu_label}
Page focus (write ONLY about this topic): {page_focus}

{spec}

Uniqueness (mandatory):
- Write ORIGINAL copy for this page id and this site voice. Do NOT reuse paragraph openings, section order templates, or closing disclaimers from other policy pages.
- Vary H2 section titles and argument structure compared to a generic cookie/privacy template.
- hero_h1 and hero_subtitle must reflect "{menu_label}" specifically, not a generic legal page.

Strict constraints:
- Return ONLY a valid JSON object (no markdown, no extra text).
- Use ONLY keywords from the list below for this page. Do NOT use reserve or home-page keywords.
- Every keyword must appear at least once in body_html as exact wording (case-insensitive match in plain text).
- Wrap the FIRST occurrence of each keyword phrase in body_html with <strong>...</strong> (not inside <a> if it hurts readability).
- body_html visible text length (HTML stripped): {TECHNICAL_BODY_MIN_CHARS}–{TECHNICAL_BODY_MAX_CHARS} characters. Aim for 2200–2800. NEVER exceed {TECHNICAL_BODY_MAX_CHARS}.
- body_html structure: start with <article class="sectionCard" style="margin: 22px; max-width: 1180px; margin-left: auto; margin-right: auto">
  then <p> intro, multiple <div class="sectionHead"><h2>Legal section title</h2></div> blocks with <p> paragraphs.
  H2/H3 may be normal legal headings — keywords are NOT required inside H2/H3.
- Include at least one internal link to index.html (e.g. back to the expert review) with natural anchor text.
- Mention "review" / independent editorial context; brand Cazilla allowed in meta fields.
- meta_title: plain text, length {TECHNICAL_META_TITLE_MIN}–{TECHNICAL_META_TITLE_MAX} chars (count before returning JSON). MUST start with main keyword "{main_kw}" (capital first letter). Pack other page keywords with commas and "and" until length is in range. Only keywords + Cazilla + review. No colon. End with . or !
- Example meta_title shape ({len(example_meta)} chars): "{example_meta}"
- meta_description: plain text, max {TECHNICAL_META_DESC_MAX} chars; first phrase must use a DIFFERENT keyword than meta_title (prefer: "{other_kws[0] if other_kws else main_kw}"). Dense natural keyword use. End with . or !
- hero_h1: plain text legal page heading (may include a keyword naturally, not required).
- hero_subtitle: one short plain-text sentence.
- Tone: {lc.legal_tone_line}; not legal advice disclaimer where appropriate.

Keywords for THIS page only (use ALL):
{kw_lines}

Main keyword: "{main_kw}"

Exact output format (JSON):
{{
  "meta_title": "...",
  "meta_description": "...",
  "hero_h1": "...",
  "hero_subtitle": "...",
  "body_html": "<article class=\\"sectionCard\\" ...>...</article>"
}}
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


def visible_text_len(html_fragment: str) -> int:
    return len(strip_tags(html_fragment))


def missing_technical_fields(content: Dict[str, Any]) -> List[str]:
    missing: List[str] = []
    for k in TECHNICAL_CONTENT_KEYS:
        if not str(content.get(k, "")).strip():
            missing.append(k)
    return missing


def fit_technical_meta_title(raw: str, rows: List[Dict[str, Any]], lc: LocaleContext) -> str:
    """Normalize meta_title into 55-60 chars per site factory rules."""
    main = str(rows[0].get("keyword", "")).strip() if rows else ""
    t = (raw or "").strip()
    if main:
        if not t.lower().startswith(main.lower()[: min(8, len(main))]):
            t = main[0].upper() + main[1:] + (" " + t if t else "")
    if not t:
        t = (main or "Cazilla") + " review."
    if t[-1] not in ".!":
        t += "."
    extras = [str(r.get("keyword", "")).strip() for r in rows[1:] if str(r.get("keyword", "")).strip()]
    guard = 0
    while len(t) < TECHNICAL_META_TITLE_MIN and guard < 12:
        guard += 1
        if extras:
            piece = extras.pop(0)
            if piece.lower() in t.lower():
                continue
            t = t.rstrip(".!") + ", " + piece + "."
        else:
            t = (t.rstrip(".!") + " Cazilla review.")[:TECHNICAL_META_TITLE_MAX]
            if len(t) < TECHNICAL_META_TITLE_MIN:
                t = (t.rstrip(".!") + f" {lc.region_name}.")[:TECHNICAL_META_TITLE_MAX]
    if len(t) > TECHNICAL_META_TITLE_MAX:
        cut = t[:TECHNICAL_META_TITLE_MAX]
        if cut[-1] not in ".!":
            cut = cut[: TECHNICAL_META_TITLE_MAX - 1].rstrip(" ,;") + "."
        t = cut
    return t


def fit_technical_meta_description(
    raw: str, rows: List[Dict[str, Any]], meta_title: str, lc: LocaleContext
) -> str:
    t = (raw or "").strip()
    if not t:
        kws = [str(r.get("keyword", "")).strip() for r in rows if str(r.get("keyword", "")).strip()]
        alt = kws[1] if len(kws) > 1 else (kws[0] if kws else "Cazilla")
        t = f"{alt[0].upper()}{alt[1:]} and independent Cazilla review terms for {lc.audience_phrase}."
    if t[-1] not in ".!":
        t += "."
    while len(t) > TECHNICAL_META_DESC_MAX:
        words = t[: TECHNICAL_META_DESC_MAX].split()
        t = " ".join(words[:-1]) if len(words) > 2 else t[: TECHNICAL_META_DESC_MAX]
        if t[-1] not in ".!":
            t = t.rstrip(" ,;") + "."
    title_start = (meta_title or "").split(",")[0].strip().lower()[:24]
    if title_start and t.lower().startswith(title_start):
        kws = [str(r.get("keyword", "")).strip() for r in rows if str(r.get("keyword", "")).strip()]
        alt = kws[1] if len(kws) > 1 else kws[0]
        t = f"{alt[0].upper()}{alt[1:]}: " + t[: max(20, TECHNICAL_META_DESC_MAX - len(alt) - 2)]
        if len(t) > TECHNICAL_META_DESC_MAX:
            t = t[: TECHNICAL_META_DESC_MAX - 1].rstrip(" ,;") + "."
    return t


def fit_technical_body_html(raw: str) -> str:
    body = (raw or "").strip()
    if visible_text_len(body) <= TECHNICAL_BODY_MAX_CHARS:
        return body
    chunks = re.split(r"(?is)(</p>)", body)
    out: List[str] = []
    total = 0
    for i in range(0, len(chunks), 2):
        piece = chunks[i] + (chunks[i + 1] if i + 1 < len(chunks) else "")
        total += visible_text_len(piece)
        if total > TECHNICAL_BODY_MAX_CHARS:
            break
        out.append(piece)
    trimmed = "".join(out).strip()
    if "</article>" not in trimmed.lower():
        trimmed += "</article>"
    return trimmed


def inject_missing_technical_keywords(html_body: str, rows: List[Dict[str, Any]], lc: LocaleContext) -> str:
    body = (html_body or "").strip()
    body_lower = strip_tags(body).lower()
    missing = [
        str(r.get("keyword", "")).strip()
        for r in rows
        if str(r.get("keyword", "")).strip() and str(r.get("keyword", "")).strip().lower() not in body_lower
    ]
    if not missing:
        return body
    bits = ", ".join(f"<strong>{html.escape(kw)}</strong>" for kw in missing)
    return body + f"<p>{bits} — referenced for {lc.audience_phrase} on this legal page.</p>"


def normalize_technical_content(content: Dict[str, Any], rows: List[Dict[str, Any]], lc: LocaleContext) -> None:
    content["meta_title"] = fit_technical_meta_title(str(content.get("meta_title", "")), rows, lc)
    content["meta_description"] = fit_technical_meta_description(
        str(content.get("meta_description", "")), rows, str(content.get("meta_title", "")), lc
    )
    body = fit_technical_body_html(str(content.get("body_html", "")))
    content["body_html"] = inject_missing_technical_keywords(body, rows, lc)


def validate_technical_content(content: Dict[str, Any], rows: List[Dict[str, Any]], lc: LocaleContext) -> None:
    normalize_technical_content(content, rows, lc)
    missing = missing_technical_fields(content)
    if missing:
        raise RuntimeError("Missing technical fields: " + ", ".join(missing))

    mt = str(content.get("meta_title", "")).strip()
    if not (TECHNICAL_META_TITLE_MIN <= len(mt) <= TECHNICAL_META_TITLE_MAX):
        raise RuntimeError(
            f"meta_title length {len(mt)} outside {TECHNICAL_META_TITLE_MIN}-{TECHNICAL_META_TITLE_MAX}: {mt!r}"
        )

    md = str(content.get("meta_description", "")).strip()
    if len(md) > TECHNICAL_META_DESC_MAX:
        raise RuntimeError(f"meta_description length {len(md)} > {TECHNICAL_META_DESC_MAX}")

    body = str(content.get("body_html", "")).strip()
    blen = visible_text_len(body)
    tech_max = TECHNICAL_BODY_MAX_CHARS + 400
    if blen < TECHNICAL_BODY_MIN_CHARS or blen > tech_max:
        raise RuntimeError(
            f"body_html visible length {blen} outside {TECHNICAL_BODY_MIN_CHARS}-{tech_max}"
        )

    body_lower = strip_tags(body).lower()
    missing_kw = [
        str(r.get("keyword", "")).strip()
        for r in rows
        if str(r.get("keyword", "")).strip() and str(r.get("keyword", "")).strip().lower() not in body_lower
    ]
    if missing_kw:
        raise RuntimeError("body_html missing keywords: " + ", ".join(missing_kw))


def replace_first_submatch(html: str, pattern: str, repl: str, flags: int = re.I | re.S) -> str:
    return re.sub(pattern, repl, html, count=1, flags=flags)


def is_offerwall_hub_html(html: str) -> bool:
    return "ow-main--hub" in html or 'id="ow-faq"' in html


def is_offerwall_slots_html(html: str) -> bool:
    h = html or ""
    return (
        'data-page="slots-catalog"' in h
        or "ow-main--slots" in h
        or 'id="ow-slots-grid"' in h
    )


def is_offerwall_bonus_html(html: str) -> bool:
    h = html or ""
    return (
        'data-page="bonus-catalog"' in h
        or "ow-main--bonus" in h
        or 'id="ow-bonus-toplist"' in h
    )


def is_offerwall_about_html(html: str) -> bool:
    h = html or ""
    return (
        'data-page="about-trust"' in h
        or "ow-main--about" in h
        or 'id="ow-about-partner"' in h
    )


def is_offerwall_html(html: str) -> bool:
    """CasinoRank IE static offerwall shell (sites/cazilla-offerwall*-en-ie)."""
    return bool(re.search(r'(?is)class="[^"]*\bow-hero\b', html)) and bool(
        re.search(r'(?is)class="[^"]*\bow-prose\b', html)
    )


def site_dir_is_offerwall_aggregator(site_dir: Path) -> bool:
    s = str(site_dir).lower()
    if "offerwall" not in s:
        return False
    return (site_dir / "assets" / "pictures").is_dir()


def is_response_html(html: str) -> bool:
    """Expert single-page response shell (sites/*response*)."""
    h = html.lower()
    return 'data-site-kind="response"' in h or 'class="rs-layout"' in h


def site_dir_is_response(site_dir: Path) -> bool:
    return "response" in str(site_dir).lower()


def is_clone_html(html: str) -> bool:
    h = html.lower()
    return 'data-site-kind="clone"' in h or 'class="cl-layout"' in h


def is_review_lobby_html(html: str) -> bool:
    h = html.lower()
    return 'data-site-kind="review-lobby"' in h or "rb-layout" in h


def site_dir_is_clone(site_dir: Path) -> bool:
    s = str(site_dir).lower()
    return "clone" in s and "response" not in s


def content_keys_for_html(html: str, site_dir: Path, *, page_id: str = "home") -> List[str]:
    if page_id == "home" and (is_response_html(html) or site_dir_is_response(site_dir)):
        return RESPONSE_CONTENT_KEYS
    return HOME_CONTENT_KEYS


def missing_response_fields(content: Dict[str, Any]) -> List[str]:
    missing: List[str] = []
    for k in RESPONSE_CONTENT_KEYS:
        v = content.get(k)
        if k in ("pros", "cons"):
            if not isinstance(v, list) or len(v) < 2:
                missing.append(k)
        elif k == "faq_section":
            if not isinstance(v, list) or len(v) < 2:
                missing.append(k)
            else:
                ok = any(isinstance(it, dict) and str(it.get("question", "")).strip() for it in v)
                if not ok:
                    missing.append(k)
        elif not str(v or "").strip():
            missing.append(k)
    return missing


def apply_content_to_response_html(html_doc: str, content: Dict[str, Any]) -> str:
    """Map RESPONSE_CONTENT_KEYS into sites/cazilla-response-* layout via data-a2-field anchors."""
    out = html_doc

    def prose_field(field: str, text: str) -> None:
        nonlocal out
        if not text:
            return
        out = replace_first_submatch(
            out,
            rf'(?is)(<div[^>]*\bdata-a2-field=["\']{re.escape(field)}["\'][^>]*>\s*<p class="rs-body"[^>]*>)([\s\S]*?)(</p>)',
            r"\g<1>\n" + text + r"\n\g<3>",
        )

    hero_title = str(content.get("hero_title", "")).strip()
    if hero_title:
        out = replace_first_submatch(
            out,
            r'(?is)(<h1[^>]*\bdata-a2-field=["\']hero_title["\'][^>]*>)(.*?)(</h1>)',
            r"\g<1>" + hero_title + r"\g<3>",
        )

    hero_sub = str(content.get("hero_subtitle", "")).strip()
    if hero_sub:
        out = replace_first_submatch(
            out,
            r'(?is)(<p class="subtitle"[^>]*\bdata-a2-field=["\']hero_subtitle["\'][^>]*>\s*)([\s\S]*?)(\s*</p>)',
            r"\g<1>\n" + hero_sub + r"\n\g<3>",
        )

    intro = str(content.get("intro_meta", "")).strip()
    if intro:
        out = replace_first_submatch(
            out,
            r'(?is)(<p class="rs-intro-meta"[^>]*\bdata-a2-field=["\']intro_meta["\'][^>]*>)(.*?)(</p>)',
            r"\g<1>" + html.escape(intro) + r"\g<3>",
        )

    pros = content.get("pros")
    if isinstance(pros, list) and pros:
        lis = "".join(f"<li>{str(p).strip()}</li>" for p in pros if str(p).strip())
        if lis:
            out = replace_first_submatch(
                out,
                r'(?is)(<ul class="rs-pros"[^>]*\bdata-a2-field=["\']pros["\'][^>]*>)([\s\S]*?)(</ul>)',
                r"\g<1>\n" + lis + r"\n\g<3>",
            )

    cons = content.get("cons")
    if isinstance(cons, list) and cons:
        lis = "".join(f"<li>{str(c).strip()}</li>" for c in cons if str(c).strip())
        if lis:
            out = replace_first_submatch(
                out,
                r'(?is)(<ul class="rs-cons"[^>]*\bdata-a2-field=["\']cons["\'][^>]*>)([\s\S]*?)(</ul>)',
                r"\g<1>\n" + lis + r"\n\g<3>",
            )

    for field in (
        "overview_section",
        "licence_section",
        "design_section",
        "bonus_section",
        "vip_section",
        "payments_section",
        "games_section",
        "comparison_section",
        "summary_section",
    ):
        prose_field(field, str(content.get(field, "")).strip())

    faq = content.get("faq_section")
    if isinstance(faq, list) and faq:
        blocks: List[str] = []
        for it in faq:
            if not isinstance(it, dict):
                continue
            q = str(it.get("question", "")).strip()
            a = str(it.get("answer", "")).strip()
            if not q or not a:
                continue
            blocks.append(
                f"<details><summary>{html.escape(q)}</summary><p class=\"rs-body\">{a}</p></details>"
            )
        if blocks:
            out = replace_first_submatch(
                out,
                r'(?is)(<div class="rs-prose"[^>]*\bdata-a2-field=["\']faq_section["\'][^>]*>)([\s\S]*?)(</div>)',
                r"\g<1>\n" + "\n".join(blocks) + r"\n\g<3>",
            )

    author = str(content.get("author_bio", "")).strip()
    if author:
        out = replace_first_submatch(
            out,
            r'(?is)(<div class="rs-author-card"[^>]*\bdata-a2-field=["\']author_bio["\'][^>]*>\s*<p class="rs-body"[^>]*>)([\s\S]*?)(</p>)',
            r"\g<1>\n" + html.escape(author) + r"\n\g<3>",
        )

    footer = str(content.get("footer_seo_text", "")).strip()
    if footer:
        out = replace_first_submatch(
            out,
            r'(?is)(<p class="fineprint"[^>]*\bdata-a2-field=["\']footer["\'][^>]*>)([\s\S]*?)(</p>)',
            r"\g<1>\n" + footer + r"\n\g<3>",
        )

    return out


def missing_clone_fields(content: Dict[str, Any]) -> List[str]:
    missing: List[str] = []
    for k in CLONE_CONTENT_KEYS:
        if not str(content.get(k, "")).strip():
            missing.append(k)
    return missing


def fit_clone_seo_html(raw: str) -> str:
    body = (raw or "").strip()
    if visible_text_len(body) <= CLONE_SEO_MAX_CHARS:
        return body
    chunks = re.split(r"(?is)(</p>)", body)
    out: List[str] = []
    total = 0
    for i in range(0, len(chunks), 2):
        piece = chunks[i] + (chunks[i + 1] if i + 1 < len(chunks) else "")
        next_total = total + visible_text_len(piece)
        if next_total > CLONE_SEO_MAX_CHARS:
            break
        total = next_total
        out.append(piece)
    trimmed = "".join(out).strip()
    return trimmed if trimmed else body


def inject_missing_clone_keywords(html_body: str, rows: List[Dict[str, Any]], lc: LocaleContext) -> str:
    body = (html_body or "").strip()
    seo_lower = strip_tags(body).lower()
    missing = [
        str(r.get("keyword", "")).strip()
        for r in rows
        if str(r.get("keyword", "")).strip() and str(r.get("keyword", "")).strip().lower() not in seo_lower
    ]
    if not missing:
        return body
    bits = []
    for kw in missing:
        bits.append(f"<strong>{html.escape(kw)}</strong>")
    body += (
        "<h2>Related search terms</h2><p>"
        + ", ".join(bits)
        + f" — editorial notes for {lc.audience_phrase} comparing licensed operators.</p>"
    )
    return body


def normalize_clone_content(content: Dict[str, Any], rows: List[Dict[str, Any]], lc: LocaleContext) -> None:
    content["meta_title"] = fit_technical_meta_title(str(content.get("meta_title", "")), rows, lc)
    content["meta_description"] = fit_technical_meta_description(
        str(content.get("meta_description", "")), rows, str(content.get("meta_title", "")), lc
    )
    seo = fit_clone_seo_html(str(content.get("main_seo_html", "")))
    content["main_seo_html"] = inject_missing_clone_keywords(seo, rows, lc)


def validate_clone_content(content: Dict[str, Any], rows: List[Dict[str, Any]], lc: LocaleContext) -> None:
    normalize_clone_content(content, rows, lc)
    missing = missing_clone_fields(content)
    if missing:
        raise RuntimeError("Missing clone fields: " + ", ".join(missing))

    mt = str(content.get("meta_title", "")).strip()
    if not (TECHNICAL_META_TITLE_MIN <= len(mt) <= TECHNICAL_META_TITLE_MAX):
        raise RuntimeError(
            f"meta_title length {len(mt)} outside {TECHNICAL_META_TITLE_MIN}-{TECHNICAL_META_TITLE_MAX}: {mt!r}"
        )

    md = str(content.get("meta_description", "")).strip()
    if len(md) > TECHNICAL_META_DESC_MAX:
        raise RuntimeError(f"meta_description length {len(md)} > {TECHNICAL_META_DESC_MAX}")

    seo = str(content.get("main_seo_html", "")).strip()
    slen = visible_text_len(seo)
    seo_max = CLONE_SEO_MAX_CHARS + 600
    if slen < CLONE_SEO_MIN_CHARS or slen > seo_max:
        raise RuntimeError(
            f"main_seo_html visible length {slen} outside {CLONE_SEO_MIN_CHARS}-{seo_max}"
        )

    seo_lower = strip_tags(seo).lower()
    missing_kw = [
        str(r.get("keyword", "")).strip()
        for r in rows
        if str(r.get("keyword", "")).strip() and str(r.get("keyword", "")).strip().lower() not in seo_lower
    ]
    if missing_kw:
        raise RuntimeError("main_seo_html missing keywords: " + ", ".join(missing_kw))


def apply_content_to_clone_html(html_doc: str, content: Dict[str, Any]) -> str:
    out = html_doc

    mt = str(content.get("meta_title", "")).strip()
    if mt:
        esc = html.escape(mt)
        esc_q = html.escape(mt, quote=True)
        out = replace_first_submatch(out, r"(?is)<title[^>]*>\s*.*?\s*</title>", f"<title>{esc}</title>")
        out = replace_first_submatch(
            out,
            r'(?is)(<meta\s+property=["\']og:title["\']\s+content=["\'])(.*?)(["\'])',
            rf"\g<1>{esc_q}\g<3>",
        )

    md = str(content.get("meta_description", "")).strip()
    if md:
        esc_d = html.escape(md, quote=True)
        out = replace_first_submatch(
            out,
            r'(?is)(<meta\s+name=["\']description["\'][^>]*\s+content=["\'])(.*?)(["\'])',
            rf"\g<1>{esc_d}\g<3>",
        )
        out = replace_first_submatch(
            out,
            r'(?is)(<meta\s+property=["\']og:description["\']\s+content=["\'])(.*?)(["\'])',
            rf"\g<1>{esc_d}\g<3>",
        )

    h1 = str(content.get("page_h1", "")).strip()
    if h1:
        out = replace_first_submatch(
            out,
            r'(?is)(<h1[^>]*\bdata-a2-field=["\']page_h1["\'][^>]*>)(.*?)(</h1>)',
            r"\g<1>" + html.escape(h1) + r"\g<3>",
        )

    lead = str(content.get("page_lead", "")).strip()
    if lead:
        out = replace_first_submatch(
            out,
            r'(?is)(<p class="cl-lead"[^>]*\bdata-a2-field=["\']page_lead["\'][^>]*>\s*)([\s\S]*?)(\s*</p>)',
            r"\g<1>\n" + lead + r"\n\g<3>",
        )

    seo = str(content.get("main_seo_html", "")).strip()
    if seo:
        out = replace_first_submatch(
            out,
            r'(?is)(<div class="cl-seoProse"[^>]*\bdata-a2-field=["\']main_seo_html["\'][^>]*>)([\s\S]*?)(</div>)',
            r"\g<1>\n" + seo + r"\n\g<3>",
        )

    foot = str(content.get("footer_note", "")).strip()
    if foot:
        out = replace_first_submatch(
            out,
            r'(?is)(<p class="cl-fineprint"[^>]*\bdata-a2-field=["\']footer_note["\'][^>]*>)([\s\S]*?)(</p>)',
            r"\g<1>" + html.escape(foot) + r"\g<3>",
        )

    return out


def apply_content_to_review_lobby_html(html_doc: str, content: Dict[str, Any]) -> str:
    out = html_doc

    mt = str(content.get("meta_title", "")).strip()
    if mt:
        esc = html.escape(mt)
        esc_q = html.escape(mt, quote=True)
        out = replace_first_submatch(out, r"(?is)<title[^>]*>\s*.*?\s*</title>", f"<title>{esc}</title>")
        out = replace_first_submatch(
            out,
            r'(?is)(<meta\s+property=["\']og:title["\']\s+content=["\'])(.*?)(["\'])',
            rf"\g<1>{esc_q}\g<3>",
        )

    md = str(content.get("meta_description", "")).strip()
    if md:
        esc_d = html.escape(md, quote=True)
        out = replace_first_submatch(
            out,
            r'(?is)(<meta\s+name=["\']description["\'][^>]*\s+content=["\'])(.*?)(["\'])',
            rf"\g<1>{esc_d}\g<3>",
        )
        out = replace_first_submatch(
            out,
            r'(?is)(<meta\s+property=["\']og:description["\']\s+content=["\'])(.*?)(["\'])',
            rf"\g<1>{esc_d}\g<3>",
        )

    h1 = str(content.get("page_h1", "")).strip()
    if h1:
        out = replace_first_submatch(
            out,
            r'(?is)(<h1[^>]*\bdata-a2-field=["\']page_h1["\'][^>]*>)(.*?)(</h1>)',
            r"\g<1>" + html.escape(h1) + r"\g<3>",
        )

    lead = str(content.get("page_lead", "")).strip()
    if lead:
        for pat in (
            r'(?is)(<section[^>]*\bdata-a2-field=["\']page_lead["\'][^>]*>\s*<p[^>]*>\s*)([\s\S]*?)(\s*</p>\s*</section>)',
            r'(?is)(<p class="rb-liveHeroLead"[^>]*\bdata-a2-field=["\']page_lead["\'][^>]*>\s*)([\s\S]*?)(\s*</p>)',
            r'(?is)(<p class="rb-lead"[^>]*\bdata-a2-field=["\']page_lead["\'][^>]*>\s*)([\s\S]*?)(\s*</p>)',
            r'(?is)(<p[^>]*\bdata-a2-field=["\']page_lead["\'][^>]*>\s*)([\s\S]*?)(\s*</p>)',
        ):
            nxt = replace_first_submatch(out, pat, r"\g<1>\n" + lead + r"\n\g<3>")
            if nxt != out:
                out = nxt
                break

    seo = str(content.get("main_seo_html", "")).strip()
    if seo:
        out = replace_first_submatch(
            out,
            r'(?is)(<div class="rb-seoProse"[^>]*\bdata-a2-field=["\']main_seo_html["\'][^>]*>)([\s\S]*?)(</div>)',
            r"\g<1>\n" + seo + r"\n\g<3>",
        )

    foot = str(content.get("footer_note", "")).strip()
    if foot:
        out = replace_first_submatch(
            out,
            r'(?is)(<p class="rb-fineprint"[^>]*\bdata-a2-field=["\']footer_note["\'][^>]*>)([\s\S]*?)(</p>)',
            r"\g<1>" + html.escape(foot) + r"\g<3>",
        )

    return out


def apply_content_to_technical_html(
    html_doc: str, content: Dict[str, Any], env: Optional[Dict[str, str]] = None
) -> str:
    """Update head meta and policy body on legal pages (response, review, offerwall shells)."""
    out = html_doc

    mt = str(content.get("meta_title", "")).strip()
    if mt:
        esc = html.escape(mt)
        esc_q = html.escape(mt, quote=True)
        out = replace_first_submatch(out, r"(?is)<title[^>]*>\s*.*?\s*</title>", f"<title>{esc}</title>")
        out = replace_first_submatch(
            out,
            r'(?is)(<meta\s+property=["\']og:title["\']\s+content=["\'])(.*?)(["\'])',
            rf"\g<1>{esc_q}\g<3>",
        )

    md = str(content.get("meta_description", "")).strip()
    if md:
        esc_d = html.escape(md, quote=True)
        out = replace_first_submatch(
            out,
            r'(?is)(<meta\s+name=["\']description["\']\s+content=["\'])(.*?)(["\'])',
            rf"\g<1>{esc_d}\g<3>",
        )
        out = replace_first_submatch(
            out,
            r'(?is)(<meta\s+property=["\']og:description["\']\s+content=["\'])(.*?)(["\'])',
            rf"\g<1>{esc_d}\g<3>",
        )

    h1 = str(content.get("hero_h1", "")).strip()
    if h1:
        esc_h1 = html.escape(h1)
        for pat in (
            r'(?is)(<h1[^>]*\bdata-a2-field=["\']page_h1["\'][^>]*>)(.*?)(</h1>)',
            r"(?is)(<section\s+class=\"[^\"]*\bhero\b[^\"]*\"[^>]*>[\s\S]*?<h1>)(.*?)(</h1>)",
            r"(?is)(<main\b[^>]*>[\s\S]*?<h1>)(.*?)(</h1>)",
        ):
            nxt = replace_first_submatch(out, pat, r"\g<1>" + esc_h1 + r"\g<3>")
            if nxt != out:
                out = nxt
                break

    sub = str(content.get("hero_subtitle", "")).strip()
    if sub:
        esc_sub = html.escape(sub)
        for pat in (
            r'(?is)(<p class="rb-lead"[^>]*\bdata-a2-field=["\']page_lead["\'][^>]*>)(.*?)(</p>)',
            r'(?is)(<p\s+class="[^"]*\bsubtitle\b[^"]*"[^>]*>)(.*?)(</p>)',
            r'(?is)(<p\s+class="[^"]*\bow-lead\b[^"]*"[^>]*>)(.*?)(</p>)',
        ):
            nxt = replace_first_submatch(out, pat, r"\g<1>" + esc_sub + r"\g<3>")
            if nxt != out:
                out = nxt
                break

    body = str(content.get("body_html", "")).strip()
    if body:
        rb_article = (
            r'(?is)(<article\s+class="rb-policyArticle"[^>]*\bdata-a2-field=["\']main_seo_html["\'][^>]*>)'
            r"([\s\S]*?)(</article>)"
        )
        nxt = replace_first_submatch(out, rb_article, r"\g<1>\n" + body + r"\n\g<3>")
        if nxt != out:
            out = nxt
        else:
            body_patterns = (
                r'(?is)(<div\s+class="rb-policyCard">)\s*[\s\S]*?\s*(</div>\s*</main>)',
                r'(?is)(<div\s+class="policyCard">)\s*[\s\S]*?\s*(</div>\s*<p\s+class="fineprint")',
                r'(?is)(<div\s+class="policyCard">)\s*[\s\S]*?\s*(</div>\s*<footer\b)',
            )
            for pat in body_patterns:
                nxt = replace_first_submatch(out, pat, r"\g<1>\n" + body + r"\n    \g<2>")
                if nxt != out:
                    out = nxt
                    break

    if env:
        cta = _main_casino_cta_fragment(env)
        if cta and cta not in out:
            cta_block = f'<p class="policyCta">{cta}</p>'
            if re.search(r'(?is)<div\s+class="policyCard"', out):
                out = replace_first_submatch(
                    out,
                    r'(?is)(</div>\s*<p\s+class="fineprint")',
                    cta_block + r"\n    \g<1>",
                )
                if cta_block not in out:
                    out = replace_first_submatch(
                        out,
                        r'(?is)(</div>\s*<footer\b)',
                        cta_block + r"\n        \g<1>",
                    )
            if cta_block not in out:
                out = replace_first_submatch(
                    out,
                    r"(?is)(</main>)",
                    f"\n        {cta_block}\n      \\g<1>",
                )

    return out


def apply_content_to_offerwall_slots_html(
    html_doc: str, content: Dict[str, Any], env: Dict[str, str]
) -> str:
    out = html_doc
    page_rel = str(content.get("site_rel_path") or "slots.html").strip().lstrip("/")
    lc = locale_context_from_env(env, strict_keywords_match=False)

    mt = str(content.get("meta_title", "")).strip()
    if mt:
        esc = html.escape(mt)
        esc_q = html.escape(mt, quote=True)
        out = replace_first_submatch(out, r"(?is)<title[^>]*>\s*.*?\s*</title>", f"<title>{esc}</title>")
        out = replace_first_submatch(
            out,
            r'(?is)(<meta\s+property=["\']og:title["\']\s+content=["\'])(.*?)(["\'])',
            rf"\g<1>{esc_q}\g<3>",
        )

    md = str(content.get("meta_description", "")).strip()
    if md:
        esc_d = html.escape(md, quote=True)
        out = replace_first_submatch(
            out,
            r'(?is)(<meta\s+name=["\']description["\'][^>]*\s+content=["\'])(.*?)(["\'])',
            rf"\g<1>{esc_d}\g<3>",
        )
        out = replace_first_submatch(
            out,
            r'(?is)(<meta\s+property=["\']og:description["\']\s+content=["\'])(.*?)(["\'])',
            rf"\g<1>{esc_d}\g<3>",
        )

    h1 = str(content.get("page_h1", "")).strip()
    if h1:
        out = replace_first_submatch(
            out,
            r'(?is)(<h1[^>]*\bdata-a2-field=["\']page_h1["\'][^>]*>)(.*?)(</h1>)',
            r"\g<1>" + html.escape(h1) + r"\g<3>",
        )

    lead = str(content.get("page_lead", "")).strip()
    if lead:
        inner = lead
        cta = _main_casino_cta_fragment(env)
        if cta and "Jouer sur Cazilla" not in lead and "Open Cazilla" not in lead:
            inner = inner + " " + cta
        out = replace_first_submatch(
            out,
            r'(?is)(<p\s+class="[^"]*\bow-lead\b[^"]*"[^>]*\bdata-a2-field=["\']page_lead["\'][^>]*>\s*)([\s\S]*?)(\s*</p>)',
            r"\g<1>" + inner + r"\g<3>",
        )

    seo = str(content.get("main_seo_html", "")).strip()
    if seo:
        out = replace_first_submatch(
            out,
            r'(?is)(<article\b[^>]*\bdata-a2-field=["\']main_seo_html["\'][^>]*>)([\s\S]*?)(</article>)',
            r"\g<1>\n" + seo + r"\n          \g<3>",
        )

    foot = str(content.get("footer_note", "")).strip()
    if foot:
        out = replace_first_submatch(
            out,
            r'(?is)(<section\s+id="footer-legal"\s*>\s*<p[^>]*\bdata-a2-field=["\']footer_note["\'][^>]*>\s*)([\s\S]*?)(\s*</p>)',
            r"\g<1>" + html.escape(foot) + r"\g<3>",
        )

    fict = normalize_fictional_operators(content.get(FICTIONAL_OPERATORS_KEY))
    inner = build_offerwall_aggregator_sections_html(
        page_rel=page_rel,
        env=env,
        fictional=fict,
        lc=lc,
        include_gallery=False,
    )
    agg_aria = "Top cinq sélections" if lc.lang == "fr" else "Top five picks"
    block = (
        f'<section id="ow-slots-toplist" class="ow-aggregatorTop5" aria-label="{html.escape(agg_aria)}">\n'
        f"{inner}</section>"
    )
    m_agg = re.search(
        r'(?is)<section\b[^>]*\bid=["\']ow-slots-toplist["\'][^>]*>[\s\S]*?</section>',
        out,
    )
    if m_agg:
        out = out[: m_agg.start()] + block + out[m_agg.end() :]

    return out


def apply_content_to_offerwall_bonus_html(
    html_doc: str, content: Dict[str, Any], env: Dict[str, str]
) -> str:
    out = html_doc
    page_rel = str(content.get("site_rel_path") or "bonus.html").strip().lstrip("/")
    lc = locale_context_from_env(env, strict_keywords_match=False)

    mt = str(content.get("meta_title", "")).strip()
    if mt:
        esc = html.escape(mt)
        esc_q = html.escape(mt, quote=True)
        out = replace_first_submatch(out, r"(?is)<title[^>]*>\s*.*?\s*</title>", f"<title>{esc}</title>")
        out = replace_first_submatch(
            out,
            r'(?is)(<meta\s+property=["\']og:title["\']\s+content=["\'])(.*?)(["\'])',
            rf"\g<1>{esc_q}\g<3>",
        )

    md = str(content.get("meta_description", "")).strip()
    if md:
        esc_d = html.escape(md, quote=True)
        out = replace_first_submatch(
            out,
            r'(?is)(<meta\s+name=["\']description["\'][^>]*\s+content=["\'])(.*?)(["\'])',
            rf"\g<1>{esc_d}\g<3>",
        )
        out = replace_first_submatch(
            out,
            r'(?is)(<meta\s+property=["\']og:description["\']\s+content=["\'])(.*?)(["\'])',
            rf"\g<1>{esc_d}\g<3>",
        )

    h1 = str(content.get("page_h1", "")).strip()
    if h1:
        out = replace_first_submatch(
            out,
            r'(?is)(<h1[^>]*\bdata-a2-field=["\']page_h1["\'][^>]*>)(.*?)(</h1>)',
            r"\g<1>" + html.escape(h1) + r"\g<3>",
        )

    lead = str(content.get("page_lead", "")).strip()
    if lead:
        inner = lead
        cta = _main_casino_cta_fragment(env)
        if cta and "Jouer sur Cazilla" not in lead and "Open Cazilla" not in lead:
            inner = inner + " " + cta
        out = replace_first_submatch(
            out,
            r'(?is)(<p\s+class="[^"]*\bow-bonusIntro\b[^"]*"[^>]*\bdata-a2-field=["\']page_lead["\'][^>]*>\s*)([\s\S]*?)(\s*</p>)',
            r"\g<1>" + inner + r"\g<3>",
        )

    expert = str(content.get("expert_callout", "")).strip()
    if expert:
        expert = re.sub(r"</?strong>", "", expert, flags=re.I)
        body = expert if expert.startswith("<") else html.escape(expert)
        out = replace_first_submatch(
            out,
            r'(?is)(<section\b[^>]*\bid=["\']ow-bonus-expert["\'][^>]*>[\s\S]*?<p[^>]*>)([\s\S]*?)(</p>)',
            r"\g<1>" + body + r"\g<3>",
        )

    seo = str(content.get("main_seo_html", "")).strip()
    if seo:
        out = replace_first_submatch(
            out,
            r'(?is)(<article\b[^>]*\bdata-a2-field=["\']main_seo_html["\'][^>]*>)([\s\S]*?)(</article>)',
            r"\g<1>\n" + seo + r"\n          \g<3>",
        )

    foot = str(content.get("footer_note", "")).strip()
    if foot:
        out = replace_first_submatch(
            out,
            r'(?is)(<section\s+id="footer-legal"\s*>\s*<p[^>]*\bdata-a2-field=["\']footer_note["\'][^>]*>\s*)([\s\S]*?)(\s*</p>)',
            r"\g<1>" + html.escape(foot) + r"\g<3>",
        )

    fict = normalize_fictional_operators(content.get(FICTIONAL_OPERATORS_KEY))
    inner = build_offerwall_aggregator_sections_html(
        page_rel=page_rel,
        env=env,
        fictional=fict,
        lc=lc,
        include_gallery=False,
    )
    agg_aria = "Top cinq sélections" if lc.lang == "fr" else "Top five picks"
    block = (
        f'<section id="ow-bonus-toplist" class="ow-aggregatorTop5" aria-label="{html.escape(agg_aria)}">\n'
        f"{inner}</section>"
    )
    m_agg = re.search(
        r'(?is)<section\b[^>]*\bid=["\']ow-bonus-toplist["\'][^>]*>[\s\S]*?</section>',
        out,
    )
    if m_agg:
        out = out[: m_agg.start()] + block + out[m_agg.end() :]

    faq_html = _render_offerwall_faq_html(
        content.get("faq_section"),
        lc,
        section_id="ow-bonus-faq",
        section_class="ow-bonusFaq",
        title_class="ow-bonusFaqTitle",
    )
    if faq_html:
        m_faq = re.search(
            r'(?is)<section\b[^>]*\bid=["\']ow-bonus-faq["\'][^>]*>[\s\S]*?</section>',
            out,
        )
        if m_faq:
            out = out[: m_faq.start()] + faq_html.strip() + out[m_faq.end() :]

    return out


def apply_content_to_offerwall_about_html(
    html_doc: str, content: Dict[str, Any], env: Dict[str, str]
) -> str:
    out = html_doc
    page_rel = str(content.get("site_rel_path") or "about.html").strip().lstrip("/")
    lc = locale_context_from_env(env, strict_keywords_match=False)

    mt = str(content.get("meta_title", "")).strip()
    if mt:
        esc = html.escape(mt)
        esc_q = html.escape(mt, quote=True)
        out = replace_first_submatch(out, r"(?is)<title[^>]*>\s*.*?\s*</title>", f"<title>{esc}</title>")
        out = replace_first_submatch(
            out,
            r'(?is)(<meta\s+property=["\']og:title["\']\s+content=["\'])(.*?)(["\'])',
            rf"\g<1>{esc_q}\g<3>",
        )

    md = str(content.get("meta_description", "")).strip()
    if md:
        esc_d = html.escape(md, quote=True)
        out = replace_first_submatch(
            out,
            r'(?is)(<meta\s+name=["\']description["\'][^>]*\s+content=["\'])(.*?)(["\'])',
            rf"\g<1>{esc_d}\g<3>",
        )
        out = replace_first_submatch(
            out,
            r'(?is)(<meta\s+property=["\']og:description["\']\s+content=["\'])(.*?)(["\'])',
            rf"\g<1>{esc_d}\g<3>",
        )

    h1 = str(content.get("page_h1", "")).strip()
    if h1:
        out = replace_first_submatch(
            out,
            r'(?is)(<h1[^>]*\bdata-a2-field=["\']page_h1["\'][^>]*>)(.*?)(</h1>)',
            r"\g<1>" + html.escape(h1) + r"\g<3>",
        )

    lead = str(content.get("page_lead", "")).strip()
    if lead:
        inner = lead
        cta = _main_casino_cta_fragment(env)
        if cta and "Jouer sur Cazilla" not in lead and "Open Cazilla" not in lead:
            inner = inner + " " + cta
        out = replace_first_submatch(
            out,
            r'(?is)(<p\s+class="[^"]*\bow-aboutIntro\b[^"]*"[^>]*\bdata-a2-field=["\']page_lead["\'][^>]*>\s*)([\s\S]*?)(\s*</p>)',
            r"\g<1>" + inner + r"\g<3>",
        )

    seo = str(content.get("main_seo_html", "")).strip()
    if seo:
        out = replace_first_submatch(
            out,
            r'(?is)(<article\b[^>]*\bdata-a2-field=["\']main_seo_html["\'][^>]*>)([\s\S]*?)(</article>)',
            r"\g<1>\n" + seo + r"\n          \g<3>",
        )

    foot = str(content.get("footer_note", "")).strip()
    if foot:
        out = replace_first_submatch(
            out,
            r'(?is)(<section\s+id="footer-legal"\s*>\s*<p[^>]*\bdata-a2-field=["\']footer_note["\'][^>]*>\s*)([\s\S]*?)(\s*</p>)',
            r"\g<1>" + html.escape(foot) + r"\g<3>",
        )

    inner = build_offerwall_aggregator_sections_html(
        page_rel=page_rel,
        env=env,
        fictional=[],
        lc=lc,
        include_gallery=False,
        featured_only=True,
    )
    agg_aria = "Partenaire mis en avant" if lc.lang == "fr" else "Featured partner"
    block = (
        f'<section id="ow-about-partner" class="ow-aggregatorTop5" aria-label="{html.escape(agg_aria)}">\n'
        f"{inner}</section>"
    )
    m_agg = re.search(
        r'(?is)<section\b[^>]*\bid=["\']ow-about-partner["\'][^>]*>[\s\S]*?</section>',
        out,
    )
    if m_agg:
        out = out[: m_agg.start()] + block + out[m_agg.end() :]

    return out


def apply_content_to_page_html(html: str, content: Dict[str, Any], env: Dict[str, str]) -> str:
    if str(content.get("page_kind", "")).strip() == "technical":
        return apply_content_to_technical_html(html, content, env)
    pk = str(content.get("page_kind", "")).strip().lower()
    if pk == PAGE_KIND_OFFERWALL_BONUS or is_offerwall_bonus_html(html):
        return apply_content_to_offerwall_bonus_html(html, content, env)
    if pk == PAGE_KIND_OFFERWALL_ABOUT or is_offerwall_about_html(html):
        return apply_content_to_offerwall_about_html(html, content, env)
    if pk == PAGE_KIND_OFFERWALL_SLOTS or is_offerwall_slots_html(html):
        return apply_content_to_offerwall_slots_html(html, content, env)
    if pk == PAGE_KIND_REVIEW_LOBBY or is_review_lobby_html(html):
        return apply_content_to_review_lobby_html(html, content)
    if is_clone_html(html) or pk == "clone":
        return apply_content_to_clone_html(html, content)
    if is_offerwall_html(html):
        return apply_content_to_offerwall_html(html, content, env)
    if is_response_html(html):
        return apply_content_to_response_html(html, content)
    return apply_content_to_index_html(html, content)


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
    lc: LocaleContext,
    include_gallery: bool = False,
    featured_only: bool = False,
) -> str:
    cta = _main_casino_cta_fragment(env) or ""
    fr = lc.lang == "fr"
    if fr:
        featured_tag = f"Partenaire mis en avant · {html.escape(lc.region_facing_label)}"
        featured_body = (
            "Notre choix principal sur cette page : promos lisibles, tables live "
            "et parcours de caisse que nous pouvons illustrer pour les lecteurs."
        )
        if featured_only:
            disclaimer = (
                f'<p class="ow-aggDisclaimer">Comparatif éditorial pour {html.escape(lc.region_name)}. '
                "<strong>Cazilla</strong> est le partenaire sortant mis en avant sur ce site — "
                "sans classement fictif supplémentaire sur cette page.</p>\n"
            )
        else:
            disclaimer = (
                f'<p class="ow-aggDisclaimer">Sélection éditoriale pour {html.escape(lc.region_name)}. '
                "<strong>#1 Cazilla</strong> est le partenaire sortant mis en avant. "
                "Les rangs #2–#5 sont des marques fictives servant uniquement à comparer mise en page "
                "et style de texte — ce ne sont pas de vraies offres licenciées sur ce domaine.</p>\n"
            )
        gallery_title = "Références lobby &amp; jeux"
    else:
        featured_tag = f"Featured partner · {html.escape(lc.region_facing_label)}"
        featured_body = (
            "Primary pick on this page: transparent promos, live tables, and cashier flows "
            "we can screenshot for readers."
        )
        if featured_only:
            disclaimer = (
                f'<p class="ow-aggDisclaimer">Editorial hub for {html.escape(lc.region_name)}. '
                "<strong>Cazilla</strong> is the featured outbound partner on this page — "
                "no fictional ranks #2–#5 here.</p>\n"
            )
        else:
            disclaimer = (
                f'<p class="ow-aggDisclaimer">Editorial shortlist for {html.escape(lc.region_name)}. '
                "<strong>#1 Cazilla</strong> is the featured outbound partner. "
                "Ranks #2–#5 are fictional placeholder brands used only to compare layout and copy "
                "patterns—they are not real licensed offers on this domain.</p>\n"
            )
        gallery_title = "Lobby &amp; games reference art"
    cards_html: List[str] = []
    img0 = html.escape(asset_href_for_html_page(page_rel, OFFERWALL_TOP5_IMAGES[0]))
    cards_html.append(
        '<article class="ow-topCard ow-topCard--featured">'
        '<div class="ow-topCardRank" aria-hidden="true">#1</div>'
        f'<div class="ow-topCardMedia"><img src="{img0}" alt="" width="480" height="300" loading="eager" decoding="async" /></div>'
        "<h3>Cazilla</h3>"
        f'<p class="ow-topCardTag">{featured_tag}</p>'
        f"<p>{featured_body}</p>"
        f'<p class="ow-topCardCta">{cta}</p>'
        "</article>"
    )
    if featured_only:
        return disclaimer + '<div class="ow-topGrid">\n' + "\n".join(cards_html) + "\n</div>\n"
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

    body = disclaimer + '<div class="ow-topGrid">\n' + "\n".join(cards_html) + "\n</div>\n"
    if not include_gallery:
        return body
    gallery_items: List[str] = []
    for rel in OFFERWALL_GALLERY_IMAGES:
        href = html.escape(asset_href_for_html_page(page_rel, rel))
        base = rel.rsplit("/", 1)[-1]
        cap = html.escape(base.replace("-", " ").rsplit(".", 1)[0].title())
        gallery_items.append(
            f'<figure class="ow-galleryCell"><img src="{href}" alt="" width="360" height="220" loading="lazy" decoding="async" /><figcaption>{cap}</figcaption></figure>'
        )
    return (
        body
        + f'<h2 class="ow-galleryTitle">{gallery_title}</h2>\n'
        + '<div class="ow-galleryGrid">\n' + "\n".join(gallery_items) + "\n</div>\n"
    )

def _section_html_block(body: str) -> str:
    text = body.strip()
    if not text:
        return ""
    if text.startswith("<"):
        return text
    return f"<p>{text}</p>"


def _render_offerwall_faq_html(
    faq: Any,
    lc: LocaleContext,
    *,
    section_id: str = "ow-faq",
    section_class: str = "ow-hubFaq",
    title_class: str = "ow-hubFaqTitle",
    title: Optional[str] = None,
) -> str:
    items: List[Dict[str, str]] = []
    if isinstance(faq, list):
        for row in faq:
            if not isinstance(row, dict):
                continue
            q = str(row.get("question") or "").strip()
            a = str(row.get("answer") or "").strip()
            if q and a:
                items.append({"question": q, "answer": a})
    if not items:
        return ""
    if title is None:
        if section_id == "ow-bonus-faq":
            title = (
                "Questions fréquentes sur les bonus casino"
                if lc.lang == "fr"
                else "Bonus FAQ"
            )
        else:
            title = "Questions fréquentes" if lc.lang == "fr" else "FAQ"
    details = []
    for row in items:
        details.append(
            f"          <details><summary>{html.escape(row['question'])}</summary>"
            f"<p>{html.escape(row['answer'])}</p></details>"
        )
    return (
        f'        <section class="{html.escape(section_class)}" id="{html.escape(section_id)}" data-a2-field="faq_section">\n'
        f'          <h2 class="{html.escape(title_class)}">{html.escape(title)}</h2>\n'
        + "\n".join(details)
        + "\n        </section>\n"
    )


def _main_casino_cta_fragment(env: Dict[str, str]) -> str:
    url = (env.get("MAIN_CASINO_URL") or os.getenv("MAIN_CASINO_URL") or "").strip().rstrip("/")
    if not url:
        return ""
    lc = locale_context_from_env(env, strict_keywords_match=False)
    label = "Jouer sur Cazilla" if lc.lang == "fr" else "Open Cazilla"
    esc = html.escape(url, quote=True)
    return f'<a href="{esc}" rel="noopener noreferrer" target="_blank">{html.escape(label)}</a>'


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
    lc = locale_context_from_env(env, strict_keywords_match=False)
    hub = is_offerwall_hub_html(html_doc)

    if hero_title:
        esc_t = html.escape(hero_title)
        esc_tq = html.escape(hero_title, quote=True)
        html_doc = replace_first_submatch(
            html_doc, r"(?is)<title[^>]*>\s*.*?\s*</title>", f"<title>{esc_t}</title>"
        )
        html_doc = replace_first_submatch(
            html_doc,
            r'(?is)(<meta\s+property=["\']og:title["\']\s+content=["\'])(.*?)(["\'])',
            rf"\g<1>{esc_tq}\g<3>",
        )

    if FICTIONAL_OPERATORS_KEY in content:
        fict = normalize_fictional_operators(content.get(FICTIONAL_OPERATORS_KEY))
        inner = build_offerwall_aggregator_sections_html(
            page_rel=page_rel,
            env=env,
            fictional=fict,
            lc=lc,
            include_gallery=not hub,
        )
        m_agg = re.search(r'(?is)<section\b[^>]*\bid=["\']ow-aggregator-top5["\'][^>]*>[\s\S]*?</section>', html_doc)
        agg_aria = "Top cinq sélections" if lc.lang == "fr" else "Top five picks"
        block = (
            f'<section id="ow-aggregator-top5" class="ow-aggregatorTop5" aria-label="{html.escape(agg_aria)}">\n{inner}</section>'
        )
        if m_agg:
            html_doc = html_doc[: m_agg.start()] + block + html_doc[m_agg.end() :]
        else:
            html_doc = replace_first_submatch(
                html_doc,
                r'(?is)(<article\s+class="[^"]*\bow-prose\b[^"]*"[^>]*>)',
                block + "\n" + r"\1",
            )

    if hero_title:
        html_doc = replace_first_submatch(
            html_doc,
            r'(?is)(<section\b[^>]*class="[^"]*\bow-hero\b[^"]*"[^>]*>\s*<h1[^>]*>)(.*?)(</h1>)',
            r"\g<1>" + html.escape(hero_title) + r"\g<3>",
        )

    if hero_sub:
        inner = hero_sub
        cta = _main_casino_cta_fragment(env)
        skip_cta = ("Open Cazilla", "Jouer sur Cazilla")
        if cta and not any(s in hero_sub for s in skip_cta):
            inner = inner + " " + cta
        html_doc = replace_first_submatch(
            html_doc,
            r'(?is)(<section\b[^>]*class="[^"]*\bow-hero\b[^"]*"[^>]*>[\s\S]*?<p\s+class="[^"]*\bow-lead\b[^"]*"[^>]*>\s*)([\s\S]*?)(\s*</p>)',
            r"\g<1>" + inner + r"\g<3>",
        )

    if about or bonus or games:
        parts: List[str] = []
        if hub:
            if lc.lang == "fr":
                h_overview, h_bonus, h_games = (
                    "Cazilla, toujours à la recherche du meilleur choix",
                    "Comment nous évaluons les casinos en ligne",
                    "Pas de casino parfait, mais de meilleures options",
                )
            else:
                h_overview, h_bonus, h_games = (
                    "Cazilla — finding the best fit",
                    "How we review online casinos",
                    "No perfect casino, better options",
                )
        elif lc.lang == "fr":
            h_overview, h_bonus, h_games = (
                "Aperçu",
                "Bonus et paiements",
                "Jeux et lobby",
            )
        else:
            h_overview, h_bonus, h_games = (
                "Overview",
                "Bonuses &amp; payments",
                "Games &amp; lobby",
            )
        if about:
            parts.append(f"<h2>{h_overview}</h2>\n{_section_html_block(about)}")
        if bonus:
            parts.append(f"<h2>{h_bonus}</h2>\n{_section_html_block(bonus)}")
        if games:
            parts.append(f"<h2>{h_games}</h2>\n{_section_html_block(games)}")
        if not hub:
            if lc.lang == "fr":
                h_link = "Lien opérateur"
                link_p = (
                    "Pour vérifier les offres en direct, continuez sur le site officiel : "
                    + (_main_casino_cta_fragment(env) or "")
                )
            else:
                h_link = "Operator link"
                link_p = (
                    "When you are ready to verify offers live, continue on the official site: "
                    + (_main_casino_cta_fragment(env) or "")
                )
            parts.append(f"<h2>{h_link}</h2>\n<p>{link_p}</p>")
        article_body = "\n".join(parts) + "\n"
        html_doc = replace_first_submatch(
            html_doc,
            r'(?is)(<article\s+class="[^"]*\bow-prose\b[^"]*"[^>]*>)([\s\S]*?)(</article>)',
            r"\g<1>\n" + article_body + r"\g<3>",
        )

    faq_html = _render_offerwall_faq_html(content.get("faq_section"), lc)
    if faq_html:
        m_faq = re.search(r'(?is)<section\b[^>]*\bid=["\']ow-faq["\'][^>]*>[\s\S]*?</section>', html_doc)
        if m_faq:
            html_doc = html_doc[: m_faq.start()] + faq_html.strip() + html_doc[m_faq.end() :]

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


def _menu_label_from_bundle(bundle: KeywordsBundle, page_id: str, *sections: str) -> str:
    try:
        raw = read_json(bundle.source_path)
    except Exception:
        return page_id.replace("-", " ").title()
    if not isinstance(raw, dict):
        return page_id.replace("-", " ").title()
    for sec in sections:
        for p in raw.get(sec) or []:
            if isinstance(p, dict) and str(p.get("id", "")).strip() == page_id:
                lab = str(p.get("menu_label") or "").strip()
                if lab:
                    return lab
    return page_id.replace("-", " ").title()


def technical_menu_label(bundle: KeywordsBundle, page_id: str) -> str:
    return _menu_label_from_bundle(bundle, page_id, "technical_pages")


def page_menu_label(bundle: KeywordsBundle, page_id: str) -> str:
    return _menu_label_from_bundle(bundle, page_id, "pages")


def run_generate(
    env: Dict[str, str],
    *,
    include_site_factory_spec: bool,
    page_id: Optional[str],
    technical_only: bool = False,
) -> None:
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
    kw_locale = str(bundle.raw_meta.get("locale") or "").strip() or None
    lc = locale_context_from_env(env, keywords_locale=kw_locale)
    print(f"Locale context: {lc.locale} ({lc.language_name}) · {lc.region_name} [{lc.geo}]")
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
            lc=lc,
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
    site_prefix = f"{site_dir_s.rstrip('/')}/"
    if out_path.exists():
        try:
            ex = read_json(out_path)
            if isinstance(ex, dict) and int(ex.get("content_format_version") or 0) == CONTENT_FORMAT_V2:
                po = ex.get("pages")
                if isinstance(po, dict):
                    for k, v in po.items():
                        if not isinstance(v, dict):
                            continue
                        th = str(v.get("target_html_path") or "").replace("\\", "/")
                        if th and not th.startswith(site_prefix):
                            continue
                        pages_out[k] = dict(v)
        except Exception:
            pass

    targets_run = list(bundle.targets)
    if filter_pid:
        targets_run = [t for t in bundle.targets if t.page_id == filter_pid]
        if not targets_run:
            raise SystemExit(f"PAGE_ID / --page-id={filter_pid!r} not found in keywords bundle targets.")

    include_tech = technical_only or (
        env.get("A2_INCLUDE_TECHNICAL") or os.getenv("A2_INCLUDE_TECHNICAL") or ""
    ).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    if technical_only:
        targets_run = [t for t in targets_run if t.kind == "technical"]
        if not targets_run:
            raise SystemExit("No technical_pages targets in keywords bundle.")
    elif not include_tech:
        targets_run = [t for t in targets_run if t.kind == "page"]

    print("Keywords file:", bundle.source_path, "(bundle v2)")
    print("Targets to generate:", ", ".join(f"{t.page_id}({t.rel_path})" for t in targets_run))
    print("Reserve phrases:", len(bundle.reserve_rows))

    last_err: Optional[Exception] = None
    for attempt in range(1, 4):
        try:
            for t in targets_run:
                print("--- Generating page_id:", t.page_id, "---")
                rows = t.rows
                hp = resolve_site_html(site_dir, t.rel_path)

                if t.kind == "technical":
                    main_kw = rows[0]["keyword"] if rows else ""
                    print("  Main keyword:", main_kw)
                    print("  Technical keywords:", len(rows))
                    prompt = build_technical_prompt(
                        page_id=t.page_id,
                        rel_path=t.rel_path,
                        menu_label=technical_menu_label(bundle, t.page_id),
                        rows=rows,
                        lc=lc,
                        include_site_factory_spec=include_site_factory_spec,
                        site_slug=site_dir.name,
                        site_voice=technical_site_voice(site_dir, lc),
                    )
                    max_tokens = 8192
                    content = call_anthropic(api_key=api_key, prompt=prompt, max_tokens=max_tokens, env=env)
                    validate_technical_content(content, rows, lc)
                    print(f"  meta_title len: {len(content['meta_title'])}")
                    print(f"  body_html len: {visible_text_len(str(content['body_html']))}")
                    page_obj = {k: content[k] for k in TECHNICAL_CONTENT_KEYS}
                    page_obj["target_html_path"] = str(hp.relative_to(ROOT))
                    page_obj["page_kind"] = "technical"
                    page_obj["site_rel_path"] = str(t.rel_path or "").strip().lstrip("/")
                    pages_out[t.page_id] = page_obj
                    continue

                hp_probe = hp
                hp_text = hp_probe.read_text(encoding="utf-8", errors="replace") if hp_probe.exists() else ""
                agg_home = (
                    t.page_id == "home"
                    and site_dir_is_offerwall_aggregator(site_dir)
                    and hp_probe.exists()
                    and is_offerwall_html(hp_text)
                )
                hub_home = agg_home and is_offerwall_hub_html(hp_text)
                if hub_home:
                    main_kw, about_kws, bonus_kws, games_kws, footer_kws = pick_keywords_offerwall_sections(rows)
                else:
                    main_kw, about_kws, footer_kws = pick_keywords(rows)
                    bonus_kws, games_kws = [], []
                print("  Main keyword:", main_kw)
                resp_home = t.page_id == "home" and hp_probe.exists() and is_response_html(hp_text)
                slots_page = (
                    t.page_id == "slots"
                    and site_dir_is_offerwall_aggregator(site_dir)
                    and hp_probe.exists()
                    and is_offerwall_slots_html(hp_text)
                )
                bonus_page = (
                    t.page_id == "bonus"
                    and site_dir_is_offerwall_aggregator(site_dir)
                    and hp_probe.exists()
                    and is_offerwall_bonus_html(hp_text)
                )
                about_page = (
                    t.page_id == "about"
                    and site_dir_is_offerwall_aggregator(site_dir)
                    and hp_probe.exists()
                    and is_offerwall_about_html(hp_text)
                )
                clone_page = hp_probe.exists() and (
                    is_clone_html(hp_text) or site_dir_is_clone(site_dir)
                )
                review_lobby_page = hp_probe.exists() and is_review_lobby_html(hp_text)
                if about_page:
                    content = generate_offerwall_about_page_content(
                        api_key=api_key,
                        menu_label=page_menu_label(bundle, t.page_id),
                        rows=rows,
                        lc=lc,
                        include_site_factory_spec=include_site_factory_spec,
                        site_voice=technical_site_voice(site_dir, lc),
                        env=env,
                    )
                    validate_offerwall_about_content(content, rows, lc)
                    print(f"  meta_title len: {len(content['meta_title'])}")
                    print(f"  main_seo_html len: {visible_text_len(str(content['main_seo_html']))}")
                    page_obj = {k: content[k] for k in OFFERWALL_ABOUT_CONTENT_KEYS}
                    page_obj["target_html_path"] = str(hp.relative_to(ROOT))
                    page_obj["page_kind"] = PAGE_KIND_OFFERWALL_ABOUT
                    page_obj["site_rel_path"] = str(t.rel_path or "").strip().lstrip("/")
                    pages_out[t.page_id] = page_obj
                    continue
                if bonus_page:
                    content = generate_offerwall_bonus_page_content(
                        api_key=api_key,
                        menu_label=page_menu_label(bundle, t.page_id),
                        rows=rows,
                        lc=lc,
                        include_site_factory_spec=include_site_factory_spec,
                        site_voice=technical_site_voice(site_dir, lc),
                        env=env,
                    )
                    validate_offerwall_bonus_content(content, rows, lc)
                    print(f"  meta_title len: {len(content['meta_title'])}")
                    print(f"  main_seo_html len: {visible_text_len(str(content['main_seo_html']))}")
                    page_obj = {k: content[k] for k in OFFERWALL_BONUS_CONTENT_KEYS}
                    page_obj["target_html_path"] = str(hp.relative_to(ROOT))
                    page_obj["page_kind"] = PAGE_KIND_OFFERWALL_BONUS
                    page_obj["site_rel_path"] = str(t.rel_path or "").strip().lstrip("/")
                    pages_out[t.page_id] = page_obj
                    continue
                if slots_page:
                    content = generate_offerwall_slots_page_content(
                        api_key=api_key,
                        menu_label=page_menu_label(bundle, t.page_id),
                        rows=rows,
                        lc=lc,
                        include_site_factory_spec=include_site_factory_spec,
                        site_voice=technical_site_voice(site_dir, lc),
                        env=env,
                    )
                    validate_offerwall_slots_content(content, rows, lc)
                    print(f"  meta_title len: {len(content['meta_title'])}")
                    print(f"  main_seo_html len: {visible_text_len(str(content['main_seo_html']))}")
                    page_obj = {k: content[k] for k in OFFERWALL_SLOTS_CONTENT_KEYS}
                    page_obj["target_html_path"] = str(hp.relative_to(ROOT))
                    page_obj["page_kind"] = PAGE_KIND_OFFERWALL_SLOTS
                    page_obj["site_rel_path"] = str(t.rel_path or "").strip().lstrip("/")
                    pages_out[t.page_id] = page_obj
                    continue
                if review_lobby_page:
                    content = generate_clone_page_content(
                        api_key=api_key,
                        page_id=t.page_id,
                        menu_label=page_menu_label(bundle, t.page_id),
                        rows=rows,
                        lc=lc,
                        include_site_factory_spec=include_site_factory_spec,
                        site_voice=technical_site_voice(site_dir, lc),
                        env=env,
                    )
                    validate_clone_content(content, rows, lc)
                    print(f"  meta_title len: {len(content['meta_title'])}")
                    print(f"  main_seo_html len: {visible_text_len(str(content['main_seo_html']))}")
                    page_obj = {k: content[k] for k in REVIEW_LOBBY_CONTENT_KEYS}
                    page_obj["target_html_path"] = str(hp.relative_to(ROOT))
                    page_obj["page_kind"] = PAGE_KIND_REVIEW_LOBBY
                    page_obj["site_rel_path"] = str(t.rel_path or "").strip().lstrip("/")
                    pages_out[t.page_id] = page_obj
                    continue
                if clone_page:
                    content = generate_clone_page_content(
                        api_key=api_key,
                        page_id=t.page_id,
                        menu_label=page_menu_label(bundle, t.page_id),
                        rows=rows,
                        lc=lc,
                        include_site_factory_spec=include_site_factory_spec,
                        site_voice=technical_site_voice(site_dir, lc),
                        env=env,
                    )
                    validate_clone_content(content, rows, lc)
                    print(f"  meta_title len: {len(content['meta_title'])}")
                    print(f"  main_seo_html len: {visible_text_len(str(content['main_seo_html']))}")
                    page_obj = {k: content[k] for k in CLONE_CONTENT_KEYS}
                    page_obj["target_html_path"] = str(hp.relative_to(ROOT))
                    page_obj["page_kind"] = "clone"
                    page_obj["site_rel_path"] = str(t.rel_path or "").strip().lstrip("/")
                    pages_out[t.page_id] = page_obj
                    continue

                page_keys = RESPONSE_CONTENT_KEYS if resp_home else HOME_CONTENT_KEYS
                prompt = build_prompt(
                    main_kw,
                    about_kws,
                    footer_kws,
                    rows,
                    lc=lc,
                    reserve_phrases=reserve_phrases,
                    include_site_factory_spec=include_site_factory_spec,
                    home_offerwall_aggregator=agg_home,
                    home_offerwall_hub=hub_home,
                    bonus_kws=bonus_kws if hub_home else None,
                    games_kws=games_kws if hub_home else None,
                    home_response=resp_home,
                )
                if include_site_factory_spec and (agg_home or resp_home):
                    max_tokens = 8192 if resp_home else 6000
                elif include_site_factory_spec:
                    max_tokens = 8192
                elif agg_home:
                    max_tokens = 2400
                elif resp_home:
                    max_tokens = 8192
                else:
                    max_tokens = 1800
                content = call_anthropic(api_key=api_key, prompt=prompt, max_tokens=max_tokens, env=env)
                if resp_home:
                    missing = missing_response_fields(content)
                else:
                    missing = [k for k in HOME_CONTENT_KEYS if k not in content or not str(content.get(k, "")).strip()]
                if agg_home:
                    fict = normalize_fictional_operators(content.get(FICTIONAL_OPERATORS_KEY))
                    if len(fict) < 4:
                        missing = list(missing) + [FICTIONAL_OPERATORS_KEY]
                if missing:
                    raise RuntimeError(f"page {t.page_id}: missing fields: " + ", ".join(missing))
                page_obj = {k: content[k] for k in page_keys}
                page_obj["target_html_path"] = str(hp.relative_to(ROOT))
                page_obj["page_kind"] = "response" if resp_home else "landing"
                page_obj["site_rel_path"] = str(t.rel_path or "").strip().lstrip("/")
                if agg_home:
                    page_obj[FICTIONAL_OPERATORS_KEY] = normalize_fictional_operators(
                        content.get(FICTIONAL_OPERATORS_KEY)
                    )
                if hub_home and content.get("faq_section"):
                    page_obj["faq_section"] = content["faq_section"]
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
                html_out = apply_content_to_page_html(html_in, pdata, env)
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
    new_html = apply_content_to_page_html(full_html, apply_src, env)
    html_path.write_text(new_html, encoding="utf-8")
    print("Updated:", html_path)

    a3 = ROOT / "agents" / "a3-ai-check" / "agents" / "a3-ai-check" / "run.py"
    print("\n=== Launching A3 --recheck ===")
    r = subprocess.run([sys.executable, str(a3), "--recheck"], cwd=str(ROOT), env=os.environ.copy())
    if r.returncode != 0:
        raise SystemExit(f"A3 recheck failed (exit {r.returncode})")


def main(argv: List[str]) -> int:
    env = load_env(ENV_PATH)
    for k, v in env.items():
        os.environ.setdefault(k, v)
    # Shell / process env wins over .env (e.g. SITE_DIR=... python3 run.py ...)
    for k, v in os.environ.items():
        if v is not None and str(v).strip():
            env[k] = str(v).strip()

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
    p.add_argument(
        "--technical",
        action="store_true",
        help="Generate only technical_pages from keywords.json (footer legal pages).",
    )
    args = p.parse_args(argv)

    use_factory = site_factory_spec_enabled(env, cli_flag=bool(args.with_site_factory_spec))
    page_id_arg = (args.page_id or "").strip() or None

    if args.fix_density:
        run_fix_density(env, include_site_factory_spec=use_factory)
        return 0

    run_generate(
        env,
        include_site_factory_spec=use_factory,
        page_id=page_id_arg,
        technical_only=bool(args.technical),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
