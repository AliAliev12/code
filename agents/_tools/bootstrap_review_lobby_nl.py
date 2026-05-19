#!/usr/bin/env python3
"""Bootstrap: review lobby nl-BE — distinct theme, 5 content + 7 technical pages."""
from __future__ import annotations

import html
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_AGENTS = ROOT / "agents"
if str(_AGENTS) not in sys.path:
    sys.path.insert(0, str(_AGENTS))

from _lib.locale_context import LocaleContext, locale_context_from_env  # noqa: E402
from _lib.repo_env import load_dotenv_file  # noqa: E402

ENV_PATH = ROOT / ".env"
CLONE_ASSETS = ROOT / "sites" / "cazilla-clone1-fr-be" / "assets"
PIC_SRC = ROOT / "sites" / "cazilla-offerwall2-en-ie" / "assets" / "pictures"

SITE: Path = ROOT / "sites" / "cazilla-review1-nl-be"
ORIGIN = "https://cazilla.click"
MAIN = "https://cazilla.casino"
SITE_SLUG = "cazilla-review1-nl-be"
SITE_NAME = "Cazilla België"
HTML_LANG = "nl-BE"
MIN_AGE = 21
LC: LocaleContext | None = None
STUB = "Voorlopige tekst. A2 vervangt dit door geoptimaliseerde inhoud."
CONTENT_PAGES: list[tuple[str, str, str]] = []
FOOTER_LEGAL: list[tuple[str, str]] = []
TECH_SPECS: list[tuple[str, str, str, str, str, str]] = []

HOME_GAMES = [
    ("Sweet Bonanza", "bonus-promo-artwork.webp"),
    ("Gates of Olympus", "fruit-classic-slot.png"),
    ("Big Bass Bonanza", "big-bass-bonanza-review.avif"),
    ("Aviator", "rocket-crash-game.png"),
    ("Sugar Rush", "crazy-time-bonus.jpg"),
    ("Book of Dead", "money-train-4-thumbnail.png"),
]

SLOT_GAMES = HOME_GAMES + [
    ("Money Train 4", "money-train-4-thumbnail.png"),
    ("Fruit Classic", "fruit-classic-slot.png"),
    ("Rocket Crash", "rocket-crash-game.png"),
]

LIVE_PREVIEW = [
    ("Roulette", "baccarat-live-table.webp"),
    ("Blackjack", "blackjack-green-table.jpg"),
    ("Baccarat", "live-tables.jpg"),
]

LIVE_TOP = [
    ("Crazy Time", "crazy-time-bonus.jpg", "Evolution"),
    ("Lightning Roulette", "baccarat-live-table.webp", "Evolution"),
    ("One Blackjack", "blackjack-green-table.jpg", "Pragmatic Play"),
    ("Mega Wheel", "bonus-promo-artwork.webp", "Pragmatic Play"),
]

LIVE_ROULETTE = [
    ("Immersive Roulette", "baccarat-live-table.webp", "Evolution"),
    ("PowerUp Roulette", "live-tables.jpg", "Pragmatic Play"),
    ("Mega Roulette", "baccarat-bonus-terms.webp", "Pragmatic Play"),
    ("Speed Roulette", "baccarat-live-table.webp", "Evolution"),
]

LIVE_SHOWS = [
    ("Sweet Bonanza Candyland", "bonus-promo-artwork.webp", "Pragmatic Play"),
    ("Monopoly Live", "crazy-time-bonus.jpg", "Evolution"),
    ("Infinite Blackjack", "blackjack-green-table.jpg", "Evolution"),
    ("VIP Blackjack", "blackjack-green-table.jpg", "Pragmatic Play"),
]


def init_site() -> None:
    global SITE, ORIGIN, MAIN, SITE_SLUG, SITE_NAME, HTML_LANG, LC, STUB, MIN_AGE
    env = load_dotenv_file(ENV_PATH)
    rel = (env.get("SITE_DIR") or "sites/cazilla-review1-nl-be").strip().lstrip("/")
    SITE = ROOT / rel
    SITE_SLUG = Path(rel).name
    ORIGIN = (env.get("SITE_URL") or "https://cazilla.click").strip().rstrip("/")
    MAIN = (env.get("MAIN_CASINO_URL") or "https://cazilla.casino").strip().rstrip("/")
    LC = locale_context_from_env(env, strict_keywords_match=False)
    HTML_LANG = LC.locale.replace("_", "-") if "_" in LC.locale else LC.locale
    SITE_NAME = "Cazilla België"
    MIN_AGE = 21 if LC.geo.upper() == "BE" else 18
    STUB = f"Voorlopige tekst. A2 vervangt dit door geoptimaliseerde inhoud voor {LC.audience_phrase}."
    _load_keywords()


