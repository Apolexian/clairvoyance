# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "flask",
#     "pywebview",
# ]
# ///

"""
Clairvoyance GUI — Native desktop session explorer and race replay.

Usage:
  uv run gui.py                # launch native window
  uv run gui.py --browser      # fallback: open in browser instead

Double-click gui.py to launch (if uv is on PATH).
"""

from __future__ import annotations

import argparse
import contextlib
import json
import logging
import os
import re
import subprocess
import sys
import threading
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from lib.master_db import (
    card_name,
    chara_name,
    event_id_to_story_id,
    event_info,
    event_name_by_event_id,
    execute_query,
    get_db_path,
    get_table_schema,
    item_name,
    race_instance_name,
    race_name,
    race_track_name,
    scenario_name,
    set_db_path,
    skill_name,
    story_name,
    support_card_name,
)
from lib.master_db import (
    is_available as master_db_available,
)
from lib.master_db import (
    list_tables as master_list_tables,
)
from lib.session_reader import (
    build_session_summaries,
    get_network_event_detail,
    get_network_events,
    get_race_replay_data,
    get_races,
    get_session,
    get_timeline,
    list_sessions,
)

# ── Setup ──────────────────────────────────────────────────────────────

FROZEN = getattr(sys, "frozen", False)

if FROZEN:
    # PyInstaller bundle: exe lives in dist/clairvoyance/
    # Data files (templates, static, js) are in _MEIPASS
    _BUNDLE_DIR = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    _APP_DIR = Path(sys.executable).resolve().parent  # where the .exe lives
    SCRIPT_DIR = _APP_DIR  # sessions/ and discovery/ live next to the .exe
else:
    _BUNDLE_DIR = Path(__file__).resolve().parent
    _APP_DIR = _BUNDLE_DIR
    SCRIPT_DIR = _BUNDLE_DIR


def _tool_cmd(tool: str, *args: str) -> list[str]:
    """
    Build the command to run a subprocess tool.

    In frozen mode: call the bundled .exe  (e.g. collect.exe --label gui)
    In dev mode:    call python script.py  (e.g. python collect.py --label gui)
    """
    if FROZEN:
        exe = _APP_DIR / f"{tool}.exe"
        log.debug("Looking for tool: %s (APP_DIR=%s)", exe, _APP_DIR)
        if not exe.exists():
            # List what IS in the directory so the log shows the real layout
            siblings = [p.name for p in _APP_DIR.iterdir()] if _APP_DIR.is_dir() else []
            log.error(
                "Tool not found: %s — APP_DIR contents: %s",
                exe,
                siblings,
            )
            raise FileNotFoundError(f"Bundled tool not found: {exe}")
        return [str(exe), *args]
    return [sys.executable, str(SCRIPT_DIR / f"{tool}.py"), *args]


app = Flask(
    __name__,
    template_folder=str(_BUNDLE_DIR / "templates"),
    static_folder=str(_BUNDLE_DIR / "static"),
)
app.config["JSON_SORT_KEYS"] = False

# ── Master DB template filters ─────────────────────────────────────────
app.jinja_env.filters["skill_name"] = skill_name
app.jinja_env.filters["chara_name"] = chara_name
app.jinja_env.filters["race_name"] = race_instance_name
app.jinja_env.filters["race_base_name"] = race_name
app.jinja_env.filters["story_name"] = story_name
app.jinja_env.filters["item_name"] = item_name
app.jinja_env.filters["card_name"] = card_name
app.jinja_env.filters["support_card_name"] = support_card_name
app.jinja_env.filters["race_track_name"] = race_track_name

# ── Uma portrait lookup ────────────────────────────────────────────────
# Scan static/uma/ once and build a {charaId: {cardId: filename}} map
_UMA_IMAGES: dict[int, dict[int, str]] = {}


def _scan_uma_images():
    uma_dir = Path(app.static_folder) / "uma"
    if not uma_dir.is_dir():
        return
    for f in uma_dir.iterdir():
        if f.suffix != ".webp":
            continue
        # chara_stand_{charaId}_{cardId}.webp
        parts = f.stem.split("_")
        if len(parts) >= 4 and parts[0] == "chara" and parts[1] == "stand":
            try:
                cid = int(parts[2])
                card = int(parts[3])
                _UMA_IMAGES.setdefault(cid, {})[card] = f.name
            except ValueError:
                continue


_scan_uma_images()


def uma_image_url(chara_id, card_id=None):
    """Return the URL for an uma portrait, or empty string if not found."""
    try:
        cid = int(chara_id) if chara_id else None
    except (ValueError, TypeError):
        return ""
    if cid is None or cid not in _UMA_IMAGES:
        return ""
    cards = _UMA_IMAGES[cid]
    # Prefer exact card_id match, then fall back to any card for this chara
    if card_id:
        try:
            card_id = int(card_id)
        except (ValueError, TypeError):
            card_id = None
    if card_id and card_id in cards:
        return f"/static/uma/{cards[card_id]}"
    # Fallback: first available
    first = next(iter(cards.values()))
    return f"/static/uma/{first}"


app.jinja_env.filters["uma_image"] = uma_image_url
app.jinja_env.globals["uma_image"] = uma_image_url

# ── Support card image lookup ──────────────────────────────────────────
# Scan static/cards/ for extracted support card webp images
_SC_IMAGES: dict[int, str] = {}


def _scan_support_card_images():
    cards_dir = Path(app.static_folder) / "cards"
    if not cards_dir.is_dir():
        return
    for f in cards_dir.iterdir():
        if f.suffix != ".webp":
            continue
        # support_card_{id}.webp
        m = re.match(r"support_card_(\d+)\.webp$", f.name)
        if m:
            _SC_IMAGES[int(m.group(1))] = f.name


_scan_support_card_images()


def support_card_image_url(sc_id) -> str:
    """Return the URL for a support card image, or empty string if not found."""
    try:
        sid = int(sc_id) if sc_id else None
    except (ValueError, TypeError):
        return ""
    if sid and sid in _SC_IMAGES:
        return f"/static/cards/{_SC_IMAGES[sid]}"
    return ""


app.jinja_env.filters["support_card_image"] = support_card_image_url
app.jinja_env.globals["support_card_image"] = support_card_image_url

LOG_FILE = SCRIPT_DIR / "gui.log"

log = logging.getLogger("clairvoyance.gui")
log.setLevel(logging.DEBUG)

# File handler — always active, captures everything (persists across runs)
_fh = logging.FileHandler(str(LOG_FILE), mode="a", encoding="utf-8")
_fh.setLevel(logging.DEBUG)
_fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s"))
log.addHandler(_fh)

# Console handler — useful in dev mode (uv run gui.py)
_ch = logging.StreamHandler(sys.stdout)
_ch.setLevel(logging.INFO)
_ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
log.addHandler(_ch)

