#!/usr/bin/env python3
"""
Extract image assets (support card icons, character portraits) from
Uma Musume game bundles.

Uses the same meta DB + dat/ + UnityPy approach as extract_story_text.py.

The game's `meta` SQLite database maps asset names → file hashes.
Asset bundles in `dat/{hash[:2]}/{hash}` are encrypted; we decrypt them
using the same key as UmaViewer and extract Texture2D / Sprite objects.

Asset name patterns in the meta DB:
  Support card icons:   supportcard/supportcardtexture/tex_support_card_{id}
  Character portraits:  chara/chr_icon_{charaId}
  Character stand art:  chara/chara_stand_{charaIdPrefix}_{cardId}

Usage (standalone):
  uv run extract_assets.py                       # auto-detect from config.json
  uv run extract_assets.py /path/to/game/root    # explicit
  uv run extract_assets.py --help

Usage (as library, from gui.py):
  from extract_assets import extract_support_card_images
  extract_support_card_images(game_dir, output_dir, card_ids=[30001, 30002])
"""

from __future__ import annotations

import contextlib
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
    UnityPy = None  # type: ignore[assignment]

try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore[assignment]

log = logging.getLogger("extract_assets")

# ── Constants (same as extract_story_text.py / UmaViewer Config.cs) ────

AB_KEY = bytes([0x53, 0x2B, 0x46, 0x31, 0xE4, 0xA7, 0xB9, 0x47, 0x3E, 0x7C, 0xFB])

_FROZEN = getattr(sys, "frozen", False)
APP_DIR = Path(sys.executable).resolve().parent if _FROZEN else Path(__file__).resolve().parent


# ── Shared crypto (identical to extract_story_text.py) ─────────────────


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


# ── Meta DB reader (generalised from extract_story_text.py) ────────────


def _try_open_encrypted_meta(meta_path: Path):
    """Try opening the encrypted meta DB.  Returns a connection or None."""
    # Reuse the implementation from extract_story_text if available
    try:
        from extract_story_text import _try_open_encrypted_meta as _open

        return _open(meta_path)
    except ImportError:
        pass
    return None


def read_meta_entries_for_pattern(game_dir: Path, name_pattern: str) -> list[dict]:
    """
    Query the meta DB for rows whose name matches `name_pattern` (SQL LIKE).
    Returns list of {name, hash, key}.
    """
    meta_path = game_dir / "meta"
    if not meta_path.is_file():
        log.error("meta database not found at %s", meta_path)
        return []

    conn = None
    # Try plain SQLite
    try:
        c = sqlite3.connect(f"file:{meta_path}?mode=ro", uri=True)
        c.row_factory = sqlite3.Row
        tables = [
            r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        ]
        if "a" in tables:
            conn = c
        else:
            c.close()
    except Exception:
        pass

    # Try encrypted
    if conn is None:
        conn = _try_open_encrypted_meta(meta_path)
        if conn is None:
            log.error("Could not open meta database at %s", meta_path)
            return []

    entries: list[dict] = []
    try:
        cols_info = conn.execute("PRAGMA table_info(a)").fetchall()
        cols = {r[1] for r in cols_info}
        has_key = "e" in cols

        if has_key:
            sql = "SELECT n, h, e FROM a WHERE n LIKE ?"
        else:
            sql = "SELECT n, h FROM a WHERE n LIKE ?"

        rows = conn.execute(sql, (name_pattern,)).fetchall()
        for r in rows:
            entries.append(
                {
                    "name": r["n"],
                    "hash": r["h"],
                    "key": r["e"] if has_key else 0,
                }
            )
    except Exception as e:
        log.error("Failed querying meta: %s", e)
    finally:
        with contextlib.suppress(Exception):
            conn.close()

    return entries


# ── Image extraction from bundles ──────────────────────────────────────


def _save_image(image_data, output_path: Path) -> bool:
    """Save a UnityPy image object to a .webp file."""
    try:
        img = image_data.image  # PIL Image from UnityPy
        if img.mode == "RGBA":
            # Keep transparency
            pass
        elif img.mode != "RGB":
            img = img.convert("RGBA")
        img.save(str(output_path), "WEBP", quality=85)
        return True
    except Exception as e:
        log.debug("Failed to save image to %s: %s", output_path, e)
        return False


