#!/usr/bin/env python3
"""Bootstrap: review lobby site (en-IE) — landing template from fr-be wireframe + distinct rb-theme-ie3."""
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

SITE: Path = ROOT / "sites" / "cazilla-review3-en-ie"
ORIGIN = "https://cazilla.today"
MAIN = "https://cazilla.casino"
SITE_SLUG = "cazilla-review3-en-ie"
SITE_NAME = "Cazilla Ireland"
HTML_LANG = "en-IE"
MIN_AGE = 18
LC: LocaleContext | None = None
STUB = "Placeholder editorial copy. A2 will replace this with optimized content."
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
    "casino-games": (
        "slots-showcase.png",
        "fruit-classic-slot.png",
        "money-train-4-thumbnail.png",
    ),
    "bonuses": (
        "bonus-promo-artwork.webp",
        "baccarat-bonus-terms.webp",
        "crazy-time-bonus.jpg",
    ),
    "live-roulette": (
        "live-tables.jpg",
        "baccarat-live-table.webp",
        "blackjack-green-table.jpg",
    ),
    "about": (
        "casino-feature-visual.png",
        "og-logo.svg",
        "blackjack-green-table.jpg",
    ),
}

LANDING_IMG_ALT: dict[str, tuple[str, str, str]] = {
    "home": (
        "Cazilla — mobile online casino Ireland",
        "Slots and games catalogue",
        "Live casino tables",
    ),
    "casino-games": (
        "Online casino games lobby",
        "Classic slot preview",
        "Featured jackpot slot",
    ),
    "bonuses": (
        "Casino bonuses and free spins",
        "Bonus terms snapshot",
        "Live game show promo",
    ),
    "live-roulette": (
        "Live roulette tables",
        "Live baccarat stream",
        "Live blackjack table",
    ),
    "about": (
        "Cazilla Ireland editorial hub",
        "Cazilla logo",
        "Table games overview",
    ),
}


def init_site() -> None:
    global SITE, ORIGIN, MAIN, SITE_SLUG, SITE_NAME, HTML_LANG, LC, STUB
    env = load_dotenv_file(ENV_PATH)
    rel = (env.get("SITE_DIR") or "sites/cazilla-review3-en-ie").strip().lstrip("/")
    SITE = ROOT / rel
    SITE_SLUG = Path(rel).name
    ORIGIN = (env.get("SITE_URL") or "https://cazilla.today").strip().rstrip("/")
    MAIN = (env.get("MAIN_CASINO_URL") or "https://cazilla.casino").strip().rstrip("/")
    LC = locale_context_from_env(env, strict_keywords_match=False)
    HTML_LANG = LC.locale.replace("_", "-") if "_" in LC.locale else LC.locale
    global MIN_AGE
    MIN_AGE = 21 if LC.geo.upper() == "BE" else 18
    SITE_NAME = "Cazilla Ireland"
    STUB = f"Placeholder editorial copy. A2 will replace this with optimized content for {LC.audience_phrase}."
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
        desc = f"{menu} — {SITE_NAME}, {LC.region_name if LC else 'Belgium'}."
        sub = f"{menu} — information for {LC.audience_phrase if LC else 'readers in Belgium'}."
        TECH_SPECS.append((slug, rel, title, desc, html.escape(menu), html.escape(sub)))
        FOOTER_LEGAL.append((rel, html.escape(menu)))


def _asset_prefix(rel: str) -> str:
    return "../" * rel.count("/")


