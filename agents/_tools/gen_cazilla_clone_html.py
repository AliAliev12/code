#!/usr/bin/env python3
"""Generator: casino-lobby clone sites (5 content pages + 7 technical).

Reads SITE_DIR, SITE_URL, MAIN_CASINO_URL, TARGET_LOCALE from repo .env.
Preserves existing _output/keywords.json (only fixes site/locale fields).
"""
from __future__ import annotations

import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_AGENTS = ROOT / "agents"
if str(_AGENTS) not in sys.path:
    sys.path.insert(0, str(_AGENTS))

from _lib.locale_context import (  # noqa: E402
    LocaleContext,
    age_gate_body,
    footer_hub_tagline,
    hub_play_heading,
    hub_sidebar_compare_line,
    locale_context_from_env,
)
ENV_PATH = ROOT / ".env"
PICTURE_SRC = ROOT / "sites" / "cazilla-offerwall2-en-ie" / "assets" / "pictures"
R3_ASSETS = ROOT / "sites" / "cazilla-review3-en-ie" / "assets"


def _load_env(path: Path = ENV_PATH) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def resolve_targets(env: dict[str, str] | None = None) -> tuple[Path, str, str, str]:
    e = env if env is not None else _load_env()
    rel = (e.get("SITE_DIR") or "sites/cazilla-clone1-en-ie").strip().lstrip("/")
    origin = (e.get("SITE_URL") or "https://cazilla.life").strip().rstrip("/")
    main = (e.get("MAIN_CASINO_URL") or "https://cazilla.casino").strip().rstrip("/")
    return ROOT / rel, origin, Path(rel).name, main


SITE: Path = ROOT / "sites" / "cazilla-clone1-en-ie"
ORIGIN: str = "https://cazilla.life"
SITE_SLUG: str = "cazilla-clone1-en-ie"
MAIN: str = "https://cazilla.casino"
LOCALE: str = ""
HTML_LANG: str = ""
LC: LocaleContext | None = None
SITE_NAME: str = "Cazilla"
THEME_VARIANT: int = 1
MIN_AGE: int = 18
STUB = "Editorial placeholder. A2 will replace with keyword-rich copy."

SIDEBAR_NAV: list[tuple[str, str, str]] = []
MAIN_PAGES: list[tuple[str, str, str, str]] = []
FOOTER_LEGAL: list[tuple[str, str]] = []
TECH_SPECS: list[tuple[str, str, str, str, str, str]] = []

PAGE_KIND_BY_ID: dict[str, str] = {
    "home": "hub",
    "slots": "slots",
    "live": "live",
    "live-games": "live",
    "live-casino": "live",
    "casino-games": "tables",
    "about": "about",
    "bonus": "bonus",
    "welcome-bonus": "bonus",
    "bonuses-promo": "promo",
}


def _norm_rel_path(path: str) -> str:
    rel = str(path or "").strip().lstrip("/")
    return rel or "index.html"


def _esc_menu_label(raw: str) -> str:
    return html.escape(str(raw or "").strip())


def infer_page_kind(page_id: str, cluster: str = "") -> str:
    pid = str(page_id or "").strip()
    if pid in PAGE_KIND_BY_ID:
        return PAGE_KIND_BY_ID[pid]
    cl = str(cluster or "").lower()
    if "slot" in cl:
        return "slots"
    if "live" in cl:
        return "live"
    if "about" in cl:
        return "about"
    if "bonus" in cl or "promo" in cl:
        return "promo" if "promo" in cl else "bonus"
    if "casino" in cl or "table" in cl:
        return "tables"
    return "tables"


def load_bundle_from_keywords() -> None:
    global SIDEBAR_NAV, MAIN_PAGES, FOOTER_LEGAL, TECH_SPECS
    kw_path = SITE / "_output" / "keywords.json"
    if not kw_path.is_file():
        raise SystemExit(f"Missing keywords bundle: {kw_path}")
    data = json.loads(kw_path.read_text(encoding="utf-8"))
    pages_raw = data.get("pages") or []
    if not isinstance(pages_raw, list) or not pages_raw:
        raise SystemExit(f"No pages[] in {kw_path}")

    main_pages: list[tuple[str, str, str, str]] = []
    sidebar: list[tuple[str, str, str]] = []
    for p in pages_raw:
        if not isinstance(p, dict):
            continue
        pid = str(p.get("id") or "").strip()
        rel = _norm_rel_path(str(p.get("path") or ""))
        label = _esc_menu_label(str(p.get("menu_label") or pid.replace("-", " ").title()))
        kind = infer_page_kind(pid, str(p.get("cluster") or ""))
        if not pid or not rel:
            continue
        main_pages.append((pid, rel, label, kind))
        sidebar.append((pid, rel, label))

    tech_raw = data.get("technical_pages") or []
    tech_specs: list[tuple[str, str, str, str, str, str]] = []
    footer: list[tuple[str, str]] = []
    for p in tech_raw:
        if not isinstance(p, dict):
            continue
        slug = str(p.get("id") or "").strip()
        rel = _norm_rel_path(str(p.get("path") or ""))
        menu = str(p.get("menu_label") or slug.replace("-", " ").title())
        if not slug or not rel:
            continue
        title = f"{menu} | {SITE_NAME}"
        desc = f"{menu} for this {LC.region_facing_label} ({SITE_NAME} editorial hub)." if LC else f"{menu} | {SITE_NAME}"
        h1 = menu
        if LC and LC.lang == "fr":
            sub = f"{menu} — informations juridiques pour {LC.audience_phrase}, sans conseil juridique."
        else:
            sub = f"Plain-language {menu.lower()} — not legal advice."
        tech_specs.append((slug, rel, title, desc, html.escape(h1), html.escape(sub)))
        footer.append((rel, html.escape(menu)))

    if not main_pages:
        raise SystemExit(f"No valid content pages in {kw_path}")
    if not tech_specs:
        raise SystemExit(f"No technical_pages in {kw_path}")

    MAIN_PAGES = main_pages
    SIDEBAR_NAV = sidebar
    FOOTER_LEGAL = footer
    TECH_SPECS = tech_specs


