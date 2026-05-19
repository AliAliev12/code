#!/usr/bin/env python3
"""Generator: Trustpilot-style Cazilla review sites (r2 skin).

Reads SITE_DIR, SITE_URL, MAIN_CASINO_URL, TARGET_* from repo .env.
Page list and paths come from sites/<slug>/_output/keywords.json (v2).

Supports:
  - Content pages: flat *.html (from pages[])
  - Legal pages: folder slug/index.html OR flat slug.html (from technical_pages[])
"""
from __future__ import annotations

import html
import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT / ".env"
_AGENTS = ROOT / "agents"
if str(_AGENTS) not in sys.path:
    sys.path.insert(0, str(_AGENTS))

from _lib.locale_context import (  # noqa: E402
    LocaleContext,
    age_gate_body,
    legal_subtitle_fallback,
    locale_context_from_env,
)
from _lib.repo_env import load_dotenv_file  # noqa: E402

REVIEW_ASSET_SRC = ROOT / "sites" / "cazilla-review2-en-ie" / "assets"
PICTURE_SRC = ROOT / "sites" / "cazilla-offerwall2-en-ie" / "assets" / "pictures"

SITE: Path = ROOT / "sites" / "default"
ORIGIN: str = ""
SITE_SLUG: str = ""
MAIN: str = ""
LC: LocaleContext | None = None
SITE_NAME: str = "Cazilla Review"
HTML_LANG: str = ""
HREFLANG: str = ""
NAV: List[Tuple[str, str]] = []
CONTENT_PAGES: List["ContentPageSpec"] = []
TECH_PAGES: List["TechPageSpec"] = []


@dataclass
class ContentPageSpec:
    page_id: str
    rel_path: str
    menu_label: str
    main_kw: str


@dataclass
class TechPageSpec:
    page_id: str
    rel_path: str
    menu_label: str
    slug: str
    depth: int
    folder_mode: bool


def _norm_rel(path: str) -> str:
    rel = str(path or "").strip().lstrip("/")
    return rel or "index.html"


def _parse_tech_path(path: str) -> Tuple[str, str, int, bool]:
    rel = _norm_rel(path)
    if rel.endswith("/index.html"):
        folder = rel[: -len("/index.html")].rstrip("/")
        slug = folder.split("/")[-1] if folder else "legal"
        return slug, rel, 1, True
    if rel.endswith(".html"):
        slug = Path(rel).stem
        return slug, rel, 0, False
    raise ValueError(f"Unsupported technical path: {path!r}")


def _legal_nav_href(rel_path: str, *, folder_mode: bool) -> str:
    rel = _norm_rel(rel_path)
    if folder_mode:
        folder = rel[: -len("/index.html")].rstrip("/")
        return f"{folder}/"
    return rel


def site_brand_name(slug: str) -> str:
    low = slug.lower()
    if "review2" in low or "insight" in low:
        return "Cazilla Insight"
    if "review3" in low or "voices" in low:
        return "Cazilla Player Voices"
    return "Cazilla Review"


def cta_labels(lc: LocaleContext) -> Tuple[str, str]:
    if lc.lang == "fr":
        return "Site officiel Cazilla", "Jouer sur Cazilla"
    if lc.lang == "nl":
        return "Officiële Cazilla-site", "Speel bij Cazilla"
    return "Official Cazilla", "Play at Cazilla"


def content_stub(lc: LocaleContext) -> str:
    if lc.lang == "fr":
        return (
            f"Texte éditorial provisoire. A2 remplacera ce bloc par un avis Cazilla pour {lc.audience_phrase}."
        )
    return f"Editorial placeholder. A2 will replace this block with review copy for {lc.audience_phrase}."


