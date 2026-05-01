#!/usr/bin/env python3
"""
Diagnostic: dump raw MonoBehaviour structure from support card story bundles.
Run on machine with game assets to understand why choice extraction is empty.

Usage:
    pip install UnityPy
    python diag_support_bundles.py /path/to/game
    python diag_support_bundles.py /path/to/game --story-ids 830289001,801001001

Outputs:
    diag_support_bundles.json  - full structured dump
    diag_support_bundles.log   - readable console log (commit this)
"""

from __future__ import annotations

import argparse
import io
import json
import sqlite3
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent

# Reuse crypto + meta reading from main script
from extract_character_events import (
    decrypt_bundle,
    read_story_meta_entries,
    _init_xor,
    _get_ci,
)


def dump_bundle(story_id: int, file_path: Path, entry_key: int) -> dict:
    """Dump all MonoBehaviour data from a bundle."""
    _init_xor()
    import UnityPy

    if entry_key != 0:
        data = decrypt_bundle(file_path, entry_key)
        env = UnityPy.load(data)
    else:
        env = UnityPy.load(str(file_path))

    result = {
        "story_id": story_id,
        "object_count": 0,
        "monobehaviours": [],
        "choice_data_lists": [],
    }

    for obj in env.objects:
        result["object_count"] += 1
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            tree = obj.read_typetree()
        except Exception as e:
            result["monobehaviours"].append({"error": str(e)})
            continue
        if not isinstance(tree, dict):
            continue

        m_name = tree.get("m_Name", "")
        # Get all non-standard keys
        interesting_keys = [
            k for k in tree
            if k not in ("m_GameObject", "m_Enabled", "m_Script", "m_Name")
        ]

        mb_info = {
            "m_Name": m_name,
            "keys": interesting_keys,
        }

        # Look for ANY list field that might contain choice/effect data
        for key in interesting_keys:
            val = tree[key]
            if isinstance(val, list) and len(val) > 0:
                if isinstance(val[0], dict):
                    mb_info[f"_{key}_count"] = len(val)
                    mb_info[f"_{key}_item0_keys"] = list(val[0].keys())
                    # Dump first item fully (truncate long strings)
                    item0 = {}
                    for k, v in val[0].items():
                        if isinstance(v, str) and len(v) > 100:
                            item0[k] = v[:100] + "..."
                        elif isinstance(v, list) and len(v) > 3:
                            item0[k] = f"list[{len(v)}]"
                            if v and isinstance(v[0], dict):
                                item0[f"{k}_item0"] = v[0]
                        else:
                            item0[k] = v
                    mb_info[f"_{key}_item0"] = item0
                else:
                    mb_info[f"_{key}"] = f"list[{len(val)}] of {type(val[0]).__name__}"

        # Check specifically for ChoiceDataList
        cdl = _get_ci(tree, "ChoiceDataList", "choiceDataList")
        if cdl and isinstance(cdl, list) and len(cdl) > 0:
            cdl_info = {
                "length": len(cdl),
                "entries": [],
            }
            for i, entry in enumerate(cdl[:5]):  # first 5 entries
                if isinstance(entry, dict):
                    entry_dump = {}
                    for k, v in entry.items():
                        if isinstance(v, list):
                            entry_dump[k] = f"list[{len(v)}]"
                            if v and isinstance(v[0], dict):
                                entry_dump[f"{k}_items"] = v[:2]
                        elif isinstance(v, str) and len(v) > 100:
                            entry_dump[k] = v[:100] + "..."
                        else:
                            entry_dump[k] = v
                    cdl_info["entries"].append(entry_dump)
            result["choice_data_lists"].append(cdl_info)

        result["monobehaviours"].append(mb_info)

    return result


