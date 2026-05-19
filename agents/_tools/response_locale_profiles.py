"""Locale-specific copy and theme overrides for response-site generator."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

FR_BE_THEME_CSS = """/* Cazilla response1-fr-be — Belgian editorial (teal / coral) */
:root {
  --rs-navy: #0d3d38;
  --rs-navy-dark: #062824;
  --rs-accent: #d64545;
  --rs-accent-hover: #b83838;
  --rs-bg: #f0f7f6;
  --rs-card: #ffffff;
  --rs-ink: #0f1f1e;
  --rs-muted: #5a6f6c;
  --rs-line: #cfe5e1;
  --rs-star: #e8a317;
  --rs-star-empty: #c5d9d5;
  --rs-success: #0d7a5f;
  --rs-max: 1100px;
}

body {
  background-image: linear-gradient(165deg, #f7fcfb 0%, var(--rs-bg) 45%, #e8f2f0 100%);
}

.hero h1,
.sectionHead h2,
.rs-section h2,
.rs-section h3,
.reviewTitle {
  color: var(--rs-navy);
  letter-spacing: -0.02em;
}

.topbar {
  background: var(--rs-navy-dark);
  border-bottom: 3px solid var(--rs-accent);
}

.logoMark {
  background: linear-gradient(135deg, var(--rs-accent), #f08080);
  color: #fff;
}

.btn.primary {
  background: var(--rs-accent);
  border-color: var(--rs-accent);
  color: #fff;
  font-weight: 700;
}

.btn.primary:hover {
  background: var(--rs-accent-hover);
  border-color: var(--rs-accent-hover);
}

.rs-sidebar a:hover,
.rs-sidebar a.is-active {
  background: #e6f4f1;
  color: var(--rs-navy);
}

.rs-ribbon {
  background: #e6f4f1;
  border-bottom: 1px solid var(--rs-line);
  color: var(--rs-navy);
}

.rs-score-pill {
  background: var(--rs-navy);
  color: #fff;
}

.rs-toc a:hover {
  border-color: var(--rs-accent);
  color: var(--rs-accent);
}

.rs-gallery-viewport {
  background: linear-gradient(145deg, #062824 0%, #0d3d38 100%);
}

.rs-gallery-viewport img {
  object-fit: contain;
  object-position: center;
}

.rs-gallery-dots button.is-active {
  background: var(--rs-accent);
}

.tag {
  background: #e6f4f1;
  color: var(--rs-navy);
}

.heroActions .btn.primary {
  background: var(--rs-success);
  border-color: var(--rs-success);
}
"""


def fr_be_compliance_block():
    return '<div class="complianceOverlay" id="ageGate" role="dialog" aria-modal="true" aria-labelledby="ageTitle">\n  <div class="complianceDialog">\n    <h2 id="ageTitle">Confirmez que vous avez 21 ans ou plus</h2>\n    <p>Ce site traite des jeux d’argent réglementés pour lecteurs en Belgique. Vous devez avoir au moins 21 ans pour continuer.</p>\n    <div class="complianceActions">\n      <button type="button" class="btn" id="ageUnder">J’ai moins de 21 ans</button>\n      <button type="button" class="btn primary" id="ageOk">J’ai 21 ans ou plus</button>\n    </div>\n  </div>\n</div>\n<div class="complianceOverlay" id="cookieGate" hidden aria-hidden="true" role="dialog" aria-modal="true" aria-labelledby="cookieTitle">\n  <div class="complianceDialog">\n    <h2 id="cookieTitle">Préférences cookies</h2>\n    <p>Nous utilisons des cookies pour mémoriser la vérification d’âge. Voir <a href="cookie-policy.html">politique de cookies</a>.</p>\n    <div class="complianceActions">\n      <button type="button" class="btn" id="cookieReject">Essentiels uniquement</button>\n      <button type="button" class="btn primary" id="cookieAccept">Accepter</button>\n    </div>\n  </div>\n</div>'


def apply_fr_be_profile(globals_dict: dict) -> None:
    """Mutate generator module globals for fr-BE response sites."""
    g = globals_dict
    g["HTML_LANG"] = "fr-BE"
    g["MIN_AGE"] = 21
    g["HREFLANG"] = "fr-BE"
    g["OG_LOCALE"] = "fr_BE"
    g["SITE_NAME"] = "Cazilla Expert Belgique"
    g["STUB"] = "Texte éditorial provisoire. A2 remplacera par un avis expert pour la Belgique."
    g["THEME_CSS_FILE"] = "rs-response1-fr-be-theme.css"
    g["THEME_CSS_BODY"] = FR_BE_THEME_CSS
    g["INDEX_TITLE"] = "Avis expert Cazilla | Casino en ligne Belgique"
    g["INDEX_DESC"] = "Test indépendant de Cazilla pour joueurs en Belgique : licence, bonus, paiements, jeux et verdict éditorial."
    g["HERO_H1_DEFAULT"] = "Avis expert Cazilla — casino en ligne Belgique"
    g["RIBBON"] = "Avis expert indépendant pour la Belgique (fr-BE). Nous n’exploitons pas de casino."
    g["DISCLAIMER"] = "21+ uniquement. Le jeu comporte des risques. Utilisez des opérateurs agréés."
    g["SCORE_META"] = "Note test éditorial"
    g["CTA_OFFICIAL"] = "Site officiel"
    g["CTA_VISIT"] = "Jouer sur Cazilla"
    g["FOOTER_POLICIES_H2"] = "Mentions légales"
    g["FOOTER_COOKIE"] = "Politique de cookies"
    g["BACK_REVIEW"] = "Retour à l’avis"
    g["LEGAL_RIBBON"] = "Informations juridiques pour lecteurs en Belgique"
    g["GALLERY_PREV"] = "Précédent"
    g["GALLERY_NEXT"] = "Suivant"
    g["PROS_LABEL"] = "Points forts"
    g["CONS_LABEL"] = "Points faibles"
    g["COMMENTS_H2"] = "Commentaires des lecteurs"
    g["FAQ_H2"] = "FAQ"
    g["AUTHOR_H2"] = "À propos de l’auteur"
    g["INTRO_H2"] = "Introduction"
    g["OVERVIEW_TABLE_ARIA"] = "Cazilla en bref"
    g["OVERVIEW_ROWS"] = [
        ("Licence", "Autorité compétente (MGA / agrément BE selon offre)"),
        ("Bonus de bienvenue", "Match premier dépôt + tours gratuits (conditions de mise variables)"),
        ("Dépôt minimum", "10 €"),
        ("Délai de retrait", "Portefeuilles ~24 h ; cartes 1–3 jours ouvrables"),
        ("Fournisseurs", "40+ (NetEnt, Pragmatic Play, Evolution, Play'n GO)"),
        ("Mobile", "Site responsive — catalogue complet iOS et Android"),
    ]
    g["SECTION_SPECS"] = [
        ("rs-overview", "Vue d’ensemble et méthode", "overview_section"),
        ("rs-licence", "Licence et sécurité", "licence_section"),
        ("rs-design", "Design et ergonomie", "design_section"),
        ("rs-bonuses", "Bonus et promotions", "bonus_section"),
        ("rs-vip", "Programme VIP", "vip_section"),
        ("rs-payments", "Paiements et retraits", "payments_section"),
        ("rs-games", "Jeux et fournisseurs", "games_section"),
        ("rs-comparison", "Comparaison avec d’autres sites", "comparison_section"),
        ("rs-summary", "Synthèse et verdict", "summary_section"),
    ]
    g["SIDEBAR_NAV"] = [
        ("Tests et classements", [("Tests casino", "#rs-overview"), ("Meilleurs casinos 2026", "#rs-comparison"), ("Nouveaux casinos", "#rs-intro")]),
        ("Live et paiements", [("Casino live", "#rs-games"), ("Paiements", "#rs-payments"), ("Plafonds de retrait", "#rs-payments")]),
        ("Bonus", [("Bonus de bienvenue", "#rs-bonuses"), ("Recharges", "#rs-bonuses"), ("Cashback", "#rs-bonuses"), ("Programme VIP", "#rs-vip")]),
        ("Jeux", [("Machines à sous", "#rs-games"), ("Roulette", "#rs-games"), ("Blackjack", "#rs-games"), ("Par fournisseur", "#rs-games")]),
        ("Guides", [("Comment choisir", "#rs-faq"), ("Aide", "#rs-summary")]),
    ]
    g["TOC_LINKS"] = [
        ("Licence", "#rs-licence"),
        ("Design", "#rs-design"),
        ("Bonus", "#rs-bonuses"),
        ("VIP", "#rs-vip"),
        ("Paiements", "#rs-payments"),
        ("Jeux", "#rs-games"),
        ("FAQ", "#rs-faq"),
        ("Synthèse", "#rs-summary"),
    ]
    g["TOP_NAV"] = [
        ("Vue d’ensemble", "#rs-overview"),
        ("Bonus", "#rs-bonuses"),
        ("Paiements", "#rs-payments"),
        ("FAQ", "#rs-faq"),
        ("Synthèse", "#rs-summary"),
    ]
    g["FOOTER_LEGAL"] = [
        ("user-agreement.html", "Conditions d’utilisation"),
        ("cookie-policy.html", "Politique de cookies"),
        ("fair-play.html", "Jeu équitable"),
        ("payments-withdrawals.html", "Paiements et retraits"),
        ("privacy-policy.html", "Politique de confidentialité"),
        ("responsible-gambling.html", "Jeu responsable"),
        ("aml-kyc.html", "AML et KYC"),
    ]
    g["PAGE_COMMENTS"] = [
        {"initials": "LM", "name": "Luc M.", "date": "8 mai 2026", "stars": "★★★★★", "title": "Bonus clairs", "body": "Conditions de mise lisibles. Retrait sur carte belge en deux jours ouvrables après KYC.", "tags": "bonus,retrait"},
        {"initials": "SV", "name": "Sophie V.", "date": "22 avr. 2026", "stars": "★★★★☆", "title": "Bon catalogue slots", "body": "Large choix de machines à sous, filtres pratiques sur mobile.", "tags": "slots,mobile"},
        {"initials": "JD", "name": "Jonas D.", "date": "5 avr. 2026", "stars": "★★★★☆", "title": "VIP accessible", "body": "Cashback atteint sans grind excessif. Chat en direct réactif.", "tags": "vip,support"},
    ]
    g["USE_FR_COMPLIANCE"] = True


def is_fr_be_site(env: dict, slug: str) -> bool:
    loc = (env.get("TARGET_LOCALE") or "").strip().lower()
    return loc == "fr-be" or slug.lower().endswith("fr-be")
