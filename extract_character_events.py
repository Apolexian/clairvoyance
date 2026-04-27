#!/usr/bin/env python3
"""
Extract character event data from Uma Musume game assets.

Produces a JSON file compatible with umaguide's character_events_clean.json format.

Pipeline:
  1. Query JP master.mdb for card→story mapping, event names, reward data
  2. Read game meta DB to locate story asset bundles
  3. Decrypt + parse bundles to extract choice text and effect data (multithreaded)
  4. Map numeric effects to human-readable strings (Speed +10, etc.)
  5. Output in character_events_clean.json format

Usage:
    uv run --extra extract extract_character_events.py /path/to/game/root
    uv run --extra extract extract_character_events.py /path/to/game/root --masterdb dump-jp/master.mdb
    uv run --extra extract extract_character_events.py /path/to/game/root --cards 100101,100201
    uv run --extra extract extract_character_events.py --masterdb-only  # no game dir, masterdb only (no choice text/effects from assets)
"""

from __future__ import annotations

import argparse
import contextlib
import json
import logging
import os
import re
import sqlite3
import struct
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
log = logging.getLogger("extract_events")

# ── Crypto (shared with dump_all_assets.py) ────────────────────────────

AB_KEY = bytes([0x53, 0x2B, 0x46, 0x31, 0xE4, 0xA7, 0xB9, 0x47, 0x3E, 0x7C, 0xFB])


def derive_bundle_key(entry_key: int) -> bytes:
    key_bytes = struct.pack("<q", entry_key)
    result = bytearray(len(AB_KEY) * 8)
    for i, b in enumerate(AB_KEY):
        base = i * 8
        for j in range(8):
            result[base + j] = b ^ key_bytes[j]
    return bytes(result)


def _decrypt_python(data: bytearray, key: bytes, offset: int = 256) -> None:
    kl = len(key)
    for i in range(offset, len(data)):
        data[i] ^= key[i % kl]


_fast_xor = None


def _compile_xor_lib():
    import subprocess
    import tempfile

    c_src = r"""
#include <stddef.h>
void xor_decrypt(unsigned char *data, size_t data_len,
                 const unsigned char *key, size_t key_len,
                 size_t offset) {
    for (size_t i = offset; i < data_len; i++) {
        data[i] ^= key[i % key_len];
    }
}
"""
    tmpdir = tempfile.mkdtemp(prefix="clairvoyance_xor_")
    src_path = os.path.join(tmpdir, "xor.c")
    if sys.platform == "darwin":
        lib_path = os.path.join(tmpdir, "xor.dylib")
        lib_flag = "-dynamiclib"
    elif sys.platform == "win32":
        return None
    else:
        lib_path = os.path.join(tmpdir, "xor.so")
        lib_flag = "-shared"

    try:
        with open(src_path, "w") as f:
            f.write(c_src)
        subprocess.run(
            ["cc", "-O3", "-fPIC", lib_flag, "-o", lib_path, src_path],
            check=True,
            capture_output=True,
        )
        import ctypes as ct

        xorlib = ct.CDLL(lib_path)
        xorlib.xor_decrypt.argtypes = [
            ct.c_char_p, ct.c_size_t, ct.c_char_p, ct.c_size_t, ct.c_size_t,
        ]
        xorlib.xor_decrypt.restype = None

        def _fast_decrypt(data: bytearray, key: bytes, offset: int = 256) -> None:
            n = len(data)
            buf = (ct.c_ubyte * n).from_buffer(data)
            xorlib.xor_decrypt(
                ct.cast(buf, ct.c_char_p), ct.c_size_t(n),
                ct.c_char_p(key), ct.c_size_t(len(key)),
                ct.c_size_t(offset),
            )

        return _fast_decrypt
    except Exception:
        return None


def _init_xor():
    global _fast_xor
    if _fast_xor is None:
        _fast_xor = _compile_xor_lib()


