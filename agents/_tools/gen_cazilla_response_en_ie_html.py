#!/usr/bin/env python3
"""Generator: HTML/CSS/JS shells for sites/*response* (expert single-page response type).

Reads SITE_DIR and SITE_URL from repo .env (defaults: sites/cazilla-response1-en-ie, https://cazilla.tmp.invalid).
"""
from __future__ import annotations

import html
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT / ".env"
PICTURE_SRC = ROOT / "sites" / "cazilla-offerwall2-en-ie" / "assets" / "pictures"
R3_ASSETS = ROOT / "sites" / "cazilla-review3-en-ie" / "assets"
MAIN = "https://cazilla.casino"


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


def resolve_site_targets(env: dict[str, str] | None = None) -> tuple[Path, str, str]:
    """SITE_DIR, SITE_URL, and folder slug from repo .env (defaults: response1 + cazilla.tmp.invalid)."""
    e = env if env is not None else _load_env()
    rel = (e.get("SITE_DIR") or "sites/cazilla-response1-en-ie").strip().lstrip("/")
    origin = (e.get("SITE_URL") or "https://cazilla.tmp.invalid").strip().rstrip("/")
    slug = Path(rel).name
    return ROOT / rel, origin, slug


SITE, ORIGIN, SITE_SLUG = resolve_site_targets()
SITE_NAME = "Cazilla Expert Test"
STUB = "Editorial placeholder. A2 will replace with locale-specific expert review copy."

SCREENSHOTS = [
    "assets/pictures/casino-feature-visual.png",
    "assets/pictures/slots-showcase.png",
    "assets/pictures/live-tables.jpg",
    "assets/pictures/blackjack-green-table.jpg",
    "assets/pictures/baccarat-live-table.webp",
    "assets/pictures/crazy-time-bonus.jpg",
    "assets/pictures/money-train-4-thumbnail.png",
    "assets/pictures/baccarat-bonus-terms.webp",
    "assets/pictures/rocket-crash-game.png",
    "assets/pictures/big-bass-bonanza-review.avif",
    "assets/pictures/fruit-classic-slot.png",
    "assets/pictures/bonus-promo-artwork.webp",
]

PAGE_COMMENTS = [
    {
        "initials": "SM",
        "name": "Sean M.",
        "date": "12 Apr 2026",
        "stars": "★★★★★",
        "title": "Fair bonus terms",
        "body": "Welcome offer was clear and wagering sat in a sensible range. Withdrawal to my Irish debit card took two business days after KYC.",
        "tags": "bonus,withdrawal",
    },
    {
        "initials": "AK",
        "name": "Aoife K.",
        "date": "3 Apr 2026",
        "stars": "★★★★☆",
        "title": "Strong slots lobby",
        "body": "Huge catalogue and filters work on mobile. Would like more transparent RTP notes beside thumbnails.",
        "tags": "slots,mobile",
    },
    {
        "initials": "PB",
        "name": "Patrick B.",
        "date": "28 Mar 2026",
        "stars": "★★★★☆",
        "title": "VIP feels attainable",
        "body": "Cashback tier unlocked after regular play without chasing losses. Support answered a limit question quickly.",
        "tags": "vip,support",
    },
]

SIDEBAR_NAV = [
    ("Tests & rankings", [("Casino tests", "#rs-overview"), ("Best casinos 2026", "#rs-comparison"), ("New casinos", "#rs-intro")]),
    ("Live & payments", [("Live casino", "#rs-games"), ("Crypto payments", "#rs-payments"), ("Payout limits", "#rs-payments")]),
    ("Bonuses", [("Welcome bonus", "#rs-bonuses"), ("Reload offers", "#rs-bonuses"), ("Cashback", "#rs-bonuses"), ("VIP programme", "#rs-vip")]),
    ("Games", [("Slots", "#rs-games"), ("Roulette", "#rs-games"), ("Blackjack", "#rs-games"), ("By provider", "#rs-games")]),
    ("Guides", [("How to choose", "#rs-faq"), ("VPN note", "#rs-faq"), ("Get help", "#rs-summary")]),
]

TOC_LINKS = [
    ("Licence", "#rs-licence"),
    ("Design", "#rs-design"),
    ("Bonuses", "#rs-bonuses"),
    ("VIP", "#rs-vip"),
    ("Payments", "#rs-payments"),
    ("Games", "#rs-games"),
    ("FAQ", "#rs-faq"),
    ("Summary", "#rs-summary"),
]

TOP_NAV = [
    ("Overview", "#rs-overview"),
    ("Bonuses", "#rs-bonuses"),
    ("Payments", "#rs-payments"),
    ("FAQ", "#rs-faq"),
    ("Summary", "#rs-summary"),
]

FOOTER_LEGAL = [
    ("user-agreement.html", "User agreement"),
    ("cookie-policy.html", "Cookie policy"),
    ("fair-play.html", "Fair play"),
    ("payments-withdrawals.html", "Payments &amp; withdrawals"),
    ("privacy-policy.html", "Privacy policy"),
    ("responsible-gambling.html", "Responsible gambling"),
    ("aml-kyc.html", "AML &amp; KYC"),
]

