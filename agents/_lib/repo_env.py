#!/usr/bin/env python3
"""
Load repository root `.env` into the process environment.

Existing `os.environ` entries win (`setdefault`), matching other agents in this repo.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict


def load_dotenv_file(path: Path) -> Dict[str, str]:
    env: Dict[str, str] = {}
    if not path.exists():
        return env
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    return env


def apply_repo_dotenv(repo_root: Path) -> None:
    """Merge ``<repo_root>/.env`` into ``os.environ`` (shell / process env overrides file)."""
    for k, v in load_dotenv_file(repo_root / ".env").items():
        os.environ.setdefault(k, v)