log.info("Clairvoyance GUI starting - log file: %s", LOG_FILE)


@app.errorhandler(Exception)
def _handle_exception(exc):
    """Guarantee JSON responses for /api/ routes — never return HTML error pages."""
    if request.path.startswith("/api/"):
        code = exc.code if isinstance(exc, HTTPException) else 500
        log.exception("API error on %s: %s", request.path, exc)
        return jsonify({"error": str(exc)}), code
    # Non-API routes: let Flask handle normally (HTML pages)
    if isinstance(exc, HTTPException):
        return exc
    log.exception("Unhandled exception: %s", exc)
    raise exc


# ── Recording state ────────────────────────────────────────────────────

_recorder_process: subprocess.Popen | None = None
_recorder_log: list[str] = []
_recorder_lock = threading.Lock()


def _stream_recorder_output(proc: subprocess.Popen) -> None:
    """Background thread to capture recorder stdout."""
    global _recorder_process
    try:
        for line in iter(proc.stdout.readline, ""):
            if not line:
                break
            with _recorder_lock:
                _recorder_log.append(line.rstrip("\n"))
                if len(_recorder_log) > 500:
                    _recorder_log.pop(0)
    except Exception:
        pass
    finally:
        proc.wait()
        log.info("Recorder process exited with code %d", proc.returncode)
        with _recorder_lock:
            _recorder_log.append(f"[recorder] Process exited with code {proc.returncode}")
            if _recorder_process is proc:
                _recorder_process = None


# ── Routes: Pages ──────────────────────────────────────────────────────


@app.route("/")
def home():
    return render_template(
        "home.html",
        sessions=list_sessions(),
        master_db_ok=master_db_available(),
    )


@app.route("/setup")
def setup_page():
    return render_template("setup.html")


@app.route("/masterdata")
def masterdata():
    return render_template("masterdata.html", db_available=master_db_available())


def _enrich_career_summary(summary: dict) -> None:
    """Resolve IDs to human-readable names and images in a career summary (in-place)."""
    # ── Character info ──
    if summary.get("chara_id") not in (None, 0, ""):
        summary["chara_name"] = chara_name(summary["chara_id"])
        summary["chara_image"] = uma_image_url(summary["chara_id"], summary.get("card_id"))
    if summary.get("card_id") not in (None, 0, ""):
        full_card = card_name(summary["card_id"])
        m = re.match(r"^\[(.+?)\]\s*(.+)$", full_card)
        if m:
            summary["outfit_title"] = m.group(1)
            if not summary.get("chara_name") or summary["chara_name"].startswith("Character #"):
                summary["chara_name"] = m.group(2)
        else:
            if not summary.get("chara_name") or summary["chara_name"].startswith("Character #"):
                summary["chara_name"] = full_card
    if summary.get("scenario_id") not in (None, 0, ""):
        summary["scenario_name"] = scenario_name(summary["scenario_id"])

    # ── Support cards ──
    for sc_id in summary.get("support_card_ids", []):
        summary.setdefault("support_card_names", []).append(
            {
                "id": sc_id,
                "name": support_card_name(sc_id),
                "image": support_card_image_url(sc_id),
            }
        )
    if summary.get("friend_support_card_id"):
        summary["friend_support_card_name"] = support_card_name(summary["friend_support_card_id"])
        summary["friend_support_card_image"] = support_card_image_url(
            summary["friend_support_card_id"]
        )

    # ── Training partner distribution ──
    _CMD_LABELS = {"101": "Speed", "102": "Stamina", "103": "Power", "105": "Guts", "106": "Wiz"}
    raw_dist = summary.get("training_partner_dist", {})
    if raw_dist:
        enriched_dist = []
        for sc_id_str, cmd_counts in raw_dist.items():
            sc_id = int(sc_id_str)
            sc_nm = support_card_name(sc_id)
            total = sum(cmd_counts.values())
            breakdown = {}
            for cmd_id_str, count in cmd_counts.items():
                label = _CMD_LABELS.get(cmd_id_str, f"Cmd {cmd_id_str}")
                breakdown[label] = count
            is_friend = sc_id == summary.get("friend_support_card_id")
            enriched_dist.append(
                {
                    "id": sc_id,
                    "name": sc_nm,
                    "image": support_card_image_url(sc_id),
                    "total": total,
                    "breakdown": breakdown,
                    "is_friend": is_friend,
                }
            )
        enriched_dist.sort(key=lambda x: x["total"], reverse=True)
        summary["training_partner_dist_enriched"] = enriched_dist
        summary["training_partner_turns_seen"] = len(summary.get("stats_history", []))

    # ── Training actions ──
    _CMD_LABELS_INT = {101: "Speed", 102: "Stamina", 103: "Power", 105: "Guts", 106: "Wiz"}
    for ta in summary.get("training_actions", []):
        cid = ta.get("command_id")
        if cid:
            ta["command_name"] = _CMD_LABELS_INT.get(cid, f"Cmd {cid}")

    # ── Skills & races ──
    for sk in summary.get("skills_acquired", []):
        sk["name"] = skill_name(sk["skill_id"])
    for sk in summary.get("skill_tips", []):
        sk["name"] = skill_name(sk["skill_id"])
    for rr in summary.get("race_results", []):
        if rr.get("race_instance_id"):
            rr["race_name"] = race_instance_name(rr["race_instance_id"])

    # ── Events ──
    for ev in summary.get("events_seen", []):
        sid = ev.get("story_id")
        if sid:
            ei = event_info(sid)
            if ei:
                ev["name"] = ei["name"]
                ev["source_type"] = ei["source_type"]
                ev["source_name"] = ei["source_name"]
                ev["source_chara"] = ei["source_chara"]
                ev["has_choice"] = ei["has_choice"]
                ev["num_branches"] = ei["num_branches"]
                ev["choice_texts"] = ei.get("choice_texts")
            else:
                ev["name"] = story_name(sid)

    for ec in summary.get("event_choices", []):
        sid = ec.get("story_id")
        eid = ec.get("event_id")
        if not sid and eid:
            sid = event_id_to_story_id(eid)
            if sid:
                ec["story_id"] = sid
        if sid:
            ei = event_info(sid)
            if ei:
                ec["name"] = ei["name"]
                ec["source_type"] = ei["source_type"]
                ec["source_name"] = ei["source_name"]
                ec["source_chara"] = ei["source_chara"]
                ec["num_branches"] = ei["num_branches"]
                ec["choice_texts"] = ei.get("choice_texts")
            else:
                ec["name"] = story_name(sid)
        elif eid:
            ec["name"] = event_name_by_event_id(eid)

    # ── Merge events_seen + event_choices ──
    _choices_by_sid: dict[int, dict] = {}
    for ec in summary.get("event_choices", []):
        sid = ec.get("story_id")
        if sid:
            _choices_by_sid[sid] = ec

    merged: list[dict] = []
    _seen_sids: set[int] = set()
    for ev in summary.get("events_seen", []):
        sid = ev.get("story_id")
        entry = dict(ev)
        if sid and sid in _choices_by_sid:
            ch = _choices_by_sid[sid]
            entry["choice_number"] = ch.get("choice_number")
            entry["stat_deltas"] = ch.get("stat_deltas")
            if ch.get("choice_texts"):
                entry["choice_texts"] = ch["choice_texts"]
        if sid:
            _seen_sids.add(sid)
        merged.append(entry)

    for ec in summary.get("event_choices", []):
        sid = ec.get("story_id")
        if sid and sid not in _seen_sids:
            merged.append(ec)
            _seen_sids.add(sid)

    summary["events_merged"] = merged

    # ── Compute a compact header label for multi-career display ──
    stats = summary.get("latest_stats", {})
    if stats:
        total = (
            stats.get("speed", 0)
            + stats.get("stamina", 0)
            + stats.get("power", 0)
            + stats.get("guts", 0)
            + stats.get("wiz", 0)
        )
        summary["_stats_total"] = total
        summary["_turn_range"] = f"T1-T{stats.get('turn', '?')}"
    else:
        summary["_stats_total"] = 0
        summary["_turn_range"] = ""


