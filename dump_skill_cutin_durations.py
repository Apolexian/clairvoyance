#!/usr/bin/env python3
"""
Extract the real unique-skill activation cut-in video duration per card.

Earlier attempts got this wrong:
  1. ParticleSystem.lengthInSec from charaskill VFX bundles - most are
     looping, so that's just "one loop cycle", not real on-screen time.
  2. The chara/body|camera|facial "3d/motion/cutin/chara/..." AnimationClip
     (~1.17s, suspiciously uniform across the whole cast) - turned out to
     be a different, shorter clip; not what plays when a unique activates.

The actual thing that plays when a unique skill goes off is a *cutscene*
identified as `cutt/cutin/skill/crd{cardId}_001/crd{cardId}_001`. That
bundle holds a MonoBehaviour (the cutscene "director") named after the
card id with a `_timeLength` field - the authoritative full sequence
duration (camera + character + effects + name-flash, all driven by
frame-indexed events inside it). Verified against real gameplay: card
101702 reads 9.27s in-data vs ~8s counted by eye - matches (well within
counting-by-eye margin), unlike the earlier ~1.17s figure which was
flatly wrong.

Card id format: {charaId}{outfit:02d}, e.g. 100101 = Special Week's
base outfit. Each individual card release has its own cut-in cutscene
(more or less flashy per rarity/era), not just one per unique-skill tier.

Usage:
  uv run dump_skill_cutin_durations.py [--card-id 101702] [--out FILE]
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import sqlite3
import struct
import sys
from pathlib import Path

import UnityPy

log = logging.getLogger("dump_skill_cutin_durations")
logging.basicConfig(level=logging.INFO, format="%(message)s")

AB_KEY = bytes([0x53, 0x2B, 0x46, 0x31, 0xE4, 0xA7, 0xB9, 0x47, 0x3E, 0x7C, 0xFB])

DEFAULT_GAME_DIR = Path.home() / "AppData/LocalLow/Cygames/Umamusume"
DEFAULT_CHARA_DATA = (
    Path.home()
    / "Documents/work/umaguide/docs/.vitepress/theme/data/TerumiCharacterData.json"
)
DEFAULT_JP_CHARA_DATA = (
    Path.home() / "Documents/work/umaguide/docs/.vitepress/theme/data/jpumas.json"
)

NAME_RE = re.compile(r"^cutt/cutin/skill/crd(\d+)_001/crd\d+_001$")


def derive_bundle_key(entry_key: int) -> bytes:
    key_bytes = struct.pack("<q", entry_key)
    result = bytearray(len(AB_KEY) * 8)
    for i, b in enumerate(AB_KEY):
        base_offset = i * 8
        for j in range(8):
            result[base_offset + j] = b ^ key_bytes[j]
    return bytes(result)


def decrypt_bundle(file_path: Path, entry_key: int) -> bytes:
    data = bytearray(file_path.read_bytes())
    if len(data) <= 256:
        return bytes(data)
    key = derive_bundle_key(entry_key)
    key_len = len(key)
    for i in range(256, len(data)):
        data[i] ^= key[i % key_len]
    return bytes(data)


def load_meta_entries(game_dir: Path) -> list[dict]:
    for candidate in (game_dir / "meta_decrypted", game_dir / "meta"):
        if not candidate.is_file():
            continue
        try:
            conn = sqlite3.connect(f"file:{candidate}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT n, h, e FROM a WHERE n LIKE 'cutt/cutin/skill/crd%_001/crd%_001'"
            ).fetchall()
            conn.close()
            if rows:
                log.info("Loaded %d skill cut-in cutscene entries from %s", len(rows), candidate.name)
                return [{"name": r["n"], "hash": r["h"], "key": r["e"]} for r in rows]
        except Exception as e:
            log.warning("Could not read %s as plain sqlite: %s", candidate, e)
    log.error("No usable meta database found in %s", game_dir)
    return []


def load_chara_names(chara_data_path: Path, jp_chara_data_path: Path) -> dict[int, str]:
    names: dict[int, str] = {}
    if chara_data_path.is_file():
        data = json.loads(chara_data_path.read_text(encoding="utf-8"))
        entries = data.values() if isinstance(data, dict) else data
        for e in entries:
            cid = e.get("charaId")
            name = e.get("charaName")
            if cid is not None and name and cid not in names:
                names[cid] = name
    else:
        log.warning("Character data file not found at %s", chara_data_path)

    if jp_chara_data_path.is_file():
        jp_data = json.loads(jp_chara_data_path.read_text(encoding="utf-8"))
        jp_entries = jp_data.values() if isinstance(jp_data, dict) else jp_data
        for e in jp_entries:
            name_pair = e.get("name") or []
            en_name = name_pair[1] if len(name_pair) > 1 else (name_pair[0] if name_pair else None)
            if not en_name:
                continue
            for outfit_id in (e.get("outfits") or {}):
                try:
                    cid = int(outfit_id) // 100
                except ValueError:
                    continue
                names.setdefault(cid, en_name)
    else:
        log.warning("JP character data file not found at %s", jp_chara_data_path)

    return names


def read_time_length(data: bytes, expected_name: str) -> float | None:
    env = UnityPy.load(data)
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            tree = obj.read_typetree()
        except Exception:
            continue
        if tree.get("m_Name") == expected_name and "_timeLength" in tree:
            return float(tree["_timeLength"])
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--game-dir", type=Path, default=DEFAULT_GAME_DIR)
    parser.add_argument("--chara-data", type=Path, default=DEFAULT_CHARA_DATA)
    parser.add_argument("--jp-chara-data", type=Path, default=DEFAULT_JP_CHARA_DATA)
    parser.add_argument("--card-id", type=int, default=None, help="Only process this cardId (e.g. 101702)")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent / "skill_cutin_durations",
        help="Output path prefix (writes .csv and .txt)",
    )
    args = parser.parse_args()

    entries = load_meta_entries(args.game_dir)
    if not entries:
        return 1

    chara_names = load_chara_names(args.chara_data, args.jp_chara_data)

    results = []
    for e in sorted(entries, key=lambda x: x["name"]):
        m = NAME_RE.match(e["name"])
        if not m:
            continue
        card_id = int(m.group(1))
        if args.card_id is not None and card_id != args.card_id:
            continue
        chara_id = card_id // 100

        h = e["hash"]
        fp = args.game_dir / "dat" / h[:2] / h
        if not fp.is_file():
            log.warning("Missing bundle for crd%s at %s", card_id, fp)
            continue
        try:
            data = decrypt_bundle(fp, e["key"])
            duration = read_time_length(data, f"crd{card_id}_001")
        except Exception as exc:
            log.warning("Failed to read crd%s: %s", card_id, exc)
            continue
        if duration is None:
            log.warning("No _timeLength found for crd%s", card_id)
            continue

        name = chara_names.get(chara_id, "")
        results.append(
            {
                "card_id": card_id,
                "chara_id": chara_id,
                "chara_name": name,
                "duration_sec": round(duration, 3),
            }
        )
        log.info("crd%s (%s): %.2fs", card_id, name, duration)

    csv_path = args.out.with_suffix(".csv")
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["card_id", "chara_id", "chara_name", "duration_sec"])
        writer.writeheader()
        writer.writerows(results)

    txt_path = args.out.with_suffix(".txt")
    with txt_path.open("w", encoding="utf-8") as f:
        f.write("Unique-skill activation cut-in video durations (real, from cutscene _timeLength)\n")
        f.write("Source: cutt/cutin/skill/crd{cardId}_001 MonoBehaviour._timeLength\n")
        f.write("One cutscene per card (outfit), not per character.\n")
        f.write("=" * 90 + "\n\n")
        current_chara = None
        for r in results:
            if r["chara_id"] != current_chara:
                current_chara = r["chara_id"]
                f.write(f"\n{r['chara_name']} (chr{r['chara_id']})\n")
            f.write(f"  card {r['card_id']}: {r['duration_sec']:.2f}s\n")

    log.info("Wrote %s and %s (%d cards)", csv_path, txt_path, len(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