TECH_SPECS: list[tuple[str, str, str, str, str, str]] = [
    (
        "user-agreement",
        "user-agreement.html",
        "User agreement | Cazilla Expert Test",
        "Terms for using this independent Cazilla expert review site for Ireland readers.",
        "User agreement for this review site",
        "Rules for using this hub — not legal advice.",
    ),
    (
        "cookie-policy",
        "cookie-policy.html",
        "Cookie policy | Cazilla Expert Test",
        "How this Ireland-facing review site uses cookies and similar technologies.",
        "Cookie policy for Ireland readers",
        "What cookies we use and how you can control them.",
    ),
    (
        "fair-play",
        "fair-play.html",
        "Fair play | Cazilla Expert Test",
        "How we keep Cazilla expert reviews fair, independent, and corrected when facts change.",
        "Fair play statement for our reviews",
        "Independence, testing methodology, and corrections.",
    ),
    (
        "payments-withdrawals",
        "payments-withdrawals.html",
        "Payments & withdrawals | Cazilla Expert Test",
        "Editorial overview of deposits and payouts for Irish players on licensed sites.",
        "Payments and withdrawals overview",
        "Typical methods and why timelines vary by operator.",
    ),
    (
        "privacy-policy",
        "privacy-policy.html",
        "Privacy policy | Cazilla Expert Test",
        "How we handle personal data on this Cazilla review hub for Ireland.",
        "Privacy policy for this review hub",
        "Plain-language data overview — not legal advice.",
    ),
    (
        "responsible-gambling",
        "responsible-gambling.html",
        "Responsible gambling | Cazilla Expert Test",
        "Safer play resources for Ireland and tools on licensed operators.",
        "Responsible gambling resources",
        "National support and operator safer-gambling tools.",
    ),
    (
        "aml-kyc",
        "aml-kyc.html",
        "AML & KYC | Cazilla Expert Test",
        "Plain-language explainer on identity checks at licensed operators.",
        "AML and KYC explainer",
        "Why licensed brands ask for ID — overview only.",
    ),
]

HOME_KEYWORDS = [
    {"keyword": "online casino in ireland", "search_volume": 6600, "keyword_difficulty": 37.0, "cpc": 163.27, "competition": "LOW"},
    {"keyword": "casino online ireland", "search_volume": 6600, "keyword_difficulty": 31.0, "cpc": 163.27, "competition": "LOW"},
    {"keyword": "ireland casino online", "search_volume": 6600, "keyword_difficulty": 31.0, "cpc": 163.27, "competition": "LOW"},
    {"keyword": "best casino online ireland", "search_volume": 1300, "keyword_difficulty": 31.0, "cpc": 142.2, "competition": "LOW"},
    {"keyword": "new casino online ireland", "search_volume": 140, "keyword_difficulty": 37.0, "cpc": 118.02, "competition": "LOW"},
    {"keyword": "new online casino ireland", "search_volume": 70, "keyword_difficulty": 36.0, "cpc": 80.55, "competition": "LOW"},
    {"keyword": "the best casino online ireland", "search_volume": 50, "keyword_difficulty": 27.0, "cpc": 147.31, "competition": "LOW"},
    {"keyword": "top online casino ireland", "search_volume": 40, "keyword_difficulty": 34.0, "cpc": 114.3, "competition": "LOW"},
    {"keyword": "best casino online in ireland", "search_volume": 40, "keyword_difficulty": 33.0, "cpc": 191.52, "competition": "LOW"},
    {"keyword": "best online casino ireland reddit", "search_volume": 40, "keyword_difficulty": 0.0, "cpc": 53.11, "competition": "HIGH"},
    {"keyword": "online casino ireland real money", "search_volume": 10, "keyword_difficulty": 37.0, "cpc": 84.76, "competition": "MEDIUM"},
    {"keyword": "online ireland casino", "search_volume": 0, "keyword_difficulty": 0.0, "cpc": 0.0, "competition": ""},
    {"keyword": "online casino bonuses ireland", "search_volume": 0, "keyword_difficulty": 0.0, "cpc": 0.0, "competition": ""},
    {"keyword": "best payout online casino ireland", "search_volume": 0, "keyword_difficulty": 0.0, "cpc": 0.0, "competition": ""},
    {"keyword": "best ireland casino online", "search_volume": 0, "keyword_difficulty": 0.0, "cpc": 0.0, "competition": ""},
    {"keyword": "online casino in ireland no deposit", "search_volume": 0, "keyword_difficulty": 0.0, "cpc": 0.0, "competition": ""},
    {"keyword": "online casino in ireland with no deposit", "search_volume": 0, "keyword_difficulty": 0.0, "cpc": 0.0, "competition": ""},
]

def _tech_kw(*phrases: str) -> list[dict[str, object]]:
    return [
        {"keyword": p, "search_volume": 0, "keyword_difficulty": 0, "cpc": 0, "competition": ""}
        for p in phrases
    ]


