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


def build_prompt(*, input_text: str, must_include: str, lang: str, tone: str, max_words: int) -> str:
    return f"""
Tu es un éditeur francophone ({lang}) spécialisé en microcopy pour un site d’avis indépendant (tone: {tone}).

Objectif: réécrire le paragraphe d’entrée pour qu’il soit naturel, éditorial, crédible, et non “SEO forcé”.

Contraintes strictes:
- Conserver le sens.
- Ne pas ajouter de promesses (ex: “instantané garanti”), ni d’allégations légales, ni d’autorités.
- Ne pas écrire à la première personne (pas de “nous”, “je”, “nos tests”, “nous avons testé/mesuré”). Rester neutre/éditorial.
- Ne pas inventer de chiffres ou de délais chiffrés (pas de “X minutes / 24 heures / 48h”, etc.). Rester général.
- Éviter les formulations vagues (“conditions internes”); préférer du concret (méthode, délais annoncés, vérifications).
- Inclure EXACTEMENT UNE fois la phrase suivante (exact-match, même casse/espaces):
  {json.dumps(must_include, ensure_ascii=False)}
- Longueur cible: ≤ {max_words} mots.
- Sortir UNIQUEMENT un JSON valide, sans markdown, de la forme:
  {{ "text": "..." }}

Texte d’entrée:
{json.dumps(input_text, ensure_ascii=False)}
""".strip()


def main() -> int:
    ap = argparse.ArgumentParser(description="A13 microcopy: rewrite a short paragraph via Anthropic.")
    ap.add_argument("--text", required=True, help="Input paragraph text.")
    ap.add_argument("--must-include", required=True, help="Exact phrase that must appear exactly once.")
    ap.add_argument("--lang", default="fr-BE")
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

    prompt = build_prompt(
        input_text=args.text,
        must_include=args.must_include,
        lang=args.lang,
        tone=args.tone,
        max_words=args.max_words,
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

