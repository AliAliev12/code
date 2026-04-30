#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests


ROOT = Path(__file__).resolve().parents[4]
ENV_PATH = ROOT / ".env"


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


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_site_dir(site_dir_arg: str) -> Path:
    raw = site_dir_arg or os.getenv("SITE_DIR", "")
    p = Path(raw) if raw else ROOT / "sites" / "cazilla-clone-be-fr"
    if not p.is_absolute():
        p = ROOT / p
    return p.resolve()


def resolve_output_dir(output_dir_arg: str) -> Path:
    raw = output_dir_arg or os.getenv("SITE_OUTPUT_DIR", "")
    p = Path(raw) if raw else ROOT / "output"
    if not p.is_absolute():
        p = ROOT / p
    return p.resolve()


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
            r"\1" + hero_title + r"\3",
        )

    if hero_sub:
        html = replace_first_submatch(
            html,
            r'(?is)(<section\b[^>]*aria-label=["\']Hero["\'][^>]*>.*?<p class="subtitle">\s*)([\s\S]*?)(\s*</p>)',
            r"\1\n" + hero_sub + r"\n\3",
        )

    if bonus:
        html = replace_first_submatch(
            html,
            r'(?is)(<section\b[^>]*\bid=["\']bonuses["\'][^>]*>[\s\S]*?<p class="subtitle"[^>]*>)([\s\S]*?)(</p>)',
            r"\1\n" + bonus + r"\n\3",
        )

    if games:
        html = replace_first_submatch(
            html,
            r'(?is)(<section\b[^>]*\bid=["\']games["\'][^>]*>[\s\S]*?<p class="subtitle"[^>]*>)([\s\S]*?)(</p>)',
            r"\1\n" + games + r"\n\3",
        )

    if about:
        html = replace_first_submatch(
            html,
            r'(?is)(<section\b[^>]*\bid=["\']about["\'][^>]*>[\s\S]*?<p class="subtitle"[^>]*>)([\s\S]*?)(</p>)',
            r"\1\n" + about + r"\n\3",
        )

    if footer:
        html = replace_first_submatch(
            html,
            r'(?is)(<footer\b[^>]*>[\s\S]*?<p\b[^>]*>)([\s\S]*?)(</p>[\s\S]*?</footer>)',
            r"\1\n" + footer + r"\n\3",
        )

    return html


def call_anthropic(api_key: str, prompt: str, model: str, max_tokens: int = 1600) -> Dict[str, Any]:
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "content-type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": 0.55,
        "messages": [{"role": "user", "content": prompt}],
    }
    r = requests.post(url, headers=headers, json=payload, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"Anthropic HTTP {r.status_code}: {r.text[:800]}")
    data = r.json()
    parts: List[str] = []
    for block in data.get("content", []) or []:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return {"text": "\n".join([p for p in parts if p]).strip()}


def extract_json_from_text(s: str) -> Dict[str, Any]:
    try:
        obj = json.loads(s)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = s[start : end + 1]
        obj = json.loads(candidate)
        if isinstance(obj, dict):
            return obj
    raise ValueError("Could not parse JSON object from model output.")


def summarize_diff(before: str, after: str, limit: int = 420) -> Tuple[str, str]:
    b = before.strip()
    a = after.strip()
    return (b[:limit] + ("…" if len(b) > limit else ""), a[:limit] + ("…" if len(a) > limit else ""))


def offender_keywords_from_qa(qa: Dict[str, Any]) -> List[str]:
    kd = qa.get("keyword_density") if isinstance(qa, dict) else None
    if not isinstance(kd, dict):
        return []
    out: List[str] = []
    for o in kd.get("offenders", []) or []:
        if isinstance(o, dict) and o.get("keyword"):
            out.append(str(o["keyword"]).strip())
    # de-dupe, keep order
    seen = set()
    deduped: List[str] = []
    for k in out:
        kl = k.lower()
        if not k or kl in seen:
            continue
        seen.add(kl)
        deduped.append(k)
    return deduped


