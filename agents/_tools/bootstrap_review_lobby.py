#!/usr/bin/env python3
"""Bootstrap: review lobby site (fr-BE) — landing template on 4 main pages + 7 technical pages."""
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

from _lib.locale_context import LocaleContext, locale_context_from_env  # noqa: E402
from _lib.repo_env import load_dotenv_file  # noqa: E402

ENV_PATH = ROOT / ".env"
CLONE_ASSETS = ROOT / "sites" / "cazilla-clone1-fr-be" / "assets"
PIC_SRC = ROOT / "sites" / "cazilla-offerwall2-en-ie" / "assets" / "pictures"

SITE: Path = ROOT / "sites" / "cazilla-review1-fr-be"
ORIGIN = "https://cazilla.cfd"
MAIN = "https://cazilla.casino"
SITE_SLUG = "cazilla-review1-fr-be"
SITE_NAME = "Cazilla Belgique"
HTML_LANG = "fr-BE"
MIN_AGE = 21
LC: LocaleContext | None = None
STUB = "Texte éditorial provisoire. A2 remplacera ce contenu."
CONTENT_PAGES: list[tuple[str, str, str]] = []
FOOTER_LEGAL: list[tuple[str, str]] = []
TECH_SPECS: list[tuple[str, str, str, str, str, str]] = []

# Three images per main page (landing wireframe positions 3, 6, 11)
LANDING_IMAGES: dict[str, tuple[str, str, str]] = {
    "home": (
        "casino-feature-visual.png",
        "slots-showcase.png",
        "live-tables.jpg",
    ),
    "slots": (
        "slots-showcase.png",
        "fruit-classic-slot.png",
        "big-bass-bonanza-review.avif",
    ),
    "bonus": (
        "bonus-promo-artwork.webp",
        "baccarat-bonus-terms.webp",
        "crazy-time-bonus.jpg",
    ),
    "about": (
        "casino-feature-visual.png",
        "og-logo.svg",
        "blackjack-green-table.jpg",
    ),
}

LANDING_IMG_ALT: dict[str, tuple[str, str, str]] = {
    "home": (
        "Lobby Cazilla — casino en ligne Belgique",
        "Catalogue machines à sous",
        "Tables casino en direct",
    ),
    "slots": (
        "Machines à sous populaires",
        "Machine à sous classique",
        "Big Bass Bonanza — aperçu",
    ),
    "bonus": (
        "Offres bonus Cazilla",
        "Bonus baccarat — conditions",
        "Promotion Crazy Time",
    ),
    "about": (
        "Cazilla Belgique — hub éditorial",
        "Logo Cazilla",
        "Blackjack en direct",
    ),
}


def init_site() -> None:
    global SITE, ORIGIN, MAIN, SITE_SLUG, SITE_NAME, HTML_LANG, LC, STUB
    env = load_dotenv_file(ENV_PATH)
    rel = (env.get("SITE_DIR") or "sites/cazilla-review1-fr-be").strip().lstrip("/")
    SITE = ROOT / rel
    SITE_SLUG = Path(rel).name
    ORIGIN = (env.get("SITE_URL") or "https://cazilla.cfd").strip().rstrip("/")
    MAIN = (env.get("MAIN_CASINO_URL") or "https://cazilla.casino").strip().rstrip("/")
    LC = locale_context_from_env(env, strict_keywords_match=False)
    HTML_LANG = LC.locale.replace("_", "-") if "_" in LC.locale else LC.locale
    SITE_NAME = "Cazilla Belgique"
    STUB = f"Texte éditorial provisoire. A2 remplacera par un contenu optimisé pour {LC.audience_phrase}."
    _load_keywords()


def _load_keywords() -> None:
    global CONTENT_PAGES, FOOTER_LEGAL, TECH_SPECS
    kw_path = SITE / "_output" / "keywords.json"
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
        desc = f"{menu} — {SITE_NAME}, {LC.region_name if LC else 'Belgique'}."
        sub = f"{menu} — informations pour {LC.audience_phrase if LC else 'lecteurs en Belgique'}."
        TECH_SPECS.append((slug, rel, title, desc, html.escape(menu), html.escape(sub)))
        FOOTER_LEGAL.append((rel, html.escape(menu)))


