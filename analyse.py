#!/usr/bin/env python3
"""
Analyse the class_dump.json from discovery and produce a human-readable summary.

Outputs:
  discovery/analysis.md        — full readable report
  discovery/interesting.json   — filtered list of classes worth hooking

Usage:
  python analyse.py
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

_FROZEN = getattr(sys, "frozen", False)

if _FROZEN:
    _APP_DIR = Path(sys.executable).resolve().parent
else:
    _APP_DIR = Path(__file__).parent

DISCOVERY_DIR = _APP_DIR / "discovery"
DUMP_FILE = DISCOVERY_DIR / "class_dump.json"
OUTPUT_MD = DISCOVERY_DIR / "analysis.md"
OUTPUT_JSON = DISCOVERY_DIR / "interesting.json"

# ── Scoring: how "interesting" is a class for guide writers? ───────────────

# Methods that indicate the class does something we want to observe
HIGH_VALUE_METHODS = {
    "activate",
    "lotactivate",
    "checktriggerandactivate",
    "beginview",
    "beginrace",
    "startrace",
    "endrace",
    "finishrace",
    "setresult",
    "showresult",
    "serialize",
    "deserialize",
    "sendrequest",
    "oncomplete",
    "onsuccess",
    "onerror",
    "selectchoice",
    "onclickdecide",
    "onclickdecidebutton",
    "onselect",
    "onclick",
    "onclickchoice",
    "playcomment",
    "triggercomment",
    "getneedskillpoint",
    "getremainingskilpoint",
    "begin",
}

# Fields that indicate the class holds data we want to read
HIGH_VALUE_FIELDS = {
    "skillid",
    "abilitytype",
    "abilityvalue",
    "activatelot",
    "raceid",
    "raceresult",
    "finishorder",
    "resultorder",
    "charaid",
    "cardid",
    "viewerid",
    "eventid",
    "choiceid",
    "scenarioid",
    "speed",
    "stamina",
    "power",
    "guts",
    "wisdom",
    "distance",
    "groundtype",
    "weather",
    "season",
}

# Class name patterns that are noise (compiler-generated, UI fluff)
NOISE_PATTERNS = [
    r"^<.*>d__\d+$",  # compiler-generated async state machines
    r"^<>c(__DisplayClass\d+)?",  # compiler-generated closures
    r"__c$",
    r"\.StaticVariableDefine\.",  # static var holders
    r"^Amazon\.",  # AWS SDK noise
    r"^System\.",  # .NET framework
    r"^MS\.",  # MS internals
    r"^ZXing\.",  # barcode library
    r"^Mono\.",  # Mono runtime
    r"^Unity(Engine)?\..*Editor",  # editor-only
    r"^Google\.",  # Google SDK
    r"^Firebase\.",  # Firebase
    r"^I18N\.",  # internationalisation lib
]

NOISE_RE = [re.compile(p) for p in NOISE_PATTERNS]


def is_noise(name: str) -> bool:
    # Check the short name (after last dot)
    short = name.rsplit(".", 1)[-1] if "." in name else name
    return any(r.search(short) or r.search(name) for r in NOISE_RE)


def score_class(name: str, cls: dict) -> tuple[int, list[str]]:
    """Score a class by how interesting it is. Returns (score, reasons)."""
    score = 0
    reasons = []

    methods = {m["name"].lower() for m in cls.get("methods", [])}
    fields = {f["name"].lower() for f in cls.get("fields", [])}

    # High-value method hits
    method_hits = methods & HIGH_VALUE_METHODS
    if method_hits:
        score += len(method_hits) * 10
        reasons.append(f"methods: {', '.join(sorted(method_hits))}")

    # High-value field hits
    field_hits = fields & HIGH_VALUE_FIELDS
    if field_hits:
        score += len(field_hits) * 8
        reasons.append(f"fields: {', '.join(sorted(field_hits))}")

    # Bonus for being a Gallop.* class (game logic, not library)
    if name.startswith("Gallop."):
        score += 5

    # Bonus for Request/Response/Task pattern (API classes)
    if name.endswith("Request") or name.endswith("Response") or name.endswith("Task"):
        score += 15
        reasons.append("API pattern")

    # Bonus for Formatter classes
    if "Formatter" in name:
        score += 10
        reasons.append("MsgPack formatter")

    # Bonus for Master data classes
    if "Master" in name and name.startswith("Gallop."):
        score += 8
        reasons.append("Master data")

    # Penalty for noise
    if is_noise(name):
        score -= 100

    # Penalty for having very few methods (likely a data-only struct with no hooks)
    n_methods = len(cls.get("methods", []))
    if n_methods <= 1:
        score -= 5

    return score, reasons


def categorise(name: str) -> str:
    lower = name.lower()
    if "skill" in lower:
        return "skill"
    if "race" in lower and "trace" not in lower:
        return "race"
    if "event" in lower or "story" in lower or "choice" in lower:
        return "event"
    if "training" in lower or "singlemode" in lower:
        return "training"
    if "formatter" in lower or "msgpack" in lower:
        return "network"
    if lower.endswith("request") or lower.endswith("response") or lower.endswith("task"):
        return "api"
    if "master" in lower:
        return "master_data"
    if "jikkyo" in lower:
        return "commentary"
    return "other"


def main():
    print(f"Reading {DUMP_FILE}...")
    with open(DUMP_FILE, encoding="utf-8") as f:
        dump: dict = json.load(f)

    print(f"  {len(dump)} classes loaded.")

    # ── Score and categorise everything ────────────────────────────────
    scored = []
    by_category: dict[str, list] = defaultdict(list)
    match_reason_counts = Counter()

    for name, cls in dump.items():
        score, reasons = score_class(name, cls)
        cat = categorise(name)
        match_reason = cls.get("matchReason", "?")
        match_reason_counts[match_reason] += 1

        entry = {
            "name": name,
            "score": score,
            "reasons": reasons,
            "category": cat,
            "matchReason": match_reason,
            "methodCount": len(cls.get("methods", [])),
            "fieldCount": len(cls.get("fields", [])),
            "methods": [m["name"] for m in cls.get("methods", [])],
            "fields": [
                {"name": f["name"], "offset": f.get("offset"), "type": f.get("type")}
                for f in cls.get("fields", [])
            ],
        }
        scored.append(entry)
        by_category[cat].append(entry)

    # Sort by score descending
    scored.sort(key=lambda e: -e["score"])
    for entries in by_category.values():
        entries.sort(key=lambda e: -e["score"])

    # ── Filter to interesting classes ──────────────────────────────────
    interesting = [e for e in scored if e["score"] > 0]

    # ── Write interesting.json ─────────────────────────────────────────
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(interesting, f, indent=2, ensure_ascii=False)
    print(f"  {len(interesting)} interesting classes -> {OUTPUT_JSON}")

    # ── Write analysis.md ──────────────────────────────────────────────
    lines = []
    lines.append("# Clairvoyance Discovery Analysis\n")
    lines.append(f"**Total classes scanned:** {len(dump)}\n")
    lines.append(f"**Interesting (score > 0):** {len(interesting)}\n")
    lines.append("")
    lines.append("## Match Reasons\n")
    lines.append("| Reason | Count |")
    lines.append("|--------|------:|")
    for reason, count in match_reason_counts.most_common():
        lines.append(f"| {reason} | {count} |")
    lines.append("")

    lines.append("## Categories\n")
    lines.append("| Category | Total | Interesting (score > 0) |")
    lines.append("|----------|------:|------------------------:|")
    for cat in [
        "skill",
        "race",
        "event",
        "training",
        "api",
        "network",
        "master_data",
        "commentary",
        "other",
    ]:
        entries = by_category.get(cat, [])
        n_interesting = sum(1 for e in entries if e["score"] > 0)
        lines.append(f"| {cat} | {len(entries)} | {n_interesting} |")
    lines.append("")

    # ── Top classes per category ───────────────────────────────────────
    for cat in [
        "skill",
        "race",
        "event",
        "training",
        "api",
        "network",
        "master_data",
        "commentary",
    ]:
        entries = by_category.get(cat, [])
        top = [e for e in entries if e["score"] > 0][:30]
        if not top:
            continue
        total = sum(1 for e in entries if e["score"] > 0)

        lines.append(f"## {cat.upper()} (top {len(top)} of {total})\n")
        for e in top:
            lines.append(f"### `{e['name']}` — score {e['score']}")
            if e["reasons"]:
                lines.append(f"*{'; '.join(e['reasons'])}*\n")

            if e["methods"]:
                lines.append("<details><summary>Methods</summary>\n")
                for m in e["methods"]:
                    lines.append(f"- `{m}`")
                lines.append("\n</details>\n")

            if e["fields"]:
                lines.append("<details><summary>Fields</summary>\n")
                lines.append("| Offset | Name | Type |")
                lines.append("|-------:|------|------|")
                for f in e["fields"]:
                    lines.append(f"| {f.get('offset', '?')} | {f['name']} | {f.get('type', '?')} |")
                lines.append("\n</details>\n")
            lines.append("")

    md_text = "\n".join(lines)
    OUTPUT_MD.write_text(md_text, encoding="utf-8")
    print(f"  Analysis report -> {OUTPUT_MD}")

    # ── Print top 30 to console ────────────────────────────────────────
    print()
    print("=" * 70)
    print("  TOP 30 MOST INTERESTING CLASSES")
    print("=" * 70)
    for e in scored[:30]:
        reasons_str = f"  ({'; '.join(e['reasons'])})" if e["reasons"] else ""
        print(f"  {e['score']:4d}  [{e['category']:<10}] {e['name']}{reasons_str}")
    print()
    print(f"Full report: {OUTPUT_MD}")
    print(f"Filtered JSON: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