def _xor_decrypt(data: bytearray, key: bytes, offset: int = 256) -> None:
    if _fast_xor:
        _fast_xor(data, key, offset)
    else:
        _decrypt_python(data, key, offset)


def decrypt_bundle(file_path: Path, entry_key: int) -> bytes:
    data = bytearray(file_path.read_bytes())
    if len(data) <= 256:
        return bytes(data)
    key = derive_bundle_key(entry_key)
    _xor_decrypt(data, key, 256)
    return bytes(data)


# ── Effect type mapping ────────────────────────────────────────────────

# Maps StatusType enum values from story SuccessEffect/FailureEffect to readable names.
# Derived from game decompilation and community documentation.
STATUS_TYPE_MAP = {
    1: "Speed",
    2: "Stamina",
    3: "Power",
    4: "Guts",
    5: "Wit",
    6: "Max Energy",
    7: "Skill Points",
    10: "Energy",
    # Motivation/mood (value: +1 = mood up, -1 = mood down)
    11: "Mood",
    # Skill hint (value = skill_id)
    21: "hint",
    22: "hint",  # hint level +2
    # Condition gain/loss
    30: "condition_gain",
    31: "condition_loss",
    # Bond
    40: "Bond",
    # All stats
    50: "All Stats",
}

# Condition IDs to names
CONDITION_MAP = {
    1: "Keen",           # やる気アップ
    2: "Dull",           # やる気ダウン
    3: "Charming",       # 愛嬌◯
    4: "Rising Star",    # 注目株
    5: "Slacker",        # なまけ癖
    6: "Slow Metabolism", # 太り気味
    7: "Night Owl",      # 夜ふかし気味
    8: "Good Practice",  # 練習上手◯
    9: "Love of Fans",   # ファン大好き
    10: "Sharp",         # 切れ者
    11: "Big Eater",     # 大食い
}


def format_effect(status_type: int, value: int) -> str | None:
    """Convert a numeric status type + value into a human-readable outcome string."""
    name = STATUS_TYPE_MAP.get(status_type)
    if name is None:
        return None

    if name == "hint":
        # value is skill_id — format as "SKILLID hint +N"
        # The hint level is implied by which type (21=+1, 22=+2)
        level = 2 if status_type == 22 else 1
        return f"{value} hint +{level}"

    if name == "Mood":
        return f"Mood {value:+d}" if value != 0 else None

    if name in ("condition_gain", "condition_loss"):
        cond_name = CONDITION_MAP.get(value, f"Condition_{value}")
        prefix = "Get" if name == "condition_gain" else "Lose"
        return f"{prefix} {cond_name}"

    if value == 0:
        return None

    return f"{name} {value:+d}" if value < 0 else f"{name} +{value}"


# ── Master DB queries ──────────────────────────────────────────────────


