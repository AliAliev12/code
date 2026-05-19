#!/usr/bin/env python3
"""
Write minimal offerwall HTML stubs (ow-hero + ow-prose + footer-legal) so A2 can
apply_content_to_offerwall_html.

Reads TARGET_* / SITE_URL / MAIN_CASINO_URL from repo .env.
Content + technical paths from keywords.json (flat .html supported).

Usage (from repo root):
  python3 agents/_tools/bootstrap_offerwall_html_stubs.py --site-dir sites/cazilla-offerwall1-fr-be
"""
from __future__ import annotations

import argparse
import html as html_lib
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_AGENTS = ROOT / "agents"
if str(_AGENTS) not in sys.path:
    sys.path.insert(0, str(_AGENTS))

from _lib.locale_context import LocaleContext, locale_context_from_env  # noqa: E402

ASSET_SRC = ROOT / "sites" / "cazilla-offerwall1-en-ie" / "assets"


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


def _depth(rel: str) -> int:
    return len(Path(rel).parts) - 1


def _ap(rel: str) -> str:
    return "../" * _depth(rel)


def _rel_href(from_rel: str, to_rel: str) -> str:
    base = os.path.dirname(from_rel) or "."
    r = os.path.relpath(to_rel, base).replace("\\", "/")
    if r == ".":
        return Path(to_rel).name
    return r


def _canonical(site_origin: str, rel: str) -> str:
    site_origin = site_origin.rstrip("/")
    if rel == "index.html":
        return f"{site_origin}/"
    if rel.endswith("/index.html"):
        seg = rel[: -len("index.html")].rstrip("/")
        return f"{site_origin}/{seg}/"
    return f"{site_origin}/{rel}"


def _html_lang(lc: LocaleContext) -> str:
    return lc.locale.replace("_", "-") if "_" in lc.locale else lc.locale


def _min_age(lc: LocaleContext) -> int:
    return 21 if lc.geo.upper() == "BE" else 18


def _site_display_name(site_dir: Path, lc: LocaleContext) -> str:
    slug = site_dir.name.lower()
    if lc.lang == "fr" and "fr-be" in slug:
        return "Cazilla Belgique"
    if lc.lang == "fr":
        return "Cazilla"
    return "Cazilla"


def _cookie_js_prefix(site_slug: str) -> str:
    safe = re.sub(r"[^a-z0-9_]+", "_", site_slug.lower()).strip("_")
    return safe[:48] or "cazilla_offerwall"


@dataclass(frozen=True)
class OwUi:
    lang: str
    min_age: int
    site_name: str
    cta_label: str
    title_suffix: str
    menu_label: str
    drawer_title: str
    agg_aria: str
    brand_aria: str
    cookie_policy_href: str

    @staticmethod
    def from_lc(lc: LocaleContext, site_name: str, cookie_policy_rel: str = "cookie-policy.html") -> OwUi:
        ma = _min_age(lc)
        if lc.lang == "fr":
            return OwUi(
                lang=_html_lang(lc),
                min_age=ma,
                site_name=site_name,
                cta_label="Jouer sur Cazilla",
                title_suffix=" — avis Cazilla",
                menu_label="Menu",
                drawer_title="Pages",
                agg_aria="Top cinq sélections",
                brand_aria=f"Accueil {site_name}",
                cookie_policy_href=cookie_policy_rel,
            )
        return OwUi(
            lang=_html_lang(lc),
            min_age=ma,
            site_name=site_name,
            cta_label="Open Cazilla",
            title_suffix=" — Cazilla review",
            menu_label="Menu",
            drawer_title="Pages",
            agg_aria="Top five picks",
            brand_aria=f"{site_name} home",
            cookie_policy_href=cookie_policy_rel,
        )


def _compliance_block(ui: OwUi, *, cookie_href: str) -> str:
    ch = html_lib.escape(cookie_href)
    if ui.lang.startswith("fr"):
        if ui.min_age >= 21:
            age_body = (
                "Ce site traite des jeux d'argent réglementés pour lecteurs en Belgique. "
                f"Vous devez avoir au moins {ui.min_age} ans pour continuer."
            )
        else:
            age_body = (
                f"Vous devez avoir {ui.min_age} ans ou plus pour continuer. "
                "Ce site traite des jeux d'argent réglementés."
            )
        return f"""    <div class="complianceOverlay" id="ageGate" role="dialog" aria-modal="true" aria-labelledby="ageTitle">
  <div class="complianceDialog">
    <h2 id="ageTitle">Confirmez que vous avez {ui.min_age} ans ou plus</h2>
    <p>{age_body}</p>
    <div class="complianceActions">
      <button type="button" class="btn" id="ageUnder">J'ai moins de {ui.min_age} ans</button>
      <button type="button" class="btn primary" id="ageOk">J'ai {ui.min_age} ans ou plus</button>
    </div>
  </div>
</div>
    <div class="complianceOverlay" id="cookieGate" hidden aria-hidden="true" role="dialog" aria-modal="true" aria-labelledby="cookieTitle">
  <div class="complianceDialog">
    <h2 id="cookieTitle">Préférences cookies</h2>
    <p>Nous utilisons des cookies pour mémoriser la vérification d'âge. Voir <a class="inTextLink" href="{ch}">politique de cookies</a>.</p>
    <div class="complianceActions">
      <button type="button" class="btn" id="cookieReject">Essentiels uniquement</button>
      <button type="button" class="btn primary" id="cookieAccept">Accepter</button>
    </div>
  </div>
</div>
"""
    age_title = f"Confirm you are {ui.min_age} or over"
    return f"""    <div class="complianceOverlay" id="ageGate" role="dialog" aria-modal="true" aria-labelledby="ageTitle">
      <div class="complianceDialog">
        <h2 id="ageTitle">{html_lib.escape(age_title)}</h2>
        <p>You must be at least {ui.min_age} to continue. This site discusses regulated gambling topics.</p>
        <div class="complianceActions">
          <button type="button" class="btn" id="ageUnder">I am under {ui.min_age}</button>
          <button type="button" class="btn primary" id="ageOk">I am {ui.min_age} or over</button>
        </div>
      </div>
    </div>
    <div class="complianceOverlay" id="cookieGate" hidden aria-hidden="true" role="dialog" aria-modal="true" aria-labelledby="cookieTitle">
  <div class="complianceDialog">
    <h2 id="cookieTitle">Cookie preferences</h2>
    <p>We use cookies to remember your age check. See <a class="inTextLink" href="{ch}">cookie policy</a>.</p>
    <div class="complianceActions">
      <button type="button" class="btn" id="cookieReject">Essential only</button>
      <button type="button" class="btn primary" id="cookieAccept">Accept</button>
    </div>
  </div>
</div>
"""


def _title_from_kw(kw: str, ui: OwUi, max_len: int = 58) -> str:
    base = kw[:1].upper() + kw[1:] if kw else "Casino"
    tail = ui.title_suffix
    t = base + tail
    if len(t) > max_len:
        t = base[: max(12, max_len - len(tail) - 3)].rstrip() + "…" + tail
    return t[:max_len]


def _desc_from_kw(kw: str, lc: LocaleContext, ui: OwUi) -> str:
    if lc.lang == "fr":
        s = (
            f"Avis éditorial Cazilla pour {lc.region_name} : {kw}. "
            f"Bonus, jeux, paiements — {ui.min_age}+."
        )
    else:
        s = (
            f"Editorial Cazilla review for {lc.region_name}: {kw}. "
            f"Bonuses, games, payments — {ui.min_age}+ readers."
        )
    return s[:138] if len(s) > 138 else s


def _placeholder_lead(lc: LocaleContext, ui: OwUi, cta_html: str) -> str:
    if lc.lang == "fr":
        return (
            f"Notes éditoriales pour {lc.audience_phrase} ({ui.min_age}+). {cta_html}"
        )
    return f"Editorial notes for {lc.audience_phrase} ({ui.min_age}+). {cta_html}"


def _short_footer(lc: LocaleContext, ui: OwUi) -> str:
    if lc.lang == "fr":
        return (
            f"{ui.site_name} publie des comparatifs éditoriaux pour {lc.audience_phrase}. "
            f"Nous n'exploitons pas de casino. Jeu responsable — {ui.min_age}+."
        )
    return (
        f"{ui.site_name} publishes independent editorial comparisons for {lc.audience_phrase}. "
        f"We do not operate a casino. Play responsibly — {ui.min_age}+."
    )


def _hub_prose_placeholder(lc: LocaleContext) -> str:
    if lc.lang == "fr":
        blocks = [
            ("Cazilla, toujours à la recherche du meilleur choix", "Texte éditorial à compléter (A2)."),
            ("Comment nous évaluons les casinos en ligne", "Méthode de comparaison à compléter (A2)."),
            ("Pas de casino parfait, mais de meilleures options", "Jeux et lobby à compléter (A2)."),
        ]
    else:
        blocks = [
            ("Cazilla — finding the best fit", "Editorial overview placeholder (A2)."),
            ("How we review online casinos", "Method placeholder (A2)."),
            ("No perfect casino, better options", "Games and lobby placeholder (A2)."),
        ]
    lines = []
    for h, p in blocks:
        lines.append(f"          <h2>{html_lib.escape(h)}</h2>\n          <p>{html_lib.escape(p)}</p>")
    return "\n".join(lines) + "\n"