def compliance_block(rel: str = "index.html") -> str:
    ap = _asset_prefix(rel)
    ck = f"{ap}cookie-policy/index.html"
    region = LC.region_name if LC else "Ireland"
    return f"""<div class="complianceOverlay" id="ageGate" role="dialog" aria-modal="true" aria-labelledby="ageTitle">
  <div class="complianceDialog">
    <h2 id="ageTitle">Confirm you are {MIN_AGE} or older</h2>
    <p>This site covers regulated gambling for readers in {html.escape(region)}. You must be at least {MIN_AGE} to continue.</p>
    <div class="complianceActions">
      <button type="button" class="btn" id="ageUnder">I am under {MIN_AGE}</button>
      <button type="button" class="btn primary" id="ageOk">I am {MIN_AGE} or older</button>
    </div>
  </div>
</div>
<div class="complianceOverlay" id="cookieGate" hidden aria-hidden="true" role="dialog" aria-modal="true" aria-labelledby="cookieTitle">
  <div class="complianceDialog">
    <h2 id="cookieTitle">Cookie preferences</h2>
    <p>We use cookies to remember age verification. See our <a class="inTextLink" href="{html.escape(ck)}">cookie policy</a>.</p>
    <div class="complianceActions">
      <button type="button" class="btn" id="cookieReject">Essential only</button>
      <button type="button" class="btn primary" id="cookieAccept">Accept</button>
    </div>
  </div>
</div>"""


def _fix_compliance(s: str) -> str:
    return s.replace("<motion class", "<div class").replace("</motion>", "</motion>").replace(
        'aria-labelledby="cookieTitle">\n  <div', 'aria-labelledby="cookieTitle">\n  <div'
    )


def head_block(rel: str, title: str, desc: str) -> str:
    ap = _asset_prefix(rel)
    canonical = f"{ORIGIN}/" if rel == "index.html" else f"{ORIGIN}/{rel}"
    og_locale = HTML_LANG.replace("-", "_")
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
<meta property="og:locale" content="{html.escape(og_locale)}" />
<meta property="og:image" content="{ORIGIN}/assets/pictures/og-logo.svg" />
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"WebSite","name":"{html.escape(SITE_NAME)}","url":"{html.escape(ORIGIN)}/"}}</script>
<link rel="stylesheet" href="{ap}assets/rb-shell.css" />
<link rel="stylesheet" href="{ap}assets/rb-lobby.css" />
<link rel="stylesheet" href="{ap}assets/rb-compliance.css" />"""


def site_header(current_rel: str | None = None) -> str:
    cur_norm = (current_rel or "").strip().lstrip("/") or None
    ap = _asset_prefix(cur_norm or "index.html")
    nav_lines = []
    for _pid, href, lab in CONTENT_PAGES:
        cur = ' aria-current="page"' if cur_norm == href else ""
        nav_lines.append(f'      <a href="{ap}{href}"{cur}>{lab}</a>')
    nav = "\n".join(nav_lines)
    m = html.escape(MAIN)
    return f"""<header class="rb-header">
  <div class="rb-headerInner">
    <a class="rb-brand" href="{ap}index.html" aria-label="Home {html.escape(SITE_NAME)}">
      <img src="{ap}assets/pictures/og-logo.svg" alt="" width="36" height="36" decoding="async" />
      <span class="rb-brandName">{html.escape(SITE_NAME.upper())}</span>
    </a>
    <nav class="rb-nav" id="mainNav" aria-label="Main navigation">
{nav}
    </nav>
    <div class="rb-headerActions">
      <button class="btn icon rb-navToggle" id="navToggle" type="button" aria-label="Open menu" aria-expanded="false" aria-controls="mainNav">≡</button>
      <a class="btn" href="{m}" rel="noopener noreferrer" target="_blank">Official site</a>
      <a class="btn primary" href="{m}" rel="noopener noreferrer" target="_blank">Play now</a>
    </div>
  </div>