def compliance_block() -> str:
    return """<div class="complianceOverlay" id="ageGate" role="dialog" aria-modal="true" aria-labelledby="ageTitle">
  <div class="complianceDialog">
    <h2 id="ageTitle">Confirmez que vous avez 21 ans ou plus</h2>
    <p>Ce site traite des jeux d'argent réglementés pour lecteurs en Belgique. Vous devez avoir au moins 21 ans pour continuer.</p>
    <div class="complianceActions">
      <button type="button" class="btn" id="ageUnder">J'ai moins de 21 ans</button>
      <button type="button" class="btn primary" id="ageOk">J'ai 21 ans ou plus</button>
    </div>
  </div>
</div>
<div class="complianceOverlay" id="cookieGate" hidden aria-hidden="true" role="dialog" aria-modal="true" aria-labelledby="cookieTitle">
  <div class="complianceDialog">
    <h2 id="cookieTitle">Préférences cookies</h2>
    <p>Nous utilisons des cookies pour mémoriser la vérification d'âge. Voir <a class="inTextLink" href="cookie-policy.html">politique de cookies</a>.</p>
    <div class="complianceActions">
      <button type="button" class="btn" id="cookieReject">Essentiels uniquement</button>
      <button type="button" class="btn primary" id="cookieAccept">Accepter</button>
    </div>
  </div>
</div>"""


