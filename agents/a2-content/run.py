#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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


def default_site_dir(env: Dict[str, str]) -> str:
    site_dir = (env.get("SITE_DIR") or os.getenv("SITE_DIR") or "").strip()
    return site_dir or "sites/default-site"


def default_html_path(env: Dict[str, str]) -> Path:
    return ROOT / default_site_dir(env) / "index.html"


def require_locale_lang(env: Dict[str, str]) -> Tuple[str, str]:
    locale = (env.get("TARGET_LOCALE") or os.getenv("TARGET_LOCALE") or "").strip()
    lang = (env.get("TARGET_LANG") or os.getenv("TARGET_LANG") or "").strip()
    if not locale:
        raise SystemExit("Missing TARGET_LOCALE in .env/environment.")
    if not lang:
        raise SystemExit("Missing TARGET_LANG in .env/environment.")
    return locale, lang


def _candidate_keywords_paths() -> List[Path]:
    here = Path(__file__).resolve().parent
    site_dir = os.getenv("SITE_DIR", "").strip()
    site_kw = (ROOT / site_dir / "_output" / "keywords.json") if site_dir else None
    candidates: List[Path] = []
    if site_kw is not None:
        candidates.append(site_kw)
    candidates.extend(
        [
            ROOT / "agents" / "a1-keywords" / "agents" / "a1-keywords" / "output" / "keywords.json",
            here / "output" / "keywords.json",
            ROOT / "output" / "keywords.json",
        ]
    )
    return candidates


def load_keywords() -> List[Dict[str, Any]]:
    path = next((p for p in _candidate_keywords_paths() if p.exists()), None)
    if not path:
        raise FileNotFoundError("keywords.json not found. Looked in:\n- " + "\n- ".join(str(p) for p in _candidate_keywords_paths()))

    data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    if not isinstance(data, list):
        raise ValueError("keywords.json must be a JSON array")

    out: List[Dict[str, Any]] = []
    for x in data:
        if not isinstance(x, dict) or "keyword" not in x:
            continue
        out.append(
            {
                "keyword": str(x.get("keyword", "")).strip(),
                "search_volume": int(x.get("search_volume") or 0),
                "keyword_difficulty": float(x.get("keyword_difficulty") or 0),
                "cpc": float(x.get("cpc") or 0),
            }
        )
    out = [k for k in out if k["keyword"]]
    out.sort(key=lambda k: (k["search_volume"], k["keyword_difficulty"]), reverse=True)
    return out


def pick_keywords(kws: List[Dict[str, Any]]) -> Tuple[str, List[str], List[str]]:
    if not kws:
        raise ValueError("No keywords loaded")

    main = kws[0]["keyword"]
    remaining = [k["keyword"] for k in kws[1:]]

    about: List[str] = []
    for kw in remaining:
        if len(about) >= 7:
            break
        about.append(kw)
    if len(about) < 5:
        about = remaining[:5]

    footer = [kw for kw in remaining if kw not in set(about)]
    return main, about, footer


def anthropic_api_key(env: Dict[str, str]) -> str:
    return env.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or ""


def model_name(env: Dict[str, str]) -> str:
    return env.get("ANTHROPIC_MODEL") or os.getenv("ANTHROPIC_MODEL") or DEFAULT_MODEL


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


def call_anthropic(
    *,
    api_key: str,
    prompt: str,
    max_tokens: int = 1600,
    model: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    env = env or {}
    chosen = model or model_name(env)
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": chosen,
        "max_tokens": max_tokens,
        "temperature": 0.55,
        "messages": [{"role": "user", "content": prompt}],
    }
    r = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload, timeout=120)
    if r.status_code != 200:
        if r.status_code == 404 and chosen == DEFAULT_MODEL:
            try:
                err = r.json().get("error", {})
            except Exception:
                err = {}
            if isinstance(err, dict) and err.get("type") == "not_found_error" and "model" in str(err.get("message", "")):
                return call_anthropic(api_key=api_key, prompt=prompt, max_tokens=max_tokens, model=FALLBACK_MODEL, env=env)
        raise RuntimeError(f"Anthropic HTTP {r.status_code}: {r.text[:800]}")
    data = r.json()
    parts: List[str] = []
    for block in data.get("content", []) or []:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    text = "\n".join([p for p in parts if p]).strip()
    obj = extract_json_object(text)
    if not obj:
        raise RuntimeError("Model response was not valid JSON. Raw text:\n" + text[:1200])
    return obj