def init_site(env: dict[str, str] | None = None) -> None:
    global SITE, ORIGIN, SITE_SLUG, MAIN, LOCALE, HTML_LANG, LC, THEME_VARIANT, MIN_AGE, STUB, SITE_NAME
    SITE, ORIGIN, SITE_SLUG, MAIN = resolve_targets(env)
    e = env if env is not None else _load_env()
    LC = locale_context_from_env(e, strict_keywords_match=False)
    LOCALE = LC.locale
    HTML_LANG = LOCALE.replace("_", "-") if "_" in LOCALE else LOCALE
    MIN_AGE = 21 if LC.geo.upper() == "BE" else 18
    slug_lower = SITE_SLUG.lower()
    if "fr-be" in slug_lower or slug_lower.endswith("-fr-be"):
        THEME_VARIANT = 4
    elif "clone3" in slug_lower:
        THEME_VARIANT = 3
    elif "clone2" in slug_lower:
        THEME_VARIANT = 2
    else:
        THEME_VARIANT = 1
    if LC.lang == "fr":
        STUB = "Texte éditorial provisoire. A2 remplacera par un contenu optimisé pour la Belgique."
        if "fr-be" in slug_lower:
            SITE_NAME = "Cazilla Belgique"
    load_bundle_from_keywords()


def theme_body_class() -> str:
    base = "cl-layout"
    return f"{base} cl-theme-v{THEME_VARIANT}" if THEME_VARIANT > 1 else base


def cookie_js_prefix() -> str:
    safe = re.sub(r"[^a-z0-9_]+", "_", SITE_SLUG.lower()).strip("_")
    return safe[:48] or "cazilla_clone"

SLOT_ITEMS = [
    ("Book of Dead", "assets/pictures/big-bass-bonanza-review.avif"),
    ("Gates of Olympus", "assets/pictures/fruit-classic-slot.png"),
    ("Sweet Bonanza", "assets/pictures/bonus-promo-artwork.webp"),
    ("Razor Shark", "assets/pictures/money-train-4-thumbnail.png"),
    ("Starburst", "assets/pictures/casino-feature-visual.png"),
    ("Big Bass Bonanza", "assets/pictures/slots-showcase.png"),
]

LIVE_ITEMS = [
    ("Live Roulette A", "assets/pictures/live-tables.jpg", "1 – 5000"),
    ("Lightning Blackjack", "assets/pictures/blackjack-green-table.jpg", "5 – 10000"),
    ("Speed Baccarat", "assets/pictures/baccarat-live-table.webp", "2+"),
    ("Crazy Time", "assets/pictures/crazy-time-bonus.jpg", "0.1+"),
    ("Immersive Roulette", "assets/pictures/live-tables.jpg", "0.5+"),
    ("Monopoly Live", "assets/pictures/crazy-time-bonus.jpg", "0.1+"),
]

TABLE_ITEMS = [
    ("European Roulette", "assets/pictures/live-tables.jpg"),
    ("American Blackjack", "assets/pictures/blackjack-green-table.jpg"),
    ("Oasis Poker", "assets/pictures/casino-feature-visual.png"),
    ("Mini Baccarat", "assets/pictures/baccarat-bonus-terms.webp"),
    ("Jacks or Better", "assets/pictures/fruit-classic-slot.png"),
    ("Sic Bo", "assets/pictures/rocket-crash-game.png"),
]


def compliance_block() -> str:
    if LC is None:
        raise RuntimeError("init_site() must run before compliance_block()")
    if MIN_AGE >= 21 and LC.lang == "fr":
        return (
            '<div class="complianceOverlay" id="ageGate" role="dialog" aria-modal="true" aria-labelledby="ageTitle">\n'
            '  <div class="complianceDialog">\n'
            '    <h2 id="ageTitle">Confirmez que vous avez 21 ans ou plus</h2>\n'
            "    <p>Ce site traite des jeux d'argent réglementés pour lecteurs en Belgique. "
            "Vous devez avoir au moins 21 ans pour continuer.</p>\n"
            '    <div class="complianceActions">\n'
            '      <button type="button" class="btn" id="ageUnder">J\'ai moins de 21 ans</button>\n'
            '      <button type="button" class="btn primary" id="ageOk">J\'ai 21 ans ou plus</button>\n'
            "    </div>\n  </div>\n</div>\n"
            '<div class="complianceOverlay" id="cookieGate" hidden aria-hidden="true" role="dialog" '
            'aria-modal="true" aria-labelledby="cookieTitle">\n'
            '  <div class="complianceDialog">\n'
            '    <h2 id="cookieTitle">Préférences cookies</h2>\n'
            "    <p>Nous utilisons des cookies pour mémoriser la vérification d'âge. "
            'Voir <a href="cookie-policy.html">politique de cookies</a>.</p>\n'
            '    <div class="complianceActions">\n'
            '      <button type="button" class="btn" id="cookieReject">Essentiels uniquement</button>\n'
            '      <button type="button" class="btn primary" id="cookieAccept">Accepter</button>\n'
            "    </div>\n  </div>\n</div>"
        )
    age_gate_line = html.escape(age_gate_body(LC))
    if LC.lang == "fr":
        cookie_title, cookie_reject, cookie_accept = "Préférences cookies", "Essentiels uniquement", "Accepter"
        cookie_p = 'Voir <a href="cookie-policy.html">politique de cookies</a>.'
        under, ok = f"J'ai moins de {MIN_AGE} ans", f"J'ai {MIN_AGE} ans ou plus"
        age_title = f"Confirmez que vous avez {MIN_AGE} ans ou plus"
    else:
        cookie_title, cookie_reject, cookie_accept = "Cookie preferences", "Essential only", "Accept"
        cookie_p = 'See <a href="cookie-policy.html">cookie policy</a>.'
        under, ok = f"I am under {MIN_AGE}", f"I am {MIN_AGE} or over"
        age_title = f"Confirm you are {MIN_AGE} or over"
    return f"""<div class="complianceOverlay" id="ageGate" role="dialog" aria-modal="true" aria-labelledby="ageTitle">
  <div class="complianceDialog">
    <h2 id="ageTitle">{html.escape(age_title)}</h2>
    <p>{age_gate_line}</p>
    <div class="complianceActions">
      <button type="button" class="btn" id="ageUnder">{html.escape(under)}</button>
      <button type="button" class="btn primary" id="ageOk">{html.escape(ok)}</button>
    </div>
  </div>
</div>
<div class="complianceOverlay" id="cookieGate" hidden aria-hidden="true" role="dialog" aria-modal="true" aria-labelledby="cookieTitle">
  <div class="complianceDialog">
    <h2 id="cookieTitle">{html.escape(cookie_title)}</h2>
    <p>{cookie_p}</p>
    <div class="complianceActions">
      <button type="button" class="btn" id="cookieReject">{html.escape(cookie_reject)}</button>
      <button type="button" class="btn primary" id="cookieAccept">{html.escape(cookie_accept)}</button>
    </div>
  </div>
</div>"""


