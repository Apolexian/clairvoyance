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
    uv run dump_all_assets.py --images-only              # images only, flat dirs
    uv run dump_all_assets.py --images-only --no-cache  # force full rescan
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


# ── Bundle type cache / manifest ───────────────────────────────────────
# Tracks which Unity types each bundle contains so subsequent runs can
# skip bundles that have no types matching the filter (e.g. images-only
# skips bundles that only contain AudioClip/TextAsset).  Also serves as
# a delta mechanism: if a bundle's hash hasn't changed, it's skipped.

_MANIFEST_NAME = ".dump_manifest.json"
_MANIFEST_VERSION = 1


def _load_manifest(output_root: Path) -> dict:
    """Load the manifest from disk. Returns {hash: {types: [...]}}.

    The top-level structure is ``{"v": 1, "bundles": {hash: {...}}}``.
    """
    p = output_root / _MANIFEST_NAME
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if data.get("v") != _MANIFEST_VERSION:
            return {}
        return data.get("bundles", {})
    except Exception:
        return {}


def _save_manifest(output_root: Path, bundles: dict) -> None:
    p = output_root / _MANIFEST_NAME
    p.write_text(
        json.dumps({"v": _MANIFEST_VERSION, "bundles": bundles}, separators=(",", ":")),
        encoding="utf-8",
    )


# Asset name prefixes that are known to never contain image data.
# Used to pre-filter entries in images-only mode for a large speedup.
_NON_IMAGE_PREFIXES = (
    "sound/",
    "movie/",
    "font/",
    "masterdb/",
    "manifest/",
    "shader/",
)


def _is_image_candidate(name: str) -> bool:
    """Return False for asset names that are known to never contain images."""
    for prefix in _NON_IMAGE_PREFIXES:
        if name.startswith(prefix):
            return False
    return True


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


# Image output format for _export_texture.  Set via --format CLI flag.
# "png" = lossless PNG, "webp" = high-quality WEBP (lossless by default).
_IMAGE_FORMAT: str = "png"
_IMAGE_QUALITY: int = 95  # only used when _IMAGE_FORMAT == "webp" and lossy


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


def _autocrop_transparent(img):
    """Crop transparent padding from an RGBA image.

    Unity textures are often padded to power-of-2 dimensions.  This trims
    fully-transparent rows/columns so the exported file has the correct
    aspect ratio (e.g. support cards at 9:12 instead of being squished
    into a 1024×1024 square).

    Returns the cropped image, or the original if no cropping is needed.
    """
    if img.mode != "RGBA":
        return img
    bbox = img.getbbox()  # bounding box of non-zero (non-transparent) area
    if bbox is None:
        return img
    # Only crop if there's meaningful padding (>1 px on any side)
    w, h = img.size
    left, upper, right, lower = bbox
    if left <= 1 and upper <= 1 and right >= w - 1 and lower >= h - 1:
        return img
    return img.crop(bbox)


def _export_texture(obj, out_dir: Path, idx: int) -> list[str]:
    """Export a Texture2D or Sprite object. Returns list of saved filenames.

    Sprite objects are preferred over Texture2D (handled in dump_bundle) since
    UnityPy's Sprite.image uses the textureRect to crop to the correct region.
    For any remaining Texture2D objects (no matching Sprite in the bundle),
    transparent padding is auto-cropped as a fallback.

    Output format is controlled by the module-level ``_IMAGE_FORMAT`` setting
    (default PNG, switchable to WEBP via ``--format webp``).
    """
    saved = []
    try:
        data = obj.read()
        name = _safe_filename(getattr(data, "m_Name", "") or "", f"texture_{idx:04d}")

        img = data.image  # PIL Image at original dimensions

        # Texture2D may have power-of-2 padding; Sprites are already cropped
        if obj.type.name == "Texture2D":
            img = _autocrop_transparent(img)

        if _IMAGE_FORMAT == "webp" and _can_webp():
            out_path = out_dir / f"{name}.webp"
            img.save(str(out_path), "WEBP", lossless=(_IMAGE_QUALITY >= 100),
                     quality=_IMAGE_QUALITY, method=4)
        else:
            out_path = out_dir / f"{name}.png"
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


