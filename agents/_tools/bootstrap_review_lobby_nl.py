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

LANDING_IMAGES: dict[str, tuple[str, str, str]] = {
    "home": ("casino-feature-visual.png", "slots-showcase.png", "live-tables.jpg"),
    "slots": ("slots-showcase.png", "fruit-classic-slot.png", "big-bass-bonanza-review.avif"),
    "bonus": ("bonus-promo-artwork.webp", "baccarat-bonus-terms.webp", "crazy-time-bonus.jpg"),
    "about": ("casino-feature-visual.png", "og-logo.svg", "blackjack-green-table.jpg"),
    "live-casino": ("live-tables.jpg", "baccarat-live-table.webp", "blackjack-green-table.jpg"),
}

LANDING_IMG_ALT_NL: dict[str, tuple[str, str, str]] = {
    "home": (
        "Cazilla lobby — online casino België",
        "Gokkasten catalogus",
        "Live casinotafels",
    ),
    "slots": (
        "Populaire online gokkasten",
        "Klassieke fruitautomaat",
        "Big Bass Bonanza — preview",
    ),
    "bonus": (
        "Cazilla bonusaanbiedingen",
        "Baccarat bonus — voorwaarden",
        "Crazy Time promotie",
    ),
    "about": (
        "Cazilla België — redactioneel platform",
        "Cazilla logo",
        "Live blackjack",
    ),
    "live-casino": (
        "Live casino tafels",
        "Live roulette",
        "Live blackjack",
    ),
}

LANDING_IMG_ALT_EN: dict[str, tuple[str, str, str]] = {
    "home": ("Cazilla lobby — online casino Belgium", "Slots catalogue", "Live casino tables"),
    "slots": ("Popular online slots", "Classic fruit slot", "Big Bass Bonanza preview"),
    "bonus": ("Cazilla bonus offers", "Baccarat bonus terms", "Crazy Time promotion"),
    "about": ("Cazilla Belgium editorial hub", "Cazilla logo", "Live blackjack"),
    "live-casino": ("Live casino tables", "Live roulette", "Live blackjack"),
}


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
    SITE_NAME = "Cazilla Belgium" if LC.lang == "en" else "Cazilla België"
    MIN_AGE = 21 if LC.geo.upper() == "BE" else 18
    if LC.lang == "en":
        STUB = f"Placeholder copy. A2 will replace this with optimized content for {LC.audience_phrase}."
    else:
        STUB = f"Voorlopige tekst. A2 vervangt dit door geoptimaliseerde inhoud voor {LC.audience_phrase}."
    _load_keywords()


def _is_en() -> bool:
    return bool(LC and LC.lang == "en")


