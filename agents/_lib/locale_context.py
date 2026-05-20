#!/usr/bin/env python3
"""Locale / geo context from repository .env for prompts and HTML generators."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Optional, Tuple


GEO_REGION_NAMES: Dict[str, Dict[str, str]] = {
    "IE": {"en": "Ireland", "fr": "Irlande", "nl": "Ierland", "de": "Irland"},
    "BE": {"en": "Belgium", "fr": "Belgique", "nl": "België", "de": "Belgien"},
    "NL": {"en": "Netherlands", "fr": "Pays-Bas", "nl": "Nederland", "de": "Niederlande"},
    "FR": {"en": "France", "fr": "France", "nl": "Frankrijk", "de": "Frankreich"},
    "GB": {"en": "United Kingdom", "fr": "Royaume-Uni", "nl": "Verenigd Koninkrijk", "de": "Vereinigtes Königreich"},
    "UK": {"en": "United Kingdom", "fr": "Royaume-Uni", "nl": "Verenigd Koninkrijk", "de": "Vereinigtes Königreich"},
    "DE": {"en": "Germany", "fr": "Allemagne", "nl": "Duitsland", "de": "Deutschland"},
    "US": {"en": "United States", "fr": "États-Unis", "nl": "Verenigde Staten", "de": "Vereinigte Staaten"},
    "CA": {"en": "Canada", "fr": "Canada", "nl": "Canada", "de": "Kanada"},
    "AU": {"en": "Australia", "fr": "Australie", "nl": "Australië", "de": "Australien"},
}

LANG_NAMES: Dict[str, str] = {
    "en": "English",
    "fr": "French",
    "de": "German",
    "nl": "Dutch",
    "es": "Spanish",
    "it": "Italian",
    "pt": "Portuguese",
}


@dataclass(frozen=True)
class LocaleContext:
    locale: str
    lang: str
    geo: str
    region_name: str
    language_name: str
    audience_phrase: str
    player_context_phrase: str
    region_facing_label: str
    legal_tone_line: str

    @property
    def locale_tag(self) -> str:
        return self.locale


def _geo_from_locale(locale: str) -> str:
    parts = locale.replace("_", "-").split("-")
    if len(parts) >= 2 and len(parts[-1]) == 2:
        return parts[-1].upper()
    return ""


def region_name_for(geo: str, lang: str) -> str:
    g = geo.upper()
    l = lang.lower()
    names = GEO_REGION_NAMES.get(g, {})
    if l in names:
        return names[l]
    if "en" in names:
        return names["en"]
    return g or "the target region"


def audience_phrase_for(lang: str, region_name: str) -> str:
    l = lang.lower()
    if l == "fr":
        return f"lecteurs en {region_name}"
    if l == "nl":
        return f"lezers in {region_name}"
    if l == "de":
        return f"Leser in {region_name}"
    if l == "es":
        return f"lectores en {region_name}"
    return f"readers in {region_name}"


def player_context_phrase_for(lang: str, region_name: str) -> str:
    l = lang.lower()
    if l == "fr":
        return f"contexte joueur en {region_name}"
    if l == "nl":
        return f"spelerscontext in {region_name}"
    if l == "de":
        return f"Spielerkontext in {region_name}"
    return f"{region_name} player context"


def region_facing_label_for(lang: str, region_name: str) -> str:
    l = lang.lower()
    if l == "fr":
        return f"site orienté {region_name}"
    if l == "nl":
        return f"{region_name}-gerichte site"
    if l == "de":
        return f"{region_name}-orientierte Seite"
    return f"{region_name}-facing site"


def legal_tone_line_for(language_name: str, audience_phrase: str) -> str:
    return f"clear legal/informational {language_name} for {audience_phrase}"


def age_gate_body(lc: LocaleContext) -> str:
    min_age = 21 if lc.geo.upper() == "BE" else 18
    if lc.lang == "fr":
        return (
            f"Vous devez avoir {min_age} ans ou plus pour continuer. "
            f"Ce site traite des jeux d'argent réglementés pour {lc.audience_phrase}."
        )
    if lc.lang == "nl":
        return (
            f"U moet {min_age} jaar of ouder zijn om verder te gaan. "
            f"Deze site bespreekt gereguleerd gokken voor {lc.audience_phrase}."
        )
    if lc.lang == "de":
        return (
            f"Sie müssen mindestens {min_age} Jahre alt sein, um fortzufahren. "
            f"Diese Website behandelt reguliertes Glücksspiel für {lc.audience_phrase}."
        )
    return (
        f"You must be {min_age}+ to continue. "
        f"This site discusses regulated gambling for {lc.audience_phrase}."
    )


def legal_subtitle_fallback(lc: LocaleContext) -> str:
    if lc.lang == "fr":
        return f"Informations juridiques pour {lc.audience_phrase}."
    if lc.lang == "nl":
        return f"Juridische informatie voor {lc.audience_phrase}."
    if lc.lang == "de":
        return f"Rechtliche Informationen für {lc.audience_phrase}."
    return f"Legal information for {lc.audience_phrase}."


def hub_sidebar_compare_line(lc: LocaleContext) -> str:
    if lc.lang == "fr":
        return (
            f"Nous comparons les catégories du lobby pour {lc.audience_phrase} — "
            "pas la caisse de l'opérateur."
        )
    if lc.lang == "nl":
        return (
            f"We vergelijken lobby-categorieën voor {lc.audience_phrase} — "
            "niet de kassa van de operator."
        )
    return f"We compare lobby-style categories for {lc.audience_phrase} — not the operator cashier."


def hub_play_heading(lc: LocaleContext) -> str:
    if lc.lang == "fr":
        return f"Jouer sur Cazilla — {lc.region_facing_label}"
    if lc.lang == "nl":
        return f"Speel bij Cazilla — {lc.region_facing_label}"
    if lc.lang == "de":
        return f"Bei Cazilla spielen — {lc.region_facing_label}"
    return f"Play at Cazilla — {lc.region_facing_label}"


def footer_hub_tagline(site_name: str, lc: LocaleContext) -> str:
    if lc.lang == "fr":
        return f"© <span id=\"year\">2026</span> {site_name}. Site éditorial indépendant orienté {lc.region_name}."
    if lc.lang == "nl":
        return f"© <span id=\"year\">2026</span> {site_name}. Onafhankelijke redactionele hub voor {lc.region_name}."
    return f"© <span id=\"year\">2026</span> {site_name}. Independent {lc.region_facing_label}."


def require_locale_lang(env: Dict[str, str]) -> Tuple[str, str]:
    locale = (env.get("TARGET_LOCALE") or os.getenv("TARGET_LOCALE") or "").strip()
    lang = (env.get("TARGET_LANG") or os.getenv("TARGET_LANG") or "").strip().lower()
    if not locale:
        raise SystemExit("Missing TARGET_LOCALE in .env/environment.")
    if not lang:
        raise SystemExit("Missing TARGET_LANG in .env/environment.")
    return locale, lang


def locale_context_from_env(
    env: Dict[str, str],
    *,
    keywords_locale: Optional[str] = None,
    strict_keywords_match: bool = True,
) -> LocaleContext:
    locale, lang = require_locale_lang(env)
    geo = (env.get("TARGET_GEO") or os.getenv("TARGET_GEO") or "").strip().upper()
    if not geo:
        geo = _geo_from_locale(locale)
    if not geo:
        raise SystemExit("Missing TARGET_GEO in .env/environment (or use locale like fr-BE).")

    if keywords_locale and strict_keywords_match:
        kw_loc = keywords_locale.strip()
        if kw_loc and kw_loc.lower() != locale.lower():
            raise SystemExit(
                f"keywords.json locale {kw_loc!r} does not match TARGET_LOCALE {locale!r} in .env"
            )

    region = region_name_for(geo, lang)
    language_name = LANG_NAMES.get(lang, lang.capitalize())
    audience = audience_phrase_for(lang, region)
    return LocaleContext(
        locale=locale,
        lang=lang,
        geo=geo,
        region_name=region,
        language_name=language_name,
        audience_phrase=audience,
        player_context_phrase=player_context_phrase_for(lang, region),
        region_facing_label=region_facing_label_for(lang, region),
        legal_tone_line=legal_tone_line_for(language_name, audience),
    )
