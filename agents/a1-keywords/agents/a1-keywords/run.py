#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

ROOT = Path(__file__).resolve().parents[4]
ENV_PATH = ROOT / ".env"
HERE = Path(__file__).resolve().parent

# Optional: map ISO geo codes to DataForSEO location_name when DATAFORSEO_LOCATION_NAME is unset.
GEO_TO_LOCATION_NAME: Dict[str, str] = {
    "IE": "Ireland",
    "BE": "Belgium",
    "NL": "Netherlands",
    "FR": "France",
    "DE": "Germany",
    "GB": "United Kingdom",
    "UK": "United Kingdom",
    "US": "United States",
    "CA": "Canada",
    "AU": "Australia",
}

# language_code -> language_name for DataForSEO when using location_name mode
LANG_CODE_TO_NAME: Dict[str, str] = {
    "en": "English",
    "fr": "French",
    "de": "German",
    "nl": "Dutch",
    "es": "Spanish",
    "it": "Italian",
    "pt": "Portuguese",
}


def load_env(path: Path) -> Dict[str, str]:
    env: Dict[str, str] = {}
    if not path.exists():
        return env
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    return env


def _int_env(name: str) -> Optional[int]:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def resolve_location_language() -> Tuple[Dict[str, Any], str]:
    """
    Build DataForSEO Labs location/language fields.
    Prefer explicit DATAFORSEO_LOCATION_CODE + TARGET_LANG (language_code).
    Else use DATAFORSEO_LOCATION_NAME or TARGET_GEO map + language_name from TARGET_LANG.
    """
    loc_code = _int_env("DATAFORSEO_LOCATION_CODE")
    lang_code = (os.getenv("TARGET_LANG") or os.getenv("DATAFORSEO_LANGUAGE_CODE") or "en").strip().lower()

    if loc_code is not None:
        payload: Dict[str, Any] = {
            "location_code": loc_code,
            "language_code": lang_code,
        }
        return payload, f"location_code={loc_code}, language_code={lang_code}"

    loc_name = (os.getenv("DATAFORSEO_LOCATION_NAME") or "").strip()
    if not loc_name:
        geo = (os.getenv("TARGET_GEO") or "").strip().upper()
        if geo:
            loc_name = GEO_TO_LOCATION_NAME.get(geo, "")
    if not loc_name:
        raise SystemExit(
            "Set one of: DATAFORSEO_LOCATION_CODE (integer), DATAFORSEO_LOCATION_NAME, "
            "or TARGET_GEO to a supported ISO code (e.g. IE) — see GEO_TO_LOCATION_NAME in run.py."
        )

    lang_name = (os.getenv("DATAFORSEO_LANGUAGE_NAME") or "").strip()
    if not lang_name:
        lang_name = LANG_CODE_TO_NAME.get(lang_code, lang_code.capitalize())

    payload = {
        "location_name": loc_name,
        "language_name": lang_name,
    }
    return payload, f"location_name={loc_name!r}, language_name={lang_name!r}"


def _parse_seeds_text(raw: str) -> List[str]:
    raw = raw.strip()
    if not raw:
        return []
    if raw.startswith("{") or raw.startswith("["):
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(x).strip() for x in data if str(x).strip()]
        if isinstance(data, dict) and "seed_keywords" in data:
            return [str(x).strip() for x in data["seed_keywords"] if str(x).strip()]
        raise SystemExit("Seed JSON must be an array or {\"seed_keywords\": [...]}")
    return [ln.strip() for ln in raw.splitlines() if ln.strip() and not ln.strip().startswith("#")]


def load_seed_keywords(seeds_file: Optional[Path]) -> List[str]:
    if seeds_file is not None and seeds_file.exists():
        return _parse_seeds_text(seeds_file.read_text(encoding="utf-8", errors="replace"))

    raw_json = (os.getenv("DATAFORSEO_SEED_KEYWORDS") or "").strip()
    if raw_json:
        data = json.loads(raw_json)
        if isinstance(data, list):
            return [str(x).strip() for x in data if str(x).strip()]
        if isinstance(data, dict) and "seed_keywords" in data:
            return [str(x).strip() for x in data["seed_keywords"] if str(x).strip()]
        raise SystemExit("DATAFORSEO_SEED_KEYWORDS must be a JSON array or {\"seed_keywords\": [...]}")

    path_env = (os.getenv("SEED_KEYWORDS_FILE") or "").strip()
    if path_env:
        p = Path(path_env)
        if not p.is_absolute():
            p = ROOT / p
        if p.exists():
            return load_seed_keywords(p)
        raise SystemExit(f"SEED_KEYWORDS_FILE not found: {p}")

    site_dir = (os.getenv("SITE_DIR") or "").strip()
    if site_dir:
        candidate = ROOT / site_dir / "_output" / "seed_keywords.json"
        if candidate.exists():
            return load_seed_keywords(candidate)

    raise SystemExit(
        "No seed keywords. Provide one of:\n"
        "  - DATAFORSEO_SEED_KEYWORDS='[\"seed one\",\"seed two\"]' in .env\n"
        "  - SEED_KEYWORDS_FILE=path/to/seeds.json (or .txt one keyword per line)\n"
        "  - {SITE_DIR}/_output/seed_keywords.json with {\"seed_keywords\": [...]} or a JSON array\n"
        "  - or pass --seeds-file path"
    )