@app.route("/session/<name>")
def session_detail(name: str):
    session = get_session(name)
    if not session:
        return "Session not found", 404

    careers, other_races = build_session_summaries(name)
    for career in careers:
        _enrich_career_summary(career)

    net = get_network_events(name)
    races = get_races(name)

    # Backfill race_results from detected races for single-career sessions
    # (multi-career: each career already has its own race_results from the parser)
    if len(careers) == 1 and not careers[0].get("race_results") and races:
        summary = careers[0]
        player_cid = summary.get("chara_id")
        for race in races:
            meta = race.get("race_metadata", {})
            rid = meta.get("race_instance_id")

            result_order = None
            entry_count = None
            horse_list = race.get("horse_summaries", [])
            if horse_list:
                entry_count = len(horse_list)
                # Match by career's chara_id first, then fall back to horse_index 0
                player = None
                if player_cid:
                    player = next(
                        (h for h in horse_list if h.get("chara_id") == player_cid),
                        None,
                    )
                if player is None:
                    player = next(
                        (h for h in horse_list if h.get("horse_index") == 0),
                        horse_list[0] if horse_list else None,
                    )
                if player:
                    result_order = player.get("finish_order") or player.get("estimated_rank")

            rr = {
                "race_instance_id": rid,
                "program_id": meta.get("program_id"),
                "result_order": result_order,
                "entry_count": entry_count,
                "turn": 0,
                "api": race.get("api", ""),
            }
            if rid:
                rr["race_name"] = race_instance_name(rid)
            else:
                rr["race_name"] = race.get("_race_label", f"Race {race.get('_race_index', '?')}")
            summary["race_results"].append(rr)

    # Primary summary = last career (for backward compat with parts of the template)
    summary = careers[-1] if careers else {}

    return render_template(
        "session.html",
        session=session,
        careers=careers,
        other_races=other_races,
        races=races,
        network=net["events"],
        network_stats=net["stats"],
        summary=summary,
    )


@app.route("/session/<name>/race/<int:race_idx>")
def race_detail(name: str, race_idx: int):
    session = get_session(name)
    if not session:
        return "Session not found", 404
    races = get_races(name)
    race = next((r for r in races if r.get("_race_index") == race_idx), None)
    if not race:
        return "Race not found", 404
    return render_template("race.html", session=session, race=race, race_idx=race_idx)


@app.route("/session/<name>/race/<int:race_idx>/replay")
def race_replay(name: str, race_idx: int):
    session = get_session(name)
    if not session:
        return "Session not found", 404
    replay = get_race_replay_data(name, race_idx)
    if not replay:
        return "Race not found", 404
    # Enrich skill activations with resolved names from master DB
    for sk in replay.get("skills", []):
        sid = sk.get("skill_id")
        if sid:
            sk["skill_label"] = skill_name(sid)
    # Enrich horse summaries with image URLs and names for the replay canvas
    for hs in replay.get("horse_summaries", []):
        cid = hs.get("chara_id")
        card = hs.get("card_id")
        if cid:
            hs["_image_url"] = uma_image_url(cid, card)
            hs["_name"] = chara_name(cid)
    # Attach course profile for slope/corner visualization
    from lib.course_data import build_course_profile, guess_course_id

    meta = replay.get("race_metadata", {})
    total_d = replay.get("total_distance", 0)
    cid = guess_course_id(
        race_distance=int(total_d),
        program_id=meta.get("program_id"),
        race_instance_id=meta.get("race_instance_id"),
    )
    if cid:
        profile = build_course_profile(cid)
        if profile:
            replay["course_profile"] = profile
    return render_template("replay.html", session=session, replay=replay, race_idx=race_idx)


# ── Routes: API ────────────────────────────────────────────────────────


@app.route("/api/sessions")
def api_sessions():
    return jsonify(
        [
            {
                "name": s.name,
                "label": s.label,
                "created": s.created,
                "counts": s.counts,
                "total_records": s.total_records,
                "modules": s.modules,
            }
            for s in list_sessions()
        ]
    )


@app.route("/api/session/<name>/timeline")
def api_timeline(name: str):
    return jsonify(get_timeline(name))


@app.route("/api/session/<name>/races")
def api_races(name: str):
    return jsonify(
        [
            {
                "_race_index": r.get("_race_index"),
                "_race_label": r.get("_race_label"),
                "_source": r.get("_source"),
                "_ts": r.get("_ts"),
                "num_horses": r.get("num_horses") or r.get("horse_count"),
                "total_frames": r.get("total_frames"),
            }
            for r in get_races(name)
        ]
    )


@app.route("/api/session/<name>/race/<int:race_idx>")
def api_race_detail(name: str, race_idx: int):
    race = next((r for r in get_races(name) if r.get("_race_index") == race_idx), None)
    return jsonify(race) if race else (jsonify({"error": "Race not found"}), 404)


@app.route("/api/session/<name>/race/<int:race_idx>/replay")
def api_race_replay(name: str, race_idx: int):
    replay = get_race_replay_data(name, race_idx)
    return jsonify(replay) if replay else (jsonify({"error": "Race not found"}), 404)


@app.route("/api/session/<name>/network")
def api_network(name: str):
    return jsonify(get_network_events(name))