def _load_keywords() -> None:
    global CONTENT_PAGES, FOOTER_LEGAL, TECH_SPECS
    for candidate in (SITE / "_output" / "keywords.json", SITE / "keywords.json"):
        if candidate.is_file():
            kw_path = candidate
            break
    else:
        raise FileNotFoundError(f"keywords.json not found under {SITE}")
    data = json.loads(kw_path.read_text(encoding="utf-8"))
    CONTENT_PAGES.clear()
    for p in data.get("pages") or []:
        if not isinstance(p, dict):
            continue
        pid = str(p.get("id") or "").strip()
        rel = str(p.get("path") or "").strip().lstrip("/") or "index.html"
        label = str(p.get("menu_label") or pid).strip()
        if pid:
            CONTENT_PAGES.append((pid, rel, html.escape(label)))
    TECH_SPECS.clear()
    FOOTER_LEGAL.clear()
    for p in data.get("technical_pages") or []:
        if not isinstance(p, dict):
            continue
        slug = str(p.get("id") or "").strip()
        rel = str(p.get("path") or "").strip().lstrip("/")
        menu = str(p.get("menu_label") or slug).strip()
        if not slug or not rel:
            continue
        title = f"{menu} | {SITE_NAME}"
        desc = f"{menu} — {SITE_NAME}, {LC.region_name if LC else 'België'}."
        sub = f"{menu} — informatie voor {LC.audience_phrase if LC else 'lezers in België'}."
        TECH_SPECS.append((slug, rel, title, desc, html.escape(menu), html.escape(sub)))
        FOOTER_LEGAL.append((rel, html.escape(menu)))


def compliance_block() -> str:
    age_body = (
        f"Deze site bespreekt gereguleerd gokken voor lezers in België. "
        f"U moet minstens {MIN_AGE} jaar zijn om verder te gaan."
    )
    return f"""<motion class="complianceOverlay" id="ageGate" role="dialog" aria-modal="true" aria-labelledby="ageTitle">
  <div class="complianceDialog">
    <h2 id="ageTitle">Bevestig dat u {MIN_AGE} jaar of ouder bent</h2>
    <p>{html.escape(age_body)}</p>
    <div class="complianceActions">
      <button type="button" class="btn" id="ageUnder">Ik ben jonger dan {MIN_AGE}</button>
      <button type="button" class="btn primary" id="ageOk">Ik ben {MIN_AGE}+</button>
    </div>
  </div>
</div>
<div class="complianceOverlay" id="cookieGate" hidden aria-hidden="true" role="dialog" aria-modal="true" aria-labelledby="cookieTitle">
  <div class="complianceDialog">
    <h2 id="cookieTitle">Cookievoorkeuren</h2>
    <p>We gebruiken cookies om de leeftijdscontrole te onthouden. Zie <a class="inTextLink" href="cookie-policy.html">cookiebeleid</a>.</p>
    <motion class="complianceActions">
      <button type="button" class="btn" id="cookieReject">Alleen essentieel</button>
      <button type="button" class="btn primary" id="cookieAccept">Accepteren</button>
    </div>
  </div>
</motion>""".replace("<motion class=", "<motion class=").replace(
        '<motion class="complianceOverlay"', '<div class="complianceOverlay"', 1
    ).replace(
        '<motion class="complianceActions">', '<motion class="complianceActions">', 1
    )


def _fix_html(s: str) -> str:
    return (
        s.replace("<motion class=", "<div class=")
        .replace("</motion>", "</div>")
        .replace('<motion class="complianceActions">', '<div class="complianceActions">')
    )


def head_block(rel: str, title: str, desc: str) -> str:
    canonical = f"{ORIGIN}/" if rel == "index.html" else f"{ORIGIN}/{rel}"
    return f"""<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title data-a2-field="meta_title">{html.escape(title)}</title>
<meta name="description" data-a2-field="meta_description" content="{html.escape(desc)}" />
<meta name="robots" content="index, follow" />
<link rel="canonical" href="{html.escape(canonical)}" />
<link rel="alternate" hreflang="{html.escape(HTML_LANG)}" href="{html.escape(canonical)}" />
<link rel="alternate" hreflang="x-default" href="{html.escape(canonical)}" />
<meta property="og:title" content="{html.escape(title)}" />
<meta property="og:description" content="{html.escape(desc)}" />
<meta property="og:url" content="{html.escape(canonical)}" />
<meta property="og:type" content="website" />
<meta property="og:locale" content="nl_BE" />
<meta property="og:image" content="{ORIGIN}/assets/pictures/og-logo.svg" />
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"WebSite","name":"{html.escape(SITE_NAME)}","url":"{html.escape(ORIGIN)}/"}}</script>
<link rel="stylesheet" href="assets/rb-shell.css" />
<link rel="stylesheet" href="assets/rb-lobby.css" />
<link rel="stylesheet" href="assets/rb-compliance.css" />"""


def site_header(current_rel: str | None = None) -> str:
    cur_norm = (current_rel or "").strip().lstrip("/") or None
    nav_lines = []
    for _pid, href, lab in CONTENT_PAGES:
        cur = ' aria-current="page"' if cur_norm == href else ""
        nav_lines.append(f'      <a href="{href}"{cur}>{lab}</a>')
    nav = "\n".join(nav_lines)
    m = html.escape(MAIN)
    return f"""<header class="rb-header">
  <div class="rb-headerInner">
    <a class="rb-brand" href="index.html" aria-label="Home {html.escape(SITE_NAME)}">
      <img src="assets/pictures/og-logo.svg" alt="" width="36" height="36" decoding="async" />
      <span class="rb-brandName">{html.escape(SITE_NAME.upper())}</span>
    </a>
    <nav class="rb-nav" id="mainNav" aria-label="Hoofdnavigatie">
{nav}
    </nav>
    <div class="rb-headerActions">
      <button class="btn icon rb-navToggle" id="navToggle" type="button" aria-label="Menu openen" aria-expanded="false" aria-controls="mainNav">≡</button>
      <a class="btn" href="{m}" rel="noopener noreferrer" target="_blank">Officiële site</a>
      <a class="btn primary" href="{m}" rel="noopener noreferrer" target="_blank">Speel</a>
    </div>
  </div>
</header>"""


