"""
Master Database Lookup
──────────────────────
Opens the game's master.mdb (SQLite) and provides cached name lookups
for skill IDs, chara IDs, race instance IDs, etc.

Users point to their own local master.mdb (everyone who has the game
installed already has it).  The path is persisted in config.json next
to the application.

The master.mdb uses a `text_data` table with (category, index) → text.
Known categories:
  6   = character (uma) names
  47  = skill names
  28  = race instance names
  111 = epithet / saddle names
"""

from __future__ import annotations

import json
import logging
import sqlite3
import sys
from functools import lru_cache
from pathlib import Path

log = logging.getLogger(__name__)

# ── Config file location ───────────────────────────────────────────────

_FROZEN = getattr(sys, "frozen", False)
if _FROZEN:
    _APP_DIR = Path(sys.executable).resolve().parent
else:
    _APP_DIR = Path(__file__).resolve().parent.parent

_CONFIG_FILE = _APP_DIR / "config.json"


def _load_config() -> dict:
    """Load the config.json file, or return empty dict."""
    if _CONFIG_FILE.is_file():
        try:
            return json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_config(cfg: dict) -> None:
    """Write config.json."""
    _CONFIG_FILE.write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ── DB path management ─────────────────────────────────────────────────


def get_db_path() -> str | None:
    """Return the configured master.mdb path, or None if not set / invalid."""
    cfg = _load_config()
    path = cfg.get("master_db_path")
    if path and Path(path).is_file():
        return path
    return None


def set_db_path(path: str | None) -> bool:
    """
    Set (or clear) the master.mdb path.  Returns True if the file is valid.
    Clears all cached lookups so the new DB takes effect immediately.
    """
    cfg = _load_config()

    if path:
        p = Path(path)
        if not p.is_file():
            return False
        # Quick sanity check: can we open it as SQLite?
        try:
            conn = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
            conn.execute("SELECT 1 FROM text_data LIMIT 1")
            conn.close()
        except Exception as e:
            log.warning("master.mdb validation failed for %s: %s", path, e)
            return False
        cfg["master_db_path"] = str(p.resolve())
    else:
        cfg.pop("master_db_path", None)

    _save_config(cfg)
    _clear_caches()
    log.info("Master DB path set to: %s", cfg.get("master_db_path", "(cleared)"))
    return True


def _clear_caches() -> None:
    """Clear all lru_cache'd data so a new DB path takes effect."""
    _load_text_data.cache_clear()
    _load_skill_data.cache_clear()


def _get_conn() -> sqlite3.Connection | None:
    """Get a read-only connection to the master DB."""
    path = get_db_path()
    if path is None:
        return None
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        log.error("Failed to open master.mdb: %s", e)
        return None


# ── Bulk loaders (cached) ─────────────────────────────────────────────


@lru_cache(maxsize=8)
def _load_text_data(category: int) -> dict[int, str]:
    """Load all text_data rows for a given category into {index: text}."""
    conn = _get_conn()
    if conn is None:
        return {}
    try:
        rows = conn.execute(
            'SELECT "index", text FROM text_data WHERE category = ?',
            (category,),
        ).fetchall()
        result = {row["index"]: row["text"] for row in rows}
        log.debug("Loaded %d text_data entries for category %d", len(result), category)
        return result
    except Exception as e:
        log.error("Failed to query text_data category %d: %s", category, e)
        return {}
    finally:
        conn.close()


@lru_cache(maxsize=1)
def _load_skill_data() -> dict[int, dict]:
    """Load skill_data table for rarity/group info."""
    conn = _get_conn()
    if conn is None:
        return {}
    try:
        rows = conn.execute(
            "SELECT id, group_id, rarity, skill_category FROM skill_data"
        ).fetchall()
        return {row["id"]: dict(row) for row in rows}
    except Exception as e:
        log.error("Failed to query skill_data: %s", e)
        return {}
    finally:
        conn.close()


# ── Text data categories ───────────────────────────────────────────────

CATEGORY_CHARA_NAME = 6
CATEGORY_RACE_INSTANCE_NAME = 28
CATEGORY_SKILL_NAME = 47
CATEGORY_EPITHET_NAME = 111
CATEGORY_STORY_NAME = 181
CATEGORY_ITEM_NAME = 225


# ── Public lookup functions ────────────────────────────────────────────


def skill_name(skill_id: int | str | None) -> str:
    """Return the human-readable skill name, or a fallback string."""
    if skill_id is None:
        return "?"
    try:
        sid = int(skill_id)
    except (ValueError, TypeError):
        return str(skill_id)

    names = _load_text_data(CATEGORY_SKILL_NAME)
    name = names.get(sid)
    if name:
        return name

    # Handle inherited unique skills (9xxxxx → look up 1xxxxx)
    if 900000 <= sid < 1000000:
        name = names.get(sid - 800000)
        if name:
            return name

    return str(sid)