TECH_KEYWORD_TEMPLATES: dict[str, list[dict[str, object]]] = {
    "user-agreement": _tech_kw(
        "casino play online ireland",
        "live online casino ireland",
    ),
    "cookie-policy": _tech_kw(
        "online casino payment methods ireland",
        "republic of ireland online casino",
        "online casinos ireland ireland casino",
    ),
    "fair-play": _tech_kw(
        "ireland online casino games",
        "how online casino cashback bonuses work ireland",
        "online casino legal in ireland",
    ),
    "payments-withdrawals": _tech_kw(
        "online casino ireland paypal",
        "real online casino ireland no deposit",
        "best online casino ireland",
        "online casino ireland no deposit free spins",
    ),
    "privacy-policy": _tech_kw(
        "online casino ireland no deposit bonus",
        "best casino ireland online",
        "free online casino ireland",
    ),
    "responsible-gambling": _tech_kw(
        "fast payout online casino ireland",
        "good online casino ireland",
        "online casino license ireland",
    ),
    "aml-kyc": _tech_kw(
        "legit online casino ireland",
        "newest online casino ireland",
        "online casino 10 minimum deposit",
        "online casino minimum deposit 5 euro",
        "online casino no minimum deposit",
        "online casino instant withdrawal",
    ),
}


def review_card(r: dict[str, str]) -> str:
    tags = [html.escape(t.strip()) for t in r.get("tags", "").split(",") if t.strip()]
    tag_html = "".join(f'<span class="tag">{t}</span>' for t in tags)
    ei = html.escape(r["initials"])
    en = html.escape(r["name"])
    ed = html.escape(r["date"])
    et = html.escape(r["title"])
    eb = html.escape(r["body"])
    es = r["stars"]
    return (
        "<article class=\"reviewCard\">\n"
        "  <div class=\"reviewCardHead\">\n"
        "    <div class=\"reviewer\">\n"
        f"      <span class=\"avatar\" aria-hidden=\"true\">{ei}</span>\n"
        "      <div>\n"
        f"        <div class=\"reviewerName\">{en}</div>\n"
        f"        <div class=\"reviewDate\">{ed}</div>\n"
        "      </div>\n"
        "    </div>\n"
        f"    <span class=\"reviewStars\" aria-label=\"Rating\">{es}</span>\n"
        "  </div>\n"
        f"  <h3 class=\"reviewTitle\">{et}</h3>\n"
        f"  <p>{eb}</p>\n"
        f"  <div class=\"reviewTags\">{tag_html}</div>\n"
        "</article>"
    )


def footer_legal_html(*, current: str | None = None) -> str:
    parts = []
    for href, lab in FOOTER_LEGAL:
        cur = ' aria-current="page"' if current == href else ""
        parts.append(f'            <a href="{href}"{cur}>{lab}</a>')
    return (
        '          <nav class="footerLegal" aria-label="Legal pages">\n'
        + "\n".join(parts)
        + "\n          </nav>"
    )


def compliance_block() -> str:
    return """<div class="complianceOverlay" id="ageGate" role="dialog" aria-modal="true" aria-labelledby="ageTitle">
  <div class="complianceDialog">
    <h2 id="ageTitle">Confirm you are 18 or over</h2>
    <p>This site discusses regulated gambling topics for readers in Ireland. You must be at least 18 to continue.</p>
    <div class="complianceActions">
      <button type="button" class="btn" id="ageUnder">I am under 18</button>
      <button type="button" class="btn primary" id="ageOk">I am 18 or over</button>
    </div>
  </div>
</div>
<div class="complianceOverlay" id="cookieGate" hidden aria-hidden="true" role="dialog" aria-modal="true" aria-labelledby="cookieTitle">
  <div class="complianceDialog">
    <h2 id="cookieTitle">Cookie preferences</h2>
    <p>We use cookies to remember your age check. See <a href="cookie-policy.html">cookie policy</a>.</p>
    <div class="complianceActions">
      <button type="button" class="btn" id="cookieReject">Essential only</button>
      <button type="button" class="btn primary" id="cookieAccept">Accept</button>
    </div>
  </div>
</div>"""


def actions_html() -> str:
    return f"""          <div class="actions">
            <button class="btn icon hamburger" id="hamburger" type="button" aria-label="Open menu">≡</button>
            <button class="btn icon sidebarToggle" id="sidebarToggle" type="button" aria-label="Open section menu">☰</button>
            <a class="btn" href="{MAIN}" rel="noopener noreferrer" target="_blank">Official site</a>
            <a class="btn primary" href="{MAIN}" rel="noopener noreferrer" target="_blank">Visit Cazilla</a>
          </div>"""


def sidebar_html() -> str:
    blocks = []
    for group, links in SIDEBAR_NAV:
        items = "\n".join(
            f'          <li><a href="{href}">{html.escape(label)}</a></li>' for label, href in links
        )
        blocks.append(f"        <h2>{html.escape(group)}</h2>\n        <ul>\n{items}\n        </ul>")
    return "      <aside class=\"rs-sidebar\" id=\"rsSidebar\" aria-label=\"Section navigation\">\n" + "\n".join(blocks) + "\n      </aside>"


def toc_html() -> str:
    items = "\n".join(f'    <li><a href="{href}">{html.escape(label)}</a></li>' for label, href in TOC_LINKS)
    return f'  <nav class="rs-tocWrap" aria-label="On-page contents">\n    <ul class="rs-toc">\n{items}\n    </ul>\n  </nav>'


def top_nav_html() -> str:
    return "\n".join(f'            <a href="{href}">{html.escape(label)}</a>' for label, href in TOP_NAV)


