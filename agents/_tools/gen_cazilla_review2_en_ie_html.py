#!/usr/bin/env python3
"""One-off generator: HTML shells for sites/cazilla-review2-en-ie (Trustpilot-style skin)."""
from __future__ import annotations

import html
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "sites" / "cazilla-review2-en-ie"
ORIGIN = "https://cazilla.skin"
MAIN = "https://cazilla.casino"

NAV = [
    ("index.html", "Home"),
    ("casino-games.html", "Casino games"),
    ("casino-deposit.html", "Casino deposit"),
    ("bonus.html", "Bonus"),
    ("about.html", "About"),
]


def nav_html(current: str | None, *, depth: int) -> str:
    prefix = "../" * depth
    lines = []
    for href, label in NAV:
        cur = ' aria-current="page"' if current is not None and href == current else ""
        lines.append(f'            <a href="{prefix}{href}"{cur}>{html.escape(label)}</a>')
    return "\n".join(lines)


def actions_html(*, depth: int) -> str:
    prefix = "../" * depth
    return f"""          <div class="actions">
            <button class="btn icon hamburger" id="hamburger" type="button" aria-label="Open menu">≡</button>
            <a class="btn" href="{MAIN}" rel="noopener noreferrer" target="_blank">Official Cazilla</a>
            <a class="btn primary" href="{MAIN}" rel="noopener noreferrer" target="_blank">Play at Cazilla</a>
          </div>"""


def compliance_block(*, depth: int) -> str:
    prefix = "../" * depth
    ck = f"{prefix}cookie-policy/" if depth else "cookie-policy/"
    return f"""<div class="complianceOverlay" id="ageGate" role="dialog" aria-modal="true" aria-labelledby="ageTitle">
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
    <p>We use cookies to remember your age check. See <a href="{ck}">cookie policy</a>.</p>
    <div class="complianceActions">
      <button type="button" class="btn" id="cookieReject">Essential only</button>
      <button type="button" class="btn primary" id="cookieAccept">Accept</button>
    </div>
  </div>
</div>"""


def footer_legal(*, depth: int) -> str:
    p = "../" * depth
    links = [
        ("user-agreement/", "User agreement"),
        ("cookie-policy/", "Cookie policy"),
        ("fair-play/", "Fair play"),
        ("payments-withdrawals/", "Payments &amp; withdrawals"),
        ("privacy-policy/", "Privacy policy"),
        ("responsible-gambling/", "Responsible gambling"),
        ("aml-kyc/", "AML &amp; KYC"),
    ]
    parts = [f'            <a href="{p}{u}">{lab}</a>' for u, lab in links]
    return (
        '          <nav class="footerLegal" aria-label="Legal pages">\n'
        + "\n".join(parts)
        + "\n          </nav>"
    )