def actions_html() -> str:
    m = html.escape(MAIN)
    if LC and LC.lang == "fr":
        return f"""    <a class="btn" href="{m}" rel="noopener noreferrer" target="_blank">Connexion</a>
    <a class="btn primary" href="{m}" rel="noopener noreferrer" target="_blank">Jouer sur Cazilla</a>"""
    return f"""    <a class="btn" href="{m}" rel="noopener noreferrer" target="_blank">Log in</a>
    <a class="btn primary" href="{m}" rel="noopener noreferrer" target="_blank">Play at Cazilla</a>"""


def fineprint_line() -> str:
    m = html.escape(MAIN)
    if LC and LC.lang == "fr":
        return f"{MIN_AGE}+ | Jeu responsable | <a href=\"{m}\" rel=\"noopener noreferrer\" target=\"_blank\">Visiter Cazilla</a>"
    return f"{MIN_AGE}+ | Play responsibly | <a href=\"{m}\" rel=\"noopener noreferrer\" target=\"_blank\">Visit Cazilla</a>"


def sidebar_nav(active_id: str) -> str:
    lines = []
    for pid, href, label in SIDEBAR_NAV:
        cur = ' aria-current="page"' if pid == active_id else ""
        cls = " is-active" if pid == active_id else ""
        lines.append(f'      <a class="cl-navItem{cls}" href="{href}"{cur}>{label}</a>')
    return "\n".join(lines)


def head_block(rel_path: str, title: str, description: str) -> str:
    canonical = f"{ORIGIN}/" if rel_path == "index.html" else f"{ORIGIN}/{rel_path}"
    return f"""<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title data-a2-field="meta_title">{html.escape(title)}</title>
<meta name="description" data-a2-field="meta_description" content="{html.escape(description)}" />
<meta name="robots" content="index, follow" />
<link rel="canonical" href="{html.escape(canonical)}" />
<link rel="alternate" hreflang="{html.escape(HTML_LANG)}" href="{html.escape(canonical)}" />
<link rel="alternate" hreflang="x-default" href="{html.escape(canonical)}" />
<meta property="og:title" content="{html.escape(title)}" />
<meta property="og:description" content="{html.escape(description)}" />
<meta property="og:url" content="{html.escape(canonical)}" />
<meta property="og:type" content="website" />
<meta property="og:locale" content="{html.escape(HTML_LANG.replace('-', '_'))}" />
<meta property="og:image" content="{ORIGIN}/assets/pictures/og-logo.svg" />
<script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "WebSite",
    "name": "{html.escape(SITE_NAME)}",
    "url": "{html.escape(ORIGIN)}/"
  }}
</script>
<link rel="stylesheet" href="assets/cl-shell.css" />
<link rel="stylesheet" href="assets/cl-page.css" />
<link rel="stylesheet" href="assets/cl-compliance.css" />"""


def footer_legal(current: str | None = None) -> str:
    parts = []
    for href, lab in FOOTER_LEGAL:
        cur = ' aria-current="page"' if current and href == current else ""
        parts.append(f'      <a href="{href}"{cur}>{lab}</a>')
    return "\n".join(parts)


def game_card(name: str, img: str, *, stakes: str = "") -> str:
    stakes_html = f'<p class="cl-cardStakes">{html.escape(stakes)}</p>' if stakes else ""
    m = html.escape(MAIN)
    return f"""    <article class="cl-gameCard">
      <div class="cl-cardThumb"><img src="{html.escape(img)}" alt="{html.escape(name)} preview" width="320" height="180" loading="lazy" decoding="async" /></div>
      <h3 class="cl-cardTitle">{html.escape(name)}</h3>
      {stakes_html}
      <motion class="cl-cardActions">
        <a class="btn primary" href="{m}" rel="noopener noreferrer" target="_blank">Play</a>
        <a class="btn" href="{m}" rel="noopener noreferrer" target="_blank">Demo</a>
      </div>
    </article>""".replace("<motion class", "<div class").replace("</motion>", "</div>")


def slots_body() -> str:
    cards = "\n".join(game_card(n, img) for n, img in SLOT_ITEMS)
    m = html.escape(MAIN)
    return f"""
      <section class="cl-promoBanner" aria-label="Welcome offer">
        <div class="cl-bannerInner">
          <h2>Welcome bonus 100% + 200 free spins</h2>
          <p>Claim on the official site — terms apply.</p>
          <a class="btn primary" href="{m}" rel="noopener noreferrer" target="_blank">Claim at Cazilla</a>
        </div>
      </section>
      <div class="cl-toolbar">
        <label class="cl-tool"><span class="cl-toolLabel">Search slots</span><input type="search" placeholder="Search slot…" /></label>
        <label class="cl-tool">Provider <select><option>All</option></select></label>
        <label class="cl-tool">Sort <select><option>Popular</option></select></label>
      </div>
      <div class="cl-tags">
        <span class="cl-tag">All</span><span class="cl-tag">New</span><span class="cl-tag">Buy bonus</span><span class="cl-tag">Megaways</span><span class="cl-tag">Books</span>
      </div>
      <div class="cl-gameGrid">
{cards}
      </div>
      <p class="cl-more"><a class="btn" href="{m}" rel="noopener noreferrer" target="_blank">Show more on Cazilla</a></p>"""


def live_body() -> str:
    cards = "\n".join(game_card(n, img, stakes=f"Stakes: {s}") for n, img, s in LIVE_ITEMS)
    return f"""
      <div class="cl-toolbar">
        <label class="cl-tool"><span class="cl-toolLabel">Search live games</span><input type="search" placeholder="Game or provider…" /></label>
        <span class="cl-filterGroup">Filter: <button type="button" class="cl-tag is-active">All</button> <button type="button" class="cl-tag">Popular</button></span>
      </div>
      <div class="cl-tags">
        <span class="cl-tag">All</span><span class="cl-tag">Roulette</span><span class="cl-tag">Blackjack</span><span class="cl-tag">Baccarat</span><span class="cl-tag">Game shows</span>
      </div>
      <div class="cl-gameGrid">
{cards}
      </motion>""".replace('<motion class="cl-gameGrid">', "").replace("</motion>", "")


