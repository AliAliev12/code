#!/usr/bin/env python3
"""Backward-compatible entry point — delegates to gen_cazilla_review_html.py (.env + keywords.json)."""
from __future__ import annotations

import sys

from gen_cazilla_review_html import main, write_technical_pages_only

if __name__ == "__main__":
    if "--tech-only" in sys.argv:
        raise SystemExit(write_technical_pages_only() or 0)
    raise SystemExit(main())
