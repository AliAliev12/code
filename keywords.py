python3 - <<'PY'
import os, json, base64, urllib.request
from pathlib import Path

ROOT = Path("/home/yegor/Git/AliAliev12/code")
ENV_PATH = ROOT / ".env"
INPUT_PATH = ROOT / "keywords.txt"   # <-- входной файл со списком ключей

def load_env(path: Path):
    env = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        env[k.strip()] = v.strip()
    return env

def post_json(url, login, password, payload):
    token = base64.b64encode(f"{login}:{password}".encode()).decode()
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))

env = load_env(ENV_PATH)

login = env.get("DATAFORSEO_LOGIN", "")
password = env.get("DATAFORSEO_PASSWORD", "")
if not login or not password:
    raise SystemExit("Missing DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD in .env")

if not INPUT_PATH.exists():
    raise SystemExit(f"Input file not found: {INPUT_PATH}")

target_lang = (env.get("TARGET_LANG") or "en").strip().lower()
loc_code_raw = (env.get("DATAFORSEO_LOCATION_CODE") or "").strip()
target_geo = (env.get("TARGET_GEO") or "").strip().upper()

loc_name_map = {
    "IE": "Ireland", "BE": "Belgium", "NL": "Netherlands", "FR": "France",
    "DE": "Germany", "GB": "United Kingdom", "UK": "United Kingdom",
    "US": "United States", "CA": "Canada", "AU": "Australia"
}
lang_name_map = {
    "en": "English", "fr": "French", "de": "German", "nl": "Dutch",
    "es": "Spanish", "it": "Italian", "pt": "Portuguese"
}

if loc_code_raw.isdigit():
    location_payload = {"location_code": int(loc_code_raw), "language_code": target_lang}
else:
    loc_name = (env.get("DATAFORSEO_LOCATION_NAME") or "").strip() or loc_name_map.get(target_geo, "")
    if not loc_name:
        raise SystemExit("No location found. Set DATAFORSEO_LOCATION_CODE or DATAFORSEO_LOCATION_NAME or TARGET_GEO in .env")
    lang_name = (env.get("DATAFORSEO_LANGUAGE_NAME") or "").strip() or lang_name_map.get(target_lang, target_lang.capitalize())
    location_payload = {"location_name": loc_name, "language_name": lang_name}

# read + dedupe
seen = set()
keywords = []
for ln in INPUT_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
    kw = ln.strip()
    if not kw:
        continue
    kl = kw.lower()
    if kl in seen:
        continue
    seen.add(kl)
    keywords.append(kw)

url = "https://api.dataforseo.com/v3/dataforseo_labs/google/related_keywords/live"
out = []

for kw in keywords:
    body = {"keyword": kw, "limit": 200}
    body.update(location_payload)
    row = {
        "keyword": kw,
        "search_volume": 0,
        "keyword_difficulty": 0.0,
        "cpc": 0.0,
        "competition": ""
    }
    try:
        data = post_json(url, login, password, [body])
        items = (((data.get("tasks") or [{}])[0].get("result") or [{}])[0].get("items") or [])
        exact = None
        for it in items:
            kd_obj = it.get("keyword_data") or it
            cand = (kd_obj.get("keyword") or ((kd_obj.get("keyword_info") or {}).get("keyword")) or "").strip()
            if cand.lower() == kw.lower():
                exact = kd_obj
                break

        if exact:
            ki = exact.get("keyword_info") or {}
            kp = exact.get("keyword_properties") or {}
            row = {
                "keyword": kw,
                "search_volume": int(ki.get("search_volume") or 0),
                "keyword_difficulty": float(kp.get("keyword_difficulty") or 0),
                "cpc": float(ki.get("cpc") or 0),
                "competition": (ki.get("competition_level") or "")
            }
    except Exception:
        pass

    out.append(row)

# as in A1
out.sort(key=lambda x: (x["search_volume"], x["keyword_difficulty"]), reverse=True)

site_dir = (env.get("SITE_DIR") or "").strip()
if site_dir:
    out_path = ROOT / site_dir / "_output" / "keywords.json"
else:
    out_path = ROOT / "agents/a1-keywords/agents/output/keywords.json"

out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"Saved: {out_path}")
print(f"Input unique keywords: {len(keywords)}")
PY