def landing_page(
    rel: str,
    page_key: str,
    title: str,
    description: str,
    h1: str,
    h2a: str,
    h2b: str,
    h2c: str,
    h3a: str,
    h3b: str,
    h3c: str,
) -> str:
    depth = 0
    canonical = f"{ORIGIN}/" if rel == "index.html" else f"{ORIGIN}/{rel}"
    og_path = canonical
    body_cls = ""
    script = "assets/r2-site.js"
    css_p = "assets/"
    ribbon = (
        '<p class="trustRibbon"><span class="stars" aria-hidden="true">★★★★☆</span>'
        "<span><strong>Independent Cazilla review</strong> for Ireland (en-IE). "
        "Editorial player feedback style hub — we do not operate a casino.</span></p>"
    )
    stub = "Editorial placeholder. A2 will replace this block with Ireland-facing review copy."
    return f"""<!doctype html>
<html lang="en-IE" data-min-gambling-age="18">
  <head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}" />
<meta name="robots" content="index, follow" />
<link rel="canonical" href="{html.escape(canonical)}" />
<link rel="alternate" hreflang="en-IE" href="{html.escape(og_path)}" />
<link rel="alternate" hreflang="x-default" href="{html.escape(og_path)}" />
<meta property="og:title" content="{html.escape(title)}" />
<meta property="og:description" content="{html.escape(description)}" />
<meta property="og:image" content="{ORIGIN}/assets/pictures/og-logo.svg" />
<meta property="og:url" content="{html.escape(og_path)}" />
<meta property="og:type" content="website" />
<meta property="og:locale" content="en_IE" />
<meta name="twitter:card" content="summary_large_image" />
<script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "WebSite",
    "name": "Cazilla Insight Reviews",
    "url": "{ORIGIN}/"
  }}
</script>
<link rel="stylesheet" href="{css_p}r2-shell.css" />
<link rel="stylesheet" href="{css_p}r2-page.css" />
<link rel="stylesheet" href="{css_p}r2-compliance.css" />
  </head>
  <body class="{body_cls}">
{compliance_block(depth=depth)}
<div id="siteContent" class="app">
      <main class="main" id="top">
        <header class="topbar">
          <div class="topbarLeft">
            <a class="logoText" href="index.html" aria-label="Cazilla review home"><span class="tpDot" aria-hidden="true"></span><span class="logoWord">CAZILLA INSIGHT</span></a>
          </div>
          <nav class="navLinks" id="mainNav" aria-label="Main navigation">
{nav_html(rel, depth=depth)}
          </nav>
{actions_html(depth=depth)}
        </header>

{ribbon}

        <section class="hero" aria-label="Hero">
          <div class="heroInner">
            <h1>{html.escape(h1)}</h1>
            <p class="subtitle">{stub}</p>
            <div class="disclaimerBar">18+ only. Gambling involves risk. Use licensed operators.</div>
            <div class="heroActions">
              <a class="btn primary" href="{MAIN}" rel="noopener noreferrer" target="_blank">Open Cazilla</a>
            </div>
          </div>
        </section>

        <div class="reviewBodyGrid">
        <section id="bonuses" class="sectionCard">
          <div class="sectionHead"><h2>{h2a}</h2></div>
          <h3>{h3a}</h3>
          <p class="subtitle">{stub}</p>
        </section>

        <section id="games" class="sectionCard">
          <div class="sectionHead"><h2>{h2b}</h2></div>
          <h3>{h3b}</h3>
          <p class="subtitle">{stub}</p>
        </section>

        <section id="about" class="sectionCard">
          <div class="sectionHead"><h2>{h2c}</h2></div>
          <h3>{h3c}</h3>
          <p class="subtitle">{stub}</p>
        </section>
        </div>

        <footer class="footer" id="footer">
          <div class="sectionHead">
            <h2>Policies and disclosures</h2>
          </div>
{footer_legal(depth=depth)}
          <p class="fineprint">{stub}</p>
          <p class="fineprint">© <span id="year">2026</span> Cazilla Insight. <a href="cookie-policy/">Cookie policy</a></p>
        </footer>
      </main>
    </div>
    <script src="{script}" defer></script>
  </body>
</html>
"""


LANDINGS = [
    (
        "index.html",
        "home",
        "Online casino Cazilla review, real money IE guide.",
        "Casino online Ireland Cazilla review, paypal paths and best online casino offers we explain calmly today!",
        "Online casino Cazilla review hub for Ireland",
        "Bonuses And Offers Through A Player Review Lens",
        "Games And Payments Irish Readers Ask About",
        "How This Cazilla Review Page Stays Independent",
        "Welcome packages in context",
        "Live tables and RNG libraries",
        "Editorial standards we follow",
    ),
    (
        "casino-games.html",
        "casino-games",
        "Casino online games Cazilla review, IE lobby tips!",
        "Online casino game Ireland Cazilla review, online casino games depth and casino games online notes!",
        "Casino online games Cazilla review for Ireland",
        "Online Casino Game Libraries We Compare",
        "Casino Games Online With Clear Ireland Notes",
        "Why Live And RNG Titles Matter In A Review",
        "Studios and catalogue depth",
        "Mobile play expectations",
        "Signals of a fair lobby",
    ),
    (
        "casino-deposit.html",
        "casino-deposit",
        "Casino online no deposit bonus Cazilla review IE!",
        "Online casino no deposit bonus Ireland Cazilla review, low deposit online casino paths and limits!",
        "Casino deposit Cazilla review for Irish players",
        "No Deposit Online Casino Offers We Decode",
        "Play Online Casino For Real Money Safely",
        "Casino Online No Deposit Bonus Fine Print",
        "Risk-free trials and caps",
        "Bankroll planning after signup",
        "When a low deposit helps testing",
    ),
    (
        "bonus.html",
        "bonus",
        "Online casino bonus Cazilla review, IE codes now!",
        "Casino bonus online Ireland Cazilla review, online casino welcome bonus and online casino bonus codes!",
        "Online casino bonus Cazilla review snapshot",
        "Online Casino Welcome Bonus Structures",
        "Online Casino Bonus Offers We Compare",
        "Online Casino Bonus Codes Without Hype",
        "Wagering and game weighting",
        "Reloads and loyalty angles",
        "Reading tables like a reviewer",
    ),
    (
        "about.html",
        "about",
        "Irish online casino Cazilla review, best IE picks!",
        "Best irish online casino Cazilla review, online casino best signals and best casino online clarity!",
        "About this Irish online casino Cazilla review desk",
        "Best Irish Online Casino Signals We Track",
        "Best Irish Casino Online Through Player Stories",
        "Top Online Casino Lists Stay Editorial Here",
        "Licensing checks we repeat",
        "Support tests we run",
        "How Ireland rules shape our pages",
    ),
]