def _placeholder_footer(lc: LocaleContext, ui: OwUi) -> str:
    if lc.lang == "fr":
        return (
            f"{ui.site_name} propose des comparatifs éditoriaux indépendants pour "
            f"{lc.audience_phrase}. Nous n'exploitons pas de casino. "
            f"Le jeu comporte des risques — jouez de façon responsable."
        )
    return (
        f"{ui.site_name} provides independent editorial comparisons for {lc.audience_phrase}. "
        "We do not operate a casino. Gambling involves risk; play responsibly."
    )


def _is_hub_index(site_slug: str, rel: str) -> bool:
    return rel == "index.html" and "offerwall" in site_slug.lower()


def _is_slots_catalog(site_slug: str, rel: str) -> bool:
    return Path(rel).name == "slots.html" and "offerwall" in site_slug.lower()


def _is_bonus_catalog(site_slug: str, rel: str) -> bool:
    return Path(rel).name == "bonus.html" and "offerwall" in site_slug.lower()


def _is_about_trust(site_slug: str, rel: str) -> bool:
    return Path(rel).name == "about.html" and "offerwall" in site_slug.lower()


def _slots_demo_cards() -> list[tuple[str, str, str]]:
    return [
        ("assets/pictures/big-bass-bonanza-review.avif", "Big Bass Bonanza", "Pragmatic Play"),
        ("assets/pictures/fruit-classic-slot.png", "Fruit Classic", "NetEnt"),
        ("assets/pictures/money-train-4-thumbnail.png", "Money Train 4", "Relax Gaming"),
        ("assets/pictures/bonus-promo-artwork.webp", "Sweet Spins", "Play'n GO"),
        ("assets/pictures/casino-feature-visual.png", "Star Cluster", "Red Tiger"),
        ("assets/pictures/slots-showcase.png", "Gates Rush", "Pragmatic Play"),
        ("assets/pictures/rocket-crash-game.png", "Rocket Rush", "Spribe"),
        ("assets/pictures/baccarat-bonus-terms.webp", "Bonus Lines", "Microgaming"),
        ("assets/pictures/crazy-time-bonus.jpg", "Crazy Multi", "Evolution"),
    ]


def _slots_grid_html(*, ap: str, casino_url: str, lc: LocaleContext, hidden_from: int = 6) -> str:
    play = "Jouer" if lc.lang == "fr" else "Play"
    demo = "Démo" if lc.lang == "fr" else "Demo"
    esc_casino = html_lib.escape(casino_url, quote=True)
    lines: list[str] = []
    for i, (src, title, provider) in enumerate(_slots_demo_cards()):
        extra_cls = " is-hidden" if i >= hidden_from else ""
        lines.append(
            f'          <article class="ow-slotsCard{extra_cls}" data-provider="{html_lib.escape(provider.lower())}">'
            f'<div class="ow-slotsCardThumb"><img src="{html_lib.escape(ap + src)}" alt="" width="320" height="200" loading="lazy" decoding="async" /></div>'
            f'<div class="ow-slotsCardBody"><h3 class="ow-slotsCardTitle">{html_lib.escape(title)}</h3>'
            f'<p class="ow-slotsCardProvider">{html_lib.escape(provider)}</p>'
            f'<div class="ow-slotsCardActions">'
            f'<a class="ow-slotsPlay" href="{esc_casino}" rel="noopener noreferrer" target="_blank">{html_lib.escape(play)}</a>'
            f'<a href="{esc_casino}" rel="noopener noreferrer" target="_blank">{html_lib.escape(demo)}</a>'
            f"</div></div></article>"
        )
    return "\n".join(lines)


def _slots_filters_html(lc: LocaleContext) -> str:
    if lc.lang == "fr":
        groups = [
            ("Type de slot", ["Fruits", "Vidéo", "Megaways", "Classiques"]),
            ("Fournisseur", ["NetEnt", "Pragmatic Play", "Play'n GO", "Nolimit City"]),
            ("Thème", ["Aventure", "Égypte", "Musique", "Animaux"]),
            ("Fonctions", ["Free spins", "Buy bonus", "Multiplicateurs", "Sticky wilds"]),
            ("Volatilité", ["Élevée", "Moyenne", "Faible"]),
            ("RTP", ["> 96 %", "> 97 %", "> 98 %"]),
        ]
    else:
        groups = [
            ("Slot type", ["Fruit", "Video", "Megaways", "Classic"]),
            ("Provider", ["NetEnt", "Pragmatic Play", "Play'n GO", "Nolimit City"]),
            ("Theme", ["Adventure", "Egypt", "Music", "Animals"]),
            ("Features", ["Free spins", "Buy bonus", "Multipliers", "Sticky wilds"]),
            ("Volatility", ["High", "Medium", "Low"]),
            ("RTP", ["> 96%", "> 97%", "> 98%"]),
        ]
    blocks: list[str] = []
    for legend, opts in groups:
        items = []
        for j, opt in enumerate(opts):
            uid = re.sub(r"[^a-z0-9]+", "-", f"{legend}-{opt}".lower()).strip("-")
            items.append(
                f'          <label><input type="checkbox" name="f-{html_lib.escape(uid)}" value="1" /> '
                f"{html_lib.escape(opt)}</label>"
            )
        blocks.append(
            f"        <fieldset><legend>{html_lib.escape(legend)}</legend>\n"
            + "\n".join(items)
            + "\n        </fieldset>"
        )
    return "\n".join(blocks)


def _slots_seo_placeholder(lc: LocaleContext) -> str:
    if lc.lang == "fr":
        return "          <p>Guide éditorial slots — contenu A2.</p>\n"
    return "          <p>Slots editorial guide — A2 content.</p>\n"


def _bonus_chips_html(lc: LocaleContext) -> str:
    if lc.lang == "fr":
        chips = [
            ("#ow-bonus-cashback", "Cashback"),
            ("#ow-bonus-welcome", "Bonus de bienvenue"),
            ("#ow-bonus-reload", "Bonus reload"),
            ("#ow-bonus-nodeposit", "Sans dépôt"),
            ("#ow-bonus-vip", "Programme fidélité"),
        ]
    else:
        chips = [
            ("#ow-bonus-cashback", "Cashback"),
            ("#ow-bonus-welcome", "Welcome bonus"),
            ("#ow-bonus-reload", "Reload bonus"),
            ("#ow-bonus-nodeposit", "No deposit"),
            ("#ow-bonus-vip", "Loyalty"),
        ]
    return "\n".join(
        f'          <a href="{html_lib.escape(href)}">{html_lib.escape(label)}</a>'
        for href, label in chips
    )


def _bonus_comparison_table_html(lc: LocaleContext) -> str:
    if lc.lang == "fr":
        h2 = "Les bonus casino en ligne : vue d'ensemble"
        th = ("Casino", "Bonus de bienvenue", "Promos régulières")
        rows = [
            ("Cazilla", "100 % + tours gratuits*", "Reload hebdo, cashback"),
            ("Marque fictive A", "Jusqu'à 200 €*", "Tours promo"),
            ("Marque fictive B", "Package mixte*", "VIP"),
            ("Marque fictive C", "Free spins*", "Reload"),
            ("Marque fictive D", "Sans dépôt limité*", "Tournois"),
        ]
        note = "*Exemples éditoriaux — vérifiez les conditions sur le site officiel."
    else:
        h2 = "Online casino bonuses at a glance"
        th = ("Casino", "Welcome bonus", "Regular promos")
        rows = [
            ("Cazilla", "100% + free spins*", "Weekly reload, cashback"),
            ("Sample brand A", "Up to €200*", "Promo spins"),
            ("Sample brand B", "Mixed package*", "VIP"),
            ("Sample brand C", "Free spins*", "Reload"),
            ("Sample brand D", "Limited no deposit*", "Tournaments"),
        ]
        note = "*Editorial examples only — verify terms on the official site."
    body_rows = []
    for name, welcome, promos in rows:
        body_rows.append(
            f"            <tr><td>{html_lib.escape(name)}</td>"
            f"<td>{html_lib.escape(welcome)}</td>"
            f"<td>{html_lib.escape(promos)}</td></tr>"
        )
    return (
        f'        <div class="ow-bonusTableWrap" id="ow-bonus-overview">\n'
        f"          <h2>{html_lib.escape(h2)}</h2>\n"
        f'          <table class="ow-bonusTable">\n'
        f"            <thead><tr>"
        f"<th>{html_lib.escape(th[0])}</th>"
        f"<th>{html_lib.escape(th[1])}</th>"
        f"<th>{html_lib.escape(th[2])}</th>"
        f"</tr></thead>\n"
        f"            <tbody>\n"
        + "\n".join(body_rows)
        + f"\n            </tbody>\n          </table>\n"
        f'          <p class="ow-bonusTableNote">{html_lib.escape(note)}</p>\n'
        f"        </div>\n"
    )