def extract_texture_from_bundle(
    file_path: Path,
    entry_key: int,
    output_path: Path,
    target_name: str | None = None,
) -> bool:
    """
    Extract a Texture2D/Sprite from an asset bundle and save as .webp.

    Args:
        file_path:   Path to the encrypted bundle on disk.
        entry_key:   Decryption key from meta DB.
        output_path: Where to write the .webp image.
        target_name: If set, only extract textures whose name contains this.

    Returns True if an image was successfully saved.
    """
    if UnityPy is None:
        return False

    try:
        if entry_key != 0:
            data = decrypt_bundle(file_path, entry_key)
            env = UnityPy.load(data)
        else:
            env = UnityPy.load(str(file_path))
    except Exception as e:
        log.debug("Failed to load bundle %s: %s", file_path.name, e)
        return False

    for obj in env.objects:
        try:
            if obj.type.name in ("Texture2D", "Sprite"):
                tex = obj.read()
                name = getattr(tex, "m_Name", "") or ""
                if target_name and target_name not in name:
                    continue
                return _save_image(tex, output_path)
        except Exception:
            continue

    return False


# ── Public API: Extract support card images ────────────────────────────


def extract_support_card_images(
    game_dir: Path,
    output_dir: Path,
    card_ids: list[int] | None = None,
    progress_callback=None,
) -> dict[int, str]:
    """
    Extract support card icon images from game asset bundles.

    Uses the ``support_thumb_{id:05d}`` asset name pattern from
    UmamusumeExplorer (GameAssets.GetSupportCardIcon), falling back to
    the full-texture ``tex_support_card_{id}`` if thumbnails aren't found.

    Returns {support_card_id: filename} for successfully extracted images.
    """
    if UnityPy is None:
        log.error("UnityPy not installed — cannot extract assets")
        return {}

    output_dir.mkdir(parents=True, exist_ok=True)
    dat_dir = game_dir / "dat"

    # ── Try thumbnail entries first (smaller, always downloaded) ────────
    # UmamusumeExplorer: "support_thumb_{id:d5}"
    # Meta name e.g. "supportcard/supportcardthumbnail/support_thumb_30001"
    entries = read_meta_entries_for_pattern(game_dir, "%support_thumb_%")
    id_pattern = re.compile(r"support_thumb_(\d+)")
    thumb_mode = True

    if not entries:
        # Fallback: full card textures
        entries = read_meta_entries_for_pattern(game_dir, "%tex_support_card_%")
        if not entries:
            entries = read_meta_entries_for_pattern(game_dir, "supportcard/%tex_support_card_%")
        id_pattern = re.compile(r"tex_support_card_(\d+)")
        thumb_mode = False

    log.info(
        "Found %d support card %s entries in meta",
        len(entries),
        "thumbnail" if thumb_mode else "texture",
    )

    # Exclude resourcelist manifests
    entries = [e for e in entries if "resourcelist" not in e["name"]]

    entry_map: dict[int, dict] = {}
    for e in entries:
        m = id_pattern.search(e["name"])
        if m:
            sc_id = int(m.group(1))
            if (card_ids is None or sc_id in card_ids) and (
                # Prefer the shortest name (base asset, not a variant)
                sc_id not in entry_map or len(e["name"]) < len(entry_map[sc_id]["name"])
            ):
                entry_map[sc_id] = e

    log.info("Matched %d support card IDs to extract", len(entry_map))

    results: dict[int, str] = {}
    total = len(entry_map)
    processed = 0

    for sc_id, entry in entry_map.items():
        h = entry["hash"]
        file_path = dat_dir / h[:2] / h
        out_name = f"support_thumb_{sc_id}.webp"
        out_file = output_dir / out_name

        # Also accept the old naming convention
        old_file = output_dir / f"support_card_{sc_id}.webp"
        if out_file.exists() or old_file.exists():
            results[sc_id] = out_file.name if out_file.exists() else old_file.name
            processed += 1
            if progress_callback:
                progress_callback(processed, total, len(results))
            continue

        if not file_path.is_file():
            processed += 1
            if progress_callback:
                progress_callback(processed, total, len(results))
            continue

        # target_name: match the texture's m_Name inside the bundle
        tex_target = f"support_thumb_{sc_id:05d}" if thumb_mode else f"tex_support_card_{sc_id}"
        ok = extract_texture_from_bundle(file_path, entry["key"], out_file, target_name=tex_target)
        if not ok:
            # Try without target_name filter (grab first texture)
            ok = extract_texture_from_bundle(file_path, entry["key"], out_file)
        if ok:
            results[sc_id] = out_file.name

        processed += 1
        if progress_callback and processed % 10 == 0:
            progress_callback(processed, total, len(results))

    if progress_callback:
        progress_callback(total, total, len(results))

    log.info("Extracted %d / %d support card images", len(results), total)
    return results