def site_footer(current_rel: str | None = None) -> str:
    legal = []
    for href, lab in FOOTER_LEGAL:
        cur = ' aria-current="page"' if current_rel == href else ""
        legal.append(f'      <a href="{href}"{cur}>{lab}</a>')
    nav_content = "\n".join(
        f'      <a href="{href}"{" aria-current=\"page\"" if current_rel == href else ""}>{lab}</a>'
        for _pid, href, lab in CONTENT_PAGES
        if href != "index.html"
    )
    m = html.escape(MAIN)
    return f"""<footer class="rb-footer" id="footer">
  <nav class="rb-footerNav" aria-label="Pagina's">
    <a href="index.html">Home</a>
{nav_content}
  </nav>
  <nav class="rb-footerLegal" aria-label="Juridisch">
{chr(10).join(legal)}
  </nav>
  <div class="rb-footerBlock">
    <h3>Providers</h3>
    <div class="rb-badges">
      <span class="rb-badge">Pragmatic Play</span><span class="rb-badge">NetEnt</span><span class="rb-badge">Evolution</span>
      <span class="rb-badge">Play'n GO</span><span class="rb-badge">Ezugi</span>
    </div>
  </motion>
  <div class="rb-footerBlock">
    <h3>Betaalmethoden</h3>
    <div class="rb-badges">
      <span class="rb-badge">Bancontact</span><span class="rb-badge">iDEAL</span><span class="rb-badge">Visa</span>
      <span class="rb-badge">Mastercard</span><span class="rb-badge">Payconiq</span>
    </div>
  </div>
  <p class="rb-license"><span class="rb-age">{MIN_AGE}+</span> Curaçao eGaming — details op <a href="{m}" rel="noopener noreferrer" target="_blank">de officiële site</a>.</p>
  <p class="rb-copy">© <span id="year"></span> {html.escape(SITE_NAME)}. Redactioneel reviewplatform, geen exploitant.</p>
</footer>""".replace("<motion class=", "<div class=").replace("</motion>", "</div>", 1)


def game_row(title: str, img: str, *, featured: bool = False) -> str:
    m = html.escape(MAIN)
    cls = "rb-gameRow rb-gameRow--featured" if featured else "rb-gameRow"
    tag = "Officieel" if featured else "Populair"
    return f"""<article class="{cls}">
  <div class="rb-gameRowThumb">
    <img src="assets/pictures/{html.escape(img)}" alt="{html.escape(title)}" width="280" height="160" loading="lazy" decoding="async" />
  </div>
  <div class="rb-gameRowBody">
    <p class="rb-gameRowTag">{tag}</p>
    <h3 class="rb-gameRowTitle">{html.escape(title)}</h3>
    <div class="rb-gameRowActions">
      <a class="btn primary" href="{m}" rel="noopener noreferrer" target="_blank">Speel</a>
      <a class="btn" href="{m}" rel="noopener noreferrer" target="_blank">Demo</a>
    </div>
  </div>
</article>"""


def live_tile(name: str, img: str, provider: str) -> str:
    m = html.escape(MAIN)
    return f"""<a class="rb-liveTile" href="{m}" rel="noopener noreferrer" target="_blank">
  <img src="assets/pictures/{html.escape(img)}" alt="{html.escape(name)}" width="280" height="160" loading="lazy" decoding="async" />
  <div class="rb-liveTileBody">
    <h3>{html.escape(name)}</h3>
    <p>{html.escape(provider)}</p>
  </div>
</a>"""


def live_section(title: str, section_id: str, games: list[tuple[str, str, str]]) -> str:
    tiles = "\n".join(live_tile(n, i, p) for n, i, p in games)
    m = html.escape(MAIN)
    return f"""<section class="rb-liveSection" aria-labelledby="{section_id}">
  <div class="rb-sectionHead">
    <h2 id="{section_id}">{html.escape(title)}</h2>
    <a class="rb-viewAll" href="{m}" rel="noopener noreferrer" target="_blank">Alles bekijken ›</a>
  </div>
  <div class="rb-liveTileGrid">
{tiles}
  </div>
</section>"""


def home_body() -> str:
    m = html.escape(MAIN)
    rows = [game_row("Cazilla — officieel casino", "casino-feature-visual.png", featured=True)]
    rows.extend(game_row(n, img) for n, img in HOME_GAMES)
    live_cards = "\n".join(
        f"""<a class="rb-liveCard" href="{m}" rel="noopener noreferrer" target="_blank">
  <img src="assets/pictures/{html.escape(img)}" alt="{html.escape(name)}" width="400" height="200" loading="lazy" decoding="async" />
  <h3>{html.escape(name)}</h3>
</a>"""
        for name, img in LIVE_PREVIEW
    )
    return f"""
      <section class="rb-promo" aria-label="Promotie">
        <h2 class="rb-promoTitle">Welkomstbonus 100&nbsp;% + 500 gratis spins</h2>
        <p class="rb-promoLead">Aanbod op de officiële site — voorwaarden en {MIN_AGE}+ in België.</p>
        <a class="btn primary" href="{m}" rel="noopener noreferrer" target="_blank">Speel nu</a>
      </section>
      <section class="rb-section" aria-labelledby="rb-cat-title">
        <motion class="rb-tags" role="tablist" aria-label="Categorieën">
          <span class="rb-tag is-active">Populair</span><span class="rb-tag">Nieuw</span>
          <span class="rb-tag">Gokkasten</span><span class="rb-tag">Tafelspellen</span><span class="rb-tag">Megaways</span>
        </div>
        <h2 id="rb-cat-title" class="rb-sectionTitle">Populaire spellen</h2>
        <div class="rb-gameList">
{chr(10).join(rows)}
        </div>
      </section>
      <section class="rb-section" aria-labelledby="rb-live-title">
        <h2 id="rb-live-title" class="rb-sectionTitle">Live casino</h2>
        <div class="rb-liveGrid">
{live_cards}
        </div>
      </section>""".replace('<motion class="rb-tags"', '<div class="rb-tags"')