def _bonus_brand_cards_html(lc: LocaleContext) -> str:
    if lc.lang == "fr":
        specs = [
            ("Meilleur bonus", "100 % + 200 FS"),
            ("Mise en jeu (wagering)", "x35 bonus"),
            ("Mise max.", "5 €"),
            ("Délai", "30 jours"),
            ("Cashback", "Jusqu'à 10 %"),
        ]
        cards = [
            ("Cazilla", specs),
            (
                "LuxeSpin Club",
                [
                    ("Meilleur bonus", "150 € package"),
                    ("Mise en jeu (wagering)", "x40"),
                    ("Mise max.", "4 €"),
                    ("Délai", "21 jours"),
                    ("Cashback", "5 %"),
                ],
            ),
        ]
    else:
        specs = [
            ("Best bonus", "100% + 200 FS"),
            ("Wagering", "x35"),
            ("Max bet", "€5"),
            ("Time limit", "30 days"),
            ("Cashback", "Up to 10%"),
        ]
        cards = [("Cazilla", specs), ("Sample Club", specs)]
    blocks = []
    for name, rows in cards:
        trs = "\n".join(
            f"              <tr><th>{html_lib.escape(k)}</th><td>{html_lib.escape(v)}</td></tr>"
            for k, v in rows
        )
        blocks.append(
            f'          <article class="ow-bonusBrandCard">\n'
            f"            <h3>{html_lib.escape(name)}</h3>\n"
            f'            <table class="ow-bonusSpecTable"><tbody>\n{trs}\n            </tbody></table>\n'
            f"          </article>"
        )
    return "\n".join(blocks)


def _bonus_faq_stub(lc: LocaleContext) -> str:
    if lc.lang == "fr":
        title = "Questions fréquentes sur les bonus casino"
        items = [
            ("Qu'est-ce que le wagering ?", "C'est le nombre de fois que vous devez miser le montant du bonus avant de pouvoir retirer les gains associés."),
            ("Vaut-il mieux jouer sans bonus ?", "Parfois oui, si vous voulez retirer vite sans contraintes de mise — lisez toujours les conditions."),
            ("Un bonus sans dépôt est-il vraiment gratuit ?", "Il permet de tester, mais des conditions de mise et des plafonds s'appliquent presque toujours."),
            ("Les free spins sont-ils séparés du bonus cash ?", "Souvent oui : gains des tours soumis à un wagering distinct."),
            ("Comment comparer deux offres ?", "Regardez wagering, mise max, jeux éligibles et durée — pas seulement le montant affiché."),
        ]
    else:
        title = "Bonus FAQ"
        items = [
            ("What is wagering?", "How many times you must bet the bonus before withdrawing related winnings."),
            ("Play without a bonus?", "Sometimes better if you want faster withdrawals without playthrough rules."),
            ("Is no-deposit really free?", "It helps you test, but wagering and caps usually apply."),
            ("Are free spins separate?", "Often yes — spin winnings may have their own wagering."),
            ("How to compare offers?", "Check wagering, max bet, eligible games and expiry — not headline amount only."),
        ]
    details = [
        f"          <details><summary>{html_lib.escape(q)}</summary><p>{html_lib.escape(a)}</p></details>"
        for q, a in items
    ]
    return (
        f'        <section class="ow-bonusFaq" id="ow-bonus-faq" data-a2-field="faq_section">\n'
        f'          <h2 class="ow-bonusFaqTitle">{html_lib.escape(title)}</h2>\n'
        + "\n".join(details)
        + "\n        </section>\n"
    )


def _bonus_seo_placeholder(lc: LocaleContext) -> str:
    if lc.lang == "fr":
        return "          <p>Guide bonus — contenu A2.</p>\n"
    return "          <p>Bonus guide — A2 content.</p>\n"


def _shell_bonus_catalog(
    *,
    rel: str,
    site_origin: str,
    html_lang: str,
    hreflang: str,
    min_age: int,
    site_name: str,
    title: str,
    description: str,
    hero_h1: str,
    hero_lead: str,
    expert_inner: str,
    seo_inner: str,
    faq_inner: str,
    footer_legal_inner: str,
    compliance_html: str,
    footer_legal_nav: str,
    drawer_nav: str,
    header_cta_href: str,
    ui: OwUi,
    lc: LocaleContext,
) -> str:
    ap = _ap(rel)
    can = _canonical(site_origin, rel)
    esc_t = html_lib.escape(title)
    esc_d = html_lib.escape(description)
    esc_can = html_lib.escape(can)
    esc_h1 = html_lib.escape(hero_h1)
    esc_lead = hero_lead
    og_img = html_lib.escape(f"{site_origin.rstrip('/')}/assets/pictures/og-logo.svg", quote=True)
    esc_hreflang = html_lib.escape(hreflang)
    esc_site = html_lib.escape(site_name)
    cta_href = html_lib.escape(header_cta_href, quote=True)
    cta_lbl = html_lib.escape(ui.cta_label)
    if lc.lang == "fr":
        toplist_h2 = "Réclamez un bonus casino en ligne"
        expert_h2 = "Le plus gros bonus n'est pas toujours le meilleur choix"
        quick_h2 = "Repères rapides sur cette page"
        quick_links = [
            ("#ow-bonus-welcome", "Meilleurs bonus de bienvenue"),
            ("#ow-bonus-reload", "Bonus reload"),
            ("#ow-bonus-nodeposit", "Offres sans dépôt"),
            ("#ow-bonus-faq", "FAQ bonus"),
        ]
    else:
        toplist_h2 = "Claim an online casino bonus"
        expert_h2 = "The biggest bonus is not always the best pick"
        quick_h2 = "Quick links on this page"
        quick_links = [
            ("#ow-bonus-welcome", "Best welcome bonuses"),
            ("#ow-bonus-reload", "Reload bonuses"),
            ("#ow-bonus-nodeposit", "No deposit offers"),
            ("#ow-bonus-faq", "Bonus FAQ"),
        ]
    quick_nav = "\n".join(
        f'            <a href="{html_lib.escape(h)}">{html_lib.escape(lbl)}</a>' for h, lbl in quick_links
    )
    agg_aria = html_lib.escape(ui.agg_aria)
    chips = _bonus_chips_html(lc)
    table = _bonus_comparison_table_html(lc)
    brands = _bonus_brand_cards_html(lc)
    return f"""<!doctype html>
<html lang="{html_lib.escape(html_lang)}" data-min-gambling-age="{min_age}">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title data-a2-field="meta_title">{esc_t}</title>
    <meta name="description" data-a2-field="meta_description" content="{esc_d}" />
    <meta name="robots" content="index, follow" />
    <link rel="canonical" href="{esc_can}" />
    <link rel="alternate" hreflang="{esc_hreflang}" href="{esc_can}" />
    <link rel="alternate" hreflang="x-default" href="{esc_can}" />
    <meta property="og:title" content="{esc_t}" />
    <meta property="og:description" content="{esc_d}" />
    <meta property="og:image" content="{og_img}" />
    <script type="application/ld+json">
      {{"@context":"https://schema.org","@type":"WebSite","name":"{esc_site}","url":"{html_lib.escape(site_origin.rstrip("/"), quote=True)}"}}
    </script>
    <link rel="stylesheet" href="{ap}assets/shell.css" />
    <link rel="stylesheet" href="{ap}assets/compliance.css" />
    <link rel="stylesheet" href="{ap}assets/offerwall-nav.css" />
    <link rel="stylesheet" href="{ap}assets/offerwall-hub.css" />
    <link rel="stylesheet" href="{ap}assets/offerwall-bonus.css" />
  </head>
  <body class="lv-body" data-site-kind="offerwall" data-page="bonus-catalog">
{compliance_html}
    <div id="siteContent" class="ow-app ow-app--bonus">
      <header class="ow-topbar ow-topbar--hub">
        <a class="ow-brand" href="{ap}index.html" aria-label="{html_lib.escape(ui.brand_aria)}">
          <img src="{ap}assets/pictures/og-logo.svg" alt="" width="34" height="34" decoding="async" />
        </a>
        <a class="ow-headerCta" href="{cta_href}" rel="noopener noreferrer" target="_blank">{cta_lbl}</a>
      </header>
      <button type="button" class="ow-menuBtn" id="menuToggle" aria-expanded="false" aria-controls="sideDrawer">{html_lib.escape(ui.menu_label)}</button>
      <div class="ow-drawerOverlay" id="drawerOverlay" hidden></div>
      <aside class="ow-drawer" id="sideDrawer" aria-hidden="true" aria-label="Site menu">
        <div class="ow-drawerHeader">
          <span class="ow-drawerTitle">{html_lib.escape(ui.drawer_title)}</span>
          <button type="button" class="ow-drawerClose" id="drawerClose" aria-label="Close menu">×</button>
        </div>
        <nav class="ow-drawerNav" aria-label="Site pages">
{drawer_nav}
        </nav>
      </aside>

      <main class="ow-main ow-main--bonus" id="top">
        <section class="ow-bonusHero ow-hero hero" aria-label="Hero">
          <h1 data-a2-field="page_h1">{esc_h1}</h1>
          <nav class="ow-bonusChips" aria-label="Quick filters">
{chips}
          </nav>
          <p class="ow-lead subtitle ow-bonusIntro" data-a2-field="page_lead">{esc_lead}</p>
        </section>

        <section class="ow-bonusToplist" aria-labelledby="ow-bonus-toplist-title">
          <h2 class="ow-bonusToplistTitle" id="ow-bonus-toplist-title">{html_lib.escape(toplist_h2)}</h2>
          <section id="ow-bonus-toplist" class="ow-aggregatorTop5" aria-label="{agg_aria}"></section>
        </section>

        <section class="ow-bonusExpert" id="ow-bonus-expert" data-a2-field="expert_callout">
          <h2>{html_lib.escape(expert_h2)}</h2>
          <p>{expert_inner}</p>
        </section>

{table}

        <div class="ow-bonusBrandCards" id="ow-bonus-brands">
{brands}
        </div>

        <nav class="ow-bonusQuickNav" aria-labelledby="ow-bonus-quick-title">
          <h2 id="ow-bonus-quick-title">{html_lib.escape(quick_h2)}</h2>
          <div class="ow-bonusQuickNavGrid">
{quick_nav}
          </div>
        </nav>

        <div class="policyCard">
          <article class="ow-prose ow-bonusSeo" data-a2-field="main_seo_html">
{seo_inner}
          </article>
        </div>

{faq_inner}

        <footer class="ow-footer ow-footer--hub" id="footer">
          <nav class="ow-footerLegal" aria-label="Legal pages">
{footer_legal_nav}
          </nav>
          <section id="footer-legal">
            <p data-a2-field="footer_note">{footer_legal_inner}</p>
          </section>
        </footer>
      </main>
    </div>
    <script src="{ap}assets/site.js" defer></script>
  </body>
</html>"""


