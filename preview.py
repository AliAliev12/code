#!/usr/bin/env python3
from __future__ import annotations

import argparse
import http.server
import socketserver
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description="Local preview server for cazilareview static output.")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--dir", default="sites/cazilla-clone-be-fr")
    args = ap.parse_args()

    root = Path(args.dir).resolve()
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

