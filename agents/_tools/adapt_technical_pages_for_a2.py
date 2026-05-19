#!/usr/bin/env python3
"""Adapt review/offerwall technical HTML shells for A2 apply_content_to_technical_html()."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_AGENTS = ROOT / "agents"
if str(_AGENTS) not in sys.path:
    sys.path.insert(0, str(_AGENTS))

from _lib.locale_context import legal_subtitle_fallback, locale_context_from_env  # noqa: E402
from _lib.repo_env import load_dotenv_file  # noqa: E402
_SITES = (
    "cazilla-review1-en-ie",
    "cazilla-review2-en-ie",
    "cazilla-review3-en-ie",
    "cazilla-offerwall1-en-ie",
    "cazilla-offerwall2-en-ie",
    "cazilla-offerwall1-fr-be",
)
_TECH_IDS = (
    "user-agreement",
    "cookie-policy",
    "fair-play",
    "payments-withdrawals",
    "privacy-policy",
    "responsible-gambling",
    "aml-kyc",
)

_POLICY_CARD_CSS = """
/* A2 technical pages: policy body container */
body.innerPage .policyCard,
body.lv-body .policyCard {
  max-width: 1180px;
  margin: 22px auto;
  padding: 0 22px;
}
body.innerPage .policyCard .sectionCard,
body.lv-body .policyCard .sectionCard {
  margin: 0;
}
body.innerPage .policyCard p,
body.lv-body .policyCard p,
body.innerPage .policyCard .ow-prose p {
  margin: 0 0 12px;
  line-height: 1.7;
  color: #334155;
}
body.innerPage .policyCard .sectionHead h2,
body.lv-body .policyCard h2 {
  margin-top: 18px;
}
body.innerPage .policyCard h3,
body.lv-body .policyCard h3 {
  margin: 14px 0 8px;
  font-size: 15px;
}
"""

_BACK_LINK = '<p class="fineprint" style="margin: 24px 0"><a href="../index.html">Back to home</a></p>'


def _ensure_inner_page(html: str) -> str:
    if re.search(r"(?is)<body[^>]*\binnerPage\b", html):
        return html
    if re.search(r'(?is)<body\s+class="([^"]*)"', html):
        return re.sub(
            r'(?is)(<body\s+class=")([^"]*)(")',
            lambda m: f'{m.group(1)}{m.group(2)} innerPage{m.group(3)}',
            html,
            count=1,
        )
    return re.sub(r"(?is)<body(\s|>)", r'<body class="innerPage"\1', html, count=1)


def _has_back_fineprint(html: str) -> bool:
    return bool(re.search(r'(?is)<p\s+class="fineprint"[^>]*>[\s\S]*?Back to home', html))


def _insert_back_fineprint(html: str) -> str:
    if _has_back_fineprint(html):
        return html
    for pat in (r'(\s*)(<footer\s+class="ow-footer")', r"(\s*)(<footer\b)"):
        if re.search(pat, html):
            return re.sub(pat, f"\n        {_BACK_LINK}\n\\1\\2", html, count=1)
    return html


def _adapt_offerwall(html: str) -> str:
    if "ow-hero" in html and not re.search(r"(?is)ow-hero[^\"]*\bhero\b", html):
        html = re.sub(
            r'<section\s+class="ow-hero"',
            '<section class="ow-hero hero" aria-label="Hero"',
            html,
            count=1,
        )
    if 'class="ow-lead subtitle"' not in html:
        html = re.sub(r'<p\s+class="ow-lead"', '<p class="ow-lead subtitle"', html, count=1)
    if "policyCard" not in html:
        m = re.search(r"(?is)(<article\s+class=\"ow-prose\"[^>]*>.*?</article>)", html)
        if m:
            html = (
                html[: m.start()]
                + f'<div class="policyCard">\n{m.group(1)}\n</div>\n'
                + html[m.end() :]
            )
            
    return _insert_back_fineprint(html)


def _adapt_review_article(html: str) -> str:
    if "policyCard" in html:
        return html
    m = re.search(
        r'(?is)(<article\s+class="sectionCard"[^>]*>.*?</article>)\s*(<p\s+class="fineprint")',
        html,
    )
    if not m:
        return html
    return (
        html[: m.start(1)]
        + f'<div class="policyCard">\n{m.group(1)}\n</div>\n'
        + m.group(2)
        + html[m.end(2) :]
    )


def _adapt_review_multi(html: str) -> str:
    if "policyCard" in html:
        return html
    m = re.search(
        r'(?is)(<section\s+class="hero"[^>]*>.*?</section>)\s*(.*?)\s*(<p\s+class="fineprint"[^>]*>\s*<a[^>]+>Back to home)',
        html,
    )
    if not m or not m.group(2).strip():
        return html
    return (
        html[: m.start()]
        + m.group(1)
        + f'\n<div class="policyCard">\n{m.group(2).strip()}\n</div>\n'
        + m.group(3)
        + html[m.end() :]
    )


def _adapt_review_stub(html: str) -> str:
    if "policyCard" in html and _has_back_fineprint(html):
        return html
    m = re.search(
        r'(?is)<section\s+class="sectionCard"[^>]*>\s*<h1>(.*?)</h1>\s*(.*?)</section>',
        html,
    )
    if not m:
        return html
    h1, rest = m.group(1).strip(), m.group(2).strip()
    sub_m = re.search(r'(?is)^\s*<p\s+class="subtitle"[^>]*>(.*?)</p>', rest)
    env = load_dotenv_file(ROOT / ".env")
    lc = locale_context_from_env(env, strict_keywords_match=False)
    subtitle = sub_m.group(1).strip() if sub_m else legal_subtitle_fallback(lc)
    body_rest = rest[sub_m.end() :] if sub_m else rest
    hero = (
        f'<section class="hero" aria-label="Hero">\n'
        f'  <div class="heroInner">\n'
        f"    <h1>{h1}</h1>\n"
        f'    <p class="subtitle">{subtitle}</p>\n'
        f"  </div>\n"
        f"</section>\n"
    )
    if body_rest.strip():
        card = f'<section class="sectionCard" style="margin-top: 22px">{body_rest}</section>'
    else:
        card = (
            '<article class="sectionCard" style="margin: 22px; max-width: 1180px; '
            'margin-left: auto; margin-right: auto"><p>Editorial legal content.</p></article>'
        )
    block = f'{hero}<div class="policyCard">\n{card}\n</div>\n{_BACK_LINK}\n'
    return html[: m.start()] + block + html[m.end() :]


def adapt_html(html: str, site_slug: str) -> str:
    html = _ensure_inner_page(html)
    if "offerwall" in site_slug:
        html = _adapt_offerwall(html)
    elif re.search(r'(?is)<section\s+class="hero"', html) and re.search(
        r'(?is)<article\s+class="sectionCard"', html
    ):
        html = _adapt_review_article(html)
        if "policyCard" not in html:
            html = _adapt_review_multi(html)
    elif re.search(r'(?is)<section\s+class="hero"', html):
        html = _adapt_review_multi(html)
    elif re.search(r'(?is)<article\s+class="sectionCard"', html):
        html = _adapt_review_article(html)
    elif re.search(r'(?is)<section\s+class="sectionCard"[^>]*>\s*<h1>', html):
        html = _adapt_review_stub(html)
    return _insert_back_fineprint(html)


def append_policy_css(site_dir: Path) -> None:
    for name in ("page.css", "r2-page.css", "r3-page.css", "shell.css"):
        css = site_dir / "assets" / name
        if not css.is_file():
            continue
        text = css.read_text(encoding="utf-8", errors="replace")
        if ".policyCard" in text:
            return
        css.write_text(text.rstrip() + "\n" + _POLICY_CARD_CSS, encoding="utf-8")
        print(f"  CSS: {css.relative_to(ROOT)}")
        return


def main() -> int:
    updated = 0
    for slug in _SITES:
        site = ROOT / "sites" / slug
        kw_path = site / "_output" / "keywords.json"
        if not kw_path.is_file():
            print(f"SKIP {slug}: no keywords.json")
            continue
        data = json.loads(kw_path.read_text(encoding="utf-8"))
        paths = [
            str(e.get("path") or "").strip().lstrip("/")
            for e in (data.get("technical_pages") or [])
            if str(e.get("path") or "").strip()
        ] or [f"{tid}/index.html" for tid in _TECH_IDS]
        print(f"=== {slug} ===")
        append_policy_css(site)
        for rel in paths:
            hp = site / rel
            if not hp.is_file():
                print(f"  MISSING {rel}")
                continue
            raw = hp.read_text(encoding="utf-8", errors="replace")
            new = adapt_html(raw, slug)
            if new != raw:
                hp.write_text(new, encoding="utf-8")
                print(f"  UPDATED {rel}")
                updated += 1
            else:
                print(f"  ok {rel}")
    print(f"Done. {updated} HTML file(s) updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
