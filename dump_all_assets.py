#!/usr/bin/env python3
"""
Dump ALL assets from Uma Musume game bundles into an organised directory tree.

Reads every entry from the game's ``meta`` database, decrypts each asset
bundle, then uses UnityPy to iterate objects and export them by type:

  Texture2D / Sprite  → PNG or WEBP images
  TextAsset           → raw bytes (often .txt, .json, .csv, .bytes)
  MonoBehaviour       → JSON (typetree dump)
  AudioClip           → WAV (via UnityPy) or raw .audioclip
  AnimationClip       → JSON (typetree dump)
  Font                → .ttf / .otf bytes
  Shader              → raw text / bytes
  Mesh                → JSON (typetree dump)
  VideoClip           → raw bytes
  Material            → JSON (typetree dump)
  Everything else     → JSON typetree if readable, otherwise skipped

Output layout mirrors the asset name from the meta DB::

    <output_dir>/
      sound/b/bgm_race_001/
        audioclip_01.wav
      chara/chr1001_00/
        chr_icon_1001.png
      story/data/50/5001011/
        storytimeline_500101102.json
      ...

Usage:
    uv run dump_all_assets.py                          # auto-detect game dir
    uv run dump_all_assets.py /path/to/game/root       # explicit
    uv run dump_all_assets.py --output ./dump           # custom output dir
    uv run dump_all_assets.py --filter "story/%"        # only story assets
    uv run dump_all_assets.py --filter "sound/%"        # only sound assets
    uv run dump_all_assets.py --types Texture2D Sprite  # only textures
    uv run dump_all_assets.py --dry-run                 # list entries, don't extract
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import logging
import os
import struct
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

log = logging.getLogger("dump_all_assets")

# ── Lazy imports (heavy deps) ──────────────────────────────────────────

_UnityPy = None
_Image = None


def _get_unitypy():
    global _UnityPy
    if _UnityPy is None:
        try:
            import UnityPy

            _UnityPy = UnityPy
        except ImportError:
            log.error("UnityPy is required.  Install with:  uv pip install UnityPy")
            sys.exit(1)
    return _UnityPy


def _get_pillow():
    global _Image
    if _Image is None:
        try:
            from PIL import Image

            _Image = Image
        except ImportError:
            pass
    return _Image


# ── Constants (shared with extract_assets.py / extract_story_text.py) ──

AB_KEY = bytes([0x53, 0x2B, 0x46, 0x31, 0xE4, 0xA7, 0xB9, 0x47, 0x3E, 0x7C, 0xFB])

_FROZEN = getattr(sys, "frozen", False)
APP_DIR = Path(sys.executable).resolve().parent if _FROZEN else Path(__file__).resolve().parent


# ── Crypto ─────────────────────────────────────────────────────────────
# The XOR decryption is the main bottleneck.  We JIT-compile a tiny C
# function via the system compiler for ~150x speedup over the Python loop.
# Falls back to pure Python if no C compiler is available.


def derive_bundle_key(entry_key: int) -> bytes:
    key_bytes = struct.pack("<q", entry_key)
    result = bytearray(len(AB_KEY) * 8)
    for i, b in enumerate(AB_KEY):
        base = i * 8
        for j in range(8):
            result[base + j] = b ^ key_bytes[j]
    return bytes(result)


def _decrypt_python(data: bytearray, key: bytes, offset: int = 256) -> None:
    """Pure-Python XOR fallback (slow but always works)."""
    kl = len(key)
    for i in range(offset, len(data)):
        data[i] ^= key[i % kl]


def _compile_xor_lib():
    """
    JIT-compile a tiny C XOR function and return a fast decrypt callable.
    Returns None if compilation fails (no cc, etc.).
    """
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
        # Skip on Windows — no easy cc
        return None
    else:
        lib_path = os.path.join(tmpdir, "xor.so")
        lib_flag = "-shared"

    try:
        with open(src_path, "w") as f:
            f.write(c_src)
        subprocess.run(
            ["cc", "-O3", "-fPIC", lib_flag, "-o", lib_path, src_path],
            check=True, capture_output=True,
        )
        import ctypes as ct

        xorlib = ct.CDLL(lib_path)
        xorlib.xor_decrypt.argtypes = [
            ct.c_char_p, ct.c_size_t,
            ct.c_char_p, ct.c_size_t,
            ct.c_size_t,
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
    except Exception as e:
        log.debug("Failed to compile C XOR lib: %s", e)
        return None


# Try to compile the fast path once at import time
_fast_xor = _compile_xor_lib()
if _fast_xor:
    log.debug("Using JIT-compiled C XOR decryption (~150x faster)")
else:
    log.debug("C compiler not available, using pure-Python XOR (slower)")


def _xor_decrypt(data: bytearray, key: bytes, offset: int = 256) -> None:
    """XOR-decrypt data in place. Uses C if available, else pure Python."""
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


# ── Meta DB ────────────────────────────────────────────────────────────


def _load_config() -> dict:
    cfg_file = APP_DIR / "config.json"
    if cfg_file.is_file():
        try:
            return json.loads(cfg_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_config(cfg: dict) -> None:
    cfg_file = APP_DIR / "config.json"
    cfg_file.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


def _validate_game_dir(p: Path) -> bool:
    """Check that a directory looks like a valid game root (has dat/ and meta)."""
    if not p.is_dir():
        return False
    has_dat = (p / "dat").is_dir()
    has_meta = (p / "meta").is_file()
    if not has_dat and not has_meta:
        return False
    return True


def _find_known_game_dirs() -> list[Path]:
    """Auto-detect common Umamusume install locations."""
    candidates: list[Path] = []
    home = Path.home()

    if sys.platform == "win32":
        # DMM / Cygames default
        for base in [
            home / "AppData/LocalLow/Cygames/umamusume",
            Path("C:/Cygames/umamusume"),
            home / "Umamusume",
        ]:
            if _validate_game_dir(base):
                candidates.append(base)
    elif sys.platform == "darwin":
        # macOS — check common locations
        for base in [
            home / "Library/Containers/jp.co.cygames.umamusume/Data",
            home / "Cygames/umamusume",
        ]:
            if _validate_game_dir(base):
                candidates.append(base)

    # Also check config.json for previously saved dirs
    cfg = _load_config()
    for key in ("game_data_dir", "game_data_dirs"):
        val = cfg.get(key)
        if isinstance(val, str) and _validate_game_dir(Path(val)):
            p = Path(val).resolve()
            if p not in candidates:
                candidates.append(p)
        elif isinstance(val, list):
            for v in val:
                if isinstance(v, str) and _validate_game_dir(Path(v)):
                    p = Path(v).resolve()
                    if p not in candidates:
                        candidates.append(p)

    # Derive from master_db_path
    mdb = cfg.get("master_db_path")
    if mdb:
        root = Path(mdb).resolve().parent.parent
        if _validate_game_dir(root) and root not in candidates:
            candidates.append(root)

    return candidates


def _prompt_game_dir(explicit: str | None = None) -> Path | None:
    """
    Resolve the game directory — from CLI arg, config, auto-detect, or interactive prompt.
    """
    # 1. Explicit CLI argument
    if explicit:
        p = Path(explicit).resolve()
        if _validate_game_dir(p):
            return p
        # Maybe they pointed at dat/ or master/ — try parent
        if _validate_game_dir(p.parent):
            return p.parent
        log.error("Not a valid game directory (needs dat/ and meta): %s", explicit)
        return None

    # 2. Auto-detect known locations
    known = _find_known_game_dirs()

    if len(known) == 1:
        print(f"Auto-detected game directory: {known[0]}")
        return known[0]

    if len(known) > 1:
        print("\nFound multiple game installations:")
        for i, p in enumerate(known, 1):
            # Try to label JP vs Global by path heuristics
            label = ""
            ps = str(p).lower()
            if "jp" in ps or "cygames" in ps:
                label = " (JP?)"
            elif "global" in ps or "kakao" in ps or "bilibili" in ps:
                label = " (Global?)"
            print(f"  [{i}] {p}{label}")
        print(f"  [0] Enter a different path")

        while True:
            try:
                choice = input("\nSelect game directory [1]: ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return None
            if not choice:
                choice = "1"
            if choice == "0":
                break
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(known):
                    return known[idx]
            except ValueError:
                pass
            print(f"Invalid choice. Enter 1-{len(known)} or 0 for custom path.")

    # 3. Interactive prompt
    print("\nGame directory not found automatically.")
    print("The game directory should contain: dat/ (asset bundles) and meta (database)")
    if sys.platform == "win32":
        print("Typical location: C:\\Users\\<you>\\AppData\\LocalLow\\Cygames\\umamusume")
    while True:
        try:
            raw = input("\nEnter path to game directory (or 'q' to quit): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return None
        if raw.lower() in ("q", "quit", "exit"):
            return None
        p = Path(raw).expanduser().resolve()
        if _validate_game_dir(p):
            return p
        # Check parent (in case they pointed to dat/ or master/)
        if _validate_game_dir(p.parent):
            print(f"  → Using parent directory: {p.parent}")
            return p.parent
        print(f"  Not a valid game directory (no dat/ or meta found in {p})")
        if p.is_dir():
            contents = [x.name for x in sorted(p.iterdir())[:15]]
            print(f"  Contents: {', '.join(contents)}")


def _prompt_output_dir(default: str = "dump") -> Path:
    """Prompt for the output directory, with a sensible default."""
    try:
        raw = input(f"\nOutput directory [{default}]: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        raw = ""
    return Path(raw) if raw else Path(default)


def _open_meta(meta_path: Path):
    """Open the meta database, trying plaintext first, then encrypted."""
    import sqlite3

    # Try plaintext
    try:
        c = sqlite3.connect(f"file:{meta_path}?mode=ro", uri=True)
        c.row_factory = sqlite3.Row
        tables = [
            r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        ]
        if "a" in tables:
            return c
        c.close()
    except Exception:
        pass

    # Try encrypted via extract_story_text helper
    try:
        from extract_story_text import _try_open_encrypted_meta

        conn = _try_open_encrypted_meta(meta_path)
        if conn:
            return conn
    except Exception as exc:
        log.debug("Encrypted meta open failed: %s", exc)

    return None


def read_all_meta_entries(game_dir: Path, name_filter: str = "%") -> list[dict]:
    """
    Read entries from the meta DB.

    Args:
        name_filter: SQL LIKE pattern to filter entries. Default '%' = everything.

    Returns list of {name, hash, key}.
    """
    import sqlite3

    meta_path = game_dir / "meta"
    if not meta_path.is_file():
        log.error("meta database not found at %s", meta_path)
        return []

    conn = _open_meta(meta_path)
    if conn is None:
        log.error("Could not open meta database at %s", meta_path)
        return []

    entries: list[dict] = []
    try:
        cols_info = conn.execute("PRAGMA table_info(a)").fetchall()
        cols = {r[1] for r in cols_info}
        has_key = "e" in cols

        if has_key:
            sql = "SELECT n, h, e FROM a WHERE n LIKE ? ORDER BY n"
        else:
            sql = "SELECT n, h FROM a WHERE n LIKE ? ORDER BY n"

        rows = conn.execute(sql, (name_filter,)).fetchall()
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


# ── Image format detection ─────────────────────────────────────────────

_webp_ok: bool | None = None


def _can_webp() -> bool:
    global _webp_ok
    if _webp_ok is None:
        Image = _get_pillow()
        if Image is None:
            _webp_ok = False
        else:
            try:
                buf = io.BytesIO()
                Image.new("RGBA", (1, 1)).save(buf, "WEBP")
                _webp_ok = True
            except Exception:
                _webp_ok = False
    return _webp_ok


def _img_ext() -> str:
    return ".webp" if _can_webp() else ".png"


# ── Per-type exporters ─────────────────────────────────────────────────


def _safe_filename(name: str, fallback: str = "unnamed") -> str:
    """Sanitise a string for use as a filename component."""
    if not name:
        return fallback
    # Replace characters that are problematic on Windows/macOS/Linux
    for ch in r'<>:"/\|?*':
        name = name.replace(ch, "_")
    # Collapse whitespace / control chars
    name = "".join(c if c.isprintable() and c != "\n" else "_" for c in name)
    return name[:200] or fallback


def _export_texture(obj, out_dir: Path, idx: int) -> list[str]:
    """Export a Texture2D or Sprite object. Returns list of saved filenames."""
    saved = []
    try:
        data = obj.read()
        name = _safe_filename(getattr(data, "m_Name", "") or "", f"texture_{idx:04d}")
        ext = _img_ext()

        Image = _get_pillow()
        if Image is None:
            # No Pillow — save raw image bytes if available
            img = getattr(data, "image", None)
            if img is not None:
                raw_path = out_dir / f"{name}.png"
                img.save(str(raw_path))
                saved.append(raw_path.name)
            return saved

        img = data.image
        if img.mode not in ("RGBA", "RGB"):
            img = img.convert("RGBA")

        out_path = out_dir / f"{name}{ext}"
        if ext == ".webp":
            img.save(str(out_path), "WEBP", quality=85)
        else:
            img.save(str(out_path), "PNG")
        saved.append(out_path.name)
    except Exception as e:
        log.debug("  texture export failed: %s", e)
    return saved


def _export_text_asset(obj, out_dir: Path, idx: int) -> list[str]:
    """Export a TextAsset (binary blob or text file)."""
    saved = []
    try:
        data = obj.read()
        name = _safe_filename(getattr(data, "m_Name", "") or "", f"textasset_{idx:04d}")
        raw = getattr(data, "m_Script", b"") or b""
        if isinstance(raw, str):
            raw = raw.encode("utf-8")

        # Guess extension from content
        ext = ".bytes"
        if raw[:1] == b"{" or raw[:1] == b"[":
            ext = ".json"
        elif raw[:5] == b"<?xml" or raw[:1] == b"<":
            ext = ".xml"
        elif b"," in raw[:200] and b"\n" in raw[:500]:
            ext = ".csv"
        elif raw[:4] == b"PK\x03\x04":
            ext = ".zip"

        out_path = out_dir / f"{name}{ext}"
        out_path.write_bytes(raw)
        saved.append(out_path.name)
    except Exception as e:
        log.debug("  textasset export failed: %s", e)
    return saved


def _export_audioclip(obj, out_dir: Path, idx: int) -> list[str]:
    """Export an AudioClip — WAV via UnityPy samples if available, else raw."""
    saved = []
    try:
        data = obj.read()
        name = _safe_filename(getattr(data, "m_Name", "") or "", f"audio_{idx:04d}")

        # UnityPy exposes .samples as {sample_name: bytes} for decoded audio
        samples = getattr(data, "samples", None)
        if samples:
            for sname, sbytes in samples.items():
                sname_safe = _safe_filename(sname or name, f"sample_{idx:04d}")
                out_path = out_dir / f"{sname_safe}.wav"
                out_path.write_bytes(sbytes)
                saved.append(out_path.name)
        else:
            # Fallback: save m_AudioData raw bytes
            audio_data = getattr(data, "m_AudioData", b"")
            if audio_data:
                out_path = out_dir / f"{name}.audioclip"
                out_path.write_bytes(audio_data)
                saved.append(out_path.name)
    except Exception as e:
        log.debug("  audioclip export failed: %s", e)
    return saved


def _export_font(obj, out_dir: Path, idx: int) -> list[str]:
    """Export a Font asset."""
    saved = []
    try:
        data = obj.read()
        name = _safe_filename(getattr(data, "m_Name", "") or "", f"font_{idx:04d}")
        font_data = getattr(data, "m_FontData", b"")
        if font_data:
            # Detect format from magic bytes
            ext = ".ttf"
            if font_data[:4] == b"OTTO":
                ext = ".otf"
            elif font_data[:4] == b"wOFF":
                ext = ".woff"
            out_path = out_dir / f"{name}{ext}"
            out_path.write_bytes(font_data)
            saved.append(out_path.name)
    except Exception as e:
        log.debug("  font export failed: %s", e)
    return saved


def _export_shader(obj, out_dir: Path, idx: int) -> list[str]:
    """Export a Shader asset."""
    saved = []
    try:
        data = obj.read()
        name = _safe_filename(getattr(data, "m_Name", "") or "", f"shader_{idx:04d}")
        # Try to get the parsed script text
        script = getattr(data, "m_Script", None)
        if script:
            text = script if isinstance(script, str) else script.decode("utf-8", errors="replace")
            out_path = out_dir / f"{name}.shader"
            out_path.write_text(text, encoding="utf-8")
            saved.append(out_path.name)
        else:
            # Fallback: typetree dump
            saved.extend(_export_typetree(obj, out_dir, idx, f"shader_{name}"))
    except Exception as e:
        log.debug("  shader export failed: %s", e)
    return saved


def _export_typetree(obj, out_dir: Path, idx: int, prefix: str = "") -> list[str]:
    """Export any object via its typetree as JSON."""
    saved = []
    try:
        tree = obj.read_typetree()
        if tree is None:
            return saved
        name = ""
        if isinstance(tree, dict):
            name = _safe_filename(tree.get("m_Name", "") or "", "")
        if not name:
            name = prefix or f"object_{idx:04d}"
        out_path = out_dir / f"{name}.json"

        # Handle bytes in the tree for JSON serialisation
        def _default(o):
            if isinstance(o, bytes):
                return f"<bytes len={len(o)}>"
            if isinstance(o, memoryview):
                return f"<memoryview len={len(o)}>"
            return str(o)

        out_path.write_text(
            json.dumps(tree, indent=2, ensure_ascii=False, default=_default),
            encoding="utf-8",
        )
        saved.append(out_path.name)
    except Exception as e:
        log.debug("  typetree export failed: %s", e)
    return saved


def _export_monobehaviour(obj, out_dir: Path, idx: int) -> list[str]:
    return _export_typetree(obj, out_dir, idx, f"monobehaviour_{idx:04d}")


def _export_animationclip(obj, out_dir: Path, idx: int) -> list[str]:
    return _export_typetree(obj, out_dir, idx, f"animclip_{idx:04d}")


def _export_mesh(obj, out_dir: Path, idx: int) -> list[str]:
    return _export_typetree(obj, out_dir, idx, f"mesh_{idx:04d}")


def _export_material(obj, out_dir: Path, idx: int) -> list[str]:
    return _export_typetree(obj, out_dir, idx, f"material_{idx:04d}")


def _export_videoclip(obj, out_dir: Path, idx: int) -> list[str]:
    """Export a VideoClip — save raw external data if present."""
    saved = []
    try:
        data = obj.read()
        name = _safe_filename(getattr(data, "m_Name", "") or "", f"video_{idx:04d}")
        video_data = getattr(data, "m_VideoData", b"") or getattr(data, "m_ExternalResources", b"")
        if video_data and isinstance(video_data, bytes) and len(video_data) > 0:
            out_path = out_dir / f"{name}.mp4"
            out_path.write_bytes(video_data)
            saved.append(out_path.name)
        else:
            # Try typetree for metadata at least
            saved.extend(_export_typetree(obj, out_dir, idx, f"videoclip_{name}"))
    except Exception as e:
        log.debug("  videoclip export failed: %s", e)
    return saved


# Dispatcher: Unity type name → exporter function
EXPORTERS: dict[str, callable] = {
    "Texture2D": _export_texture,
    "Sprite": _export_texture,
    "TextAsset": _export_text_asset,
    "MonoBehaviour": _export_monobehaviour,
    "AudioClip": _export_audioclip,
    "AnimationClip": _export_animationclip,
    "Font": _export_font,
    "Shader": _export_shader,
    "Mesh": _export_mesh,
    "Material": _export_material,
    "VideoClip": _export_videoclip,
}

# Types that are structural / not worth exporting individually
SKIP_TYPES = {
    "GameObject",
    "Transform",
    "RectTransform",
    "CanvasRenderer",
    "AssetBundle",
    "PreloadData",
}


def dump_bundle(
    file_path: Path,
    entry_key: int,
    asset_name: str,
    output_root: Path,
    type_filter: set[str] | None = None,
) -> dict[str, int]:
    """
    Decrypt and dump all objects from a single asset bundle.

    Returns a dict of {type_name: count_exported}.
    """
    UnityPy = _get_unitypy()
    stats: dict[str, int] = {}

    out_dir = output_root / asset_name
    out_dir.mkdir(parents=True, exist_ok=True)

    env = None
    try:
        if entry_key != 0:
            data = decrypt_bundle(file_path, entry_key)
            try:
                env = UnityPy.load(data)
            except Exception:
                env = UnityPy.load(io.BytesIO(data))
        else:
            env = UnityPy.load(str(file_path))
    except Exception as e:
        log.warning("Failed to load bundle %s: %s", asset_name, e)
        with contextlib.suppress(OSError):
            out_dir.rmdir()
        return stats

    for idx, obj in enumerate(env.objects):
        type_name = obj.type.name

        if type_name in SKIP_TYPES:
            continue

        if type_filter and type_name not in type_filter:
            continue

        exporter = EXPORTERS.get(type_name)
        if exporter:
            files = exporter(obj, out_dir, idx)
        else:
            files = _export_typetree(obj, out_dir, idx, f"{type_name.lower()}_{idx:04d}")

        if files:
            stats[type_name] = stats.get(type_name, 0) + len(files)

    if not stats:
        with contextlib.suppress(OSError):
            out_dir.rmdir()

    return stats


# ── Worker function for multiprocessing ────────────────────────────────


def _dump_one(args: tuple) -> tuple[str, dict[str, int], str | None]:
    """
    Process a single bundle entry. Designed to be called via ProcessPoolExecutor.

    Args is a tuple of (file_path_str, entry_key, asset_name, output_root_str, type_filter_list).
    Returns (asset_name, stats_dict, error_msg_or_None).
    """
    file_path_str, entry_key, asset_name, output_root_str, type_filter_list = args
    file_path = Path(file_path_str)
    output_root = Path(output_root_str)
    type_filter = set(type_filter_list) if type_filter_list else None

    try:
        stats = dump_bundle(file_path, entry_key, asset_name, output_root, type_filter)
        return (asset_name, stats, None)
    except Exception as e:
        return (asset_name, {}, str(e))


# ── Main dump logic ───────────────────────────────────────────────────


def dump_all(
    game_dir: Path,
    output_root: Path,
    name_filter: str = "%",
    type_filter: set[str] | None = None,
    dry_run: bool = False,
    skip_existing: bool = True,
    workers: int = 0,
) -> dict[str, int]:
    """
    Dump all assets matching the filter.

    Args:
        workers: Number of parallel workers. 0 = auto (cpu_count), 1 = sequential.

    Returns aggregate {type_name: total_count}.
    """
    entries = read_all_meta_entries(game_dir, name_filter)
    if not entries:
        log.error("No entries found in meta DB (filter=%r)", name_filter)
        return {}

    # Filter out resourcelist / manifest-only entries
    entries = [e for e in entries if "resourcelist" not in e["name"]]

    log.info("Found %d asset entries to process", len(entries))

    if dry_run:
        by_prefix: dict[str, int] = {}
        for e in entries:
            prefix = e["name"].split("/")[0] if "/" in e["name"] else "(root)"
            by_prefix[prefix] = by_prefix.get(prefix, 0) + 1
        print(f"\nDry run: {len(entries)} assets total")
        print(f"{'Category':<40} {'Count':>8}")
        print("-" * 50)
        for prefix in sorted(by_prefix, key=lambda k: -by_prefix[k]):
            print(f"{prefix:<40} {by_prefix[prefix]:>8}")
        return {}

    dat_dir = game_dir / "dat"
    total = len(entries)
    agg_stats: dict[str, int] = {}
    processed = 0
    skipped = 0
    errors = 0
    t0 = time.time()

    # Build work list, skipping already-done and missing files
    work_items: list[tuple] = []
    type_filter_list = list(type_filter) if type_filter else None

    for entry in entries:
        asset_name = entry["name"]
        h = entry["hash"]
        file_path = dat_dir / h[:2] / h

        out_dir = output_root / asset_name
        if skip_existing and out_dir.is_dir() and any(out_dir.iterdir()):
            skipped += 1
            processed += 1
            continue

        if not file_path.is_file():
            processed += 1
            continue

        work_items.append((
            str(file_path), entry["key"], asset_name,
            str(output_root), type_filter_list,
        ))

    remaining = len(work_items)
    log.info(
        "%d to extract, %d skipped (existing), %d missing files",
        remaining, skipped, processed - skipped,
    )

    if not work_items:
        _progress(total, total, skipped, errors, agg_stats, t0, final=True)
        return agg_stats

    if workers == 0:
        workers = min(os.cpu_count() or 4, 8)

    # Show initial progress
    _progress(processed, total, skipped, errors, agg_stats, t0)

    if workers == 1:
        # Sequential mode
        for args in work_items:
            asset_name, stats, err = _dump_one(args)
            if err:
                errors += 1
                log.debug("Error processing %s: %s", asset_name, err)
            for k, v in stats.items():
                agg_stats[k] = agg_stats.get(k, 0) + v
            processed += 1
            if processed % 50 == 0:
                _progress(processed, total, skipped, errors, agg_stats, t0)
    else:
        # Parallel mode
        log.info("Using %d worker processes", workers)
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(_dump_one, args): args[2]
                for args in work_items
            }
            for future in as_completed(futures):
                asset_name = futures[future]
                try:
                    _, stats, err = future.result()
                    if err:
                        errors += 1
                        log.debug("Error processing %s: %s", asset_name, err)
                    for k, v in stats.items():
                        agg_stats[k] = agg_stats.get(k, 0) + v
                except Exception as e:
                    errors += 1
                    log.debug("Worker exception for %s: %s", asset_name, e)
                processed += 1
                if processed % 50 == 0:
                    _progress(processed, total, skipped, errors, agg_stats, t0)

    _progress(processed, total, skipped, errors, agg_stats, t0, final=True)
    return agg_stats


# ── Symboli Rudolf ASCII art (generated from game art) ─────────────────
# The Emperor supervises while your assets are extracted. 皇帝に敬礼！

# Frame 0: facing right (original pose)
_RUDOLF_R = [
    "          *   ?*                ",
    "          *++,***+              ",
    "           +*;,;+++?            ",
    "           *+,..+*+             ",
    "      *++:;;*:,,+++*            ",
    "      ?*++;.,,,;*:.:*+;         ",
    "        +?,:,,;;... ,++++*      ",
    "       ;++;*:**..;*;;***+**     ",
    "      *++*******?**+*??**+      ",
    "      *?+**+;*+:,:;+*+ **       ",
    "        ;::;;+;:;::+*++         ",
    "      +,  ,?%?;...   .,,        ",
    "     :+++,+++**...,+;..:+       ",
    "     *+*++:,.;?...:+;;??*?      ",
    "      *+**??????++****+;        ",
    "      ++++*?????***?*+++        ",
    "        %?**??  ****?***+++     ",
    "           +*??  ****  ***++;?  ",
    "           +??*   ***;    **++  ",
    "           ..,:    ,..+   **?   ",
    "           :  :    .  ;         ",
    "            ..;     , ,         ",
    "          .  :*     . .         ",
    "          ::;%      :,:         ",
]

# Frame 1: facing left (mirrored)
_RUDOLF_L = [
    "                *?   *          ",
    "              +***,++*          ",
    "            ?+++;,;*+           ",
    "             +*+..,+*           ",
    "            *+++,,:*;;:++*      ",
    "         ;+*:.:*;,,,.;++*?      ",
    "      *++++, ...;;,,:,?+        ",
    "     **+***;;*;..**:*;++;       ",
    "      +**??*+**?*******++*      ",
    "       ** +*+;:,:+*;+**+?*      ",
    "         ++*+::;:;+;;::;        ",
    "        ,,.   ...;?%?,  ,+      ",
    "       +:..;+,...**+++,+++:     ",
    "      ?*??;;+:...?;.,:++*+*     ",
    "        ;+****++??????**+*      ",
    "        +++*?***?????*++++      ",
    "     +++***?****  ??**?%        ",
    "  ?;++***  ****  ??*+           ",
    "  ++**    ;***   *??+           ",
    "   ?**   +..,    :,..           ",
    "         ;  .    :  :           ",
    "         , ,     ;..            ",
    "         . .     *:  .          ",
    "         :,:      %;::          ",
]

# Dancing: 4 frames — shift left, centre-right, shift right, centre-left
RUDOLF_FRAMES = []
for _base in [_RUDOLF_R, _RUDOLF_L]:
    # Bounce: shift by 1 column
    shifted = ["  " + l for l in _base]
    RUDOLF_FRAMES.append(_base)
    RUDOLF_FRAMES.append(shifted)

RUDOLF_DONE = [
    "                                              ",
    "          *   ?*                               ",
    "          *++,***+    皇帝の勝利だ！          ",
    "           +*;,;+++?                           ",
    "           *+,..+*+    Extraction complete!    ",
    "      *++:;;*:,,+++*                           ",
    "      ?*++;.,,,;*:.:*+;                        ",
    "        +?,:,,;;... ,++++*                     ",
    "       ;++;*:**..;*;;***+**                    ",
    "      *++*******?**+*??**+                     ",
    "      *?+**+;*+:,:;+*+ **                      ",
    "        ;::;;+;:;::+*++                        ",
    "      +,  ,?%?;...   .,,                       ",
    "     :+++,+++**...,+;..:+                      ",
    "     *+*++:,.;?...:+;;??*?                     ",
    "      *+**??????++****+;                       ",
    "      ++++*?????***?*+++                       ",
    "        %?**??  ****?***+++                    ",
    "           +*??  ****  ***++;?                 ",
    "           +??*   ***;    **++                 ",
    "           ..,:    ,..+   **?                  ",
    "           :  :    .  ;                        ",
    "            ..;     , ,                        ",
    "          .  :*     . .                        ",
    "          ::;%      :,:                        ",
]

_prev_lines = 0


def _progress(
    done: int,
    total: int,
    skipped: int,
    errors: int,
    stats: dict[str, int],
    t0: float,
    final: bool = False,
):
    global _prev_lines
    elapsed = time.time() - t0
    rate = done / elapsed if elapsed > 0 else 0
    total_files = sum(stats.values())
    pct = done * 100 / total if total else 0

    # Build the progress bar
    bar_width = 30
    filled = int(bar_width * pct / 100) if total else 0
    bar = "█" * filled + "░" * (bar_width - filled)

    # Pick Rudolf frame
    if final:
        frame = RUDOLF_DONE
    else:
        frame = RUDOLF_FRAMES[done % len(RUDOLF_FRAMES)]

    # Stats lines (displayed below the art)
    stat_parts = [f"{total_files} files"]
    if skipped:
        stat_parts.append(f"{skipped} skip")
    if errors:
        stat_parts.append(f"{errors} err")
    stat_parts.append(f"{elapsed:.0f}s")
    if rate > 0:
        stat_parts.append(f"{rate:.0f}/s")
    stat_str = " | ".join(stat_parts)

    output_lines = list(frame) + [
        "",
        f"  [{bar}] {pct:.0f}%",
        f"  {done}/{total} bundles | {stat_str}",
    ]

    # Move cursor up to overwrite previous frame
    if _prev_lines > 0:
        sys.stdout.write(f"\033[{_prev_lines}A\033[J")

    output = "\n".join(output_lines)
    sys.stdout.write(output + "\n")
    sys.stdout.flush()
    _prev_lines = len(output_lines)

    if final:
        print()
        if stats:
            print("Exported assets by type:")
            for t in sorted(stats, key=lambda k: -stats[k]):
                print(f"  {t:<25} {stats[t]:>8}")
        print()


# ── CLI ────────────────────────────────────────────────────────────────


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(
        description="Dump ALL assets from Uma Musume game bundles.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              # interactive — asks for paths
  %(prog)s /path/to/game/root           # explicit game dir, asks for output
  %(prog)s /game/root -o ./dump-jp      # fully non-interactive
  %(prog)s --filter "story/%%"           # only story assets
  %(prog)s --filter "sound/%%"           # only sound assets
  %(prog)s --filter "chara/%%"           # only character assets
  %(prog)s --types Texture2D Sprite     # only textures
  %(prog)s --types MonoBehaviour        # only MonoBehaviours (JSON)
  %(prog)s --dry-run                    # list asset categories without extracting
  %(prog)s --no-skip                    # re-extract even if output exists
        """,
    )
    parser.add_argument("game_dir", nargs="?", help="Path to game root (contains dat/ and meta)")
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output directory (default: ask interactively, or ./dump if piped)",
    )
    parser.add_argument(
        "--filter", "-f",
        default="%",
        help="SQL LIKE filter on asset name (default: %% = everything)",
    )
    parser.add_argument(
        "--types", "-t",
        nargs="*",
        help="Only export these Unity types (e.g. Texture2D MonoBehaviour AudioClip)",
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="List matching entries without extracting",
    )
    parser.add_argument(
        "--no-skip",
        action="store_true",
        help="Re-extract assets even if output directory already has files",
    )
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=0,
        help="Number of parallel workers (default: auto = cpu_count, 1 = sequential)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save the chosen game directory to config.json for next time",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # ── Resolve game directory (interactive if needed) ──
    game_dir = _prompt_game_dir(args.game_dir)
    if not game_dir:
        sys.exit(1)

    log.info("Game directory: %s", game_dir)

    # Offer to save for next time
    cfg = _load_config()
    saved_dir = cfg.get("game_data_dir")
    if str(game_dir.resolve()) != str(Path(saved_dir).resolve() if saved_dir else ""):
        should_save = args.save
        if not should_save and sys.stdin.isatty():
            try:
                ans = input(f"\nSave this game directory to config.json for next time? [Y/n]: ").strip()
                should_save = ans.lower() in ("", "y", "yes")
            except (EOFError, KeyboardInterrupt):
                print()
        if should_save:
            cfg["game_data_dir"] = str(game_dir.resolve())
            _save_config(cfg)
            log.info("Saved game_data_dir to config.json")

    # ── Resolve output directory ──
    if args.output is not None:
        output_root = Path(args.output)
    elif sys.stdin.isatty():
        output_root = _prompt_output_dir("dump")
    else:
        output_root = Path("dump")

    output_root.mkdir(parents=True, exist_ok=True)
    log.info("Output directory: %s", output_root.resolve())

    type_filter = set(args.types) if args.types else None

    stats = dump_all(
        game_dir=game_dir,
        output_root=output_root,
        name_filter=args.filter,
        type_filter=type_filter,
        dry_run=args.dry_run,
        skip_existing=not args.no_skip,
        workers=args.workers,
    )

    if stats:
        log.info("Done! Assets written to %s", output_root.resolve())


if __name__ == "__main__":
    main()