</header>"""


def site_footer(current_rel: str | None = None) -> str:
    ap = _asset_prefix((current_rel or "index.html").strip().lstrip("/"))
    legal = []
    for href, lab in FOOTER_LEGAL:
        cur = ' aria-current="page"' if current_rel == href else ""
        legal.append(f'      <a href="{ap}{href}"{cur}>{lab}</a>')
    nav_content = "\n".join(
        f'      <a href="{ap}{href}"{" aria-current=\"page\"" if current_rel == href else ""}>{lab}</a>'
        for _pid, href, lab in CONTENT_PAGES
        if href != "index.html"
    )
    m = html.escape(MAIN)
    return f"""<footer class="rb-footer" id="footer">
  <nav class="rb-footerNav" aria-label="Site pages">
    <a href="{ap}index.html">Home</a>
{nav_content}
  </nav>
  <nav class="rb-footerLegal" aria-label="Legal pages">
{chr(10).join(legal)}
  </nav>
  <div class="rb-footerBlock">
    <h3>Providers</h3>
    <div class="rb-badges">
      <span class="rb-badge">Pragmatic Play</span><span class="rb-badge">NetEnt</span><span class="rb-badge">Evolution</span>
      <span class="rb-badge">Play'n GO</span><span class="rb-badge">Habanero</span>
    </div>
  </div>
  <div class="rb-footerBlock">
    <h3>Payments</h3>
    <div class="rb-badges">
      <span class="rb-badge">Visa</span><span class="rb-badge">Mastercard</span><span class="rb-badge">PayPal</span>
      <span class="rb-badge">Apple Pay</span><span class="rb-badge">Skrill</span>
    </div>
  </div>
  <p class="rb-license"><span class="rb-age">{MIN_AGE}+</span> Curaçao eGaming licence — check details on the <a href="{m}" rel="noopener noreferrer" target="_blank">official site</a>.</p>
  <p class="rb-copy">© <span id="year">2026</span> {html.escape(SITE_NAME)}. Editorial review hub — play links go to the operator.</p>
</footer>"""


def _landing_cta() -> str:
    m = html.escape(MAIN)
    return (
        f'<p class="rb-ctaBar"><a class="btn primary" href="{m}" rel="noopener noreferrer" '
        f'target="_blank">Play at Cazilla</a></p>'
    )


def _landing_figure(page_id: str, index: int, asset_prefix: str = "") -> str:
    imgs = LANDING_IMAGES.get(page_id, LANDING_IMAGES["home"])
    alts = LANDING_IMG_ALT.get(page_id, LANDING_IMG_ALT["home"])
    i = min(max(index, 0), 2)
    src = html.escape(imgs[i])
    alt = html.escape(alts[i])
    return (
        f'<figure class="rb-landingMedia"><img src="{asset_prefix}assets/pictures/{src}" alt="{alt}" '
        f'width="720" loading="lazy" decoding="async" /></figure>'
    )


def landing_stub(page_id: str) -> str:
    """Stub inside article[data-a2-field=main_seo_html]; A2 replaces the whole article body."""
    return f"""<p>{html.escape(STUB)}</p>
{_landing_cta()}
{_landing_figure(page_id, 0)}
<h2>Key points</h2>
<p>{html.escape(STUB)}</p>
<ul>
  <li>Editorial placeholder point one</li>
  <li>Editorial placeholder point two</li>
  <li>Editorial placeholder point three</li>
</ul>
{_landing_cta()}
{_landing_figure(page_id, 1)}
<h2>Recommended steps</h2>
<p>{html.escape(STUB)}</p>
<ol>
  <li>Placeholder step one</li>
  <li>Placeholder step two</li>
  <li>Placeholder step three</li>
</ol>
{_landing_cta()}
<h2>Quick comparison</h2>
<p>{html.escape(STUB)}</p>
<table class="rb-dataTable">
  <thead><tr><th>Criterion</th><th>Cazilla</th><th>Check</th></tr></thead>
  <tbody>
    <tr><td>Bonus</td><td>On official site</td><td>Wagering terms</td></tr>
    <tr><td>Payments</td><td>Cards &amp; e-wallets</td><td>Withdrawal times</td></tr>
    <tr><td>Mobile</td><td>Browser</td><td>Stability</td></tr>
  </tbody>
</table>
{_landing_cta()}
{_landing_figure(page_id, 2)}
<section class="rb-faq" aria-labelledby="rb-faq-title">
  <h2 id="rb-faq-title">Frequently asked questions</h2>
  <details open><summary>Placeholder question 1?</summary><p>{html.escape(STUB)}</p></details>
  <details open><summary>Placeholder question 2?</summary><p>{html.escape(STUB)}</p></details>
  <details open><summary>Placeholder question 3?</summary><p>{html.escape(STUB)}</p></details>
  <details open><summary>Placeholder question 4?</summary><p>{html.escape(STUB)}</p></details>
  <details open><summary>Placeholder question 5?</summary><p>{html.escape(STUB)}</p></details>