@app.route("/api/session/<name>/network/<int:idx>")
def api_network_detail(name: str, idx: int):
    detail = get_network_event_detail(name, idx)
    return jsonify(detail) if detail else (jsonify({"error": "Event not found"}), 404)


# ── Routes: Settings ───────────────────────────────────────────────────


@app.route("/api/settings/master_db")
def api_master_db_status():
    """Return current master DB path and availability."""
    return jsonify(
        {
            "available": master_db_available(),
            "path": get_db_path(),
        }
    )


@app.route("/api/settings/master_db", methods=["POST"])
def api_master_db_set():
    """Set or clear the master DB path."""
    data = request.get_json(silent=True) or {}
    path = data.get("path")

    if path is None or path == "":
        set_db_path(None)
        return jsonify({"ok": True, "available": False, "path": None})

    ok = set_db_path(path)
    if not ok:
        return jsonify(
            {
                "ok": False,
                "error": "Invalid file — not a valid master.mdb (must be SQLite with a text_data table)",
            }
        ), 400

    return jsonify({"ok": True, "available": True, "path": get_db_path()})


# ── Routes: Master Data Browser ────────────────────────────────────────


@app.route("/api/masterdata/tables")
def api_masterdata_tables():
    """List all tables and their column schemas."""
    tables = master_list_tables()
    result = []
    for t in tables:
        schema = get_table_schema(t)
        result.append({"name": t, "columns": schema})
    return jsonify(result)


@app.route("/api/masterdata/table_counts")
def api_masterdata_table_counts():
    """Return row count for each table."""
    from lib.master_db import execute_query as _eq

    tables = master_list_tables()
    counts = {}
    for t in tables:
        res = _eq(f'SELECT COUNT(*) as n FROM "{t}"', limit=1)
        if res.get("rows"):
            counts[t] = res["rows"][0][0]
        else:
            counts[t] = 0
    return jsonify(counts)


@app.route("/api/masterdata/text_categories")
def api_masterdata_text_categories():
    """Return all text_data categories with sample entries."""
    from lib.master_db import execute_query as _eq

    # Get all categories and their counts
    res = _eq(
        "SELECT category, COUNT(*) as cnt FROM text_data GROUP BY category ORDER BY category",
        limit=5000,
    )
    if res.get("error") or not res.get("rows"):
        return jsonify([])

    categories = []
    for row in res["rows"]:
        cat_id = row[0]
        count = row[1]
        # Get a few sample entries for this category
        samples_res = _eq(
            f'SELECT "index", text FROM text_data WHERE category = {cat_id} ORDER BY "index" LIMIT 3',
            limit=3,
        )
        samples = []
        if samples_res.get("rows"):
            for sr in samples_res["rows"]:
                text = sr[1] or ""
                if len(text) > 80:
                    text = text[:80] + "…"
                samples.append({"index": sr[0], "text": text})
        categories.append({"id": cat_id, "count": count, "samples": samples})
    return jsonify(categories)


@app.route("/api/masterdata/query", methods=["POST"])
def api_masterdata_query():
    """Execute a read-only SQL query."""
    data = request.get_json(silent=True) or {}
    sql = data.get("sql", "").strip()
    if not sql:
        return jsonify({"error": "No SQL provided"}), 400
    limit = min(int(data.get("limit", 1000)), 5000)
    return jsonify(execute_query(sql, limit=limit))


# ── Routes: Setup (discover + analyse) ─────────────────────────────────

DISCOVERY_DIR = SCRIPT_DIR / "discovery"


@app.route("/api/setup/status")
def api_setup_status():
    """Check which pipeline artifacts exist."""
    class_dump = DISCOVERY_DIR / "class_dump.json"
    interesting = DISCOVERY_DIR / "interesting.json"
    analysis = DISCOVERY_DIR / "analysis.md"

    return jsonify(
        {
            "class_dump": class_dump.exists(),
            "interesting": interesting.exists(),
            "analysis": analysis.exists(),
            "ready": interesting.exists(),  # the key gate for recording
            "running": _setup_running,
            "log": _setup_log[-80:],
        }
    )


_setup_process: subprocess.Popen | None = None
_setup_running: bool = False
_setup_log: list[str] = []
_setup_lock = threading.Lock()


def _stream_output(proc: subprocess.Popen, log_list: list[str], lock: threading.Lock) -> None:
    """Read subprocess stdout line-by-line into a shared log list. Blocks until EOF."""
    try:
        for line in iter(proc.stdout.readline, ""):
            if not line:
                break
            with lock:
                log_list.append(line.rstrip("\n"))
                if len(log_list) > 500:
                    log_list.pop(0)
    except Exception:
        pass
    finally:
        proc.wait()
        log.info("Process exited with code %d (pid %d)", proc.returncode, proc.pid)
        with lock:
            log_list.append(f"[setup] Exited with code {proc.returncode}")


@app.route("/api/setup/run", methods=["POST"])
def api_setup_run():
    """Run the full discover -> analyse pipeline."""
    global _setup_process, _setup_running

    with _setup_lock:
        if _setup_running:
            return jsonify({"error": "Setup already running"}), 400

    try:
        data = request.get_json(silent=True) or {}
        skip_discover = data.get("skip_discover", False)

        # Build the command
        if skip_discover and (DISCOVERY_DIR / "class_dump.json").exists():
            # Only run analyse
            cmd = _tool_cmd("analyse")
        else:
            # Full discover (--all scans the entire Gallop namespace)
            cmd = _tool_cmd("discover", "--all")

        with _setup_lock:
            _setup_log.clear()
            _setup_log.append(f"[setup] Starting: {' '.join(cmd)}")
            if not skip_discover:
                _setup_log.append("[setup] Phase 1: Scanning game binary (this takes a while)...")
            _setup_running = True

        kwargs: dict = dict(
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(SCRIPT_DIR),
        )
        if os.name == "nt":
            kwargs["creationflags"] = (
                subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
            )
        proc = subprocess.Popen(cmd, **kwargs)
        with _setup_lock:
            _setup_process = proc
        threading.Thread(
            target=_run_setup_pipeline, args=(proc, skip_discover), daemon=True
        ).start()
        log.info("Setup started (pid=%d): %s", proc.pid, " ".join(cmd))
        return jsonify({"status": "started", "pid": proc.pid})
    except Exception as e:
        log.exception("api_setup_run failed")
        return jsonify({"error": str(e)}), 500


