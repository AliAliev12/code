## Agent-Based SEO Site Factory (pipeline spec)

This repo contains static sites under `sites/` and a set of agents to generate, QA, and iteratively fix the output.

### Core idea
`generate → QA → fix → QA → decision → publish`

### Artifacts (source of truth)
- **Keywords**: if `SITE_DIR` is set in `.env` (for example `sites/cazilla-review-en-ie`), A1 writes `<SITE_DIR>/_output/keywords.json` (and `.csv`); otherwise `agents/a1-keywords/agents/a1-keywords/output/keywords.*`. A2 reads `<SITE_DIR>/_output/keywords.json` first when `SITE_DIR` is set.
  - **Overwrite guard**: A1 generators now refuse to overwrite an existing `keywords.json` by default. To intentionally replace it, pass `--allow-overwrite` (for `a1-keywords`) or set `ALLOW_KEYWORDS_OVERWRITE=1`.
  - **v2 bundle** (optional): `keywords.json` may be an object with `version: 2`, `pages[]`, optional `technical_pages[]`, `reserve[]`. Legacy format remains a **JSON array** of keyword rows (v1). Parser: `agents/_lib/keywords_bundle.py`.
  - **A2**: `--page-id` or `PAGE_ID` selects a v2 page; `output/content.json` includes `target_page_id`, `target_html_path`, `keywords_bundle_version`.
  - **v2 example** (each `pages` / `technical_pages` item: `id`, `path` relative to site root, `keywords` array; optional `qa_profile`: `standard` | `technical` — technical relaxes minimum H2 count):

```json
{
  "version": 2,
  "pages": [
    { "id": "home", "path": "index.html", "keywords": [ { "keyword": "example", "search_volume": 100, "keyword_difficulty": 0, "cpc": 0 } ] }
  ],
  "technical_pages": [],
  "reserve": []
}
```

- **Footer / `technical_pages`**: состав юрстраниц в футере, ключи только из `technical_pages[]`, объём **1500–3000** символов в `<main>`, генерация текста A2 (`--technical`); оболочка — `tech_page_html` + `assets/` — см. **`agents/prompts/cazilla-site-factory-ru.md`** (раздел **«Футер и технические страницы»**).

- **Site output**: `<SITE_DIR>/**/index.html` + `assets/*` + `robots.txt` + `sitemap.xml`
- **QA outputs** (written to `output/`):
  - `qa_smoke.json` — link/anchor/meta/asset smoke checks (P0/P1/P2)
  - `qa_report.json` — SEO + keyword density; includes `pages[]` per audited HTML when multiple targets exist, rollup `status`, and `results` (flat merged checks with optional `page_id` in details)
  - `qa_chief.json` — final decision layer (PASS/FIX/FAIL)
  - `autofix_log.json` — deterministic autofixes applied by the orchestrator
  - `orchestrator_history.json` — iteration history

### QA gates (current)
- **P0**: blocks publish (decision `FAIL`)
- **P1**: triggers decision `FIX` (conservative, publish-ready requires 0 P1)
- **P2**: informational

### Deterministic autofixes (current)
Applied before each QA run:
- Replace `https://cazilla.casino/register` → `https://cazilla.casino/`
- Replace `og:image` pointing to `https://cazilareview.xyz/images/og-image.jpg` → `https://cazilareview.xyz/assets/bass.svg`

### Site / content factory spec (Russian prompt)

Единый промпт ТЗ (ключи, кластеры, перелинковка, регион и возрастной gate, cookies, мета title/description/ALT, объёмы текста, футер, sitemap/robots/301):

- **`agents/prompts/cazilla-site-factory-ru.md`**

Подмешать этот файл в запрос **A2** (Anthropic) к существующей JSON-схеме главной:

```bash
python3 agents/a2-content/run.py --with-site-factory-spec
```

Или в `.env`: `A2_WITH_SITE_FACTORY_SPEC=1`.

Обёртка **ключей** страницы в `<strong>` внутри `<main>` по данным `keywords.json` (при заданном `SITE_DIR`): `python3 agents/_tools/wrap_keywords_strong_in_main.py`.

### Environment (`.env`)

По умолчанию **каталог сайта и локаль** задаются в **`<корень репозитория>/.env`**: как минимум `SITE_DIR` (например `sites/cazilla-review-en-ie`), `TARGET_LOCALE`, `TARGET_LANG`; для проверок исходящих/канонических ссылок в A6 — `SITE_URL`, `MAIN_CASINO_URL`. Оркестратор, A6, A11, A12 при старте подмешивают переменные из `.env` в окружение процесса. Явный `--site-dir` у оркестратора / A11 / A6 переопределяет путь для этого запуска.

### How to run the full loop

```bash
python3 agents/orchestrator.py --site-dir sites/cazilla-review-en-ie --max-iterations 3
```

This will:
- apply deterministic autofixes
- run smoke QA (`agents/a11-smoke/run.py`)
- run SEO QA (`agents/a6-design-qa/run.py`)
- run chief QA decision (`agents/a12-chief-qa/run.py`)
- stop early on PASS

### Extending to full “factory”
Recommended next additions:
- **Content QA** agent outputting `output/qa_content.json`
- **Design QA** agent outputting `output/qa_design.json`
- Update `a12-chief-qa` to combine the three QA reports with explicit weights and conflict-resolution rules.

