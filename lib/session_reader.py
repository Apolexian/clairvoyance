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

    Also enriches horse_summaries with rushed_segments from the
    race-level dict (API races store them separately).

    The binary sim stores speed as uint16 (x100) and lane_position as
    uint16 (0-10000).  We normalise to the same scale the dump hooks
    produce: speed in m/s (float) and lane_position 0.0-1.0.

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
                entry: dict = {"frame_index": i, "time": f.get("time", 0)}
                horses = f.get("horses", [])
                for hi, h in enumerate(horses):
                    entry[f"horse_{hi}"] = {
                        "distance": h.get("distance", 0),
                        "speed": round(h.get("speed", 0) / 100, 2),
                        "hp": h.get("hp", 0),
                        "temptation": h.get("temptation_mode", "NULL"),
                    }
                sampled.append(entry)
            race["sampled_frames"] = sampled

    # ── Attach rushed_segments to each horse summary ───────────────
    rs_segments = race.get("rushed_segments", {})
    summaries = race.get("horse_summaries", [])
    if rs_segments and summaries:
        for h in summaries:
            idx = str(h.get("horse_index", ""))
            if idx in rs_segments and not h.get("rushed_segments"):
                h["rushed_segments"] = rs_segments[idx]

    # ── Attach pace_down_segments to each horse summary ──────────
    pd_segments = race.get("pace_down_segments", {})
    if pd_segments and summaries:
        for h in summaries:
            idx = str(h.get("horse_index", ""))
            if idx in pd_segments and not h.get("pace_down_segments"):
                h["pace_down_segments"] = pd_segments[idx]


def get_races(session_name: str) -> list[dict]:
    """
    Extract race records from a session.

    API races (``race_simulation``) are preferred — they contain the full
    binary sim with skill activations, finish results, compete events, etc.
    Dump-based races are only used as a fallback when no API race was captured.
    """
    records = read_domain(session_name, "race")

    api_races: list[dict] = []
    dump_analyses: list[dict] = []

    # Accumulators for on-the-fly dump assembly (fallback only)
    dump_frame_records: list[dict] = []
    lifecycle_records: list[dict] = []
    skill_records: list[dict] = []

    for rec in records:
        event = rec.get("event", "")

        if event == "race_simulation":
            rec["_source"] = "api"
            _normalize_api_race_frames(rec)
            # Drop heavy raw data after extracting what we need
            rec.pop("simulation", None)
            rec.pop("raw_b64", None)
            rec.pop("msgpack_decoded", None)
            api_races.append(rec)

        elif event == "race_analysis_from_dump":
            rec["_source"] = "dump"
            dump_analyses.append(rec)

        elif event == "dump" and "RaceSimulateHorseFrameData" in rec.get("class", ""):
            dump_frame_records.append(rec)
        elif event == "race_lifecycle":
            lifecycle_records.append(rec)
        elif event == "race_skill_activate":
            skill_records.append(rec)

    # ── Decide which source to use ─────────────────────────────────
    if api_races:
        # API data is authoritative — skip dump races entirely
        races = api_races
        if dump_analyses or dump_frame_records:
            log.info(
                "Using %d API race(s), ignoring dump data (%d analyses, %d raw records)",
                len(api_races),
                len(dump_analyses),
                len(dump_frame_records),
            )
    elif dump_analyses:
        # Pre-processed dump analyses (no API data available)
        races = dump_analyses
    elif dump_frame_records:
        # Raw dump records — assemble on the fly
        races = []
        try:
            from .race_processor import process_dump_race_frames

            analysis = process_dump_race_frames(
                dump_frame_records,
                lifecycle_records=lifecycle_records or None,
                skill_records=skill_records or None,
            )
            if analysis:
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
    else:
        races = []

    # ── Number and label all races ─────────────────────────────────
    for idx, rec in enumerate(races, 1):
        rec["_race_index"] = idx
        if rec["_source"] == "api":
            meta = rec.get("race_metadata", {})
            parts = [f"Race {idx}"]
            if meta.get("program_id"):
                parts.append(f"pgm:{meta['program_id']}")
            parts.append(rec.get("api", "unknown"))
            rec["_race_label"] = " · ".join(parts)
        else:
            num_horses = rec.get("num_horses", "?")
            dist = rec.get("estimated_total_distance", "?")
            rec["_race_label"] = f"Race {idx} (dump, {num_horses} horses, {dist}m)"

    return races