def _run_setup_pipeline(proc: subprocess.Popen, skip_discover: bool) -> None:
    """
    Stream output from discover, then chain analyse if discover succeeds.
    Sets _setup_running = False when the entire pipeline is done.
    """
    global _setup_process, _setup_running
    try:
        # Stream output from first command
        _stream_output(proc, _setup_log, _setup_lock)

        # If we just ran discover (not skip), now run analyse
        if not skip_discover and proc.returncode == 0:
            with _setup_lock:
                _setup_log.append("")
                _setup_log.append("[setup] Phase 2: Analysing class dump...")
            try:
                analyse_cmd = _tool_cmd("analyse")
                kwargs: dict = dict(
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    cwd=str(SCRIPT_DIR),
                )
                if os.name == "nt":
                    kwargs["creationflags"] = (
                        subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
                    )
                analyse_proc = subprocess.Popen(analyse_cmd, **kwargs)
                with _setup_lock:
                    _setup_process = analyse_proc
                _stream_output(analyse_proc, _setup_log, _setup_lock)
                if analyse_proc.returncode == 0:
                    with _setup_lock:
                        _setup_log.append("[setup] Setup complete - ready to record!")
                else:
                    with _setup_lock:
                        _setup_log.append("[setup] Analyse failed.")
            except Exception as e:
                with _setup_lock:
                    _setup_log.append(f"[setup] Analyse error: {e}")
        elif skip_discover and proc.returncode == 0:
            with _setup_lock:
                _setup_log.append("[setup] Analysis complete - ready to record!")
        else:
            with _setup_lock:
                _setup_log.append("[setup] Discovery failed - check that the game is running.")

        # Verify the key output file actually exists
        ij = DISCOVERY_DIR / "interesting.json"
        if ij.exists():
            log.info("Setup pipeline done - interesting.json confirmed at %s", ij)
        else:
            log.warning("Setup pipeline done but interesting.json NOT found at %s", ij)
            with _setup_lock:
                _setup_log.append("[setup] WARNING: interesting.json not found after setup.")
    finally:
        # Always clear the running flag when the pipeline ends
        with _setup_lock:
            _setup_running = False
            _setup_process = None


# ── Routes: Setup Wizard (guided first-run flow) ──────────────────────

# pywebview window reference — set in main() when running in native mode
_webview_window = None

# Story extraction state
_extraction_running: bool = False
_extraction_progress: dict = {
    "processed": 0,
    "total": 0,
    "found": 0,
    "skipped": 0,
    "error": None,
    "status": "idle",
}
_extraction_lock = threading.Lock()


@app.route("/api/setup/wizard_status")
def api_wizard_status():
    """Return current wizard state: is master DB configured? Do story choices exist?"""
    story_choices_file = _APP_DIR / "story_choices.json"
    db_path = get_db_path()
    game_data_dir = None

    # Check story_choices has actual content (not just an empty file / empty dict)
    story_choices_loaded = False
    if story_choices_file.is_file():
        try:
            raw = json.loads(story_choices_file.read_text(encoding="utf-8"))
            story_choices_loaded = isinstance(raw, dict) and len(raw) > 0
        except Exception:
            story_choices_loaded = False

    if db_path:
        game_data_dir = _find_game_data_dir(db_path)

    # Fallback: check config directly (user may have set game_data_dir manually)
    if not game_data_dir:
        cfg_file = _APP_DIR / "config.json"
        if cfg_file.is_file():
            with contextlib.suppress(Exception):
                cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
                gdd = cfg.get("game_data_dir")
                if gdd and (Path(gdd) / "dat").is_dir():
                    game_data_dir = gdd

    # Binary scan status
    interesting = DISCOVERY_DIR / "interesting.json"
    scan_ready = interesting.exists()

    return jsonify(
        {
            "master_db_configured": master_db_available(),
            "master_db_path": db_path,
            "story_choices_exist": story_choices_loaded,
            "game_data_dir": game_data_dir,
            "extraction_running": _extraction_running,
            "scan_ready": scan_ready,
            "scan_running": _setup_running,
            "scan_log": _setup_log[-80:],
        }
    )


@app.route("/api/setup/pick_mdb", methods=["POST"])
def api_pick_mdb():
    """
    Open a native file picker to select master.mdb, validate it, and save to config.

    In browser mode (no pywebview), accepts a JSON body with {path: "..."}.
    """
    # Check if a manual path was provided (browser mode or fallback)
    data = request.get_json(silent=True) or {}
    manual_path = data.get("path")

    if manual_path:
        ok = set_db_path(manual_path)
        if not ok:
            return jsonify({"ok": False, "error": "Invalid file — not a valid master.mdb"})
        return _mdb_success_response(manual_path)

    # Native mode: use pywebview file dialog
    if _webview_window is None:
        return jsonify({"fallback": True, "message": "No native window — use manual path input"})

    try:
        import webview  # type: ignore[import-untyped]

        result = _webview_window.create_file_dialog(
            webview.OPEN_DIALOG,
            file_types=("MDB Files (*.mdb)", "All Files (*.*)"),
        )
        if not result:
            return jsonify({"cancelled": True})

        chosen = result[0] if isinstance(result, (list, tuple)) else str(result)
        ok = set_db_path(chosen)
        if not ok:
            return jsonify({"ok": False, "error": f"Invalid file: {chosen}"})
        return _mdb_success_response(chosen)
    except Exception as e:
        log.exception("File dialog failed")
        return jsonify({"ok": False, "error": str(e)})


def _find_game_data_dir(mdb_path: str) -> str | None:
    """
    Try multiple heuristics to find the game data directory (containing dat/ and meta).

    The master.mdb can be at various locations:
      - {game_root}/master/master.mdb         → parent.parent
      - {game_root}/master.mdb                → parent
      - Somewhere else entirely (user copied it)

    Also search common Windows game data paths via LocalLow.
    """
    p = Path(mdb_path).resolve()
    log.info("_find_game_data_dir: starting from mdb_path=%s (resolved=%s)", mdb_path, p)

    # Try walking up from the mdb file (up to 4 levels)
    candidate = p.parent
    for i in range(4):
        dat_candidate = candidate / "dat"
        if dat_candidate.is_dir():
            log.info("_find_game_data_dir: FOUND dat/ at %s (level %d up)", candidate, i)
            return str(candidate)
        else:
            log.debug("_find_game_data_dir: no dat/ at %s", candidate)
        candidate = candidate.parent

    # Check config for an explicit game_data_dir
    cfg_file = _APP_DIR / "config.json"
    if cfg_file.is_file():
        with contextlib.suppress(Exception):
            cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
            gdd = cfg.get("game_data_dir")
            if gdd:
                if (Path(gdd) / "dat").is_dir():
                    log.info("_find_game_data_dir: FOUND via config game_data_dir=%s", gdd)
                    return gdd
                else:
                    log.warning(
                        "_find_game_data_dir: config game_data_dir=%s but dat/ not found there", gdd
                    )

    # Try common Windows LocalLow paths (works even if mdb was copied elsewhere)
    import platform

    if platform.system() == "Windows":
        localappdata = os.environ.get("LOCALAPPDATA", "")
        if localappdata:
            locallow = Path(localappdata).parent / "LocalLow" / "Cygames" / "umamusume"
            if (locallow / "dat").is_dir():
                log.info("_find_game_data_dir: FOUND via LocalLow at %s", locallow)
                return str(locallow)
            else:
                log.debug("_find_game_data_dir: no dat/ at LocalLow path %s", locallow)

    log.warning(
        "_find_game_data_dir: could NOT find dat/ directory. "
        "Searched parents of %s (up 4 levels) and config. "
        "Parent dirs tried: %s",
        p,
        [str(p.parents[i]) for i in range(min(4, len(p.parents)))],
    )
    return None