def get_related_keywords(
    seed: str,
    *,
    login: str,
    password: str,
    location_payload: Dict[str, Any],
    min_volume: int,
) -> List[Dict[str, Any]]:
    body: Dict[str, Any] = {
        "keyword": seed,
        "limit": 200,
        "filters": [["keyword_data.keyword_info.search_volume", ">=", min_volume]],
        "order_by": ["keyword_data.keyword_info.search_volume,desc"],
    }
    body.update(location_payload)

    r = requests.post(
        "https://api.dataforseo.com/v3/dataforseo_labs/google/related_keywords/live",
        auth=(login, password),
        json=[body],
        timeout=120,
    )
    if r.status_code != 200:
        raise RuntimeError(f"DataForSEO HTTP {r.status_code}: {r.text[:500]}")

    data = r.json()
    task = data["tasks"][0]
    print("  status:", task.get("status_code"), task.get("status_message"))
    result = task.get("result")
    if not result or not result[0].get("items"):
        return []
    out: List[Dict[str, Any]] = []
    for item in result[0]["items"]:
        kw = item.get("keyword_data") or item
        keyword = kw.get("keyword") or (kw.get("keyword_info") or {}).get("keyword")
        if not keyword:
            continue
        keyword_info = kw.get("keyword_info") or {}
        keyword_properties = kw.get("keyword_properties") or {}
        out.append(
            {
                "keyword": keyword,
                "search_volume": int(keyword_info.get("search_volume") or 0),
                "keyword_difficulty": float(keyword_properties.get("keyword_difficulty") or 0),
                "cpc": float(keyword_info.get("cpc") or 0),
                "competition": keyword_info.get("competition_level", "") or "",
            }
        )
    return out


def output_dir() -> Path:
    site_dir = (os.getenv("SITE_DIR") or "").strip()
    if site_dir:
        d = ROOT / site_dir / "_output"
        d.mkdir(parents=True, exist_ok=True)
        return d
    d = HERE / "output"
    d.mkdir(parents=True, exist_ok=True)
    return d


def run(seeds_file: Optional[Path]) -> None:
    env = load_env(ENV_PATH)
    for k, v in env.items():
        os.environ.setdefault(k, v)

    login = os.getenv("DATAFORSEO_LOGIN") or ""
    password = os.getenv("DATAFORSEO_PASSWORD") or ""
    if not login or not password:
        raise SystemExit("Missing DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD in .env or environment.")

    location_payload, loc_desc = resolve_location_language()
    min_volume = _int_env("DATAFORSEO_MIN_SEARCH_VOLUME")
    if min_volume is None:
        min_volume = 50

    seeds = load_seed_keywords(seeds_file)
    if not seeds:
        raise SystemExit("Seed keyword list is empty.")

    print("=== A1 Keywords Agent ===")
    print("Location:", loc_desc)
    print("Min search volume:", min_volume)
    print("Seeds:", len(seeds))

    all_kw: List[Dict[str, Any]] = []
    for seed in seeds:
        print("Fetching:", seed)
        kws = get_related_keywords(
            seed,
            login=login,
            password=password,
            location_payload=location_payload,
            min_volume=min_volume,
        )
        print("  ->", len(kws), "keywords")
        all_kw.extend(kws)

    seen: set[str] = set()
    unique = [k for k in all_kw if k["keyword"] not in seen and not seen.add(k["keyword"])]
    filtered = sorted(unique, key=lambda x: (x["search_volume"], x["keyword_difficulty"]), reverse=True)

    out_dir = output_dir()
    csv_path = out_dir / "keywords.csv"
    json_path = out_dir / "keywords.json"

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["keyword", "search_volume", "keyword_difficulty", "cpc", "competition"])
        w.writeheader()
        w.writerows(filtered)
    json_path.write_text(json.dumps(filtered, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nSaved:", json_path)
    print("Saved:", csv_path)
    print("\nFound:", len(filtered), "keywords")
    for k in filtered[:10]:
        print(" ", k["keyword"], "| vol:", k["search_volume"], "| KD:", k["keyword_difficulty"], "| CPC:", k["cpc"])


def main(argv: List[str]) -> int:
    p = argparse.ArgumentParser(description="A1: fetch related keywords from DataForSEO Labs.")
    p.add_argument(
        "--seeds-file",
        type=Path,
        default=None,
        help="JSON array, {\"seed_keywords\": [...]}, or one keyword per line.",
    )
    args = p.parse_args(argv)
    run(seeds_file=args.seeds_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