def gallery_html() -> str:
    slides = []
    for i, src in enumerate(SCREENSHOTS):
        name = Path(src).name
        cls = "is-active" if i == 0 else ""
        slides.append(
            f'        <img src="{src}" alt="Screenshot {i + 1}: {html.escape(name)}" '
            f'data-slide="{i}" class="{cls}" loading="lazy" />'
        )
    dots = "\n".join(
        f'        <button type="button" data-goto="{i}" aria-label="Slide {i + 1}"'
        f' class="{"is-active" if i == 0 else ""}"></button>'
        for i in range(len(SCREENSHOTS))
    )
    return (
        "        <section class=\"rs-gallery\" aria-label=\"Screenshots\">\n"
        "          <div class=\"rs-gallery-viewport\" id=\"galleryViewport\" aria-live=\"polite\">\n"
        + "\n".join(slides)
        + "\n          </div>\n"
        "          <div class=\"rs-gallery-controls\">\n"
        "            <button type=\"button\" class=\"btn\" id=\"galleryPrev\" aria-label=\"Previous screenshot\">Prev</button>\n"
        "            <div class=\"rs-gallery-dots\" id=\"galleryDots\">\n"
        + dots
        + "\n            </div>\n"
        "            <button type=\"button\" class=\"btn\" id=\"galleryNext\" aria-label=\"Next screenshot\">Next</button>\n"
        "          </div>\n"
        "        </section>"
    )


def pros_cons_html() -> str:
    pros = "\n".join(f"              <li>{html.escape(STUB[:70])}</li>" for _ in range(3))
    cons = "\n".join(f"              <li>{html.escape(STUB[:65])}</li>" for _ in range(2))
    return f"""        <div class="rs-pros-cons">
          <div>
            <h3>Pros</h3>
            <ul class="rs-pros" data-a2-field="pros">
{pros}
            </ul>
          </div>
          <div>
            <h3>Cons</h3>
            <ul class="rs-cons" data-a2-field="cons">
{cons}
            </ul>
          </div>
        </div>"""


def overview_table_html() -> str:
    rows = [
        ("Licence", "Malta Gaming Authority (MGA)"),
        ("Welcome bonus", "First-deposit match + free spins (40x wagering)"),
        ("Min deposit", "€10"),
        ("Withdrawal speed", "E-wallets ~24h; cards 1–3 business days"),
        ("Game providers", "40+ (NetEnt, Pragmatic Play, Evolution, Play'n GO)"),
        ("Mobile", "Responsive web — full catalogue on iOS and Android"),
    ]
    body = "\n".join(f"              <tr><th>{html.escape(k)}</th><td>{html.escape(v)}</td></tr>" for k, v in rows)
    return f"""          <table class="rs-overview-table" aria-label="Cazilla at a glance">
            <tbody>
{body}
            </tbody>
          </table>"""


def section_html(section_id: str, heading: str, field: str, *, extra: str = "") -> str:
    return f"""        <section id="{section_id}" class="rs-section">
          <h2>{html.escape(heading)}</h2>
{extra}          <div class="rs-prose" data-a2-field="{field}">
            <p class="rs-body">{html.escape(STUB)}</p>
          </div>
        </section>"""


def faq_html() -> str:
    items = []
    for i in range(3):
        items.append(
            f"""          <details>
            <summary>FAQ placeholder {i + 1}</summary>
            <p class="rs-body">{html.escape(STUB)}</p>
          </details>"""
        )
    return f"""        <section id="rs-faq" class="rs-section rs-faq">
          <h2>FAQ</h2>
          <div class="rs-prose" data-a2-field="faq_section">
{chr(10).join(items)}
          </div>
        </section>"""


def comments_html() -> str:
    cards = "\n".join(review_card(c) for c in PAGE_COMMENTS)
    return f"""        <section id="rs-comments" class="rs-section rs-comments">
          <h2>Reader comments</h2>
          <div class="reviewFeed">
{cards}
          </div>
        </section>"""


