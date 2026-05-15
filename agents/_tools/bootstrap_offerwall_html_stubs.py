#!/usr/bin/env python3
"""
Write minimal offerwall HTML stubs (ow-hero + ow-prose + footer-legal) so A2 can
apply_content_to_offerwall_html. Content paths come from keywords pages[] only; legal and
cookie-policy stubs use a fixed path list and do not read technical_pages keywords.

Usage (from repo root, with .env):
  python3 agents/_tools/bootstrap_offerwall_html_stubs.py --site-dir sites/cazilla-offerwall2-en-ie
"""
from __future__ import annotations

import argparse
import html as html_lib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    return env


def _first_kw(page: dict) -> str:
    rows = page.get("keywords") or []
    if isinstance(rows, list) and rows:
        k = rows[0].get("keyword") if isinstance(rows[0], dict) else None
        if k:
            return str(k).strip()
    return "Online casino"


def _title_from_kw(kw: str, max_len: int = 58) -> str:
    base = kw[:1].upper() + kw[1:] if kw else "Casino"
    tail = " — Cazilla IE review"
    t = base + tail
    if len(t) > max_len:
        t = base[: max(12, max_len - len(tail) - 3)].rstrip() + "…" + tail
    return t[:max_len]


def _desc_from_kw(kw: str) -> str:
    s = (
        f"Editorial Cazilla review for Ireland: {kw}. "
        "Bonuses, games, payments, and safer play for 18+ readers."
    )
    return s[:138] if len(s) > 138 else s


def _depth(rel: str) -> int:
    return len(Path(rel).parts) - 1


def _ap(rel: str) -> str:
    return "../" * _depth(rel)


def _canonical(site_origin: str, rel: str) -> str:
    site_origin = site_origin.rstrip("/")
    if rel == "index.html":
        return f"{site_origin}/"
    if rel.endswith("/index.html"):
        seg = rel[: -len("index.html")].rstrip("/")
        return f"{site_origin}/{seg}/"
    return f"{site_origin}/{rel}"