def live_body_fixed() -> str:
    cards = "\n".join(game_card(n, img, stakes=f"Stakes: {s}") for n, img, s in LIVE_ITEMS)
    return f"""
      <div class="cl-toolbar">
        <label class="cl-tool"><span class="cl-toolLabel">Search live games</span><input type="search" placeholder="Game or provider…" /></label>
        <span class="cl-filterGroup">Filter: <button type="button" class="cl-tag is-active">All</button> <button type="button" class="cl-tag">Popular</button></span>
      </div>
      <div class="cl-tags">
        <span class="cl-tag">All</span><span class="cl-tag">Roulette</span><span class="cl-tag">Blackjack</span><span class="cl-tag">Baccarat</span><span class="cl-tag">Game shows</span>
      </div>
      <div class="cl-gameGrid">
{cards}
      </div>"""


def tables_body() -> str:
    cards = "\n".join(game_card(n, img) for n, img in TABLE_ITEMS)
    return f"""
      <div class="cl-toolbar">
        <label class="cl-tool"><span class="cl-toolLabel">Search game</span><input type="search" placeholder="Search by name…" /></label>
        <label class="cl-tool">Provider <select><option>All brands</option></select></label>
      </div>
      <div class="cl-tags">
        <span class="cl-tag">All</span><span class="cl-tag">Roulette</span><span class="cl-tag">Cards</span><span class="cl-tag">Poker</span><span class="cl-tag">Video poker</span>
      </div>
      <div class="cl-gameGrid">
{cards}
      </div>"""


def bonus_body() -> str:
    m = html.escape(MAIN)
    return f"""
      <section class="cl-bonusPanel">
        <label class="cl-promoRow">Promo code <input type="text" placeholder="EXTRA50" /> <a class="btn" href="{m}" rel="noopener noreferrer" target="_blank">Apply on Cazilla</a></label>
        <article class="cl-activeBonus">
          <h2>Active bonus (example)</h2>
          <p>Welcome match 100% — wagering example x35.</p>
          <div class="cl-progress" role="progressbar" aria-valuenow="60" aria-valuemin="0" aria-valuemax="100"><span style="width:60%"></span></motion>
          <p class="cl-muted">48 hours remaining — manage on the operator site.</p>
          <a class="btn" href="{m}" rel="noopener noreferrer" target="_blank">Manage bonuses at Cazilla</a>
        </article>
        <ul class="cl-bonusList">
          <li>20 free spins — <a href="{m}" rel="noopener noreferrer" target="_blank">Activate</a></li>
          <li>Birthday offer — <a href="{m}" rel="noopener noreferrer" target="_blank">Check eligibility</a></li>
        </ul>
      </section>""".replace("</span></motion>", "</span></motion>").replace(
        '<span style="width:60%"></span></motion>', '<span style="width:60%"></span></div>'
    )



def home_hub_body() -> str:
    m = html.escape(MAIN)
    hub_cards = []
    for pid, href, label in SIDEBAR_NAV:
        if pid == "home":
            continue
        hub_cards.append(
            f'        <a class="cl-hubCard" href="{html.escape(href)}"><h3>{label}</h3>'
            f'<p>Open section</p><span class="cl-hubArrow" aria-hidden="true">→</span></a>'
        )
    featured = "\n".join(game_card(n, img) for n, img in SLOT_ITEMS[:4])
    return f"""
      <section class="cl-promoBanner cl-promoBannerHub" aria-label="Featured">
        <div class="cl-bannerInner">
          <h2>{html.escape(hub_play_heading(LC))}</h2>
          <p>Independent editorial guides — all play links go to the official operator.</p>
          <a class="btn primary" href="{m}" rel="noopener noreferrer" target="_blank">Go to Cazilla</a>
        </div>
      </section>
      <div class="cl-hubGrid">
{chr(10).join(hub_cards)}
      </div>
      <h2 class="cl-sectionTitle">Popular picks</h2>
      <div class="cl-gameGrid cl-gameGridCompact">
{featured}
      </div>"""


def about_body() -> str:
    m = html.escape(MAIN)
    return f"""
      <div class="cl-aboutGrid">
        <article class="cl-aboutCard">
          <h2>Independent editorial</h2>
          <p>{html.escape(hub_sidebar_compare_line(LC))}</p>
        </article>
        <article class="cl-aboutCard">
          <h2>Safer play first</h2>
          <p>18+ only. Use licensed sites and national support if gambling stops being fun.</p>
        </article>
        <article class="cl-aboutCard">
          <h2>Official play</h2>
          <p>All Play buttons link to <a href="{m}" rel="noopener noreferrer" target="_blank">Cazilla</a> where terms apply.</p>
        </article>
      </div>"""


def promo_body() -> str:
    m = html.escape(MAIN)
    return f"""
      <div class="cl-toolbar"><span class="cl-filterGroup">Filter: <button type="button" class="cl-tag is-active">All</button> <button type="button" class="cl-tag">New players</button> <button type="button" class="cl-tag">Regulars</button> <button type="button" class="cl-tag">Tournaments</button></span></div>
      <div class="cl-promoGrid">
        <article class="cl-promoCard cl-promoHero">
          <h2>Welcome package</h2>
          <p>Up to 1500 EUR + 150 free spins on first deposits.</p>
          <a class="btn primary" href="{m}" rel="noopener noreferrer" target="_blank">Activate</a>
        </article>
        <article class="cl-promoCard"><h3>Weekly reload</h3><p>50% Friday reload.</p><a class="btn" href="{m}" rel="noopener noreferrer" target="_blank">Claim</a></article>
        <article class="cl-promoCard"><h3>10% cashback</h3><p>Weekly cashback on net losses.</p><a class="btn" href="{m}" rel="noopener noreferrer" target="_blank">Get cashback</a></article>
        <article class="cl-promoCard"><h3>Crypto bonus 150%</h3><p>Deposit with USDT.</p><a class="btn" href="{m}" rel="noopener noreferrer" target="_blank">Deposit</a></article>
        <article class="cl-promoCard"><h3>Tournament week</h3><p>Prize pool €50,000.</p><a class="btn" href="{m}" rel="noopener noreferrer" target="_blank">Join</a></article>
      </div>"""


BODY_BY_KIND = {
    "hub": home_hub_body,
    "slots": slots_body,
    "live": live_body_fixed,
    "tables": tables_body,
    "about": about_body,
    "bonus": bonus_body,
    "promo": promo_body,
}


