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


# ── Meta database decryption keys (from UmaViewer Config.cs) ───────────

# DB encryption key — JP (XOR'd with DBBaseKey to produce the final key)
DB_KEY = bytes(
    [
        0x6D,
        0x5B,
        0x65,
        0x33,
        0x63,
        0x36,
        0x63,
        0x25,
        0x54,
        0x71,
        0x2D,
        0x73,
        0x50,
        0x53,
        0x63,
        0x38,
        0x6D,
        0x34,
        0x37,
        0x7B,
        0x35,
        0x63,
        0x70,
        0x23,
        0x37,
        0x34,
        0x53,
        0x29,
        0x73,
        0x43,
        0x36,
        0x33,
    ]
)

# DB encryption key — Global (from UmaViewer Config.cs GlobalDBKey)
GLOBAL_DB_KEY = bytes(
    [
        0x56,
        0x63,
        0x6B,
        0x63,
        0x42,
        0x72,
        0x37,
        0x76,
        0x65,
        0x70,
        0x41,
        0x62,
    ]
)

DB_BASE_KEY = bytes(
    [
        0xF1,
        0x70,
        0xCE,
        0xA4,
        0xDF,
        0xCE,
        0xA3,
        0xE1,
        0xA5,
        0xD8,
        0xC7,
        0x0B,
        0xD1,
        0x00,
        0x00,
        0x00,
    ]
)


def _derive_db_key(db_key: bytes = DB_KEY) -> bytes:
    """Derive the final decryption key: db_key XOR DBBaseKey (cycling 13 bytes)."""
    key = bytearray(db_key)
    for i in range(len(key)):
        key[i] ^= DB_BASE_KEY[i % 13]
    return bytes(key)


def _try_open_encrypted_meta(meta_path: Path) -> sqlite3.Connection | None:
    """
    Try to open an encrypted meta database.

    Tries the Global key first (most users), then JP key as fallback.
    For each key, attempts:
      1. pysqlcipher3 (if installed) — pure Python SQLCipher binding
      2. sqlcipher3 (alternative package name)
      3. sqlite3mc DLL via ctypes on Windows (same as UmaViewer)

    On success, returns a sqlite3.Connection to a decrypted in-memory or temp copy.
    """
    keys_to_try = [
        ("Global", _derive_db_key(GLOBAL_DB_KEY)),
        ("JP", _derive_db_key(DB_KEY)),
    ]

    for region, key in keys_to_try:
        key_hex = key.hex()
        log.debug("Trying %s key for meta decryption...", region)

        # ── Strategy 1: try pysqlcipher3 ──────────────────────────
        try:
            from pysqlcipher3 import dbapi2 as sqlcipher  # type: ignore

            conn = sqlcipher.connect(str(meta_path))
            conn.execute(f"PRAGMA key = \"x'{key_hex}'\"")
            conn.execute("PRAGMA cipher_compatibility = 3")
            # Test if it works
            conn.execute("SELECT name FROM sqlite_master LIMIT 1")
            conn.row_factory = sqlite3.Row
            log.info("Opened encrypted meta via pysqlcipher3 (%s key)", region)
            return conn
        except ImportError:
            log.debug("pysqlcipher3 not available")
        except Exception as e:
            log.debug("pysqlcipher3 failed with %s key: %s", region, e)

        # ── Strategy 2: try sqlcipher3 (alternative package name) ─
        try:
            import sqlcipher3  # type: ignore

            conn = sqlcipher3.connect(str(meta_path))
            conn.execute(f"PRAGMA key = \"x'{key_hex}'\"")
            conn.execute("PRAGMA cipher_compatibility = 3")
            conn.execute("SELECT name FROM sqlite_master LIMIT 1")
            conn.row_factory = sqlite3.Row
            log.info("Opened encrypted meta via sqlcipher3 (%s key)", region)
            return conn
        except ImportError:
            log.debug("sqlcipher3 not available")
        except Exception as e:
            log.debug("sqlcipher3 failed with %s key: %s", region, e)

        # ── Strategy 3: try sqlite3mc via ctypes (Windows) ────────
        if sys.platform == "win32":
            conn = _try_decrypt_via_sqlite3mc(meta_path, key)
            if conn:
                log.info("Decrypted meta via sqlite3mc (%s key)", region)
                return conn

    return None


