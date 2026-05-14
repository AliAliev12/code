#!/usr/bin/env python3
from __future__ import annotations

import argparse
import http.server
import os
import socketserver
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
_AGENTS_DIR = ROOT / "agents"
if str(_AGENTS_DIR) not in sys.path:
    sys.path.insert(0, str(_AGENTS_DIR))

from _lib.repo_env import apply_repo_dotenv  # noqa: E402


def main() -> int:
    apply_repo_dotenv(ROOT)

    ap = argparse.ArgumentParser(description="Local preview server for cazilareview static output.")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument(
        "--dir",
        default="",
        help="Site directory under repo root, or absolute path. Default: SITE_DIR from .env.",
    )
    args = ap.parse_args()

    rel = (args.dir or os.getenv("SITE_DIR") or "").strip()
    if not rel:
        raise SystemExit("Missing site directory: pass --dir PATH or set SITE_DIR in repo root .env")
    root = Path(rel).resolve() if Path(rel).is_absolute() else (ROOT / rel).resolve()
    if not root.exists():
        raise SystemExit(f"Directory does not exist: {root}")

    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", args.port), lambda *a, **kw: handler(*a, directory=str(root), **kw)) as httpd:
        print(f"Serving {root} at http://localhost:{args.port}/")
        print("Press Ctrl+C to stop.")
        httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