def query_masterdb(
    db_path: Path,
    card_ids: list[int] | None = None,
) -> dict:
    """
    Query the JP master.mdb for all character event data.

    Returns:
        {
            "cards": {card_id: {chara_id, stories: [{story_id, event_name, ...}]}},
            "common_stories": {chara_id: [{story_id, event_name, card_id}]},
        }
    """
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    # Get all card_id → chara_id mappings
    card_chara_map: dict[int, int] = {}
    rows = conn.execute(
        "SELECT DISTINCT card_id, card_chara_id FROM single_mode_story_data "
        "WHERE card_id != 0 AND id < 100000"
    ).fetchall()
    for r in rows:
        card_chara_map[r["card_id"]] = r["card_chara_id"]

    if card_ids:
        target_cards = set(card_ids)
    else:
        target_cards = set(card_chara_map.keys())

    # Get all relevant chara_ids
    target_charas = {card_chara_map[c] for c in target_cards if c in card_chara_map}

    # Query all stories for target characters
    # card_id=0 means shared across all outfits of that character
    placeholders = ",".join("?" * len(target_charas))
    stories = conn.execute(
        f"SELECT s.id, s.story_id, s.card_id, s.card_chara_id, s.support_card_id, "
        f"s.event_category, t.text as event_name "
        f"FROM single_mode_story_data s "
        f"LEFT JOIN text_data t ON t.category=181 AND t.\"index\"=s.story_id "
        f"WHERE s.card_chara_id IN ({placeholders}) "
        f"AND s.support_card_id = 0 AND s.id < 100000 "
        f"ORDER BY s.story_id",
        list(target_charas),
    ).fetchall()

    # Organise: card-specific stories vs shared chara stories
    cards: dict[int, dict] = {}
    common_stories: dict[int, list] = {}

    for s in stories:
        story_info = {
            "story_id": s["story_id"],
            "event_name": s["event_name"] or "",
            "event_category": s["event_category"],
            "card_id": s["card_id"],
            "chara_id": s["card_chara_id"],
        }

        if s["card_id"] != 0:
            # Card-specific event
            cid = s["card_id"]
            if cid not in cards:
                cards[cid] = {"chara_id": s["card_chara_id"], "stories": []}
            cards[cid]["stories"].append(story_info)
        else:
            # Shared character event
            chara = s["card_chara_id"]
            if chara not in common_stories:
                common_stories[chara] = []
            common_stories[chara].append(story_info)

    conn.close()

    return {
        "cards": cards,
        "common_stories": common_stories,
        "card_chara_map": card_chara_map,
    }


# ── Meta DB ────────────────────────────────────────────────────────────


def _open_meta(meta_path: Path):
    """Open the meta database (plaintext first, then encrypted)."""
    try:
        c = sqlite3.connect(f"file:{meta_path}?mode=ro", uri=True)
        c.row_factory = sqlite3.Row
        tables = [
            r[0]
            for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        ]
        if "a" in tables:
            return c
        c.close()
    except Exception:
        pass

    # Fallback: try encrypted via extract_story_text helper
    try:
        from extract_story_text import _try_open_encrypted_meta

        conn = _try_open_encrypted_meta(meta_path)
        if conn:
            return conn
    except Exception as exc:
        log.debug("Encrypted meta open failed: %s", exc)

    return None


def read_story_meta_entries(game_dir: Path, story_ids: set[int]) -> dict[int, dict]:
    """
    Read meta DB entries for story bundles matching the given story_ids.

    Returns {story_id: {name, hash, key}} for found bundles.
    """
    meta_path = game_dir / "meta"
    if not meta_path.is_file():
        log.error("meta database not found at %s", meta_path)
        return {}

    conn = _open_meta(meta_path)
    if conn is None:
        log.error("Could not open meta database at %s", meta_path)
        return {}

    # Build a set of expected asset name patterns from story_ids
    # Story ID 501001510 → asset name "story/data/50/5010015/storytimeline_501001510"
    # Pattern: story/data/{first2}/{first7}/storytimeline_{full_id}
    story_name_map: dict[str, int] = {}
    for sid in story_ids:
        s = str(sid)
        if len(s) >= 7:
            prefix2 = s[:2]
            prefix7 = s[:7]
            name = f"story/data/{prefix2}/{prefix7}/storytimeline_{sid}"
            story_name_map[name] = sid

    results: dict[int, dict] = {}

    try:
        cols_info = conn.execute("PRAGMA table_info(a)").fetchall()
        cols = {r[1] for r in cols_info}
        has_key = "e" in cols

        if has_key:
            sql = "SELECT n, h, e FROM a WHERE n LIKE 'story/data/%storytimeline%' ORDER BY n"
        else:
            sql = "SELECT n, h FROM a WHERE n LIKE 'story/data/%storytimeline%' ORDER BY n"

        rows = conn.execute(sql).fetchall()
        for r in rows:
            name = r["n"]
            if name in story_name_map:
                sid = story_name_map[name]
                results[sid] = {
                    "name": name,
                    "hash": r["h"],
                    "key": r["e"] if has_key else 0,
                }
            else:
                # Try extracting story_id from the asset name
                m = re.search(r"storytimeline_(\d+)", name)
                if m:
                    extracted_sid = int(m.group(1))
                    if extracted_sid in story_ids:
                        results[extracted_sid] = {
                            "name": name,
                            "hash": r["h"],
                            "key": r["e"] if has_key else 0,
                        }
    except Exception as e:
        log.error("Failed querying meta: %s", e)
    finally:
        with contextlib.suppress(Exception):
            conn.close()

    return results