def section_headings(lc: LocaleContext, page_id: str, menu_label: str) -> Tuple[str, str, str, str, str, str]:
    if lc.lang == "fr":
        return (
            "Bonus et offres vus par des joueurs",
            "Jeux et paiements au centre de l'avis",
            "Comment nous restons indépendants",
            "Offres de bienvenue en contexte",
            "Catalogue et expérience mobile",
            "Méthode éditoriale",
        )
    themes = {
        "slots": (
            "Slot libraries we compare",
            "Mobile play and RTP context",
            "What fairness signals mean",
            "Studios and catalogue depth",
            "Volatility in plain language",
            "How we test lobby UX",
        ),
        "bonus": (
            "Welcome bonus structures",
            "Bonus offers we compare",
            "Promo codes without hype",
            "Wagering and game weighting",
            "Reloads and loyalty angles",
            "Reading tables like a reviewer",
        ),
        "about": (
            "Signals we track for players",
            "Stories behind our ratings",
            "Editorial standards on this hub",
            "Licensing checks we repeat",
            "Support tests we run",
            f"How {lc.region_name} context shapes our pages",
        ),
        "casino-games": (
            "Game libraries we compare",
            "Table and live titles",
            "RNG vs live dealer notes",
            "Studios and depth",
            "Mobile expectations",
            "Fair lobby signals",
        ),
        "casino-deposit": (
            "No-deposit paths explained",
            "Real-money play safely",
            "Low-deposit fine print",
            "Risk-free trials and caps",
            "Bankroll planning",
            "When a small deposit helps",
        ),
    }
    default = (
        "Bonuses through a review lens",
        "Games and payments readers ask about",
        "How this page stays independent",
        "Welcome packages in context",
        "Live tables and RNG libraries",
        "Editorial standards we follow",
    )
    return themes.get(page_id, default)


def landing_meta(page: ContentPageSpec, lc: LocaleContext) -> Tuple[str, str, str]:
    kw = page.main_kw
    cap = kw[0].upper() + kw[1:] if kw else page.menu_label
    if lc.lang == "fr":
        title = f"{cap} | Avis Cazilla {lc.region_name}."
        desc = f"{cap} — avis éditorial indépendant pour {lc.audience_phrase}."
        h1 = f"{cap} — avis Cazilla"
    else:
        title = f"{cap} | Cazilla review {lc.region_name}."
        desc = f"{cap} — independent Cazilla review for {lc.audience_phrase}."
        h1 = f"{cap} — Cazilla review"
    return title[:70], desc[:160], h1[:70]


def init_site(env: dict[str, str] | None = None) -> None:
    global SITE, ORIGIN, SITE_SLUG, MAIN, LC, SITE_NAME, HTML_LANG, HREFLANG
    global NAV, CONTENT_PAGES, TECH_PAGES

    e = env if env is not None else load_dotenv_file(ENV_PATH)
    rel = (e.get("SITE_DIR") or "").strip().lstrip("/")
    if not rel:
        raise SystemExit("Missing SITE_DIR in .env")
    SITE = ROOT / rel
    SITE_SLUG = SITE.name
    ORIGIN = (e.get("SITE_URL") or "").strip().rstrip("/")
    MAIN = (e.get("MAIN_CASINO_URL") or "https://cazilla.casino").strip().rstrip("/")
    if not ORIGIN:
        raise SystemExit("Missing SITE_URL in .env")

    kw_path = SITE / "_output" / "keywords.json"
    if not kw_path.is_file():
        raise SystemExit(f"Missing keywords bundle: {kw_path}")
    data = json.loads(kw_path.read_text(encoding="utf-8"))
    kw_locale = str(data.get("locale") or "").strip() or None
    LC = locale_context_from_env(e, keywords_locale=kw_locale)
    HTML_LANG = LC.locale.replace("_", "-")
    HREFLANG = (e.get("QA_HREFLANG_PRIMARY") or LC.locale).strip()
    SITE_NAME = (e.get("REVIEW_SITE_NAME") or "").strip() or site_brand_name(SITE_SLUG)

    CONTENT_PAGES = []
    for p in data.get("pages") or []:
        if not isinstance(p, dict):
            continue
        pid = str(p.get("id") or "").strip()
        rel = _norm_rel(str(p.get("path") or ""))
        label = str(p.get("menu_label") or pid.replace("-", " ").title()).strip()
        kws = p.get("keywords") or []
        main_kw = ""
        if isinstance(kws, list) and kws and isinstance(kws[0], dict):
            main_kw = str(kws[0].get("keyword") or "").strip()
        if pid and rel:
            CONTENT_PAGES.append(ContentPageSpec(pid, rel, label, main_kw))

    TECH_PAGES = []
    for p in data.get("technical_pages") or []:
        if not isinstance(p, dict):
            continue
        pid = str(p.get("id") or "").strip()
        raw_path = str(p.get("path") or "")
        label = str(p.get("menu_label") or pid.replace("-", " ").title()).strip()
        if not pid or not raw_path:
            continue
        slug, rel, depth, folder_mode = _parse_tech_path(raw_path)
        TECH_PAGES.append(TechPageSpec(pid, rel, label, slug, depth, folder_mode))

    if not CONTENT_PAGES:
        raise SystemExit("keywords.json: pages[] is empty")
    if not TECH_PAGES:
        raise SystemExit("keywords.json: technical_pages[] is empty")

    NAV = [(p.rel_path, p.menu_label) for p in CONTENT_PAGES]