def page_html(page_id: str, rel: str, menu_label: str, kind: str) -> str:
    title = f"{menu_label.replace('&amp;', '&')} | {SITE_NAME} — {LC.region_name}"
    desc = f"{menu_label.replace('&amp;', '&')} — editorial hub for {LC.audience_phrase}."
    h1 = menu_label.replace("&amp;", "&")
    body_fn = BODY_BY_KIND.get(kind, tables_body)
    body = body_fn()
    footer_cur = rel if rel != "index.html" else None
    m = html.escape(MAIN)
    return f"""<!doctype html>
<html lang="{html.escape(HTML_LANG)}" data-site-kind="clone" data-min-gambling-age="{MIN_AGE}">
  <head>
{head_block(rel, title, desc)}
  </head>
  <body class="{theme_body_class()}">
{compliance_block()}
<div id="siteContent" class="cl-app">
  <header class="cl-topbar">
    <a class="cl-brand" href="index.html"><span class="cl-logoMark">C</span><span class="cl-logoWord">{html.escape(SITE_NAME.upper())}</span></a>
    <div class="cl-topActions">
{actions_html()}
      <button type="button" class="btn icon cl-menuBtn" id="clMenuBtn" aria-label="Open menu">≡</button>
    </div>
  </header>
  <div class="cl-grid">
    <aside class="cl-sidebar" id="clSidebar" aria-label="Sidebar">
      <p class="cl-sideSearch"><label class="visually-hidden" for="siteSearch">Search site</label><input id="siteSearch" type="search" placeholder="Search the site…" /></p>
      <nav class="cl-sidebarNav" aria-label="Site sections">
{sidebar_nav(page_id)}
      </nav>
      <p class="cl-sideMeta"><span>Language: {html.escape(LOCALE)}</span></p>
      <p class="cl-sideMeta"><a href="{m}" rel="noopener noreferrer" target="_blank">Support chat on Cazilla</a></p>
    </aside>
    <main class="cl-main" id="top">
      <section class="cl-pageHero">
        <h1 data-a2-field="page_h1">{html.escape(h1)}</h1>
        <p class="cl-lead" data-a2-field="page_lead">{html.escape(STUB)}</p>
      </section>
{body}
      <div class="cl-seoProse" data-a2-field="main_seo_html">
        <p>{html.escape(STUB)}</p>
      </div>
      <p class="cl-fineprint" data-a2-field="footer_note">{fineprint_line()}</p>
    </main>
  </div>
  <footer class="cl-footer">
    <nav class="cl-footerLegal" aria-label="Legal pages">
{footer_legal(footer_cur)}
    </nav>
    <p class="cl-copy">{footer_hub_tagline(html.escape(SITE_NAME), LC)}</p>
  </footer>
</div>
<script src="assets/cl-site.js" defer></script>
  </body>
</html>"""


def tech_body(slug: str) -> str:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "gen_r3", ROOT / "agents" / "_tools" / "gen_cazilla_review3_en_ie_html.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    body = mod.tech_body(slug)
    return body.replace("Cazilla Player Voices", SITE_NAME)


def tech_page_html(rel: str, title: str, description: str, h1: str, hero_sub: str, slug: str) -> str:
    body = tech_body(slug)
    return f"""<!doctype html>
<html lang="{html.escape(HTML_LANG)}" data-site-kind="clone" data-min-gambling-age="{MIN_AGE}">
  <head>
{head_block(rel, title, description)}
  </head>
  <body class="{theme_body_class()} innerPage">
{compliance_block()}
<div id="siteContent" class="cl-app">
  <header class="cl-topbar">
    <a class="cl-brand" href="index.html"><span class="cl-logoMark">C</span><span class="cl-logoWord">{html.escape(SITE_NAME.upper())}</span></a>
    <div class="cl-topActions">{actions_html()}</div>
  </header>
  <main class="cl-main cl-mainLegal">
    <section class="hero" aria-label="Hero">
      <div class="heroInner">
        <h1>{html.escape(h1)}</h1>
        <p class="subtitle">{html.escape(hero_sub)}</p>
      </div>
    </section>
    <motion class="policyCard">{body}</div>
    <p class="fineprint" style="margin: 24px 0"><a href="index.html">Back to home</a></p>
  </main>
  <footer class="cl-footer">
    <nav class="cl-footerLegal" aria-label="Legal pages">
{footer_legal(rel)}
    </nav>
    <p class="cl-copy">© <span id="year">2026</span> {html.escape(SITE_NAME)}.</p>
  </footer>
</div>
<script src="assets/cl-site.js" defer></script>
  </body>
</html>""".replace('<motion class="policyCard">', '<motion class="policyCard">'.replace(
        '<motion class="policyCard">', '<div class="policyCard">'
    )).replace("</motion>", "</div>", 1)


def tech_page_html_fixed(rel: str, title: str, description: str, h1: str, hero_sub: str, slug: str) -> str:
    body = tech_body(slug)
    return f"""<!doctype html>
<html lang="{html.escape(HTML_LANG)}" data-site-kind="clone" data-min-gambling-age="{MIN_AGE}">
  <head>
{head_block(rel, title, description)}
  </head>
  <body class="{theme_body_class()} innerPage">
{compliance_block()}
<div id="siteContent" class="cl-app">
  <header class="cl-topbar">
    <a class="cl-brand" href="index.html"><span class="cl-logoMark">C</span><span class="cl-logoWord">{html.escape(SITE_NAME.upper())}</span></a>
    <div class="cl-topActions">{actions_html()}</motion>
  </header>
  <main class="cl-main cl-mainLegal">
    <section class="hero" aria-label="Hero">
      <div class="heroInner">
        <h1>{html.escape(h1)}</h1>
        <p class="subtitle">{html.escape(hero_sub)}</p>
      </div>
    </section>
    <div class="policyCard">{body}</div>
    <p class="fineprint" style="margin: 24px 0"><a href="index.html">Back to home</a></p>
  </main>
  <footer class="cl-footer">
    <nav class="cl-footerLegal" aria-label="Legal pages">
{footer_legal(rel)}
    </nav>
    <p class="cl-copy">© <span id="year">2026</span> {html.escape(SITE_NAME)}.</p>
  </footer>
</div>
<script src="assets/cl-site.js" defer></script>
  </body>
</html>""".replace("</motion>\n  </header>", "</div>\n  </header>")