def _bonus_expert_placeholder(lc: LocaleContext) -> str:
    if lc.lang == "fr":
        return (
            "Un package à 500 € avec un wagering x50 peut coûter plus cher qu'un bonus "
            "modeste à x30. Comparez mise max, jeux éligibles et délai avant de déposer."
        )
    return (
        "A €500 package at x50 wagering can cost more than a modest bonus at x30. "
        "Compare max bet, eligible games and expiry before you deposit."
    )


_SVG_SHIELD = (
    '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
    '<path d="M12 2 4 5v6c0 5 3.4 9.7 8 11 4.6-1.3 8-6 8-11V5l-8-3zm0 2.2 6 2.25V11c0 3.8-2.5 7.4-6 8.7C8.5 18.4 6 14.8 6 11V6.45l6-2.25z"/>'
    "</svg>"
)
_SVG_COIN = (
    '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
    '<path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm0 2c1.7 0 3.2.5 4.5 1.4-1 .8-2.2 1.3-3.5 1.5-1.3-.2-2.5-.7-3.5-1.5A7.9 7.9 0 0 1 12 4zm-4.2 3.3c1.2.9 2.7 1.4 4.2 1.4s3-.5 4.2-1.4c.6 1 .9 2.1.9 3.3s-.3 2.3-.9 3.3c-1.2-.9-2.7-1.4-4.2-1.4s-3 .5-4.2 1.4c-.6-1-.9-2.1-.9-3.3s.3-2.3.9-3.3zM6 12.8c1 .7 2.2 1.1 3.4 1.2 1.2-.1 2.4-.5 3.4-1.2.3.6.5 1.2.5 1.9 0 .7-.2 1.3-.5 1.9-1 .7-2.2 1.1-3.4 1.2-1.2-.1-2.4-.5-3.4-1.2a4 4 0 0 1-.5-1.9c0-.7.2-1.3.5-1.9z"/>'
    "</svg>"
)
_SVG_BULB = (
    '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
    '<path d="M9 21h6v-1H9v1zm3-19a7 7 0 0 0-4.9 11.9c.6.6 1 1.4 1.1 2.3H14c.1-.9.5-1.7 1.1-2.3A7 7 0 0 0 12 2zm0 2a5 5 0 0 1 3.5 8.5c-.8.8-1.2 1.8-1.3 2.9h-4.4c-.1-1.1-.5-2.1-1.3-2.9A5 5 0 0 1 12 4z"/>'
    "</svg>"
)


def _about_values_grid_html(lc: LocaleContext) -> str:
    if lc.lang == "fr":
        title = "Nos 3 garanties essentielles"
        cards = [
            (_SVG_SHIELD, "100 % indépendant", "Nos notes ne sont pas achetées par les opérateurs ; Cazilla peut être mis en avant, mais le texte reste éditorial."),
            (_SVG_COIN, "Testé avec de l'argent réel", "Dépôts réels, retraits et support testés — pas seulement la page promo."),
            (_SVG_BULB, "Conseils fiables", "Du premier dépôt au gros volume : conditions de bonus et pièges expliqués clairement."),
        ]
        policy = 'Voir aussi notre <a href="fair-play.html">charte éditoriale (fair play)</a>.'
    else:
        title = "Our 3 core guarantees"
        cards = [
            (_SVG_SHIELD, "100% independent", "Scores are not sold to operators; Cazilla may be featured but copy stays editorial."),
            (_SVG_COIN, "Tested with real money", "Deposits, withdrawals and support checked — not promo pages only."),
            (_SVG_BULB, "Reliable tips", "From first deposit to high rollers: bonus terms and traps explained plainly."),
        ]
        policy = 'See our <a href="fair-play.html">editorial fair play charter</a>.'
    blocks = []
    for svg, h3, body in cards:
        blocks.append(
            f'          <article class="ow-aboutValueCard">\n'
            f'            <div class="ow-aboutValueIcon">{svg}</div>\n'
            f"            <h3>{html_lib.escape(h3)}</h3>\n"
            f"            <p>{html_lib.escape(body)}</p>\n"
            f"          </article>"
        )
    return (
        f'        <section class="ow-aboutValues" aria-labelledby="ow-about-values-title">\n'
        f'          <h2 class="ow-aboutValuesTitle" id="ow-about-values-title">{html_lib.escape(title)}</h2>\n'
        f'          <div class="ow-aboutValuesGrid">\n'
        + "\n".join(blocks)
        + f'\n          </div>\n'
        f'          <p class="ow-aboutPolicyLinks">{policy}</p>\n'
        f"        </section>\n"
    )


def _about_seo_placeholder(lc: LocaleContext) -> str:
    if lc.lang == "fr":
        return "          <p>Guide éditorial — contenu A2.</p>\n"
    return "          <p>About guide — A2 content.</p>\n"


def _shell_about_trust(
    *,
    rel: str,
    site_origin: str,
    html_lang: str,
    hreflang: str,
    min_age: int,
    site_name: str,
    title: str,
    description: str,
    hero_h1: str,
    hero_lead: str,
    seo_inner: str,
    footer_legal_inner: str,
    compliance_html: str,
    footer_legal_nav: str,
    drawer_nav: str,
    header_cta_href: str,
    ui: OwUi,
    lc: LocaleContext,
) -> str:
    ap = _ap(rel)
    can = _canonical(site_origin, rel)
    esc_t = html_lib.escape(title)
    esc_d = html_lib.escape(description)
    esc_can = html_lib.escape(can)
    esc_h1 = html_lib.escape(hero_h1)
    esc_lead = hero_lead
    og_img = html_lib.escape(f"{site_origin.rstrip('/')}/assets/pictures/og-logo.svg", quote=True)
    esc_hreflang = html_lib.escape(hreflang)
    esc_site = html_lib.escape(site_name)
    cta_href = html_lib.escape(header_cta_href, quote=True)
    cta_lbl = html_lib.escape(ui.cta_label)
    if lc.lang == "fr":
        partner_h2 = "Partenaire mis en avant"
    else:
        partner_h2 = "Featured partner"
    values = _about_values_grid_html(lc)
    return f"""<!doctype html>
<html lang="{html_lib.escape(html_lang)}" data-min-gambling-age="{min_age}">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title data-a2-field="meta_title">{esc_t}</title>
    <meta name="description" data-a2-field="meta_description" content="{esc_d}" />
    <meta name="robots" content="index, follow" />
    <link rel="canonical" href="{esc_can}" />
    <link rel="alternate" hreflang="{esc_hreflang}" href="{esc_can}" />
    <link rel="alternate" hreflang="x-default" href="{esc_can}" />
    <meta property="og:title" content="{esc_t}" />
    <meta property="og:description" content="{esc_d}" />
    <meta property="og:image" content="{og_img}" />
    <script type="application/ld+json">
      {{"@context":"https://schema.org","@type":"WebSite","name":"{esc_site}","url":"{html_lib.escape(site_origin.rstrip("/"), quote=True)}"}}
    </script>
    <link rel="stylesheet" href="{ap}assets/shell.css" />
    <link rel="stylesheet" href="{ap}assets/compliance.css" />
    <link rel="stylesheet" href="{ap}assets/offerwall-nav.css" />
    <link rel="stylesheet" href="{ap}assets/offerwall-hub.css" />
    <link rel="stylesheet" href="{ap}assets/offerwall-about.css" />
  </head>
  <body class="lv-body" data-site-kind="offerwall" data-page="about-trust">
{compliance_html}
    <div id="siteContent" class="ow-app ow-app--about">
      <header class="ow-topbar ow-topbar--hub">
        <a class="ow-brand" href="{ap}index.html" aria-label="{html_lib.escape(ui.brand_aria)}">
          <img src="{ap}assets/pictures/og-logo.svg" alt="" width="34" height="34" decoding="async" />
        </a>
        <a class="ow-headerCta" href="{cta_href}" rel="noopener noreferrer" target="_blank">{cta_lbl}</a>
      </header>
      <button type="button" class="ow-menuBtn" id="menuToggle" aria-expanded="false" aria-controls="sideDrawer">{html_lib.escape(ui.menu_label)}</button>
      <div class="ow-drawerOverlay" id="drawerOverlay" hidden></div>
      <aside class="ow-drawer" id="sideDrawer" aria-hidden="true" aria-label="Site menu">
        <div class="ow-drawerHeader">
          <span class="ow-drawerTitle">{html_lib.escape(ui.drawer_title)}</span>
          <button type="button" class="ow-drawerClose" id="drawerClose" aria-label="Close menu">×</button>
        </div>
        <nav class="ow-drawerNav" aria-label="Site pages">
{drawer_nav}
        </nav>
      </aside>

      <main class="ow-main ow-main--about" id="top">
        <section class="ow-aboutHero ow-hero hero" aria-label="Hero">
          <h1 data-a2-field="page_h1">{esc_h1}</h1>
          <p class="ow-lead subtitle ow-aboutIntro" data-a2-field="page_lead">{esc_lead}</p>
        </section>

{values}

        <section class="ow-aboutPartner" aria-labelledby="ow-about-partner-title">
          <h2 class="ow-aboutPartnerTitle" id="ow-about-partner-title">{html_lib.escape(partner_h2)}</h2>
          <section id="ow-about-partner" class="ow-aggregatorTop5" aria-label="{html_lib.escape(partner_h2)}"></section>
        </section>

        <div class="policyCard">
          <article class="ow-prose ow-aboutSeo" data-a2-field="main_seo_html">
{seo_inner}
          </article>
        </div>

        <footer class="ow-footer ow-footer--hub" id="footer">
          <nav class="ow-footerLegal" aria-label="Legal pages">
{footer_legal_nav}
          </nav>
          <section id="footer-legal">
            <p data-a2-field="footer_note">{footer_legal_inner}</p>
          </section>
        </footer>
      </main>
    </div>
    <script src="{ap}assets/site.js" defer></script>
  </body>
</html>"""