def index_html() -> str:
    sections = "\n".join(
        [
            section_html("rs-overview", "Overview & methodology", "overview_section", extra=overview_table_html() + "\n"),
            f"""        <section id="rs-intro" class="rs-section">
          <h2>Introduction</h2>
          <p class="rs-intro-meta" data-a2-field="intro_meta">{html.escape(STUB)}</p>
        </section>""",
            section_html("rs-licence", "Licence & security", "licence_section"),
            section_html("rs-design", "Design & UX", "design_section"),
            section_html("rs-bonuses", "Bonuses & promotions", "bonus_section"),
            section_html("rs-vip", "VIP programme", "vip_section"),
            section_html("rs-payments", "Payments & withdrawals", "payments_section"),
            section_html("rs-games", "Games & providers", "games_section"),
            section_html("rs-comparison", "Comparison with alternatives", "comparison_section"),
            section_html("rs-summary", "Summary & verdict", "summary_section"),
            faq_html(),
            f"""        <section id="rs-author" class="rs-section">
          <h2>About the author</h2>
          <div class="rs-author-card" data-a2-field="author_bio">
            <p class="rs-body">{html.escape(STUB)}</p>
          </div>
        </section>""",
            comments_html(),
        ]
    )
    return f"""<!doctype html>
<html lang="en-IE" data-site-kind="response" data-min-gambling-age="18">
  <head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Cazilla expert review | Ireland online casino test</title>
<meta name="description" content="Independent expert test-drive review of Cazilla for Ireland: licence, bonuses, payments, games, and player-focused verdict." />
<meta name="robots" content="index, follow" />
<link rel="canonical" href="{ORIGIN}/" />
<link rel="alternate" hreflang="en-IE" href="{ORIGIN}/" />
<link rel="alternate" hreflang="x-default" href="{ORIGIN}/" />
<meta property="og:title" content="Cazilla expert review | Ireland" />
<meta property="og:description" content="Expert test-drive review of Cazilla for Irish players." />
<meta property="og:url" content="{ORIGIN}/" />
<meta property="og:type" content="article" />
<meta property="og:locale" content="en_IE" />
<meta property="og:image" content="{ORIGIN}/assets/pictures/og-logo.svg" />
<script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "WebSite",
    "name": "{html.escape(SITE_NAME)}",
    "url": "{ORIGIN}/"
  }}
</script>
<link rel="stylesheet" href="assets/rs-shell.css" />
<link rel="stylesheet" href="assets/rs-page.css" />
<link rel="stylesheet" href="assets/rs-compliance.css" />
  </head>
  <body class="rs-layout">
{compliance_block()}
<div id="siteContent" class="app rs-app">
  <div class="rs-grid">
{sidebar_html()}
    <div class="rs-column">
      <header class="topbar rs-topbar">
        <div class="topbarLeft">
          <a class="logoText" href="index.html" aria-label="{html.escape(SITE_NAME)} home"><span class="logoMark" aria-hidden="true">C</span><span class="logoWord">{html.escape(SITE_NAME.upper())}</span></a>
        </div>
        <nav class="navLinks" id="mainNav" aria-label="Main navigation">
{top_nav_html()}
        </nav>
{actions_html()}
      </header>
      <p class="rs-ribbon"><span class="stars" aria-hidden="true">★★★★★</span> <strong>{html.escape(SITE_NAME)}</strong> — independent expert review for Ireland (en-IE). We do not operate a casino.</p>
      <main class="main rs-main" id="top">
        <section class="hero" aria-label="Hero">
          <div class="heroInner">
            <h1 data-a2-field="hero_title">Cazilla expert review for Ireland</h1>
            <p class="subtitle" data-a2-field="hero_subtitle">{html.escape(STUB)}</p>
            <div class="rs-hero-rating" aria-label="Editorial rating">
              <p class="rs-score-pill">5.0 <span>/ 5.0</span></p>
              <span class="scoreStars" aria-hidden="true">★★★★★</span>
              <span class="scoreMeta">Expert test-drive score</span>
            </div>
            <div class="disclaimerBar">18+ only. Gambling involves risk. Use licensed operators.</div>
            <div class="heroActions">
              <a class="btn primary" href="{MAIN}" rel="noopener noreferrer" target="_blank">Visit Cazilla</a>
            </div>
          </div>
        </section>
{toc_html()}
{gallery_html()}
{pros_cons_html()}
{sections}
      </main>
      <footer class="footer rs-footer" id="footer">
        <div class="sectionHead"><h2>Policies and disclosures</h2></div>
{footer_legal_html()}
        <p class="fineprint" data-a2-field="footer">{html.escape(STUB)}</p>
        <p class="fineprint">© <span id="year">2026</span> {html.escape(SITE_NAME)}. <a href="cookie-policy.html">Cookie policy</a></p>
      </footer>
    </div>
  </div>
</div>
<script src="assets/rs-site.js" defer></script>
  </body>
</html>"""


def _r3_tech_body(slug: str) -> str:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "gen_r3",
        ROOT / "agents" / "_tools" / "gen_cazilla_review3_en_ie_html.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod.tech_body(slug)


def tech_body(slug: str) -> str:
    body = _r3_tech_body(slug)
    body = body.replace("Cazilla Player Voices", SITE_NAME)
    body = body.replace("../cookie-policy/", "cookie-policy.html")
    body = body.replace("../privacy-policy/", "privacy-policy.html")
    return body


