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
    build_session_summary,
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


@app.route("/session/<name>")
def session_detail(name: str):
    session = get_session(name)
    if not session:
        return "Session not found", 404

    summary = build_session_summary(name)

    # Resolve IDs to human-readable names via master DB
    if summary.get("chara_id") not in (None, 0, ""):
        summary["chara_name"] = chara_name(summary["chara_id"])
        summary["chara_image"] = uma_image_url(summary["chara_id"], summary.get("card_id"))
    if summary.get("card_id") not in (None, 0, ""):
        full_card = card_name(summary["card_id"])
        # card_name returns "[Outfit Title] CharaName" — split into parts
        m = re.match(r"^\[(.+?)\]\s*(.+)$", full_card)
        if m:
            summary["outfit_title"] = m.group(1)
            # Use as fallback when chara_name lookup missed
            if not summary.get("chara_name") or summary["chara_name"].startswith("Character #"):
                summary["chara_name"] = m.group(2)
        else:
            # No bracket format — use the whole string as fallback name
            if not summary.get("chara_name") or summary["chara_name"].startswith("Character #"):
                summary["chara_name"] = full_card
    if summary.get("scenario_id") not in (None, 0, ""):
        summary["scenario_name"] = scenario_name(summary["scenario_id"])
    for sc_id in summary.get("support_card_ids", []):
        summary.setdefault("support_card_names", []).append(
            {
                "id": sc_id,
                "name": support_card_name(sc_id),
            }
        )
    if summary.get("friend_support_card_id"):
        summary["friend_support_card_name"] = support_card_name(summary["friend_support_card_id"])
    for sk in summary.get("skills_acquired", []):
        sk["name"] = skill_name(sk["skill_id"])
    for sk in summary.get("skill_tips", []):
        sk["name"] = skill_name(sk["skill_id"])
    for rr in summary.get("race_results", []):
        if rr.get("race_instance_id"):
            rr["race_name"] = race_instance_name(rr["race_instance_id"])

    # Enrich events with master DB lookups
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

        # If story_id is missing but event_id is present, resolve it
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
            # Last resort: annotate with event_id-derived name
            ec["name"] = event_name_by_event_id(eid)

    net = get_network_events(name)

    return render_template(
        "session.html",
        session=session,
        races=get_races(name),
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
_extraction_progress: dict = {"processed": 0, "total": 0, "found": 0, "error": None}
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

    return jsonify(
        {
            "master_db_configured": master_db_available(),
            "master_db_path": db_path,
            "story_choices_exist": story_choices_loaded,
            "game_data_dir": game_data_dir,
            "extraction_running": _extraction_running,
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

    # Try walking up from the mdb file (up to 4 levels)
    candidate = p.parent
    for _ in range(4):
        if (candidate / "dat").is_dir():
            return str(candidate)
        candidate = candidate.parent

    # Check config for an explicit game_data_dir
    cfg_file = _APP_DIR / "config.json"
    if cfg_file.is_file():
        with contextlib.suppress(Exception):
            cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
            gdd = cfg.get("game_data_dir")
            if gdd and (Path(gdd) / "dat").is_dir():
                return gdd

    # Try common Windows LocalLow paths (works even if mdb was copied elsewhere)
    import platform

    if platform.system() == "Windows":
        localappdata = os.environ.get("LOCALAPPDATA", "")
        if localappdata:
            locallow = Path(localappdata).parent / "LocalLow" / "Cygames" / "umamusume"
            if (locallow / "dat").is_dir():
                return str(locallow)

    return None


def _mdb_success_response(path: str):
    """Build the success JSON after setting master DB path."""
    resolved = get_db_path() or path
    game_data_dir = _find_game_data_dir(resolved)

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

    return jsonify({"ok": True, "path": resolved, "game_data_dir": game_data_dir})


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
        return jsonify(
            {
                "error": "Game data directory not found. Story extraction requires the full game install with dat/ and meta files."
            }
        ), 400

    # Check meta database
    meta_exists = (game_dir / "meta").is_file() or (game_dir / "meta_umaviewer").is_file()
    if not meta_exists:
        return jsonify({"error": f"meta database not found in {game_dir}"}), 400

    with _extraction_lock:
        _extraction_running = True
        _extraction_progress.update({"processed": 0, "total": 0, "found": 0, "error": None})

    threading.Thread(target=_run_extraction, args=(game_dir,), daemon=True).start()
    return jsonify({"status": "started"})


def _run_extraction(game_dir: Path) -> None:
    """Background thread for story text extraction."""
    global _extraction_running
    try:
        from extract_story_text import extract_choices_from_bundle, read_meta_entries

        dat_dir = game_dir / "dat"
        entries = read_meta_entries(game_dir)

        with _extraction_lock:
            _extraction_progress["total"] = len(entries)

        all_choices: dict[str, list[str]] = {}
        processed = 0
        found = 0
        skipped = 0

        for entry in entries:
            h = entry["hash"]
            file_path = dat_dir / h[:2] / h
            if not file_path.is_file():
                skipped += 1
                processed += 1
                with _extraction_lock:
                    _extraction_progress["processed"] = processed
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

        log.info("Story extraction complete: %d stories with choices", found)
        with _extraction_lock:
            _extraction_progress["found"] = found

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