def extract_chara_icons(
    game_dir: Path,
    output_dir: Path,
    progress_callback=None,
) -> dict[int, str]:
    """
    Extract character icon images (small portraits) from game bundles.

    Uses the ``chr_icon_{charaId:04d}`` asset pattern from UmamusumeExplorer
    (GameAssets.GetCharaIcon).  These are the compact square/round icons used
    everywhere in the game UI.

    Returns {chara_id: filename} for extracted images.
    """
    if UnityPy is None:
        log.error("UnityPy not installed — cannot extract assets")
        return {}

    output_dir.mkdir(parents=True, exist_ok=True)
    dat_dir = game_dir / "dat"

    entries = read_meta_entries_for_pattern(game_dir, "%chr_icon_%")
    entries = [e for e in entries if "resourcelist" not in e["name"]]
    log.info("Found %d character icon entries in meta", len(entries))

    # Parse chara_id from entry name.
    # Base icons:   "chara/chrXXXX_YY/chr_icon_1001"  → chara_id 1001
    # Outfit icons: "chara/chrXXXX_YY/chr_icon_1001_100101_01" → skip (prefer base)
    base_pattern = re.compile(r"chr_icon_(\d{4})(?:[^_\d]|$)")
    outfit_pattern = re.compile(r"chr_icon_(\d{4})_(\d{6})_(\d{2})")

    # Collect: prefer base icon per chara_id, fall back to any outfit variant
    base_map: dict[int, dict] = {}
    outfit_map: dict[int, dict] = {}
    for e in entries:
        m_base = base_pattern.search(e["name"])
        m_outfit = outfit_pattern.search(e["name"])
        if m_base and not m_outfit:
            cid = int(m_base.group(1))
            if cid not in base_map or len(e["name"]) < len(base_map[cid]["name"]):
                base_map[cid] = e
        elif m_outfit:
            cid = int(m_outfit.group(1))
            if cid not in outfit_map:
                outfit_map[cid] = e

    # Merge: base takes priority
    entry_map: dict[int, dict] = {}
    for cid, e in outfit_map.items():
        entry_map[cid] = e
    for cid, e in base_map.items():
        entry_map[cid] = e  # overwrite outfit with base

    log.info("Matched %d unique character IDs for icon extraction", len(entry_map))

    results: dict[int, str] = {}
    total = len(entry_map)
    processed = 0

    for cid, entry in entry_map.items():
        h = entry["hash"]
        file_path = dat_dir / h[:2] / h
        out_file = output_dir / f"chr_icon_{cid:04d}.webp"

        if out_file.exists():
            results[cid] = out_file.name
            processed += 1
            if progress_callback:
                progress_callback(processed, total, len(results))
            continue

        if not file_path.is_file():
            processed += 1
            if progress_callback:
                progress_callback(processed, total, len(results))
            continue

        ok = extract_texture_from_bundle(
            file_path, entry["key"], out_file, target_name=f"chr_icon_{cid:04d}"
        )
        if not ok:
            # Try without target filter (grab first texture in bundle)
            ok = extract_texture_from_bundle(file_path, entry["key"], out_file)
        if ok:
            results[cid] = out_file.name

        processed += 1
        if progress_callback and processed % 20 == 0:
            progress_callback(processed, total, len(results))

    if progress_callback:
        progress_callback(total, total, len(results))

    log.info("Extracted %d / %d character icons", len(results), total)
    return results