def slots_body() -> str:
    m = html.escape(MAIN)
    cards = "\n".join(game_row(n, img) for n, img in SLOT_GAMES)
    return f"""
      <div class="rb-toolbar">
        <label class="rb-tool">Zoek spel <input type="search" placeholder="Spelnaam…" /></label>
        <label class="rb-tool">Provider <select><option>Alle</option></select></label>
      </div>
      <div class="rb-tags">
        <span class="rb-tag is-active">Populair</span><span class="rb-tag">Gokkasten</span>
        <span class="rb-tag">Jackpot</span><span class="rb-tag">Tafelspellen</span><span class="rb-tag">Megaways</span>
      </div>
      <motion class="rb-gameList">
{cards}
      </div>
      <p class="rb-more"><a class="btn" href="{m}" rel="noopener noreferrer" target="_blank">Meer tonen</a></p>""".replace(
        '<motion class="rb-gameList">', '<div class="rb-gameList">'
    )


def bonus_body() -> str:
    m = html.escape(MAIN)
    cards_data = [
        ("Eerste storting 100&nbsp;%", "Gokkasten en live casino"),
        ("Casino cashback 25&nbsp;%", "Op netto dagverliezen"),
        ("Crypto bonus 20&nbsp;%", "Stortingen in crypto"),
        ("Vriend uitnodigen", "Beloning per uitgenodigde vriend"),
    ]
    grid = []
    for title, sub in cards_data:
        grid.append(
            f"""<article class="rb-bonusCard">
  <h3>{title}</h3>
  <p>{html.escape(sub)}</p>
  <div class="rb-bonusCardActions">
    <a class="btn" href="{m}" rel="noopener noreferrer" target="_blank">Details</a>
    <a class="btn primary" href="{m}" rel="noopener noreferrer" target="_blank">Speel</a>
  </div>
</article>"""
        )
    return f"""
      <div class="rb-tags">
        <span class="rb-tag is-active">Alle bonussen</span><span class="rb-tag">Welkomst</span>
        <span class="rb-tag">Storting</span><span class="rb-tag">Cashback</span><span class="rb-tag">Speciaal</span>
      </div>
      <div class="rb-bonusGrid">
{chr(10).join(grid)}
      </div>
      <section class="rb-termsBox" aria-labelledby="rb-terms-title">
        <h2 id="rb-terms-title">Algemene bonusvoorwaarden</h2>
        <ul>
          <li>Elke bonus kan andere inzetvereisten hebben.</li>
          <li>Maximaal één actieve bonus per spelersaccount.</li>
          <li>Lees altijd de regels op de officiële site vóór acceptatie.</li>
        </ul>
      </section>"""


def about_body() -> str:
    m = html.escape(MAIN)
    return f"""
      <section class="rb-aboutIntro" data-a2-field="page_lead">
        <p>{html.escape(STUB)}</p>
      </section>
      <section class="rb-aboutValues" aria-labelledby="rb-values-title">
        <h2 id="rb-values-title">Onze waarden</h2>
        <div class="rb-aboutGrid">
          <article class="rb-aboutCard"><h3>Betrouwbaarheid</h3><p>Redactionele tests en transparantie over aanbiedingen.</p></article>
          <article class="rb-aboutCard"><h3>Klantgericht</h3><p>Duidelijke support en flows voor Belgische spelers.</p></article>
          <article class="rb-aboutCard"><h3>Eerlijk spel</h3><p>Gelicentieerde providers en gecontroleerde RNG.</p></article>
        </div>
      </section>
      <section class="rb-licenseBox" aria-labelledby="rb-lic-title">
        <h2 id="rb-lic-title">Licentie en regelgeving</h2>
        <p>Informatie over Curaçao-licentie en gegevensbescherming — <a href="{m}" rel="noopener noreferrer" target="_blank">Officiële site</a>.</p>
      </section>"""


def live_casino_body() -> str:
    m = html.escape(MAIN)
    return f"""
      <section class="rb-liveHero" aria-label="Live casino">
        <h1 data-a2-field="page_h1">Welkom bij het live casino van Cazilla</h1>
        <p class="rb-liveHeroLead" data-a2-field="page_lead">Welkomstbonus: 100% tot €500 + 200 gratis spins — voorwaarden op de officiële site.</p>
        <a class="btn primary rb-liveHeroCta" href="{m}" rel="noopener noreferrer" target="_blank">Bonus claimen</a>
      </section>
      <div class="rb-tags rb-tags--live" role="tablist" aria-label="Live filters">
        <span class="rb-tag is-active">Alle spellen</span><span class="rb-tag">Top</span>
        <span class="rb-tag">Roulette</span><span class="rb-tag">Blackjack</span>
        <span class="rb-tag">Game shows</span><span class="rb-tag">Baccarat</span>
      </div>
{live_section("Top live casino", "rb-live-top", LIVE_TOP)}
{live_section("Live roulette", "rb-live-roulette", LIVE_ROULETTE)}
{live_section("Game shows &amp; blackjack", "rb-live-shows", LIVE_SHOWS)}
      <section class="rb-liveSeo" aria-label="Informatie">
        <motion class="rb-seoProse" data-a2-field="main_seo_html">
          <p>{html.escape(STUB)}</p>
          <details class="rb-faqItem">
            <summary>Hoe begin ik met live casino spelen?</summary>
            <p>{html.escape(STUB)}</p>
          </details>
          <details class="rb-faqItem">
            <summary>Welke providers zijn beschikbaar bij Cazilla?</summary>
            <p>{html.escape(STUB)}</p>
          </details>
        </div>
      </section>
      <section class="rb-providerStrip" aria-label="Live providers">
        <h2 class="rb-providerStripTitle">Live providers</h2>
        <div class="rb-badges">
          <span class="rb-badge">Pragmatic Live</span><span class="rb-badge">Evolution</span>
          <span class="rb-badge">Ezugi</span><span class="rb-badge">Live88</span><span class="rb-badge">Playtech</span>
        </div>
      </section>""".replace('<motion class="rb-seoProse"', '<motion class="rb-seoProse"').replace(
        '<motion class="rb-seoProse"', '<div class="rb-seoProse"', 1
    )