def inner_shell(
    *,
    folder: str,
    title: str,
    description: str,
    h1: str,
    body_html: str,
    hero_subtitle: str,
) -> str:
    depth = 1
    canonical = f"{ORIGIN}/{folder}/"
    script = "../assets/r2-site.js"
    css_p = "../assets/"
    ribbon = (
        '<p class="trustRibbon"><span class="stars" aria-hidden="true">★★★★☆</span>'
        "<span><strong>Independent Cazilla review</strong> — legal information for Ireland readers.</span></p>"
    )
    return f"""<!doctype html>
<html lang="en-IE" data-min-gambling-age="18">
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
<meta property="og:image" content="{ORIGIN}/assets/pictures/og-logo.svg" />
<meta property="og:url" content="{html.escape(canonical)}" />
<meta property="og:type" content="website" />
<meta property="og:locale" content="en_IE" />
<link rel="stylesheet" href="{css_p}r2-shell.css" />
<link rel="stylesheet" href="{css_p}r2-page.css" />
<link rel="stylesheet" href="{css_p}r2-compliance.css" />
  </head>
  <body class="innerPage">
{compliance_block(depth=depth)}
<div id="siteContent" class="app">
      <main class="main" id="top">
<header class="topbar">
  <div class="topbarLeft">
    <a class="logoText" href="../index.html" aria-label="Cazilla review home"><span class="tpDot" aria-hidden="true"></span><span class="logoWord">CAZILLA INSIGHT</span></a>
  </div>
  <nav class="navLinks" id="mainNav" aria-label="Main navigation">
{nav_html(None, depth=1)}
  </nav>
{actions_html(depth=1)}
</header>
{ribbon}
<section class="hero" aria-label="Hero">
  <div class="heroInner">
    <h1>{html.escape(h1)}</h1>
    <p class="subtitle">{html.escape(hero_subtitle)}</p>
  </div>
</section>

{body_html}

<p class="fineprint" style="margin: 24px 22px"><a href="../index.html">Back to home</a></p>

      </main>
    </div>
    <script src="{script}" defer></script>
  </body>
</html>
"""