def _theme_class() -> str:
    return "rb-theme-enbe" if _is_en() else "rb-theme-nl"


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
    if _is_en():
        age_body = (
            f"This site discusses regulated gambling for readers in Belgium. "
            f"You must be at least {MIN_AGE} years old to continue."
        )
        age_title = f"Confirm you are {MIN_AGE}+"
        age_under = f"I am under {MIN_AGE}"
        age_ok = f"I am {MIN_AGE}+"
        cookie_title = "Cookie preferences"
        cookie_text = 'We use cookies to remember age verification. See <a class="inTextLink" href="cookie-policy.html">cookie policy</a>.'
        cookie_reject = "Essential only"
        cookie_accept = "Accept"
    else:
        age_body = (
            f"Deze site bespreekt gereguleerd gokken voor lezers in België. "
            f"U moet minstens {MIN_AGE} jaar zijn om verder te gaan."
        )
        age_title = f"Bevestig dat u {MIN_AGE} jaar of ouder bent"
        age_under = f"Ik ben jonger dan {MIN_AGE}"
        age_ok = f"Ik ben {MIN_AGE}+"
        cookie_title = "Cookievoorkeuren"
        cookie_text = 'We gebruiken cookies om de leeftijdscontrole te onthouden. Zie <a class="inTextLink" href="cookie-policy.html">cookiebeleid</a>.'
        cookie_reject = "Alleen essentieel"
        cookie_accept = "Accepteren"
    return f"""<motion class="complianceOverlay" id="ageGate" role="dialog" aria-modal="true" aria-labelledby="ageTitle">
  <div class="complianceDialog">
    <h2 id="ageTitle">{age_title}</h2>
    <p>{html.escape(age_body)}</p>
    <div class="complianceActions">
      <button type="button" class="btn" id="ageUnder">{age_under}</button>
      <button type="button" class="btn primary" id="ageOk">{age_ok}</button>
    </div>
  </div>
</div>
<div class="complianceOverlay" id="cookieGate" hidden aria-hidden="true" role="dialog" aria-modal="true" aria-labelledby="cookieTitle">
  <div class="complianceDialog">
    <h2 id="cookieTitle">{cookie_title}</h2>
    <p>{cookie_text}</p>
    <motion class="complianceActions">
      <button type="button" class="btn" id="cookieReject">{cookie_reject}</button>
      <button type="button" class="btn primary" id="cookieAccept">{cookie_accept}</button>
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
    og_locale = "en_BE" if _is_en() else "nl_BE"
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
<meta property="og:locale" content="{og_locale}" />
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
    nav_label = "Main navigation" if _is_en() else "Hoofdnavigatie"
    menu_label = "Open menu" if _is_en() else "Menu openen"
    off_site = "Official site" if _is_en() else "Officiële site"
    play_label = "Play now" if _is_en() else "Speel"
    return f"""<header class="rb-header">
  <div class="rb-headerInner">
    <a class="rb-brand" href="index.html" aria-label="Home {html.escape(SITE_NAME)}">
      <img src="assets/pictures/og-logo.svg" alt="" width="36" height="36" decoding="async" />
      <span class="rb-brandName">{html.escape(SITE_NAME.upper())}</span>
    </a>
    <nav class="rb-nav" id="mainNav" aria-label="{nav_label}">
{nav}
    </nav>
    <div class="rb-headerActions">
      <button class="btn icon rb-navToggle" id="navToggle" type="button" aria-label="{menu_label}" aria-expanded="false" aria-controls="mainNav">≡</button>
      <a class="btn" href="{m}" rel="noopener noreferrer" target="_blank">{off_site}</a>
      <a class="btn primary" href="{m}" rel="noopener noreferrer" target="_blank">{play_label}</a>
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
    nav_label = "Pages" if _is_en() else "Pagina's"
    legal_label = "Legal" if _is_en() else "Juridisch"
    providers_label = "Providers"
    payments_label = "Payment methods" if _is_en() else "Betaalmethoden"
    license_text = (
        f'<p class="rb-license"><span class="rb-age">{MIN_AGE}+</span> Curaçao eGaming — details on <a href="{m}" rel="noopener noreferrer" target="_blank">the official site</a>.</p>'
        if _is_en()
        else f'<p class="rb-license"><span class="rb-age">{MIN_AGE}+</span> Curaçao eGaming — details op <a href="{m}" rel="noopener noreferrer" target="_blank">de officiële site</a>.</p>'
    )
    copy_text = (
        f'© <span id="year"></span> {html.escape(SITE_NAME)}. Editorial review platform, not an operator.'
        if _is_en()
        else f'© <span id="year"></span> {html.escape(SITE_NAME)}. Redactioneel reviewplatform, geen exploitant.'
    )
    return f"""<footer class="rb-footer" id="footer">
  <nav class="rb-footerNav" aria-label="{nav_label}">
    <a href="index.html">Home</a>
{nav_content}
  </nav>
  <nav class="rb-footerLegal" aria-label="{legal_label}">
{chr(10).join(legal)}
  </nav>
  <div class="rb-footerBlock">
    <h3>{providers_label}</h3>
    <div class="rb-badges">
      <span class="rb-badge">Pragmatic Play</span><span class="rb-badge">NetEnt</span><span class="rb-badge">Evolution</span>
      <span class="rb-badge">Play'n GO</span><span class="rb-badge">Ezugi</span>
    </div>
  </motion>
  <div class="rb-footerBlock">
    <h3>{payments_label}</h3>
    <div class="rb-badges">
      <span class="rb-badge">Bancontact</span><span class="rb-badge">iDEAL</span><span class="rb-badge">Visa</span>
      <span class="rb-badge">Mastercard</span><span class="rb-badge">Payconiq</span>
    </div>
  </div>
  {license_text}
  <p class="rb-copy">{copy_text}</p>
</footer>""".replace("<motion class=", "<div class=").replace("</motion>", "</div>", 1)