def _shell(
    *,
    rel: str,
    site_origin: str,
    title: str,
    description: str,
    include_agg: bool,
    main_casino_url: str,
    hero_h1: str,
    hero_lead: str,
    prose_inner: str,
    footer_legal_inner: str,
) -> str:
    ap = _ap(rel)
    can = _canonical(site_origin, rel)
    esc_t = html_lib.escape(title)
    esc_d = html_lib.escape(description)
    esc_can = html_lib.escape(can)
    esc_h1 = html_lib.escape(hero_h1)
    esc_lead = hero_lead  # may contain safe HTML (CTA link)
    og_img = html_lib.escape(f"{site_origin.rstrip('/')}/assets/pictures/og-logo.svg", quote=True)
    agg_block = ""
    if include_agg:
        agg_block = (
            '<section id="ow-aggregator-top5" class="ow-aggregatorTop5" aria-label="Top five picks"></section>\n'
        )
    return f"""<!doctype html>
<html lang="en-IE">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{esc_t}</title>
    <meta name="description" content="{esc_d}" />
    <meta name="robots" content="index, follow" />
    <link rel="canonical" href="{esc_can}" />
    <link rel="alternate" hreflang="en-IE" href="{esc_can}" />
    <link rel="alternate" hreflang="x-default" href="{esc_can}" />
    <meta property="og:title" content="{esc_t}" />
    <meta property="og:description" content="{esc_d}" />
    <meta property="og:image" content="{og_img}" />
    <script type="application/ld+json">
      {{"@context":"https://schema.org","@type":"WebSite","name":"Cazilla IE","url":"{html_lib.escape(site_origin.rstrip("/"), quote=True)}"}}
    </script>
    <link rel="stylesheet" href="{ap}assets/shell.css" />
    <link rel="stylesheet" href="{ap}assets/compliance.css" />
    <link rel="stylesheet" href="{ap}assets/offerwall-nav.css" />
  </head>
  <body class="lv-body">
    <div class="complianceOverlay" id="ageGate" role="dialog" aria-modal="true" aria-labelledby="ageTitle">
      <div class="complianceDialog">
        <h2 id="ageTitle">Confirm you are 18 or over</h2>
        <p>
          This site discusses regulated gambling topics for Ireland. Irish law sets the minimum gambling age at 18. You must be at least 18 to continue. If you are not 18 yet, please leave this page.
        </p>
        <div class="complianceActions">
          <button type="button" class="btn" id="ageUnder">I am under 18</button>
          <button type="button" class="btn primary" id="ageOk">I am 18 or over</button>
        </div>
      </div>
    </div>
    <div class="complianceOverlay" id="cookieGate" hidden aria-hidden="true" role="dialog" aria-modal="true" aria-labelledby="cookieTitle">
      <div class="complianceDialog">
        <h2 id="cookieTitle">Cookie preferences</h2>
        <p>
          We use cookies to remember your age check and to measure basic traffic. See <a class="inTextLink" href="#footer-legal">Cookie policy</a> in the footer on this page.
        </p>
        <div class="complianceActions">
          <button type="button" class="btn" id="cookieReject">Essential only</button>
          <button type="button" class="btn primary" id="cookieAccept">Accept</button>
        </div>
      </div>
    </div>

    <div id="siteContent">
      <header class="ow-topbar">
        <a class="ow-brand" href="{ap}index.html" aria-label="Cazilla IE home">
          <img src="{ap}assets/pictures/og-logo.svg" alt="" width="34" height="34" decoding="async" />
        </a>
      </header>
      <button type="button" class="ow-menuBtn" id="menuToggle" aria-expanded="false" aria-controls="sideDrawer">Menu</button>
      <div class="ow-drawerOverlay" id="drawerOverlay" hidden></div>
      <aside class="ow-drawer" id="sideDrawer" aria-hidden="true" aria-label="Site menu">
        <div class="ow-drawerHeader">
          <span class="ow-drawerTitle">Pages</span>
          <button type="button" class="ow-drawerClose" id="drawerClose" aria-label="Close menu">×</button>
        </div>
        <nav class="ow-drawerNav" aria-label="Site pages">
          <a class="ow-navAnchor" href="{ap}index.html">Home</a>
        </nav>
      </aside>

      <main class="ow-main" id="top">
        <section class="ow-hero">
          <h1>{esc_h1}</h1>
          <p class="ow-lead">
            {esc_lead}
          </p>
        </section>
{agg_block}
        <article class="ow-prose">
{prose_inner}
        </article>

        <footer class="ow-footer" id="footer">
          <nav class="ow-footerLegal" aria-label="Legal pages">
            <a href="{ap}user-agreement/">User agreement</a>
            <a href="{ap}privacy-policy/">Privacy policy</a>
            <a href="{ap}cookie-policy/">Cookie policy</a>
            <a href="{ap}fair-play/">Fair play</a>
            <a href="{ap}payments-withdrawals/">Payments and withdrawals</a>
            <a href="{ap}responsible-gambling/">Responsible gambling</a>
            <a href="{ap}aml-kyc/">AML and KYC</a>
          </nav>
          <section id="footer-legal">
            <p>{footer_legal_inner}</p>
          </section>
        </footer>
      </main>
    </div>
    <script src="{ap}assets/site.js" defer></script>
  </body>
</html>
"""


