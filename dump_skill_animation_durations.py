#!/usr/bin/env python3
"""
Extract unique-skill activation VFX durations from the game's charaskill
effect prefab bundles.

The game has no data-table field for "how long does the unique skill
activation animation play" - that's baked into Unity asset bundles
(ParticleSystem prefabs), not master.mdb. This script decrypts those
bundles (same approach as extract_assets.py / extract_story_text.py),
reads every ParticleSystem's `lengthInSec` via UnityPy's typetree reader,
and reports the max per prefab-group as an approximation of the visual
effect's on-screen duration.

Asset naming: 3d/effect/charaskill/pfb_eff_chr{charaId}_{group}/pfb_eff_chr{charaId}_{group}_{NN}
  - group is usually 00 / 02 / 03, one bundle per unique-skill tier
    (base unique skill, then its two evolutions) - matches the game's
    3-tier unique skill evolution system.
  - each group is a *set* of prefab files (NN = 01, 02, 03, ...), each
    holding a handful of Unity objects (ParticleSystem, GameObject,
    Material, Texture2D, Transform). The group's overall visual duration
    is approximated as the max lengthInSec across all ParticleSystems in
    all its files.

Usage:
  uv run dump_skill_animation_durations.py [--chara-id 1001] [--out FILE]

Output: a CSV (chara_id, chara_name, group, num_files, num_particle_systems,
max_duration_sec) plus a human-readable .txt summary, both written next to
each other.
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
from collections import defaultdict
from pathlib import Path

import UnityPy

log = logging.getLogger("dump_skill_animation_durations")
logging.basicConfig(level=logging.INFO, format="%(message)s")

AB_KEY = bytes([0x53, 0x2B, 0x46, 0x31, 0xE4, 0xA7, 0xB9, 0x47, 0x3E, 0x7C, 0xFB])

DEFAULT_GAME_DIR = Path.home() / "AppData/LocalLow/Cygames/Umamusume"
# uma.guide repo - used to resolve charaId -> character name for the report
DEFAULT_CHARA_DATA = (
    Path.home()
    / "Documents/work/umaguide/docs/.vitepress/theme/data/TerumiCharacterData.json"
)
# Fallback for JP-only characters missing from TerumiCharacterData.json
DEFAULT_JP_CHARA_DATA = (
    Path.home() / "Documents/work/umaguide/docs/.vitepress/theme/data/jpumas.json"
)

NAME_RE = re.compile(
    r"^3d/effect/charaskill/pfb_eff_chr(\d+)_(\d+)/pfb_eff_chr\d+_\d+_(\d+)$"
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
    """Read all charaskill effect prefab rows from the (already-decrypted)
    meta DB. Falls back to meta_decrypted if meta itself isn't plain sqlite."""
    for candidate in (game_dir / "meta_decrypted", game_dir / "meta"):
        if not candidate.is_file():
            continue
        try:
            conn = sqlite3.connect(f"file:{candidate}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT n, h, e FROM a WHERE n LIKE '3d/effect/charaskill/pfb_eff_chr%'"
            ).fetchall()
            conn.close()
            if rows:
                log.info("Loaded %d charaskill entries from %s", len(rows), candidate.name)
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

    # Fill in JP-only characters (name = [jp, en]) via their outfit ids (cardId // 100)
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


def max_particle_length(data: bytes) -> tuple[float, int]:
    """Return (max lengthInSec across ParticleSystems, count of ParticleSystems) in a bundle."""
    env = UnityPy.load(data)
    best = 0.0
    count = 0
    for obj in env.objects:
        if obj.type.name != "ParticleSystem":
            continue
        count += 1
        try:
            tree = obj.read_typetree()
        except Exception:
            continue
        length = tree.get("lengthInSec")
        if isinstance(length, (int, float)):
            best = max(best, float(length))
    return best, count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--game-dir", type=Path, default=DEFAULT_GAME_DIR)
    parser.add_argument("--chara-data", type=Path, default=DEFAULT_CHARA_DATA)
    parser.add_argument("--jp-chara-data", type=Path, default=DEFAULT_JP_CHARA_DATA)
    parser.add_argument("--chara-id", type=int, default=None, help="Only process this charaId")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent / "skill_animation_durations",
        help="Output path prefix (writes .csv and .txt)",
    )
    args = parser.parse_args()

    entries = load_meta_entries(args.game_dir)
    if not entries:
        return 1

    chara_names = load_chara_names(args.chara_data, args.jp_chara_data)

    # group[(charaId, group)] -> list of (name, hash, key)
    groups: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for e in entries:
        m = NAME_RE.match(e["name"])
        if not m:
            continue
        chara_id, group, _stage = int(m.group(1)), int(m.group(2)), m.group(3)
        if args.chara_id is not None and chara_id != args.chara_id:
            continue
        groups[(chara_id, group)].append(e)

    log.info("Found %d (charaId, group) prefab sets to process", len(groups))

    results = []
    for (chara_id, group), files in sorted(groups.items()):
        max_dur = 0.0
        ps_count = 0
        ok_files = 0
        for e in files:
            h = e["hash"]
            fp = args.game_dir / "dat" / h[:2] / h
            if not fp.is_file():
                continue
            try:
                data = decrypt_bundle(fp, e["key"])
                dur, count = max_particle_length(data)
            except Exception as exc:
                log.warning("Failed to read %s: %s", e["name"], exc)
                continue
            ok_files += 1
            ps_count += count
            max_dur = max(max_dur, dur)
        results.append(
            {
                "chara_id": chara_id,
                "chara_name": chara_names.get(chara_id, ""),
                "group": group,
                "num_files": ok_files,
                "num_particle_systems": ps_count,
                "max_duration_sec": round(max_dur, 3),
            }
        )
        log.info(
            "chr%s_%02d (%s): %d files, %d particle systems, max %.2fs",
            chara_id, group, chara_names.get(chara_id, "?"), ok_files, ps_count, max_dur,
        )

    csv_path = args.out.with_suffix(".csv")
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["chara_id", "chara_name", "group", "num_files", "num_particle_systems", "max_duration_sec"],
        )
        writer.writeheader()
        writer.writerows(results)

    txt_path = args.out.with_suffix(".txt")
    with txt_path.open("w", encoding="utf-8") as f:
        f.write("Unique-skill activation VFX durations (approx, from ParticleSystem.lengthInSec)\n")
        f.write("Groups are the game's unique-skill evolution tiers (00 = base, then evolutions).\n")
        f.write("=" * 90 + "\n\n")
        current_chara = None
        for r in results:
            if r["chara_id"] != current_chara:
                current_chara = r["chara_id"]
                f.write(f"\n{r['chara_name']} (chr{r['chara_id']})\n")
            f.write(
                f"  group {r['group']:02d}: max {r['max_duration_sec']:.2f}s "
                f"({r['num_particle_systems']} particle systems across {r['num_files']} files)\n"
            )

    log.info("Wrote %s and %s", csv_path, txt_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