def _get_audio_data(data) -> bytes | None:
    """Get raw audio bytes from an AudioClip, handling external resources."""
    audio_data = getattr(data, "m_AudioData", None)
    if audio_data and len(audio_data) > 0:
        return bytes(audio_data)
    # Audio stored in external .resource file
    res = getattr(data, "m_Resource", None)
    if res and getattr(res, "m_Size", 0) > 0:
        try:
            from UnityPy.helpers.ResourceReader import get_resource_data

            return get_resource_data(
                res.m_Source, data.object_reader.assets_file, res.m_Offset, res.m_Size
            )
        except Exception as e:
            log.debug("  failed to read external audio resource: %s", e)
    return None


def _audio_ext_from_magic(data: bytes) -> str:
    """Detect audio format from magic bytes."""
    if data[:4] == b"OggS":
        return ".ogg"
    if data[:4] == b"RIFF":
        return ".wav"
    if len(data) >= 8 and data[4:8] == b"ftyp":
        return ".m4a"
    if data[:4] in (b"FSB3", b"FSB4", b"FSB5"):
        return ".fsb"
    return ".bin"


def _export_audioclip(obj, out_dir: Path, idx: int) -> list[str]:
    """Export an AudioClip.

    Strategy:
      1. Try UnityPy .samples (decodes OGG/WAV/M4A natively, FSB via FMOD).
      2. If .samples fails (FMOD not installed), save raw audio with the
         correct extension so external tools (vgmstream, foobar2000) can
         open it.
    """
    saved = []
    try:
        data = obj.read()
        name = _safe_filename(getattr(data, "m_Name", "") or "", f"audio_{idx:04d}")

        # Try the full UnityPy decode path first (handles OGG/WAV/M4A natively,
        # FSB via pyfmodex if the FMOD native library is installed)
        try:
            samples = data.samples
            if samples:
                for sname, sbytes in samples.items():
                    sname_safe = _safe_filename(sname or name, f"sample_{idx:04d}")
                    out_path = out_dir / sname_safe
                    out_path.write_bytes(sbytes)
                    saved.append(out_path.name)
                return saved
        except Exception as e:
            log.debug("  UnityPy .samples decode failed (likely no FMOD): %s", e)

        # Fallback: save raw audio data with detected extension
        raw = _get_audio_data(data)
        if raw and len(raw) > 0:
            ext = _audio_ext_from_magic(raw)
            out_path = out_dir / f"{name}{ext}"
            out_path.write_bytes(raw)
            saved.append(out_path.name)
            if ext == ".fsb":
                log.debug(
                    "  saved as FSB (install FMOD SDK for WAV conversion, "
                    "or use vgmstream/foobar2000 to play)"
                )
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


def _video_ext_from_magic(data: bytes) -> str:
    """Detect video format from magic bytes."""
    if len(data) >= 8 and data[4:8] == b"ftyp":
        return ".mp4"
    if data[:4] == b"CRID":
        return ".usm"
    if data[:4] == b"\x1aE\xdf\xa3":
        return ".webm"
    return ".mp4"


