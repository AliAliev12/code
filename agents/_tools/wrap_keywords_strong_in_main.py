#!/usr/bin/env python3
"""
Wrap keywords from keywords.json (v2) in <strong> inside <main> only.
Preserves <script>/<style>/<noscript> blocks; does not wrap inside existing <strong>...</strong>.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_AGENTS_DIR = ROOT / "agents"
if str(_AGENTS_DIR) not in sys.path:
    sys.path.insert(0, str(_AGENTS_DIR))

from _lib.repo_env import apply_repo_dotenv  # noqa: E402

apply_repo_dotenv(ROOT)
_SITE_REL = (os.environ.get("SITE_DIR") or "sites/cazilla-offerwall1-en-ie").strip()
SITE = ROOT / _SITE_REL
KW_PATH = SITE / "_output" / "keywords.json"

_BLOCK_TAGS = re.compile(
    r"<(script|style|noscript)\b[^>]*>.*?</\1\s*>",
    re.I | re.DOTALL,
)


def _load_page_keywords() -> dict[str, list[str]]:
    data = json.loads(KW_PATH.read_text(encoding="utf-8"))
    out: dict[str, list[str]] = {}
    for key in ("pages", "technical_pages"):
        for page in data.get(key) or []:
            pid = str(page.get("id") or "").strip()
            if not pid:
                continue
            kws = [
                str(x.get("keyword", "")).strip().lower()
                for x in (page.get("keywords") or [])
                if str(x.get("keyword", "")).strip()
            ]
            out[pid] = sorted(set(kws), key=len, reverse=True)
    return out


def _html_path(page_id: str) -> Path | None:
    m = {
        "home": SITE / "index.html",
        "we-recommend": SITE / "we-recommend.html",
        "how-to-choose": SITE / "how-to-choose.html",
        "player-faq": SITE / "faq.html",
        "cookie-policy": SITE / "cookie-policy" / "index.html",
    }
    p = m.get(page_id)
    return p if p and p.is_file() else None


def _split_main(html: str) -> tuple[str, str, str] | None:
    m = re.search(r"<main\b[^>]*>", html, re.I)
    if not m:
        return None
    start = m.start()
    open_end = m.end()
    mc = re.search(r"</main\s*>", html[open_end:], re.I)
    if not mc:
        return None
    end = open_end + mc.end()
    return html[:start], html[start:end], html[end:]


def _next_strong_block(s: str, i: int) -> tuple[int, int] | None:
    m = re.search(r"<strong\b[^>]*>", s[i:], re.I)
    if not m:
        return None
    start = i + m.start()
    open_end = i + m.end()
    m2 = re.search(r"</strong\s*>", s[open_end:], re.I)
    if not m2:
        return None
    end = open_end + m2.end()
    return start, end


def _subst_outside_strong(s: str, kw: str) -> str:
    pat = re.compile(re.escape(kw), re.I)
    out: list[str] = []
    pos = 0
    while pos < len(s):
        nxb = _next_strong_block(s, pos)
        if nxb is None:
            tail = s[pos:]
            out.append(
                pat.sub(lambda m: "<strong>" + m.group(0) + "</strong>", tail)
            )
            break
        start, end = nxb
        if start > pos:
            chunk = s[pos:start]
            out.append(
                pat.sub(lambda m: "<strong>" + m.group(0) + "</strong>", chunk)
            )
        out.append(s[start:end])
        pos = end
    return "".join(out)


def _wrap_plain_text(text: str, keywords: list[str]) -> str:
    if not text.strip():
        return text
    s = text
    for kw in keywords:
        if len(kw) < 3:
            continue
        s = _subst_outside_strong(s, kw)
    while re.search(r"<strong>\s*<strong\b", s, re.I):
        s = re.sub(r"<strong>\s*<strong\b[^>]*>", "<strong>", s, flags=re.I)
        s = re.sub(r"</strong>\s*</strong\s*>", "</strong>", s, flags=re.I)
    return s


def _process_chunk(chunk: str, keywords: list[str]) -> str:
    """Process HTML chunk: wrap keywords only outside tags and outside existing <strong>...</strong>."""
    out: list[str] = []
    pos = 0
    while pos < len(chunk):
        if chunk[pos] != "<":
            nxt = chunk.find("<", pos)
            if nxt == -1:
                out.append(_wrap_plain_text(chunk[pos:], keywords))
                break
            out.append(_wrap_plain_text(chunk[pos:nxt], keywords))
            pos = nxt
            continue
        nxt = chunk.find(">", pos)
        if nxt == -1:
            out.append(chunk[pos:])
            break
        tag = chunk[pos : nxt + 1]
        if tag.lower().startswith("<strong"):
            close = re.search(r"</strong\s*>", chunk[nxt + 1 :], re.I)
            if close:
                end = nxt + 1 + close.end()
                out.append(chunk[pos:end])
                pos = end
                continue
        out.append(tag)
        pos = nxt + 1
    return "".join(out)


def _process_main(main: str, keywords: list[str]) -> str:
    parts: list[str] = []
    i = 0
    for m in _BLOCK_TAGS.finditer(main):
        parts.append(_process_chunk(main[i : m.start()], keywords))
        parts.append(m.group(0))
        i = m.end()
    parts.append(_process_chunk(main[i:], keywords))
    return "".join(parts)


def process_file(path: Path, keywords: list[str]) -> bool:
    html = path.read_text(encoding="utf-8")
    sp = _split_main(html)
    if not sp:
        print(f"SKIP no main: {path.relative_to(ROOT)}")
        return False
    pre, main, post = sp
    new_main = _process_main(main, keywords)
    if new_main == main:
        print(f"UNCHANGED: {path.relative_to(ROOT)}")
        return False
    path.write_text(pre + new_main + post, encoding="utf-8")
    print(f"UPDATED: {path.relative_to(ROOT)}")
    return True


def main() -> int:
    by_page = _load_page_keywords()
    n = 0
    for pid, kws in by_page.items():
        hp = _html_path(pid)
        if hp and process_file(hp, kws):
            n += 1
    print(f"Files updated: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