def _shell_slots_catalog(
    *,
    rel: str,
    site_origin: str,
    html_lang: str,
    hreflang: str,
    min_age: int,
    site_name: str,
    title: str,
    description: str,
    hero_h1: str,
    hero_lead: str,
    seo_inner: str,
    footer_legal_inner: str,
    compliance_html: str,
    footer_legal_nav: str,
    drawer_nav: str,
    header_cta_href: str,
    ui: OwUi,
    lc: LocaleContext,
) -> str:
    ap = _ap(rel)
    can = _canonical(site_origin, rel)
    esc_t = html_lib.escape(title)
    esc_d = html_lib.escape(description)
    esc_can = html_lib.escape(can)
    esc_h1 = html_lib.escape(hero_h1)
    esc_lead = hero_lead
    og_img = html_lib.escape(f"{site_origin.rstrip('/')}/assets/pictures/og-logo.svg", quote=True)
    esc_hreflang = html_lib.escape(hreflang)
    esc_site = html_lib.escape(site_name)
    cta_href = html_lib.escape(header_cta_href, quote=True)
    cta_lbl = html_lib.escape(ui.cta_label)
    if lc.lang == "fr":
        hint = (
            "Trop de choix ? Utilisez les filtres à gauche pour affiner les machines à sous, "
            "puis ouvrez Cazilla pour jouer en démo ou en argent réel."
        )
        more_btn = "Afficher plus de jeux"
        toplist_h2 = "Casinos avec le meilleur catalogue de slots pour la Belgique"
    else:
        hint = "Too much choice? Use the filters on the left, then open Cazilla to play demo or real-money slots."
        more_btn = "Show more games"
        toplist_h2 = "Casinos with the strongest slots lobby"
    grid = _slots_grid_html(ap=ap, casino_url=header_cta_href, lc=lc)
    filters = _slots_filters_html(lc)
    agg_aria = html_lib.escape(ui.agg_aria)
    return f"""<!doctype html>
<html lang="{html_lib.escape(html_lang)}" data-min-gambling-age="{min_age}">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title data-a2-field="meta_title">{esc_t}</title>
    <meta name="description" data-a2-field="meta_description" content="{esc_d}" />
    <meta name="robots" content="index, follow" />
    <link rel="canonical" href="{esc_can}" />
    <link rel="alternate" hreflang="{esc_hreflang}" href="{esc_can}" />
    <link rel="alternate" hreflang="x-default" href="{esc_can}" />
    <meta property="og:title" content="{esc_t}" />
    <meta property="og:description" content="{esc_d}" />
    <meta property="og:image" content="{og_img}" />
    <script type="application/ld+json">
      {{"@context":"https://schema.org","@type":"WebSite","name":"{esc_site}","url":"{html_lib.escape(site_origin.rstrip("/"), quote=True)}"}}
    </script>
    <link rel="stylesheet" href="{ap}assets/shell.css" />
    <link rel="stylesheet" href="{ap}assets/compliance.css" />
    <link rel="stylesheet" href="{ap}assets/offerwall-nav.css" />
    <link rel="stylesheet" href="{ap}assets/offerwall-hub.css" />
    <link rel="stylesheet" href="{ap}assets/offerwall-slots.css" />
  </head>
  <body class="lv-body" data-site-kind="offerwall" data-page="slots-catalog">
{compliance_html}
    <div id="siteContent" class="ow-app ow-app--slots">
      <header class="ow-topbar ow-topbar--hub">
        <a class="ow-brand" href="{ap}index.html" aria-label="{html_lib.escape(ui.brand_aria)}">
          <img src="{ap}assets/pictures/og-logo.svg" alt="" width="34" height="34" decoding="async" />
        </a>
        <a class="ow-headerCta" href="{cta_href}" rel="noopener noreferrer" target="_blank">{cta_lbl}</a>
      </header>
      <button type="button" class="ow-menuBtn" id="menuToggle" aria-expanded="false" aria-controls="sideDrawer">{html_lib.escape(ui.menu_label)}</button>
      <div class="ow-drawerOverlay" id="drawerOverlay" hidden></div>
      <aside class="ow-drawer" id="sideDrawer" aria-hidden="true" aria-label="Site menu">
        <div class="ow-drawerHeader">
          <span class="ow-drawerTitle">{html_lib.escape(ui.drawer_title)}</span>
          <button type="button" class="ow-drawerClose" id="drawerClose" aria-label="Close menu">×</button>
        </div>
        <nav class="ow-drawerNav" aria-label="Site pages">
{drawer_nav}
        </nav>
      </aside>

      <main class="ow-main ow-main--slots" id="top">
        <section class="ow-slotsHero ow-hero hero" aria-label="Hero">
          <h1 data-a2-field="page_h1">{esc_h1}</h1>
          <p class="ow-lead subtitle" data-a2-field="page_lead">{esc_lead}</p>
        </section>

        <div class="ow-slotsFinder">
          <aside class="ow-slotsFilters" aria-label="Slot filters">
{filters}
          </aside>
          <div class="ow-slotsResults">
            <p class="ow-slotsHint">{html_lib.escape(hint)}</p>
            <div class="ow-slotsGrid" id="ow-slots-grid">
{grid}
            </div>
            <button type="button" class="ow-slotsMoreLoad" id="owSlotsLoadMore">{html_lib.escape(more_btn)}</button>
          </div>
        </div>

        <section class="ow-slotsToplist" aria-labelledby="ow-slots-toplist-title">
          <h2 class="ow-slotsToplistTitle" id="ow-slots-toplist-title">{html_lib.escape(toplist_h2)}</h2>
          <section id="ow-slots-toplist" class="ow-aggregatorTop5" aria-label="{agg_aria}"></section>
        </section>

        <div class="policyCard">
          <article class="ow-prose ow-slotsSeo" data-a2-field="main_seo_html">
{seo_inner}
          </article>
        </div>

        <footer class="ow-footer ow-footer--hub" id="footer">
          <nav class="ow-footerLegal" aria-label="Legal pages">
{footer_legal_nav}
          </nav>
          <section id="footer-legal">
            <p data-a2-field="footer_note">{footer_legal_inner}</p>
          </section>
        </footer>
      </main>
    </div>
    <script src="{ap}assets/site.js" defer></script>
    <script src="{ap}assets/offerwall-slots.js" defer></script>
  </body>
</html>"""


def _content_menu_items(data: dict) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for page in data.get("pages") or []:
        if not isinstance(page, dict):
            continue
        rel = str(page.get("path") or "").strip().lstrip("/")
        if not rel:
            continue
        pid = str(page.get("id") or "").strip()
        label = str(page.get("menu_label") or "").strip() or pid.replace("-", " ").title() or "Page"
        out.append((rel, label))
    return out