def main():
    parser = argparse.ArgumentParser(description="Diagnostic: dump support card bundle structure")
    parser.add_argument("game_dir", type=Path, help="Path to game root (with dat/ and meta)")
    parser.add_argument(
        "--masterdb", type=Path,
        default=APP_DIR / "dump-jp" / "master.mdb",
        help="Path to master.mdb",
    )
    parser.add_argument(
        "--story-ids", type=str, default=None,
        help="Comma-separated story IDs to inspect (default: auto-pick 5 interesting ones)",
    )
    args = parser.parse_args()

    # Tee all output to both stdout and log file
    log_path = APP_DIR / "diag_support_bundles.log"
    log_file = open(log_path, "w", encoding="utf-8")

    class Tee:
        def __init__(self, *streams):
            self.streams = streams
        def write(self, data):
            for s in self.streams:
                s.write(data)
                s.flush()
        def flush(self):
            for s in self.streams:
                s.flush()

    sys.stdout = Tee(sys.__stdout__, log_file)

    if args.story_ids:
        target_ids = {int(s.strip()) for s in args.story_ids.split(",")}
    else:
        # Auto-pick: get a few known support card stories
        conn = sqlite3.connect(f"file:{args.masterdb}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT DISTINCT s.story_id, s.support_card_id, s.support_chara_id, "
            "t.text as event_name "
            "FROM single_mode_story_data s "
            "LEFT JOIN text_data t ON t.category=181 AND t.\"index\"=s.story_id "
            "WHERE s.support_chara_id > 0 OR s.support_card_id > 0 "
            "ORDER BY s.story_id LIMIT 200"
        ).fetchall()
        conn.close()

        # Pick: 2 shared events (80xxxx), 2 card-specific (82/83xxxx), 1 known multi-choice
        shared = [r for r in rows if str(r["story_id"]).startswith("80")]
        specific = [r for r in rows if str(r["story_id"]).startswith("83") or str(r["story_id"]).startswith("82")]
        picks = shared[:2] + specific[:2]
        # Also add a known event: 830289001 (Young & Unstoppable)
        target_ids = {r["story_id"] for r in picks}
        target_ids.add(830289001)
        target_ids.add(801001001)  # スペシャルウィーク shared event

        print(f"Auto-selected {len(target_ids)} stories to inspect:")
        for r in rows:
            if r["story_id"] in target_ids:
                print(f"  {r['story_id']} {r['event_name']} (card={r['support_card_id']}, chara={r['support_chara_id']})")

    meta_entries = read_story_meta_entries(args.game_dir, target_ids)
    print(f"\nFound {len(meta_entries)}/{len(target_ids)} bundles in meta")

    dat_dir = args.game_dir / "dat"
    results = []

    for sid in sorted(target_ids):
        entry = meta_entries.get(sid)
        if not entry:
            print(f"\n--- Story {sid}: NOT FOUND in meta ---")
            continue

        h = entry["hash"]
        file_path = dat_dir / h[:2] / h
        if not file_path.is_file():
            print(f"\n--- Story {sid}: bundle file missing ({h}) ---")
            continue

        print(f"\n--- Story {sid} ---")
        result = dump_bundle(sid, file_path, entry["key"])
        results.append(result)

        print(f"  Objects: {result['object_count']}")
        print(f"  MonoBehaviours: {len(result['monobehaviours'])}")
        print(f"  ChoiceDataLists found: {len(result['choice_data_lists'])}")

        for mb in result["monobehaviours"]:
            if "error" in mb:
                continue
            keys = mb.get("keys", [])
            if any("choice" in k.lower() or "effect" in k.lower() or "select" in k.lower() for k in keys):
                print(f"  ** Interesting MB: m_Name={mb['m_Name']}")
                print(f"     Keys: {keys}")
                for k, v in mb.items():
                    if k.startswith("_") and "item0" in k:
                        print(f"     {k}: {json.dumps(v, ensure_ascii=False, default=str)[:300]}")

        for i, cdl in enumerate(result["choice_data_lists"]):
            print(f"  ChoiceDataList #{i}: {cdl['length']} entries")
            for j, e in enumerate(cdl["entries"]):
                print(f"    [{j}]: {json.dumps(e, ensure_ascii=False, default=str)[:400]}")

    # Write full dump
    out_path = APP_DIR / "diag_support_bundles.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nFull dump written to {out_path}")
    print(f"Log written to {log_path}")
    log_file.close()
    sys.stdout = sys.__stdout__


if __name__ == "__main__":
    main()
