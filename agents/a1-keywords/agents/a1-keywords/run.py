import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any, Dict, List

import requests

LOGIN = os.getenv("DATAFORSEO_LOGIN")
PASSWORD = os.getenv("DATAFORSEO_PASSWORD")

DEFAULT_SEED_KEYWORDS = [
    "cazilla casino",
    "cazilla",
    "meilleur casino en ligne belgique",
    "casino en ligne belgique",
    "casino en ligne bonus",
    "casino belge en ligne",
    "jeux casino en ligne",
    "bonus casino belgique",
]


def get_related_keywords(seed: str, *, lang: str, location_code: int) -> List[Dict[str, Any]]:
    if not LOGIN or not PASSWORD:
        raise RuntimeError("Missing DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD env vars")

    r = requests.post(
        "https://api.dataforseo.com/v3/dataforseo_labs/google/related_keywords/live",
        auth=(LOGIN, PASSWORD),
        json=[
            {
                "keyword": seed,
                "location_code": location_code,
                "language_code": lang,
                "limit": 200,
                "filters": [["keyword_data.keyword_info.search_volume", ">=", 50]],
                "order_by": ["keyword_data.keyword_info.search_volume,desc"],
            }
        ],
        timeout=60,
    )
    if r.status_code != 200:
        raise RuntimeError(f"DataForSEO HTTP {r.status_code}: {r.text[:500]}")

    data = r.json()
    task = data["tasks"][0]
    print("  status:", task["status_code"], task["status_message"])
    result = task.get("result")
    if not result or not result[0].get("items"):
        return []
    out = []
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
                "search_volume": keyword_info.get("search_volume") or 0,
                "keyword_difficulty": keyword_properties.get("keyword_difficulty") or 0,
                "cpc": keyword_info.get("cpc") or 0,
                "competition": keyword_info.get("competition_level", "") or "",
            }
        )
    return out


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default=os.getenv("SITE_OUTPUT_DIR", "output"))
    ap.add_argument("--lang", default=os.getenv("A1_LANG", "fr"))
    ap.add_argument("--location-code", type=int, default=int(os.getenv("A1_LOCATION_CODE", "2056")))
    ap.add_argument("--seed", action="append", default=[])
    ap.add_argument("--seeds-file", default="")
    return ap.parse_args()


def resolve_seeds(args: argparse.Namespace) -> List[str]:
    seeds = [s.strip() for s in args.seed if str(s).strip()]
    if args.seeds_file:
        p = Path(args.seeds_file).resolve()
        if not p.exists():
            raise SystemExit(f"--seeds-file not found: {p}")
        for raw in p.read_text(encoding="utf-8", errors="replace").splitlines():
            s = raw.strip()
            if s and not s.startswith("#"):
                seeds.append(s)
    return seeds if seeds else DEFAULT_SEED_KEYWORDS[:]


def run() -> None:
    args = parse_args()
    seeds = resolve_seeds(args)
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=== A1 Keywords Agent ===")
    all_kw = []
    for seed in seeds:
        print("Fetching:", seed)
        kws = get_related_keywords(seed, lang=args.lang, location_code=args.location_code)
        print("  ->", len(kws), "keywords")
        all_kw.extend(kws)
    seen = set()
    unique = [k for k in all_kw if k["keyword"] not in seen and not seen.add(k["keyword"])]
    filtered = sorted([k for k in unique if k["search_volume"] >= 50], key=lambda x: x["search_volume"], reverse=True)
    with (out_dir / "keywords.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["keyword", "search_volume", "keyword_difficulty", "cpc", "competition"])
        w.writeheader()
        w.writerows(filtered)
    (out_dir / "keywords.json").write_text(json.dumps(filtered, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nFound:", len(filtered), "keywords")
    for k in filtered[:10]:
        print(" ", k["keyword"], "| vol:", k["search_volume"], "| KD:", k["keyword_difficulty"], "| CPC:", k["cpc"])


if __name__ == "__main__":
    run()