def tech_body(slug: str) -> str:
    """Editorial policy copy for Ireland-facing readers (no keyword stuffing, no duplicate filler)."""

    wrap = (
        lambda inner: '<article class="sectionCard" style="margin: 22px; max-width: 1180px; margin-left: auto; margin-right: auto">'
        f"{inner}</article>"
    )

    blocks: dict[str, str] = {
        "privacy-policy": """
<p>Cazilla Insight is an independent review and information site. This page explains, in everyday language, what personal data we may process when you use the site and what choices you have. It is not legal advice; if you need advice about your situation, speak to a qualified professional.</p>
<div class="sectionHead"><h2>Who this applies to</h2></div>
<p>These notes apply to visitors who browse our pages from Ireland or elsewhere. We do not run a gambling service: we do not take bets, hold player balances, or operate a casino cashier. Any account you open is with a licensed operator under their terms.</p>
<div class="sectionHead"><h2>What we may collect</h2></div>
<p>Depending on how you use the site, we or our hosting and analytics providers may process technical data such as your IP address (often truncated), browser type, device type, coarse location derived from the network, pages viewed, and timestamps. If you contact us, we process what you choose to send (for example your email address and message text).</p>
<p>Our age and cookie prompts may store a small preference in your browser so we do not ask on every visit. Details are in our <a href="../cookie-policy/">cookie policy</a>.</p>
<div class="sectionHead"><h2>Why we use data</h2></div>
<p>We use this information to keep the site secure, to understand which articles are useful, to fix errors, and to respond to messages you send us. We do not sell email lists to unrelated marketers, and we keep optional contact data only as long as we need it to reply or to meet a legal obligation.</p>
<div class="sectionHead"><h2>Your rights (GDPR / Ireland)</h2></div>
<p>If EU data protection law applies, you may have rights including access, correction, deletion, restriction, objection, and portability in certain cases. You may also complain to the Irish Data Protection Commission (<abbr title="Data Protection Commission">DPC</abbr>). For requests about data we control as publisher, contact us using the details given on the site; allow reasonable time for verification.</p>
<div class="sectionHead"><h2>Operators hold your gaming data</h2></div>
<p>If you register with a brand we write about, that operator processes your gaming, payment, and verification data under their own privacy notice. Read their policy and support channels for access or deletion requests relating to your player account.</p>
""",
        "cookie-policy": """
<p>This page describes how Cazilla Insight uses cookies and similar technologies. It is meant to help you make an informed choice alongside your browser settings.</p>
<div class="sectionHead"><h2>What we use cookies for</h2></div>
<p>We group technologies into a small number of practical categories:</p>
<h3>Essential</h3>
<p>These keep the site working safely: for example remembering that you passed the age check, maintaining security-related headers, and (where applicable) load balancing. They are not used to profile you for marketing.</p>
<h3>Analytics</h3>
<p>We may use analytics to see aggregate traffic (popular pages, rough devices, approximate geography). Where possible we prefer privacy-preserving or aggregated configurations.</p>
<h3>Optional marketing</h3>
<p>Marketing or advertising tags stay off unless you accept them in the banner. You can change your mind later by clearing site data for this domain or using the controls we provide when available.</p>
<div class="sectionHead"><h2>How long choices are remembered</h2></div>
<p>When you accept or reject non-essential cookies, we store that choice for a limited period so you are not interrupted on every visit. After it expires, we may ask again so your preference stays up to date.</p>
<div class="sectionHead"><h2>Your controls</h2></div>
<p>You can block or delete cookies in your browser settings. Doing so may affect how the age gate or preference storage behaves. For more on personal data, see our <a href="../privacy-policy/">privacy policy</a>.</p>
""",
        "user-agreement": """
<p>By using Cazilla Insight you agree to the following editorial terms. If you do not agree, please stop using the site.</p>
<div class="sectionHead"><h2>What this site is</h2></div>
<p>Cazilla Insight publishes reviews and explanatory articles about remote gambling products aimed primarily at adults in Ireland. We aim to be accurate and fair at the time of writing, but offers, rules, and interfaces change. Always confirm critical details on the operator's official site before you deposit or play.</p>
<div class="sectionHead"><h2>Acceptable use</h2></div>
<p>Do not attempt to disrupt the site, scrape it in a way that harms performance, or misuse any forms or contact paths. Do not use our pages to harass staff of operators or other readers.</p>
<div class="sectionHead"><h2>Outbound links and commercial relationships</h2></div>
<p>Some outbound links may use standard referral parameters used in publishing. Commercial relationships do not change our obligation to describe drawbacks as well as benefits. Where we have a material connection, we aim to present it clearly in context.</p>
<div class="sectionHead"><h2>No warranty</h2></div>
<p>Content is provided "as is" for general information. We are not responsible for losses arising from reliance on our summaries, from third-party sites, or from gambling activity you choose to undertake. Gambling can be addictive: only play with money you can afford to lose and use operator tools and national support services if you need help.</p>
<div class="sectionHead"><h2>Changes</h2></div>
<p>We may update these terms occasionally. Continued use after changes are posted means you accept the revised version. Material changes will be reflected on this page with a reasonable update note where practicable.</p>
""",
        "fair-play": """
<p>This statement describes how we approach editorial fairness when we review Cazilla and related topics for Irish readers.</p>
<div class="sectionHead"><h2>Independence</h2></div>
<p>Our reviewers are not employees of the brands we cover. We pay for our own test accounts where practical, and we do not accept payment to remove factual criticism.</p>
<div class="sectionHead"><h2>What we check</h2></div>
<p>Typical review work includes: licence and safer-gambling messaging visible on the product, clarity of bonus terms, game catalogue and lobby behaviour, payment and withdrawal paths, and how customer support answers routine questions.</p>
<div class="sectionHead"><h2>Corrections</h2></div>
<p>If we discover a factual error, we correct it and note the fix when the mistake could mislead readers about money, safety, or legality. For minor wording or layout updates we may edit without a separate notice.</p>
<div class="sectionHead"><h2>Disagreement between reviewers</h2></div>
<p>When two reviewers reach different conclusions, we re-run the disputed flow, compare evidence, and publish the more conservative takeaway so readers see the safer interpretation.</p>
""",
        "payments-withdrawals": """
<p>This page summarises how deposits and withdrawals usually work at licensed remote gambling sites. It is educational only: timelines and methods depend on the operator, your verification status, and the payment rail you choose.</p>
<div class="sectionHead"><h2>Common payment methods (Ireland)</h2></div>
<p>Many Irish-facing brands support debit cards, bank transfer, and widely used e-wallets. Some also support mobile payment or voucher products. Availability, fees, and limits are set in the operator's cashier, not on this site.</p>
<div class="sectionHead"><h2>Why payouts are sometimes delayed</h2></div>
<p>First-time withdrawals often trigger identity checks. Larger amounts may need extra review. Weekends, public holidays, manual fraud checks, and "pending" windows in the cashier can all add time before funds reach your bank or wallet.</p>
<div class="sectionHead"><h2>What we publish in reviews</h2></div>
<p>When we quote ranges or typical speeds, we describe patterns we have seen in testing or in public documentation. They are not guarantees. Always read the operator's withdrawal policy and verify KYC requirements before you play.</p>
""",
        "aml-kyc": """
<p>Anti-money laundering (<abbr title="Anti-money laundering">AML</abbr>) and know-your-customer (<abbr title="Know your customer">KYC</abbr>) rules are legal obligations on licensed operators. This page explains the ideas in plain language for readers in Ireland.</p>
<div class="sectionHead"><h2>Why operators ask for ID</h2></div>
<p>Licensed venues must know who their customers are. You will usually be asked for proof of identity and address before large withdrawals or once cumulative activity crosses thresholds defined in law and in the operator's terms.</p>
<div class="sectionHead"><h2>Source of funds</h2></div>
<p>When risk checks flag unusual patterns, an operator may ask how you fund your play (for example employment income, savings, or a recent sale). That can feel intrusive, but it is part of how regulated firms detect crime and protect vulnerable customers.</p>
<div class="sectionHead"><h2>What we do on this site</h2></div>
<p>Cazilla Insight does not verify your identity and does not process gambling transactions. Only the operator's compliance team can tell you exactly which documents they need. Use official support channels if you are unsure what to upload.</p>
""",
        "responsible-gambling": """
<p>Gambling should be entertainment, not a way to solve money problems. If it stops feeling that way, pause and talk to someone you trust or a professional support service.</p>
<div class="sectionHead"><h2>National support (Ireland)</h2></div>
<p>Free, confidential help is available through <a href="https://www.gamblingcare.ie/" rel="noopener noreferrer">GamblingCare.ie</a> (including the National Gambling Helpline) and through resources published by the <a href="https://www.grai.ie/" rel="noopener noreferrer">Gambling Regulatory Authority of Ireland</a>. Citizens Information also summarises <a href="https://www.citizensinformation.ie/en/health/health-services/addiction-treatment-services/help-for-gambling-addiction/" rel="noopener noreferrer">treatment and support options</a>.</p>
<div class="sectionHead"><h2>Tools on licensed sites</h2></div>
<p>Reputable operators offer deposit limits, reality checks, time-outs, and self-exclusion. Turn them on before you play, not after losses mount.</p>
<div class="sectionHead"><h2>Warning signs</h2></div>
<p>Chasing losses, borrowing to gamble, hiding activity from family, or feeling anxious when you try to stop are all signals to seek help immediately. This editorial site cannot provide crisis counselling; use the helpline and clinical routes above.</p>
""",
    }
    inner = blocks.get(slug)
    if inner is None:
        inner = "<p>Content for this policy page is not configured.</p>"
    return wrap(inner.strip())