def _mdb_success_response(path: str):
    """Build the success JSON after setting master DB path."""
    resolved = get_db_path() or path
    game_data_dir = _find_game_data_dir(resolved)

    # Build diagnostic info about what we found
    diag: dict = {"mdb_path_resolved": str(Path(resolved).resolve())}
    if game_data_dir:
        gd = Path(game_data_dir)
        diag["game_data_dir"] = game_data_dir
        diag["dat_exists"] = (gd / "dat").is_dir()
        diag["meta_exists"] = (gd / "meta").is_file()
        # Show first few dat/ subdirs for confirmation
        dat_dir = gd / "dat"
        if dat_dir.is_dir():
            try:
                subdirs = sorted([d.name for d in dat_dir.iterdir() if d.is_dir()][:10])
                diag["dat_subdirs_sample"] = subdirs
            except Exception:
                pass
    else:
        # Show what we tried so the user can see why it failed
        p = Path(resolved).resolve()
        tried = []
        candidate = p.parent
        for _ in range(4):
            tried.append(str(candidate / "dat"))
            candidate = candidate.parent
        diag["tried_paths"] = tried

    if game_data_dir:
        # Save game_data_dir to config
        cfg = {}
        cfg_file = _APP_DIR / "config.json"
        if cfg_file.is_file():
            with contextlib.suppress(Exception):
                cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
        cfg["game_data_dir"] = game_data_dir
        try:
            cfg_file.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        except Exception as e:
            log.warning("Failed to save game_data_dir to config: %s", e)

    return jsonify({"ok": True, "path": resolved, "game_data_dir": game_data_dir, "diag": diag})


@app.route("/api/setup/set_game_dir", methods=["POST"])
def api_set_game_dir():
    """Manually set the game data directory (containing dat/ and meta)."""
    data = request.get_json(silent=True) or {}
    path = data.get("path", "").strip()
    if not path:
        return jsonify({"ok": False, "error": "No path provided"}), 400

    p = Path(path)
    if not p.is_dir():
        return jsonify({"ok": False, "error": f"Not a directory: {path}"}), 400

    if not (p / "dat").is_dir():
        return jsonify({"ok": False, "error": f"No dat/ subdirectory found in: {path}"}), 400

    # Save to config
    cfg = {}
    cfg_file = _APP_DIR / "config.json"
    if cfg_file.is_file():
        with contextlib.suppress(Exception):
            cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
    cfg["game_data_dir"] = str(p)
    try:
        cfg_file.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    except Exception as e:
        log.warning("Failed to save game_data_dir to config: %s", e)
        return jsonify({"ok": False, "error": f"Failed to save config: {e}"}), 500

    has_meta = (p / "meta").is_file() or (p / "meta_umaviewer").is_file()
    log.info("Game data dir set to: %s (meta=%s)", p, has_meta)
    return jsonify({"ok": True, "path": str(p), "has_meta": has_meta})


@app.route("/api/setup/extract_stories", methods=["POST"])
def api_extract_stories():
    """Run story text extraction in the background."""
    global _extraction_running

    with _extraction_lock:
        if _extraction_running:
            return jsonify({"error": "Extraction already running"}), 400

    # Check if game data dir is available
    db_path = get_db_path()
    game_dir = None
    if db_path:
        gdd = _find_game_data_dir(db_path)
        if gdd:
            game_dir = Path(gdd)

    # Fallback: check config directly (user may have set game_data_dir manually)
    if not game_dir:
        cfg_file = _APP_DIR / "config.json"
        if cfg_file.is_file():
            with contextlib.suppress(Exception):
                cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
                gdd = cfg.get("game_data_dir")
                if gdd and (Path(gdd) / "dat").is_dir():
                    game_dir = Path(gdd)

    if not game_dir:
        # Build a diagnostic message showing exactly what we tried
        if db_path:
            tried = []
            p = Path(db_path).resolve()
            candidate = p.parent
            for _ in range(4):
                tried.append(str(candidate / "dat"))
                candidate = candidate.parent
            msg = (
                "Game data directory not found. "
                "Story extraction requires the full game install with dat/ and meta files.\n"
                f"Master DB path: {db_path}\n"
                f"Searched for dat/ at:\n" + "\n".join(f"  {t}" for t in tried)
            )
        else:
            msg = (
                "Game data directory not found. "
                "Set master.mdb first, or use the manual game dir input."
            )
        return jsonify({"error": msg}), 400

    # Check meta database exists (decryption is handled by read_meta_entries)
    if not (game_dir / "meta").is_file():
        return jsonify({"error": f"meta database not found in {game_dir}"}), 400

    with _extraction_lock:
        _extraction_running = True
        _extraction_progress.update(
            {
                "processed": 0,
                "total": 0,
                "found": 0,
                "skipped": 0,
                "error": None,
                "status": "starting",
            }
        )

    threading.Thread(target=_run_extraction, args=(game_dir,), daemon=True).start()
    return jsonify({"status": "started", "game_dir": str(game_dir)})