def build_prompt(main_kw: str, about_kws: List[str], footer_kws: List[str], kws: List[Dict[str, Any]], *, locale: str, lang: str) -> str:
    top = kws[:20]
    kw_lines = "\n".join(
        [f'- "{k["keyword"]}" (vol {k["search_volume"]}, KD {k["keyword_difficulty"]}, CPC {k["cpc"]})' for k in top]
    )

    return f"""
You are an SEO copywriter for locale {locale} (language: {lang}). Write original, natural copy for a Cazilla review-style casino site.

Strict constraints:
- Return ONLY a valid JSON object (no markdown, no extra text).
- No misleading promises, no unverifiable legal/regulator claims.
- Neutral, informative, user-focused tone.
- Integrate keywords naturally; avoid stuffing.
- Length targets:
  - hero_title: H1 (<= 70 chars) and must contain main keyword.
  - hero_subtitle: 2-3 sentences.
  - about_section: 150-200 words, include 5-7 provided keywords.
  - bonus_section: 100-150 words.
  - games_section: 100-150 words.
  - footer_seo_text: 100-150 words, include as many remaining keywords as natural.

Main keyword (H1): "{main_kw}"

Keywords for about_section (5-7):
{json.dumps(about_kws, ensure_ascii=False)}

Keywords for footer_seo_text (remaining):
{json.dumps(footer_kws, ensure_ascii=False)}

Keyword context (top 20 with metrics):
{kw_lines}

Exact output format (JSON):
{{
  "hero_title": "...",
  "hero_subtitle": "...",
  "about_section": "...",
  "bonus_section": "...",
  "games_section": "...",
  "footer_seo_text": "..."
}}
""".strip()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def remove_head(html: str) -> str:
    return re.sub(r"(?is)<head\b[^>]*>.*?</head>", " ", html)


def remove_ld_json_scripts(html: str) -> str:
    return re.sub(
        r'(?is)<script\b[^>]*\btype=["\']application/ld\+json["\'][^>]*>.*?</script>',
        " ",
        html,
    )


def strip_tags(html: str) -> str:
    html = re.sub(r"(?is)<(script|style)\b[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?is)<!--.*?-->", " ", html)
    html = re.sub(r"(?is)<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", html).strip()


def extract_body_html(html: str) -> str:
    m = re.search(r"(?is)<body\b[^>]*>(.*)</body>", html)
    return m.group(1) if m else html


def visible_body_text_lower(html: str) -> str:
    frag = extract_body_html(remove_head(html))
    frag = remove_ld_json_scripts(frag)
    return strip_tags(frag).lower()


def count_kw_in_body(html: str, kw: str) -> int:
    hay = visible_body_text_lower(html)
    needle = (kw or "").strip().lower()
    return hay.count(needle) if needle else 0


def replace_first_submatch(html: str, pattern: str, repl: str, flags: int = re.I | re.S) -> str:
    return re.sub(pattern, repl, html, count=1, flags=flags)