def _landing_cta_label() -> str:
    return "Play at Cazilla" if _is_en() else "Speel bij Cazilla"


def _landing_cta() -> str:
    m = html.escape(MAIN)
    label = html.escape(_landing_cta_label())
    return (
        f'<p class="rb-ctaBar"><a class="btn primary" href="{m}" rel="noopener noreferrer" '
        f'target="_blank">{label}</a></p>'
    )


def _landing_figure(page_id: str, index: int) -> str:
    imgs = LANDING_IMAGES.get(page_id, LANDING_IMAGES["home"])
    alts_map = LANDING_IMG_ALT_EN if _is_en() else LANDING_IMG_ALT_NL
    alts = alts_map.get(page_id, alts_map["home"])
    i = min(max(index, 0), 2)
    src = html.escape(imgs[i])
    alt = html.escape(alts[i])
    return (
        f'<figure class="rb-landingMedia"><img src="assets/pictures/{src}" alt="{alt}" '
        f'width="720" loading="lazy" decoding="async" /></figure>'
    )


def landing_stub(page_id: str) -> str:
    if _is_en():
        h2_points, h2_steps, h2_table, faq_title = "Key points", "Recommended steps", "Quick comparison", "Frequently asked questions"
        li_points = ("Editorial point one (placeholder)", "Editorial point two (placeholder)", "Editorial point three (placeholder)")
        li_steps = ("Step one (placeholder)", "Step two (placeholder)", "Step three (placeholder)")
        th_crit, th_caz, th_check = "Criterion", "Cazilla", "Check"
        tr_bonus, tr_pay, tr_mob = ("Bonus", "On official site", "Wagering terms"), ("Payments", "Cards & e-wallets", "Withdrawal times"), ("Mobile", "Browser", "Stability")
        q1, q2, q3 = "Placeholder question 1?", "Placeholder question 2?", "Placeholder question 3?"
    else:
        h2_points, h2_steps, h2_table, faq_title = "Belangrijkste punten", "Aanbevolen stappen", "Snelle vergelijking", "Veelgestelde vragen"
        li_points = ("Redactioneel punt één (voorlopig)", "Redactioneel punt twee (voorlopig)", "Redactioneel punt drie (voorlopig)")
        li_steps = ("Stap één (voorlopig)", "Stap twee (voorlopig)", "Stap drie (voorlopig)")
        th_crit, th_caz, th_check = "Criterium", "Cazilla", "Te controleren"
        tr_bonus, tr_pay, tr_mob = ("Bonus", "Op officiële site", "Inzetvoorwaarden"), ("Betalingen", "Kaarten & e-wallets", "Uitbetalingstermijn"), ("Mobiel", "Browser", "Stabiliteit")
        q1, q2, q3 = "Voorlopige vraag 1?", "Voorlopige vraag 2?", "Voorlopige vraag 3?"
    ul = "\n".join(f"  <li>{html.escape(x)}</li>" for x in li_points)
    ol = "\n".join(f"  <li>{html.escape(x)}</li>" for x in li_steps)
    return f"""<p>{html.escape(STUB)}</p>
{_landing_cta()}
{_landing_figure(page_id, 0)}
<h2>{html.escape(h2_points)}</h2>
<p>{html.escape(STUB)}</p>
<ul>
{ul}
</ul>
{_landing_cta()}
{_landing_figure(page_id, 1)}
<h2>{html.escape(h2_steps)}</h2>
<p>{html.escape(STUB)}</p>
<ol>
{ol}
</ol>
{_landing_cta()}
<h2>{html.escape(h2_table)}</h2>
<p>{html.escape(STUB)}</p>
<table class="rb-dataTable">
  <thead><tr><th>{html.escape(th_crit)}</th><th>{html.escape(th_caz)}</th><th>{html.escape(th_check)}</th></tr></thead>
  <tbody>
    <tr><td>{html.escape(tr_bonus[0])}</td><td>{html.escape(tr_bonus[1])}</td><td>{html.escape(tr_bonus[2])}</td></tr>
    <tr><td>{html.escape(tr_pay[0])}</td><td>{html.escape(tr_pay[1])}</td><td>{html.escape(tr_pay[2])}</td></tr>
    <tr><td>{html.escape(tr_mob[0])}</td><td>{html.escape(tr_mob[1])}</td><td>{html.escape(tr_mob[2])}</td></tr>
  </tbody>
</table>
{_landing_cta()}
{_landing_figure(page_id, 2)}
<section class="rb-faq" aria-labelledby="rb-faq-title">
  <h2 id="rb-faq-title">{html.escape(faq_title)}</h2>
  <details open><summary>{html.escape(q1)}</summary><p>{html.escape(STUB)}</p></details>
  <details open><summary>{html.escape(q2)}</summary><p>{html.escape(STUB)}</p></details>
  <details open><summary>{html.escape(q3)}</summary><p>{html.escape(STUB)}</p></details>
</section>"""