def get_race_replay_data(session_name: str, race_idx: int) -> dict | None:
    """
    Build replay-ready data for a specific race.

    Returns ALL frames (not sampled) plus skill activations and metadata,
    structured for the canvas replay animation.

    Uses the same API-first preference as :func:`get_races`.
    """
    records = read_domain(session_name, "race")

    # Collect races with API-first preference (mirrors get_races logic)
    api_races: list[dict] = []
    dump_races: list[dict] = []
    for rec in records:
        event = rec.get("event", "")
        if event == "race_simulation":
            api_races.append(rec)
        elif event == "race_analysis_from_dump":
            dump_races.append(rec)

    races = api_races if api_races else dump_races

    if race_idx < 1 or race_idx > len(races):
        return None

    target = races[race_idx - 1]
    event = target.get("event", "")

    replay: dict = {
        "race_index": race_idx,
        "source": "api" if event == "race_simulation" else "dump",
        "frames": [],
        "skills": [],
        "compete_events": target.get("compete_events", []),
        "rushed_segments": target.get("rushed_segments", {}),
        "pace_down_segments": target.get("pace_down_segments", {}),
        "phases": target.get("phases", {}),
        "horse_summaries": target.get("horse_summaries", []),
        "horses": target.get("horses", []),
        "race_metadata": target.get("race_metadata", {}),
        "total_distance": 0,
        "num_horses": 0,
    }

    # ── Temptation mode id mapping (string → int) ──────────────────
    _TEMPT_STR_TO_ID = {
        "NULL": 0,
        "POSITION_SASHI": 1,
        "POSITION_SENKO": 2,
        "POSITION_NIGE": 3,
        "BOOST": 4,
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
                    t_str = h.get("temptation_mode", "NULL")
                    t_id = (
                        _TEMPT_STR_TO_ID.get(t_str, 0) if isinstance(t_str, str) else (t_str or 0)
                    )
                    frame[str(hi)] = {
                        "d": round(h.get("distance", 0), 2),
                        "s": round(h.get("speed", 0) / 100, 2),
                        "hp": h.get("hp", 0),
                        "t": t_str,
                        "t_id": t_id,
                        "lane": round(h.get("lane_position", 0) / 10000, 4),
                        "blk": h.get("block_front_horse_index", -1),
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
            fi = sf.get("frame_index", 0)
            frame = {"idx": fi, "time": fi / 15.0}  # simulation runs at ~15fps
            for hi in range(num_horses):
                hdata = sf.get(f"horse_{hi}", {})
                t_val = hdata.get("temptation", "NULL")
                t_id = _TEMPT_STR_TO_ID.get(t_val, 0) if isinstance(t_val, str) else (t_val or 0)
                frame[str(hi)] = {
                    "d": hdata.get("distance", 0),
                    "s": hdata.get("speed", 0),
                    "hp": hdata.get("hp", 0),
                    "t": t_val,
                    "t_id": t_id,
                    "lane": 0,
                    "blk": -1,
                }
            replay["frames"].append(frame)
        replay["num_horses"] = num_horses
        replay["total_distance"] = target.get("estimated_total_distance", 0)
        replay["skills"] = target.get("skill_activations", [])

    return replay


# Keys that contain PII or non-game device/auth data — stripped from detail views
_PII_KEYS = frozenset(
    {
        "viewer_id",
        "device",
        "device_id",
        "device_name",
        "graphics_device_name",
        "ip_address",
        "platform_os_version",
        "carrier",
        "keychain",
        "button_info",
        "dmm_viewer_id",
        "dmm_onetime_token",
        "steam_id",
        "steam_session_ticket",
        "sid",  # session token
        "owner_viewer_id",  # friend viewer ids in support cards
        "locale",
    }
)

# Top-level record keys to drop entirely (binary blobs, internal metadata)
_DROP_TOP_KEYS = frozenset({"raw_b64", "taskFields", "postDataBytes"})


def _strip_pii(obj: object) -> object:
    """Recursively strip PII / device keys from a JSON-like structure."""
    if isinstance(obj, dict):
        return {k: _strip_pii(v) for k, v in obj.items() if k not in _PII_KEYS}
    if isinstance(obj, list):
        return [_strip_pii(item) for item in obj]
    return obj


def get_network_events(session_name: str) -> dict:
    """
    Get all network events with rich summary info and aggregate stats.

    Returns ``{"events": [...], "stats": {...}}`` where each event has:
      _idx, event, direction, api, task, formatter, httpUrl, httpMethod,
      bytes, has_decoded, raw_bytes_len, _reqId, _pair_idx, _ts, chara_stats
    """
    records = read_domain(session_name, "network")
    events: list[dict] = []

    # ── Pass 1: build summary for every record ────────────────────
    total_bytes = 0
    decoded_count = 0
    type_counts: dict[str, int] = {}
    api_set: set[str] = set()

    for idx, rec in enumerate(records):
        event_type = rec.get("event", "")
        type_counts[event_type] = type_counts.get(event_type, 0) + 1

        # Compute byte size from whichever field is available:
        #  - "bytes" / "captured": low-level hooks (ssl_read, libnative_*, schannel_*)
        #  - "postDataBytes": api_send (Task.Send hook)
        #  - "raw_bytes_len": set by collect.py when msgpack decode fails
        #  - raw_b64: base64-encoded binary payload (actual wire bytes)
        raw_bytes = rec.get("bytes") or rec.get("raw_bytes_len") or 0
        if not raw_bytes:
            raw_bytes = rec.get("postDataBytes") or 0
        if not raw_bytes:
            b64 = rec.get("raw_b64")
            if b64 and isinstance(b64, str):
                # base64 encodes 3 bytes → 4 chars; approximate original size
                raw_bytes = len(b64) * 3 // 4
        total_bytes += raw_bytes

        has_decoded = "msgpack_decoded" in rec
        if has_decoded:
            decoded_count += 1

        api = rec.get("api", "")
        if api:
            api_set.add(api)

        summary: dict = {
            "_idx": idx,
            "event": event_type,
            "direction": rec.get("direction", ""),
            "api": api,
            "task": rec.get("task", ""),
            "formatter": rec.get("formatter", ""),
            "httpUrl": rec.get("httpUrl", ""),
            "httpMethod": rec.get("httpMethod", ""),
            "bytes": raw_bytes,
            "captured": rec.get("captured") or raw_bytes,
            "truncated": rec.get("truncated", False),
            "has_decoded": has_decoded,
            "raw_bytes_len": rec.get("raw_bytes_len", 0),
            "_reqId": rec.get("_reqId"),
            "_seq": rec.get("_seq"),
            "_pair_idx": None,
            "_ts": rec.get("_ts", ""),
        }

        # Extract key game state if present (for chara_stats inline display)
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

        # For formatter events, derive a short "API-like" label
        if not api and summary["formatter"]:
            # Gallop_SingleModeFreeChoiceRewardRequest → SingleModeFreeChoiceReward
            short = summary["formatter"].replace("Gallop_", "").replace("Gallop.", "")
            for suffix in ("Request", "Response"):
                if short.endswith(suffix):
                    short = short[: -len(suffix)]
                    break
            summary["_label"] = short

        events.append(summary)

    # ── Pass 2: pair api_send ↔ api_response ──────────────────────
    # Strategy: use _reqId when available (new sessions), fall back to
    # matching api name (legacy sessions).
    pending_by_reqid: dict[int, int] = {}  # reqId → event idx
    pending_by_api: dict[str, int] = {}  # apiName → event idx (fallback)

    for ev in events:
        event_type = ev["event"]
        req_id = ev.get("_reqId")
        api = ev["api"]

        if event_type == "api_send":
            if req_id is not None:
                pending_by_reqid[req_id] = ev["_idx"]
            if api:
                pending_by_api[api] = ev["_idx"]

        elif event_type in ("api_response", "api_error"):
            paired_idx = None
            # Try reqId match first
            if req_id is not None and req_id in pending_by_reqid:
                paired_idx = pending_by_reqid.pop(req_id)
            # Fallback: match by api name
            elif api and api in pending_by_api:
                paired_idx = pending_by_api.pop(api)

            if paired_idx is not None:
                ev["_pair_idx"] = paired_idx
                events[paired_idx]["_pair_idx"] = ev["_idx"]

    # ── Build aggregate stats ─────────────────────────────────────
    total = len(events)
    stats = {
        "total": total,
        "type_counts": type_counts,
        "total_bytes": total_bytes,
        "decoded_count": decoded_count,
        "decode_rate": round(decoded_count / total * 100, 1) if total else 0,
        "distinct_apis": len(api_set),
        "direction_counts": {
            "in": sum(1 for e in events if e["direction"] == "in"),
            "out": sum(1 for e in events if e["direction"] == "out"),
            "unknown": sum(1 for e in events if not e["direction"]),
        },
    }

    return {"events": events, "stats": stats}


def get_network_event_detail(session_name: str, idx: int) -> dict | None:
    """
    Return the full cleaned data for a single network event (0-based index).

    Strips PII/device fields and binary blobs so the user sees only
    game-relevant data.  Also includes `_annotations` from master DB
    lookups for known ID fields (story_id, chara_id, skill_id, etc.).
    """
    records = read_domain(session_name, "network")
    if idx < 0 or idx >= len(records):
        return None

    rec = records[idx]
    # Build a clean copy without binary blobs and top-level noise
    cleaned: dict = {}
    for k, v in rec.items():
        if k in _DROP_TOP_KEYS:
            continue
        cleaned[k] = v

    # Strip PII recursively from the decoded payload
    if "msgpack_decoded" in cleaned:
        cleaned["msgpack_decoded"] = _strip_pii(cleaned["msgpack_decoded"])

    # Annotate known ID fields from master DB
    try:
        from . import master_db

        payload = cleaned.get("msgpack_decoded", cleaned)
        annotations = master_db.annotate_ids(payload)
        if annotations:
            cleaned["_annotations"] = annotations
    except Exception:
        pass  # master DB not available or error — no annotations

    return cleaned


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


def _extract_int(decoded: dict, data: dict, rec: dict, key: str):
    """Extract an integer field from decoded msgpack, data, responseFields, or fields.

    Checks multiple locations where the game protocol may place request/response
    fields.  Returns the value as int, or None if not found.
    """
    # Top-level decoded (request payloads have no 'data' wrapper)
    val = decoded.get(key) if isinstance(decoded, dict) else None
    if val is not None:
        return int(val)
    # Nested under 'data' (response payloads)
    if isinstance(data, dict):
        val = data.get(key)
        if val is not None:
            return int(val)
    # responseFields (read from typed Response object in JS hook)
    rf = rec.get("responseFields")
    if isinstance(rf, dict):
        val = rf.get(key)
        if val is not None:
            return int(val)
    # fields (read from MsgPack formatter hooks)
    f = rec.get("fields")
    if isinstance(f, dict):
        val = f.get(key)
        if val is not None:
            return int(val)
    return None


# ── Non-career context detection ───────────────────────────────────────
# APIs that belong to PvP / event modes, NOT to Single Mode career runs.
# Records matching these are skipped for career-specific extraction
# (support cards, training, stats) to avoid polluting the career summary.
_NON_CAREER_KEYWORDS = (
    "ChampionsRace",
    "RoomRace",
    "TeamStadiumRace",
    "LegendRace",
    "PracticeRace",
    "champions_race",
    "room_race",
    "team_stadium_race",
    "legend_race",
    "practice_race",
)


def _is_non_career_context(api: str) -> bool:
    """Return True if the API belongs to a non-career context (CM, PvP, etc.)."""
    if not api:
        return False
    # SingleMode APIs are always career context, even if they contain a
    # substring that looks non-career (e.g. SingleModeTeamRace...)
    if "SingleMode" in api or "single_mode" in api:
        return False
    return any(kw in api for kw in _NON_CAREER_KEYWORDS)


def _chara_matches(entry: dict, player_cid: int | None, player_card: int | None) -> bool:
    """Check if a race entry belongs to the player using multiple ID strategies.

    The game uses two ID schemes:
      - chara_id: base character (4-digit, e.g. 1001)
      - card_id:  outfit variant (6-digit, e.g. 100101)

    ``chara_info`` may populate ``chara_id`` with either form depending on
    the API version / scenario, while race results and horse data may use
    the other.  We try exact matches first, then cross-match by deriving
    the base character from the card_id (``card_id // 100``).
    """
    if not isinstance(entry, dict):
        return False

    e_cid = entry.get("chara_id")
    e_card = entry.get("card_id")

    # 1. Exact chara_id match
    if player_cid is not None and e_cid is not None and e_cid == player_cid:
        return True

    # 2. Exact card_id match
    if player_card is not None and e_card is not None and e_card == player_card:
        return True

    # 3. Cross-match: player_cid is actually a card_id (6-digit)
    #    and entry has the base chara_id, or vice-versa.
    try:
        if player_cid is not None and e_cid is not None:
            # player_cid is 6-digit card-style, entry has base chara
            if player_cid > 9999 and e_cid == player_cid // 100:
                return True
            # entry is 6-digit card-style, player has base chara
            if e_cid > 9999 and player_cid == e_cid // 100:
                return True

        # 4. Derive base from card_id fields
        if player_card is not None and e_cid is not None and player_card // 100 == e_cid:
            return True
        if player_cid is not None and e_card is not None and e_card // 100 == player_cid:
            return True
    except (TypeError, ValueError):
        pass

    return False


def _build_summary_from_records(records: list[dict]) -> dict:
    """
    Build a structured summary from a list of network event records.

    Extracts:
      - character info (name, card, latest stats, motivation, fans, turn)
      - support cards used
      - skills acquired
      - race results
      - training actions taken
      - stats progression over turns
    """

    summary: dict = {
        "chara_id": None,
        "card_id": None,
        "scenario_id": None,
        "support_card_ids": [],
        "friend_support_card_id": None,
        "latest_stats": {},
        "stats_history": [],  # [{turn, speed, stamina, power, guts, wiz, vital, fans}]
        "skills_acquired": [],  # [{skill_id, turn}]
        "skill_tips": [],  # [{skill_id, turn}]
        "race_results": [],  # [{turn, race_instance_id, result_order, api}]
        "training_actions": [],  # [{turn, command_id, api}]
        "events_seen": [],  # [{story_id, turn, api}]
        "event_choices": [],  # [{story_id, turn, choice_number, stat_deltas, _ts}]
        "training_partner_dist": {},  # {support_card_id: {command_id: count}}
        "total_api_calls": len(records),
        "api_breakdown": {},  # {api_name: count}
        "first_ts": None,
        "last_ts": None,
    }

    seen_skills: set[int] = set()
    seen_support: set[int] = set()

    # Mapping: partner/target_id → support_card_id (built from evaluation_info_array)
    _partner_to_sc: dict[int, int] = {}
    # Track which turns we already counted (avoid double-counting from multiple APIs per turn)
    _dist_seen_turns: set[int] = set()

    # For computing stat deltas around choice events: track the last stats snapshot
    _STAT_KEYS = ("speed", "stamina", "power", "guts", "wiz", "vital", "skill_point", "motivation")
    _last_stats: dict[str, int] = {}
    # Pending choice: we see the request first, then the response with updated stats
    _pending_choice: dict | None = None

    for rec in records:
        raw_api = rec.get("api", "")
        # Derive API-like label from formatter when api is missing
        # (msgpack_serialize / msgpack_deserialize events use formatter)
        api = raw_api
        if not api:
            fmt = rec.get("formatter", "")
            if fmt:
                short = fmt.replace("Gallop_", "").replace("Gallop.", "")
                for suffix in ("Request", "Response"):
                    if short.endswith(suffix):
                        short = short[: -len(suffix)]
                        break
                api = short
        ts = rec.get("_ts", "")

        # Track first/last timestamps
        if ts:
            if summary["first_ts"] is None:
                summary["first_ts"] = ts
            summary["last_ts"] = ts

        # Count API calls (only real api field, not formatter-derived)
        if raw_api:
            summary["api_breakdown"][raw_api] = summary["api_breakdown"].get(raw_api, 0) + 1

        decoded = rec.get("msgpack_decoded", {})
        if not isinstance(decoded, dict):
            continue
        data = decoded.get("data", {})
        if not isinstance(data, dict):
            continue

        # ── Skip non-career records for career-specific fields ─────
        # PvP / Champions Meeting / Room Match / Team Stadium / Legend Race
        # records may appear mid-career.  We don't know which runner is
        # the player's so we only record that a race happened (no result).
        # The user can see full details via the Detected Races links.
        if _is_non_career_context(api):
            # Only log one entry per race (result APIs, not start APIs)
            if "Result" in api or "result" in api:
                summary.setdefault("_non_career_races", []).append(
                    {
                        "api": api,
                        "_ts": ts,
                    }
                )
            continue

        # ── Character info ──────────────────────────────────────
        chara = data.get("chara_info", {})
        if isinstance(chara, dict) and chara.get("speed"):
            cid = chara.get("chara_id")
            card = chara.get("card_id")
            if cid and not summary["chara_id"]:
                summary["chara_id"] = cid
            if card and not summary["card_id"]:
                summary["card_id"] = card

            turn = chara.get("turn", 0)
            stats_snap = {
                "turn": turn,
                "speed": chara.get("speed", 0),
                "stamina": chara.get("stamina", 0),
                "power": chara.get("pow") or chara.get("power", 0),
                "guts": chara.get("guts", 0),
                "wiz": chara.get("wiz", 0),
                "vital": chara.get("vital", 0),
                "max_vital": chara.get("max_vital", 0),
                "fans": chara.get("fans", 0),
                "motivation": chara.get("motivation", 0),
                "skill_point": chara.get("skill_point", 0),
            }
            summary["latest_stats"] = stats_snap

            # Avoid duplicating turns in history
            if not summary["stats_history"] or summary["stats_history"][-1].get("turn") != turn:
                summary["stats_history"].append(stats_snap)

            # ── Compute stat deltas if we have a pending choice ──
            if _pending_choice is not None:
                deltas: dict[str, int] = {}
                for k in _STAT_KEYS:
                    new_val = stats_snap.get(k, 0)
                    old_val = _last_stats.get(k, 0)
                    diff = new_val - old_val
                    if diff != 0:
                        deltas[k] = diff
                _pending_choice["stat_deltas"] = deltas
                _pending_choice["turn"] = turn
                summary["event_choices"].append(_pending_choice)
                _pending_choice = None

            # Snapshot current stats for future delta computation
            _last_stats = {k: stats_snap.get(k, 0) for k in _STAT_KEYS}

            # Skills on the chara
            skill_array = chara.get("skill_array", [])
            if isinstance(skill_array, list):
                for sk in skill_array:
                    if isinstance(sk, dict):
                        sid = sk.get("skill_id")
                        if sid and sid not in seen_skills:
                            seen_skills.add(sid)
                            summary["skills_acquired"].append({"skill_id": sid, "turn": turn})

            # Skill tips (hints)
            skill_tips = chara.get("skill_tips_array", [])
            if isinstance(skill_tips, list):
                for tip in skill_tips:
                    if isinstance(tip, dict):
                        sid = tip.get("skill_id")
                        if sid and sid not in seen_skills:
                            summary["skill_tips"].append({"skill_id": sid, "turn": turn})

        # ── Scenario id ─────────────────────────────────────────
        if data.get("single_mode_scenario_id") and not summary["scenario_id"]:
            summary["scenario_id"] = data["single_mode_scenario_id"]

        # ── Support cards ───────────────────────────────────────
        # Method 1: support_card_array / support_card_deck_array (array of objects)
        #   Present in start-of-career APIs (SingleModeStart, SingleModeFreeStart, etc.)
        support_array = data.get("support_card_array") or data.get("support_card_deck_array", [])
        if isinstance(support_array, list):
            for sc in support_array:
                if isinstance(sc, dict):
                    scid = sc.get("support_card_id")
                    if scid and scid not in seen_support:
                        seen_support.add(scid)
                        summary["support_card_ids"].append(scid)

        # Method 2: support_card_ids (plain array of ints, e.g. SingleModeFreeStart)
        sc_ids = data.get("support_card_ids")
        if isinstance(sc_ids, list):
            for scid in sc_ids:
                if isinstance(scid, int) and scid and scid not in seen_support:
                    seen_support.add(scid)
                    summary["support_card_ids"].append(scid)

        # Method 3: chara_info.support_card_array (inside the character data)
        #   When continuing a career, the deck is often nested in chara_info.
        if isinstance(chara, dict):
            chara_sc_array = chara.get("support_card_array") or chara.get("support_card_list", [])
            if isinstance(chara_sc_array, list):
                for sc in chara_sc_array:
                    if isinstance(sc, dict):
                        scid = sc.get("support_card_id")
                        if scid and scid not in seen_support:
                            seen_support.add(scid)
                            summary["support_card_ids"].append(scid)

        # Method 4: evaluation_info_array — training partners map to support cards
        #   Can appear at data level or nested under team_data_set (Aoharu).
        eval_sources = [data.get("evaluation_info_array", [])]
        tds = data.get("team_data_set")
        if isinstance(tds, dict):
            eval_sources.append(tds.get("evaluation_info_array", []))
        for eval_array in eval_sources:
            if not isinstance(eval_array, list):
                continue
            for ei in eval_array:
                if isinstance(ei, dict):
                    scid = ei.get("support_card_id")
                    target = ei.get("target_id")
                    # Build partner→support_card mapping for distribution tracking
                    if target and scid:
                        _partner_to_sc[target] = scid
                    if scid and scid not in seen_support:
                        seen_support.add(scid)
                        summary["support_card_ids"].append(scid)

        # Method 5: home_info may contain support card data
        home_info = data.get("home_info", {})
        if isinstance(home_info, dict):
            home_sc = home_info.get("support_card_array") or home_info.get(
                "support_card_deck_array", []
            )
            if isinstance(home_sc, list):
                for sc in home_sc:
                    if isinstance(sc, dict):
                        scid = sc.get("support_card_id")
                        if scid and scid not in seen_support:
                            seen_support.add(scid)
                            summary["support_card_ids"].append(scid)

        # Method 6: trained_chara_info (race/evaluation contexts)
        trained_chara = data.get("trained_chara_info", {})
        if isinstance(trained_chara, dict):
            tc_sc = trained_chara.get("support_card_array") or trained_chara.get(
                "support_card_list", []
            )
            if isinstance(tc_sc, list):
                for sc in tc_sc:
                    if isinstance(sc, dict):
                        scid = sc.get("support_card_id")
                        if scid and scid not in seen_support:
                            seen_support.add(scid)
                            summary["support_card_ids"].append(scid)

        # Method 7: trained_chara_array (multi-chara contexts like Champions Meeting)
        trained_array = data.get("trained_chara_array", [])
        if isinstance(trained_array, list):
            for tc in trained_array:
                if isinstance(tc, dict):
                    tc_sc = tc.get("support_card_list") or tc.get("support_card_array", [])
                    if isinstance(tc_sc, list):
                        for sc in tc_sc:
                            if isinstance(sc, dict):
                                scid = sc.get("support_card_id")
                                if scid and scid not in seen_support:
                                    seen_support.add(scid)
                                    summary["support_card_ids"].append(scid)

        # Friend (borrowed) support card
        friend_sc = data.get("friend_support_card_info")
        if isinstance(friend_sc, dict) and not summary["friend_support_card_id"]:
            fid = friend_sc.get("support_card_id")
            if fid:
                summary["friend_support_card_id"] = fid
        # Also check for friend card in top-level decoded (some API formats)
        if not summary["friend_support_card_id"]:
            friend_sc2 = decoded.get("friend_support_card_info")
            if isinstance(friend_sc2, dict):
                fid = friend_sc2.get("support_card_id")
                if fid:
                    summary["friend_support_card_id"] = fid

        # ── Training partner distribution ──────────────────────────
        # command_info_array lists each training type and which partners
        # are present.  Combined with the partner→support_card mapping from
        # evaluation_info_array, we build {sc_id: {command_id: count}}.
        # command_id: 101=Speed, 102=Stamina, 103=Power, 105=Guts, 106=Wiz
        cmd_array = data.get("command_info_array", [])
        if isinstance(cmd_array, list) and _partner_to_sc:
            turn = chara.get("turn", 0) if isinstance(chara, dict) else 0
            if turn and turn not in _dist_seen_turns:
                _dist_seen_turns.add(turn)
                dist = summary["training_partner_dist"]
                for cmd in cmd_array:
                    if not isinstance(cmd, dict):
                        continue
                    cid = cmd.get("command_id")
                    if not cid:
                        continue
                    # Partners present at this training — try multiple known field names
                    partners = (
                        cmd.get("tips_event_partner_array")
                        or cmd.get("training_partner_array")
                        or []
                    )
                    if not isinstance(partners, list):
                        continue
                    for p in partners:
                        pid = (
                            p
                            if isinstance(p, int)
                            else (p.get("partner_id") if isinstance(p, dict) else None)
                        )
                        if pid is None:
                            continue
                        scid = _partner_to_sc.get(pid)
                        if scid:
                            sc_key = str(scid)
                            cmd_key = str(cid)
                            dist.setdefault(sc_key, {})
                            dist[sc_key][cmd_key] = dist[sc_key].get(cmd_key, 0) + 1

        # ── Race results ────────────────────────────────────────
        # Find the player's race result by matching chara_id / card_id.
        # The API may return results as:
        #   - race_result_info: single dict (usually the player in career)
        #   - race_result_array: list of all horses' results
        # We use _chara_matches() for robust matching across ID formats
        # (base chara_id vs outfit card_id).
        player_cid = summary.get("chara_id")
        player_card = summary.get("card_id")
        player_race_result = None

        # Check race_result_array first (list of all horses)
        race_arr = data.get("race_result_array")
        if isinstance(race_arr, list) and (player_cid or player_card):
            for rr_entry in race_arr:
                if _chara_matches(rr_entry, player_cid, player_card):
                    player_race_result = rr_entry
                    break

        # Fall back to race_result_info (single dict)
        if player_race_result is None:
            rri = data.get("race_result_info")
            if isinstance(rri, list):
                # Sometimes it's a list — find our horse
                for rr_entry in rri:
                    if isinstance(rr_entry, dict) and (
                        (not player_cid and not player_card)
                        or _chara_matches(rr_entry, player_cid, player_card)
                    ):
                        player_race_result = rr_entry
                        break
            elif isinstance(rri, dict) and rri.get("result_order") is not None:
                player_race_result = rri

        if player_race_result and player_race_result.get("result_order") is not None:
            turn = 0
            if isinstance(chara, dict):
                turn = chara.get("turn", 0)
            raw_order = player_race_result["result_order"]
            summary["race_results"].append(
                {
                    "turn": turn,
                    "race_instance_id": player_race_result.get("race_instance_id"),
                    "program_id": player_race_result.get("program_id"),
                    "result_order": raw_order + 1,  # game is 0-based; convert to 1-based
                    "entry_count": player_race_result.get("entry_count")
                    or player_race_result.get("num"),
                    "api": api,
                    "_ts": ts,
                }
            )

        # Also check race_start_info / race_horse_data for race entries
        race_start = data.get("race_start_info", {})
        if (
            isinstance(race_start, dict)
            and race_start.get("race_instance_id")
            and not any(
                r.get("race_instance_id") == race_start.get("race_instance_id")
                for r in summary["race_results"]
            )
        ):
            summary["race_results"].append(
                {
                    "turn": chara.get("turn", 0) if isinstance(chara, dict) else 0,
                    "race_instance_id": race_start.get("race_instance_id"),
                    "program_id": race_start.get("program_id"),
                    "result_order": None,  # not finished yet
                    "api": api,
                    "_ts": ts,
                }
            )

        # ── Training actions ────────────────────────────────────
        if "ExecCommand" in api or "training" in api.lower():
            command = data.get("command_info", {})
            if isinstance(command, dict) and command.get("command_id"):
                turn = 0
                if isinstance(chara, dict):
                    turn = chara.get("turn", 0)
                summary["training_actions"].append(
                    {
                        "turn": turn,
                        "command_id": command["command_id"],
                        "api": api,
                        "_ts": ts,
                    }
                )

        # ── Story events ────────────────────────────────────────
        unchecked = data.get("unchecked_event_array", [])
        if isinstance(unchecked, list):
            for ev in unchecked:
                if isinstance(ev, dict) and ev.get("story_id"):
                    turn = 0
                    if isinstance(chara, dict):
                        turn = chara.get("turn", 0)
                    summary["events_seen"].append(
                        {
                            "story_id": ev["story_id"],
                            "turn": turn,
                            "event_id": ev.get("event_id"),
                        }
                    )

        # ── Event choice tracking ──────────────────────────────
        # When the player picks a choice, the game sends a
        # *CheckEvent, *ChoiceReward, or *GetChoiceReward API.
        # The REQUEST payload contains choice_number (1-based)
        # and event_id.  The RESPONSE comes back with updated
        # chara_info — we compute stat deltas vs the previous snapshot.
        _CHOICE_API_PATTERNS = (
            "CheckEvent",  # SingleModeFreeCheckEvent, SingleModeCheckEvent, SingleModeTeamCheckEvent
            "ChoiceReward",  # SingleModeFreeChoiceReward
            "GetChoiceReward",  # SingleModeGetChoiceReward, SingleModeTeamGetChoiceReward
        )
        is_choice_api = any(p in api for p in _CHOICE_API_PATTERNS)
        if is_choice_api:
            event_type = rec.get("event", "")
            is_request = event_type in ("api_send", "msgpack_serialize")
            is_response = event_type in ("api_response", "msgpack_deserialize")

            if is_request:
                # Request side — extract choice_number from decoded MsgPack.
                # Request payloads have fields at top-level (no "data" wrapper).
                choice_num = _extract_int(decoded, data, rec, "choice_number")

                # choice_number is 1-based; 0 means "no choice" (single-option event)
                if choice_num is not None and choice_num > 0:
                    # Use event_id from the request to match the correct story_id
                    event_id = _extract_int(decoded, data, rec, "event_id")
                    recent_story_id = None
                    if event_id and summary["events_seen"]:
                        for ev in reversed(summary["events_seen"]):
                            if ev.get("event_id") == event_id:
                                recent_story_id = ev.get("story_id")
                                break
                    # Fallback: most recent event
                    if recent_story_id is None and summary["events_seen"]:
                        recent_story_id = summary["events_seen"][-1].get("story_id")

                    _pending_choice = {
                        "story_id": recent_story_id,
                        "choice_number": int(choice_num),
                        "event_id": event_id,
                        "api": api,
                        "_ts": ts,
                        "turn": 0,
                        "stat_deltas": {},
                    }

            elif is_response and _pending_choice is not None:
                # Response side — if we have chara_info, deltas will be
                # computed in the chara_info block above on the next
                # iteration.  But if decoded has choice_number we missed
                # from the send, grab it now.
                if _pending_choice.get("choice_number") is None:
                    choice_num = _extract_int(decoded, data, rec, "choice_number")
                    if choice_num is not None and choice_num > 0:
                        _pending_choice["choice_number"] = int(choice_num)

    # Flush any pending choice that never got a stat delta (end of session)
    if _pending_choice is not None:
        summary["event_choices"].append(_pending_choice)

    return summary


# ── Multi-career detection ─────────────────────────────────────────────

# APIs that signal the start of a brand-new career run
_CAREER_START_API_KEYWORDS = (
    "SingleModeStart",
    "SingleModeFreeStart",
    "SingleModeTeamStart",
    "single_mode/start",
    "single_mode_free/start",
    "single_mode_team/start",
)


def _is_career_start_api(api: str) -> bool:
    """Check whether an API name signals the start of a new career run."""
    if not api:
        return False
    return any(keyword in api for keyword in _CAREER_START_API_KEYWORDS)


def _detect_career_boundaries(records: list[dict]) -> list[int]:
    """
    Scan network records and return indices where new career runs begin.

    Detection heuristics (in priority order):
      1. Explicit career-start API (SingleModeStart, etc.)
      2. (chara_id, card_id) pair changes to a different combo
      3. Turn counter resets to ≤1 after reaching >5  (same character replayed)
    """
    if not records:
        return []

    boundaries: list[int] = [0]
    prev_chara_card: tuple[int, int] | None = None
    prev_max_turn = 0

    for i, rec in enumerate(records):
        raw_api = rec.get("api", "")

        # Heuristic 1: explicit start API
        if _is_career_start_api(raw_api):
            if i > 0 and (not boundaries or boundaries[-1] != i):
                boundaries.append(i)
                prev_max_turn = 0
                prev_chara_card = None
            continue

        # Look for chara_info to detect character / turn changes
        decoded = rec.get("msgpack_decoded", {})
        if not isinstance(decoded, dict):
            continue
        data = decoded.get("data", {})
        if not isinstance(data, dict):
            continue

        chara = data.get("chara_info", {})
        if not isinstance(chara, dict) or not chara.get("speed"):
            continue

        cid = chara.get("chara_id")
        card = chara.get("card_id")
        turn = chara.get("turn", 0)

        cc = (cid, card) if cid and card else None

        # Heuristic 2: different character + card combo or turn reset
        if (
            (cc and prev_chara_card and cc != prev_chara_card) or (prev_max_turn > 5 and turn <= 1)
        ) and (not boundaries or boundaries[-1] != i):
            boundaries.append(i)
            prev_max_turn = 0

        if cc:
            prev_chara_card = cc
        prev_max_turn = max(prev_max_turn, turn)

    return sorted(set(boundaries))


def build_session_summaries(session_name: str) -> tuple[list[dict], list[dict]]:
    """
    Build one summary per career run detected in a session.

    Returns ``(careers, other_races)`` where *careers* is one summary dict
    per career run and *other_races* is a flat list of race-result dicts
    from non-career contexts (Champions Meeting, Room Match, etc.).

    Single-career sessions return a list with one element.
    """
    records = read_domain(session_name, "network")
    if not records:
        return [_build_summary_from_records([])], []

    boundaries = _detect_career_boundaries(records)

    summaries: list[dict] = []
    other_races: list[dict] = []
    for idx, start in enumerate(boundaries):
        end = boundaries[idx + 1] if idx + 1 < len(boundaries) else len(records)
        s = _build_summary_from_records(records[start:end])
        s["_career_index"] = idx
        # Pull non-career races out of the career dict → session level
        other_races.extend(s.pop("_non_career_races", []))
        summaries.append(s)

    if not summaries:
        return [_build_summary_from_records([])], other_races
    return summaries, other_races


def build_session_summary(session_name: str) -> dict:
    """
    Build a single flat summary for a session (backward-compatible API).

    When multiple careers are detected, returns the **last** one (most recent).
    Prefer :func:`build_session_summaries` for full multi-career support.
    """
    summaries, _other = build_session_summaries(session_name)
    return summaries[-1] if summaries else _build_summary_from_records([])