def apply_content_to_index_html(html: str, content: Dict[str, Any]) -> str:
    """
    Updates visible copy blocks in target site index.html using stable section anchors.
    """
    hero_title = str(content.get("hero_title", "")).strip()
    hero_sub = str(content.get("hero_subtitle", "")).strip()
    bonus = str(content.get("bonus_section", "")).strip()
    games = str(content.get("games_section", "")).strip()
    about = str(content.get("about_section", "")).strip()
    footer = str(content.get("footer_seo_text", "")).strip()

    if hero_title:
        html = replace_first_submatch(
            html,
            r'(?is)(<section\b[^>]*aria-label=["\']Hero["\'][^>]*>.*?<h1>)(.*?)(</h1>)',
            r"\g<1>" + hero_title + r"\g<3>",
        )

    if hero_sub:
        html = replace_first_submatch(
            html,
            r'(?is)(<section\b[^>]*aria-label=["\']Hero["\'][^>]*>.*?<p class="subtitle">\s*)([\s\S]*?)(\s*</p>)',
            r"\g<1>\n" + hero_sub + r"\n\g<3>",
        )

    if bonus:
        html = replace_first_submatch(
            html,
            r'(?is)(<section\b[^>]*\bid=["\']bonuses["\'][^>]*>[\s\S]*?<p class="subtitle"[^>]*>)([\s\S]*?)(</p>)',
            r"\g<1>\n" + bonus + r"\n\g<3>",
        )

    if games:
        html = replace_first_submatch(
            html,
            r'(?is)(<section\b[^>]*\bid=["\']games["\'][^>]*>[\s\S]*?<p class="subtitle"[^>]*>)([\s\S]*?)(</p>)',
            r"\g<1>\n" + games + r"\n\g<3>",
        )

    if about:
        html = replace_first_submatch(
            html,
            r'(?is)(<section\b[^>]*\bid=["\']about["\'][^>]*>[\s\S]*?<p class="subtitle"[^>]*>)([\s\S]*?)(</p>)',
            r"\g<1>\n" + about + r"\n\g<3>",
        )

    if footer:
        html = replace_first_submatch(
            html,
            r'(?is)(<footer\b[^>]*>[\s\S]*?<p\b[^>]*>)([\s\S]*?)(</p>[\s\S]*?</footer>)',
            r"\g<1>\n" + footer + r"\n\g<3>",
        )

    return html


def build_density_fix_prompt(*, full_html: str, offenders: List[Dict[str, Any]], current_content: Dict[str, Any], locale: str, lang: str) -> str:
    off_lines = []
    for o in offenders:
        if not isinstance(o, dict):
            continue
        kw = str(o.get("keyword", "")).strip()
        if not kw:
            continue
        off_lines.append(f'- "{kw}"')
    off_block = "\n".join(off_lines) if off_lines else "- (none)"

    return f"""
You are an SEO copywriter for locale {locale} (language: {lang}).

Goal:
- Reduce repetition for keywords listed below in section texts.
- For EACH listed keyword: appear at MOST 3 times in all visible body text (excluding <head> and JSON-LD).
- Replace repetitions with natural rewrites/synonyms.
- Do not over-edit unrelated SEO keywords.
- Do not change HTML structure: return text fields only (no HTML).

Keywords to fix (QA offenders):
{off_block}

Current text (content.json):
{json.dumps({k: current_content.get(k, "") for k in ["hero_title","hero_subtitle","about_section","bonus_section","games_section","footer_seo_text"]}, ensure_ascii=False, indent=2)}

Full HTML page for context (do not output HTML):
{full_html}

Return ONLY valid JSON with exactly these keys:
{{
  "hero_title": "...",
  "hero_subtitle": "...",
  "about_section": "...",
  "bonus_section": "...",
  "games_section": "...",
  "footer_seo_text": "..."
}}
""".strip()


def run_generate(env: Dict[str, str]) -> None:
    print("=== A2 Content Agent ===")
    kws = load_keywords()
    main_kw, about_kws, footer_kws = pick_keywords(kws)
    print("Main keyword:", main_kw)
    print("About keywords:", len(about_kws))
    print("Footer keywords:", len(footer_kws))

    api_key = anthropic_api_key(env)
    if not api_key:
        raise SystemExit("Missing ANTHROPIC_API_KEY in .env or environment.")

    locale, lang = require_locale_lang(env)
    prompt = build_prompt(main_kw, about_kws, footer_kws, kws, locale=locale, lang=lang)

    last_err: Optional[Exception] = None
    for attempt in range(1, 4):
        try:
            content = call_anthropic(api_key=api_key, prompt=prompt, max_tokens=1800, env=env)
            required = ["hero_title", "hero_subtitle", "about_section", "bonus_section", "games_section", "footer_seo_text"]
            missing = [k for k in required if k not in content or not str(content.get(k, "")).strip()]
            if missing:
                raise RuntimeError("Missing fields in response: " + ", ".join(missing))

            out_path = ROOT / "output" / "content.json"
            write_json(out_path, content)
            print("Saved:", out_path)
            return
        except Exception as e:
            last_err = e
            time.sleep(1.5 * attempt)
            print(f"Attempt {attempt} failed: {e}")
    raise SystemExit(f"Failed after retries: {last_err}")


