#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

import requests


ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT / ".env"

DEFAULT_MODEL = "claude-sonnet-4-20250514"
FALLBACK_MODEL = "claude-sonnet-4-6"


def load_env(path: Path) -> Dict[str, str]:
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


def extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    text = text.strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def call_anthropic(*, api_key: str, prompt: str, model: str, max_tokens: int) -> Dict[str, Any]:
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": 0.55,
        "messages": [{"role": "user", "content": prompt}],
    }
    r = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"Anthropic HTTP {r.status_code}: {r.text[:800]}")
    data = r.json()
    parts = []
    for block in data.get("content", []) or []:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    text = "\n".join([p for p in parts if p]).strip()
    obj = extract_json_object(text)
    if not obj:
        raise RuntimeError("Model response was not valid JSON. Raw text:\n" + text[:1200])
    return obj


def build_prompt(*, input_text: str, must_include: str, lang: str, tone: str, max_words: int, locale: str) -> str:
    lang_name = "English" if str(lang).lower().startswith("en") else "French"
    return f"""
You are a {lang_name} copy editor ({locale}) specialized in microcopy for an independent review website (tone: {tone}).

Goal: rewrite the opening paragraph so it sounds natural, editorial, and credible (not forced SEO).

Strict constraints:
- Keep the original meaning.
- Do not add promises, legal claims, or authority claims.
- Do not write in first person (no "we", "I", "our tests"). Keep neutral editorial tone.
- Do not invent numbers or turnaround times.
- Prefer concrete wording over vague statements.
- Include EXACTLY ONCE the following phrase (exact match):
  {json.dumps(must_include, ensure_ascii=False)}
- Target length: <= {max_words} words.
- Output ONLY valid JSON (no markdown), in this shape:
  {{ "text": "..." }}

Input text:
{json.dumps(input_text, ensure_ascii=False)}
""".strip()


def main() -> int:
    ap = argparse.ArgumentParser(description="A13 microcopy: rewrite a short paragraph via Anthropic.")
    ap.add_argument("--text", required=True, help="Input paragraph text.")
    ap.add_argument("--must-include", required=True, help="Exact phrase that must appear exactly once.")
    ap.add_argument("--lang", default="en")
    ap.add_argument("--locale", default="")
    ap.add_argument("--tone", default="editorial, independent review")
    ap.add_argument("--max-words", type=int, default=70)
    ap.add_argument("--model", default="")
    ap.add_argument("--max-tokens", type=int, default=220)
    args = ap.parse_args()

    env = {**load_env(ENV_PATH), **os.environ}
    api_key = env.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("Missing ANTHROPIC_API_KEY in .env or env var.")

    model = (args.model or env.get("ANTHROPIC_MODEL") or DEFAULT_MODEL).strip()

    locale = (args.locale or env.get("TARGET_LOCALE") or "en-IE").strip()
    lang = (args.lang or env.get("TARGET_LANG") or "en").strip()

    prompt = build_prompt(
        input_text=args.text,
        must_include=args.must_include,
        lang=lang,
        tone=args.tone,
        max_words=args.max_words,
        locale=locale,
    )

    last_err: Optional[Exception] = None
    for m in [model, FALLBACK_MODEL]:
        try:
            obj = call_anthropic(api_key=api_key, prompt=prompt, model=m, max_tokens=args.max_tokens)
            out = str(obj.get("text", "")).strip()
            if not out:
                raise ValueError("Empty 'text' in model output.")
            # Basic must-include checks
            if out.count(args.must_include) != 1:
                raise ValueError("Output must include the exact must-include phrase exactly once.")
            print(out)
            return 0
        except Exception as e:
            last_err = e
            continue

    raise SystemExit(str(last_err))


if __name__ == "__main__":
    raise SystemExit(main())