def _try_decrypt_via_sqlite3mc(meta_path: Path, key: bytes) -> sqlite3.Connection | None:
    """
    Use sqlite3mc DLL via ctypes to decrypt the meta DB to a plaintext copy.
    Creates meta_decrypted next to the original.
    """
    import ctypes

    # Search for the DLL in multiple locations.
    # For a PyInstaller --onedir build the layout is:
    #   dist/Clairvoyance/Clairvoyance.exe
    #   dist/Clairvoyance/sqlite3mc_x64.dll      ← next to exe (APP_DIR)
    #   dist/Clairvoyance/_internal/              ← sys._MEIPASS
    #   dist/Clairvoyance/_internal/sqlite3mc_x64.dll  ← bundled via --add-binary
    _meipass = Path(sys._MEIPASS) if _FROZEN and hasattr(sys, "_MEIPASS") else None
    _exe_dir = Path(sys.executable).resolve().parent if _FROZEN else None

    search_dirs = [
        APP_DIR,  # next to script / exe
        _exe_dir,  # exe's own directory (frozen)
        _meipass,  # PyInstaller _MEIPASS (onedir → _internal/)
        APP_DIR / "_internal",  # explicit _internal/ fallback
    ]
    dll_names = ["sqlite3mc_x64.dll", "sqlite3mc.dll"]

    log.debug("sqlite3mc DLL search dirs: %s", [str(d) for d in search_dirs if d])

    dll = None
    for d in search_dirs:
        if d is None or not d.is_dir():
            continue
        for name in dll_names:
            candidate = d / name
            if candidate.is_file():
                try:
                    dll = ctypes.CDLL(str(candidate))
                    log.info("Loaded %s from %s", name, d)
                    break
                except OSError:
                    continue
        if dll:
            break

    # Also try bare name (system PATH)
    if dll is None:
        for name in ["sqlite3mc_x64", "sqlite3mc_x64.dll", "sqlite3mc"]:
            try:
                dll = ctypes.CDLL(name)
                log.info("Loaded %s from system PATH", name)
                break
            except OSError:
                continue

    if dll is None:
        log.debug("sqlite3mc DLL not found — cannot decrypt meta natively")
        return None

    try:
        log.info("Decrypting meta via sqlite3mc DLL...")

        # ── Declare function signatures (critical on 64-bit Windows) ──
        # Without these, ctypes assumes c_int returns, truncating 64-bit
        # pointers and causing access violations.
        _vp = ctypes.c_void_p
        _cp = ctypes.c_char_p
        _ci = ctypes.c_int
        _pp = ctypes.POINTER(ctypes.c_void_p)

        dll.sqlite3_open_v2.argtypes = [_cp, _pp, _ci, _cp]
        dll.sqlite3_open_v2.restype = _ci

        dll.sqlite3mc_config.argtypes = [_vp, _cp, _ci]
        dll.sqlite3mc_config.restype = _ci

        dll.sqlite3_exec.argtypes = [_vp, _cp, _vp, _vp, _pp]
        dll.sqlite3_exec.restype = _ci

        dll.sqlite3_errmsg.argtypes = [_vp]
        dll.sqlite3_errmsg.restype = _cp

        dll.sqlite3_backup_init.argtypes = [_vp, _cp, _vp, _cp]
        dll.sqlite3_backup_init.restype = _vp

        dll.sqlite3_backup_step.argtypes = [_vp, _ci]
        dll.sqlite3_backup_step.restype = _ci

        dll.sqlite3_backup_finish.argtypes = [_vp]
        dll.sqlite3_backup_finish.restype = _ci

        dll.sqlite3_close.argtypes = [_vp]
        dll.sqlite3_close.restype = _ci

        def _errmsg(db: ctypes.c_void_p) -> str:
            msg = dll.sqlite3_errmsg(db)
            return msg.decode("utf-8", errors="replace") if msg else "(null)"

        # ── Open encrypted DB and try cipher IDs ────────────────────
        # sqlite3mc cipher IDs (from sqlite3mc documentation):
        #   1 = AES-128 (wxSQLite3)
        #   2 = AES-256 (wxSQLite3)
        #   3 = ChaCha20 (sqleet) — also used by sqlite3mc for RC4
        #   4 = SQLCipher AES-256
        #   5 = RC4 (System.Data.SQLite) in newer sqlite3mc builds
        # UmaViewer uses cipher index 3 (see UmaDatabaseController.cs L91).
        # Try 3 first, then 5 and 4 as fallbacks.
        SQLITE_OPEN_READWRITE = 0x00000002
        SQLITE_OPEN_CREATE = 0x00000004
        _CIPHER_IDS = [3, 5, 4]

        # sqlite3_key: set key as raw bytes (matching UmaViewer Sqlite3MC.Key_SetBytes)
        dll.sqlite3_key.argtypes = [_vp, ctypes.c_char_p, _ci]
        dll.sqlite3_key.restype = _ci

        validated_db_ptr = None
        for cipher_id in _CIPHER_IDS:
            db_ptr = ctypes.c_void_p()
            rc = dll.sqlite3_open_v2(
                str(meta_path).encode("utf-8"),
                ctypes.byref(db_ptr),
                SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE,
                None,
            )
            if rc != 0:
                log.error("sqlite3mc open failed rc=%d errmsg=%s", rc, _errmsg(db_ptr))
                continue
            log.debug("sqlite3_open_v2 OK, db_ptr=%s", db_ptr.value)

            # Set cipher (before any DB access, matching UmaViewer)
            rc = dll.sqlite3mc_config(db_ptr, b"cipher", cipher_id)
            log.debug("sqlite3mc_config('cipher', %d) rc=%d", cipher_id, rc)

            # Set key as raw bytes via sqlite3_key (matches UmaViewer's
            # Sqlite3MC.Key_SetBytes which calls sqlite3_key(db, pKey, nKey)).
            rc = dll.sqlite3_key(db_ptr, key, len(key))
            log.debug("sqlite3_key(raw %d bytes) rc=%d", len(key), rc)
            if rc != 0:
                log.debug(
                    "sqlite3_key failed for cipher %d rc=%d errmsg=%s",
                    cipher_id,
                    rc,
                    _errmsg(db_ptr),
                )
                dll.sqlite3_close(db_ptr)
                continue

            # Validate: try a read to confirm key+cipher works
            err_ptr = ctypes.c_void_p()
            rc = dll.sqlite3_exec(
                db_ptr,
                b"SELECT name FROM sqlite_master LIMIT 1;",
                None,
                None,
                ctypes.byref(err_ptr),
            )
            if rc != 0:
                log.debug(
                    "sqlite3mc validation failed for cipher %d rc=%d errmsg=%s",
                    cipher_id,
                    rc,
                    _errmsg(db_ptr),
                )
                dll.sqlite3_close(db_ptr)
                continue

            log.info("Validation OK — cipher=%d key=%d bytes", cipher_id, len(key))
            validated_db_ptr = db_ptr
            break

        if validated_db_ptr is None:
            log.error("sqlite3mc: no cipher ID worked (tried %s)", _CIPHER_IDS)
            return None
        db_ptr = validated_db_ptr

        # ── Create plaintext copy via backup API ─────────────────────
        decrypted_path = meta_path.parent / "meta_decrypted"
        # Remove stale file from a previous run so backup starts fresh
        if decrypted_path.exists():
            decrypted_path.unlink()
        dest_ptr = ctypes.c_void_p()
        rc = dll.sqlite3_open_v2(
            str(decrypted_path).encode("utf-8"),
            ctypes.byref(dest_ptr),
            SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE,
            None,
        )
        if rc != 0:
            log.error("sqlite3mc open dest failed rc=%d errmsg=%s", rc, _errmsg(dest_ptr))
            dll.sqlite3_close(db_ptr)
            return None

        backup = dll.sqlite3_backup_init(dest_ptr, b"main", db_ptr, b"main")
        if not backup:
            log.error("sqlite3_backup_init failed errmsg=%s", _errmsg(dest_ptr))
            dll.sqlite3_close(dest_ptr)
            dll.sqlite3_close(db_ptr)
            return None

        SQLITE_OK = 0
        SQLITE_DONE = 101
        while True:
            rc = dll.sqlite3_backup_step(backup, 5)
            if rc == SQLITE_DONE:
                break
            if rc != SQLITE_OK:
                log.error("sqlite3_backup_step failed rc=%d", rc)
                break

        dll.sqlite3_backup_finish(backup)
        dll.sqlite3_close(dest_ptr)
        dll.sqlite3_close(db_ptr)

        log.info("Decrypted meta -> %s", decrypted_path)

        # Open the decrypted copy with standard sqlite3
        conn = sqlite3.connect(f"file:{decrypted_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        conn.execute("SELECT name FROM sqlite_master LIMIT 1")
        return conn

    except Exception as e:
        log.error("sqlite3mc decryption failed: %s", e)
        return None


# ── Meta database reading ──────────────────────────────────────────────


def read_meta_entries(game_dir: Path) -> list[dict]:
    """
    Read story data entries from the meta database.

    Returns list of {name, hash, key} dicts for story timeline assets.

    The game's meta file is encrypted (sqlite3mc RC4). We try:
      1. meta opened as plain SQLite (works if already decrypted)
      2. meta decrypted on-the-fly using the known game key
    """
    meta_path = game_dir / "meta"
    conn = None

    if not meta_path.is_file():
        log.error("meta database not found at %s", meta_path)
        return []

    # ── Try 1: plain (unencrypted or already-decrypted) meta ──
    try:
        c = sqlite3.connect(f"file:{meta_path}?mode=ro", uri=True)
        c.row_factory = sqlite3.Row
        tables = [
            r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        ]
        if "a" in tables:
            log.info("Using plain meta: %s", meta_path)
            conn = c
        else:
            c.close()
            log.info(
                "meta file exists but appears encrypted (0 tables visible). "
                "Attempting decryption..."
            )
    except Exception as e:
        log.info("meta plain open failed (%s) — attempting decryption...", e)

    # ── Try 2: decrypt the encrypted meta ─────────────────────
    if conn is None:
        conn = _try_open_encrypted_meta(meta_path)
        if conn is None:
            log.error(
                "Could not decrypt meta database at %s.\n"
                "The meta file is encrypted (sqlite3mc RC4 cipher).\n"
                "To fix this, either:\n"
                "  • Place sqlite3mc_x64.dll next to this program (Windows)\n"
                "  • Install pysqlcipher3: pip install pysqlcipher3",
                meta_path,
            )
            return []

    # ── Read entries from the opened connection ───────────────
    entries = []
    try:
        cols_info = conn.execute("PRAGMA table_info(a)").fetchall()
        col_names = [r[1] for r in cols_info]
        cols = set(col_names)
        log.info("Meta DB table 'a' columns: %s", col_names)

        if "n" not in cols or "h" not in cols:
            log.error("Table 'a' missing required columns 'n'/'h'. Found: %s", col_names)
            conn.close()
            return []

        has_key = "e" in cols

        total_rows = conn.execute("SELECT COUNT(*) FROM a").fetchone()[0]
        log.info("Table 'a' has %d total rows", total_rows)

        # Query for actual story timeline bundles.
        # Exclude 'resourcelist' entries — those are dependency manifests,
        # not the actual story data bundles with TextAsset JSON.
        if has_key:
            sql = (
                "SELECT n, h, e FROM a "
                "WHERE n LIKE 'story/data/%storytimeline%' "
                "AND n NOT LIKE '%resourcelist%'"
            )
            sql_reslist = (
                "SELECT COUNT(*) FROM a "
                "WHERE n LIKE 'story/data/%storytimeline%' "
                "AND n LIKE '%resourcelist%'"
            )
        else:
            sql = (
                "SELECT n, h FROM a "
                "WHERE n LIKE 'story/data/%storytimeline%' "
                "AND n NOT LIKE '%resourcelist%'"
            )
            sql_reslist = (
                "SELECT COUNT(*) FROM a "
                "WHERE n LIKE 'story/data/%storytimeline%' "
                "AND n LIKE '%resourcelist%'"
            )

        reslist_count = conn.execute(sql_reslist).fetchone()[0]
        rows = conn.execute(sql).fetchall()
        for r in rows:
            entries.append(
                {
                    "name": r["n"],
                    "hash": r["h"],
                    "key": r["e"] if has_key else 0,
                }
            )
        log.info(
            "Found %d story timeline data entries (%d resourcelist entries excluded)",
            len(entries),
            reslist_count,
        )

        if entries:
            sample = entries[0]
            log.info("  Sample: name=%s hash=%s", sample["name"], sample["hash"])

    except Exception as e:
        log.error("Failed to query meta database: %s", e)
    finally:
        with contextlib.suppress(Exception):
            conn.close()

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


_block_keys_logged = False


def _get_ci(d: dict, *candidates: str):
    """Case-insensitive dict lookup.  Try exact candidates first, then lowercase match."""
    for k in candidates:
        if k in d:
            return d[k]
    lower_map = {k2.lower(): k2 for k2 in d}
    for k in candidates:
        real = lower_map.get(k.lower())
        if real is not None:
            return d[real]
    return None


def _extract_choices_from_dict(data: dict) -> list[str]:
    """
    Extract choice text labels from a story data dict.

    Works on both parsed JSON and MonoBehaviour typetree dicts.
    The dict has a BlockList array. Blocks with ChoiceDataList
    contain the player's choice options.

    Handles both PascalCase (API JSON) and whatever casing the Unity
    typetree uses, via case-insensitive key lookup.
    """
    global _block_keys_logged
    choices: list[str] = []
    block_list = data.get("BlockList", [])
    if not isinstance(block_list, list):
        return choices

    # One-shot diagnostic: log the first block's keys so we can see the real field names.
    if not _block_keys_logged and block_list:
        _block_keys_logged = True
        b0 = block_list[0]
        if isinstance(b0, dict):
            log.info(
                "DIAGNOSTIC: first block keys = %s",
                list(b0.keys()),
            )
            # Also log any key whose name contains "choice" or "select" (case-insensitive)
            for k, v in b0.items():
                kl = k.lower()
                if "choice" in kl or "select" in kl or "option" in kl:
                    sample = repr(v)[:300] if not isinstance(v, list) else f"list[{len(v)}]"
                    log.info("DIAGNOSTIC: block[0]['%s'] = %s", k, sample)
            # Log keys of all blocks that have any choice-like list with items
            for bi, blk in enumerate(block_list):
                if not isinstance(blk, dict):
                    continue
                for k, v in blk.items():
                    if isinstance(v, list) and len(v) > 0:
                        kl = k.lower()
                        if "choice" in kl or "select" in kl or "option" in kl:
                            item0 = v[0]
                            item_info = (
                                list(item0.keys()) if isinstance(item0, dict) else repr(item0)[:200]
                            )
                            log.info(
                                "DIAGNOSTIC: block[%d]['%s'] has %d items, first item keys=%s",
                                bi,
                                k,
                                len(v),
                                item_info,
                            )
                            break  # one example is enough
        else:
            log.info("DIAGNOSTIC: first block is type %s, not dict", type(b0).__name__)

    for block in block_list:
        if not isinstance(block, dict):
            continue
        # Case-insensitive lookup for the choice list
        choice_data_list = _get_ci(
            block,
            "ChoiceDataList",
            "choiceDataList",
            "ChoiceDatalist",
            "SelectDataList",
            "selectDataList",
        )
        if not choice_data_list or not isinstance(choice_data_list, list):
            continue
        for choice in choice_data_list:
            if isinstance(choice, str):
                # Maybe the list directly contains strings
                t = choice.strip()
                if t:
                    choices.append(t)
                continue
            if not isinstance(choice, dict):
                continue
            text = _get_ci(choice, "Text", "text", "Name", "name", "Label", "label")
            if isinstance(text, str):
                text = text.strip()
                if text:
                    choices.append(text)
    return choices


def parse_story_choices(json_text: str) -> list[str]:
    """
    Parse a StoryData JSON and extract choice text labels.

    The StoryData has a BlockList array. Blocks with ChoiceDataList
    contain the player's choice options.
    """
    try:
        data = json.loads(json_text)
    except (json.JSONDecodeError, ValueError):
        return []
    if not isinstance(data, dict):
        return []
    return _extract_choices_from_dict(data)


def extract_choices_from_bundle(file_path: Path, entry_key: int = 0) -> dict[int, list[str]]:
    """
    Load an asset bundle and extract story choice text.

    The game's story timeline bundles contain multiple MonoBehaviour objects:
    - One StoryTimelineData object with BlockList (gives us StoryId)
    - Many StoryTimelineTextClipData objects (ScriptableObject-derived clips),
      some of which have a non-empty ChoiceDataList with the player's choice text.

    ChoiceDataList is NOT nested inside BlockList blocks -- clips are stored as
    separate serialized objects (Unity PPtr references from block→track→clip).
    So we scan ALL MonoBehaviours and collect choices from clip objects.

    Returns {story_id: [choice_texts]} for all stories found in the bundle.
    """
    global _block_keys_logged
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

    mono_count = 0
    story_id: int | None = None
    all_choices: list[str] = []

    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        mono_count += 1
        try:
            tree = obj.read_typetree()
        except Exception:
            continue
        if not isinstance(tree, dict):
            continue

        # ── Look for StoryTimelineData (has BlockList) → get StoryId ──
        if "BlockList" in tree:
            if not story_id:
                raw_sid = tree.get("StoryId")
                if isinstance(raw_sid, int) and raw_sid > 0:
                    story_id = raw_sid
                if not story_id:
                    m_name = tree.get("m_Name", "")
                    if isinstance(m_name, str):
                        m = re.search(r"storytimeline_?(\d+)", m_name)
                        if m:
                            story_id = int(m.group(1))
                if not story_id:
                    title = tree.get("Title", "")
                    if isinstance(title, str):
                        m = re.search(r"(\d{6,})", title)
                        if m:
                            story_id = int(m.group(1))

            # One-shot: log the first block's keys for diagnostic
            if not _block_keys_logged:
                _block_keys_logged = True
                bl = tree["BlockList"]
                if isinstance(bl, list) and bl:
                    b0 = bl[0]
                    if isinstance(b0, dict):
                        log.info("DIAG block[0] keys: %s", list(b0.keys()))
                        # Show TextTrack.ClipList if present (should be PPtrs)
                        tt = b0.get("TextTrack")
                        if isinstance(tt, dict):
                            log.info("DIAG block[0].TextTrack keys: %s", list(tt.keys()))
                            cl = tt.get("ClipList")
                            if isinstance(cl, list) and cl:
                                log.info("DIAG block[0].TextTrack.ClipList[0]: %s", cl[0])

        # ── Look for StoryTimelineTextClipData (has ChoiceDataList) ──
        choice_list = _get_ci(
            tree,
            "ChoiceDataList",
            "choiceDataList",
        )
        if choice_list and isinstance(choice_list, list):
            for choice in choice_list:
                if isinstance(choice, str):
                    t = choice.strip()
                    if t:
                        all_choices.append(t)
                elif isinstance(choice, dict):
                    text = _get_ci(choice, "Text", "text", "Name", "name")
                    if isinstance(text, str):
                        t = text.strip()
                        if t:
                            all_choices.append(t)

    # Also try to get story_id from the meta entry name (fallback)
    if not story_id:
        sid = extract_story_id_from_name(str(file_path))
        if sid:
            story_id = sid

    if story_id and all_choices:
        results[story_id] = all_choices

    if mono_count > 0 and log.isEnabledFor(logging.DEBUG):
        log.debug(
            "  bundle %s: %d MonoBehaviour, story_id=%s, %d choices",
            file_path.name[:16],
            mono_count,
            story_id,
            len(all_choices),
        )
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
    meta_exists = (game_dir / "meta").is_file()
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
