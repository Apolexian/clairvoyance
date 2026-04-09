"""
Session Reader — read-only access to saved session data.

Enumerates session directories, parses manifests, and provides
lazy-loaded access to JSONL domain records.
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

log = logging.getLogger("clairvoyance")

if getattr(sys, "frozen", False):
    # Frozen (PyInstaller): sessions/ lives next to the .exe
    SESSIONS_DIR = Path(sys.executable).resolve().parent / "sessions"
else:
    SESSIONS_DIR = Path(__file__).resolve().parent.parent / "sessions"


@dataclass
class SessionInfo:
    """Metadata about a saved session."""

    name: str
    path: Path
    created: str = ""
    label: str = ""
    counts: dict[str, int] = field(default_factory=dict)
    modules: list[str] = field(default_factory=list)
    hook_statuses: dict[str, int] = field(default_factory=dict)

    @property
    def created_dt(self) -> datetime | None:
        try:
            return datetime.fromisoformat(self.created)
        except (ValueError, TypeError):
            return None

    @property
    def total_records(self) -> int:
        return sum(self.counts.values())


def list_sessions() -> list[SessionInfo]:
    """List all saved sessions, newest first."""
    if not SESSIONS_DIR.exists():
        return []

    sessions = []
    for d in sorted(SESSIONS_DIR.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        manifest_path = d / "manifest.json"
        info = SessionInfo(name=d.name, path=d)

        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                info.created = manifest.get("created", "")
                info.counts = manifest.get("counts", {})
                info.modules = manifest.get("modules", [])
                info.hook_statuses = manifest.get("hookStatuses", {})
            except Exception as e:
                log.warning("Failed to read manifest %s: %s", manifest_path, e)

        # Extract label from directory name (format: YYYY-MM-DDTHH-MM-SS_label)
        parts = d.name.split("_", 1)
        if len(parts) > 1:
            info.label = parts[1]

        sessions.append(info)

    return sessions


def get_session(name: str) -> SessionInfo | None:
    """Get a specific session by directory name."""
    session_dir = SESSIONS_DIR / name
    if not session_dir.is_dir():
        return None

    for s in list_sessions():
        if s.name == name:
            return s
    return None


def read_domain(session_name: str, domain: str) -> list[dict]:
    """Read all records from a session's domain JSONL file."""
    path = SESSIONS_DIR / session_name / f"{domain}.jsonl"
    if not path.exists():
        return []

    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def _normalize_api_race_frames(race: dict) -> None:
    """
    Convert API race simulation frames into the sampled_frames format
    used by dump races, so charts render uniformly for both sources.

    Also enriches horse_summaries with pace_down_segments from the
    race-level dict (API races store them separately).

    API format:  simulation.frames[].{time, horses[].{distance, speed, hp, ...}}
    Target:      sampled_frames[].{frame_index, horse_0: {distance, speed, hp}, ...}
    """
    # ── Normalize sampled frames ───────────────────────────────────
    sim = race.get("simulation")
    if sim and isinstance(sim, dict) and not race.get("sampled_frames"):
        frames = sim.get("frames")
        if frames and isinstance(frames, list):
            sampled = []
            step = max(1, len(frames) // 30)
            for i in range(0, len(frames), step):
                f = frames[i]
                entry: dict = {"frame_index": i}
                horses = f.get("horses", [])
                for hi, h in enumerate(horses):
                    entry[f"horse_{hi}"] = {
                        "distance": h.get("distance", 0),
                        "speed": h.get("speed", 0),
                        "hp": h.get("hp", 0),
                        "temptation": h.get("temptation_mode", "NULL"),
                    }
                sampled.append(entry)
            race["sampled_frames"] = sampled

    # ── Attach pace_down_segments to each horse summary ────────────
    pd_segments = race.get("pace_down_segments", {})
    summaries = race.get("horse_summaries", [])
    if pd_segments and summaries:
        for h in summaries:
            idx = str(h.get("horse_index", ""))
            if idx in pd_segments and not h.get("pace_down_segments"):
                h["pace_down_segments"] = pd_segments[idx]


def get_races(session_name: str) -> list[dict]:
    """
    Extract race records from a session.

    Returns a list of race dicts, each containing:
    - Race simulation data (from API)
    - Dump-based race analysis (from frame hooks)

    If the session has raw dump records but no pre-processed analysis
    (e.g. process was killed before cleanup), we assemble the analysis
    on the fly.
    """
    records = read_domain(session_name, "race")

    races = []
    race_idx = 0
    has_analysis = False

    # Accumulators for on-the-fly processing
    dump_frame_records: list[dict] = []
    lifecycle_records: list[dict] = []
    skill_records: list[dict] = []

    for rec in records:
        event = rec.get("event", "")

        if event == "race_simulation":
            # API-based race
            race_idx += 1
            rec["_race_index"] = race_idx
            rec["_race_label"] = f"Race {race_idx} ({rec.get('api', 'unknown')})"
            rec["_source"] = "api"
            _normalize_api_race_frames(rec)
            # Drop heavy raw data after extracting what we need
            rec.pop("simulation", None)
            rec.pop("raw_b64", None)
            rec.pop("msgpack_decoded", None)
            races.append(rec)

        elif event == "race_analysis_from_dump":
            # Dump-hook assembled race (pre-processed at session end)
            has_analysis = True
            race_idx += 1
            rec["_race_index"] = race_idx
            num_horses = rec.get("num_horses", "?")
            dist = rec.get("estimated_total_distance", "?")
            rec["_race_label"] = f"Race {race_idx} (dump, {num_horses} horses, {dist}m)"
            rec["_source"] = "dump"
            races.append(rec)

        elif event == "dump" and "RaceSimulateHorseFrameData" in rec.get("class", ""):
            dump_frame_records.append(rec)
        elif event == "race_lifecycle":
            lifecycle_records.append(rec)
        elif event == "race_skill_activate":
            skill_records.append(rec)

    # If we have raw dump records but no pre-processed analysis, assemble now
    if dump_frame_records and not has_analysis:
        try:
            from .race_processor import process_dump_race_frames

            analysis = process_dump_race_frames(
                dump_frame_records,
                lifecycle_records=lifecycle_records or None,
                skill_records=skill_records or None,
            )
            if analysis:
                race_idx += 1
                analysis["_race_index"] = race_idx
                num_horses = analysis.get("num_horses", "?")
                dist = analysis.get("estimated_total_distance", "?")
                analysis["_race_label"] = f"Race {race_idx} (dump, {num_horses} horses, {dist}m)"
                analysis["_source"] = "dump"
                races.append(analysis)
                log.info(
                    "Assembled race from %d raw dump records: %d horses, %d frames",
                    len(dump_frame_records),
                    analysis.get("num_horses", 0),
                    analysis.get("total_frames", 0),
                )
        except Exception as e:
            log.warning("Failed to assemble race from raw dump records: %s", e)

    return races


def get_race_replay_data(session_name: str, race_idx: int) -> dict | None:
    """
    Build replay-ready data for a specific race.

    Returns ALL frames (not sampled) plus skill activations and metadata,
    structured for the canvas replay animation.
    """
    records = read_domain(session_name, "race")

    # Find the target race
    current_idx = 0
    target = None
    for rec in records:
        event = rec.get("event", "")
        if event in ("race_simulation", "race_analysis_from_dump"):
            current_idx += 1
            if current_idx == race_idx:
                target = rec
                break

    if target is None:
        return None

    event = target.get("event", "")
    replay: dict = {
        "race_index": race_idx,
        "source": "api" if event == "race_simulation" else "dump",
        "frames": [],
        "skills": [],
        "phases": target.get("phases", {}),
        "horse_summaries": target.get("horse_summaries", []),
        "total_distance": 0,
        "num_horses": 0,
    }

    if event == "race_simulation":
        # API race — extract ALL frames from simulation (not sampled)
        sim = target.get("simulation", {})
        if isinstance(sim, dict):
            raw_frames = sim.get("frames", [])
            for i, f in enumerate(raw_frames):
                horses = f.get("horses", [])
                frame: dict = {"idx": i, "time": f.get("time", 0)}
                for hi, h in enumerate(horses):
                    frame[hi] = {
                        "d": round(h.get("distance", 0), 2),
                        "s": h.get("speed", 0),
                        "hp": h.get("hp", 0),
                        "t": h.get("temptation_mode", "NULL"),
                        "lane": h.get("lane_position", 0),
                    }
                replay["frames"].append(frame)
            replay["num_horses"] = len(raw_frames[0].get("horses", [])) if raw_frames else 0

        # Skills with frame_time
        replay["skills"] = target.get("skill_activations", [])
        phases = target.get("phases", {})
        replay["total_distance"] = phases.get("total_distance", 0)

    elif event == "race_analysis_from_dump":
        # Dump race — rebuild all frames from the sampled data
        # The dump processor only stores ~30 samples, but that's what we have
        sampled = target.get("sampled_frames", [])
        num_horses = target.get("num_horses", 0)
        for sf in sampled:
            frame = {"idx": sf.get("frame_index", 0), "time": sf.get("frame_index", 0)}
            for hi in range(num_horses):
                hdata = sf.get(f"horse_{hi}", {})
                frame[hi] = {
                    "d": hdata.get("distance", 0),
                    "s": hdata.get("speed", 0),
                    "hp": hdata.get("hp", 0),
                    "t": hdata.get("temptation", "NULL"),
                    "lane": 0,
                }
            replay["frames"].append(frame)
        replay["num_horses"] = num_horses
        replay["total_distance"] = target.get("estimated_total_distance", 0)
        replay["skills"] = target.get("skill_activations", [])

    return replay


def get_network_events(session_name: str) -> list[dict]:
    """Get network events with summary info."""
    records = read_domain(session_name, "network")
    events = []
    for rec in records:
        summary = {
            "event": rec.get("event", ""),
            "api": rec.get("api", ""),
            "task": rec.get("task", ""),
            "_ts": rec.get("_ts", ""),
        }
        # Extract key game state if present
        decoded = rec.get("msgpack_decoded", {})
        if isinstance(decoded, dict):
            data = decoded.get("data", {})
            if isinstance(data, dict):
                chara = data.get("chara_info", {})
                if isinstance(chara, dict) and chara.get("speed"):
                    summary["chara_stats"] = {
                        "speed": chara.get("speed"),
                        "stamina": chara.get("stamina"),
                        "power": chara.get("pow") or chara.get("power"),
                        "guts": chara.get("guts"),
                        "wiz": chara.get("wiz"),
                        "vital": chara.get("vital"),
                        "turn": chara.get("turn"),
                        "fans": chara.get("fans"),
                        "motivation": chara.get("motivation"),
                    }
        events.append(summary)
    return events


def get_timeline(session_name: str) -> list[dict]:
    """
    Build a unified timeline of all events across domains.

    Returns events sorted by timestamp, tagged with their domain.
    """
    timeline = []

    # Network events
    for rec in read_domain(session_name, "network"):
        timeline.append(
            {
                "domain": "network",
                "event": rec.get("event", ""),
                "api": rec.get("api", ""),
                "_ts": rec.get("_ts", ""),
                "is_race": any(
                    p in rec.get("api", "")
                    for p in [
                        "RaceStart",
                        "RaceResult",
                        "RaceEntry",
                    ]
                ),
            }
        )

    # Race events
    for rec in read_domain(session_name, "race"):
        event_type = rec.get("event", "")
        entry = {
            "domain": "race",
            "event": event_type,
            "_ts": rec.get("_ts", ""),
            "is_race": True,
        }
        if event_type == "dump":
            entry["class"] = rec.get("class", "")
        elif event_type in ("race_simulation", "race_analysis_from_dump"):
            entry["highlight"] = True
        timeline.append(entry)

    # Sort by timestamp
    timeline.sort(key=lambda e: e.get("_ts", ""))

    return timeline