CL_PAGE_CSS = """
:root {
  --cl-accent: #22c55e;
  --cl-accent2: #a855f7;
  --cl-bg: #0f1419;
  --cl-panel: #151b23;
  --cl-line: rgba(255,255,255,0.08);
  --cl-text: #f1f5f9;
  --cl-muted: #94a3b8;
}
body.cl-layout { margin: 0; background: var(--cl-bg); color: var(--cl-text); font-family: system-ui, sans-serif; }
.cl-app { min-height: 100vh; display: flex; flex-direction: column; }
.cl-topbar { display: flex; align-items: center; justify-content: space-between; padding: 12px 18px; background: #0b0f14; border-bottom: 1px solid var(--cl-line); position: sticky; top: 0; z-index: 40; }
.cl-brand { display: flex; align-items: center; gap: 10px; text-decoration: none; color: inherit; font-weight: 800; }
.cl-logoMark { width: 32px; height: 32px; border-radius: 8px; background: linear-gradient(135deg, var(--cl-accent), var(--cl-accent2)); display: inline-flex; align-items: center; justify-content: center; }
.cl-topActions { display: flex; gap: 8px; align-items: center; }
.cl-grid { display: grid; grid-template-columns: 240px minmax(0, 1fr); flex: 1; max-width: 1400px; width: 100%; margin: 0 auto; }
.cl-sidebar { background: var(--cl-panel); border-right: 1px solid var(--cl-line); padding: 16px 14px; }
.cl-sidebarNav { display: flex; flex-direction: column; gap: 4px; }
.cl-navItem { padding: 8px 10px; border-radius: 8px; text-decoration: none; color: var(--cl-text); font-size: 14px; }
.cl-navItem.is-active, .cl-navItem:hover { background: rgba(34,197,94,0.15); color: #bbf7d0; }
.cl-sideSearch input { width: 100%; margin: 8px 0 14px; padding: 8px 10px; border-radius: 8px; border: 1px solid var(--cl-line); background: #0b0f14; color: var(--cl-text); }
.cl-sideMeta { font-size: 12px; color: var(--cl-muted); margin: 8px 0; }
.cl-main { padding: 20px 22px 32px; min-width: 0; }
.cl-pageHero h1 { margin: 0 0 8px; font-size: clamp(1.5rem, 2vw, 2rem); }
.cl-lead { color: var(--cl-muted); margin: 0 0 18px; max-width: 70ch; line-height: 1.6; }
.cl-seoProse { margin-top: 24px; padding: 18px; background: rgba(255,255,255,0.03); border: 1px solid var(--cl-line); border-radius: 12px; }
.cl-seoProse p, .cl-seoProse li { line-height: 1.7; color: #cbd5e1; }
.cl-promoBanner { background: linear-gradient(90deg, #14532d, #3b0764); border-radius: 12px; padding: 18px; margin-bottom: 18px; }
.cl-toolbar { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 12px; }
.cl-tags { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
.cl-tag { font-size: 12px; padding: 6px 10px; border-radius: 999px; background: #1e293b; border: none; color: inherit; cursor: pointer; }
.cl-tag.is-active { background: var(--cl-accent); color: #052e16; }
.cl-gameGrid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 14px; margin-bottom: 16px; }
.cl-gameCard { background: var(--cl-panel); border: 1px solid var(--cl-line); border-radius: 12px; overflow: hidden; }
.cl-cardThumb img { width: 100%; height: 120px; object-fit: cover; display: block; }
.cl-cardTitle { margin: 10px 12px 6px; font-size: 15px; }
.cl-cardStakes { margin: 0 12px; font-size: 12px; color: var(--cl-muted); }
.cl-cardActions { display: flex; gap: 8px; padding: 0 12px 12px; }
.cl-promoGrid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 14px; }
.cl-promoCard { background: var(--cl-panel); border: 1px solid var(--cl-line); border-radius: 12px; padding: 16px; }
.cl-promoHero { grid-column: span 2; background: linear-gradient(135deg, #1e3a5f, #312e81); }
@media (max-width: 720px) { .cl-promoHero { grid-column: span 1; } }
.cl-bonusPanel { background: var(--cl-panel); border-radius: 12px; padding: 18px; border: 1px solid var(--cl-line); }
.cl-activeBonus { margin: 16px 0; padding: 14px; background: rgba(0,0,0,0.2); border-radius: 10px; }
.cl-progress { height: 10px; background: #1e293b; border-radius: 999px; overflow: hidden; margin: 10px 0; }
.cl-progress span { display: block; height: 100%; background: var(--cl-accent); }
.cl-footer { margin-top: auto; padding: 20px 22px; border-top: 1px solid var(--cl-line); background: #0b0f14; }
.cl-footerLegal { display: flex; flex-wrap: wrap; gap: 12px 16px; margin-bottom: 10px; }
.cl-footerLegal a { color: var(--cl-muted); font-size: 13px; text-decoration: none; }
.cl-footerLegal a:hover { color: var(--cl-text); }
.btn { display: inline-flex; align-items: center; justify-content: center; padding: 8px 14px; border-radius: 8px; border: 1px solid var(--cl-line); background: #1e293b; color: inherit; text-decoration: none; font-size: 14px; cursor: pointer; }
.btn.primary { background: var(--cl-accent); border-color: transparent; color: #052e16; font-weight: 700; }
.cl-fineprint { font-size: 13px; color: var(--cl-muted); margin-top: 20px; }
body.innerPage .policyCard { max-width: 900px; margin: 0 auto; padding: 0 8px; }
body.innerPage .policyCard p { line-height: 1.7; color: #cbd5e1; }
body.innerPage .hero { padding: 24px 8px 8px; }
body.innerPage .subtitle { color: var(--cl-muted); }
.visually-hidden { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0,0,0,0); }
@media (max-width: 900px) {
  .cl-grid { grid-template-columns: 1fr; }
  .cl-sidebar { position: fixed; inset: 0 auto 0 0; width: min(280px, 88vw); z-index: 50; transform: translateX(-105%); transition: transform .2s; }
  .cl-sidebar[data-open="true"] { transform: translateX(0); }
  .cl-menuBtn { display: inline-flex !important; }
}
.cl-menuBtn { display: none; }
.cl-hubGrid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; margin-bottom: 20px; }
.cl-hubCard { display: block; padding: 14px; border-radius: 12px; border: 1px solid var(--cl-line); background: var(--cl-panel); text-decoration: none; color: inherit; }
.cl-hubCard h3 { margin: 0 0 6px; font-size: 15px; }
.cl-hubCard p { margin: 0; font-size: 12px; color: var(--cl-muted); }
.cl-hubArrow { float: right; color: var(--cl-accent); }
.cl-sectionTitle { margin: 8px 0 12px; font-size: 1.1rem; }
.cl-aboutGrid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 14px; }
.cl-aboutCard { padding: 16px; border-radius: 12px; border: 1px solid var(--cl-line); background: var(--cl-panel); }
"""