</section>"""


def landing_body(page_id: str) -> str:
    return f"""
    <article class="rb-landing" data-a2-field="main_seo_html">
{landing_stub(page_id)}
    </article>"""


def content_page(page_id: str, rel: str, menu_label: str) -> str:
    title = f"{menu_label} | {SITE_NAME}"
    desc = f"{menu_label} — editorial Cazilla review for readers in Ireland ({MIN_AGE}+)."
    h1 = menu_label.replace("&amp;", "&")
    landing = landing_body(page_id)
    return f"""<!doctype html>
<html lang="{html.escape(HTML_LANG)}" data-site-kind="review-lobby" data-min-gambling-age="{MIN_AGE}">
  <head>
{head_block(rel, title, desc)}
  </head>
  <body class="rb-layout rb-theme-ie3">
{compliance_block(rel)}
<div id="siteContent" class="rb-app">
{site_header(rel)}
  <main class="rb-main" id="top">
    <h1 class="rb-pageTitle" data-a2-field="page_h1">{html.escape(h1)}</h1>
{landing}
    <p class="rb-fineprint" data-a2-field="footer_note">{MIN_AGE}+ | Play responsibly | Ireland</p>
  </main>
{site_footer(rel)}
</div>
<script src="{_asset_prefix(rel)}assets/rb-site.js" defer></script>
  </body>
</html>"""


def tech_policy_stub(slug: str) -> str:
    return (
        '<article class="rb-policyArticle" data-a2-field="main_seo_html">'
        f"<p>{html.escape(STUB)}</p>"
        '<p><a href="../index.html">Back to home</a></p>'
        "</article>"
    )


def technical_page(rel: str, title: str, desc: str, h1: str, hero_sub: str, slug: str) -> str:
    body = tech_policy_stub(slug)
    return f"""<!doctype html>
<html lang="{html.escape(HTML_LANG)}" data-site-kind="review-lobby" data-min-gambling-age="{MIN_AGE}">
  <head>
{head_block(rel, title, desc)}
  </head>
  <body class="rb-layout rb-layout--legal rb-theme-ie3">
{compliance_block(rel)}
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
<script src="{_asset_prefix(rel)}assets/rb-site.js" defer></script>
  </body>
</html>"""


RB_SHELL_CSS = (CLONE_ASSETS / "cl-shell.css").read_text(encoding="utf-8") if (CLONE_ASSETS / "cl-shell.css").is_file() else ""

RB_LOBBY_CSS = """
/* Review lobby en-IE — teal + rose (rb-theme-ie3) (distinct from fr gold, nl amber/emerald) */
body.rb-theme-ie3 {
  --rb-accent: #2dd4bf;
  --rb-accent2: #fb7185;
  --rb-bg: #071018;
  --rb-panel: #0f1c28;
  --rb-line: rgba(45, 212, 191, 0.22);
  --rb-text: #e8f4f8;
  --rb-muted: #a1a1aa;
}

.rb-layout {
  margin: 0;
  background: var(--rb-bg);
  background-image:
    linear-gradient(160deg, rgba(45, 212, 191, 0.07) 0%, transparent 42%),
    linear-gradient(220deg, rgba(217, 119, 6, 0.06) 0%, transparent 38%);
  color: var(--rb-text);
  font-family: "IBM Plex Sans", "Segoe UI", system-ui, sans-serif;
}

.rb-app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  max-width: 940px;
  margin: 0 auto;
  padding: 0 14px;
}

.rb-header {
  margin-top: 14px;
  padding: 0;
  background: transparent;
  border: none;
  position: relative;
  z-index: 30;
}

.rb-headerInner {
  display: flex;
  align-items: stretch;
  gap: 0;
  flex-wrap: wrap;
  background: var(--rb-panel);
  border-radius: 16px;
  border: 1px solid var(--rb-line);
  overflow: hidden;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4);
}

.rb-brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: inherit;
  font-weight: 800;
  font-size: 0.82rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  flex-shrink: 0;
  padding: 14px 16px;
  background: linear-gradient(135deg, rgba(45, 212, 191, 0.2), rgba(217, 119, 6, 0.12));
  border-right: 1px solid var(--rb-line);
}

