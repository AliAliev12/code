# Local preview

Root-relative links (e.g. `/bonus-casino-belgique/`) work correctly when the site is served over HTTP.

Run:

```bash
python3 preview.py --port 8000
```

Then open:

- `http://localhost:8000/`

## Optional: LINK_MODE=local

If you must open pages without a server, you can switch internal links to relative form during build:

```bash
LINK_MODE=local PREDEPLOY_NOINDEX=false python3 agents/a9-deploy/toggle_index.py
```