def _drawer_nav_html(*, from_rel: str, items: list[tuple[str, str]], current_rel: str) -> str:
    lines: list[str] = []
    cur = Path(current_rel).as_posix()
    for to_rel, label in items:
        href = _rel_href(from_rel, to_rel)
        is_here = Path(to_rel).as_posix() == cur
        cls = "ow-navAnchor" + (" is-current" if is_here else "")
        cur_attr = ' aria-current="page"' if is_here else ""
        lines.append(
            f'          <a class="{cls}" href="{html_lib.escape(href)}"{cur_attr}>'
            f"{html_lib.escape(label)}</a>"
        )
    return "\n".join(lines)


def _hub_chips_html(*, ap: str, lc: LocaleContext, pages: list[tuple[str, str]]) -> str:
    skip = {"index.html", "home.html"}
    chips: list[str] = []
    for rel, label in pages:
        if Path(rel).as_posix() in skip:
            continue
        href = html_lib.escape(f"{ap}{rel}")
        chips.append(f'          <a href="{href}">{html_lib.escape(label)}</a>')
    if not chips:
        return ""
    aria = "Liens rapides" if lc.lang == "fr" else "Quick links"
    return (
        f'          <nav class="ow-hubChips" aria-label="{html_lib.escape(aria)}">\n'
        + "\n".join(chips)
        + "\n          </nav>\n"
    )


def _hub_slots_preview(*, ap: str, lc: LocaleContext) -> str:
    slots_href = html_lib.escape(f"{ap}slots.html")
    if lc.lang == "fr":
        title = "Aperçu des machines à sous"
        cards = [
            ("assets/pictures/fruit-classic-slot.png", "Classiques"),
            ("assets/pictures/money-train-4-thumbnail.png", "Money Train 4"),
            ("assets/pictures/big-bass-bonanza-review.avif", "Big Bass Bonanza"),
        ]
        cta = "Voir toutes les slots"
    else:
        title = "Slots preview"
        cards = [
            ("assets/pictures/fruit-classic-slot.png", "Classics"),
            ("assets/pictures/money-train-4-thumbnail.png", "Money Train 4"),
            ("assets/pictures/big-bass-bonanza-review.avif", "Big Bass Bonanza"),
        ]
        cta = "Browse all slots"
    cells: list[str] = []
    for src, cap in cards:
        cells.append(
            f'          <a class="ow-hubSlotCard" href="{slots_href}">'
            f'<img src="{html_lib.escape(ap + src)}" alt="" width="320" height="240" loading="lazy" decoding="async" />'
            f"<span>{html_lib.escape(cap)}</span></a>"
        )
    return (
        f'        <section class="ow-hubSlots" id="ow-hub-slots-preview" aria-labelledby="ow-hub-slots-title">\n'
        f'          <h2 class="ow-hubSlotsTitle" id="ow-hub-slots-title">{html_lib.escape(title)}</h2>\n'
        f'          <div class="ow-hubSlotsGrid">\n'
        + "\n".join(cells)
        + f'\n          </div>\n          <p class="ow-hubSlotsMore"><a href="{slots_href}">{html_lib.escape(cta)}</a></p>\n'
        "        </section>\n"
    )


def _hub_faq_stub(lc: LocaleContext) -> str:
    if lc.lang == "fr":
        title = "Questions fréquentes"
        items = [
            (
                "Cazilla est-il un casino licencié en Belgique ?",
                "Cette page est un comparatif éditorial : Cazilla est notre partenaire #1, "
                "les rangs #2–#5 sont fictifs. Vérifiez toujours les conditions sur le site officiel.",
            ),
            (
                "Puis-je jouer en mode démo ?",
                "Beaucoup de titres proposent une démo ; la disponibilité dépend du jeu et du compte. "
                "Consultez le lobby Cazilla pour confirmer.",
            ),
            (
                "Quels moyens de paiement sont courants ?",
                "Cartes, portefeuilles et virements selon l'opérateur. Les délais de retrait varient — "
                "lisez la page Paiements avant de déposer.",
            ),
            (
                "Comment comparer les bonus ?",
                "Regardez le montant, le wagering, les jeux éligibles et la durée. "
                "Un gros bonus n'est pas toujours le plus avantageux.",
            ),
            (
                "Jouer de façon responsable en Belgique",
                "Fixez des limites, faites des pauses et demandez de l'aide si le jeu cesse d'être un plaisir. "
                "Ressources listées dans notre page Jeu responsable.",
            ),
        ]
    else:
        title = "FAQ"
        items = [
            (
                "Is Cazilla licensed in my region?",
                "This page is editorial: Cazilla is our #1 outbound partner; ranks #2–#5 are fictional placeholders. "
                "Always verify terms on the official site.",
            ),
            (
                "Can I play in demo mode?",
                "Many titles offer demos; availability depends on the game and account. Check the Cazilla lobby.",
            ),
            (
                "Which payment methods are common?",
                "Cards, e-wallets and bank transfer depending on the operator. Read the Payments page before depositing.",
            ),
            (
                "How do I compare bonuses?",
                "Check amount, wagering, eligible games and expiry. A large headline bonus is not always the best deal.",
            ),
            (
                "Responsible play",
                "Set limits, take breaks and seek help if gambling stops being fun. See our Responsible gambling page.",
            ),
        ]
    details = []
    for q, a in items:
        details.append(
            f"          <details><summary>{html_lib.escape(q)}</summary><p>{html_lib.escape(a)}</p></details>"
        )
    return (
        f'        <section class="ow-hubFaq" id="ow-faq" data-a2-field="faq_section">\n'
        f'          <h2 class="ow-hubFaqTitle">{html_lib.escape(title)}</h2>\n'
        + "\n".join(details)
        + "\n        </section>\n"
    )


def _shell_home_hub(
    *,
    rel: str,
    site_origin: str,
    html_lang: str,
    hreflang: str,
    min_age: int,
    site_name: str,
    title: str,
    description: str,
    hero_h1: str,
    hero_lead: str,
    prose_inner: str,
    footer_legal_inner: str,
    compliance_html: str,
    footer_legal_nav: str,
    drawer_nav: str,
    hub_chips: str,
    hub_slots: str,
    hub_faq: str,
    header_cta_href: str,
    ui: OwUi,
) -> str:
    ap = _ap(rel)
    can = _canonical(site_origin, rel)
    esc_t = html_lib.escape(title)
    esc_d = html_lib.escape(description)
    esc_can = html_lib.escape(can)
    esc_h1 = html_lib.escape(hero_h1)
    esc_lead = hero_lead
    og_img = html_lib.escape(f"{site_origin.rstrip('/')}/assets/pictures/og-logo.svg", quote=True)
    esc_hreflang = html_lib.escape(hreflang)
    esc_site = html_lib.escape(site_name)
    cta_href = html_lib.escape(header_cta_href, quote=True)
    cta_lbl = html_lib.escape(ui.cta_label)
    agg_block = (
        f'        <section id="ow-aggregator-top5" class="ow-aggregatorTop5" aria-label="{html_lib.escape(ui.agg_aria)}"></section>\n'
    )
    return f"""<!doctype html>
<html lang="{html_lib.escape(html_lang)}" data-min-gambling-age="{min_age}">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title data-a2-field="meta_title">{esc_t}</title>
    <meta name="description" data-a2-field="meta_description" content="{esc_d}" />
    <meta name="robots" content="index, follow" />
    <link rel="canonical" href="{esc_can}" />
    <link rel="alternate" hreflang="{esc_hreflang}" href="{esc_can}" />
    <link rel="alternate" hreflang="x-default" href="{esc_can}" />
    <meta property="og:title" content="{esc_t}" />
    <meta property="og:description" content="{esc_d}" />
    <meta property="og:image" content="{og_img}" />
    <script type="application/ld+json">
      {{"@context":"https://schema.org","@type":"WebSite","name":"{esc_site}","url":"{html_lib.escape(site_origin.rstrip("/"), quote=True)}"}}
    </script>
    <link rel="stylesheet" href="{ap}assets/shell.css" />
    <link rel="stylesheet" href="{ap}assets/compliance.css" />
    <link rel="stylesheet" href="{ap}assets/offerwall-nav.css" />
    <link rel="stylesheet" href="{ap}assets/offerwall-hub.css" />
  </head>
  <body class="lv-body" data-site-kind="offerwall">
{compliance_html}
    <div id="siteContent" class="ow-app ow-app--hub">
      <header class="ow-topbar ow-topbar--hub">
        <a class="ow-brand" href="{ap}index.html" aria-label="{html_lib.escape(ui.brand_aria)}">
          <img src="{ap}assets/pictures/og-logo.svg" alt="" width="34" height="34" decoding="async" />
        </a>
        <a class="ow-headerCta" href="{cta_href}" rel="noopener noreferrer" target="_blank">{cta_lbl}</a>
      </header>
      <button type="button" class="ow-menuBtn" id="menuToggle" aria-expanded="false" aria-controls="sideDrawer">{html_lib.escape(ui.menu_label)}</button>
      <div class="ow-drawerOverlay" id="drawerOverlay" hidden></div>
      <aside class="ow-drawer" id="sideDrawer" aria-hidden="true" aria-label="Site menu">
        <div class="ow-drawerHeader">
          <span class="ow-drawerTitle">{html_lib.escape(ui.drawer_title)}</span>
          <button type="button" class="ow-drawerClose" id="drawerClose" aria-label="Close menu">×</button>
        </div>
        <nav class="ow-drawerNav" aria-label="Site pages">
{drawer_nav}
        </nav>
      </aside>

      <main class="ow-main ow-main--hub" id="top">
        <section class="ow-hero hero ow-hero--hub" aria-label="Hero">
          <h1 data-a2-field="page_h1">{esc_h1}</h1>
          <p class="ow-lead subtitle" data-a2-field="page_lead">
            {esc_lead}
          </p>
{hub_chips}        </section>
{agg_block}
        <div class="policyCard">
        <article class="ow-prose ow-prose--hub" data-a2-field="main_seo_html">
{prose_inner}
        </article>
        </div>

{hub_slots}
{hub_faq}
        <footer class="ow-footer ow-footer--hub" id="footer">
          <nav class="ow-footerLegal" aria-label="Legal pages">
{footer_legal_nav}
          </nav>
          <section id="footer-legal">
            <p data-a2-field="footer_note">{footer_legal_inner}</p>
          </section>
        </footer>
      </main>
    </div>
    <script src="{ap}assets/site.js" defer></script>
  </body>
</html>"""