def chara_name(chara_id: int | str | None) -> str:
    """Return the character (uma) name, or a fallback string."""
    if chara_id is None:
        return "?"
    try:
        cid = int(chara_id)
    except (ValueError, TypeError):
        return str(chara_id)

    names = _load_text_data(CATEGORY_CHARA_NAME)
    return names.get(cid, f"chara:{cid}")


def race_instance_name(race_instance_id: int | str | None) -> str:
    """Return the race instance name, or a fallback string."""
    if race_instance_id is None:
        return "?"
    try:
        rid = int(race_instance_id)
    except (ValueError, TypeError):
        return str(race_instance_id)

    names = _load_text_data(CATEGORY_RACE_INSTANCE_NAME)
    return names.get(rid, str(rid))


def story_name(story_id: int | str | None) -> str:
    """Return the story/event name (text_data category 181), or a fallback."""
    if story_id is None:
        return "?"
    try:
        sid = int(story_id)
    except (ValueError, TypeError):
        return str(story_id)

    names = _load_text_data(CATEGORY_STORY_NAME)
    return names.get(sid, str(sid))


def item_name(item_id: int | str | None) -> str:
    """Return the item name (text_data category 225), or a fallback."""
    if item_id is None:
        return "?"
    try:
        iid = int(item_id)
    except (ValueError, TypeError):
        return str(item_id)

    names = _load_text_data(CATEGORY_ITEM_NAME)
    return names.get(iid, str(iid))


# ── ID annotation for JSON payloads ───────────────────────────────────

# Maps JSON key names → (text_data_category, label_prefix).
# When we see one of these keys with an integer value, we look it up.
_ANNOTATABLE_KEYS: dict[str, tuple[int, str]] = {
    "story_id": (CATEGORY_STORY_NAME, "story"),
    "chara_id": (CATEGORY_CHARA_NAME, "chara"),
    "skill_id": (CATEGORY_SKILL_NAME, "skill"),
    "race_instance_id": (CATEGORY_RACE_INSTANCE_NAME, "race"),
    "item_id": (CATEGORY_ITEM_NAME, "item"),
}


def annotate_ids(obj: object, _path: str = "") -> dict[str, str]:
    """
    Recursively walk a JSON-like structure and build annotations for known ID fields.

    Returns a dict of {json_path: "human-readable label"} for every
    recognised ID key that resolves to a name in the master DB.

    Example return:
      {"data.unchecked_event_array.0.story_id": "ゴルシの秘密特訓",
       "data.chara_info.chara_id": "Special Week"}
    """
    if not is_available():
        return {}

    annotations: dict[str, str] = {}

    if isinstance(obj, dict):
        for k, v in obj.items():
            child_path = f"{_path}.{k}" if _path else k

            # Check if this key is annotatable and the value is an int
            if k in _ANNOTATABLE_KEYS and isinstance(v, (int, float)) and v != 0:
                cat, _label = _ANNOTATABLE_KEYS[k]
                vid = int(v)
                names = _load_text_data(cat)
                resolved = names.get(vid)
                if resolved and resolved != str(vid):
                    annotations[child_path] = resolved

            # Recurse into the value
            annotations.update(annotate_ids(v, child_path))

    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            child_path = f"{_path}.{i}"
            annotations.update(annotate_ids(item, child_path))

    return annotations


def is_available() -> bool:
    """Check if the master DB is accessible."""
    return get_db_path() is not None


def list_tables() -> list[str]:
    """List all non-empty tables in the master DB."""
    conn = _get_conn()
    if conn is None:
        return []
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        return [row["name"] for row in rows]
    except Exception:
        return []
    finally:
        conn.close()


def get_table_schema(table: str) -> list[dict]:
    """Return column info for a table via PRAGMA table_info."""
    conn = _get_conn()
    if conn is None:
        return []
    try:
        rows = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
        return [{"name": r["name"], "type": r["type"], "pk": bool(r["pk"])} for r in rows]
    except Exception:
        return []
    finally:
        conn.close()


def execute_query(sql: str, limit: int = 1000) -> dict:
    """
    Execute a read-only SQL query and return results.

    Returns:
        {columns: list[str], rows: list[list], row_count: int, truncated: bool, error: str|None}
    """
    conn = _get_conn()
    if conn is None:
        return {
            "columns": [],
            "rows": [],
            "row_count": 0,
            "truncated": False,
            "error": "Master DB not configured — set the path in the Record panel.",
        }

    # Block any write statements
    stripped = sql.strip().upper()
    for kw in (
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "ALTER",
        "CREATE",
        "ATTACH",
        "DETACH",
        "REPLACE",
    ):
        if stripped.startswith(kw):
            return {
                "columns": [],
                "rows": [],
                "row_count": 0,
                "truncated": False,
                "error": f"Write operations not allowed ({kw}).",
            }

    try:
        cursor = conn.execute(sql)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = []
        truncated = False
        for i, row in enumerate(cursor):
            if i >= limit:
                truncated = True
                break
            rows.append(list(row))
        return {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "truncated": truncated,
            "error": None,
        }
    except Exception as e:
        return {"columns": [], "rows": [], "row_count": 0, "truncated": False, "error": str(e)}
    finally:
        conn.close()
