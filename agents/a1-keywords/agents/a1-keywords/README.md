# A1 Keywords (DataForSEO)

Fetches **related keywords** from DataForSEO Labs and writes `keywords.json` + `keywords.csv`.

## Environment (repo root `.env`)

Required:

- `DATAFORSEO_LOGIN`, `DATAFORSEO_PASSWORD`

Location + language (pick one style):

1. **Numeric location (recommended for precision)**  
   - `DATAFORSEO_LOCATION_CODE` — e.g. `2372` for Ireland (see DataForSEO locations).  
   - `TARGET_LANG` or `DATAFORSEO_LANGUAGE_CODE` — e.g. `en`

2. **Named location**  
   - `DATAFORSEO_LOCATION_NAME` — e.g. `Ireland`  
   - `DATAFORSEO_LANGUAGE_NAME` — e.g. `English` (optional; derived from `TARGET_LANG` if omitted)  
   - Or set `TARGET_GEO=IE` and use the built-in map to `Ireland` when `DATAFORSEO_LOCATION_NAME` is empty.

Optional:

- `SITE_DIR` — if set (e.g. `sites/cazilla-review2-en-ie`), output goes to `{SITE_DIR}/_output/keywords.json` under the repo root. Otherwise output is `agents/a1-keywords/agents/a1-keywords/output/`.
- `DATAFORSEO_MIN_SEARCH_VOLUME` — default `50`.
- `DATAFORSEO_SEED_KEYWORDS` — JSON array of seed strings, e.g. `["online casino","cazilla"]`.
- `SEED_KEYWORDS_FILE` — path to a file (repo-relative or absolute): JSON array, `{"seed_keywords":[...]}`, or one keyword per line.

Seeds resolution order:

1. `--seeds-file` CLI argument  
2. `DATAFORSEO_SEED_KEYWORDS` in `.env`  
3. `SEED_KEYWORDS_FILE`  
4. `{SITE_DIR}/_output/seed_keywords.json` if `SITE_DIR` is set and the file exists  

## Run

From repo root:

```bash
set -a && source .env && set +a
python3 agents/a1-keywords/agents/a1-keywords/run.py
```

With explicit seeds file:

```bash
python3 agents/a1-keywords/agents/a1-keywords/run.py --seeds-file sites/cazilla-review2-en-ie/_output/seed_keywords.json
```

## Output shape

Each row is an object with `keyword`, `search_volume`, `keyword_difficulty`, `cpc`, and optional `competition` — compatible with agent `A2`.