# ── Bundle extraction ──────────────────────────────────────────────────


def _get_ci(d: dict, *keys: str):
    """Case-insensitive dict get — tries each key variant."""
    for k in keys:
        if k in d:
            return d[k]
    dl = {k2.lower(): v for k2, v in d.items()}
    for k in keys:
        v = dl.get(k.lower())
        if v is not None:
            return v
    return None


def _is_gender_variant_pair(a: str, b: str) -> bool:
    """Check if two strings are trainer gender variants (male/female speech)."""
    if a == b:
        return True
    # Gender variants differ by 1-3 chars at most and share 80%+ of characters
    if abs(len(a) - len(b)) > 3:
        return False
    # Use SequenceMatcher ratio for fuzzy comparison
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a, b).ratio() > 0.7


def _dedupe_gender_variants(entries: list[dict]) -> list[dict]:
    """
    Remove trainer gender variant duplicates from choice entries.

    Gender variants come in pairs: male speech (だ/な/俺/ぞ) and
    female speech (の/ね/私/よ). Keep only one from each pair.
    """
    if len(entries) < 2:
        return entries

    # Try to detect if ALL entries are gender variant pairs
    # (even count, each consecutive pair is similar)
    if len(entries) % 2 == 0:
        all_pairs = True
        for i in range(0, len(entries), 2):
            if not _is_gender_variant_pair(entries[i]["text"], entries[i + 1]["text"]):
                all_pairs = False
                break
        if all_pairs:
            # These are gendered dialogue, not real choices — skip entirely
            return []

    # Otherwise, dedupe any individual pairs while keeping real choices
    result = []
    skip = set()
    for i, entry in enumerate(entries):
        if i in skip:
            continue
        # Check if next entry is a gender variant
        if i + 1 < len(entries) and _is_gender_variant_pair(entry["text"], entries[i + 1]["text"]):
            skip.add(i + 1)
        result.append(entry)

    return result


def _extract_choice_data(tree: dict, diag: bool = False) -> list[dict]:
    """
    Extract choice data from a StoryTimelineTextClipData MonoBehaviour.

    Real player choices have multiple entries in ChoiceDataList (2+ options).
    Single-entry lists are dialogue/narration text — skip those.
    Gender variant pairs (male/female trainer speech) are detected and removed.

    Returns list of {text, success_effects, failure_effects}
    """
    choice_list = _get_ci(tree, "ChoiceDataList", "choiceDataList")
    if not choice_list or not isinstance(choice_list, list):
        return []

    # Filter: single-entry ChoiceDataList is dialogue, not a real choice
    text_entries = [
        c for c in choice_list
        if isinstance(c, dict) and isinstance(_get_ci(c, "Text", "text", "Name", "name"), str)
        and (_get_ci(c, "Text", "text", "Name", "name") or "").strip()
    ]
    if len(text_entries) < 2:
        return []

    # Diagnostic: log first choice's keys to understand structure
    if diag and text_entries:
        c0 = text_entries[0]
        log.info("DIAG ChoiceDataList[0] keys: %s", list(c0.keys()))
        for k, v in c0.items():
            if isinstance(v, list) and v:
                log.info("DIAG   %s = list[%d], first=%s", k, len(v),
                         repr(v[0])[:200] if v else "empty")
            else:
                log.info("DIAG   %s = %s", k, repr(v)[:200])

    choices = []
    for choice in text_entries:
        text = _get_ci(choice, "Text", "text", "Name", "name")
        if not isinstance(text, str) or not text.strip():
            continue

        # Extract effects from all known field name variants
        success = []
        failure = []
        for eff_key, dest in [
            ("SuccessEffect", success),
            ("FailureEffect", failure),
            ("SuccessEffectList", success),
            ("FailureEffectList", failure),
            ("successEffect", success),
            ("failureEffect", failure),
        ]:
            eff_list = _get_ci(choice, eff_key)
            if not eff_list or not isinstance(eff_list, list):
                continue
            for eff in eff_list:
                if not isinstance(eff, dict):
                    continue
                st = _get_ci(eff, "StatusType", "statusType", "Type", "type")
                val = _get_ci(eff, "Value", "value")
                if isinstance(st, int) and isinstance(val, int) and st != 0:
                    dest.append((st, val))

        choices.append({
            "text": text.strip(),
            "success_effects": success,
            "failure_effects": failure,
        })

    # Remove gender variant pairs (male/female trainer dialogue)
    choices = _dedupe_gender_variants(choices)

    return choices


