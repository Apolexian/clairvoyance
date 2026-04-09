"""
Master Database Lookup
──────────────────────
Opens the game's master.mdb (SQLite) and provides cached name lookups
for skill IDs, chara IDs, race instance IDs, card IDs, etc.

Users point to their own local master.mdb (everyone who has the game
installed already has it).  The path is persisted in config.json next
to the application.

The master.mdb uses a `text_data` table with (category, index) → text.
Known categories (sourced from UmaMusumeAPI ViewCreation.sql + hakuraku):
  4   = card names (full, "[Title] CharaName")
  5   = card titles ("[Title]")
  6   = character (uma) names
  23  = item names
  28  = race instance names
  32  = race names
  34  = race track names
  47  = skill names
  48  = skill descriptions
  76  = support card titles
  94  = main story episode titles
  111 = epithet / saddle names
  147 = scenario / training skill names
  181 = story names (general)
  189 = story event titles
  191 = story event episode titles
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

CATEGORY_CARD_NAME_FULL = 4  # "[Title] CharaName" via card_data.id
CATEGORY_CARD_TITLE = 5  # "[Title]" via card_data.id
CATEGORY_CHARA_NAME = 6  # character names via chara_data.id
CATEGORY_CHARA_CV = 7  # character voice actor via chara_data.id
CATEGORY_GACHA_TEXT = 13  # gacha banner text via gacha_data.id
CATEGORY_DRESS_NAME = 14  # dress names via dress_data.id
CATEGORY_SONG_NAME = 16  # song / live data via live_data.music_id
CATEGORY_ITEM_NAME = 23  # item names via item_data.id
CATEGORY_ITEM_COMMENT = 24  # item descriptions via item_data.id
CATEGORY_RACE_INSTANCE_NAME = 28  # race instance via race_instance.id
CATEGORY_RACE_NAME = 32  # race names via race.id
CATEGORY_RACE_TRACK_NAME = 34  # race track names via race_track.id
CATEGORY_SKILL_NAME = 47  # skill names via skill_data.id
CATEGORY_SKILL_DESC = 48  # skill descriptions via skill_data.id
CATEGORY_MOB_NAME = 59  # mob names via mob_data.mob_id
CATEGORY_GIFT_MESSAGE = 64  # gift messages via gift_message.id
CATEGORY_MISSION_NAME = 67  # mission names via mission_data.id
CATEGORY_LOGIN_BONUS_NAME = 70  # login bonus names via login_bonus_data.id
CATEGORY_SUPPORT_CARD_TITLE = 76  # support card titles via support_card_data.id
CATEGORY_MAIN_STORY_TITLE = 94  # main story episode titles via main_story_data.id
CATEGORY_EPITHET_NAME = 111  # epithet / saddle names
CATEGORY_PIECE_NAME = 113  # piece data (character shards) via piece_data.id
CATEGORY_SM_CHARA_GRADE = 121  # single mode chara grade via single_mode_chara_grade.id
CATEGORY_SCENARIO_NAME = 147  # scenario / training skill names (from hakuraku umdb)
CATEGORY_TS_SCORE_BONUS = 148  # team stadium score bonus via team_stadium_score_bonus.id
CATEGORY_SC_UNIQUE_EFFECT = 155  # support card unique effect names
CATEGORY_CHARA_RUNNING_STYLE = 159  # character running style (Front Runner, Late Surger, etc.)
CATEGORY_CHARA_GROUND_TYPE = 160  # character ground type (Turf, Dirt)
CATEGORY_CHARA_DISTANCE = 161  # character distance range (Medium-Long, Sprint-Medium, etc.)
CATEGORY_CHARA_BIO = 163  # character biography / self-introduction text
CATEGORY_CHARA_NAME_ALT = 170  # alternative character names (same as 6 for most)
CATEGORY_STORY_NAME = 181  # story names (legacy — may be empty in some DBs)
CATEGORY_HONOR_NAME = 130  # honor/epithet names (e.g. "Rainy Runner")
CATEGORY_HONOR_CONDITION = 131  # honor/epithet conditions
CATEGORY_SM_CONDITION = 142  # single mode conditions (e.g. "Night Owl")
CATEGORY_SM_CONDITION_DESC = 143  # single mode condition descriptions
CATEGORY_CHARA_CATCHPHRASE = 144  # character catchphrases
CATEGORY_NPC_NAME = 152  # NPC names (Akito, Kazuki, etc.)
CATEGORY_SM_ITEM_NAME = 177  # single mode item names (Hot Spring Ticket, etc.)
CATEGORY_SONG_DESC = 128  # song descriptions
CATEGORY_STORY_EVENT_TITLE = 189  # story event titles via story_event_data.story_event_id
CATEGORY_STORY_EVENT_MISSION = 190  # story event mission names
CATEGORY_STORY_EVENT_EPISODE = 191  # story event episode titles
CATEGORY_CHAMPIONS_CUP_NAME = 206  # Champions Meeting cup names (Taurus Cup, etc.)
CATEGORY_SM_SCENARIO_NAME = 119  # Single mode scenario names (URA Finale, Unity Cup, etc.)
CATEGORY_SM_SCENARIO_DESC = 120  # Single mode scenario descriptions
CATEGORY_SM_FREE_SHOP_ITEM = 225  # Single mode free shop item names
CATEGORY_WINS_SADDLE_NAME = 247  # Wins saddle condition names


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
    return names.get(cid, f"Character #{cid}")


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
    """Return the story/event name, trying multiple text_data categories."""
    if story_id is None:
        return "?"
    try:
        sid = int(story_id)
    except (ValueError, TypeError):
        return str(story_id)

    # Try categories in priority order — different story_id ranges map to different categories
    for cat in (
        CATEGORY_STORY_NAME,  # 181 — general story names
        CATEGORY_STORY_EVENT_TITLE,  # 189 — story event titles
        CATEGORY_STORY_EVENT_EPISODE,  # 191 — story event episode titles
        CATEGORY_MAIN_STORY_TITLE,  # 94  — main story episodes
    ):
        names = _load_text_data(cat)
        name = names.get(sid)
        if name:
            return name
    return str(sid)


def item_name(item_id: int | str | None) -> str:
    """Return the item name (text_data category 23 or 225), or a fallback."""
    if item_id is None:
        return "?"
    try:
        iid = int(item_id)
    except (ValueError, TypeError):
        return str(item_id)

    # Primary: category 23 (from UmaMusumeAPI)
    names = _load_text_data(CATEGORY_ITEM_NAME)
    if names.get(iid):
        return names[iid]
    # Fallback: category 225 (legacy)
    names225 = _load_text_data(225)
    return names225.get(iid, str(iid))


def card_name(card_id: int | str | None) -> str:
    """Return the card name (text_data category 4 '[Title] Name', or 5 '[Title]')."""
    if card_id is None:
        return "?"
    try:
        cid = int(card_id)
    except (ValueError, TypeError):
        return str(card_id)

    # Category 4: full name like "[Title] CharaName"
    names = _load_text_data(CATEGORY_CARD_NAME_FULL)
    name = names.get(cid)
    if name:
        return name
    # Category 5: just the title bracket
    names5 = _load_text_data(CATEGORY_CARD_TITLE)
    return names5.get(cid, str(cid))


def support_card_name(sc_id: int | str | None) -> str:
    """Return the support card title (text_data category 76)."""
    if sc_id is None:
        return "?"
    try:
        sid = int(sc_id)
    except (ValueError, TypeError):
        return str(sc_id)

    names = _load_text_data(CATEGORY_SUPPORT_CARD_TITLE)
    return names.get(sid, str(sid))


def race_name(race_id: int | str | None) -> str:
    """Return the race name (text_data category 32)."""
    if race_id is None:
        return "?"
    try:
        rid = int(race_id)
    except (ValueError, TypeError):
        return str(race_id)

    names = _load_text_data(CATEGORY_RACE_NAME)
    return names.get(rid, str(rid))


def race_track_name(track_id: int | str | None) -> str:
    """Return the race track name (text_data category 34)."""
    if track_id is None:
        return "?"
    try:
        tid = int(track_id)
    except (ValueError, TypeError):
        return str(track_id)

    names = _load_text_data(CATEGORY_RACE_TRACK_NAME)
    return names.get(tid, str(tid))


# ── Event / choice lookups ─────────────────────────────────────────────


@lru_cache(maxsize=1)
def _load_story_data() -> dict[int, dict]:
    """
    Load single_mode_story_data into {story_id: {card_id, support_card_id, ...}}.

    This tells us WHICH card/support card triggers a given event.
    """
    conn = _get_conn()
    if conn is None:
        return {}
    try:
        rows = conn.execute(
            "SELECT id, story_id, card_id, card_chara_id, "
            "       support_card_id, support_chara_id "
            "FROM single_mode_story_data"
        ).fetchall()
        result: dict[int, dict] = {}
        for r in rows:
            sid = r["story_id"]
            if sid and sid not in result:
                result[sid] = {
                    "story_data_id": r["id"],
                    "card_id": r["card_id"],
                    "card_chara_id": r["card_chara_id"],
                    "support_card_id": r["support_card_id"],
                    "support_chara_id": r["support_chara_id"],
                }
        return result
    except Exception as e:
        log.error("Failed to load single_mode_story_data: %s", e)
        return {}
    finally:
        conn.close()


@lru_cache(maxsize=1)
def _load_conclusion_set() -> dict[int, list[int]]:
    """
    Load single_mode_conclusion_set into {story_id: [conclusion_id, ...]}.

    Each story_id can map to multiple conclusion_ids — one per choice branch.
    The number of distinct conclusion_ids tells us how many outcome branches exist.
    """
    conn = _get_conn()
    if conn is None:
        return {}
    try:
        rows = conn.execute(
            "SELECT story_id, conclusion_id FROM single_mode_conclusion_set "
            "ORDER BY story_id, conclusion_id"
        ).fetchall()
        result: dict[int, list[int]] = {}
        for r in rows:
            sid = r["story_id"]
            cid = r["conclusion_id"]
            result.setdefault(sid, [])
            if cid not in result[sid]:
                result[sid].append(cid)
        return result
    except Exception as e:
        log.error("Failed to load single_mode_conclusion_set: %s", e)
        return {}
    finally:
        conn.close()


def event_info(story_id: int | str | None) -> dict | None:
    """
    Return enriched info about a story/event:
      - name: resolved event title
      - source_type: 'card' | 'support' | 'scenario' | 'unknown'
      - source_name: human-readable name of the triggering card/support
      - source_chara: character name if known
      - num_branches: how many outcome branches exist (from conclusion_set)
      - has_choice: True if num_branches > 1

    Returns None if story_id is invalid or not found.
    """
    if story_id is None:
        return None
    try:
        sid = int(story_id)
    except (ValueError, TypeError):
        return None

    name = story_name(sid)
    info: dict = {
        "story_id": sid,
        "name": name,
        "source_type": "unknown",
        "source_name": None,
        "source_chara": None,
        "num_branches": 1,
        "has_choice": False,
    }

    # Look up which card/support triggers this event
    story_data = _load_story_data()
    sd = story_data.get(sid)
    if sd:
        sc_id = sd.get("support_card_id")
        card_id_val = sd.get("card_id")
        sc_chara = sd.get("support_chara_id")
        card_chara = sd.get("card_chara_id")

        if sc_id and sc_id != 0:
            info["source_type"] = "support"
            info["source_name"] = support_card_name(sc_id)
            if sc_chara and sc_chara != 0:
                info["source_chara"] = chara_name(sc_chara)
        elif card_id_val and card_id_val != 0:
            info["source_type"] = "card"
            info["source_name"] = card_name(card_id_val)
            if card_chara and card_chara != 0:
                info["source_chara"] = chara_name(card_chara)
        else:
            # Scenario / generic events (no specific card)
            info["source_type"] = "scenario"

    # Look up number of branches from conclusion_set
    conclusions = _load_conclusion_set()
    branches = conclusions.get(sid, [])
    info["num_branches"] = max(len(branches), 1)
    info["has_choice"] = len(branches) > 1

    return info


def _clear_caches() -> None:
    """Clear all lru_cache'd data so a new DB path takes effect."""
    _load_text_data.cache_clear()
    _load_skill_data.cache_clear()
    _load_story_data.cache_clear()
    _load_conclusion_set.cache_clear()