def _fix_compliance(s: str) -> str:
    return s.replace("<motion class", "<div class").replace("</motion>", "</motion>").replace(
        'aria-labelledby="cookieTitle">\n  <div', 'aria-labelledby="cookieTitle">\n  <div'
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
<meta property="og:locale" content="fr_BE" />
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
    <a class="rb-brand" href="index.html" aria-label="Accueil {html.escape(SITE_NAME)}">
      <img src="assets/pictures/og-logo.svg" alt="" width="36" height="36" decoding="async" />
      <span class="rb-brandName">{html.escape(SITE_NAME.upper())}</span>
    </a>
    <nav class="rb-nav" id="mainNav" aria-label="Navigation principale">
{nav}
    </nav>
    <div class="rb-headerActions">
      <button class="btn icon rb-navToggle" id="navToggle" type="button" aria-label="Ouvrir le menu" aria-expanded="false" aria-controls="mainNav">≡</button>
      <a class="btn" href="{m}" rel="noopener noreferrer" target="_blank">Site officiel</a>
      <a class="btn primary" href="{m}" rel="noopener noreferrer" target="_blank">Jouer</a>
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
  <nav class="rb-footerNav" aria-label="Pages du site">
    <a href="index.html">Accueil</a>
{nav_content}
  </nav>
  <nav class="rb-footerLegal" aria-label="Pages légales">
{chr(10).join(legal)}
  </nav>
  <div class="rb-footerBlock">
    <h3>Fournisseurs</h3>
    <div class="rb-badges">
      <span class="rb-badge">Pragmatic Play</span><span class="rb-badge">NetEnt</span><span class="rb-badge">Evolution</span>
      <span class="rb-badge">Play'n GO</span><span class="rb-badge">Habanero</span>
    </div>
  </div>
  <div class="rb-footerBlock">
    <h3>Paiements</h3>
    <div class="rb-badges">
      <span class="rb-badge">Visa</span><span class="rb-badge">Mastercard</span><span class="rb-badge">Bancontact</span>
      <span class="rb-badge">Bitcoin</span><span class="rb-badge">Skrill</span>
    </div>
  </div>
  <p class="rb-license"><span class="rb-age">21+</span> Licence Curaçao eGaming — vérifiez les détails sur <a href="{m}" rel="noopener noreferrer" target="_blank">le site officiel</a>.</p>
  <p class="rb-copy">© <span id="year">2026</span> {html.escape(SITE_NAME)}. Lobby éditorial — liens de jeu vers l'opérateur.</p>
</footer>"""


def _landing_cta() -> str:
    m = html.escape(MAIN)
    return (
        f'<p class="rb-ctaBar"><a class="btn primary" href="{m}" rel="noopener noreferrer" '
        f'target="_blank">Jouer sur Cazilla</a></p>'
    )


def _landing_figure(page_id: str, index: int) -> str:
    imgs = LANDING_IMAGES.get(page_id, LANDING_IMAGES["home"])
    alts = LANDING_IMG_ALT.get(page_id, LANDING_IMG_ALT["home"])
    i = min(max(index, 0), 2)
    src = html.escape(imgs[i])
    alt = html.escape(alts[i])
    return (
        f'<figure class="rb-landingMedia"><img src="assets/pictures/{src}" alt="{alt}" '
        f'width="720" loading="lazy" decoding="async" /></figure>'
    )


def landing_stub(page_id: str) -> str:
    """Stub inside article[data-a2-field=main_seo_html]; A2 replaces the whole article body."""
    return f"""<p>{html.escape(STUB)}</p>
{_landing_cta()}
{_landing_figure(page_id, 0)}
<h2>Points clés</h2>
<p>{html.escape(STUB)}</p>
<ul>
  <li>Point éditorial provisoire un</li>
  <li>Point éditorial provisoire deux</li>
  <li>Point éditorial provisoire trois</li>
</ul>
{_landing_cta()}
{_landing_figure(page_id, 1)}
<h2>Étapes recommandées</h2>
<p>{html.escape(STUB)}</p>
<ol>
  <li>Étape provisoire un</li>
  <li>Étape provisoire deux</li>
  <li>Étape provisoire trois</li>
</ol>
{_landing_cta()}
<h2>Comparatif rapide</h2>
<p>{html.escape(STUB)}</p>
<table class="rb-dataTable">
  <thead><tr><th>Critère</th><th>Cazilla</th><th>À vérifier</th></tr></thead>
  <tbody>
    <tr><td>Bonus</td><td>Sur le site officiel</td><td>Conditions de mise</td></tr>
    <tr><td>Paiements</td><td>Cartes &amp; e-wallets</td><td>Délais de retrait</td></tr>
    <tr><td>Mobile</td><td>Navigateur</td><td>Stabilité</td></tr>
  </tbody>
</table>
{_landing_cta()}
{_landing_figure(page_id, 2)}
<section class="rb-faq" aria-labelledby="rb-faq-title">
  <h2 id="rb-faq-title">Questions fréquentes</h2>
  <details open><summary>Question provisoire 1 ?</summary><p>{html.escape(STUB)}</p></details>
  <details open><summary>Question provisoire 2 ?</summary><p>{html.escape(STUB)}</p></details>
  <details open><summary>Question provisoire 3 ?</summary><p>{html.escape(STUB)}</p></details>
</section>"""


def landing_body(page_id: str) -> str:
    return f"""
    <article class="rb-landing" data-a2-field="main_seo_html">
{landing_stub(page_id)}
    </article>"""


def content_page(page_id: str, rel: str, menu_label: str) -> str:
    title = f"{menu_label} | {SITE_NAME}"
    desc = f"{menu_label} — avis éditorial Cazilla pour lecteurs en Belgique (21+)."
    h1 = menu_label.replace("&amp;", "&")
    landing = landing_body(page_id)
    return f"""<!doctype html>
<html lang="{html.escape(HTML_LANG)}" data-site-kind="review-lobby" data-min-gambling-age="{MIN_AGE}">
  <head>
{head_block(rel, title, desc)}
  </head>
  <body class="rb-layout">
{compliance_block()}
<div id="siteContent" class="rb-app">
{site_header(rel)}
  <main class="rb-main" id="top">
    <h1 class="rb-pageTitle" data-a2-field="page_h1">{html.escape(h1)}</h1>
{landing}
    <p class="rb-fineprint" data-a2-field="footer_note">21+ | Jeu responsable | Belgique</p>
  </main>
{site_footer(rel)}
</div>
<script src="assets/rb-site.js" defer></script>
  </body>
</html>"""


def tech_policy_stub(slug: str) -> str:
    return (
        '<article class="rb-policyArticle" data-a2-field="main_seo_html">'
        f"<p>{html.escape(STUB)}</p>"
        '<p><a href="index.html">Retour à l\'accueil</a></p>'
        "</article>"
    )


def technical_page(rel: str, title: str, desc: str, h1: str, hero_sub: str, slug: str) -> str:
    body = tech_policy_stub(slug)
    return f"""<!doctype html>
<html lang="{html.escape(HTML_LANG)}" data-site-kind="review-lobby" data-min-gambling-age="{MIN_AGE}">
  <head>
{head_block(rel, title, desc)}
  </head>
  <body class="rb-layout rb-layout--legal">
{compliance_block()}
<div id="siteContent" class="rb-app">
{site_header(rel)}
  <main class="rb-main" id="top">
    <section class="rb-legalHero">
      <h1 data-a2-field="page_h1">{h1}</h1>
      <p class="rb-lead" data-a2-field="page_lead">{hero_sub}</p>
    </section>
    <div class="rb-policyCard">{body}</div>
  </main>
{site_footer(rel)}
</div>
<script src="assets/rb-site.js" defer></script>
  </body>
</html>"""


RB_SHELL_CSS = (CLONE_ASSETS / "cl-shell.css").read_text(encoding="utf-8") if (CLONE_ASSETS / "cl-shell.css").is_file() else ""

RB_LOBBY_CSS = """
/* Review lobby layout — minimal header, vertical game list */
.rb-layout { margin: 0; background: var(--cl-bg, #14161c); color: var(--cl-text, #f5f0e8); font-family: system-ui, sans-serif; }
.rb-app { min-height: 100vh; display: flex; flex-direction: column; max-width: 920px; margin: 0 auto; }
.rb-header { padding: 12px 18px; background: #0f1115; border-bottom: 2px solid var(--cl-accent, #c9a227); position: relative; z-index: 30; }
.rb-headerInner { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
.rb-brand { display: inline-flex; align-items: center; gap: 10px; text-decoration: none; color: inherit; font-weight: 800; font-size: 0.95rem; letter-spacing: 0.04em; flex-shrink: 0; }
.rb-brand img { border-radius: 8px; }
.rb-nav { display: flex; flex-wrap: wrap; gap: 6px 18px; align-items: center; margin-left: auto; }
.rb-nav a { color: var(--cl-muted, #a8a29e); text-decoration: none; font-size: 14px; font-weight: 500; }
.rb-nav a:hover, .rb-nav a[aria-current="page"] { color: var(--cl-text, #f5f0e8); }
.rb-nav a[aria-current="page"] { font-weight: 700; color: var(--cl-accent, #c9a227); }
.rb-headerActions { display: flex; gap: 8px; align-items: center; flex-shrink: 0; }
.btn.icon { display: none; min-width: 40px; padding: 8px 12px; font-size: 18px; line-height: 1; }
@media (max-width: 720px) {
  .btn.icon { display: inline-flex; }
  .rb-headerInner { position: relative; }
  .rb-nav { display: none; position: absolute; top: 100%; left: -18px; right: -18px; flex-direction: column; align-items: stretch; gap: 4px; margin: 0; padding: 12px 18px 16px; background: #0f1115; border-bottom: 2px solid var(--cl-accent, #c9a227); }
  .rb-nav[data-open="true"] { display: flex; }
  .rb-headerActions .btn:not(.icon):not(.primary) { display: none; }
}
.rb-main { flex: 1; padding: 18px 18px 32px; }
.rb-pageTitle { margin: 0 0 16px; font-size: clamp(1.35rem, 3vw, 1.75rem); }
.rb-promo { text-align: center; padding: 28px 20px; margin-bottom: 22px; border-radius: 14px;
  background: linear-gradient(135deg, #1b4332 0%, #3d2c1e 50%, #1a1d24 100%);
  border: 1px solid rgba(201, 162, 39, 0.25); }
.rb-promoTitle { margin: 0 0 10px; font-size: clamp(1.2rem, 3vw, 1.65rem); color: #fef3c7; }
.rb-promoLead { margin: 0 0 16px; color: #d6d3d1; font-size: 15px; }
.rb-section { margin-bottom: 28px; scroll-margin-top: 80px; }
.rb-sectionTitle { margin: 0 0 14px; font-size: 1.1rem; }
.rb-tags { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
.rb-tag { font-size: 12px; padding: 6px 12px; border-radius: 999px; background: #1e293b; color: inherit; cursor: default; }
.rb-tag.is-active { background: var(--cl-accent, #c9a227); color: #1a1a1a; font-weight: 700; }
.rb-gameList { display: flex; flex-direction: column; gap: 12px; margin: 0; padding: 0; list-style: none; }
.rb-gameRow { display: flex; gap: 14px; align-items: center; padding: 12px; border-radius: 12px;
  border: 1px solid var(--cl-line, rgba(255,255,255,0.1)); background: var(--cl-panel, #1c1f28); }
.rb-gameRow--featured { border: 2px solid var(--cl-accent, #c9a227); background: linear-gradient(90deg, rgba(201,162,39,0.08), transparent); }
.rb-gameRowThumb { flex: 0 0 140px; border-radius: 10px; overflow: hidden; }
.rb-gameRowThumb img { width: 100%; height: 90px; object-fit: cover; display: block; }
.rb-gameRowBody { flex: 1; min-width: 0; }
.rb-gameRowTag { margin: 0 0 4px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--cl-muted); }
.rb-gameRowTitle { margin: 0 0 8px; font-size: 1.05rem; }
.rb-gameRowActions { display: flex; flex-wrap: wrap; gap: 8px; }
.rb-liveGrid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
@media (max-width: 640px) { .rb-liveGrid { grid-template-columns: 1fr; } .rb-gameRow { flex-direction: column; align-items: stretch; } .rb-gameRowThumb { flex-basis: auto; } }
.rb-liveCard { display: block; text-decoration: none; color: inherit; border-radius: 12px; overflow: hidden; border: 1px solid var(--cl-line); background: var(--cl-panel); }
.rb-liveCard img { width: 100%; height: 120px; object-fit: cover; display: block; }
.rb-liveCard h3 { margin: 10px 12px 12px; font-size: 15px; }
.rb-toolbar { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 14px; }
.rb-tool { font-size: 13px; color: var(--cl-muted); display: flex; flex-direction: column; gap: 4px; }
.rb-tool input, .rb-tool select { padding: 8px 10px; border-radius: 8px; border: 1px solid var(--cl-line); background: #0b0f14; color: inherit; min-width: 180px; }
.rb-more { text-align: center; margin: 20px 0; }
.rb-bonusGrid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 14px; margin-bottom: 20px; }
.rb-bonusCard { padding: 16px; border-radius: 12px; border: 1px solid var(--cl-line); background: var(--cl-panel); }
.rb-bonusCard h3 { margin: 0 0 8px; font-size: 1rem; }
.rb-bonusCard p { margin: 0 0 12px; font-size: 14px; color: var(--cl-muted); }
.rb-bonusCardActions { display: flex; flex-wrap: wrap; gap: 8px; }
.rb-termsBox, .rb-licenseBox { padding: 16px; border-radius: 12px; border: 1px solid var(--cl-line); background: rgba(255,255,255,0.03); margin-top: 16px; }
.rb-termsBox ul { margin: 0; padding-left: 1.2rem; color: #cbd5e1; line-height: 1.6; }
.rb-aboutIntro p { line-height: 1.65; color: #cbd5e1; }
.rb-aboutGrid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }
.rb-aboutCard { padding: 14px; border-radius: 12px; border: 1px solid var(--cl-line); background: var(--cl-panel); }
.rb-aboutCard h3 { margin: 0 0 8px; font-size: 15px; }
.rb-seoProse { margin-top: 24px; padding: 18px; border-radius: 12px; border: 1px solid var(--cl-line); background: rgba(45,106,79,0.06); }
.rb-seoProse p, .rb-seoProse li { line-height: 1.7; color: #cbd5e1; }
.rb-fineprint { font-size: 13px; color: var(--cl-muted); margin-top: 20px; }
.rb-footer { padding: 24px 18px; border-top: 1px solid var(--cl-line); background: #0b0f14; margin-top: auto; }
.rb-footerNav, .rb-footerLegal { display: flex; flex-wrap: wrap; gap: 10px 16px; margin-bottom: 14px; }
.rb-footerNav a, .rb-footerLegal a { color: var(--cl-muted); font-size: 13px; text-decoration: none; }
.rb-footerNav a:hover, .rb-footerLegal a:hover { color: var(--cl-text); }
.rb-footerBlock h3 { margin: 0 0 8px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--cl-muted); }
.rb-badges { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
.rb-badge { padding: 5px 10px; border-radius: 8px; font-size: 12px; background: #1e293b; border: 1px solid var(--cl-line); }
.rb-license { font-size: 13px; color: var(--cl-muted); display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }
.rb-age { display: inline-flex; padding: 4px 10px; border-radius: 6px; font-weight: 800; background: var(--cl-accent); color: #1a1a1a; }
.rb-copy { font-size: 12px; color: var(--cl-muted); margin: 12px 0 0; }
.rb-legalHero { margin-bottom: 16px; }
.rb-lead { color: var(--cl-muted); line-height: 1.6; }
.rb-policyCard { margin-bottom: 20px; }
.rb-policyArticle p { line-height: 1.7; color: #cbd5e1; }
body.rb-layout--legal .rb-main { max-width: 820px; }
.btn { display: inline-flex; align-items: center; justify-content: center; padding: 8px 14px; border-radius: 8px; border: 1px solid var(--cl-line); background: #1e293b; color: inherit; text-decoration: none; font-size: 14px; cursor: pointer; font-family: inherit; }
.btn.primary { background: var(--cl-accent, #c9a227); border-color: transparent; color: #1a1a1a; font-weight: 700; }

/* Landing wireframe (4 main pages) */
.rb-landing { margin-top: 8px; }
.rb-landing h2 { margin: 1.4rem 0 0.6rem; font-size: 1.15rem; color: #fef3c7; }
.rb-landing p, .rb-landing li { line-height: 1.7; color: #cbd5e1; }
.rb-landing ul, .rb-landing ol { margin: 0.5rem 0 1rem; padding-left: 1.25rem; }
.rb-ctaBar { display: flex; justify-content: center; align-items: center; margin: 1.25rem 0; }
.rb-landingMedia { margin: 1rem 0; border-radius: 12px; border: 1px solid var(--cl-line); background: var(--cl-panel, #1c1f28); display: flex; justify-content: center; align-items: center; padding: 10px 14px; }
.rb-landingMedia img { width: auto; max-width: min(100%, 520px); height: auto; max-height: 220px; object-fit: contain; object-position: center; display: block; margin: 0 auto; }
@media (max-width: 640px) {
  .rb-landingMedia { padding: 8px 10px; }
  .rb-landingMedia img { max-width: 100%; max-height: 180px; }
}

.rb-dataTable { width: 100%; border-collapse: collapse; margin: 0.75rem 0 1rem; font-size: 14px; }
.rb-dataTable th, .rb-dataTable td { border: 1px solid var(--cl-line); padding: 10px 12px; text-align: left; }
.rb-dataTable th { background: rgba(201,162,39,0.12); color: #fef3c7; }
.rb-faq { margin-top: 1.5rem; padding-top: 0.5rem; border-top: 1px solid var(--cl-line); }
.rb-faq details { margin-bottom: 12px; border: 1px solid var(--cl-line); border-radius: 10px; padding: 12px 14px; background: var(--cl-panel); }
.rb-faq details[open] { padding-bottom: 14px; }
.rb-faq summary { cursor: default; font-weight: 600; padding: 0 0 8px; list-style: none; pointer-events: none; }
.rb-faq summary::-webkit-details-marker { display: none; }
.rb-faq summary::marker { content: ""; }
.rb-faq details > p { margin: 0; padding: 0; }
body.rb-layout { --cl-accent: #c9a227; --cl-accent2: #2d6a4f; --cl-bg: #14161c; --cl-panel: #1c1f28; --cl-line: rgba(201,162,39,0.12); --cl-text: #f5f0e8; --cl-muted: #a8a29e; }
"""

RB_COMPLIANCE_CSS = """
#siteContent.isBlurred { filter: blur(12px); user-select: none; pointer-events: none; }
.complianceOverlay { position: fixed; inset: 0; z-index: 500; display: grid; place-items: center; padding: 20px; background: rgba(6,5,12,0.78); backdrop-filter: blur(6px); }
.complianceOverlay[hidden] { display: none !important; }
.complianceDialog { width: min(420px,100%); border-radius: 14px; border: 1px solid rgba(201,162,39,0.35); background: #1c1f28; color: #f5f0e8; padding: 22px; box-shadow: 0 24px 60px rgba(0,0,0,0.5); }
.complianceDialog h2 { margin: 0 0 10px; font-size: 18px; }
.complianceDialog p { margin: 0 0 14px; color: #cbd5e1; font-size: 14px; line-height: 1.55; }
.complianceActions { display: flex; flex-wrap: wrap; gap: 10px; }
.inTextLink { color: #e9d5ff; }
html.complianceNoScroll, html.complianceNoScroll body { overflow: hidden; height: 100%; }
"""

RB_SITE_JS = """
(function () {
  "use strict";
  var AGE = "cazilla_review1_fr_be_age_ok";
  var COOKIE = "cazilla_review1_fr_be_cookie";
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
      navToggle.setAttribute("aria-label", open ? "Ouvrir le menu" : "Fermer le menu");
    });
    document.addEventListener("click", function (ev) {
      if (mainNav.dataset.open !== "true") return;
      if (mainNav.contains(ev.target) || navToggle.contains(ev.target)) return;
      mainNav.dataset.open = "false";
      navToggle.setAttribute("aria-expanded", "false");
      navToggle.setAttribute("aria-label", "Ouvrir le menu");
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
    shell = RB_SHELL_CSS
    if "body.cl-theme-v4" in shell:
        shell += "\n/* review lobby uses rb-layout vars in rb-lobby.css */\n"
    (assets / "rb-shell.css").write_text(shell, encoding="utf-8")
    (assets / "rb-lobby.css").write_text(RB_LOBBY_CSS.strip() + "\n", encoding="utf-8")
    (assets / "rb-compliance.css").write_text(RB_COMPLIANCE_CSS.strip() + "\n", encoding="utf-8")
    (assets / "rb-site.js").write_text(RB_SITE_JS.strip() + "\n", encoding="utf-8")
    for old in ("rv-shell.css", "rv-lobby.css", "rv-compliance.css", "rv-site.js", "r2-shell.css", "r2-page.css", "r2-compliance.css", "r2-site.js"):
        p = assets / old
        if p.is_file():
            p.unlink()




def write_robots_sitemap() -> None:
    kw_path = SITE / "_output" / "keywords.json"
    data = json.loads(kw_path.read_text(encoding="utf-8"))
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
        pri = "1.0" if loc.rstrip("/").endswith("cazilla.cfd") or loc.endswith("index.html") else "0.85"
        if loc.endswith("/index.html"):
            pri = "1.0"
        elif loc.endswith(".html"):
            pri = "0.85"
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
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(technical_page(rel, title, desc, h1, sub, slug), encoding="utf-8")
        print("Wrote", rel)
    write_htaccess()
    write_robots_sitemap()
    print("Bootstrap complete ->", SITE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