TECH_SPECS: list[tuple[str, str, str, str, str]] = [
    (
        "user-agreement",
        "User agreement | Cazilla Insight",
        "Terms for using this independent Cazilla review site: acceptable use, outbound links, and limits of our editorial content for Ireland.",
        "User agreement for the Cazilla Insight review hub",
        "Rules for using this hub and what we do not guarantee — not legal advice.",
    ),
    (
        "cookie-policy",
        "Cookie policy | Cazilla Insight",
        "How Cazilla Insight uses cookies and similar technologies for essential functions, analytics, and optional marketing on this Ireland-facing review site.",
        "Cookie policy for Ireland readers on this review hub",
        "What cookies we use, why they matter, and how you can control them.",
    ),
    (
        "fair-play",
        "Fair play | Cazilla Insight",
        "How we keep Cazilla reviews fair: independence, what we test, corrections, and what happens when reviewers disagree.",
        "Fair play statement for our Cazilla reviews",
        "How we stay independent and what we do when facts or conclusions differ.",
    ),
    (
        "payments-withdrawals",
        "Payments & withdrawals | Cazilla Insight",
        "Editorial overview of deposits and payouts for Irish players: typical methods, why withdrawals can be delayed, and why cashier rules live with the operator.",
        "Payments and withdrawals overview for Irish readers",
        "How Irish players usually move money on licensed sites — timelines vary by operator.",
    ),
    (
        "privacy-policy",
        "Privacy policy | Cazilla Insight",
        "How we handle personal data on this Cazilla review hub for Ireland: what we collect, why, your GDPR rights, and where operator privacy notices apply.",
        "Privacy policy for the Cazilla Insight review hub",
        "Plain-language overview of data on this editorial site — not legal advice.",
    ),
    (
        "responsible-gambling",
        "Responsible gambling | Cazilla Insight",
        "Safer play resources for Ireland: national support services, self-exclusion and limits on licensed sites, and when to seek help.",
        "Responsible gambling resources for Ireland",
        "Where Irish players can get help and which safer-gambling tools to use first.",
    ),
    (
        "aml-kyc",
        "AML & KYC | Cazilla Insight",
        "Plain-language explainer on identity checks and source-of-funds requests at licensed operators — not legal advice for your case.",
        "AML and KYC explainer for Ireland-facing readers",
        "Why licensed brands ask for ID and proof of funds — overview only.",
    ),
]