# ── ID annotation for JSON payloads ───────────────────────────────────

# Maps JSON key names → (text_data_category, label_prefix).
# When we see one of these keys with an integer value, we look it up.
_ANNOTATABLE_KEYS: dict[str, tuple[int, str]] = {
    # Characters & cards
    "chara_id": (CATEGORY_CHARA_NAME, "chara"),
    "card_id": (CATEGORY_CARD_NAME_FULL, "card"),
    "support_card_id": (CATEGORY_SUPPORT_CARD_TITLE, "support"),
    # Skills
    "skill_id": (CATEGORY_SKILL_NAME, "skill"),
    # Races
    "race_instance_id": (CATEGORY_RACE_INSTANCE_NAME, "race"),
    "race_id": (CATEGORY_RACE_NAME, "race"),
    "race_track_id": (CATEGORY_RACE_TRACK_NAME, "track"),
    # Items
    "item_id": (CATEGORY_ITEM_NAME, "item"),
    # Stories & events
    "story_id": (CATEGORY_STORY_NAME, "story"),
    "story_event_id": (CATEGORY_STORY_EVENT_TITLE, "event"),
    # Other
    "music_id": (CATEGORY_SONG_NAME, "song"),
    "dress_id": (CATEGORY_DRESS_NAME, "dress"),
    "mob_id": (CATEGORY_MOB_NAME, "mob"),
    "mission_id": (CATEGORY_MISSION_NAME, "mission"),
    "piece_id": (CATEGORY_PIECE_NAME, "piece"),
    "nickname_id": (CATEGORY_HONOR_NAME, "honor"),
    "scenario_id": (CATEGORY_SM_SCENARIO_NAME, "scenario"),
    "login_bonus_id": (CATEGORY_LOGIN_BONUS_NAME, "login_bonus"),
}