def _footer_legal_nav(ap: str, legal_items: list[tuple[str, str]]) -> str:
    lines = []
    for rel, label in legal_items:
        href = f"{ap}{rel}" if not rel.startswith(("http://", "https://")) else rel
        lines.append(f'            <a href="{html_lib.escape(href)}">{html_lib.escape(label)}</a>')
    return "\n".join(lines)


def _shell(
    *,
    rel: str,
    site_origin: str,
    html_lang: str,
    hreflang: str,
    min_age: int,
    site_name: str,
    title: str,
    description: str,
    include_agg: bool,
    hero_h1: str,
    hero_lead: str,
    prose_inner: str,
    footer_legal_inner: str,
    compliance_html: str,
    footer_legal_nav: str,
    ui: OwUi,
) -> str:
    ap = _ap(rel)
    can = _canonical(site_origin, rel)
    esc_t = html_lib.escape(title)
    esc_d = html_lib.escape(description)
    esc_can = html_lib.escape(can)
    esc_h1 = html_lib.escape(hero_h1)
    esc_lead = hero_lead
    og_img = html_lib.escape(f"{site_origin.rstrip('/')}/assets/pictures/og-logo.svg", quote=True)
    esc_hreflang = html_lib.escape(hreflang)
    esc_site = html_lib.escape(site_name)
    agg_block = ""
    if include_agg:
        agg_block = (
            f'<section id="ow-aggregator-top5" class="ow-aggregatorTop5" aria-label="{html_lib.escape(ui.agg_aria)}"></section>\n'
        )
    return f"""<!doctype html>
<html lang="{html_lib.escape(html_lang)}" data-min-gambling-age="{min_age}">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title data-a2-field="meta_title">{esc_t}</title>
    <meta name="description" data-a2-field="meta_description" content="{esc_d}" />
    <meta name="robots" content="index, follow" />
    <link rel="canonical" href="{esc_can}" />
    <link rel="alternate" hreflang="{esc_hreflang}" href="{esc_can}" />
    <link rel="alternate" hreflang="x-default" href="{esc_can}" />
    <meta property="og:title" content="{esc_t}" />
    <meta property="og:description" content="{esc_d}" />
    <meta property="og:image" content="{og_img}" />
    <script type="application/ld+json">
      {{"@context":"https://schema.org","@type":"WebSite","name":"{esc_site}","url":"{html_lib.escape(site_origin.rstrip("/"), quote=True)}"}}
    </script>
    <link rel="stylesheet" href="{ap}assets/shell.css" />
    <link rel="stylesheet" href="{ap}assets/compliance.css" />
    <link rel="stylesheet" href="{ap}assets/offerwall-nav.css" />
  </head>
  <body class="lv-body" data-site-kind="offerwall">
{compliance_html}
    <div id="siteContent" class="ow-app">
      <header class="ow-topbar">
        <a class="ow-brand" href="{ap}index.html" aria-label="{html_lib.escape(ui.brand_aria)}">
          <img src="{ap}assets/pictures/og-logo.svg" alt="" width="34" height="34" decoding="async" />
        </a>
      </header>
      <button type="button" class="ow-menuBtn" id="menuToggle" aria-expanded="false" aria-controls="sideDrawer">{html_lib.escape(ui.menu_label)}</button>
      <div class="ow-drawerOverlay" id="drawerOverlay" hidden></div>
      <aside class="ow-drawer" id="sideDrawer" aria-hidden="true" aria-label="Site menu">
        <div class="ow-drawerHeader">
          <span class="ow-drawerTitle">{html_lib.escape(ui.drawer_title)}</span>
          <button type="button" class="ow-drawerClose" id="drawerClose" aria-label="Close menu">×</button>
        </div>
        <nav class="ow-drawerNav" aria-label="Site pages">
          <a class="ow-navAnchor" href="{ap}index.html">Home</a>
        </nav>
      </aside>

      <main class="ow-main" id="top">
        <section class="ow-hero hero" aria-label="Hero">
          <h1 data-a2-field="page_h1">{esc_h1}</h1>
          <p class="ow-lead subtitle" data-a2-field="page_lead">
            {esc_lead}
          </p>
        </section>
{agg_block}        <div class="policyCard">
        <article class="ow-prose" data-a2-field="main_seo_html">
{prose_inner}
        </article>
        </div>

        <footer class="ow-footer" id="footer">
          <nav class="ow-footerLegal" aria-label="Legal pages">
{footer_legal_nav}
          </nav>
          <section id="footer-legal">
            <p data-a2-field="footer_note">{footer_legal_inner}</p>
          </section>
        </footer>
      </main>
    </div>
    <script src="{ap}assets/site.js" defer></script>
  </body>
</html>"""


def _kw_pages(data: dict) -> list[tuple[str, dict]]:
    out: list[tuple[str, dict]] = []
    for page in data.get("pages") or []:
        if isinstance(page, dict):
            rel = str(page.get("path") or "").strip().lstrip("/")
            if rel:
                out.append((rel, page))
    return out


def _technical_pages(data: dict) -> list[tuple[str, str, str]]:
    """rel, h1, default paragraph."""
    out: list[tuple[str, str, str]] = []
    for page in data.get("technical_pages") or []:
        if not isinstance(page, dict):
            continue
        rel = str(page.get("path") or "").strip().lstrip("/")
        if not rel:
            continue
        label = str(page.get("menu_label") or page.get("id") or "Legal").strip()
        if not label:
            label = "Legal"
        pid = str(page.get("id") or "").strip()
        if pid == "responsible-gambling" and "fr" in str(data.get("locale") or ""):
            para = (
                "Si le jeu n'est plus un plaisir, faites une pause et demandez de l'aide. "
                "Des ressources existent pour les joueurs en Belgique."
            )
        elif pid == "cookie-policy":
            para = (
                "Ce site utilise des cookies pour mémoriser la vérification d'âge et vos préférences. "
                "Les détails figurent sur cette page."
            )
        else:
            para = (
                "Informations juridiques et éditoriales sur cette page. "
                "Ce texte sera remplacé par A2."
            )
        out.append((rel, label, para))
    return out


def _collect_legal_footer(data: dict) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    for page in data.get("technical_pages") or []:
        if not isinstance(page, dict):
            continue
        rel = str(page.get("path") or "").strip().lstrip("/")
        if not rel:
            continue
        label = str(page.get("menu_label") or page.get("id") or "Legal").strip()
        items.append((rel, label))
    return items


def copy_assets(site_dir: Path, site_slug: str) -> None:
    dest = site_dir / "assets"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(ASSET_SRC, dest)
    tpl = ASSET_SRC / "site.js"
    if tpl.is_file():
        js = tpl.read_text(encoding="utf-8")
        prefix = _cookie_js_prefix(site_slug)
        js = js.replace("cazilla_ow2_ie_age_ok", f"{prefix}_age_ok")
        js = js.replace("cazilla_ow2_ie_cookie", f"{prefix}_cookie")
        (dest / "site.js").write_text(js, encoding="utf-8")