def _export_videoclip(obj, out_dir: Path, idx: int) -> list[str]:
    """Export a VideoClip.

    Videos are usually stored in an external StreamedResource (not inline).
    We read m_ExternalResources via UnityPy's resource reader, then save
    with the correct extension based on magic bytes.
    """
    saved = []
    try:
        data = obj.read()
        name = _safe_filename(getattr(data, "m_Name", "") or "", f"video_{idx:04d}")

        video_bytes = None

        # m_ExternalResources is a StreamedResource with (m_Source, m_Offset, m_Size)
        res = getattr(data, "m_ExternalResources", None)
        if res and getattr(res, "m_Size", 0) > 0:
            try:
                from UnityPy.helpers.ResourceReader import get_resource_data

                video_bytes = get_resource_data(
                    res.m_Source, data.object_reader.assets_file, res.m_Offset, res.m_Size
                )
            except FileNotFoundError:
                # External .resource file not bundled — common for large videos.
                # Log the original path so the user knows where to find it.
                orig = getattr(data, "m_OriginalPath", "")
                log.debug(
                    "  video %r: external resource %r not found (original: %s)",
                    name,
                    getattr(res, "m_Source", "?"),
                    orig or "unknown",
                )
            except Exception as e:
                log.debug("  video %r: failed to read resource: %s", name, e)

        # Some clips embed data directly (rare)
        if not video_bytes:
            raw = getattr(data, "m_VideoData", b"")
            if raw and len(raw) > 0:
                video_bytes = bytes(raw)

        if video_bytes and len(video_bytes) > 0:
            ext = _video_ext_from_magic(video_bytes)
            out_path = out_dir / f"{name}{ext}"
            out_path.write_bytes(video_bytes)
            saved.append(out_path.name)
        else:
            # No video data available — dump metadata as JSON
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


def _resolve_external_resources(env, asset_name: str, dat_dir: Path | None,
                                meta_lookup: dict[str, tuple[str, int]] | None) -> None:
    """Load external .resource/.resS files that objects in *env* reference.

    Unity bundles for audio/video often store the heavy data in a separate
    StreamedResource.  The m_Source field names a cab like ``CAB-xxx.resource``
    that lives inside a *companion* bundle.  In Uma Musume's hash-based storage
    the companion is a different file in dat/, so UnityPy can't find it on
    disk by name.

    We scan every SerializedFile's externals and every AudioClip/VideoClip
    resource reference, then load the companion bundle from dat/ using the
    meta DB hash mapping.
    """
    if not dat_dir or not meta_lookup:
        return

    import ntpath
    UnityPy = _get_unitypy()

    needed: set[str] = set()

    # 1) Gather explicit externals listed in serialized files
    for f in env.files.values():
        for ext in getattr(f, "externals", []):
            path = getattr(ext, "path", "")
            if path:
                needed.add(path)

    # 2) Scan objects for StreamedResource references
    for obj in env.objects:
        tname = obj.type.name
        if tname not in ("AudioClip", "VideoClip"):
            continue
        try:
            data = obj.read()
            res = getattr(data, "m_Resource", None) or getattr(data, "m_ExternalResources", None)
            if res and getattr(res, "m_Size", 0) > 0:
                src = getattr(res, "m_Source", "")
                if src:
                    needed.add(src)
        except Exception:
            pass

    if not needed:
        return

    # Filter out resources already registered as cabs
    missing = set()
    for name in needed:
        basename = ntpath.basename(name).lower()
        if env.get_cab(basename) is None and env.get_cab(name) is None:
            missing.add(name)

    if not missing:
        return

    # The meta DB maps asset names → (hash, key). Companion resource bundles
    # often share the same asset name prefix.  We also try the exact cab name.
    # Build a reverse lookup: cab-name-stem → meta entry.
    #
    # In practice, Uma Musume's meta DB entries like
    #   sound/b/bgm_race_001  → hash1 (the bundle with AudioClip metadata)
    # don't have a separate entry for the .resource — it's inside the SAME
    # bundle archive.  So if we get here, the resource is truly inside the
    # loaded bundle but UnityPy couldn't find it.  Let's check env.files:
    loaded_cabs = {k.lower() for k in env.cabs}
    for name in list(missing):
        # Try variations that UnityPy's get_resource_data checks
        basename = ntpath.basename(name)
        stem = ntpath.splitext(basename)[0]
        variations = [
            basename.lower(),
            f"{stem}.resource".lower(),
            f"{stem}.assets.ress".lower(),
            f"{stem}.ress".lower(),
        ]
        if any(v in loaded_cabs for v in variations):
            missing.discard(name)

    if not missing:
        return

    log.debug("  %s: resolving %d external resources: %s",
              asset_name, len(missing), [ntpath.basename(n) for n in missing])

    # Try companion bundles from the sibling lookup (entries sharing same
    # directory prefix in the meta DB namespace)
    candidates: list[tuple[str, str, int]] = [
        (meta_name, h, key) for meta_name, (h, key) in meta_lookup.items()
    ]

    for meta_name, h, key in candidates:
        fp = dat_dir / h[:2] / h
        if not fp.is_file():
            continue
        try:
            if key != 0:
                comp_data = decrypt_bundle(fp, key)
                try:
                    comp_env = UnityPy.load(comp_data)
                except Exception:
                    comp_env = UnityPy.load(io.BytesIO(comp_data))
            else:
                comp_env = UnityPy.load(str(fp))

            # Register all cabs from companion into main env
            registered_any = False
            for cab_name, cab_reader in comp_env.cabs.items():
                if cab_name not in env.cabs:
                    env.register_cab(cab_name, cab_reader)
                    registered_any = True
            if registered_any:
                log.debug("  loaded companion bundle %s (%s)", h[:12], meta_name)

            # Check if all missing resources are now resolved
            still_missing = set()
            for name in missing:
                basename = ntpath.basename(name).lower()
                if env.get_cab(basename) is None and env.get_cab(name) is None:
                    still_missing.add(name)
            missing = still_missing
            if not missing:
                return
        except Exception as e:
            log.debug("  failed to load companion %s: %s", h[:12], e)

    if missing:
        log.debug("  %s: could not resolve resources: %s",
                  asset_name, [ntpath.basename(n) for n in missing])


