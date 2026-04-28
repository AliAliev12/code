import os, json, requests, csv

LOGIN = os.getenv("DATAFORSEO_LOGIN")
PASSWORD = os.getenv("DATAFORSEO_PASSWORD")
LANG = "fr"
LOCATION_CODE = 2056  # Belgium

SEED_KEYWORDS = [
    "cazilla casino",
    "cazilla",
    "meilleur casino en ligne belgique",
    "casino en ligne belgique",
    "casino en ligne bonus",
    "casino belge en ligne",
    "jeux casino en ligne",
    "bonus casino belgique",
]

def get_related_keywords(seed):
    if not LOGIN or not PASSWORD:
        raise RuntimeError("Missing DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD env vars")

    r = requests.post(
        "https://api.dataforseo.com/v3/dataforseo_labs/google/related_keywords/live",
        auth=(LOGIN, PASSWORD),
        json=[
            {
                "keyword": seed,
                "location_code": LOCATION_CODE,
                "language_code": LANG,
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
        # DataForSEO Labs may return either a "keyword_data" object or flat fields at item root.
        kw = item.get("keyword_data") or item
        keyword = kw.get("keyword") or (kw.get("keyword_info") or {}).get("keyword")
        if not keyword:
            continue
        keyword_info = kw.get("keyword_info") or {}
        keyword_properties = kw.get("keyword_properties") or {}
        out.append({
            "keyword": keyword,
            "search_volume": keyword_info.get("search_volume") or 0,
            "keyword_difficulty": keyword_properties.get("keyword_difficulty") or 0,
            "cpc": keyword_info.get("cpc") or 0,
            "competition": keyword_info.get("competition_level", "") or "",
        })
    return out

def run():
    print("=== A1 Keywords Agent ===")
    all_kw = []
    for seed in SEED_KEYWORDS:
        print("Fetching:", seed)
        kws = get_related_keywords(seed)
        print("  ->", len(kws), "keywords")
        all_kw.extend(kws)
    seen = set()
    unique = [k for k in all_kw if k["keyword"] not in seen and not seen.add(k["keyword"])]
    filtered = sorted([k for k in unique if k["search_volume"] >= 50], key=lambda x: x["search_volume"], reverse=True)
    os.makedirs("output", exist_ok=True)
    with open("output/keywords.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["keyword","search_volume","keyword_difficulty","cpc","competition"])
        w.writeheader()
        w.writerows(filtered)
    with open("output/keywords.json", "w", encoding="utf-8") as f:
        json.dump(filtered, f, ensure_ascii=False, indent=2)
    print("\nFound:", len(filtered), "keywords")
    for k in filtered[:10]:
        print(" ", k["keyword"], "| vol:", k["search_volume"], "| KD:", k["keyword_difficulty"], "| CPC:", k["cpc"])

if __name__ == "__main__":
    run()