def _run_extraction(game_dir: Path) -> None:
    """Background thread for story text extraction."""
    global _extraction_running
    try:
        from extract_story_text import extract_choices_from_bundle, read_meta_entries

        # Ensure extract_story_text logger output goes to gui.log too
        est_logger = logging.getLogger("extract_story_text")
        if not est_logger.handlers:
            est_logger.setLevel(logging.DEBUG)
        for h in log.handlers:
            if h not in est_logger.handlers:
                est_logger.addHandler(h)

        dat_dir = game_dir / "dat"
        log.info("Story extraction: game_dir=%s, dat_dir=%s", game_dir, dat_dir)

        # Check dat/ directory
        if not dat_dir.is_dir():
            msg = f"dat/ directory not found at {dat_dir}"
            log.error(msg)
            with _extraction_lock:
                _extraction_progress["error"] = msg
            return

        # Log dat/ structure for diagnostics
        try:
            dat_subdirs = sorted([d.name for d in dat_dir.iterdir() if d.is_dir()])
            log.info("dat/ has %d subdirectories: %s", len(dat_subdirs), dat_subdirs[:20])
        except Exception as e:
            log.warning("Could not list dat/ contents: %s", e)

        # Read meta database
        with _extraction_lock:
            _extraction_progress["status"] = "reading meta database"
        entries = read_meta_entries(game_dir)
        log.info("Meta returned %d story timeline entries", len(entries))

        if not entries:
            # read_meta_entries already logged detailed errors.
            # Surface a summary to the frontend.
            meta_path = game_dir / "meta"
            if not meta_path.is_file():
                msg = (
                    f"meta database not found at {meta_path}.\n"
                    f"It should be in the game root next to dat/."
                )
            else:
                msg = (
                    f"meta database at {meta_path} returned 0 story entries.\n"
                    f"It may be encrypted and decryption failed.\n"
                    f"Place sqlite3mc_x64.dll next to the program, "
                    f"or install pysqlcipher3."
                )
            log.error(msg)
            with _extraction_lock:
                _extraction_progress["error"] = msg
                _extraction_progress["total"] = 0
            return

        with _extraction_lock:
            _extraction_progress["total"] = len(entries)
            _extraction_progress["status"] = "extracting"

        # Log a sample entry so we can verify hash format
        sample = entries[0]
        log.info(
            "Sample meta entry: name=%s hash=%s key=%s → expected path: %s",
            sample["name"],
            sample["hash"],
            sample["key"],
            dat_dir / sample["hash"][:2] / sample["hash"],
        )

        all_choices: dict[str, list[str]] = {}
        processed = 0
        found = 0
        skipped = 0
        missing_samples: list[str] = []  # first few missing paths for diagnostics

        for entry in entries:
            h = entry["hash"]
            file_path = dat_dir / h[:2] / h
            if not file_path.is_file():
                skipped += 1
                processed += 1
                if len(missing_samples) < 3:
                    missing_samples.append(str(file_path))
                with _extraction_lock:
                    _extraction_progress["processed"] = processed
                    _extraction_progress["skipped"] = skipped
                continue

            bundle_choices = extract_choices_from_bundle(file_path, entry["key"])
            processed += 1

            if bundle_choices:
                for sid, choices in bundle_choices.items():
                    all_choices[str(sid)] = choices
                    found += 1

            with _extraction_lock:
                _extraction_progress["processed"] = processed
                _extraction_progress["found"] = found
                _extraction_progress["skipped"] = skipped

        log.info(
            "Story extraction complete: %d entries, %d processed, %d skipped (file missing), %d with choices",
            len(entries),
            processed - skipped,
            skipped,
            found,
        )

        # If ALL files were missing, that's a specific diagnosable problem
        if skipped == len(entries):
            msg = (
                f"All {len(entries)} asset files were missing from dat/. "
                f"The meta database hash format may not match the file names on disk. "
                f"Sample expected paths:\n" + "\n".join(f"  {p}" for p in missing_samples)
            )
            log.error(msg)
            with _extraction_lock:
                _extraction_progress["error"] = msg
            return

        with _extraction_lock:
            _extraction_progress["found"] = found
            _extraction_progress["status"] = "done"

        # Only write to file if we actually found something —
        # an empty file would falsely show "already loaded" in the wizard.
        if not all_choices:
            log.info("No story choices found — not writing story_choices.json")
            return

        # Write output
        output_file = _APP_DIR / "story_choices.json"
        # Merge with existing
        if output_file.is_file():
            try:
                existing = json.loads(output_file.read_text(encoding="utf-8"))
                if isinstance(existing, dict):
                    existing.update(all_choices)
                    all_choices = existing
            except Exception:
                pass

        output_file.write_text(
            json.dumps(all_choices, indent=2, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )

        # Clear the master_db story choices cache so it reloads
        try:
            from lib.master_db import _load_story_choices

            _load_story_choices.cache_clear()
        except Exception:
            pass

    except ImportError:
        log.error("UnityPy not installed — cannot extract story text")
        with _extraction_lock:
            _extraction_progress["error"] = (
                "UnityPy is not installed. Install it with: pip install UnityPy"
            )
    except Exception as e:
        log.exception("Story extraction failed")
        with _extraction_lock:
            _extraction_progress["error"] = str(e)
    finally:
        with _extraction_lock:
            _extraction_running = False


@app.route("/api/setup/extract_status")
def api_extract_status():
    """Poll extraction progress."""
    with _extraction_lock:
        return jsonify(
            {
                "running": _extraction_running,
                **_extraction_progress,
            }
        )


# ── Routes: Recorder ───────────────────────────────────────────────────


@app.route("/api/recorder/status")
def api_recorder_status():
    with _recorder_lock:
        running = _recorder_process is not None and _recorder_process.poll() is None
        return jsonify({"running": running, "log": _recorder_log[-50:]})


@app.route("/api/recorder/start", methods=["POST"])
def api_recorder_start():
    global _recorder_process
    with _recorder_lock:
        if _recorder_process is not None and _recorder_process.poll() is None:
            return jsonify({"error": "Recorder already running"}), 400

    try:
        data = request.get_json(silent=True) or {}
        label = data.get("label", "gui")
        modules = data.get("modules", ["dump", "network", "races"])
        cmd = _tool_cmd("collect", "--label", label, "--modules", *modules)

        with _recorder_lock:
            _recorder_log.clear()
            _recorder_log.append(f"[gui] Starting: {' '.join(cmd)}")
        kwargs: dict = dict(
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(SCRIPT_DIR),
        )
        # On Windows, hide console window
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        proc = subprocess.Popen(cmd, **kwargs)
        with _recorder_lock:
            _recorder_process = proc
        threading.Thread(target=_stream_recorder_output, args=(proc,), daemon=True).start()
        log.info("Recorder started (pid=%d): %s", proc.pid, " ".join(cmd))
        return jsonify({"status": "started", "pid": proc.pid})
    except Exception as e:
        log.exception("api_recorder_start failed")
        return jsonify({"error": str(e)}), 500


@app.route("/api/recorder/stop", methods=["POST"])
def api_recorder_stop():
    with _recorder_lock:
        proc = _recorder_process
        if proc is None or proc.poll() is not None:
            return jsonify({"status": "not_running"})
    try:
        # Close stdin to signal the collector to stop gracefully.
        # The collector monitors stdin; EOF triggers clean shutdown
        # (saves manifest, processes dump frames, etc).
        # This avoids CTRL_BREAK_EVENT which crashes Frida's C++ threads.
        if proc.stdin:
            with contextlib.suppress(Exception):
                proc.stdin.close()
        with _recorder_lock:
            _recorder_log.append("[gui] Sent stop signal")

        # Watchdog: if the process doesn't exit within 15s, force-kill it.
        # This runs in a background thread so the HTTP response returns immediately.
        def _watchdog():
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                log.warning("Recorder did not exit in time, terminating")
                proc.terminate()
                with _recorder_lock:
                    _recorder_log.append("[gui] Recorder force-terminated after timeout")

        threading.Thread(target=_watchdog, daemon=True).start()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"status": "stopping"})


