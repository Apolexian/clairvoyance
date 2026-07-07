#!/usr/bin/env python3
"""
Mark JP home timeline bundles for download by setting g=0 in the encrypted meta DB.
The game will download them on next launch.

Usage:
    python mark_home_convos_for_download.py
"""
import ctypes
import logging
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from extract_story_text import DB_KEY, GLOBAL_DB_KEY, DB_BASE_KEY, APP_DIR

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

JP_GAME_DIR = Path("C:/Program Files (x86)/Steam/steamapps/common/UmamusumePrettyDerby_Jpn/UmamusumePrettyDerby_Jpn_Data/Persistent")
META_PATH = JP_GAME_DIR / "meta"

SQL_COUNT = b"""
    SELECT COUNT(*) FROM a
    WHERE n LIKE 'home/data%hometimeline%'
    AND n NOT LIKE '%resourcelist%'
    AND n NOT LIKE '%ast_%'
    AND g != 0
"""

SQL_UPDATE = b"""
    UPDATE a SET g = 0
    WHERE n LIKE 'home/data%hometimeline%'
    AND n NOT LIKE '%resourcelist%'
    AND n NOT LIKE '%ast_%'
    AND g != 0
"""


def _derive_db_key(db_key: bytes) -> bytes:
    key = bytearray(db_key)
    for i in range(len(key)):
        key[i] ^= DB_BASE_KEY[i % 13]
    return bytes(key)


def main():
    if not META_PATH.is_file():
        log.error("meta not found at %s", META_PATH)
        sys.exit(1)

    # Find sqlite3mc DLL
    search_dirs = [APP_DIR, APP_DIR / "_internal"]
    dll = None
    for d in search_dirs:
        if not d or not d.is_dir():
            continue
        for name in ["sqlite3mc_x64.dll", "sqlite3mc.dll"]:
            c = d / name
            if c.is_file():
                try:
                    dll = ctypes.CDLL(str(c))
                    log.info("Loaded %s", c)
                    break
                except OSError:
                    continue
        if dll:
            break
    if dll is None:
        for name in ["sqlite3mc_x64", "sqlite3mc_x64.dll", "sqlite3mc"]:
            try:
                dll = ctypes.CDLL(name)
                break
            except OSError:
                continue
    if dll is None:
        log.error("sqlite3mc DLL not found")
        sys.exit(1)

    _vp = ctypes.c_void_p
    _cp = ctypes.c_char_p
    _ci = ctypes.c_int
    _pp = ctypes.POINTER(ctypes.c_void_p)

    dll.sqlite3_open_v2.argtypes = [_cp, _pp, _ci, _cp]
    dll.sqlite3_open_v2.restype = _ci
    dll.sqlite3mc_config.argtypes = [_vp, _cp, _ci]
    dll.sqlite3mc_config.restype = _ci
    dll.sqlite3_key.argtypes = [_vp, _cp, _ci]
    dll.sqlite3_key.restype = _ci
    dll.sqlite3_exec.argtypes = [_vp, _cp, _vp, _vp, _pp]
    dll.sqlite3_exec.restype = _ci
    dll.sqlite3_errmsg.argtypes = [_vp]
    dll.sqlite3_errmsg.restype = _cp
    dll.sqlite3_changes.argtypes = [_vp]
    dll.sqlite3_changes.restype = _ci
    dll.sqlite3_close.argtypes = [_vp]
    dll.sqlite3_close.restype = _ci

    SQLITE_OPEN_READWRITE = 0x00000002
    keys_to_try = [("JP", _derive_db_key(DB_KEY)), ("Global", _derive_db_key(GLOBAL_DB_KEY))]

    # Backup
    bak = META_PATH.with_suffix(".bak")
    if not bak.is_file():
        shutil.copy2(META_PATH, bak)
        log.info("Backed up meta → %s", bak.name)

    for region, key in keys_to_try:
        for cipher_id in [3, 5, 4]:
            db_ptr = ctypes.c_void_p()
            rc = dll.sqlite3_open_v2(str(META_PATH).encode(), ctypes.byref(db_ptr), SQLITE_OPEN_READWRITE, None)
            if rc != 0:
                continue
            dll.sqlite3mc_config(db_ptr, b"cipher", cipher_id)
            rc = dll.sqlite3_key(db_ptr, key, len(key))
            if rc != 0:
                dll.sqlite3_close(db_ptr)
                continue

            err_ptr = ctypes.c_void_p()
            rc = dll.sqlite3_exec(db_ptr, b"SELECT name FROM sqlite_master LIMIT 1;", None, None, ctypes.byref(err_ptr))
            if rc != 0:
                dll.sqlite3_close(db_ptr)
                continue

            log.info("Opened meta with %s key, cipher %d", region, cipher_id)

            rc = dll.sqlite3_exec(db_ptr, SQL_UPDATE, None, None, ctypes.byref(err_ptr))
            if rc == 0:
                changed = dll.sqlite3_changes(db_ptr)
                log.info("Marked %d home timeline entries for download (g=0)", changed)
                log.info("Now launch the JP game — it will download the bundles on startup.")
                dll.sqlite3_close(db_ptr)
                return
            else:
                msg = dll.sqlite3_errmsg(db_ptr)
                log.error("UPDATE failed: %s", msg.decode() if msg else "unknown")
                dll.sqlite3_close(db_ptr)

    log.error("Failed to open meta with any key/cipher combination")
    sys.exit(1)


if __name__ == "__main__":
    main()