def _extract_from_bundle_worker(args: tuple) -> tuple[int, list[dict], str | None]:
    """
    Worker function for parallel bundle extraction.

    Args: (story_id, file_path_str, entry_key, diag)
    Returns: (story_id, choices, error_or_none)
    """
    story_id, file_path_str, entry_key = args[:3]
    diag = args[3] if len(args) > 3 else False
    file_path = Path(file_path_str)

    _init_xor()

    try:
        import UnityPy

        if entry_key != 0:
            data = decrypt_bundle(file_path, entry_key)
            env = UnityPy.load(data)
        else:
            env = UnityPy.load(str(file_path))
    except Exception as e:
        return (story_id, [], f"Failed to load bundle: {e}")

    all_choices: list[dict] = []
    diag_done = False

    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            tree = obj.read_typetree()
        except Exception:
            continue
        if not isinstance(tree, dict):
            continue

        # Diagnostic: dump structure of ANY object with ChoiceDataList
        if diag and not diag_done:
            cdl = _get_ci(tree, "ChoiceDataList", "choiceDataList")
            if cdl and isinstance(cdl, list) and len(cdl) > 0:
                diag_done = True
                log.info("DIAG story=%d obj keys: %s", story_id, list(tree.keys()))
                c0 = cdl[0]
                if isinstance(c0, dict):
                    log.info("DIAG ChoiceDataList[0] keys: %s", list(c0.keys()))
                    for k, v in c0.items():
                        if isinstance(v, list):
                            if v and isinstance(v[0], dict):
                                log.info("DIAG   %s = list[%d], item keys=%s",
                                         k, len(v), list(v[0].keys()))
                            else:
                                log.info("DIAG   %s = list[%d] %s",
                                         k, len(v), repr(v[:2])[:200])
                        else:
                            log.info("DIAG   %s = %s", k, repr(v)[:200])

        # Extract choices from TextClipData objects
        choices = _extract_choice_data(tree, diag=False)
        if choices:
            all_choices.extend(choices)

    # Deduplicate by text while preserving order
    seen = set()
    unique = []
    for c in all_choices:
        if c["text"] not in seen:
            seen.add(c["text"])
            unique.append(c)

    return (story_id, unique, None)


# ── Category classification ───────────────────────────────────────────

# Story ID patterns → event categories
# 50{charaId}0XX = lifecycle events (debut, new year, valentine, christmas, ending, etc.)
# 50{charaId}1XX = race-related stories
# 50{charaId}2XX = race-related (goals)
# 50{charaId}5XX = random/choice events
# 400XXXXXX = shared/special events