# ── Routes: Asset extraction ───────────────────────────────────────────

_asset_extraction_running: bool = False
_asset_extraction_progress: dict = {
    "processed": 0,
    "total": 0,
    "found": 0,
    "error": None,
    "status": "idle",
    "phase": "",
}
_asset_extraction_lock = threading.Lock()


@app.route("/api/setup/extract_assets", methods=["POST"])
def api_extract_assets():
    """Run support-card + character portrait image extraction in background."""
    global _asset_extraction_running

    with _asset_extraction_lock:
        if _asset_extraction_running:
            return jsonify({"error": "Asset extraction already running"}), 400

    # Resolve game data directory (same logic as story extraction)
    db_path = get_db_path()
    game_dir = None
    if db_path:
        gdd = _find_game_data_dir(db_path)
        if gdd:
            game_dir = Path(gdd)
    if not game_dir:
        cfg_file = _APP_DIR / "config.json"
        if cfg_file.is_file():
            with contextlib.suppress(Exception):
                cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
                gdd = cfg.get("game_data_dir")
                if gdd and (Path(gdd) / "dat").is_dir():
                    game_dir = Path(gdd)
    if not game_dir:
        return jsonify(
            {"error": "Game data directory not found. Set master.mdb or game dir first."}
        ), 400
    if not (game_dir / "meta").is_file():
        return jsonify({"error": f"meta database not found in {game_dir}"}), 400

    # Optional: restrict to specific types
    data = request.get_json(silent=True) or {}
    extract_type = data.get("type", "all")  # "support", "portraits", or "all"

    with _asset_extraction_lock:
        _asset_extraction_running = True
        _asset_extraction_progress.update(
            {
                "processed": 0,
                "total": 0,
                "found": 0,
                "error": None,
                "status": "starting",
                "phase": "",
            }
        )

    threading.Thread(
        target=_run_asset_extraction, args=(game_dir, extract_type), daemon=True
    ).start()
    return jsonify({"status": "started", "game_dir": str(game_dir), "type": extract_type})


def _run_asset_extraction(game_dir: Path, extract_type: str) -> None:
    """Background thread for asset image extraction."""
    global _asset_extraction_running
    try:
        from extract_assets import extract_chara_portraits, extract_support_card_images

        # Wire extract_assets logger into gui.log
        ea_logger = logging.getLogger("extract_assets")
        if not ea_logger.handlers:
            ea_logger.setLevel(logging.DEBUG)
        for h in log.handlers:
            if h not in ea_logger.handlers:
                ea_logger.addHandler(h)

        total_found = 0

        def _progress(processed, total, found):
            with _asset_extraction_lock:
                _asset_extraction_progress["processed"] = processed
                _asset_extraction_progress["total"] = total
                _asset_extraction_progress["found"] = found

        if extract_type in ("support", "all"):
            with _asset_extraction_lock:
                _asset_extraction_progress["phase"] = "support cards"
                _asset_extraction_progress["status"] = "extracting"
            cards_dir = Path(app.static_folder) / "cards"
            results = extract_support_card_images(game_dir, cards_dir, progress_callback=_progress)
            total_found += len(results)
            log.info("Asset extraction: %d support card images", len(results))
            # Refresh the in-memory support card image index
            _SC_IMAGES.clear()
            _scan_support_card_images()

        if extract_type in ("portraits", "all"):
            with _asset_extraction_lock:
                _asset_extraction_progress["phase"] = "character portraits"
                _asset_extraction_progress["processed"] = 0
                _asset_extraction_progress["total"] = 0
                _asset_extraction_progress["found"] = 0
            uma_dir = Path(app.static_folder) / "uma"
            results = extract_chara_portraits(game_dir, uma_dir, progress_callback=_progress)
            total_found += len(results)
            log.info("Asset extraction: %d character portraits", len(results))
            # Refresh the in-memory uma image index
            _UMA_IMAGES.clear()
            _scan_uma_images()

        with _asset_extraction_lock:
            _asset_extraction_progress["status"] = "done"
            _asset_extraction_progress["found"] = total_found

    except ImportError:
        log.error("UnityPy not installed — cannot extract assets")
        with _asset_extraction_lock:
            _asset_extraction_progress["error"] = (
                "UnityPy is not installed. Install it with: pip install UnityPy"
            )
    except Exception as e:
        log.exception("Asset extraction failed")
        with _asset_extraction_lock:
            _asset_extraction_progress["error"] = str(e)
    finally:
        with _asset_extraction_lock:
            _asset_extraction_running = False


@app.route("/api/setup/extract_assets_status")
def api_extract_assets_status():
    """Poll asset extraction progress."""
    with _asset_extraction_lock:
        return jsonify(
            {
                "running": _asset_extraction_running,
                **_asset_extraction_progress,
            }
        )


# ── Main ───────────────────────────────────────────────────────────────

_PORT = 5050


def _run_flask():
    """Run Flask in a background thread (no reloader, quiet)."""
    import logging as _log

    _log.getLogger("werkzeug").setLevel(_log.WARNING)
    app.run(host="127.0.0.1", port=_PORT, debug=False, use_reloader=False)


def main():
    parser = argparse.ArgumentParser(description="Clairvoyance GUI")
    parser.add_argument(
        "--browser", action="store_true", help="Open in browser instead of native window"
    )
    parser.add_argument("--port", type=int, default=5050, help="Port (default: 5050)")
    parser.add_argument(
        "--debug", action="store_true", help="Enable Flask debug mode (browser only)"
    )
    args = parser.parse_args()

    global _PORT
    _PORT = args.port
    url = f"http://127.0.0.1:{_PORT}"

    if args.browser or args.debug:
        # Fallback: plain Flask in browser
        print(f"\n  Clairvoyance — {url}\n")
        app.run(host="127.0.0.1", port=_PORT, debug=args.debug)
    else:
        # Native window via pywebview
        import webview  # type: ignore[import-untyped]

        # Start Flask in background
        server = threading.Thread(target=_run_flask, daemon=True)
        server.start()

        # Give Flask a moment to bind
        import time

        time.sleep(0.4)

        _icon_path = str(_BUNDLE_DIR / "static" / "main_small_icon.png")

        window = webview.create_window(
            "Clairvoyance",
            url,
            width=1280,
            height=860,
            min_size=(900, 600),
        )

        # Store window reference so Flask routes can open file dialogs
        global _webview_window
        _webview_window = window

        webview.start(icon=_icon_path)


if __name__ == "__main__":
    main()