BODY_BY_ID = {
    "home": home_body,
    "slots": slots_body,
    "bonus": bonus_body,
    "about": about_body,
    "live-casino": live_casino_body,
}


def content_page(page_id: str, rel: str, menu_label: str) -> str:
    title = f"{menu_label} | {SITE_NAME}"
    desc = f"{menu_label} — casino lobby voor lezers in België ({MIN_AGE}+)."
    h1 = menu_label.replace("&amp;", "&")
    body_fn = BODY_BY_ID.get(page_id, slots_body)
    body = _fix_html(body_fn())
    seo_block = ""
    if page_id == "home":
        seo_block = f"""
      <div class="rb-seoProse" data-a2-field="main_seo_html">
        <p>{html.escape(STUB)}</p>
      </div>"""
    elif page_id in ("slots", "bonus", "about"):
        seo_block = f"""
      <motion class="rb-seoProse" data-a2-field="main_seo_html"><p>{html.escape(STUB)}</p></motion>""".replace(
            "<motion", "<motion"
        )
        seo_block = f'\n      <div class="rb-seoProse" data-a2-field="main_seo_html"><p>{html.escape(STUB)}</p></div>'
    elif page_id == "live-casino":
        seo_block = ""
    title_block = ""
    if page_id != "live-casino":
        title_block = f'    <h1 class="rb-pageTitle" data-a2-field="page_h1">{html.escape(h1)}</h1>\n'
    fine = f"{MIN_AGE}+ | Speel verantwoord | België"
    return f"""<!doctype html>
<html lang="{html.escape(HTML_LANG)}" data-site-kind="review-lobby" data-min-gambling-age="{MIN_AGE}">
  <head>
{head_block(rel, title, desc)}
  </head>
  <body class="rb-layout rb-theme-nl">
{_fix_html(compliance_block())}
<div id="siteContent" class="rb-app">
{site_header(rel)}
  <main class="rb-main" id="top">
{title_block}{body}
{seo_block}
    <p class="rb-fineprint" data-a2-field="footer_note">{html.escape(fine)}</p>
  </main>
{_fix_html(site_footer(rel))}
</div>
<script src="assets/rb-site.js" defer></script>
  </body>
</html>"""


def tech_policy_stub() -> str:
    return (
        '<article class="rb-policyArticle" data-a2-field="main_seo_html">'
        f"<p>{html.escape(STUB)}</p>"
        '<p><a href="index.html">Terug naar home</a></p>'
        "</article>"
    )


def technical_page(rel: str, title: str, desc: str, h1: str, hero_sub: str, slug: str) -> str:
    body = tech_policy_stub()
    return f"""<!doctype html>
<html lang="{html.escape(HTML_LANG)}" data-site-kind="review-lobby" data-min-gambling-age="{MIN_AGE}">
  <head>
{head_block(rel, title, desc)}
  </head>
  <body class="rb-layout rb-layout--legal rb-theme-nl">
{_fix_html(compliance_block())}
<div id="siteContent" class="rb-app">
{site_header(rel)}
  <main class="rb-main" id="top">
    <section class="rb-legalHero">
      <h1 data-a2-field="page_h1">{h1}</h1>
      <p class="rb-lead" data-a2-field="page_lead">{hero_sub}</p>
    </section>
    <div class="rb-policyCard">{body}</div>
  </main>
{_fix_html(site_footer(rel))}
</motion>
<script src="assets/rb-site.js" defer></script>
  </body>
</html>""".replace("</motion>\n<script", "</motion>\n<script").replace(
        "</motion>\n<script", "</div>\n<script"
    )