def landing_body(page_id: str) -> str:
    return f"""
    <article class="rb-landing" data-a2-field="main_seo_html">
{landing_stub(page_id)}
    </article>"""


def content_page(page_id: str, rel: str, menu_label: str) -> str:
    title = f"{menu_label} | {SITE_NAME}"
    if _is_en():
        desc = f"{menu_label} — editorial Cazilla review for readers in Belgium ({MIN_AGE}+)."
        fine = f"{MIN_AGE}+ | Play responsibly | Belgium"
    else:
        desc = f"{menu_label} — redactioneel Cazilla-overzicht voor lezers in België ({MIN_AGE}+)."
        fine = f"{MIN_AGE}+ | Speel verantwoord | België"
    h1 = menu_label.replace("&amp;", "&")
    landing = landing_body(page_id)
    return f"""<!doctype html>
<html lang="{html.escape(HTML_LANG)}" data-site-kind="review-lobby" data-min-gambling-age="{MIN_AGE}">
  <head>
{head_block(rel, title, desc)}
  </head>
  <body class="rb-layout {_theme_class()}">
{_fix_html(compliance_block())}
<div id="siteContent" class="rb-app">
{site_header(rel)}
  <main class="rb-main" id="top">
    <h1 class="rb-pageTitle" data-a2-field="page_h1">{html.escape(h1)}</h1>
{landing}
    <p class="rb-fineprint" data-a2-field="footer_note">{html.escape(fine)}</p>
  </main>
{_fix_html(site_footer(rel))}
</div>
<script src="assets/rb-site.js" defer></script>
  </body>
</html>"""


def tech_policy_stub() -> str:
    back_home = "Back to home" if _is_en() else "Terug naar home"
    return (
        '<article class="rb-policyArticle" data-a2-field="main_seo_html">'
        f"<p>{html.escape(STUB)}</p>"
        f'<p><a href="index.html">{back_home}</a></p>'
        "</article>"
    )