def dump_bundle(
    file_path: Path,
    entry_key: int,
    asset_name: str,
    output_root: Path,
    type_filter: set[str] | None = None,
    flat_depth: int | None = None,
    collapse_singles: bool = False,
    dat_dir: Path | None = None,
    meta_lookup: dict[str, tuple[str, int]] | None = None,
) -> dict[str, int]:
    """
    Decrypt and dump all objects from a single asset bundle.

    Args:
        flat_depth: If set, cap the output directory nesting to this many
                    levels below *output_root*.  For example ``flat_depth=1``
                    turns ``chara/chr1001_00/pfb_chr1001_00`` into
                    ``chara/chr1001_00__pfb_chr1001_00`` (one subdirectory).
        collapse_singles: If True, when a bundle produces exactly one file
                          move it up to the parent directory and remove the
                          now-empty wrapper directory.  File names are kept
                          as-is (they contain the IDs callers rely on).
        dat_dir: Path to the dat/ directory for resolving external resources.
        meta_lookup: {asset_name: (hash, key)} for finding companion bundles.

    Returns a dict of {type_name: count_exported}.
    """
    UnityPy = _get_unitypy()
    stats: dict[str, int] = {}

    if flat_depth is not None:
        parts = Path(asset_name).parts
        if len(parts) > flat_depth:
            rest = "__".join(parts[flat_depth:])
            if flat_depth > 0:
                out_dir = output_root / Path(*parts[:flat_depth]) / rest
            else:
                out_dir = output_root / rest
        else:
            out_dir = output_root / asset_name
    else:
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

    # Resolve external .resource/.resS files for audio/video
    _resolve_external_resources(env, asset_name, dat_dir, meta_lookup)

    # When exporting images, prefer Sprite over Texture2D for the same
    # asset name because Sprite.image uses the textureRect to crop to the
    # correct aspect ratio (e.g. 9:12 support cards) whereas Texture2D
    # returns the raw texture which may have power-of-2 padding.
    sprite_names: set[str] = set()
    if not type_filter or "Texture2D" in type_filter or "Sprite" in type_filter:
        for obj in env.objects:
            if obj.type.name == "Sprite":
                with contextlib.suppress(Exception):
                    name = obj.peek_name()
                    if name:
                        sprite_names.add(name)

    for idx, obj in enumerate(env.objects):
        type_name = obj.type.name

        if type_name in SKIP_TYPES:
            continue

        if type_filter and type_name not in type_filter:
            continue

        # Skip Texture2D when a Sprite with the same name exists — the
        # Sprite export will have the correct dimensions / aspect ratio.
        if type_name == "Texture2D" and sprite_names:
            with contextlib.suppress(Exception):
                if obj.peek_name() in sprite_names:
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
    elif collapse_singles:
        _collapse_single_file_dir(out_dir)

    return stats