def tech_page_html(rel: str, title: str, description: str, h1: str, hero_sub: str, slug: str) -> str:
    canonical = f"{ORIGIN}/{rel}"
    body = tech_body(slug)
    return f"""<!doctype html>
<html lang="en-IE" data-site-kind="response" data-min-gambling-age="18">
  <head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}" />
<meta name="robots" content="index, follow" />
<link rel="canonical" href="{html.escape(canonical)}" />
<link rel="alternate" hreflang="en-IE" href="{html.escape(canonical)}" />
<link rel="alternate" hreflang="x-default" href="{html.escape(canonical)}" />
<meta property="og:title" content="{html.escape(title)}" />
<meta property="og:description" content="{html.escape(description)}" />
<meta property="og:url" content="{html.escape(canonical)}" />
<meta property="og:type" content="website" />
<meta property="og:locale" content="en_IE" />
<meta property="og:image" content="{ORIGIN}/assets/pictures/og-logo.svg" />
<link rel="stylesheet" href="assets/rs-shell.css" />
<link rel="stylesheet" href="assets/rs-page.css" />
<link rel="stylesheet" href="assets/rs-compliance.css" />
  </head>
  <body class="rs-layout innerPage">
{compliance_block()}
<div id="siteContent" class="app rs-app">
  <header class="topbar rs-topbar">
    <div class="topbarLeft">
      <a class="logoText" href="index.html" aria-label="{html.escape(SITE_NAME)} home"><span class="logoMark" aria-hidden="true">C</span><span class="logoWord">{html.escape(SITE_NAME.upper())}</span></a>
    </div>
    <nav class="navLinks" id="mainNav" aria-label="Main navigation">
      <a href="index.html">Review home</a>
    </nav>
{actions_html()}
  </header>
  <p class="rs-ribbon"><strong>Legal information</strong> for Ireland readers — {html.escape(SITE_NAME)}.</p>
  <main class="main rs-main">
    <section class="hero" aria-label="Hero">
      <div class="heroInner">
        <h1>{html.escape(h1)}</h1>
        <p class="subtitle">{html.escape(hero_sub)}</p>
      </div>
    </section>
    <div class="policyCard">{body}</div>
    <p class="fineprint" style="margin: 24px 0"><a href="index.html">Back to review</a></p>
  </main>
  <footer class="footer rs-footer">
{footer_legal_html(current=rel)}
    <p class="fineprint">© <span id="year">2026</span> {html.escape(SITE_NAME)}.</p>
  </footer>
</div>
<script src="assets/rs-site.js" defer></script>
  </body>
</html>"""


RS_SHELL_EXTRA = """
body.rs-layout { margin: 0; }
.rs-app { min-height: 100vh; }
.rs-grid { display: grid; grid-template-columns: 260px minmax(0, 1fr); align-items: start; max-width: 1400px; margin: 0 auto; }
.rs-sidebar { position: sticky; top: 56px; max-height: calc(100vh - 56px); overflow-y: auto; padding: 18px 14px 24px 18px; background: #fff; border-right: 1px solid var(--rs-line); }
.rs-sidebar h2 { margin: 14px 0 6px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--rs-muted); }
.rs-sidebar ul { list-style: none; margin: 0 0 8px; padding: 0; }
.rs-sidebar a { display: block; padding: 5px 8px; font-size: 13px; color: var(--rs-ink); text-decoration: none; border-radius: 6px; }
.rs-sidebar a:hover, .rs-sidebar a.is-active { background: #eff6ff; color: var(--rs-accent); }
.rs-column { min-width: 0; }
.rs-topbar { position: sticky; top: 0; z-index: 50; }
.rs-main { padding: 0 22px 40px; }
.rs-ribbon { margin: 0; padding: 10px 22px; background: #fff; border-bottom: 1px solid var(--rs-line); font-size: 14px; color: var(--rs-muted); text-align: center; }
.btn.icon.sidebarToggle { display: none; }
@media (max-width: 960px) {
  .rs-grid { grid-template-columns: 1fr; }
  .btn.icon.sidebarToggle { display: inline-flex; }
  .rs-sidebar { position: fixed; inset: 0 auto 0 0; width: min(280px, 88vw); z-index: 60; transform: translateX(-105%); transition: transform 0.2s ease; box-shadow: 8px 0 24px rgba(15,23,42,0.15); }
  .rs-sidebar[data-open="true"] { transform: translateX(0); }
  body.rs-sidebar-open::before { content: ""; position: fixed; inset: 0; background: rgba(15,23,42,0.45); z-index: 55; }
}
"""

RS_PAGE_EXTRA = """
.rs-hero-rating { display: flex; flex-wrap: wrap; align-items: center; gap: 12px 18px; margin-top: 12px; }
.rs-score-pill { font-size: 28px; font-weight: 800; color: var(--rs-navy); margin: 0; }
.rs-score-pill span { font-size: 16px; font-weight: 600; color: var(--rs-muted); }
.rs-tocWrap { margin: 18px 0; }
.rs-toc { display: flex; flex-wrap: wrap; gap: 8px; margin: 0; padding: 0; list-style: none; }
.rs-toc a { font-size: 13px; padding: 6px 12px; border-radius: 999px; border: 1px solid var(--rs-line); background: #fff; color: var(--rs-ink); text-decoration: none; }
.rs-toc a:hover { border-color: var(--rs-accent); color: var(--rs-accent); }
.rs-intro-meta { font-size: 14px; color: var(--rs-muted); margin: 0 0 16px; }
.rs-gallery { margin: 20px 0; background: var(--rs-card); border: 1px solid var(--rs-line); border-radius: 12px; overflow: hidden; }
.rs-gallery-viewport { position: relative; aspect-ratio: 16/9; background: #0f172a; }
.rs-gallery-viewport img { width: 100%; height: 100%; object-fit: cover; display: none; }
.rs-gallery-viewport img.is-active { display: block; }
.rs-gallery-controls { display: flex; align-items: center; justify-content: space-between; padding: 10px 14px; gap: 10px; }
.rs-gallery-dots { display: flex; flex-wrap: wrap; gap: 6px; }
.rs-gallery-dots button { width: 8px; height: 8px; border-radius: 50%; border: none; background: var(--rs-line); cursor: pointer; padding: 0; }
.rs-gallery-dots button.is-active { background: var(--rs-accent); }
.rs-pros-cons { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 20px 0; }
@media (max-width: 640px) { .rs-pros-cons { grid-template-columns: 1fr; } }
.rs-pros-cons h3 { margin: 0 0 8px; font-size: 15px; }
.rs-pros, .rs-cons { margin: 0; padding-left: 20px; font-size: 14px; line-height: 1.6; }
.rs-overview-table { width: 100%; border-collapse: collapse; font-size: 14px; margin: 12px 0 0; }
.rs-overview-table th, .rs-overview-table td { border: 1px solid var(--rs-line); padding: 8px 10px; text-align: left; }
.rs-overview-table th { background: #f8fafc; }
.rs-section { margin: 28px 0; padding: 20px 22px; background: var(--rs-card); border: 1px solid var(--rs-line); border-radius: 12px; }
.rs-section h2 { margin: 0 0 12px; font-size: 20px; color: var(--rs-navy); }
.rs-prose .rs-body { margin: 0; font-size: 15px; line-height: 1.7; color: #334155; }
.rs-faq details { border: 1px solid var(--rs-line); border-radius: 8px; padding: 10px 12px; margin-bottom: 8px; background: #fff; }
.rs-faq summary { cursor: pointer; font-weight: 600; }
.rs-author-card { padding: 16px 18px; border: 1px solid var(--rs-line); border-radius: 12px; background: #f8fafc; }
.rs-footer { padding: 24px 22px 48px; border-top: 1px solid var(--rs-line); }
body.innerPage .policyCard { max-width: 1180px; margin: 22px auto; padding: 0 22px; }
body.innerPage .policyCard .sectionCard { margin: 0; }
body.innerPage .policyCard p { margin: 0 0 12px; line-height: 1.7; color: #334155; }
"""