def nav_html(current: str | None, *, depth: int) -> str:
    prefix = "../" * depth
    lines = []
    for href, label in NAV:
        cur = ' aria-current="page"' if current is not None and href == current else ""
        lines.append(f'            <a href="{prefix}{html.escape(href)}"{cur}>{html.escape(label)}</a>')
    return "\n".join(lines)
def actions_html(*, depth: int) -> str:
    assert LC is not None
    off, play = cta_labels(LC)
    return (
        '          <div class="actions">\n'
        '            <button class="btn icon hamburger" id="hamburger" type="button" aria-label="Open menu">≡</button>\n'
        f'            <a class="btn" href="{html.escape(MAIN)}" rel="noopener noreferrer" target="_blank">{html.escape(off)}</a>\n'
        f'            <a class="btn primary" href="{html.escape(MAIN)}" rel="noopener noreferrer" target="_blank">{html.escape(play)}</a>\n'
        "          </div>"
    )


def cookie_policy_href(*, depth: int) -> str:
    prefix = "../" * depth
    for t in TECH_PAGES:
        if t.slug == "cookie-policy":
            return prefix + _legal_nav_href(t.rel_path, folder_mode=t.folder_mode)
    return f"{prefix}cookie-policy.html"


def compliance_block(*, depth: int) -> str:
    assert LC is not None
    ck = html.escape(cookie_policy_href(depth=depth))
    age_p = html.escape(age_gate_body(LC))
    if LC.lang == "fr":
        cookie_intro = "Nous utilisons des cookies pour mémoriser la vérification d'âge. Voir"
        cookie_label = "politique de cookies"
    else:
        cookie_intro = "We use cookies to remember your age check. See"
        cookie_label = "cookie policy"
    return f"""<div class="complianceOverlay" id="ageGate" role="dialog" aria-modal="true" aria-labelledby="ageTitle">
  <div class="complianceDialog">
    <h2 id="ageTitle">Confirm you are 18 or over</h2>
    <p>{age_p}</p>
    <div class="complianceActions">
      <button type="button" class="btn" id="ageUnder">I am under 18</button>
      <button type="button" class="btn primary" id="ageOk">I am 18 or over</button>
    </div>
  </div>
</div>
<div class="complianceOverlay" id="cookieGate" hidden aria-hidden="true" role="dialog" aria-modal="true" aria-labelledby="cookieTitle">
  <div class="complianceDialog">
    <h2 id="cookieTitle">Cookie preferences</h2>
    <p>{html.escape(cookie_intro)} <a href="{ck}">{html.escape(cookie_label)}</a>.</p>
    <div class="complianceActions">
      <button type="button" class="btn" id="cookieReject">Essential only</button>
      <button type="button" class="btn primary" id="cookieAccept">Accept</button>
    </div>
  </div>
</div>"""