def extract_chara_portraits(
    game_dir: Path,
    output_dir: Path,
    progress_callback=None,
) -> dict[str, str]:
    """
    Extract character portrait images (chara_stand_*) from game bundles.
    Returns {filename_stem: filename} for extracted images.
    """
    if UnityPy is None:
        log.error("UnityPy not installed — cannot extract assets")
        return {}

    output_dir.mkdir(parents=True, exist_ok=True)
    dat_dir = game_dir / "dat"

    entries = read_meta_entries_for_pattern(game_dir, "%chara_stand_%")
    log.info("Found %d character portrait entries in meta", len(entries))

    results: dict[str, str] = {}
    total = len(entries)
    processed = 0

    stand_pattern = re.compile(r"(chara_stand_\d+_\d+)")
    for entry in entries:
        m = stand_pattern.search(entry["name"])
        if not m:
            processed += 1
            continue

        stem = m.group(1)
        out_file = output_dir / f"{stem}.webp"
        if out_file.exists():
            results[stem] = out_file.name
            processed += 1
            continue

        h = entry["hash"]
        file_path = dat_dir / h[:2] / h
        if not file_path.is_file():
            processed += 1
            continue

        ok = extract_texture_from_bundle(file_path, entry["key"], out_file, target_name=stem)
        if ok:
            results[stem] = out_file.name

        processed += 1
        if progress_callback and processed % 20 == 0:
            progress_callback(processed, total, len(results))

    if progress_callback:
        progress_callback(total, total, len(results))

    log.info("Extracted %d / %d character portraits", len(results), total)
    return results


# ── CLI ────────────────────────────────────────────────────────────────


def main():
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(
        description="Extract image assets from Uma Musume game bundles."
    )
    parser.add_argument("game_dir", nargs="?", help="Path to game root (contains dat/ and meta)")
    parser.add_argument(
        "--type",
        choices=["support", "icons", "portraits", "all"],
        default="all",
        help="What to extract (default: all)",
    )
    parser.add_argument("--ids", nargs="*", type=int, help="Only extract these support card IDs")
    parser.add_argument(
        "--output", default=None, help="Output directory (default: static/cards or static/uma)"
    )
    args = parser.parse_args()

    # Find game dir
    game_dir = None
    if args.game_dir:
        game_dir = Path(args.game_dir)
    else:
        cfg_file = APP_DIR / "config.json"
        if cfg_file.is_file():
            with contextlib.suppress(Exception):
                cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
                gdd = cfg.get("game_data_dir")
                if gdd:
                    game_dir = Path(gdd)

    if not game_dir or not game_dir.is_dir():
        log.error(
            "Game directory not found. Pass it as argument or set game_data_dir in config.json"
        )
        sys.exit(1)

    if not (game_dir / "dat").is_dir():
        log.error("dat/ not found in %s", game_dir)
        sys.exit(1)

    if UnityPy is None:
        log.error("UnityPy is required.  Install with:  pip install UnityPy")
        sys.exit(1)

    def _progress(done, total, found):
        print(f"\r  {done}/{total} processed, {found} extracted", end="", flush=True)

    if args.type in ("support", "all"):
        out = Path(args.output) if args.output else APP_DIR / "static" / "cards"
        print(f"Extracting support card images → {out}")
        results = extract_support_card_images(
            game_dir, out, card_ids=args.ids, progress_callback=_progress
        )
        print(f"\n  Done: {len(results)} support card images")

    if args.type in ("icons", "all"):
        out = Path(args.output) if args.output else APP_DIR / "static" / "uma"
        print(f"Extracting character icons → {out}")
        results = extract_chara_icons(game_dir, out, progress_callback=_progress)
        print(f"\n  Done: {len(results)} character icons")

    if args.type in ("portraits", "all"):
        out = Path(args.output) if args.output else APP_DIR / "static" / "uma"
        print(f"Extracting character portraits → {out}")
        results = extract_chara_portraits(game_dir, out, progress_callback=_progress)
        print(f"\n  Done: {len(results)} character portraits")


if __name__ == "__main__":
    main()
