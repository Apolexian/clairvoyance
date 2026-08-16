#!/usr/bin/env python3
"""
Extract the actual unique-skill cut-in body-pose animation duration per
character.

Prior approach (dump_skill_animation_durations.py) read ParticleSystem
lengthInSec from the charaskill VFX bundles - but most of those are
looping, so lengthInSec is just "one loop cycle", not the real on-screen
time (which is controlled by compiled game code, not a static field).

This instead reads the character's cut-in body-pose AnimationClip
directly - a single, non-looping, per-character clip at:

  3d/motion/cutin/chara/body/chr{charaId}_001/anm_cti_chr{charaId}_001

This clip plays once during the unique-skill cut-in camera cutscene
(same clip regardless of unique-skill evolution tier - the pose is
fixed per character, only the background/effects change between tiers).
Its Mecanim MuscleClip m_StartTime/m_StopTime/m_LoopTime give a real,
authoritative animation duration - not a proxy or a loop cycle length.

Usage:
  uv run dump_skill_cutin_durations.py [--chara-id 1001] [--out FILE]
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

NAME_RE = re.compile(
    r"^3d/motion/cutin/chara/body/chr(\d+)_001/anm_cti_chr\d+_001$"
)


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
                "SELECT n, h, e FROM a WHERE n LIKE '3d/motion/cutin/chara/body/chr%_001/anm_cti_chr%_001'"
            ).fetchall()
            conn.close()
            if rows:
                log.info("Loaded %d cut-in body motion entries from %s", len(rows), candidate.name)
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


def read_clip_duration(data: bytes) -> dict | None:
    """Return {duration_sec, loop_time, sample_rate} for the AnimationClip in this bundle."""
    env = UnityPy.load(data)
    for obj in env.objects:
        if obj.type.name != "AnimationClip":
            continue
        try:
            tree = obj.read_typetree()
        except Exception:
            continue
        muscle = tree.get("m_MuscleClip") or {}
        start = muscle.get("m_StartTime")
        stop = muscle.get("m_StopTime")
        loop = muscle.get("m_LoopTime")
        if isinstance(start, (int, float)) and isinstance(stop, (int, float)):
            return {
                "duration_sec": round(stop - start, 4),
                "loop_time": bool(loop),
                "sample_rate": tree.get("m_SampleRate"),
            }
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--game-dir", type=Path, default=DEFAULT_GAME_DIR)
    parser.add_argument("--chara-data", type=Path, default=DEFAULT_CHARA_DATA)
    parser.add_argument("--jp-chara-data", type=Path, default=DEFAULT_JP_CHARA_DATA)
    parser.add_argument("--chara-id", type=int, default=None)
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
        chara_id = int(m.group(1))
        if args.chara_id is not None and chara_id != args.chara_id:
            continue

        h = e["hash"]
        fp = args.game_dir / "dat" / h[:2] / h
        if not fp.is_file():
            log.warning("Missing bundle for chr%s at %s", chara_id, fp)
            continue
        try:
            data = decrypt_bundle(fp, e["key"])
            info = read_clip_duration(data)
        except Exception as exc:
            log.warning("Failed to read chr%s: %s", chara_id, exc)
            continue
        if info is None:
            log.warning("No AnimationClip muscle data found for chr%s", chara_id)
            continue

        name = chara_names.get(chara_id, "")
        results.append({"chara_id": chara_id, "chara_name": name, **info})
        log.info(
            "chr%s (%s): %.3fs (loop=%s)",
            chara_id, name, info["duration_sec"], info["loop_time"],
        )

    csv_path = args.out.with_suffix(".csv")
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["chara_id", "chara_name", "duration_sec", "loop_time", "sample_rate"]
        )
        writer.writeheader()
        writer.writerows(results)

    txt_path = args.out.with_suffix(".txt")
    with txt_path.open("w", encoding="utf-8") as f:
        f.write("Unique-skill cut-in body-pose animation durations (real AnimationClip length)\n")
        f.write("Source: 3d/motion/cutin/chara/body/chr{id}_001/anm_cti_chr{id}_001 (Mecanim MuscleClip)\n")
        f.write("Same clip plays regardless of unique-skill evolution tier.\n")
        f.write("=" * 90 + "\n\n")
        for r in results:
            f.write(
                f"{r['chara_name']:<28} (chr{r['chara_id']}): "
                f"{r['duration_sec']:.3f}s  loop={r['loop_time']}\n"
            )

    log.info("Wrote %s and %s (%d characters)", csv_path, txt_path, len(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