def run_fix_density(env: Dict[str, str]) -> None:
    print("=== A2 Content Agent (fix-density) ===")
    api_key = anthropic_api_key(env)
    if not api_key:
        raise SystemExit("Missing ANTHROPIC_API_KEY in .env or environment.")

    qa_path = ROOT / "output" / "qa_report.json"
    if not qa_path.exists():
        raise SystemExit(f"qa_report.json not found: {qa_path}")
    qa = read_json(qa_path)
    if not isinstance(qa, dict):
        raise SystemExit("qa_report.json must be an object")

    kd = qa.get("keyword_density") or {}
    offenders = kd.get("offenders") if isinstance(kd, dict) else None
    if not isinstance(offenders, list) or not offenders:
        print("No offenders in qa_report.keyword_density — nothing to do.")
        return

    qa_html_path = str((qa.get("meta") or {}).get("html_path") or "").strip()
    html_path = Path(qa_html_path) if qa_html_path else default_html_path(env)
    if not html_path.exists():
        raise SystemExit(
            f"HTML path not found: {html_path}. "
            "Set SITE_DIR in .env/environment or provide qa_report.meta.html_path."
        )
    full_html = html_path.read_text(encoding="utf-8", errors="replace")

    content_path = ROOT / "output" / "content.json"
    if not content_path.exists():
        fallback = Path(__file__).resolve().parent / "output" / "content.json"
        if fallback.exists():
            content_path.write_text(fallback.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
        else:
            raise SystemExit(f"content.json not found at {content_path} (and fallback missing).")

    current = read_json(content_path)
    if not isinstance(current, dict):
        raise SystemExit("content.json must be an object")

    locale, lang = require_locale_lang(env)
    prompt = build_density_fix_prompt(full_html=full_html, offenders=offenders, current_content=current, locale=locale, lang=lang)
    fixed = call_anthropic(api_key=api_key, prompt=prompt, max_tokens=2200, env=env)

    required = ["hero_title", "hero_subtitle", "about_section", "bonus_section", "games_section", "footer_seo_text"]
    missing = [k for k in required if k not in fixed or not str(fixed.get(k, "")).strip()]
    if missing:
        raise SystemExit("Missing fields in fix-density response: " + ", ".join(missing))

    merged = dict(current)
    merged.update({k: fixed[k] for k in required})
    write_json(content_path, merged)
    print("Updated:", content_path)

    new_html = apply_content_to_index_html(full_html, merged)
    html_path.write_text(new_html, encoding="utf-8")
    print("Updated:", html_path)

    a3 = ROOT / "agents" / "a3-ai-check" / "agents" / "a3-ai-check" / "run.py"
    print("\n=== Launching A3 --recheck ===")
    r = subprocess.run([sys.executable, str(a3), "--recheck"], cwd=str(ROOT), env=os.environ.copy())
    if r.returncode != 0:
        raise SystemExit(f"A3 recheck failed (exit {r.returncode})")


def main(argv: List[str]) -> int:
    env = load_env(ENV_PATH)
    # allow os.environ overrides too
    for k, v in env.items():
        os.environ.setdefault(k, v)

    p = argparse.ArgumentParser()
    p.add_argument("--fix-density", action="store_true")
    args = p.parse_args(argv)

    if args.fix_density:
        run_fix_density(env)
        return 0

    run_generate(env)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