RB_LOBBY_CSS = """
/* Review lobby nl-BE — teal / coral theme (distinct from fr-BE gold) */
.rb-layout { margin: 0; background: var(--rb-bg); color: var(--rb-text); font-family: "Segoe UI", system-ui, sans-serif; }
.rb-app { min-height: 100vh; display: flex; flex-direction: column; max-width: 960px; margin: 0 auto; }
.rb-header { padding: 12px 18px; background: linear-gradient(180deg, #0c1222 0%, #111827 100%); border-bottom: 3px solid var(--rb-accent); position: relative; z-index: 30; }
.rb-headerInner { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
.rb-brand { display: inline-flex; align-items: center; gap: 10px; text-decoration: none; color: inherit; font-weight: 800; font-size: 0.92rem; letter-spacing: 0.05em; flex-shrink: 0; }
.rb-brand img { border-radius: 10px; box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.35); }
.rb-nav { display: flex; flex-wrap: wrap; gap: 6px 16px; align-items: center; margin-left: auto; }
.rb-nav a { color: var(--rb-muted); text-decoration: none; font-size: 14px; font-weight: 500; }
.rb-nav a:hover, .rb-nav a[aria-current="page"] { color: var(--rb-text); }
.rb-nav a[aria-current="page"] { font-weight: 700; color: var(--rb-accent2); }
.rb-headerActions { display: flex; gap: 8px; align-items: center; flex-shrink: 0; }
.btn.icon { display: none; min-width: 40px; padding: 8px 12px; font-size: 18px; line-height: 1; }
@media (max-width: 720px) {
  .btn.icon { display: inline-flex; }
  .rb-headerInner { position: relative; }
  .rb-nav { display: none; position: absolute; top: 100%; left: -18px; right: -18px; flex-direction: column; align-items: stretch; gap: 4px; margin: 0; padding: 12px 18px 16px; background: #111827; border-bottom: 3px solid var(--rb-accent); }
  .rb-nav[data-open="true"] { display: flex; }
  .rb-headerActions .btn:not(.icon):not(.primary) { display: none; }
}
.rb-main { flex: 1; padding: 18px 18px 32px; }
.rb-pageTitle { margin: 0 0 16px; font-size: clamp(1.35rem, 3vw, 1.75rem); color: #e0f2fe; }
.rb-promo { text-align: center; padding: 28px 20px; margin-bottom: 22px; border-radius: 16px;
  background: linear-gradient(135deg, #0e7490 0%, #7c3aed 45%, #0f172a 100%);
  border: 1px solid rgba(56, 189, 248, 0.35); box-shadow: 0 12px 40px rgba(14, 116, 144, 0.25); }
.rb-promoTitle { margin: 0 0 10px; font-size: clamp(1.2rem, 3vw, 1.65rem); color: #f0f9ff; }
.rb-promoLead { margin: 0 0 16px; color: #bae6fd; font-size: 15px; }
.rb-section { margin-bottom: 28px; scroll-margin-top: 88px; }
.rb-sectionTitle { margin: 0 0 14px; font-size: 1.1rem; color: #e0f2fe; }
.rb-sectionHead { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: 8px; margin-bottom: 12px; }
.rb-sectionHead h2 { margin: 0; font-size: 1.1rem; color: #e0f2fe; }
.rb-viewAll { font-size: 14px; color: var(--rb-accent2); text-decoration: none; }
.rb-viewAll:hover { text-decoration: underline; }
.rb-tags { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
.rb-tags--live { margin-top: 4px; }
.rb-tag { font-size: 12px; padding: 6px 12px; border-radius: 999px; background: #1e293b; color: inherit; cursor: default; border: 1px solid rgba(148, 163, 184, 0.2); }
.rb-tag.is-active { background: var(--rb-accent); color: #0f172a; font-weight: 700; border-color: transparent; }
.rb-gameList { display: flex; flex-direction: column; gap: 12px; }
.rb-gameRow { display: flex; gap: 14px; align-items: center; padding: 12px; border-radius: 14px;
  border: 1px solid var(--rb-line); background: var(--rb-panel); }
.rb-gameRow--featured { border: 2px solid var(--rb-accent2); background: linear-gradient(90deg, rgba(56,189,248,0.12), transparent); }
.rb-gameRowThumb { flex: 0 0 140px; border-radius: 10px; overflow: hidden; }
.rb-gameRowThumb img { width: 100%; height: 90px; object-fit: cover; display: block; }
.rb-gameRowBody { flex: 1; min-width: 0; }
.rb-gameRowTag { margin: 0 0 4px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--rb-muted); }
.rb-gameRowTitle { margin: 0 0 8px; font-size: 1.05rem; }
.rb-gameRowActions { display: flex; flex-wrap: wrap; gap: 8px; }
.rb-liveGrid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.rb-liveTileGrid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
@media (max-width: 900px) { .rb-liveTileGrid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 640px) {
  .rb-liveGrid { grid-template-columns: 1fr; }
  .rb-liveTileGrid { grid-template-columns: 1fr; }
  .rb-gameRow { flex-direction: column; align-items: stretch; }
  .rb-gameRowThumb { flex-basis: auto; }
}
.rb-liveCard, .rb-liveTile { display: block; text-decoration: none; color: inherit; border-radius: 14px; overflow: hidden; border: 1px solid var(--rb-line); background: var(--rb-panel); transition: border-color 0.15s, transform 0.15s; }
.rb-liveCard:hover, .rb-liveTile:hover { border-color: var(--rb-accent2); transform: translateY(-2px); }
.rb-liveCard img, .rb-liveTile > img { width: 100%; height: 120px; object-fit: cover; display: block; }
.rb-liveCard h3 { margin: 10px 12px 12px; font-size: 15px; }
.rb-liveTileBody { padding: 10px 12px 12px; }
.rb-liveTileBody h3 { margin: 0 0 4px; font-size: 15px; }
.rb-liveTileBody p { margin: 0; font-size: 12px; color: var(--rb-muted); }
.rb-liveSection { margin-bottom: 26px; }
.rb-liveHero { text-align: center; padding: 32px 22px; margin-bottom: 18px; border-radius: 16px;
  background: linear-gradient(135deg, #164e63 0%, #4c1d95 50%, #0f172a 100%);
  border: 1px solid rgba(244, 114, 182, 0.35); }
.rb-liveHero h1 { margin: 0 0 12px; font-size: clamp(1.35rem, 3.5vw, 1.85rem); color: #fdf2f8; }
.rb-liveHeroLead { margin: 0 0 18px; color: #e9d5ff; font-size: 15px; max-width: 36em; margin-left: auto; margin-right: auto; }
.rb-liveHeroCta { font-size: 15px; padding: 10px 22px; }
.rb-liveSeo { margin-top: 8px; }
.rb-faqItem { margin-top: 10px; border: 1px solid var(--rb-line); border-radius: 10px; padding: 10px 14px; background: rgba(15, 23, 42, 0.5); }
.rb-faqItem summary { cursor: pointer; font-weight: 600; color: #e0f2fe; }
.rb-providerStrip { margin: 20px 0 8px; padding: 16px; border-radius: 12px; border: 1px dashed var(--rb-line); }
.rb-providerStripTitle { margin: 0 0 10px; font-size: 13px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--rb-muted); }
.rb-toolbar { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 14px; }
.rb-tool { font-size: 13px; color: var(--rb-muted); display: flex; flex-direction: column; gap: 4px; }
.rb-tool input, .rb-tool select { padding: 8px 10px; border-radius: 8px; border: 1px solid var(--rb-line); background: #0b1220; color: inherit; min-width: 180px; }
.rb-more { text-align: center; margin: 20px 0; }
.rb-bonusGrid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 14px; margin-bottom: 20px; }
.rb-bonusCard { padding: 16px; border-radius: 14px; border: 1px solid var(--rb-line); background: var(--rb-panel); }
.rb-bonusCard h3 { margin: 0 0 8px; font-size: 1rem; }
.rb-bonusCard p { margin: 0 0 12px; font-size: 14px; color: var(--rb-muted); }
.rb-bonusCardActions { display: flex; flex-wrap: wrap; gap: 8px; }
.rb-termsBox, .rb-licenseBox { padding: 16px; border-radius: 14px; border: 1px solid var(--rb-line); background: rgba(56, 189, 248, 0.05); margin-top: 16px; }
.rb-termsBox ul { margin: 0; padding-left: 1.2rem; color: #cbd5e1; line-height: 1.6; }
.rb-aboutIntro p { line-height: 1.65; color: #cbd5e1; }
.rb-aboutGrid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }
.rb-aboutCard { padding: 14px; border-radius: 14px; border: 1px solid var(--rb-line); background: var(--rb-panel); }
.rb-aboutCard h3 { margin:  0 0 8px; font-size: 15px; }
.rb-seoProse { margin-top: 24px; padding: 18px; border-radius: 14px; border: 1px solid var(--rb-line); background: rgba(14, 116, 144, 0.08); }
.rb-seoProse p, .rb-seoProse li { line-height: 1.7; color: #cbd5e1; }
.rb-fineprint { font-size: 13px; color: var(--rb-muted); margin-top: 20px; }
.rb-footer { padding: 24px 18px; border-top: 1px solid var(--rb-line); background: #0a0f1a; margin-top: auto; }
.rb-footerNav, .rb-footerLegal { display: flex; flex-wrap: wrap; gap: 10px 16px; margin-bottom: 14px; }
.rb-footerNav a, .rb-footerLegal a { color: var(--rb-muted); font-size: 13px; text-decoration: none; }
.rb-footerNav a:hover, .rb-footerLegal a:hover { color: var(--rb-text); }
.rb-footerBlock h3 { margin: 0 0 8px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--rb-muted); }
.rb-badges { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
.rb-badge { padding: 5px 10px; border-radius: 8px; font-size: 12px; background: #1e293b; border: 1px solid var(--rb-line); }
.rb-license { font-size: 13px; color: var(--rb-muted); display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }
.rb-age { display: inline-flex; padding: 4px 10px; border-radius: 6px; font-weight: 800; background: var(--rb-accent2); color: #0f172a; }
.rb-copy { font-size: 12px; color: var(--rb-muted); margin: 12px 0 0; }
.rb-legalHero { margin-bottom: 16px; }
.rb-lead { color: var(--rb-muted); line-height: 1.6; }
.rb-policyCard { margin-bottom: 20px; }
.rb-policyArticle p { line-height: 1.7; color: #cbd5e1; }
body.rb-layout--legal .rb-main { max-width: 820px; }
.btn { display: inline-flex; align-items: center; justify-content: center; padding: 8px 14px; border-radius: 10px; border: 1px solid var(--rb-line); background: #1e293b; color: inherit; text-decoration: none; font-size: 14px; cursor: pointer; font-family: inherit; }
.btn.primary { background: linear-gradient(135deg, var(--rb-accent2), #f472b6); border-color: transparent; color: #0f172a; font-weight: 700; }
body.rb-theme-nl { --rb-accent: #22d3ee; --rb-accent2: #38bdf8; --rb-bg: #0b1020; --rb-panel: #151d2e; --rb-line: rgba(56, 189, 248, 0.18); --rb-text: #f1f5f9; --rb-muted: #94a3b8; }
"""