CL_THEME_V2_CSS = """
body.cl-theme-v2 {
  --cl-accent: #f59e0b;
  --cl-accent2: #3b82f6;
  --cl-bg: #12121a;
  --cl-panel: #1a1a24;
}
body.cl-theme-v2 .cl-grid {
  grid-template-columns: minmax(0, 1fr) min(196px, 24vw);
}
body.cl-theme-v2 .cl-main { grid-column: 1; min-width: 0; }
body.cl-theme-v2 .cl-sidebar {
  grid-column: 2;
  border-right: none;
  border-left: 1px solid var(--cl-line);
  padding: 14px 12px;
}
body.cl-theme-v2 .cl-navItem.is-active,
body.cl-theme-v2 .cl-navItem:hover { background: rgba(245, 158, 11, 0.16); color: #fde68a; }
body.cl-theme-v2 .btn.primary { color: #1c1917; }
body.cl-theme-v2 .cl-promoBanner { background: linear-gradient(125deg, #1e3a8a 0%, #7c2d12 100%); }
body.cl-theme-v2 .cl-gameCard { border-radius: 16px; }
body.cl-theme-v2 .cl-topbar { background: linear-gradient(90deg, #0f172a, #1e1b4b); }
body.cl-theme-v2 .cl-hubCard { border-radius: 14px; }
@media (max-width: 900px) {
  body.cl-theme-v2 .cl-main,
  body.cl-theme-v2 .cl-sidebar { grid-column: auto; }
}
"""

CL_THEME_V3_CSS = """
body.cl-theme-v3 {
  --cl-accent: #ec4899;
  --cl-accent2: #06b6d4;
  --cl-bg: #0a0f1a;
  --cl-panel: #111827;
}
body.cl-theme-v3 .cl-grid {
  grid-template-columns: 1fr;
  grid-template-rows: auto minmax(0, 1fr);
}
body.cl-theme-v3 .cl-sidebar {
  border-right: none;
  border-bottom: 1px solid var(--cl-line);
  padding: 10px 16px 12px;
}
body.cl-theme-v3 .cl-sidebarNav {
  flex-direction: row;
  flex-wrap: wrap;
  gap: 6px;
}
body.cl-theme-v3 .cl-sideSearch,
body.cl-theme-v3 .cl-sideMeta { display: none; }
body.cl-theme-v3 .cl-navItem {
  font-size: 13px;
  padding: 6px 12px;
  border: 1px solid transparent;
}
body.cl-theme-v3 .cl-navItem.is-active,
body.cl-theme-v3 .cl-navItem:hover {
  background: rgba(236, 72, 153, 0.14);
  color: #fbcfe8;
  border-color: rgba(236, 72, 153, 0.35);
}
body.cl-theme-v3 .cl-topbar {
  background: linear-gradient(90deg, #0f172a 0%, #312e81 50%, #831843 100%);
}
body.cl-theme-v3 .cl-logoMark {
  border-radius: 50%;
  background: linear-gradient(135deg, var(--cl-accent), var(--cl-accent2));
}
body.cl-theme-v3 .btn.primary { color: #1e1b4b; }
body.cl-theme-v3 .cl-promoBanner {
  background: linear-gradient(120deg, #134e4a 0%, #701a75 55%, #0e7490 100%);
  border: 1px solid rgba(6, 182, 212, 0.25);
}
body.cl-theme-v3 .cl-gameCard {
  border-radius: 10px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
}
body.cl-theme-v3 .cl-hubCard {
  border-radius: 10px;
  border-left: 3px solid var(--cl-accent);
}
body.cl-theme-v3 .cl-main { padding: 18px 20px 28px; }
body.cl-theme-v3 .cl-seoProse {
  border-radius: 10px;
  border-color: rgba(6, 182, 212, 0.2);
}
@media (max-width: 900px) {
  body.cl-theme-v3 .cl-sidebar {
    position: static;
    width: auto;
    transform: none;
  }
  body.cl-theme-v3 .cl-sidebarNav { overflow-x: auto; flex-wrap: nowrap; }
}
"""