LIFECYCLE_EVENTS = {
    "新年": ("nyear", "New Year's Event"),
    "初詣": ("nyear", "New Year's Event"),
    "バレンタイン": ("wchoice", "Choice Event"),
    "クリスマス": ("wchoice", "Choice Event"),
    "ファン感謝祭": ("nochoice", "No-Choice Event"),
    "夏合宿": ("nochoice", "No-Choice Event"),
    "エンディング": ("nochoice", "No-Choice Event"),
    "温泉旅行": ("outings", "Outing Event"),
    "ダンスレッスン": ("dance", "Dance Lesson"),
}


def classify_event(
    story_id: int, event_name: str, has_choices: bool, event_category: int,
) -> tuple[str, str]:
    """
    Classify an event into category and type.

    event_category from masterdb:
        1 = lifecycle (fixed story events like debut, ending)
        2 = race/goal events
        3 = random events (choice events, no-choice, outings, dance, etc.)
    """
    sid_str = str(story_id)

    # Check lifecycle keywords
    for keyword, (cat, etype) in LIFECYCLE_EVENTS.items():
        if keyword in event_name:
            return (cat, etype)

    # Dance lessons
    if "ダンス" in event_name:
        return ("dance", "Dance Lesson")

    # Outings
    if "お出かけ" in event_name:
        return ("outings", "Outing Event")

    # Secret/version events (story_id starts with 40)
    if sid_str.startswith("40"):
        if has_choices:
            return ("wchoice", "Choice Event")
        return ("version", "Version Event")

    # event_category=3 are random training events — most are choice events
    if event_category == 3:
        return ("wchoice", "Choice Event")

    # Race events (category 2) and lifecycle (category 1)
    if event_category == 2:
        return ("nochoice", "No-Choice Event")

    if has_choices:
        return ("wchoice", "Choice Event")

    return ("nochoice", "No-Choice Event")


# ── Main pipeline ─────────────────────────────────────────────────────