def build_humanize_subset_prompt(fields: List[str], subset: Dict[str, Any], offender_kws: List[str]) -> str:
    offenders = ", ".join([f'"{k}"' for k in offender_kws]) if offender_kws else "(none)"
    return f"""
Tu es un rédacteur SEO francophone (Belgique) et un éditeur anti-détection IA.

Réécris UNIQUEMENT les champs fournis (subset) pour qu'ils sonnent naturels (fr-BE), sans répétitions mécaniques.
Contraintes:
- garder le sens global et le vocabulaire casino/belgique
- phrases de longueur variée, ton humain
- chaque mot-clé listé ci-dessous doit apparaître AU MOINS 1 fois dans l'ensemble des champs réécrits (tout le subset concaténé), sans bourrage
- intégrer aussi exactement une fois la phrase: "meilleur casino belge en ligne" (si elle n'est pas déjà présente dans le subset, ajoute-la naturellement dans un seul champ)
- retourner UNIQUEMENT un JSON valide, sans markdown, avec exactement les mêmes clés que le subset

Mots-clés offenders (présence minimale requise dans le subset):
[{offenders}]

Subset JSON:
{json.dumps(subset, ensure_ascii=False, indent=2)}
""".strip()


def run_full_humanize(env: Dict[str, str], *, site_dir: Path, output_dir: Path) -> int:
    api_key = env.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("Missing ANTHROPIC_API_KEY in .env or env var.")

    in_path = output_dir / "content.json"
    if not in_path.exists():
        fallback = ROOT / "agents" / "a2-content" / "agents" / "a2-content" / "output" / "content.json"
        if fallback.exists():
            in_path.parent.mkdir(parents=True, exist_ok=True)
            in_path.write_text(fallback.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
        else:
            raise SystemExit(f"Input content.json not found at {in_path} (and fallback missing).")

    out_path = output_dir / "content_humanized.json"
    content = read_json(in_path)
    if not isinstance(content, dict):
        raise SystemExit("output/content.json must be a JSON object.")

    fields = ["hero_subtitle", "about_section", "bonus_section", "games_section", "footer_seo_text"]
    missing = [f for f in fields if f not in content]
    if missing:
        raise SystemExit(f"Missing fields in content.json: {missing}")

    prompt = f"""
Tu es un rédacteur SEO francophone (Belgique) et un éditeur anti-détection IA.

Réécris les textes ci-dessous pour qu'ils sonnent VRAIMENT comme écrits par un humain:
- style naturel, phrases de longueur variée, vocabulaire concret
- garder le sens, rester en français (fr-BE)
- pas de répétitions mécaniques, pas de "marketing" trop robotique
- conserver les mots-clés importants déjà présents, mais intégrer aussi exactement une fois la phrase: "meilleur casino belge en ligne"
  (important pour notre QA keywords)
- NE PAS ajouter de nouvelles sections ni de listes longues, juste des paragraphes fluides

Retourne UNIQUEMENT un JSON valide, sans markdown, avec exactement ces clés:
{fields}

Textes d'entrée (JSON):
{json.dumps({k: content[k] for k in fields}, ensure_ascii=False, indent=2)}
""".strip()

    models = ["claude-sonnet-4-6", "claude-sonnet-4-20250514"]
    last_err: Optional[Exception] = None
    for model in models:
        try:
            res = call_anthropic(api_key=api_key, prompt=prompt, model=model, max_tokens=1800)
            obj = extract_json_from_text(res["text"])
            for k in fields:
                if not isinstance(obj.get(k), str) or not obj[k].strip():
                    raise ValueError(f"Field {k} missing/empty in model output.")

            merged = dict(content)
            merged.update({k: obj[k] for k in fields})
            write_json(out_path, {k: merged.get(k, "") for k in ["hero_title", *fields]})

            html_path = site_dir / "index.html"
            if html_path.exists():
                html = html_path.read_text(encoding="utf-8", errors="replace")
                html_path.write_text(apply_content_to_index_html(html, merged), encoding="utf-8")

            print(f"Saved: {out_path}")
            print("\n=== Comparison (original vs humanized, truncated) ===")
            for k in fields:
                b, a = summarize_diff(str(content[k]), str(obj[k]))
                print(f"\n[{k}]")
                print("ORIG:", b)
                print("NEW :", a)
            return 0
        except Exception as e:
            last_err = e
            time.sleep(0.4)

    raise SystemExit(str(last_err))


def run_recheck(env: Dict[str, str], *, site_dir: Path, output_dir: Path) -> int:
    print("=== A3 Humanizer (recheck) ===")
    api_key = env.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("Missing ANTHROPIC_API_KEY in .env or env var.")

    content_path = output_dir / "content.json"
    prev_path = output_dir / "content_humanized.json"
    qa_path = output_dir / "qa_report.json"

    content = read_json(content_path)
    if not isinstance(content, dict):
        raise SystemExit("output/content.json must be a JSON object.")

    prev = read_json(prev_path) if prev_path.exists() and prev_path.stat().st_size > 2 else {}
    if not isinstance(prev, dict):
        prev = {}

    qa: Dict[str, Any] = read_json(qa_path) if qa_path.exists() else {}
    if not isinstance(qa, dict):
        qa = {}

    offender_kws = offender_keywords_from_qa(qa)

    fields = ["hero_subtitle", "about_section", "bonus_section", "games_section", "footer_seo_text"]
    missing = [f for f in fields if f not in content]
    if missing:
        raise SystemExit(f"Missing fields in content.json: {missing}")

    changed_fields = [f for f in fields if str(content.get(f, "")).strip() != str(prev.get(f, "")).strip()]
    if not changed_fields:
        changed_fields = fields[:]  # if no baseline, re-humanize everything except hero_title

    subset = {k: content[k] for k in changed_fields}
    prompt = build_humanize_subset_prompt(changed_fields, subset, offender_kws)

    models = ["claude-sonnet-4-6", "claude-sonnet-4-20250514"]
    last_err: Optional[Exception] = None
    obj: Dict[str, Any] = {}
    for model in models:
        try:
            res = call_anthropic(api_key=api_key, prompt=prompt, model=model, max_tokens=2000)
            obj = extract_json_from_text(res["text"])
            for k in changed_fields:
                if not isinstance(obj.get(k), str) or not obj[k].strip():
                    raise ValueError(f"Field {k} missing/empty in model output.")
            break
        except Exception as e:
            last_err = e
            time.sleep(0.4)
            obj = {}

    if not obj:
        raise SystemExit(str(last_err))

    merged = dict(content)
    merged.update({k: obj[k] for k in changed_fields})
    out_path = output_dir / "content_humanized.json"
    write_json(out_path, {k: merged.get(k, "") for k in ["hero_title", *fields]})

    html_path = site_dir / "index.html"
    html_before = html_path.read_text(encoding="utf-8", errors="replace") if html_path.exists() else ""
    counts_before = {k: count_kw_in_body(html_before, k) for k in offender_kws}

    if html_path.exists():
        html_path.write_text(apply_content_to_index_html(html_before, merged), encoding="utf-8")

    html_after = html_path.read_text(encoding="utf-8", errors="replace") if html_path.exists() else ""
    counts_after = {k: count_kw_in_body(html_after, k) for k in offender_kws}

    for kw in offender_kws:
        if counts_after.get(kw, 0) < 1:
            raise SystemExit(f"Recheck validation failed: offender keyword missing after humanize: {kw}")

    for kw in offender_kws:
        b = int(counts_before.get(kw, 0))
        a = int(counts_after.get(kw, 0))
        print(f"✅ Density fixed: {kw}: было {b} раз → стало {a} раз")

    return 0


def main(argv: List[str]) -> int:
    env = load_env(ENV_PATH)
    for k, v in env.items():
        os.environ.setdefault(k, v)

    p = argparse.ArgumentParser()
    p.add_argument("--recheck", action="store_true")
    p.add_argument("--site-dir", default="")
    p.add_argument("--output-dir", default="")
    args = p.parse_args(argv)
    site_dir = resolve_site_dir(args.site_dir)
    output_dir = resolve_output_dir(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    os.environ["SITE_DIR"] = str(site_dir)
    os.environ["SITE_OUTPUT_DIR"] = str(output_dir)

    if args.recheck:
        return run_recheck(env, site_dir=site_dir, output_dir=output_dir)
    return run_full_humanize(env, site_dir=site_dir, output_dir=output_dir)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