RB_COMPLIANCE_CSS = """
#siteContent.isBlurred { filter: blur(12px); user-select: none; pointer-events: none; }
.complianceOverlay { position: fixed; inset: 0; z-index: 500; display: grid; place-items: center; padding: 20px; background: rgba(4, 8, 18, 0.82); backdrop-filter: blur(6px); }
.complianceOverlay[hidden] { display: none !important; }
.complianceDialog { width: min(420px,100%); border-radius: 14px; border: 1px solid rgba(56, 189, 248, 0.4); background: #151d2e; color: #f1f5f9; padding: 22px; box-shadow: 0 24px 60px rgba(0,0,0,0.55); }
.complianceDialog h2 { margin: 0 0 10px; font-size: 18px; }
.complianceDialog p { margin: 0 0 14px; color: #cbd5e1; font-size: 14px; line-height: 1.55; }
.complianceActions { display: flex; flex-wrap: wrap; gap: 10px; }
.inTextLink { color: #7dd3fc; }
html.complianceNoScroll, html.complianceNoScroll body { overflow: hidden; height: 100%; }
"""

RB_SITE_JS = """
(function () {
  "use strict";
  var AGE = "cazilla_review1_nl_be_age_ok";
  var COOKIE = "cazilla_review1_nl_be_cookie";
  function getCookie(n) {
    var m = document.cookie.match(new RegExp("(?:^|; )" + n.replace(/([.$?*|{}()[\\]\\\\/+^])/g, "\\\\$1") + "=([^;]*)"));
    return m ? decodeURIComponent(m[1]) : "";
  }
  function setCookie(n, v, max) {
    document.cookie = n + "=" + encodeURIComponent(v) + ";path=/;max-age=" + max + ";SameSite=Lax";
  }
  function show(el) { if (el) { el.removeAttribute("hidden"); el.setAttribute("aria-hidden", "false"); } }
  function hide(el) { if (el) { el.setAttribute("hidden", "hidden"); el.setAttribute("aria-hidden", "true"); } }
  var ageGate = document.getElementById("ageGate");
  var cookieGate = document.getElementById("cookieGate");
  var site = document.getElementById("siteContent");
  function blur(on) { if (site) site.classList.toggle("isBlurred", !!on); }
  function lock(on) { document.documentElement.classList.toggle("complianceNoScroll", !!on); }
  var ageOk = document.getElementById("ageOk");
  var ageUnder = document.getElementById("ageUnder");
  if (ageOk) ageOk.addEventListener("click", function () {
    setCookie(AGE, "1", 3 * 24 * 60 * 60);
    hide(ageGate); blur(false); lock(false);
    if (!getCookie(COOKIE)) show(cookieGate); else hide(cookieGate);
  });
  if (ageUnder) ageUnder.addEventListener("click", function () { hide(ageGate); blur(true); lock(true); });
  var ca = document.getElementById("cookieAccept");
  var cr = document.getElementById("cookieReject");
  if (ca) ca.addEventListener("click", function () { setCookie(COOKIE, "accept", 365 * 24 * 60 * 60); hide(cookieGate); });
  if (cr) cr.addEventListener("click", function () { setCookie(COOKIE, "reject", 365 * 24 * 60 * 60); hide(cookieGate); });
  if (getCookie(AGE) === "1") {
    hide(ageGate); blur(false); lock(false);
    if (!getCookie(COOKIE)) show(cookieGate); else hide(cookieGate);
  } else { show(ageGate); hide(cookieGate); lock(true); }
  var y = document.getElementById("year");
  if (y) y.textContent = String(new Date().getFullYear());
  var navToggle = document.getElementById("navToggle");
  var mainNav = document.getElementById("mainNav");
  if (navToggle && mainNav) {
    navToggle.addEventListener("click", function () {
      var open = mainNav.dataset.open === "true";
      mainNav.dataset.open = open ? "false" : "true";
      navToggle.setAttribute("aria-expanded", open ? "false" : "true");
      navToggle.setAttribute("aria-label", open ? "Menu openen" : "Menu sluiten");
    });
    document.addEventListener("click", function (ev) {
      if (mainNav.dataset.open !== "true") return;
      if (mainNav.contains(ev.target) || navToggle.contains(ev.target)) return;
      mainNav.dataset.open = "false";
      navToggle.setAttribute("aria-expanded", "false");
      navToggle.setAttribute("aria-label", "Menu openen");
    });
  }
})();
"""