def write_technical_pages_only() -> None:
    """Regenerate policy HTML only (does not overwrite landing pages or .htaccess)."""
    for folder, title, desc, h1, hero_sub in TECH_SPECS:
        d = SITE / folder
        d.mkdir(parents=True, exist_ok=True)
        body = tech_body(folder)
        (d / "index.html").write_text(
            inner_shell(
                folder=folder,
                title=title,
                description=desc,
                h1=h1,
                body_html=body,
                hero_subtitle=hero_sub,
            ),
            encoding="utf-8",
        )
    print("Wrote technical pages only ->", SITE)


def main() -> None:
    SITE.mkdir(parents=True, exist_ok=True)
    for item in LANDINGS:
        rel = item[0]
        (SITE / rel).write_text(landing_page(*item), encoding="utf-8")

    for folder, title, desc, h1, hero_sub in TECH_SPECS:
        d = SITE / folder
        d.mkdir(parents=True, exist_ok=True)
        body = tech_body(folder)
        (d / "index.html").write_text(
            inner_shell(
                folder=folder,
                title=title,
                description=desc,
                h1=h1,
                body_html=body,
                hero_subtitle=hero_sub,
            ),
            encoding="utf-8",
        )

    ht = """RewriteEngine On
RewriteCond %{HTTPS} off
RewriteRule ^ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]
RewriteCond %{HTTP_HOST} ^www\\.(.+)$ [NC]
RewriteRule ^ https://%1%{REQUEST_URI} [L,R=301]
RewriteRule ^index\\.html$ / [L,R=301]
"""
    (SITE / ".htaccess").write_text(ht, encoding="utf-8")
    print("Wrote landing pages, technical pages, .htaccess ->", SITE)


if __name__ == "__main__":
    import sys

    if "--tech-only" in sys.argv:
        raise SystemExit(write_technical_pages_only() or 0)
    raise SystemExit(main())