def footer_legal(*, depth: int) -> str:
    prefix = "../" * depth
    parts = []
    for t in TECH_PAGES:
        href = prefix + _legal_nav_href(t.rel_path, folder_mode=t.folder_mode)
        parts.append(f'            <a href="{html.escape(href)}">{html.escape(t.menu_label)}</a>')
    return (
        '          <nav class="footerLegal" aria-label="Legal pages">\n'
        + "\n".join(parts)
        + "\n          </nav>"
    )


def canonical_url(rel: str) -> str:
    rel = _norm_rel(rel)
    if rel == "index.html":
        return f"{ORIGIN}/"
    if rel.endswith("/index.html") and rel.count("/") >= 1:
        folder = rel[: -len("/index.html")].rstrip("/")
        return f"{ORIGIN}/{folder}/"
    return f"{ORIGIN}/{rel}"


def head_block(rel: str, title: str, description: str, *, depth: int) -> str:
    canonical = canonical_url(rel)
    css_p = "../" * depth + "assets/"
    og_loc = HTML_LANG.replace("-", "_")
    return f"""<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}" />
<meta name="robots" content="index, follow" />
<link rel="canonical" href="{html.escape(canonical)}" />
<link rel="alternate" hreflang="{html.escape(HREFLANG)}" href="{html.escape(canonical)}" />
<link rel="alternate" hreflang="x-default" href="{html.escape(canonical)}" />
<meta property="og:title" content="{html.escape(title)}" />
<meta property="og:description" content="{html.escape(description)}" />
<meta property="og:image" content="{ORIGIN}/assets/pictures/og-logo.svg" />
<meta property="og:url" content="{html.escape(canonical)}" />
<meta property="og:type" content="website" />
<meta property="og:locale" content="{html.escape(og_loc)}" />
<meta name="twitter:card" content="summary_large_image" />
<script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "WebSite",
    "name": {json.dumps(SITE_NAME)},
    "url": {json.dumps(ORIGIN + "/")}
  }}
</script>
<link rel="stylesheet" href="{css_p}r2-shell.css" />
<link rel="stylesheet" href="{css_p}r2-page.css" />
<link rel="stylesheet" href="{css_p}r2-compliance.css" />"""


def trust_ribbon(*, legal: bool = False) -> str:
    assert LC is not None
    if legal:
        if LC.lang == "fr":
            inner = f"<strong>Avis Cazilla indépendant</strong> — informations juridiques pour {LC.audience_phrase}."
        else:
            inner = f"<strong>Independent Cazilla review</strong> — legal information for {LC.audience_phrase}."
    elif LC.lang == "fr":
        inner = (
            f"<strong>Avis Cazilla indépendant</strong> pour {LC.region_name} ({LC.locale}). "
            "Hub éditorial — nous n'exploitons pas de casino."
        )
    else:
        inner = (
            f"<strong>Independent Cazilla review</strong> for {LC.region_name} ({LC.locale}). "
            "Editorial player feedback hub — we do not operate a casino."
        )
    return (
        '<p class="trustRibbon"><span class="stars" aria-hidden="true">★★★★☆</span>'
        f"<span>{inner}</span></p>"
    )


def disclaimer_bar() -> str:
    if LC and LC.lang == "fr":
        return "18+ uniquement. Le jeu comporte des risques. Utilisez des opérateurs agréés."
    return "18+ only. Gambling involves risk. Use licensed operators."


def policies_footer_title() -> str:
    if LC and LC.lang == "fr":
        return "Politiques et informations"
    return "Policies and disclosures"


def open_cta_label() -> str:
    if LC and LC.lang == "fr":
        return "Ouvrir Cazilla"
    return "Open Cazilla"


