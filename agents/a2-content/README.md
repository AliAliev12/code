# A2 Content (Anthropic)

This agent generates SEO text via the **Anthropic API**.

## Setup

Add to your `.env` at repo root:

- `ANTHROPIC_API_KEY=...`
- optional: `ANTHROPIC_MODEL=...`

## Site factory spec (full Russian prompt)

Полное ТЗ для генерации/правок сайтов: `agents/prompts/cazilla-site-factory-ru.md`.

Чтобы добавить его в промпт к модели (вместе с JSON-форматом ниже):

```bash
python3 agents/a2-content/run.py --with-site-factory-spec
```

Либо `A2_WITH_SITE_FACTORY_SPEC=1` в `.env`.

## Run

Generate content JSON:

```bash
python3 agents/a2-content/run.py
```

Fix keyword density offenders using `output/qa_report.json`:

```bash
python3 agents/a2-content/run.py --fix-density
```