def build_character_events(
    masterdb_path: Path,
    game_dir: Path | None = None,
    card_ids: list[int] | None = None,
    workers: int = 0,
    existing_data_path: Path | None = None,
) -> list[dict]:
    """
    Build the character events data structure.

    Args:
        masterdb_path: Path to JP master.mdb
        game_dir: Path to game root (with dat/ and meta). None = masterdb-only mode.
        card_ids: Optional filter for specific card IDs. None = all cards.
        workers: Number of parallel workers. 0 = auto.
        existing_data_path: Path to existing character_events_clean.json to merge with.

    Returns list compatible with character_events_clean.json format.
    """
    t0 = time.time()

    # Load existing data for merging
    existing: dict[int, dict] = {}
    if existing_data_path and existing_data_path.is_file():
        try:
            with open(existing_data_path) as f:
                for entry in json.load(f):
                    existing[entry["card_id"]] = entry
            log.info("Loaded %d existing umas from %s", len(existing), existing_data_path.name)
        except Exception as e:
            log.warning("Failed to load existing data: %s", e)

    # Step 1: Query masterdb
    log.info("Querying master database...")
    db_data = query_masterdb(masterdb_path, card_ids)
    cards = db_data["cards"]
    common_stories = db_data["common_stories"]
    card_chara_map = db_data["card_chara_map"]

    all_target_cards = set(cards.keys())
    if card_ids:
        all_target_cards &= set(card_ids)

    log.info(
        "Found %d character variants, %d characters with shared events",
        len(all_target_cards),
        len(common_stories),
    )

    # Collect all story_ids we need to extract
    all_story_ids: set[int] = set()
    for cid in all_target_cards:
        if cid in cards:
            for s in cards[cid]["stories"]:
                all_story_ids.add(s["story_id"])
    for chara_id in {card_chara_map.get(c, 0) for c in all_target_cards}:
        if chara_id in common_stories:
            for s in common_stories[chara_id]:
                all_story_ids.add(s["story_id"])

    log.info("Total unique story_ids to process: %d", len(all_story_ids))

    # Step 2: Extract from assets (if game_dir provided)
    story_choices: dict[int, list[dict]] = {}  # story_id → choices with effects

    if game_dir:
        log.info("Reading meta database for story bundles...")
        meta_entries = read_story_meta_entries(game_dir, all_story_ids)
        log.info("Found %d/%d story bundles in meta", len(meta_entries), len(all_story_ids))

        dat_dir = game_dir / "dat"
        work_items = []
        first = True
        for sid, entry in meta_entries.items():
            h = entry["hash"]
            file_path = dat_dir / h[:2] / h
            if file_path.is_file():
                work_items.append((sid, str(file_path), entry["key"], first))
                first = False

        log.info("Extracting choices from %d bundles...", len(work_items))

        if workers == 0:
            workers = min(os.cpu_count() or 4, 8)

        # Run first bundle sequentially in main process for diagnostic logging
        if work_items:
            first_args = work_items[0]
            sid, choices, err = _extract_from_bundle_worker(first_args)
            if err:
                log.debug("Error extracting %d: %s", sid, err)
            if choices:
                story_choices[sid] = choices
            work_items = work_items[1:]

        if len(work_items) <= 10 or workers == 1:
            # Sequential for small batches
            for args in work_items:
                sid, choices, err = _extract_from_bundle_worker(args)
                if err:
                    log.debug("Error extracting %d: %s", sid, err)
                if choices:
                    story_choices[sid] = choices
        else:
            log.info("Using %d worker processes", workers)
            with ProcessPoolExecutor(max_workers=workers) as executor:
                futures = {
                    executor.submit(_extract_from_bundle_worker, args): args[0]
                    for args in work_items
                }
                for done, future in enumerate(as_completed(futures), 1):
                    sid = futures[future]
                    try:
                        _, choices, err = future.result()
                        if err:
                            log.debug("Error extracting %d: %s", sid, err)
                        if choices:
                            story_choices[sid] = choices
                    except Exception as e:
                        log.debug("Worker exception for %d: %s", sid, e)
                    if done % 100 == 0:
                        log.info("  Progress: %d/%d bundles", done, len(work_items))

        log.info("Extracted choices from %d stories", len(story_choices))

    # Step 3: Build the output structure
    log.info("Building event data...")
    result: list[dict] = []

    for card_id in sorted(all_target_cards):
        chara_id = card_chara_map.get(card_id, card_id // 100)

        # Collect all stories for this card: shared + card-specific
        all_stories = []
        if chara_id in common_stories:
            all_stories.extend(common_stories[chara_id])
        if card_id in cards:
            all_stories.extend(cards[card_id]["stories"])

        # Deduplicate by story_id (card-specific takes priority)
        seen_stories: dict[int, dict] = {}
        for s in all_stories:
            sid = s["story_id"]
            if sid not in seen_stories or s["card_id"] != 0:
                seen_stories[sid] = s

        events = []
        choice_event_order = 0

        for story in sorted(seen_stories.values(), key=lambda x: x["story_id"]):
            sid = story["story_id"]
            event_name_jp = story["event_name"]
            choices = story_choices.get(sid, [])
            has_choices = len(choices) > 0
            category, event_type = classify_event(
                sid, event_name_jp, has_choices, story["event_category"]
            )

            # Build options from extracted choices
            options = []
            for choice in choices:
                outcomes = []

                # Format success effects
                success_parts = []
                for st, val in choice.get("success_effects", []):
                    formatted = format_effect(st, val)
                    if formatted:
                        success_parts.append(formatted)
                if success_parts:
                    outcomes.append("\n".join(success_parts))

                # Format failure effects (separate outcome)
                failure_parts = []
                for st, val in choice.get("failure_effects", []):
                    formatted = format_effect(st, val)
                    if formatted:
                        failure_parts.append(formatted)
                if failure_parts:
                    outcomes.append("\n".join(failure_parts))

                # If no effects extracted, add empty outcome
                if not outcomes:
                    outcomes = [""]

                options.append({
                    "option_name": choice["text"],
                    "outcomes": outcomes,
                    "option_name_jp": choice["text"],
                })

            # Skip no-choice and lifecycle events that add no value
            if category in ("nochoice",) and not options:
                continue

            event_entry = {
                "event_name": event_name_jp,  # Will be JP text (no translation available)
                "event_name_jp": event_name_jp,
                "event_type": event_type,
                "category": category,
                "event_order": choice_event_order if category == "wchoice" else 0,
                "options": options,
            }
            events.append(event_entry)
            if category == "wchoice":
                choice_event_order += 1

        # Try to get card title and chara name from existing data or leave as JP
        card_title = ""
        chara_name = ""
        if card_id in existing:
            card_title = existing[card_id].get("card_title", "")
            chara_name = existing[card_id].get("chara_name", "")

        if events:
            result.append({
                "card_id": card_id,
                "card_title": card_title,
                "chara_name": chara_name,
                "chara_id": chara_id,
                "events": events,
            })

    elapsed = time.time() - t0
    log.info(
        "Built event data for %d character variants in %.1fs (%d with asset choices)",
        len(result),
        elapsed,
        sum(1 for r in result if any(e["options"] for e in r["events"])),
    )

    return result


# ── CLI ────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Extract character event data from Uma Musume game assets.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "game_dir",
        nargs="?",
        type=Path,
        help="Path to game root directory (with dat/ and meta). "
        "Omit for masterdb-only mode.",
    )
    parser.add_argument(
        "--masterdb",
        type=Path,
        default=APP_DIR / "dump-jp" / "master.mdb",
        help="Path to JP master.mdb (default: dump-jp/master.mdb)",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=APP_DIR / "character_events.json",
        help="Output file path (default: character_events.json)",
    )
    parser.add_argument(
        "--cards",
        type=str,
        default=None,
        help="Comma-separated list of card IDs to extract (default: all)",
    )
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=0,
        help="Number of parallel workers (default: auto)",
    )
    parser.add_argument(
        "--existing",
        type=Path,
        default=None,
        help="Path to existing character_events_clean.json to merge card titles/names from",
    )
    parser.add_argument(
        "--masterdb-only",
        action="store_true",
        help="Only extract from masterdb (no asset bundles). "
        "Produces events with names but no choice text/effects.",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")

    # Log to both console and file
    log.setLevel(level)
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(fmt)
    log.addHandler(console)

    log_file = APP_DIR / "extract_events.log"
    fh = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    fh.setLevel(logging.DEBUG)  # always capture full detail in file
    fh.setFormatter(fmt)
    log.addHandler(fh)
    log.info("Logging to %s", log_file)

    if not args.masterdb.is_file():
        log.error("Master database not found: %s", args.masterdb)
        sys.exit(1)

    game_dir = None
    if args.game_dir:
        game_dir = args.game_dir
        if not (game_dir / "dat").is_dir() or not (game_dir / "meta").is_file():
            log.error("Invalid game directory: %s (needs dat/ and meta)", game_dir)
            sys.exit(1)
    elif not args.masterdb_only:
        log.warning("No game directory specified. Use --masterdb-only for masterdb-only mode.")
        log.warning("Running in masterdb-only mode (no choice text/effects from assets).")

    card_ids = None
    if args.cards:
        card_ids = [int(c.strip()) for c in args.cards.split(",")]

    result = build_character_events(
        masterdb_path=args.masterdb,
        game_dir=game_dir,
        card_ids=card_ids,
        workers=args.workers,
        existing_data_path=args.existing,
    )

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    log.info("Wrote %d character variants to %s", len(result), args.output)


if __name__ == "__main__":
    main()