.rb-brand img {
  border-radius: 6px;
  box-shadow: 0 0 0 2px var(--rb-accent2);
}

.rb-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  align-items: center;
  margin-left: auto;
  padding: 10px 12px;
}

.rb-nav a {
  color: var(--rb-muted);
  text-decoration: none;
  font-size: 13px;
  font-weight: 500;
  padding: 6px 11px;
  border-radius: 6px;
  border: 1px solid transparent;
}

.rb-nav a:hover {
  color: var(--rb-text);
  border-color: var(--rb-line);
}

.rb-nav a[aria-current="page"] {
  font-weight: 700;
  color: #1a1028;
  background: var(--rb-accent);
  border-color: transparent;
}

.rb-headerActions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-shrink: 0;
  padding: 10px 12px;
  border-left: 1px solid var(--rb-line);
}

.btn.icon {
  display: none;
  min-width: 40px;
  padding: 8px 12px;
  font-size: 18px;
  line-height: 1;
}

@media (max-width: 720px) {
  .btn.icon { display: inline-flex; }
  .rb-headerInner { position: relative; flex-direction: column; align-items: stretch; }
  .rb-brand { border-right: none; border-bottom: 1px solid var(--rb-line); }
  .rb-nav {
    display: none;
    margin: 0;
    padding: 12px;
    flex-direction: column;
    align-items: stretch;
    border-top: 1px solid var(--rb-line);
  }
  .rb-nav[data-open="true"] { display: flex; }
  .rb-headerActions {
    border-left: none;
    border-top: 1px solid var(--rb-line);
    justify-content: flex-end;
  }
  .rb-headerActions .btn:not(.icon):not(.primary) { display: none; }
}

.rb-main { flex: 1; padding: 22px 4px 40px; }