def technical_page(rel: str, title: str, desc: str, h1: str, hero_sub: str, slug: str) -> str:
    body = tech_policy_stub()
    return f"""<!doctype html>
<html lang="{html.escape(HTML_LANG)}" data-site-kind="review-lobby" data-min-gambling-age="{MIN_AGE}">
  <head>
{head_block(rel, title, desc)}
  </head>
  <body class="rb-layout rb-layout--legal {_theme_class()}">
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
</div>
<script src="assets/rb-site.js" defer></script>
  </body>
</html>""".replace("</motion>\n<script", "</motion>\n<script").replace(
        "</motion>\n<script", "</div>\n<script"
    )


RB_LOBBY_CSS = """
/* Review lobby nl-BE — warm amber + emerald (distinct from fr-BE gold bar) */
body.rb-theme-nl {
  --rb-accent: #ea580c;
  --rb-accent2: #059669;
  --rb-bg: #12151a;
  --rb-panel: #1c2329;
  --rb-line: rgba(234, 88, 12, 0.22);
  --rb-text: #faf8f5;
  --rb-muted: #a8a29e;
  --rb-radius: 12px;
  --rb-radius-lg: 20px;
}

.rb-layout {
  margin: 0;
  background: var(--rb-bg);
  background-image: radial-gradient(ellipse 120% 80% at 100% -20%, rgba(5, 150, 105, 0.12), transparent 50%),
    radial-gradient(ellipse 90% 60% at 0% 100%, rgba(234, 88, 12, 0.08), transparent 45%);
  color: var(--rb-text);
  font-family: "Inter", "Nunito Sans", "Helvetica Neue", system-ui, sans-serif;
}

.rb-app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  max-width: 900px;
  margin: 0 auto;
  padding: 0 12px;
}

.rb-header {
  padding: 14px 16px;
  margin: 12px 0 0;
  background: var(--rb-panel);
  border: 1px solid var(--rb-line);
  border-left: 4px solid var(--rb-accent);
  border-radius: var(--rb-radius-lg);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);
  position: sticky;
  top: 10px;
  z-index: 30;
}

.rb-headerInner { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }

.rb-brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: inherit;
  font-weight: 800;
  font-size: 0.88rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  flex-shrink: 0;
}

.rb-brand img {
  border-radius: 50%;
  box-shadow: 0 0 0 2px var(--rb-accent2);
}

.rb-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  margin-left: auto;
}

.rb-nav a {
  color: var(--rb-muted);
  text-decoration: none;
  font-size: 13px;
  font-weight: 500;
  padding: 6px 12px;
  border-radius: 999px;
  transition: background 0.15s, color 0.15s;
}

.rb-nav a:hover { color: var(--rb-text); background: rgba(255, 255, 255, 0.06); }

.rb-nav a[aria-current="page"] {
  font-weight: 700;
  color: #0f1419;
  background: var(--rb-accent);
}

.rb-headerActions { display: flex; gap: 8px; align-items: center; flex-shrink: 0; }

.btn.icon {
  display: none;
  min-width: 40px;
  padding: 8px 12px;
  font-size: 18px;
  line-height: 1;
  border-radius: var(--rb-radius);
}

@media (max-width: 720px) {
  .btn.icon { display: inline-flex; }
  .rb-headerInner { position: relative; }
  .rb-nav {
    display: none;
    position: absolute;
    top: calc(100% + 8px);
    left: 0;
    right: 0;
    flex-direction: column;
    align-items: stretch;
    gap: 4px;
    margin: 0;
    padding: 12px;
    background: var(--rb-panel);
    border: 1px solid var(--rb-line);
    border-radius: var(--rb-radius);
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
  }
  .rb-nav[data-open="true"] { display: flex; }
  .rb-headerActions .btn:not(.icon):not(.primary) { display: none; }
}

.rb-main { flex: 1; padding: 20px 6px 36px; }

.rb-pageTitle {
  margin: 0 0 20px;
  padding: 0 0 0 14px;
  border-left: 4px solid var(--rb-accent2);
  font-size: clamp(1.4rem, 3.2vw, 1.85rem);
  font-weight: 800;
  color: var(--rb-text);
  letter-spacing: -0.02em;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 9px 16px;
  border-radius: var(--rb-radius);
  border: 1px solid var(--rb-line);
  background: #252d36;
  color: inherit;
  text-decoration: none;
  font-size: 14px;
  cursor: pointer;
  font-family: inherit;
  transition: background 0.15s, border-color 0.15s;
}

.btn:hover { border-color: var(--rb-accent2); }

.btn.primary {
  background: var(--rb-accent);
  border-color: transparent;
  color: #fff;
  font-weight: 700;
  box-shadow: 0 4px 14px rgba(234, 88, 12, 0.35);
}

.btn.primary:hover {
  background: #c2410c;
  box-shadow: 0 6px 20px rgba(234, 88, 12, 0.45);
}

/* Landing */
.rb-landing {
  margin-top: 4px;
  padding: 22px 20px 28px;
  border-radius: var(--rb-radius-lg);
  border: 1px solid var(--rb-line);
  background: var(--rb-panel);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.rb-landing h2 {
  margin: 1.5rem 0 0.65rem;
  padding-bottom: 6px;
  font-size: 1.12rem;
  font-weight: 700;
  color: #fef3c7;
  border-bottom: 2px solid var(--rb-accent2);
  display: inline-block;
}

.rb-landing p,
.rb-landing li { line-height: 1.75; color: #d6d3d1; }

.rb-landing ul,
.rb-landing ol { margin: 0.5rem 0 1rem; padding-left: 1.35rem; }

.rb-ctaBar {
  display: flex;
  justify-content: center;
  align-items: center;
  margin: 1.5rem 0;
}

.rb-ctaBar .btn.primary {
  padding: 12px 28px;
  border-radius: 999px;
  font-size: 15px;
  letter-spacing: 0.02em;
}

.rb-landingMedia {
  margin: 1.25rem 0;
  border-radius: var(--rb-radius);
  border: 2px dashed rgba(5, 150, 105, 0.45);
  background: rgba(5, 150, 105, 0.06);
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 14px 16px;
}

.rb-landingMedia img {
  width: auto;
  max-width: min(100%, 520px);
  height: auto;
  max-height: 220px;
  object-fit: contain;
  object-position: center;
  display: block;
  margin: 0 auto;
  border-radius: 8px;
}

@media (max-width: 640px) {
  .rb-landingMedia { padding: 10px 12px; }
  .rb-landingMedia img { max-width: 100%; max-height: 180px; }
}

.rb-dataTable {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  margin: 0.75rem 0 1rem;
  font-size: 14px;
  border-radius: var(--rb-radius);
  overflow: hidden;
  border: 1px solid var(--rb-line);
}

.rb-dataTable th,
.rb-dataTable td {
  border: none;
  border-bottom: 1px solid var(--rb-line);
  padding: 11px 14px;
  text-align: left;
}

.rb-dataTable tr:last-child td { border-bottom: none; }

.rb-dataTable th {
  background: rgba(5, 150, 105, 0.2);
  color: #ecfdf5;
  font-weight: 600;
}

.rb-dataTable tr:nth-child(even) td { background: rgba(0, 0, 0, 0.15); }

.rb-faq {
  margin-top: 1.75rem;
  padding-top: 1rem;
  border-top: 2px solid var(--rb-line);
}

.rb-faq details {
  margin-bottom: 10px;
  border: none;
  border-left: 3px solid var(--rb-accent2);
  border-radius: 0 var(--rb-radius) var(--rb-radius) 0;
  padding: 12px 14px 12px 16px;
  background: rgba(0, 0, 0, 0.2);
}

.rb-faq details[open] { padding-bottom: 14px; background: rgba(5, 150, 105, 0.08); }

.rb-faq summary {
  cursor: default;
  font-weight: 600;
  color: #fef3c7;
  padding: 0 0 8px;
  list-style: none;
  pointer-events: none;
}

.rb-faq summary::-webkit-details-marker { display: none; }
.rb-faq summary::marker { content: ""; }
.rb-faq details > p { margin: 0; padding: 0; color: #d6d3d1; }

.rb-fineprint {
  font-size: 13px;
  color: var(--rb-muted);
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px dashed var(--rb-line);
  text-align: center;
}

/* Footer */
.rb-footer {
  padding: 28px 16px 24px;
  margin: 0 -12px;
  border-top: none;
  background: #0d1014;
  margin-top: auto;
  position: relative;
}

.rb-footer::before {
  content: "";
  display: block;
  height: 3px;
  margin: 0 16px 20px;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--rb-accent2), var(--rb-accent), var(--rb-accent2));
}

.rb-footerNav,
.rb-footerLegal {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 16px;
  margin-bottom: 14px;
}

.rb-footerNav a,
.rb-footerLegal a {
  color: var(--rb-muted);
  font-size: 13px;
  text-decoration: none;
}

.rb-footerNav a:hover,
.rb-footerLegal a:hover { color: var(--rb-accent); }

.rb-footerBlock h3 {
  margin: 0 0 8px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--rb-accent2);
}

.rb-badges { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }

.rb-badge {
  padding: 5px 11px;
  border-radius: 6px;
  font-size: 12px;
  background: #252d36;
  border: 1px solid var(--rb-line);
}

.rb-license {
  font-size: 13px;
  color: var(--rb-muted);
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.rb-age {
  display: inline-flex;
  padding: 4px 10px;
  border-radius: 6px;
  font-weight: 800;
  background: var(--rb-accent);
  color: #fff;
}

.rb-copy { font-size: 12px; color: var(--rb-muted); margin: 12px 0 0; }

/* Legal pages */
.rb-legalHero {
  margin-bottom: 20px;
  padding: 18px 20px;
  border-radius: var(--rb-radius);
  border-left: 4px solid var(--rb-accent2);
  background: rgba(5, 150, 105, 0.1);
}

.rb-legalHero h1 { margin: 0 0 8px; font-size: clamp(1.25rem, 3vw, 1.6rem); }

.rb-lead { color: var(--rb-muted); line-height: 1.65; margin: 0; }

.rb-policyCard {
  margin-bottom: 20px;
  padding: 4px 0;
  border-radius: var(--rb-radius);
}

.rb-policyArticle p { line-height: 1.75; color: #d6d3d1; }

body.rb-layout--legal .rb-main { max-width: 820px; }

body.rb-layout--legal .rb-header { position: relative; top: auto; }

.policyCta {
  text-align: center;
  margin: 24px 0 8px;
}

.policyCta a {
  display: inline-flex;
  padding: 12px 26px;
  border-radius: 999px;
  background: var(--rb-accent);
  color: #fff !important;
  font-weight: 700;
  text-decoration: none;
  box-shadow: 0 4px 14px rgba(234, 88, 12, 0.35);
}

.policyCta a:hover { background: #c2410c; }

/* Legacy lobby blocks (if any remain in HTML) */
.rb-promo,
.rb-liveHero {
  text-align: center;
  padding: 28px 20px;
  margin-bottom: 22px;
  border-radius: var(--rb-radius-lg);
  background: linear-gradient(145deg, rgba(5, 150, 105, 0.25) 0%, rgba(234, 88, 12, 0.15) 100%);
  border: 1px solid var(--rb-line);
}

.rb-gameRow,
.rb-bonusCard,
.rb-aboutCard {
  border-radius: var(--rb-radius);
  border: 1px solid var(--rb-line);
  background: var(--rb-panel);
}

.rb-seoProse {
  margin-top: 24px;
  padding: 18px;
  border-radius: var(--rb-radius);
  border: 1px solid var(--rb-line);
  background: rgba(5, 150, 105, 0.06);
}

.rb-seoProse p,
.rb-seoProse li { line-height: 1.7; color: #d6d3d1; }

body.rb-theme-enbe {
  --rb-accent: #f97316;
  --rb-accent2: #fb7185;
  --rb-bg: #111111;
  --rb-panel: #1c1c1c;
  --rb-line: rgba(251, 113, 133, 0.24);
  --rb-text: #f8fafc;
  --rb-muted: #cbd5e1;
}
"""

