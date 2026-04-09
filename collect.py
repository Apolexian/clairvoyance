# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "frida",
#     "msgpack",
# ]
# ///

"""
Clairvoyance — Phase 2: Background Collector
─────────────────────────────────────────────
Attaches to Uma Musume and silently collects skill activations, event text,
race results, and other game data while you play.

All data is written to per-session JSONL files under sessions/.

Usage:
  uv run collect.py                # start collecting
  uv run collect.py --label test1  # custom session label
  uv run collect.py --modules skills events races  # choose what to hook
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import sys
import time
import traceback

import msgpack

from lib.attach import attach
from lib.race_processor import process_dump_race_frames, try_process_race
from lib.session import Session

# ── Paths ──────────────────────────────────────────────────────────────────

_FROZEN = getattr(sys, "frozen", False)

if _FROZEN:
    # PyInstaller: data files (js/) live in the temp _MEIPASS bundle,
    # but working directories (sessions/, logs) live next to the .exe.
    _BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))  # _MEIPASS
    SCRIPT_DIR = os.path.dirname(os.path.abspath(sys.executable))
    JS_DIR = os.path.join(_BUNDLE_DIR, "js")
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    JS_DIR = os.path.join(SCRIPT_DIR, "js")


# ── Logging ────────────────────────────────────────────────────────────────

LOG_FILE = os.path.join(SCRIPT_DIR, "collect.log")
JS_LOG_FILE = os.path.join(SCRIPT_DIR, "collect_js.log")

# Main logger — console + file, important events only
log = logging.getLogger("clairvoyance")
log.setLevel(logging.DEBUG)

# Force UTF-8 on stdout so Unicode doesn't crash on Windows cp1252
if sys.stdout:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_console = logging.StreamHandler(sys.stdout)
_console.setLevel(logging.INFO)
_console.setFormatter(logging.Formatter("%(message)s"))
log.addHandler(_console)

_logfile = logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8")
_logfile.setLevel(logging.DEBUG)
_logfile.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
log.addHandler(_logfile)

# JS logger — verbose Frida console.log output, file only (no console spam)
js_log = logging.getLogger("clairvoyance.js")
js_log.setLevel(logging.DEBUG)
js_log.propagate = False

_js_logfile = logging.FileHandler(JS_LOG_FILE, mode="w", encoding="utf-8")
_js_logfile.setLevel(logging.DEBUG)
_js_logfile.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
js_log.addHandler(_js_logfile)

# ── CLI ────────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(description="Clairvoyance Collector")
parser.add_argument("--label", default="", help="Optional label for the session directory")
parser.add_argument(
    "--modules",
    nargs="*",
    default=["skills", "events", "races", "network"],
    help="Which hook modules to load (default: skills events races network). "
    "Add 'dump' for data-driven field capture from interesting.json.",
)
parser.add_argument(
    "--timeout", type=int, default=0, help="Auto-stop after N seconds (0 = run until Ctrl+C)"
)
parser.add_argument(
    "--dump-min-score",
    type=int,
    default=30,
    help="[dump module] Minimum class score to hook (default: 30)",
)
parser.add_argument(
    "--dump-max-classes",
    type=int,
    default=100,
    help="[dump module] Maximum number of classes to hook (default: 100)",
)
args = parser.parse_args()

# ── Available hook modules ─────────────────────────────────────────────────

HOOK_MODULES = {
    "skills": "hook_skills.js",
    "events": "hook_events.js",
    "races": "hook_races.js",
    "network": "hook_network.js",
    "dump": "hook_dump.js",  # data-driven, needs interesting.json
}

DISCOVERY_DIR = os.path.join(SCRIPT_DIR, "discovery")


def load_js(filename: str) -> str:
    path = os.path.join(JS_DIR, filename)
    with open(path, encoding="utf-8") as f:
        return f.read()


def load_dump_targets(min_score: int, max_classes: int) -> list[dict]:
    """Load top-scored classes from interesting.json for the dump module."""
    path = os.path.join(DISCOVERY_DIR, "interesting.json")
    if not os.path.exists(path):
        log.error("  [X] discovery/interesting.json not found. Run: make analyse")
        return []

    with open(path, encoding="utf-8") as f:
        all_classes = json.load(f)

    # Filter to classes above min_score, take top N
    filtered = [c for c in all_classes if c.get("score", 0) >= min_score]
    filtered.sort(key=lambda c: -c.get("score", 0))
    targets = filtered[:max_classes]

    log.info(
        "  [dump] Loaded %d target classes (score >= %d, max %d) from interesting.json",
        len(targets),
        min_score,
        max_classes,
    )

    return targets


def build_collector_script(modules: list[str]) -> str:
    """Build the combined collector script from helpers + selected hook modules."""
    helpers = load_js("il2cpp_helpers.js")

    hook_code = []
    for mod in modules:
        if mod not in HOOK_MODULES:
            log.warning("Unknown module '%s', skipping.", mod)
            continue

        js_src = load_js(HOOK_MODULES[mod])

        # The dump module needs class layouts injected
        if mod == "dump":
            targets = load_dump_targets(
                min_score=args.dump_min_score,
                max_classes=args.dump_max_classes,
            )
            if not targets:
                log.warning("  [dump] No targets loaded, skipping dump module.")
                continue
            js_src = js_src.replace("INJECTED_DUMP_TARGETS", json.dumps(targets))

        hook_code.append(f"// ── Module: {mod} ──")
        hook_code.append(js_src)

    combined = "\n\n".join(hook_code)
    return f"(function(){{\n{helpers}\n\n{combined}\n}})();"


# ── Session + message handling ─────────────────────────────────────────────

session_data: Session | None = None
hook_statuses: dict[str, int] = {}
is_ready = False
has_error = False

# Accumulators for dump-hook race frame data
_dump_frame_records: list[dict] = []
_race_lifecycle_records: list[dict] = []
_race_skill_records: list[dict] = []

# ── MsgPack decode helpers ─────────────────────────────────────────────


def _sanitise_bytes(obj: object) -> object:
    """Recursively convert bytes values to lossy UTF-8 strings for JSON safety."""
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    if isinstance(obj, dict):
        return {_sanitise_bytes(k): _sanitise_bytes(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitise_bytes(v) for v in obj]
    return obj


def _try_msgpack_decode(raw: bytes) -> dict | list | None:
    """
    Try to decode raw bytes as MsgPack with multiple fallback strategies.

    The game's C# MsgPack serialiser encodes byte[] fields as old-spec str
    (not bin), so raw=False (force UTF-8) fails on responses with binary blobs.
    """
    # Strategy 1: raw=True — safest, treats all str/bin as bytes
    try:
        decoded = msgpack.unpackb(raw, raw=True, strict_map_key=False)
        return _sanitise_bytes(decoded)
    except msgpack.ExtraData as e:
        # Valid msgpack followed by trailing bytes — take the valid part
        log.debug("  [msgpack] ExtraData — using partial decode")
        return _sanitise_bytes(e.unpacked)
    except Exception as e:
        log.debug("  [msgpack] raw=True failed: %s: %s", type(e).__name__, e)

    # Strategy 2: raw=False — nicer strings, but fails on binary blobs
    try:
        decoded = msgpack.unpackb(raw, raw=False, strict_map_key=False)
        return decoded
    except Exception as e:
        log.debug("  [msgpack] raw=False failed: %s: %s", type(e).__name__, e)

    return None


def on_message(message, data):
    global is_ready, has_error

    msg_type = message.get("type")

    if msg_type == "send":
        payload = message.get("payload")
        if not isinstance(payload, dict):
            return

        ptype = payload.get("type")

        if ptype == "error":
            has_error = True
            log.error("  [X] %s", payload.get("message", ""))

        elif ptype == "hook_status":
            mod = payload.get("module", "?")
            count = payload.get("hookCount", 0)
            hook_statuses[mod] = count
            log.info("  [%s] %d hooks installed", mod, count)

            # Consider ready when we've heard from all modules
            if len(hook_statuses) >= len(args.modules):
                is_ready = True

        elif ptype == "collect":
            # This is the main data pathway
            domain = payload.get("domain", "raw")
            record = payload.get("data", {})

            # If the JS side sent binary data (e.g. SSL_read/write buffers,
            # or postData byte arrays from Task hooks), decode it.
            if data is not None and len(data) > 0:
                raw = bytes(data)
                decoded = _try_msgpack_decode(raw)
                if decoded is not None:
                    # MsgPack decoded successfully — use clean structured data.
                    # Only keep raw_b64 for archival re-decode; skip the
                    # garbled raw_text / hex noise.
                    record["msgpack_decoded"] = decoded
                    record["raw_b64"] = base64.b64encode(raw).decode("ascii")
                else:
                    # Decode failed — keep raw diagnostics so we can debug
                    try:
                        text = raw.decode("utf-8", errors="replace")
                        record["raw_text"] = text[:8192]
                    except Exception:
                        pass
                    record["raw_hex_preview"] = raw[:256].hex()
                    record["raw_bytes_len"] = len(raw)
                    record["raw_b64"] = base64.b64encode(raw).decode("ascii")

            # ── Race data extraction ──────────────────────────────────
            # When we see a decoded MsgPack response from a race API,
            # parse the race_simulate_data binary blob and write a
            # structured race record to the "race" domain.
            if domain == "network" and record.get("event") in ("api_response", "api_send"):
                api = record.get("api", "")
                has_decoded = "msgpack_decoded" in record
                if has_decoded:
                    try:
                        race_record = try_process_race(record)
                        if race_record and session_data:
                            session_data.write("race", race_record)
                            log.info(
                                "  [race] Wrote race record from %s (%s)",
                                api,
                                race_record.get("event", "?"),
                            )
                    except Exception as e:
                        log.warning("  [race] Processing error for %s: %s", api, e)
                elif any(p in api for p in ("Race", "race")):
                    log.warning(
                        "  [race] Race-related API '%s' had no decoded msgpack data "
                        "(raw_bytes_len=%s)",
                        api,
                        record.get("raw_bytes_len", "N/A"),
                    )

            # ── Accumulate dump-hook race frame data ───────────────────
            # Records from RaceSimulateHorseFrameData.Deserialize are
            # accumulated and batch-processed at session end.
            if domain == "race":
                event_type = record.get("event", "")
                if event_type == "dump" and "RaceSimulateHorseFrameData" in record.get("class", ""):
                    _dump_frame_records.append(record)
                elif event_type == "race_lifecycle":
                    _race_lifecycle_records.append(record)
                elif event_type == "race_skill_activate":
                    _race_skill_records.append(record)

            if session_data:
                session_data.write(domain, record)

    elif msg_type == "error":
        has_error = True
        log.error("  [X] JS Error: %s", message.get("description", ""))
        js_log.error("[JS ERROR] %s", message.get("description", ""))
        stack = message.get("stack")
        if stack:
            for line in str(stack).splitlines()[:5]:
                log.error("      %s", line)
                js_log.error("  %s", line)

    elif msg_type == "log":
        # Verbose JS console output -> file only, not console
        js_log.info("%s", message.get("payload", ""))


# ── Main ───────────────────────────────────────────────────────────────────


def main():
    global session_data

    log.info("=" * 60)
    log.info("  Clairvoyance — Collector")
    log.info("=" * 60)
    log.info("")
    log.info("  Modules: %s", ", ".join(args.modules))
    if args.label:
        log.info("  Label: %s", args.label)
    log.info("")

    # Create session
    session_data = Session(label=args.label)

    # Attach to game
    frida_session = attach()
    if frida_session is None:
        sys.exit(1)

    try:
        src = build_collector_script(args.modules)
        script = frida_session.create_script(src, runtime="v8")
        script.on("message", on_message)
        log.info("[*] Loading hooks...")
        script.load()
    except Exception as e:
        log.error("[X] Failed to load script: %s: %s", type(e).__name__, e)
        traceback.print_exc()
        sys.exit(1)

    # Wait for hooks to be ready
    for _ in range(60):
        time.sleep(0.5)
        if is_ready or has_error:
            break

    if has_error:
        log.error("\n[X] Script failed.")
        sys.exit(1)

    total_hooks = sum(hook_statuses.values())
    log.info("")
    log.info("  %d total hooks active across %d modules.", total_hooks, len(hook_statuses))
    log.info("  Session: %s", session_data.dir)
    log.info("")
    log.info("  Collecting data — play the game!")
    log.info("  Ctrl+C to stop.")
    log.info("")

    # Status ticker
    try:
        tick = 0
        duration = args.timeout if args.timeout > 0 else 999999
        while tick < duration:
            time.sleep(10)
            tick += 10
            if has_error:
                break
            counts = session_data.counts
            if counts:
                parts = [f"{k}: {v}" for k, v in sorted(counts.items())]
                log.info("  [%ds] Collected - %s", tick, " | ".join(parts))
            else:
                log.info("  [%ds] Waiting for game events...", tick)
    except KeyboardInterrupt:
        log.info("\n[*] Stopped by user.")

    # ── Process accumulated dump-hook race frames ────────────────────────
    log.info(
        "  [race-dump] Accumulated: %d frame records, %d lifecycle, %d skill",
        len(_dump_frame_records),
        len(_race_lifecycle_records),
        len(_race_skill_records),
    )
    if _dump_frame_records:
        log.info(
            "  [race-dump] Processing %d accumulated frame records...",
            len(_dump_frame_records),
        )
        try:
            race_analysis = process_dump_race_frames(
                _dump_frame_records,
                lifecycle_records=_race_lifecycle_records or None,
                skill_records=_race_skill_records or None,
            )
            if race_analysis and session_data:
                session_data.write("race", race_analysis)
                log.info("  [race-dump] Race analysis written to race.jsonl")
        except Exception as e:
            log.warning("  [race-dump] Failed to process dump frames: %s", e)

    # Save manifest and close
    session_data.write_manifest(
        modules=args.modules,
        hookStatuses=hook_statuses,
    )
    session_data.close()

    log.info("")
    log.info("  Session saved: %s", session_data.dir)
    counts = session_data.counts
    if counts:
        for k, v in sorted(counts.items()):
            log.info("    %s: %d records", k, v)
    log.info("")
    log.info("=" * 60)
    log.info("  Done.")
    log.info("  Log files:")
    log.info("    Main:    %s", LOG_FILE)
    log.info("    JS:      %s", JS_LOG_FILE)
    if has_error:
        log.info("  WARNING: Errors occurred — check logs above.")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