RS_SITE_JS = r"""(function () {
  "use strict";
  var AGE_COOKIE = "cazilla_response_skin_age_ok";
  var COOKIE_CHOICE = "cazilla_response_skin_cookie";
  var AGE_MAX_AGE = 3 * 24 * 60 * 60;
  var hamburger = document.getElementById("hamburger");
  var mainNav = document.getElementById("mainNav");
  var sidebar = document.getElementById("rsSidebar");
  var sidebarToggle = document.getElementById("sidebarToggle");
  var year = document.getElementById("year");
  if (year) year.textContent = String(new Date().getFullYear());
  if (hamburger && mainNav) {
    hamburger.addEventListener("click", function () {
      mainNav.dataset.open = mainNav.dataset.open === "true" ? "false" : "true";
    });
  }
  function setSidebar(open) {
    if (!sidebar) return;
    sidebar.dataset.open = open ? "true" : "false";
    document.body.classList.toggle("rs-sidebar-open", !!open);
  }
  if (sidebarToggle) {
    sidebarToggle.addEventListener("click", function () {
      setSidebar(sidebar.dataset.open !== "true");
    });
  }
  function getCookie(name) {
    var m = document.cookie.match(
      new RegExp("(?:^|; )" + name.replace(/([.$?*|{}()[\]\\/+^])/g, "\\$1") + "=([^;]*)")
    );
    return m ? decodeURIComponent(m[1]) : "";
  }
  function setCookie(name, value, maxAgeSec) {
    document.cookie =
      name + "=" + encodeURIComponent(value) + ";path=/;max-age=" + String(maxAgeSec) + ";SameSite=Lax";
  }
  var ageGate = document.getElementById("ageGate");
  var cookieGate = document.getElementById("cookieGate");
  var siteContent = document.getElementById("siteContent");
  var ageUnder = document.getElementById("ageUnder");
  var ageOk = document.getElementById("ageOk");
  var cookieAccept = document.getElementById("cookieAccept");
  var cookieReject = document.getElementById("cookieReject");
  function show(el) {
    if (!el) return;
    el.removeAttribute("hidden");
    el.setAttribute("aria-hidden", "false");
  }
  function hide(el) {
    if (!el) return;
    el.setAttribute("hidden", "hidden");
    el.setAttribute("aria-hidden", "true");
  }
  function setBlur(on) {
    if (siteContent) siteContent.classList.toggle("isBlurred", !!on);
  }
  function setScrollLock(on) {
    document.documentElement.classList.toggle("complianceNoScroll", !!on);
  }
  if (ageUnder) {
    ageUnder.addEventListener("click", function () {
      hide(ageGate);
      setBlur(true);
      setScrollLock(true);
    });
  }
  if (ageOk) {
    ageOk.addEventListener("click", function () {
      setCookie(AGE_COOKIE, "1", AGE_MAX_AGE);
      hide(ageGate);
      setBlur(false);
      setScrollLock(false);
      show(cookieGate);
    });
  }
  function closeCookieChoice(val) {
    setCookie(COOKIE_CHOICE, val, 365 * 24 * 60 * 60);
    hide(cookieGate);
  }
  if (cookieAccept) cookieAccept.addEventListener("click", function () { closeCookieChoice("accept"); });
  if (cookieReject) cookieReject.addEventListener("click", function () { closeCookieChoice("reject"); });
  if (getCookie(AGE_COOKIE) === "1") {
    hide(ageGate);
    setBlur(false);
    if (!getCookie(COOKIE_CHOICE)) show(cookieGate);
    else hide(cookieGate);
  } else {
    show(ageGate);
    hide(cookieGate);
  }
  var viewport = document.getElementById("galleryViewport");
  var prev = document.getElementById("galleryPrev");
  var next = document.getElementById("galleryNext");
  var dots = document.getElementById("galleryDots");
  if (viewport) {
    var slides = Array.prototype.slice.call(viewport.querySelectorAll("img[data-slide]"));
    var idx = 0;
    function showSlide(i) {
      if (!slides.length) return;
      idx = (i + slides.length) % slides.length;
      slides.forEach(function (img, n) {
        img.classList.toggle("is-active", n === idx);
      });
      if (dots) {
        Array.prototype.forEach.call(dots.querySelectorAll("button"), function (btn, n) {
          btn.classList.toggle("is-active", n === idx);
        });
      }
    }
    if (prev) prev.addEventListener("click", function () { showSlide(idx - 1); });
    if (next) next.addEventListener("click", function () { showSlide(idx + 1); });
    if (dots) {
      dots.addEventListener("click", function (e) {
        var t = e.target;
        if (t && t.getAttribute("data-goto") != null) {
          showSlide(parseInt(t.getAttribute("data-goto"), 10));
        }
      });
    }
    showSlide(0);
  }
})();"""


