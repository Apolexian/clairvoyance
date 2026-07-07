#!/usr/bin/env python3
"""
Extract Uma Musume home screen conversations to CSV.

Output columns:
    uma_id          chara_id of the gallery uma (gallery_chara_id from trigger)
    uma_name        display name
    story_num       disp_order (1-indexed per uma, corresponds to "Slice of Life N")
    num_participants 1, 2, or 3
    chara_id_1      participant 1 chara_id
    chara_id_2      participant 2 chara_id (0 if solo)
    chara_id_3      participant 3 chara_id (0 if solo/duo)
    chara_name_1    display name of participant 1
    chara_name_2    display name of participant 2 (empty if solo)
    chara_name_3    display name of participant 3 (empty if solo/duo)
    pos_id          raw position code from home_story_trigger
    location        human-readable location label
    story_id        raw story_id from home_story_trigger
    asset_name      hometimeline asset name
    lines           pipe-separated dialogue: "Speaker: Text|Speaker: Text|..."

Usage:
    python extract_home_conversations.py
    python extract_home_conversations.py --game-dir "C:/path/to/Umamusume" --mdb "C:/path/to/master.mdb"
    python extract_home_conversations.py --no-text   # skip asset extraction, metadata only

Requirements:
    pip install UnityPy
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
import struct
import sys
from pathlib import Path

try:
    import UnityPy
except ImportError:
    print("ERROR: UnityPy required. Install: pip install UnityPy")
    sys.exit(1)

# ── Paths ──────────────────────────────────────────────────────────────

GAME_DIR_DEFAULT = Path("C:/Users/nikit/AppData/LocalLow/Cygames/Umamusume")
MDB_DEFAULT = Path("C:/Users/nikit/Documents/work/mastermdb/master.mdb")
OUTPUT_FILE = Path(__file__).parent / "home_conversations.csv"

# ── Asset decryption (same keys as extract_story_text.py) ─────────────

AB_KEY = bytes([0x53, 0x2B, 0x46, 0x31, 0xE4, 0xA7, 0xB9, 0x47, 0x3E, 0x7C, 0xFB])


def derive_bundle_key(entry_key: int) -> bytes:
    key_bytes = struct.pack("<q", entry_key)
    result = bytearray(len(AB_KEY) * 8)
    for i, b in enumerate(AB_KEY):
        base = i * 8
        for j in range(8):
            result[base + j] = b ^ key_bytes[j]
    return bytes(result)


def decrypt_bundle(file_path: Path, entry_key: int) -> bytes:
    data = bytearray(file_path.read_bytes())
    if len(data) <= 256 or entry_key == 0:
        return bytes(data)
    key = derive_bundle_key(entry_key)
    kl = len(key)
    for i in range(256, len(data)):
        data[i] ^= key[i % kl]
    return bytes(data)


# ── Location labels ────────────────────────────────────────────────────

# Hundreds digit of pos_id → location zone
# Derived from Aclone's example list cross-referenced with pos_ids
LOCATION_ZONE = {
    1: "right (jukebox)",
    2: "back left (campus map)",
    3: "middle left (table)",
    4: "middle right (advertisements)",
    5: "front left (campus map)",
}


def pos_id_to_location(pos_id: int) -> str:
    zone = pos_id // 100
    return LOCATION_ZONE.get(zone, f"pos_{pos_id}")


# ── Asset name construction ────────────────────────────────────────────

def make_asset_name(num: int, story_id: int) -> str:
    return f"home/data/00000/{num:02d}/hometimeline_00000_{num:02d}_{story_id:07d}"


def make_voice_sheet_id(num: int, story_id: int) -> str:
    """VoiceSheetId embedded in each clip — used to filter within shared bundles."""
    return f"00000_{num:02d}_{story_id:07d}"


# ── Line extraction from bundle ────────────────────────────────────────

def extract_lines(file_path: Path, entry_key: int, voice_sheet_id: str = "") -> list[tuple[str, str]]:
    """Return ordered list of (speaker_name, text) from a hometimeline bundle.

    voice_sheet_id filters to the correct story within bundles that contain
    multiple stories (e.g. solo + duo stories share one asset file).
    Format: '00000_{num:02d}_{story_id:07d}'
    Ordering uses CueId which reflects the game's playback sequence.
    """
    try:
        data = decrypt_bundle(file_path, entry_key)
        env = UnityPy.load(data)
    except Exception as e:
        print(f"  WARN: failed to load {file_path.name}: {e}", file=sys.stderr)
        return []

    # (cue_id, name, text) — CueId is playback order within a story
    clips: list[tuple[int, str, str]] = []

    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            tree = obj.read_typetree()
        except Exception:
            continue
        if not isinstance(tree, dict):
            continue

        if "Text" not in tree or "CharaId" not in tree or "Name" not in tree:
            continue

        text = tree.get("Text", "").strip()
        name = tree.get("Name", "").strip()
        if not text:
            continue

        # Filter to matching story when voice_sheet_id provided
        if voice_sheet_id and tree.get("VoiceSheetId", "") != voice_sheet_id:
            continue

        cue_id = tree.get("CueId", 0)
        clips.append((cue_id, name, text))

    # Sort by CueId for correct playback order
    clips.sort(key=lambda x: x[0])
    return [(name, text) for _, name, text in clips]


# ── Main ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Extract home conversations to CSV")
    parser.add_argument("--game-dir", default=str(GAME_DIR_DEFAULT))
    parser.add_argument("--mdb", default=str(MDB_DEFAULT))
    parser.add_argument("--output", default=str(OUTPUT_FILE))
    parser.add_argument("--no-text", action="store_true", help="Skip dialogue extraction")
    args = parser.parse_args()

    game_dir = Path(args.game_dir)
    mdb_path = Path(args.mdb)
    dat_dir = game_dir / "dat"
    meta_path = game_dir / "meta_decrypted"

    # Prefer decrypted meta; fall back to encrypted
    if not meta_path.is_file():
        meta_path = game_dir / "meta"
    if not meta_path.is_file():
        print(f"ERROR: meta not found in {game_dir}", file=sys.stderr)
        sys.exit(1)

    # ── Load chara names from master.mdb ──
    mdb = sqlite3.connect(str(mdb_path))
    chara_names: dict[int, str] = {}
    for row in mdb.execute("SELECT \"index\", text FROM text_data WHERE category=170"):
        chara_names[row[0]] = row[1]

    # ── Load triggers ──
    triggers = mdb.execute(
        "SELECT story_id, num, chara_id_1, chara_id_2, chara_id_3, "
        "pos_id, gallery_chara_id, disp_order "
        "FROM home_story_trigger ORDER BY gallery_chara_id, disp_order"
    ).fetchall()
    mdb.close()

    # ── Build asset hash lookup from meta ──
    meta_conn = sqlite3.connect(f"file:{meta_path}?mode=ro", uri=True)
    meta_conn.row_factory = sqlite3.Row
    asset_lookup: dict[str, tuple[str, int]] = {}
    for row in meta_conn.execute(
        "SELECT n, h, e FROM a WHERE n LIKE 'home/data%hometimeline%' "
        "AND n NOT LIKE '%resourcelist%'"
    ):
        asset_lookup[row["n"]] = (row["h"], row["e"])
    meta_conn.close()
    print(f"Loaded {len(asset_lookup)} hometimeline asset entries", file=sys.stderr)

    # ── Extract ──
    rows = []
    total = len(triggers)
    for i, (story_id, num, cid1, cid2, cid3, pos_id, gallery_cid, disp_order) in enumerate(triggers):
        asset_name = make_asset_name(num, story_id)
        location = pos_id_to_location(pos_id)

        uma_name = chara_names.get(gallery_cid, str(gallery_cid))
        name1 = chara_names.get(cid1, str(cid1)) if cid1 else ""
        name2 = chara_names.get(cid2, str(cid2)) if cid2 else ""
        name3 = chara_names.get(cid3, str(cid3)) if cid3 else ""

        lines_str = ""
        if not args.no_text:
            meta_entry = asset_lookup.get(asset_name)
            if meta_entry:
                h, key = meta_entry
                file_path = dat_dir / h[:2] / h
                if file_path.is_file():
                    vsid = make_voice_sheet_id(num, story_id)
                    lines = extract_lines(file_path, key, voice_sheet_id=vsid)
                    lines_str = "|".join(
                        f"{spk}: {txt}".replace("\n", " ").replace("<n>", " ")
                        for spk, txt in lines
                    )
                else:
                    lines_str = "FILE_MISSING"
            else:
                lines_str = "ASSET_NOT_IN_META"

        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{total} processed...", file=sys.stderr)

        rows.append({
            "uma_id": gallery_cid,
            "uma_name": uma_name,
            "story_num": disp_order,
            "num_participants": num,
            "chara_id_1": cid1,
            "chara_id_2": cid2 or "",
            "chara_id_3": cid3 or "",
            "chara_name_1": name1,
            "chara_name_2": name2,
            "chara_name_3": name3,
            "pos_id": pos_id,
            "location": location,
            "story_id": story_id,
            "asset_name": asset_name,
            "lines": lines_str,
        })

    output_path = Path(args.output)
    fieldnames = [
        "uma_id", "uma_name", "story_num", "num_participants",
        "chara_id_1", "chara_id_2", "chara_id_3",
        "chara_name_1", "chara_name_2", "chara_name_3",
        "pos_id", "location", "story_id", "asset_name", "lines",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {output_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