CL_THEME_V4_CSS = """
body.cl-theme-v4 {
  --cl-accent: #c9a227;
  --cl-accent2: #2d6a4f;
  --cl-bg: #14161c;
  --cl-panel: #1c1f28;
  --cl-line: rgba(201, 162, 39, 0.12);
  --cl-text: #f5f0e8;
  --cl-muted: #a8a29e;
}
body.cl-theme-v4 .cl-topbar {
  background: #0f1115;
  border-bottom: 2px solid var(--cl-accent);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.35);
}
body.cl-theme-v4 .cl-logoMark {
  border-radius: 6px;
  background: linear-gradient(145deg, var(--cl-accent), #8b6914);
  color: #1a1a1a;
  font-weight: 900;
}
body.cl-theme-v4 .cl-grid {
  grid-template-columns: min(168px, 15vw) minmax(0, 1fr);
  gap: 0;
  max-width: min(1440px, 100%);
}
body.cl-theme-v4 .cl-main {
  grid-column: 2;
  min-width: 0;
  padding: 22px clamp(18px, 2.5vw, 36px) 32px;
}
body.cl-theme-v4 .cl-sidebar {
  grid-column: 1;
  border-right: 1px solid var(--cl-line);
  border-left: none;
  background: linear-gradient(180deg, #1a1d24 0%, #14161c 100%);
  padding: 14px 10px;
  width: auto;
  max-width: 168px;
}
body.cl-theme-v4 .cl-sideSearch input {
  font-size: 13px;
  padding: 6px 8px;
}
body.cl-theme-v4 .cl-sideMeta {
  font-size: 11px;
  line-height: 1.35;
}
body.cl-theme-v4 .cl-navItem {
  border-left: 3px solid transparent;
  border-radius: 0 8px 8px 0;
  margin-bottom: 2px;
  font-size: 13px;
  padding: 7px 8px;
  line-height: 1.25;
}
body.cl-theme-v4 .cl-navItem.is-active,
body.cl-theme-v4 .cl-navItem:hover {
  background: rgba(201, 162, 39, 0.1);
  border-left-color: var(--cl-accent);
  color: #fde68a;
}
body.cl-theme-v4 .cl-lead {
  max-width: none;
}
body.cl-theme-v4 .btn.primary {
  background: var(--cl-accent);
  color: #1a1a1a;
  font-weight: 700;
}
body.cl-theme-v4 .cl-promoBanner {
  background: linear-gradient(135deg, #1b4332 0%, #3d2c1e 50%, #1a1d24 100%);
  border: 1px solid rgba(201, 162, 39, 0.2);
  border-radius: 14px;
}
body.cl-theme-v4 .cl-gameCard {
  border-radius: 10px;
  transition: border-color 0.15s, transform 0.15s;
}
body.cl-theme-v4 .cl-gameCard:hover {
  border-color: rgba(201, 162, 39, 0.45);
  transform: translateY(-2px);
}
body.cl-theme-v4 .cl-seoProse {
  background: rgba(45, 106, 79, 0.06);
  border-color: rgba(45, 106, 79, 0.25);
  border-radius: 14px;
}
body.cl-theme-v4 .cl-hubCard {
  border-radius: 10px;
  border-top: 2px solid var(--cl-accent2);
}
body.cl-theme-v4 .cl-hubArrow { color: var(--cl-accent); }
@media (max-width: 900px) {
  body.cl-theme-v4 .cl-grid { grid-template-columns: 1fr; }
  body.cl-theme-v4 .cl-main,
  body.cl-theme-v4 .cl-sidebar { grid-column: auto; max-width: none; }
  body.cl-theme-v4 .cl-sidebar {
    border-left: none;
    border-right: none;
    border-bottom: 1px solid var(--cl-line);
  }
}
"""


def combined_page_css() -> str:
    css = CL_PAGE_CSS
    if THEME_VARIANT == 2:
        css += CL_THEME_V2_CSS
    elif THEME_VARIANT == 3:
        css += CL_THEME_V3_CSS
    elif THEME_VARIANT == 4:
        css += CL_THEME_V4_CSS
    return css


def build_cl_site_js() -> str:
    age_key = f"{cookie_js_prefix()}_age_ok"
    cookie_key = f"{cookie_js_prefix()}_cookie"
    tpl = (ROOT / "sites" / "cazilla-clone1-en-ie" / "assets" / "cl-site.js")
    if tpl.is_file():
        js = tpl.read_text(encoding="utf-8")
    else:
        js = "(function () { \"use strict\"; })();"
    js = js.replace("cazilla_clone_age_ok", age_key).replace("cazilla_clone_cookie", cookie_key)
    return js


def write_assets() -> None:
    assets = SITE / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    shell_src = R3_ASSETS / "r3-shell.css"
    comp_src = R3_ASSETS / "r3-compliance.css"
    shell = shell_src.read_text(encoding="utf-8").replace("--r3-", "--cl-") if shell_src.is_file() else ""
    comp = comp_src.read_text(encoding="utf-8").replace("--r3-", "--cl-") if comp_src.is_file() else ""
    (assets / "cl-shell.css").write_text(shell + combined_page_css(), encoding="utf-8")
    (assets / "cl-page.css").write_text("/* reserved */\n", encoding="utf-8")
    comp_extra = "\n.complianceOverlay { pointer-events: auto; }\n.complianceDialog { pointer-events: auto; }\n"
    if "pointer-events: auto" not in comp:
        comp += comp_extra
    (assets / "cl-compliance.css").write_text(comp, encoding="utf-8")
    (assets / "cl-site.js").write_text(build_cl_site_js(), encoding="utf-8")


def copy_pictures() -> None:
    dest = SITE / "assets" / "pictures"
    dest.mkdir(parents=True, exist_ok=True)
    if PICTURE_SRC.is_dir():
        for f in PICTURE_SRC.iterdir():
            if f.is_file():
                shutil.copy2(f, dest / f.name)


def write_robots_sitemap_htaccess() -> None:
    (SITE / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {ORIGIN}/sitemap.xml\n", encoding="utf-8")
    urls: list[str] = []
    for _pid, rel, _label, _kind in MAIN_PAGES:
        urls.append(f"{ORIGIN}/" if rel == "index.html" else f"{ORIGIN}/{rel}")
    for _slug, rel, *_ in TECH_SPECS:
        urls.append(f"{ORIGIN}/{rel}")
    seen: set[str] = set()
    entries = []
    for loc in urls:
        if loc in seen:
            continue
        seen.add(loc)
        pri = "1.0" if loc.endswith("/") or loc.endswith("index.html") else "0.8"
        entries.append(
            f'  <url><loc>{loc}</loc><lastmod>2026-05-15</lastmod><changefreq>weekly</changefreq><priority>{pri}</priority></url>'
        )
    (SITE / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(entries)
        + "\n</urlset>\n",
        encoding="utf-8",
    )
    (SITE / ".htaccess").write_text(
        "RewriteEngine On\nRewriteCond %{HTTPS} off\nRewriteRule ^ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]\n",
        encoding="utf-8",
    )


def fix_keywords_meta() -> None:
    kw = SITE / "_output" / "keywords.json"
    if not kw.is_file():
        return
    data = json.loads(kw.read_text(encoding="utf-8"))
    data["site"] = SITE_SLUG
    data["locale"] = LOCALE
    kw.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    init_site()
    SITE.mkdir(parents=True, exist_ok=True)
    for page_id, rel, label, kind in MAIN_PAGES:
        (SITE / rel).write_text(page_html(page_id, rel, label, kind), encoding="utf-8")
        print("Wrote", rel)
    for slug, rel, title, desc, h1, sub in TECH_SPECS:
        (SITE / rel).write_text(tech_page_html_fixed(rel, title, desc, h1, sub, slug), encoding="utf-8")
        print("Wrote", rel)
    write_assets()
    copy_pictures()
    write_robots_sitemap_htaccess()
    fix_keywords_meta()
    print("Clone site ->", SITE, "| MAIN:", MAIN, "| ORIGIN:", ORIGIN)


if __name__ == "__main__":
    raise SystemExit(main())