def write_assets() -> None:
    assets = SITE / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    pics = assets / "pictures"
    pics.mkdir(exist_ok=True)
    if PIC_SRC.is_dir():
        for f in PIC_SRC.iterdir():
            if f.is_file():
                shutil.copy2(f, pics / f.name)
    shell = ""
    if (CLONE_ASSETS / "cl-shell.css").is_file():
        shell = (CLONE_ASSETS / "cl-shell.css").read_text(encoding="utf-8")
    (assets / "rb-shell.css").write_text(shell, encoding="utf-8")
    (assets / "rb-lobby.css").write_text(RB_LOBBY_CSS.strip() + "\n", encoding="utf-8")
    (assets / "rb-compliance.css").write_text(RB_COMPLIANCE_CSS.strip() + "\n", encoding="utf-8")
    (assets / "rb-site.js").write_text(RB_SITE_JS.strip() + "\n", encoding="utf-8")


def write_htaccess() -> None:
    (SITE / ".htaccess").write_text(
        "RewriteEngine On\nRewriteCond %{HTTPS} off\nRewriteRule ^ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]\n",
        encoding="utf-8",
    )


def main() -> int:
    init_site()
    write_assets()
    for pid, rel, label in CONTENT_PAGES:
        out = SITE / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content_page(pid, rel, label), encoding="utf-8")
        print("Wrote", rel)
    for slug, rel, title, desc, h1, sub in TECH_SPECS:
        out = SITE / rel
        out.write_text(technical_page(rel, title, desc, h1, sub, slug), encoding="utf-8")
        print("Wrote", rel)
    write_htaccess()
    print("Bootstrap complete ->", SITE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