def _collapse_single_file_dir(out_dir: Path) -> None:
    """Move a lone file up to the parent dir and remove the wrapper."""
    try:
        children = list(out_dir.iterdir())
        if len(children) != 1 or not children[0].is_file():
            return
        single = children[0]
        dest = out_dir.parent / single.name
        if dest.exists():
            return  # name collision — keep the directory
        single.rename(dest)
        out_dir.rmdir()
    except OSError:
        pass


# ── Worker function for multiprocessing ────────────────────────────────


def _dump_one(args: tuple) -> tuple[str, str, dict[str, int], str | None]:
    """
    Process a single bundle entry. Designed to be called via ProcessPoolExecutor.

    Args is a tuple of (file_path_str, entry_key, asset_name, entry_hash,
    output_root_str, type_filter_list, flat_depth, collapse_singles,
    image_format, image_quality, dat_dir_str, meta_lookup).
    Returns (asset_name, entry_hash, stats_dict, error_msg_or_None).
    """
    (file_path_str, entry_key, asset_name, entry_hash, output_root_str,
     type_filter_list, flat_depth, collapse_singles,
     image_format, image_quality, dat_dir_str, meta_lookup) = args
    file_path = Path(file_path_str)
    output_root = Path(output_root_str)
    type_filter = set(type_filter_list) if type_filter_list else None
    dat_dir = Path(dat_dir_str) if dat_dir_str else None

    # Set module globals in spawned workers (macOS/Windows use spawn)
    global _IMAGE_FORMAT, _IMAGE_QUALITY
    _IMAGE_FORMAT = image_format
    _IMAGE_QUALITY = image_quality

    try:
        stats = dump_bundle(
            file_path, entry_key, asset_name, output_root,
            type_filter, flat_depth, collapse_singles,
            dat_dir=dat_dir, meta_lookup=meta_lookup,
        )
        return (asset_name, entry_hash, stats, None)
    except Exception as e:
        return (asset_name, entry_hash, {}, str(e))


# ── Main dump logic ───────────────────────────────────────────────────


