#!/usr/bin/env python3
"""
Extract event choice text from Uma Musume story asset bundles.

Reads the game's `meta` database to locate story data assets, then uses
UnityPy to extract the StoryData JSON from each asset bundle, pulling
out the choice option labels.

Result is written to `story_choices.json` — a mapping of:
    { story_id_str: ["Choice 1 text", "Choice 2 text", ...], ... }

Usage:
    uv run extract_story_text.py                       # auto-detect game dir from config.json
    uv run extract_story_text.py /path/to/game/root    # explicit game directory
    uv run extract_story_text.py --help

Requirements:
    pip install UnityPy   (or:  uv add --optional extract UnityPy)

The game directory should contain:
    meta                (SQLite database mapping asset names → file hashes)
    master/master.mdb   (master database)
    dat/XX/...          (asset bundle files)
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import struct
import sys
from pathlib import Path

try:
    import UnityPy
except ImportError:
    print("ERROR: UnityPy is required.  Install with:  pip install UnityPy")
    sys.exit(1)

# ── Logging ────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("extract_story_text")

# ── Constants from UmaViewer Config.cs ─────────────────────────────────

# Asset bundle encryption key (from UmaViewer Config.cs L136-139)
AB_KEY = bytes([0x53, 0x2B, 0x46, 0x31, 0xE4, 0xA7, 0xB9, 0x47, 0x3E, 0x7C, 0xFB])

# ── Paths ──────────────────────────────────────────────────────────────

_FROZEN = getattr(sys, "frozen", False)
if _FROZEN:
    APP_DIR = Path(sys.executable).resolve().parent
else:
    APP_DIR = Path(__file__).resolve().parent

CONFIG_FILE = APP_DIR / "config.json"
OUTPUT_FILE = APP_DIR / "story_choices.json"


def _load_config() -> dict:
    if CONFIG_FILE.is_file():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


# ── Game directory detection ───────────────────────────────────────────


def detect_game_dir(explicit_path: str | None = None) -> Path | None:
    """
    Find the game root directory.

    Priority:
      1. Explicit CLI argument
      2. 'game_data_dir' in config.json
      3. Derived from 'master_db_path' in config.json (go up 2 levels from master/master.mdb)
    """
    if explicit_path:
        p = Path(explicit_path)
        if p.is_dir():
            return p
        log.error("Explicit path is not a directory: %s", explicit_path)
        return None

    cfg = _load_config()

    # Check explicit game_data_dir config
    gdd = cfg.get("game_data_dir")
    if gdd and Path(gdd).is_dir():
        return Path(gdd)

    # Derive from master_db_path  (e.g. .../Cygames/umamusume/master/master.mdb → .../Cygames/umamusume)
    mdb = cfg.get("master_db_path")
    if mdb:
        game_root = Path(mdb).resolve().parent.parent
        if game_root.is_dir():
            return game_root

    return None


# ── Meta database reading ──────────────────────────────────────────────


def read_meta_entries(game_dir: Path) -> list[dict]:
    """
    Read story data entries from the meta database.

    Returns list of {name, hash, key} dicts for story timeline assets.
    """
    meta_path = game_dir / "meta"
    if not meta_path.is_file():
        # Try UmaViewer standalone copy
        meta_path = game_dir / "meta_umaviewer"
    if not meta_path.is_file():
        log.error("Meta database not found at %s", game_dir / "meta")
        return []

    entries = []
    try:
        conn = sqlite3.connect(f"file:{meta_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row

        # Check if encryption column 'e' exists
        cols = {r[1] for r in conn.execute("PRAGMA table_info(a)").fetchall()}
        has_key = "e" in cols

        if has_key:
            sql = "SELECT n, h, e FROM a WHERE n LIKE 'story/data/%storytimeline%'"
        else:
            sql = "SELECT n, h FROM a WHERE n LIKE 'story/data/%storytimeline%'"

        rows = conn.execute(sql).fetchall()
        for r in rows:
            entry = {
                "name": r["n"],
                "hash": r["h"],
                "key": r["e"] if has_key else 0,
            }
            entries.append(entry)
        conn.close()
        log.info("Found %d story timeline entries in meta database", len(entries))
    except Exception as e:
        log.error("Failed to read meta database: %s", e)
        log.info(
            "The meta database may be encrypted. Try using an unencrypted copy (meta_umaviewer)."
        )

    return entries


# ── Asset bundle decryption ────────────────────────────────────────────


def derive_bundle_key(entry_key: int) -> bytes:
    """
    Derive the XOR decryption key for an asset bundle.

    Matches UmaViewer UmaDatabaseEntry.cs FKey property:
    - AB_KEY is 11 bytes
    - entry_key is a 64-bit int from the meta database
    - Output is 11*8 = 88 bytes
    """
    key_bytes = struct.pack("<q", entry_key)  # little-endian int64
    result = bytearray(len(AB_KEY) * 8)
    for i, b in enumerate(AB_KEY):
        base_offset = i * 8
        for j in range(8):
            result[base_offset + j] = b ^ key_bytes[j]
    return bytes(result)


def decrypt_bundle(file_path: Path, entry_key: int) -> bytes:
    """
    Decrypt an encrypted asset bundle file.

    Matches UmaViewer AssetBundleDecryptor.cs:
    - First 256 bytes are left as-is (header)
    - Remaining bytes are XOR'd with the cycling key
    """
    data = bytearray(file_path.read_bytes())
    if len(data) <= 256:
        return bytes(data)

    key = derive_bundle_key(entry_key)
    key_len = len(key)
    for i in range(256, len(data)):
        data[i] ^= key[i % key_len]
    return bytes(data)


# ── Story data parsing ─────────────────────────────────────────────────


def extract_story_id_from_name(asset_name: str) -> int | None:
    """Extract the numeric story ID from an asset name like 'story/data/50/5001011/storytimeline_500101102'."""
    m = re.search(r"storytimeline_(\d+)", asset_name)
    if m:
        return int(m.group(1))
    return None


def parse_story_choices(json_text: str) -> list[str]:
    """
    Parse a StoryData JSON and extract choice text labels.

    The StoryData has a BlockList array. Blocks with ChoiceDataList
    contain the player's choice options.
    """
    choices: list[str] = []
    try:
        data = json.loads(json_text)
    except (json.JSONDecodeError, ValueError):
        return choices

    block_list = data.get("BlockList", [])
    for block in block_list:
        choice_data_list = block.get("ChoiceDataList")
        if choice_data_list and isinstance(choice_data_list, list):
            for choice in choice_data_list:
                text = choice.get("Text", "").strip()
                if text:
                    choices.append(text)
    return choices


def extract_choices_from_bundle(file_path: Path, entry_key: int = 0) -> dict[int, list[str]]:
    """
    Load an asset bundle and extract story choice text from TextAsset objects.

    Returns {story_id: [choice_texts]} for all stories found in the bundle.
    """
    results: dict[int, list[str]] = {}

    try:
        if entry_key != 0:
            data = decrypt_bundle(file_path, entry_key)
            env = UnityPy.load(data)
        else:
            env = UnityPy.load(str(file_path))
    except Exception as e:
        log.debug("Failed to load bundle %s: %s", file_path.name, e)
        return results

    for obj in env.objects:
        try:
            if obj.type.name == "TextAsset":
                text_asset = obj.read()
                # The asset name often encodes the story ID
                asset_name = getattr(text_asset, "m_Name", "") or ""

                # Try to get the text content
                text_content = None
                if hasattr(text_asset, "m_Script"):
                    raw = text_asset.m_Script
                    if isinstance(raw, bytes):
                        text_content = raw.decode("utf-8", errors="replace")
                    else:
                        text_content = str(raw)
                elif hasattr(text_asset, "text"):
                    text_content = text_asset.text

                if not text_content:
                    continue

                # Only parse JSON-like content that looks like story data
                text_content = text_content.strip()
                if not text_content.startswith("{"):
                    continue

                choices = parse_story_choices(text_content)
                if choices:
                    # Try to get story_id from the asset name
                    story_id = None
                    m = re.search(r"storytimeline_?(\d+)", asset_name)
                    if m:
                        story_id = int(m.group(1))

                    if story_id:
                        results[story_id] = choices
        except Exception:
            continue

    return results


# ── Main extraction loop ───────────────────────────────────────────────


def run_extraction(game_dir: Path) -> dict[str, list[str]]:
    """
    Main extraction: scan all story asset bundles and extract choice text.

    Returns the full {story_id_str: [choice_texts]} mapping.
    """
    dat_dir = game_dir / "dat"
    if not dat_dir.is_dir():
        log.error("dat/ directory not found at %s", dat_dir)
        return {}

    entries = read_meta_entries(game_dir)
    if not entries:
        return {}

    all_choices: dict[str, list[str]] = {}
    processed = 0
    skipped = 0
    found = 0

    for i, entry in enumerate(entries):
        h = entry["hash"]
        file_path = dat_dir / h[:2] / h
        if not file_path.is_file():
            skipped += 1
            continue

        story_id_from_name = extract_story_id_from_name(entry["name"])

        bundle_choices = extract_choices_from_bundle(file_path, entry["key"])
        processed += 1

        if bundle_choices:
            for sid, choices in bundle_choices.items():
                all_choices[str(sid)] = choices
                found += 1
        elif story_id_from_name:
            # Even if we didn't find choices in the bundle, try loading
            # the bundle by story_id path as fallback
            pass

        if (i + 1) % 200 == 0:
            log.info(
                "  Progress: %d/%d entries (%d processed, %d with choices, %d skipped)",
                i + 1,
                len(entries),
                processed,
                found,
                skipped,
            )

    log.info(
        "Done: %d entries scanned, %d bundles processed, %d stories with choices, %d files missing",
        len(entries),
        processed,
        found,
        skipped,
    )
    return all_choices


# ── CLI ────────────────────────────────────────────────────────────────


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract event choice text from Uma Musume story asset bundles."
    )
    parser.add_argument(
        "game_dir",
        nargs="?",
        default=None,
        help="Path to the game data directory (containing meta, master/, dat/). "
        "Auto-detected from config.json if not specified.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=str(OUTPUT_FILE),
        help=f"Output JSON file path (default: {OUTPUT_FILE})",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    game_dir = detect_game_dir(args.game_dir)
    if not game_dir:
        log.error(
            "Could not detect game directory.\n"
            "  Either pass it as an argument:\n"
            "    python extract_story_text.py /path/to/Cygames/umamusume\n"
            "  Or set 'game_data_dir' in config.json:\n"
            '    {"game_data_dir": "/path/to/Cygames/umamusume"}\n'
            "  Or ensure 'master_db_path' in config.json points to a master.mdb\n"
            "  inside the game directory (e.g. .../umamusume/master/master.mdb)."
        )
        sys.exit(1)

    log.info("Game directory: %s", game_dir)

    # Verify expected structure
    meta_exists = (game_dir / "meta").is_file() or (game_dir / "meta_umaviewer").is_file()
    dat_exists = (game_dir / "dat").is_dir()
    if not meta_exists:
        log.error("meta database not found in %s", game_dir)
        sys.exit(1)
    if not dat_exists:
        log.error("dat/ directory not found in %s", game_dir)
        sys.exit(1)

    log.info("Starting extraction...")
    choices = run_extraction(game_dir)

    # Merge with existing file if present
    output_path = Path(args.output)
    if output_path.is_file():
        try:
            existing = json.loads(output_path.read_text(encoding="utf-8"))
            if isinstance(existing, dict):
                log.info("Merging with %d existing entries from %s", len(existing), output_path)
                existing.update(choices)
                choices = existing
        except Exception:
            pass

    output_path.write_text(
        json.dumps(choices, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    log.info("Wrote %d story choice entries to %s", len(choices), output_path)


if __name__ == "__main__":
    main()