def write_robots_sitemap(site_dir: Path, site_origin: str, data: dict, hreflang: str) -> None:
    origin = site_origin.rstrip("/")
    (site_dir / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {origin}/sitemap.xml\n",
        encoding="utf-8",
    )
    urls: list[str] = []
    for rel, _ in _kw_pages(data):
        urls.append(_canonical(origin, rel))
    for rel, _, _ in _technical_pages(data):
        urls.append(_canonical(origin, rel))
    entries = []
    for loc in urls:
        pri = "1.0" if loc.endswith("/") else "0.85"
        entries.append(
            f'  <url>\n    <loc>{loc}</loc>\n'
            f'    <xhtml:link rel="alternate" hreflang="{html_lib.escape(hreflang)}" href="{loc}"/>\n'
            f'    <xhtml:link rel="alternate" hreflang="x-default" href="{loc}"/>\n'
            f"    <lastmod>2026-05-19</lastmod>\n    <changefreq>weekly</changefreq>\n    <priority>{pri}</priority>\n  </url>"
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
        '        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        + "\n".join(entries)
        + "\n</urlset>\n"
    )
    (site_dir / "sitemap.xml").write_text(xml, encoding="utf-8")
    (site_dir / ".htaccess").write_text(
        "RewriteEngine On\nRewriteCond %{HTTPS} off\nRewriteRule ^ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]\n",
        encoding="utf-8",
    )


def fix_keywords_meta(kw_path: Path, site_slug: str, locale: str) -> None:
    if not kw_path.is_file():
        return
    data = json.loads(kw_path.read_text(encoding="utf-8"))
    data["site"] = site_slug
    data["locale"] = locale
    kw_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site-dir", type=Path, required=True)
    ap.add_argument("--skip-assets", action="store_true")
    ap.add_argument(
        "--only",
        action="append",
        default=[],
        help="Write only these page paths (e.g. slots.html). Technical pages skipped unless listed.",
    )
    args = ap.parse_args()
    only_pages = {str(p).strip().lstrip("/") for p in args.only if str(p).strip()}
    site_dir = (ROOT / args.site_dir).resolve() if not args.site_dir.is_absolute() else args.site_dir
    site_slug = site_dir.name

    env_path = ROOT / ".env"
    env = _load_env(env_path)
    for k, v in env.items():
        os.environ.setdefault(k, v)
    lc = locale_context_from_env(env, strict_keywords_match=False)
    html_lang = _html_lang(lc)
    hreflang = html_lang
    min_age = _min_age(lc)
    site_name = _site_display_name(site_dir, lc)
    ui = OwUi.from_lc(lc, site_name)

    site_origin = (os.getenv("SITE_URL") or "https://example.invalid").strip().rstrip("/")
    main_url = (os.getenv("MAIN_CASINO_URL") or "https://cazilla.casino").strip()
    cta = (
        f'<a href="{html_lib.escape(main_url, quote=True)}" rel="noopener noreferrer" target="_blank">'
        f"{html_lib.escape(ui.cta_label)}</a>"
    )

    kw_path = site_dir / "_output" / "keywords.json"
    if not kw_path.exists():
        raise SystemExit(f"Missing {kw_path}")
    data = json.loads(kw_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("keywords.json must be an object (v2)")

    if not args.skip_assets:
        if not ASSET_SRC.is_dir():
            raise SystemExit(f"Missing asset source: {ASSET_SRC}")
        copy_assets(site_dir, site_slug)
        print("Copied assets ->", (site_dir / "assets").relative_to(ROOT))

    legal_footer = _collect_legal_footer(data)
    menu_items = _content_menu_items(data)
    cookie_rel = "cookie-policy.html"
    for rel, _ in legal_footer:
        if "cookie" in rel:
            cookie_rel = rel
            break

    for rel, page in _kw_pages(data):
        if only_pages and rel not in only_pages:
            continue
        kw = _first_kw(page)
        title = _title_from_kw(kw, ui)
        desc = _desc_from_kw(kw, lc, ui)
        label = str(page.get("menu_label") or page.get("id") or "Page").strip()
        cookie_href = _rel_href(rel, cookie_rel)
        compliance = _compliance_block(ui, cookie_href=cookie_href)
        footer_nav = _footer_legal_nav(_ap(rel), legal_footer)
        footer_note = html_lib.escape(_short_footer(lc, ui))
        drawer_nav = _drawer_nav_html(from_rel=rel, items=menu_items, current_rel=rel)
        if _is_slots_catalog(site_slug, rel):
            doc = _shell_slots_catalog(
                rel=rel,
                site_origin=site_origin,
                html_lang=html_lang,
                hreflang=hreflang,
                min_age=min_age,
                site_name=site_name,
                title=title,
                description=desc,
                hero_h1=label,
                hero_lead=_placeholder_lead(lc, ui, cta),
                seo_inner=_slots_seo_placeholder(lc),
                footer_legal_inner=footer_note,
                compliance_html=compliance,
                footer_legal_nav=footer_nav,
                drawer_nav=drawer_nav,
                header_cta_href=main_url,
                ui=ui,
                lc=lc,
            )
        elif _is_about_trust(site_slug, rel):
            about_h1 = "À propos de Cazilla" if lc.lang == "fr" else "About Cazilla"
            doc = _shell_about_trust(
                rel=rel,
                site_origin=site_origin,
                html_lang=html_lang,
                hreflang=hreflang,
                min_age=min_age,
                site_name=site_name,
                title=title,
                description=desc,
                hero_h1=about_h1,
                hero_lead=_placeholder_lead(lc, ui, cta),
                seo_inner=_about_seo_placeholder(lc),
                footer_legal_inner=footer_note,
                compliance_html=compliance,
                footer_legal_nav=footer_nav,
                drawer_nav=drawer_nav,
                header_cta_href=main_url,
                ui=ui,
                lc=lc,
            )
        elif _is_bonus_catalog(site_slug, rel):
            doc = _shell_bonus_catalog(
                rel=rel,
                site_origin=site_origin,
                html_lang=html_lang,
                hreflang=hreflang,
                min_age=min_age,
                site_name=site_name,
                title=title,
                description=desc,
                hero_h1=label,
                hero_lead=_placeholder_lead(lc, ui, cta),
                expert_inner=html_lib.escape(_bonus_expert_placeholder(lc)),
                seo_inner=_bonus_seo_placeholder(lc),
                faq_inner=_bonus_faq_stub(lc),
                footer_legal_inner=footer_note,
                compliance_html=compliance,
                footer_legal_nav=footer_nav,
                drawer_nav=drawer_nav,
                header_cta_href=main_url,
                ui=ui,
                lc=lc,
            )
        elif _is_hub_index(site_slug, rel):
            doc = _shell_home_hub(
                rel=rel,
                site_origin=site_origin,
                html_lang=html_lang,
                hreflang=hreflang,
                min_age=min_age,
                site_name=site_name,
                title=title,
                description=desc,
                hero_h1=label,
                hero_lead=_placeholder_lead(lc, ui, cta),
                prose_inner=_hub_prose_placeholder(lc),
                footer_legal_inner=footer_note,
                compliance_html=compliance,
                footer_legal_nav=footer_nav,
                drawer_nav=drawer_nav,
                hub_chips=_hub_chips_html(ap=_ap(rel), lc=lc, pages=menu_items),
                hub_slots=_hub_slots_preview(ap=_ap(rel), lc=lc),
                hub_faq=_hub_faq_stub(lc),
                header_cta_href=main_url,
                ui=ui,
            )
        else:
            doc = _shell(
                rel=rel,
                site_origin=site_origin,
                html_lang=html_lang,
                hreflang=hreflang,
                min_age=min_age,
                site_name=site_name,
                title=title,
                description=desc,
                include_agg=False,
                hero_h1=label,
                hero_lead=_placeholder_lead(lc, ui, cta),
                prose_inner="          <p>Placeholder body.</p>\n",
                footer_legal_inner=footer_note,
                compliance_html=compliance,
                footer_legal_nav=footer_nav,
                ui=ui,
            )
        out = site_dir / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(doc, encoding="utf-8")
        print("Wrote", out.relative_to(ROOT))

    for rel, h1, para in _technical_pages(data):
        if only_pages and rel not in only_pages:
            continue
        cookie_href = _rel_href(rel, cookie_rel)
        compliance = _compliance_block(ui, cookie_href=cookie_href)
        footer_nav = _footer_legal_nav(_ap(rel), legal_footer)
        title = f"{h1}{ui.title_suffix}"[:58]
        if lc.lang == "fr":
            desc = f"{h1} — informations pour {lc.audience_phrase} ({min_age}+)."[:135]
            lead = f"Informations de référence pour {lc.audience_phrase}. {cta}"
        else:
            desc = f"{h1} information for {lc.audience_phrase} ({min_age}+)."[:135]
            lead = f"Reference information for {lc.audience_phrase}. {cta}"
        doc = _shell(
            rel=rel,
            site_origin=site_origin,
            html_lang=html_lang,
            hreflang=hreflang,
            min_age=min_age,
            site_name=site_name,
            title=title,
            description=desc[:138],
            include_agg=False,
            hero_h1=h1,
            hero_lead=lead,
            prose_inner=f"          <p>{html_lib.escape(para)}</p>\n",
            footer_legal_inner=footer_note,
            compliance_html=compliance,
            footer_legal_nav=footer_nav,
            ui=ui,
        )
        out = site_dir / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(doc, encoding="utf-8")
        print("Wrote technical", out.relative_to(ROOT))

    write_robots_sitemap(site_dir, site_origin, data, hreflang)
    fix_keywords_meta(kw_path, site_slug, lc.locale)
    print("Wrote robots.txt, sitemap.xml, .htaccess")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