# Keys that should try multiple categories in sequence (for IDs that span types)
_MULTI_CATEGORY_KEYS: dict[str, list[int]] = {
    "story_id": [
        CATEGORY_STORY_NAME,  # 181
        CATEGORY_STORY_EVENT_TITLE,  # 189
        CATEGORY_STORY_EVENT_EPISODE,  # 191
        CATEGORY_MAIN_STORY_TITLE,  # 94
    ],
    "card_id": [
        CATEGORY_CARD_NAME_FULL,  # 4  — "[Title] CharaName"
        CATEGORY_CARD_TITLE,  # 5  — "[Title]"
    ],
    "item_id": [
        CATEGORY_ITEM_NAME,  # 23
        225,  # legacy category
    ],
    "skill_id": [
        CATEGORY_SKILL_NAME,  # 47
    ],
}


def _resolve_multi_category(key: str, vid: int) -> str | None:
    """Try multiple text_data categories in order for a given key."""
    cats = _MULTI_CATEGORY_KEYS.get(key)
    if not cats:
        return None
    for cat in cats:
        names = _load_text_data(cat)
        name = names.get(vid)
        if name and name != str(vid):
            return name

    # For skill_id: also handle inherited unique skills (9xxxxx → 1xxxxx)
    if key == "skill_id" and 900000 <= vid < 1000000:
        names = _load_text_data(CATEGORY_SKILL_NAME)
        name = names.get(vid - 800000)
        if name:
            return name

    return None


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
                vid = int(v)
                resolved = None

                # Try multi-category lookup first (for keys that span types)
                if k in _MULTI_CATEGORY_KEYS:
                    resolved = _resolve_multi_category(k, vid)

                # Fall back to single-category lookup
                if not resolved:
                    cat, _label = _ANNOTATABLE_KEYS[k]
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