.rb-pageTitle {
  margin: 0 0 18px;
  font-size: clamp(1.45rem, 3.5vw, 1.9rem);
  font-weight: 800;
  letter-spacing: -0.03em;
  background: linear-gradient(90deg, #e8f4f8 0%, #5eead4 55%, #fda4af 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 9px 16px;
  border-radius: 8px;
  border: 1px solid var(--rb-line);
  background: #252030;
  color: inherit;
  text-decoration: none;
  font-size: 14px;
  cursor: pointer;
  font-family: inherit;
}

.btn.primary {
  background: linear-gradient(135deg, var(--rb-accent2), #e11d48);
  border-color: transparent;
  color: #fff;
  font-weight: 700;
}

/* Landing */
.rb-landing {
  margin-top: 6px;
  padding: 24px 22px 30px;
  border-radius: 18px;
  border: 1px solid var(--rb-line);
  background: var(--rb-panel);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.rb-landing h2 {
  margin: 1.5rem 0 0.65rem;
  font-size: 1.1rem;
  font-weight: 700;
  color: #ccfbf1;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-size: 0.82rem;
}

.rb-landing p,
.rb-landing li { line-height: 1.75; color: #d4d4d8; }

.rb-landing ul,
.rb-landing ol { margin: 0.5rem 0 1rem; padding-left: 1.3rem; }

.rb-ctaBar {
  display: flex;
  justify-content: center;
  align-items: center;
  margin: 1.4rem 0;
}

.rb-ctaBar .btn.primary {
  padding: 12px 30px;
  border-radius: 8px;
  box-shadow: 0 6px 24px rgba(217, 119, 6, 0.35);
}

.rb-landingMedia {
  margin: 1.2rem 0;
  border-radius: 14px;
  border: 1px solid var(--rb-line);
  background: rgba(45, 212, 191, 0.06);
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 12px 16px;
  position: relative;
}

.rb-landingMedia::before {
  content: "";
  position: absolute;
  inset: 0;
  border-radius: inherit;
  border-top: 3px solid var(--rb-accent);
  pointer-events: none;
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
}

@media (max-width: 640px) {
  .rb-landingMedia { padding: 10px 12px; }
  .rb-landingMedia img { max-width: 100%; max-height: 180px; }
}

.rb-dataTable {
  width: 100%;
  border-collapse: collapse;
  margin: 0.75rem 0 1rem;
  font-size: 14px;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid var(--rb-line);
}

.rb-dataTable th,
.rb-dataTable td {
  border: 1px solid var(--rb-line);
  padding: 10px 12px;
  text-align: left;
}

.rb-dataTable th {
  background: rgba(45, 212, 191, 0.18);
  color: #ede9fe;
}

.rb-faq {
  margin-top: 1.6rem;
  padding-top: 1rem;
  border-top: 1px dashed var(--rb-line);
}

.rb-faq details {
  margin-bottom: 10px;
  border-radius: 10px;
  padding: 12px 14px;
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid var(--rb-line);
}

.rb-faq details[open] { padding-bottom: 14px; }

.rb-faq summary {
  cursor: default;
  font-weight: 600;
  color: #fda4af;
  padding: 0 0 8px;
  list-style: none;
  pointer-events: none;
}

.rb-faq summary::-webkit-details-marker { display: none; }
.rb-faq summary::marker { content: ""; }
.rb-faq details > p { margin: 0; padding: 0; }

.rb-fineprint {
  font-size: 13px;
  color: var(--rb-muted);
  margin-top: 22px;
  text-align: center;
}

.rb-footer {
  padding: 26px 16px 22px;
  margin: 0 -14px;
  background: #08060c;
  margin-top: auto;
  border-top: 3px solid transparent;
  border-image: linear-gradient(90deg, var(--rb-accent), var(--rb-accent2)) 1;
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
  padding: 5px 10px;
  border-radius: 6px;
  font-size: 12px;
  background: #252030;
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
  background: var(--rb-accent2);
  color: #fff;
}

.rb-copy { font-size: 12px; color: var(--rb-muted); margin: 12px 0 0; }

.rb-legalHero {
  margin-bottom: 18px;
  padding: 16px 18px;
  border-radius: 12px;
  background: rgba(45, 212, 191, 0.1);
  border: 1px solid var(--rb-line);
}

.rb-legalHero h1 { margin: 0 0 8px; }

.rb-lead { color: var(--rb-muted); line-height: 1.65; margin: 0; }

.rb-policyCard { margin-bottom: 20px; }

.rb-policyArticle p { line-height: 1.75; color: #d4d4d8; }

body.rb-layout--legal .rb-main { max-width: 820px; }

.policyCta { text-align: center; margin: 22px 0 8px; }

.policyCta a {
  display: inline-flex;
  padding: 11px 24px;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--rb-accent2), #e11d48);
  color: #fff !important;
  font-weight: 700;
  text-decoration: none;
}

.rb-seoProse {
  margin-top: 24px;
  padding: 18px;
  border-radius: 12px;
  border: 1px solid var(--rb-line);
  background: rgba(45, 212, 191, 0.06);
}

.rb-seoProse p,
.rb-seoProse li { line-height: 1.7; color: #d4d4d8; }
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
  background: rgba(7, 16, 24, 0.9);
  backdrop-filter: blur(8px);
}
.complianceOverlay[hidden] { display: none !important; }
.complianceDialog {
  width: min(420px, 100%);
  border-radius: 18px;
  border: 1px solid rgba(45, 212, 191, 0.45);
  border-bottom: 4px solid #fb7185;
  background: #0f1c28;
  color: #e8f4f8;
  padding: 24px;
  box-shadow: 0 28px 70px rgba(0, 0, 0, 0.55);
}
.complianceDialog h2 { margin: 0 0 10px; font-size: 18px; color: #ccfbf1; }
.complianceDialog p { margin: 0 0 14px; color: #d4d4d8; font-size: 14px; line-height: 1.55; }
.complianceActions { display: flex; flex-wrap: wrap; gap: 10px; }
.complianceDialog .btn.primary { background: linear-gradient(135deg, #fb7185, #e11d48); color: #fff; }
.inTextLink { color: #5eead4; }
html.complianceNoScroll,
html.complianceNoScroll body { overflow: hidden; height: 100%; }
"""

RB_SITE_JS = """
(function () {
  "use strict";
  var AGE = "cazilla_review3_en_ie_age_ok";
  var COOKIE = "cazilla_review3_en_ie_cookie";
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