RB_COMPLIANCE_CSS = """
#siteContent.isBlurred { filter: blur(12px); user-select: none; pointer-events: none; }
.complianceOverlay {
  position: fixed;
  inset: 0;
  z-index: 500;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(18, 21, 26, 0.88);
  backdrop-filter: blur(8px);
}
.complianceOverlay[hidden] { display: none !important; }
.complianceDialog {
  width: min(420px, 100%);
  border-radius: 20px;
  border: 1px solid rgba(234, 88, 12, 0.45);
  border-top: 4px solid #059669;
  background: #1c2329;
  color: #faf8f5;
  padding: 24px;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.55);
}
.complianceDialog h2 { margin: 0 0 10px; font-size: 18px; color: #fef3c7; }
.complianceDialog p { margin: 0 0 14px; color: #d6d3d1; font-size: 14px; line-height: 1.55; }
.complianceActions { display: flex; flex-wrap: wrap; gap: 10px; }
.complianceDialog .btn.primary { background: #ea580c; color: #fff; }
.inTextLink { color: #6ee7b7; text-decoration: underline; }
html.complianceNoScroll,
html.complianceNoScroll body { overflow: hidden; height: 100%; }
"""

RB_SITE_JS = """
(function () {
  "use strict";
  var AGE = "cazilla_review_lobby_age_ok";
  var COOKIE = "cazilla_review_lobby_cookie";
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
      navToggle.setAttribute("aria-label", open ? "Open menu" : "Close menu");
    });
    document.addEventListener("click", function (ev) {
      if (mainNav.dataset.open !== "true") return;
      if (mainNav.contains(ev.target) || navToggle.contains(ev.target)) return;
      mainNav.dataset.open = "false";
      navToggle.setAttribute("aria-expanded", "false");
      navToggle.setAttribute("aria-label", "Open menu");
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


def write_robots_sitemap() -> None:
    origin = ORIGIN.rstrip("/")
    hreflang = HTML_LANG
    (SITE / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {origin}/sitemap.xml\n",
        encoding="utf-8",
    )
    urls: list[str] = []
    for _pid, rel, _lab in CONTENT_PAGES:
        urls.append(origin + ("/" if rel == "index.html" else f"/{rel}"))
    for _slug, rel, *_rest in TECH_SPECS:
        urls.append(f"{origin}/{rel}")
    entries = []
    for loc in urls:
        pri = "1.0" if loc.endswith("index.html") or loc.rstrip("/") == origin else "0.85"
        entries.append(
            f'  <url>\n    <loc>{html.escape(loc)}</loc>\n'
            f'    <xhtml:link rel="alternate" hreflang="{html.escape(hreflang)}" href="{html.escape(loc)}"/>\n'
            f'    <xhtml:link rel="alternate" hreflang="x-default" href="{html.escape(loc)}"/>\n'
            f"    <lastmod>2026-05-20</lastmod>\n    <changefreq>weekly</changefreq>\n    <priority>{pri}</priority>\n  </url>"
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
        '        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        + "\n".join(entries)
        + "\n</urlset>\n"
    )
    (SITE / "sitemap.xml").write_text(xml, encoding="utf-8")


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
    write_robots_sitemap()
    print("Bootstrap complete ->", SITE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
