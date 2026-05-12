# A2 Content (Anthropic)

This agent generates SEO text via the **Anthropic API**.

## Setup

Add to your `.env` at repo root:

- `ANTHROPIC_API_KEY=...`
- optional: `ANTHROPIC_MODEL=...`

## Run

Generate content JSON:

```bash
python3 agents/a2-content/run.py
```

Fix keyword density offenders using `output/qa_report.json`:

```bash
python3 agents/a2-content/run.py --fix-density
```

