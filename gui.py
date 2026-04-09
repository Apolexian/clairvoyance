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
import logging
import os
import signal
import subprocess
import sys
import threading
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from lib.session_reader import (
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
        if not exe.exists():
            raise FileNotFoundError(f"Bundled tool not found: {exe}")
        return [str(exe), *args]
    return [sys.executable, str(SCRIPT_DIR / f"{tool}.py"), *args]


app = Flask(
    __name__,
    template_folder=str(_BUNDLE_DIR / "templates"),
    static_folder=str(_BUNDLE_DIR / "static"),
)
app.config["JSON_SORT_KEYS"] = False

LOG_FILE = SCRIPT_DIR / "gui.log"

log = logging.getLogger("clairvoyance.gui")
log.setLevel(logging.DEBUG)

# File handler — always active, captures everything (persists across runs)
_fh = logging.FileHandler(str(LOG_FILE), mode="a", encoding="utf-8")
_fh.setLevel(logging.DEBUG)
_fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s — %(message)s"))
log.addHandler(_fh)

# Console handler — useful in dev mode (uv run gui.py)
_ch = logging.StreamHandler(sys.stdout)
_ch.setLevel(logging.INFO)
_ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
log.addHandler(_ch)

log.info("Clairvoyance GUI starting — log file: %s", LOG_FILE)


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
    return render_template("home.html", sessions=list_sessions())


@app.route("/session/<name>")
def session_detail(name: str):
    session = get_session(name)
    if not session:
        return "Session not found", 404
    return render_template(
        "session.html",
        session=session,
        races=get_races(name),
        network=get_network_events(name),
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
            "running": _setup_process is not None and _setup_process.poll() is None,
            "log": _setup_log[-80:],
        }
    )


_setup_process: subprocess.Popen | None = None
_setup_log: list[str] = []
_setup_lock = threading.Lock()


def _stream_setup_output(proc: subprocess.Popen) -> None:
    global _setup_process
    try:
        for line in iter(proc.stdout.readline, ""):
            if not line:
                break
            with _setup_lock:
                _setup_log.append(line.rstrip("\n"))
                if len(_setup_log) > 500:
                    _setup_log.pop(0)
    except Exception:
        pass
    finally:
        proc.wait()
        log.info("Setup process exited with code %d", proc.returncode)
        with _setup_lock:
            _setup_log.append(f"[setup] Exited with code {proc.returncode}")
            if _setup_process is proc:
                _setup_process = None


@app.route("/api/setup/run", methods=["POST"])
def api_setup_run():
    """Run the full discover → analyse pipeline."""
    global _setup_process

    with _setup_lock:
        if _setup_process is not None and _setup_process.poll() is None:
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

        kwargs: dict = dict(
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(SCRIPT_DIR),
        )
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
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
    """
    global _setup_process
    # Stream output from first command
    _stream_setup_output(proc)

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
                cwd=str(SCRIPT_DIR),
            )
            if os.name == "nt":
                kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
            analyse_proc = subprocess.Popen(analyse_cmd, **kwargs)
            with _setup_lock:
                _setup_process = analyse_proc
            _stream_setup_output(analyse_proc)
            if analyse_proc.returncode == 0:
                with _setup_lock:
                    _setup_log.append("[setup] ✓ Setup complete — ready to record!")
            else:
                with _setup_lock:
                    _setup_log.append("[setup] ✗ Analyse failed.")
        except Exception as e:
            with _setup_lock:
                _setup_log.append(f"[setup] ✗ Analyse error: {e}")
    elif skip_discover and proc.returncode == 0:
        with _setup_lock:
            _setup_log.append("[setup] ✓ Analysis complete — ready to record!")
    else:
        with _setup_lock:
            _setup_log.append("[setup] ✗ Discovery failed — check that the game is running.")


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
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(SCRIPT_DIR),
        )
        # On Windows, create in a new process group so we can send CTRL_BREAK
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
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
    global _recorder_process
    with _recorder_lock:
        proc = _recorder_process
        if proc is None or proc.poll() is not None:
            return jsonify({"status": "not_running"})
    try:
        if os.name == "nt":
            # Windows: send CTRL_BREAK to the process group
            proc.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            proc.send_signal(signal.SIGINT)
        _recorder_log.append("[gui] Sent stop signal")
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

        webview.create_window(
            "Clairvoyance",
            url,
            width=1280,
            height=860,
            min_size=(900, 600),
        )
        webview.start(icon=_icon_path)


if __name__ == "__main__":
    main()