def adapt_css(text: str) -> str:
    return text.replace("--r3-", "--rs-")


def write_assets() -> None:
    assets = SITE / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    (assets / "rs-shell.css").write_text(
        adapt_css((R3_ASSETS / "r3-shell.css").read_text(encoding="utf-8")) + RS_SHELL_EXTRA,
        encoding="utf-8",
    )
    (assets / "rs-page.css").write_text(
        adapt_css((R3_ASSETS / "r3-page.css").read_text(encoding="utf-8")) + RS_PAGE_EXTRA,
        encoding="utf-8",
    )
    (assets / "rs-compliance.css").write_text(
        adapt_css((R3_ASSETS / "r3-compliance.css").read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    (assets / "rs-site.js").write_text(RS_SITE_JS, encoding="utf-8")


def copy_pictures() -> None:
    dest = SITE / "assets" / "pictures"
    dest.mkdir(parents=True, exist_ok=True)
    if PICTURE_SRC.is_dir():
        for f in PICTURE_SRC.iterdir():
            if f.is_file():
                shutil.copy2(f, dest / f.name)


def write_robots() -> None:
    (SITE / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {ORIGIN}/sitemap.xml\n",
        encoding="utf-8",
    )


def write_sitemap() -> None:
    urls = [f"{ORIGIN}/"] + [f"{ORIGIN}/{spec[1]}" for spec in TECH_SPECS]
    entries = []
    for loc in urls:
        pri = "1.0" if loc.endswith("/") else "0.7"
        entries.append(
            f"""  <url>
    <loc>{loc}</loc>
    <xhtml:link rel="alternate" hreflang="en-IE" href="{loc}"/>
    <xhtml:link rel="alternate" hreflang="x-default" href="{loc}"/>
    <lastmod>2026-05-15</lastmod>
    <changefreq>weekly</changefreq>
    <priority>{pri}</priority>
  </url>"""
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
    ht = """RewriteEngine On
RewriteCond %{HTTPS} off
RewriteRule ^ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]
RewriteCond %{HTTP_HOST} ^www\\.(.+)$ [NC]
RewriteRule ^ https://%1%{REQUEST_URI} [L,R=301]
RewriteRule ^index\\.html$ / [L,R=301]
"""
    (SITE / ".htaccess").write_text(ht, encoding="utf-8")


TECH_MENU_LABELS = {
    "user-agreement": "User agreement",
    "cookie-policy": "Cookie policy",
    "fair-play": "Fair play",
    "payments-withdrawals": "Payments & withdrawals",
    "privacy-policy": "Privacy policy",
    "responsible-gambling": "Responsible gambling",
    "aml-kyc": "AML & KYC",
}


def write_keywords_scaffold() -> None:
    technical = []
    for slug, rel, _title, _desc, _h1, _hero in TECH_SPECS:
        technical.append(
            {
                "id": slug,
                "path": rel,
                "menu_label": TECH_MENU_LABELS[slug],
                "cluster": f"cl_{slug.replace('-', '_')}",
                "qa_profile": "technical",
                "keywords": TECH_KEYWORD_TEMPLATES.get(slug, []),
            }
        )
    data = {
        "version": 2,
        "locale": "en-IE",
        "site": SITE_SLUG,
        "pages": [
            {
                "id": "home",
                "path": "/index.html",
                "menu_label": "Review",
                "cluster": "cl_response_home",
                "qa_profile": "standard",
                "keywords": HOME_KEYWORDS,
            }
        ],
        "technical_pages": technical,
        "reserve": [],
    }
    out = SITE / "_output" / "keywords.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "index.html").write_text(index_html(), encoding="utf-8")
    for slug, rel, title, desc, h1, hero_sub in TECH_SPECS:
        (SITE / rel).write_text(
            tech_page_html(rel, title, desc, h1, hero_sub, slug),
            encoding="utf-8",
        )
    write_assets()
    copy_pictures()
    write_robots()
    write_sitemap()
    write_htaccess()
    write_keywords_scaffold()
    print("Wrote response site ->", SITE)


if __name__ == "__main__":
    raise SystemExit(main())