def dump_all(
    game_dir: Path,
    output_root: Path,
    name_filter: str = "%",
    type_filter: set[str] | None = None,
    dry_run: bool = False,
    skip_existing: bool = True,
    workers: int = 0,
    flat_depth: int | None = None,
    collapse_singles: bool = False,
    use_cache: bool = True,
) -> dict[str, int]:
    """
    Dump all assets matching the filter.

    Args:
        workers: Number of parallel workers. 0 = auto (cpu_count), 1 = sequential.
        flat_depth: Max directory nesting depth below output_root (None = unlimited).
        collapse_singles: Collapse single-file output directories.
        use_cache: Use .dump_manifest.json to skip already-processed bundles
                   and bundles known to have no matching types (delta mode).

    Returns aggregate {type_name: total_count}.
    """
    entries = read_all_meta_entries(game_dir, name_filter)
    if not entries:
        log.error("No entries found in meta DB (filter=%r)", name_filter)
        return {}

    # Filter out resourcelist / manifest-only entries
    entries = [e for e in entries if "resourcelist" not in e["name"]]

    # In images-only mode, skip asset names that are known to never contain images
    images_only = type_filter and type_filter <= {"Texture2D", "Sprite"}
    if images_only:
        before = len(entries)
        entries = [e for e in entries if _is_image_candidate(e["name"])]
        excluded = before - len(entries)
        if excluded:
            log.info("Excluded %d non-image entries (sound/movie/font/…)", excluded)

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
    cache_skipped = 0
    errors = 0
    t0 = time.time()

    # Load manifest for delta / type-cache support
    manifest = _load_manifest(output_root) if use_cache else {}

    # Build work list, skipping already-done and missing files
    work_items: list[tuple] = []
    type_filter_list = list(type_filter) if type_filter else None

    for entry in entries:
        asset_name = entry["name"]
        h = entry["hash"]
        file_path = dat_dir / h[:2] / h

        # Delta: skip if manifest shows this hash was already processed
        if use_cache and h in manifest:
            cached = manifest[h]
            # If type-filtered, skip bundles that had no matching types
            if type_filter:
                cached_types = set(cached.get("types", []))
                if not (cached_types & type_filter):
                    cache_skipped += 1
                    processed += 1
                    continue
            # Hash matches and not type-filtered out — already extracted
            skipped += 1
            processed += 1
            continue

        out_dir = output_root / asset_name
        if skip_existing and out_dir.is_dir() and any(out_dir.iterdir()):
            skipped += 1
            processed += 1
            continue

        if not file_path.is_file():
            processed += 1
            continue

        # Build a small sibling lookup for resolving companion resource bundles
        # (only entries sharing the same directory prefix)
        prefix = asset_name.rsplit("/", 1)[0] + "/" if "/" in asset_name else ""
        sibling_lookup = {
            n: (e2["hash"], e2["key"])
            for e2 in entries
            for n in [e2["name"]]
            if prefix and n.startswith(prefix) and n != asset_name
        } if prefix else {}

        work_items.append((
            str(file_path), entry["key"], asset_name, h,
            str(output_root), type_filter_list, flat_depth,
            collapse_singles, _IMAGE_FORMAT, _IMAGE_QUALITY,
            str(dat_dir), sibling_lookup,
        ))

    remaining = len(work_items)
    skip_detail = f"{skipped} skipped (existing)"
    if cache_skipped:
        skip_detail += f", {cache_skipped} skipped (cache: no matching types)"
    log.info(
        "%d to extract, %s, %d missing files",
        remaining, skip_detail, processed - skipped - cache_skipped,
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
            asset_name, entry_hash, stats, err = _dump_one(args)
            if err:
                errors += 1
                log.debug("Error processing %s: %s", asset_name, err)
            for k, v in stats.items():
                agg_stats[k] = agg_stats.get(k, 0) + v
            if use_cache:
                manifest[entry_hash] = {"types": list(stats.keys())}
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
                    _, entry_hash, stats, err = future.result()
                    if err:
                        errors += 1
                        log.debug("Error processing %s: %s", asset_name, err)
                    for k, v in stats.items():
                        agg_stats[k] = agg_stats.get(k, 0) + v
                    if use_cache:
                        manifest[entry_hash] = {"types": list(stats.keys())}
                except Exception as e:
                    errors += 1
                    log.debug("Worker exception for %s: %s", asset_name, e)
                processed += 1
                if processed % 50 == 0:
                    _progress(processed, total, skipped, errors, agg_stats, t0)

    _progress(processed, total, skipped, errors, agg_stats, t0, final=True)

    # Persist manifest for next run (delta + type cache)
    if use_cache and manifest:
        _save_manifest(output_root, manifest)
        log.info("Saved manifest (%d entries) → %s", len(manifest), _MANIFEST_NAME)

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
  %(prog)s --images-only                # only images, flat directory structure
  %(prog)s --images-only --no-cache    # images-only, ignore manifest cache
  %(prog)s --support-cards             # only support card images
  %(prog)s --chara                     # only character icons + portraits
  %(prog)s --images-only --format webp # images as high-quality WEBP (~3x smaller)
  %(prog)s --format webp --quality 100 # WEBP lossless (smaller than PNG)
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
        "--images-only", "-i",
        action="store_true",
        help="Only dump images (Texture2D/Sprite), collapse single-file dirs, "
             "flatten output to max 1 directory depth",
    )
    parser.add_argument(
        "--support-cards",
        action="store_true",
        help="Only dump support card images (supportcard/ assets)",
    )
    parser.add_argument(
        "--chara",
        action="store_true",
        help="Only dump character images (icons + portraits from chara/ assets)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Ignore the .dump_manifest.json cache (force full rescan)",
    )
    parser.add_argument(
        "--format",
        choices=["png", "webp"],
        default="png",
        help="Image output format (default: png). webp is much smaller with "
             "negligible quality loss at high --quality values",
    )
    parser.add_argument(
        "--quality", "-q",
        type=int,
        default=95,
        help="WEBP quality 1-100, or 100 for lossless (default: 95). "
             "Only used with --format webp",
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

    # Set image output format (used by _export_texture in worker processes)
    global _IMAGE_FORMAT, _IMAGE_QUALITY
    _IMAGE_FORMAT = args.format
    _IMAGE_QUALITY = max(1, min(100, args.quality))
    if _IMAGE_FORMAT == "webp":
        if _can_webp():
            mode = "lossless" if _IMAGE_QUALITY >= 100 else f"quality={_IMAGE_QUALITY}"
            log.info("Image format: WEBP (%s)", mode)
        else:
            log.warning("WEBP not available (missing Pillow plugin), falling back to PNG")
            _IMAGE_FORMAT = "png"

    type_filter = set(args.types) if args.types else None
    flat_depth = None
    collapse_singles = False
    name_filter = args.filter

    # Convenience presets — these imply --images-only behaviour
    if args.support_cards:
        type_filter = {"Texture2D", "Sprite"}
        flat_depth = 0          # everything flat in output_root
        collapse_singles = True
        if name_filter == "%":
            name_filter = "supportcard/%"
        # Default to webp for support cards (much smaller for web use)
        if args.format == "png" and "--format" not in sys.argv:
            _IMAGE_FORMAT = "webp"
            if _can_webp():
                mode = "lossless" if _IMAGE_QUALITY >= 100 else f"quality={_IMAGE_QUALITY}"
                log.info("Image format: WEBP (%s) [default for --support-cards]", mode)
            else:
                log.warning("WEBP not available, falling back to PNG")
                _IMAGE_FORMAT = "png"

    if args.chara:
        type_filter = {"Texture2D", "Sprite"}
        flat_depth = 0
        collapse_singles = True
        if name_filter == "%":
            name_filter = "chara/%"
        if args.format == "png" and "--format" not in sys.argv:
            _IMAGE_FORMAT = "webp"
            if _can_webp():
                mode = "lossless" if _IMAGE_QUALITY >= 100 else f"quality={_IMAGE_QUALITY}"
                log.info("Image format: WEBP (%s) [default for --chara]", mode)
            else:
                log.warning("WEBP not available, falling back to PNG")
                _IMAGE_FORMAT = "png"

    if args.images_only:
        type_filter = {"Texture2D", "Sprite"}
        flat_depth = 1
        collapse_singles = True

    stats = dump_all(
        game_dir=game_dir,
        output_root=output_root,
        name_filter=name_filter,
        type_filter=type_filter,
        dry_run=args.dry_run,
        skip_existing=not args.no_skip,
        workers=args.workers,
        flat_depth=flat_depth,
        collapse_singles=collapse_singles,
        use_cache=not args.no_cache,
    )

    if stats:
        log.info("Done! Assets written to %s", output_root.resolve())


if __name__ == "__main__":
    main()