def _kw_pages(data: dict) -> list[tuple[str, dict]]:
    """Only pages[]; technical/legal HTML is written from LEGAL_STUBS in main()."""
    out: list[tuple[str, dict]] = []
    for page in data.get("pages") or []:
        if isinstance(page, dict):
            rel = str(page.get("path") or "").strip().lstrip("/")
            if rel:
                out.append((rel, page))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site-dir", type=Path, required=True)
    args = ap.parse_args()
    site_dir = (ROOT / args.site_dir).resolve() if not args.site_dir.is_absolute() else args.site_dir
    env_path = ROOT / ".env"
    env = _load_env(env_path)
    for k, v in env.items():
        os.environ.setdefault(k, v)
    site_origin = (os.getenv("SITE_URL") or "https://example.invalid").strip().rstrip("/")
    main_url = (os.getenv("MAIN_CASINO_URL") or "https://cazilla.casino").strip()

    kw_path = site_dir / "_output" / "keywords.json"
    if not kw_path.exists():
        raise SystemExit(f"Missing {kw_path}")
    data = json.loads(kw_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("keywords.json must be an object (v2)")

    cta = f'<a href="{html_lib.escape(main_url, quote=True)}" rel="noopener noreferrer" target="_blank">Open Cazilla</a>'

    for rel, page in _kw_pages(data):
        kw = _first_kw(page)
        title = _title_from_kw(kw)
        desc = _desc_from_kw(kw)
        label = str(page.get("menu_label") or page.get("id") or "Page").strip()
        hero_h1 = label
        hero_lead = f"Editorial notes for Irish readers (18+). {cta}"
        prose_inner = "          <p>Placeholder body.</p>\n"
        footer_inner = html_lib.escape(
            "Cazilla provides independent editorial comparisons for adults in Ireland. We do not operate a casino. "
            "Gambling involves risk; play responsibly and seek help if you need it."
        )
        include_agg = rel == "index.html" and "offerwall" in site_dir.name.lower()
        doc = _shell(
            rel=rel,
            site_origin=site_origin,
            title=title,
            description=desc,
            include_agg=include_agg,
            main_casino_url=main_url,
            hero_h1=hero_h1,
            hero_lead=hero_lead,
            prose_inner=prose_inner,
            footer_legal_inner=footer_inner,
        )
        out = site_dir / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(doc, encoding="utf-8")
        print("Wrote", out.relative_to(ROOT))

    legal = [
        (
            "user-agreement/index.html",
            "User agreement",
            "This page summarises how you may use this editorial website. It is not legal advice. "
            "For binding terms of any third-party operator, read that operator’s own terms on their official site.",
        ),
        (
            "privacy-policy/index.html",
            "Privacy policy",
            "We process limited technical data to run this site (for example age-check and cookie choices on your device). "
            "We do not sell personal data. Contact details for the publisher should be listed on the main site policy if required.",
        ),
        (
            "cookie-policy/index.html",
            "Cookie policy",
            "This site uses cookies to remember your age check, cookie preference, and basic session needs. "
            "Analytics or similar cookies, if any, are described here; you can revisit choices when prompted.",
        ),
        (
            "fair-play/index.html",
            "Fair play",
            "We describe how licensed operators are expected to present fair games and transparent rules. "
            "Always verify RTP, rules, and dispute procedures on the operator’s official pages before playing.",
        ),
        (
            "payments-withdrawals/index.html",
            "Payments and withdrawals",
            "Payment methods and withdrawal speeds vary by operator and by bank. "
            "Check KYC requirements, limits, and fees on the official cashier pages of any brand you choose.",
        ),
        (
            "responsible-gambling/index.html",
            "Responsible gambling",
            "If gambling stops being fun, pause and seek help. Ireland offers free confidential support for adults affected by gambling harm. "
            "Never chase losses and set strict time and money limits.",
        ),
        (
            "aml-kyc/index.html",
            "AML and KYC",
            "Licensed operators must verify customer identity and monitor transactions for anti-money-laundering compliance. "
            "Expect document checks before large withdrawals.",
        ),
    ]

    for rel, h1, para in legal:
        if (site_dir / rel).exists():
            continue
        title = f"{h1} — Cazilla IE"
        desc = f"{h1} information for readers in Ireland (18+)."
        prose_inner = f"          <p>{html_lib.escape(para)}</p>\n"
        footer_inner = html_lib.escape(
            "Independent editorial site. 18+ only for gambling-related content in Ireland."
        )
        doc = _shell(
            rel=rel,
            site_origin=site_origin,
            title=title[:58],
            description=desc[:135],
            include_agg=False,
            main_casino_url=main_url,
            hero_h1=h1,
            hero_lead=f"Reference information for Irish readers. {cta}",
            prose_inner=prose_inner,
            footer_legal_inner=footer_inner,
        )
        out = site_dir / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(doc, encoding="utf-8")
        print("Wrote legal", out.relative_to(ROOT))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
