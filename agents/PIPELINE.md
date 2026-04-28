## Agent-Based SEO Site Factory (pipeline spec)

This repo contains a static site (`sites/cazilla-clone-be-fr/`) and a set of agents to generate, QA, and iteratively fix the output.

### Core idea
`generate → QA → fix → QA → decision → publish`

### Artifacts (source of truth)
- **Keywords**: `agents/a1-keywords/agents/a1-keywords/output/keywords.csv` and `.../keywords.json`
- **Site output**: `sites/cazilla-clone-be-fr/**/index.html` + `assets/*` + `robots.txt` + `sitemap.xml`
- **QA outputs** (written to `output/`):
  - `qa_smoke.json` — link/anchor/meta/asset smoke checks (P0/P1/P2)
  - `qa_report.json` — SEO + keyword density checks (existing agent `a6-design-qa`)
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

### How to run the full loop

```bash
python3 agents/orchestrator.py --site-dir sites/cazilla-clone-be-fr --max-iterations 3
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