def cookie_footer_link(*, depth: int) -> str:
    for t in TECH_PAGES:
        if t.slug == "cookie-policy":
            href = ("../" * depth) + _legal_nav_href(t.rel_path, folder_mode=t.folder_mode)
            return f'<a href="{html.escape(href)}">{html.escape(t.menu_label)}</a>'
    href = ("../" * depth) + "cookie-policy.html"
    return f'<a href="{html.escape(href)}">cookie policy</a>'


def tech_policy_body() -> str:
    assert LC is not None
    return (
        '<article class="sectionCard" style="margin: 22px; max-width: 1180px; margin-left: auto; margin-right: auto">'
        f"<p>{html.escape(content_stub(LC))}</p></article>"
    )


def landing_page(page: ContentPageSpec) -> str:
    assert LC is not None
    rel = page.rel_path
    title, desc, h1 = landing_meta(page, LC)
    h2a, h2b, h2c, h3a, h3b, h3c = section_headings(LC, page.page_id, page.menu_label)
    stub = content_stub(LC)
    return f"""<!doctype html>
<html lang="{html.escape(HTML_LANG)}" data-min-gambling-age="18">
  <head>
{head_block(rel, title, desc, depth=0)}
  </head>
  <body class="">
{compliance_block(depth=0)}
<div id="siteContent" class="app">
      <main class="main" id="top">
        <header class="topbar">
          <div class="topbarLeft">
            <a class="logoText" href="index.html" aria-label="Cazilla review home"><span class="tpDot" aria-hidden="true"></span><span class="logoWord">{html.escape(SITE_NAME.upper())}</span></a>
          </div>
          <nav class="navLinks" id="mainNav" aria-label="Main navigation">
{nav_html(rel, depth=0)}
          </nav>
{actions_html(depth=0)}
        </header>

{trust_ribbon()}

        <section class="hero" aria-label="Hero">
          <div class="heroInner">
            <h1>{html.escape(h1)}</h1>
            <p class="subtitle">{html.escape(stub)}</p>
            <div class="disclaimerBar">{html.escape(disclaimer_bar())}</div>
            <div class="heroActions">
              <a class="btn primary" href="{html.escape(MAIN)}" rel="noopener noreferrer" target="_blank">{html.escape(open_cta_label())}</a>
            </div>
          </div>
        </section>

<div class="reviewBodyGrid">
        <section id="bonuses" class="sectionCard">
          <div class="sectionHead"><h2>{html.escape(h2a)}</h2></div>
          <h3>{html.escape(h3a)}</h3>
          <p class="subtitle">{html.escape(stub)}</p>
        </section>

        <section id="games" class="sectionCard">
          <div class="sectionHead"><h2>{html.escape(h2b)}</h2></div>
          <h3>{html.escape(h3b)}</h3>
          <p class="subtitle">{html.escape(stub)}</p>
        </section>

        <section id="about" class="sectionCard">
          <div class="sectionHead"><h2>{html.escape(h2c)}</h2></div>
          <h3>{html.escape(h3c)}</h3>
          <p class="subtitle">{html.escape(stub)}</p>
        </section>
        </div>

        <footer class="footer" id="footer">
          <div class="sectionHead">
            <h2>{html.escape(policies_footer_title())}</h2>
          </div>
{footer_legal(depth=0)}
          <p class="fineprint">{html.escape(stub)}</p>
          <p class="fineprint">© <span id="year">2026</span> {html.escape(SITE_NAME)}. {cookie_footer_link(depth=0)}</p>
        </footer>
      </main>
    </div>
    <script src="assets/r2-site.js" defer></script>
  </body>
</html>
"""


def technical_page(spec: TechPageSpec) -> str:
    assert LC is not None
    depth = spec.depth
    rel = spec.rel_path
    title = f"{spec.menu_label} | {SITE_NAME}"
    desc = f"{spec.menu_label} — {SITE_NAME}, {LC.region_name}."
    h1 = spec.menu_label
    hero_sub = legal_subtitle_fallback(LC)
    prefix = "../" * depth
    script = prefix + "assets/r2-site.js"
    home_href = prefix + "index.html"
    head_rel = rel if not spec.folder_mode else f"{spec.slug}/index.html"
    back_home = "Retour à l'accueil" if LC.lang == "fr" else "Back to home"
    body = tech_policy_body()
    nav_current = None
    return f"""<!doctype html>
<html lang="{html.escape(HTML_LANG)}" data-min-gambling-age="18">
  <head>
{head_block(head_rel, title, desc, depth=depth)}
  </head>
  <body class="innerPage">
{compliance_block(depth=depth)}
<div id="siteContent" class="app">
      <main class="main" id="top">
<header class="topbar">
  <div class="topbarLeft">
    <a class="logoText" href="{html.escape(home_href)}" aria-label="Cazilla review home"><span class="tpDot" aria-hidden="true"></span><span class="logoWord">{html.escape(SITE_NAME.upper())}</span></a>
  </div>
  <nav class="navLinks" id="mainNav" aria-label="Main navigation">
{nav_html(nav_current, depth=depth)}
  </nav>
{actions_html(depth=depth)}
</header>
{trust_ribbon(legal=True)}
<section class="hero" aria-label="Hero">
  <div class="heroInner">
    <h1>{html.escape(h1)}</h1>
    <p class="subtitle">{html.escape(hero_sub)}</p>
  </div>
</section>

<div class="policyCard">
{body}
    </div>

<p class="fineprint" style="margin: 24px 22px"><a href="{html.escape(home_href)}">{html.escape(back_home)}</a></p>

      </main>
    </div>
    <script src="{html.escape(script)}" defer></script>
  </body>
</html>
"""


def copy_assets() -> None:
    dest = SITE / "assets"
    dest.mkdir(parents=True, exist_ok=True)
    for name in ("r2-shell.css", "r2-page.css", "r2-compliance.css", "r2-site.js"):
        src = REVIEW_ASSET_SRC / name
        if src.is_file():
            shutil.copy2(src, dest / name)
    pics = dest / "pictures"
    pics.mkdir(parents=True, exist_ok=True)
    if PICTURE_SRC.is_dir():
        for f in PICTURE_SRC.iterdir():
            if f.is_file():
                shutil.copy2(f, pics / f.name)


def fix_keywords_meta() -> None:
    assert LC is not None
    kw = SITE / "_output" / "keywords.json"
    if not kw.is_file():
        return
    data = json.loads(kw.read_text(encoding="utf-8"))
    data["site"] = SITE_SLUG
    data["locale"] = LC.locale
    kw.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_htaccess() -> None:
    ht = """RewriteEngine On
RewriteCond %{HTTPS} off
RewriteRule ^ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]
RewriteCond %{HTTP_HOST} ^www\\.(.+)$ [NC]
RewriteRule ^ https://%1%{REQUEST_URI} [L,R=301]
RewriteRule ^index\\.html$ / [L,R=301]
"""
    (SITE / ".htaccess").write_text(ht, encoding="utf-8")


def write_all_landings() -> None:
    for page in CONTENT_PAGES:
        out = SITE / page.rel_path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(landing_page(page), encoding="utf-8")
        print("Wrote", page.rel_path)


def write_all_technical() -> None:
    for spec in TECH_PAGES:
        out = SITE / spec.rel_path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(technical_page(spec), encoding="utf-8")
        print("Wrote", spec.rel_path)


def write_technical_pages_only() -> None:
    write_all_technical()
    print("Technical pages only ->", SITE)


def main() -> int:
    init_site()
    SITE.mkdir(parents=True, exist_ok=True)
    write_all_landings()
    write_all_technical()
    copy_assets()
    write_htaccess()
    fix_keywords_meta()
    print("Review site ->", SITE, "| ORIGIN:", ORIGIN, "| locale:", LC.locale if LC else "?")
    return 0


if __name__ == "__main__":
    import sys as _sys

    if "--tech-only" in _sys.argv:
        init_site()
        SITE.mkdir(parents=True, exist_ok=True)
        raise SystemExit(write_technical_pages_only() or 0)
    raise SystemExit(main())
