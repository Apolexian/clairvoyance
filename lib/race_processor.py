"""
Race Data Processor
───────────────────
Takes decoded MsgPack API responses, detects race endpoints,
extracts and parses the race_simulate_data binary blob, and
produces structured race records.

Also processes dump-hook frame records from
RaceSimulateHorseFrameData.Deserialize into structured race analyses.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from .race_sim_parser import (
    RaceSimulateData,
    SimulateEventType,
    deserialize_from_base64,
    deserialize_from_bytes,
    event_type_name,
    race_data_to_dict,
    running_style_name,
    temptation_mode_name,
)

log = logging.getLogger("clairvoyance")


# ── API endpoint patterns that contain race data ───────────────────────

RACE_API_PATTERNS = [
    "SingleModeFreeRaceStart",
    "SingleModeRaceStart",
    "TeamRaceStart",
    "ChampionsRaceStart",
    "PracticeRaceStart",
    "RoomRaceStart",
    "LegendRaceStart",
    "TeamStadiumRaceStart",
    "RaceStart",  # catch-all
]

RACE_RESULT_PATTERNS = [
    "SingleModeFreeRaceResult",
    "SingleModeRaceResult",
    "TeamRaceResult",
    "ChampionsRaceResult",
    "PracticeRaceResult",
    "RoomRaceResult",
    "LegendRaceResult",
    "TeamStadiumRaceResult",
    "RaceResult",  # catch-all
]


def is_race_api(api_name: str) -> bool:
    """Check if an API name relates to a race start."""
    return any(p in api_name for p in RACE_API_PATTERNS)


def is_race_result_api(api_name: str) -> bool:
    """Check if an API name relates to race results."""
    return any(p in api_name for p in RACE_RESULT_PATTERNS)


# ── Recursive key finder ──────────────────────────────────────────────


def _find_key_recursive(obj: Any, key: str, max_depth: int = 10) -> Any:
    """Recursively search a nested dict/list structure for a key."""
    if max_depth <= 0:
        return None
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            result = _find_key_recursive(v, key, max_depth - 1)
            if result is not None:
                return result
    elif isinstance(obj, list):
        for item in obj:
            result = _find_key_recursive(item, key, max_depth - 1)
            if result is not None:
                return result
    return None


# ── Extract race horse info ────────────────────────────────────────────


def _extract_horse_info(decoded: dict) -> list[dict] | None:
    """Extract the race_horse_data_array from the decoded MsgPack response."""
    for key in ("race_horse_data_array", "race_horse_data"):
        result = _find_key_recursive(decoded, key)
        if result and isinstance(result, list):
            return result
    return None


def _extract_race_simulate_data(decoded: dict) -> str | None:
    """Extract the base64-encoded race_simulate_data field."""
    for key in ("race_simulate_data", "simulate_data", "race_result_info"):
        result = _find_key_recursive(decoded, key)
        if result is not None:
            if isinstance(result, str):
                return result
            # It might be nested inside another dict
            if isinstance(result, dict):
                for sub_key in ("race_simulate_data", "simulate_data"):
                    if sub_key in result and isinstance(result[sub_key], str):
                        return result[sub_key]
    return None


# ── Build structured race record ──────────────────────────────────────


def _extract_skill_activations(rd: RaceSimulateData) -> list[dict]:
    """Extract all skill activation events from race simulation data."""
    activations = []
    for event in rd.events:
        if event.type == SimulateEventType.SKILL and len(event.params) >= 2:
            act: dict = {
                "frame_time": round(event.frame_time, 4),
                "horse_index": event.params[0],
                "skill_id": event.params[1],
            }
            if len(event.params) >= 3:
                act["duration_raw"] = event.params[2]
            if len(event.params) >= 4:
                act["cooldown_raw"] = event.params[3]
            if len(event.params) >= 5:
                act["target_mask"] = event.params[4]
            activations.append(act)
    return activations


def _extract_compete_events(rd: RaceSimulateData) -> list[dict]:
    """Extract compete/dueling events."""
    competes = []
    for event in rd.events:
        if event.type in (
            SimulateEventType.COMPETE_TOP,
            SimulateEventType.COMPETE_FIGHT,
            SimulateEventType.COMPETE_BEFORE_SPURT,
        ):
            competes.append(
                {
                    "frame_time": round(event.frame_time, 4),
                    "type": event_type_name(event.type),
                    "horse_index": event.params[0] if event.params else -1,
                    "params": event.params,
                }
            )
    return competes


def _detect_pace_down_segments(rd: RaceSimulateData) -> dict[int, list[dict]]:
    """
    Detect pace-down (temptation) segments for each horse from frame data.

    temptation_mode != 0 means the horse is in some kind of temptation/rush mode.
    This is the key indicator for "pace down" behavior.
    """
    segments: dict[int, list[dict]] = {}
    if not rd.frames:
        return segments

    for horse_idx in range(rd.horse_num):
        horse_segments: list[dict] = []
        current_segment: dict | None = None

        for frame in rd.frames:
            if horse_idx >= len(frame.horse_frames):
                continue
            hf = frame.horse_frames[horse_idx]
            mode = hf.temptation_mode

            if mode != 0:
                if current_segment is None:
                    current_segment = {
                        "start_time": round(frame.time, 4),
                        "start_distance": round(hf.distance, 2),
                        "mode": temptation_mode_name(mode),
                        "mode_id": mode,
                    }
                # Update end point
                current_segment["end_time"] = round(frame.time, 4)
                current_segment["end_distance"] = round(hf.distance, 2)
            else:
                if current_segment is not None:
                    current_segment["duration"] = round(
                        current_segment["end_time"] - current_segment["start_time"], 4
                    )
                    horse_segments.append(current_segment)
                    current_segment = None

        # Close any open segment
        if current_segment is not None:
            current_segment["duration"] = round(
                current_segment["end_time"] - current_segment["start_time"], 4
            )
            horse_segments.append(current_segment)

        if horse_segments:
            segments[horse_idx] = horse_segments

    return segments


def _detect_phases(rd: RaceSimulateData) -> dict:
    """
    Calculate race phase boundaries.
    Phase 1 (Opening): 0 to distance/6
    Phase 2 (Mid):     distance/6 to distance*2/3
    Phase 3 (Final):   distance*2/3 to distance*5/6
    Phase 4 (Spurt):   distance*5/6 to distance
    """
    # Determine total race distance from the max distance in results/frames
    total_distance = rd.distance_diff_max
    if rd.frames:
        for frame in rd.frames:
            for hf in frame.horse_frames:
                if hf.distance > total_distance:
                    total_distance = hf.distance

    # Fallback: use last spurt distances
    for hr in rd.horse_results:
        if hr.last_spurt_start_distance > 0:
            # Race distance must be at least this + some spurt
            est = hr.last_spurt_start_distance * 1.5
            if est > total_distance:
                total_distance = est

    if total_distance <= 0:
        return {"total_distance": 0}

    return {
        "total_distance": round(total_distance, 2),
        "phase_1_end": round(total_distance / 6, 2),
        "phase_2_end": round(total_distance * 2 / 3, 2),
        "phase_3_end": round(total_distance * 5 / 6, 2),
    }


def _summarize_horse(rd: RaceSimulateData, idx: int) -> dict | None:
    """Build a per-horse summary from simulation data."""
    if idx >= len(rd.horse_results):
        return None

    hr = rd.horse_results[idx]
    summary: dict = {
        "horse_index": idx,
        "finish_order": hr.finish_order,
        "finish_time": round(hr.finish_time, 4),
        "finish_time_raw": round(hr.finish_time_raw, 4),
        "finish_diff_time": round(hr.finish_diff_time, 4),
        "start_delay_time": round(hr.start_delay_time, 4),
        "is_late_start": hr.start_delay_time >= 0.08,
        "running_style": running_style_name(hr.running_style),
        "last_spurt_start_distance": round(hr.last_spurt_start_distance, 2),
        "guts_order": hr.guts_order,
        "wiz_order": hr.wiz_order,
        "defeat": hr.defeat,
    }

    # Count skill activations for this horse
    skills = [
        e
        for e in rd.events
        if e.type == SimulateEventType.SKILL and len(e.params) >= 2 and e.params[0] == idx
    ]
    summary["skill_activation_count"] = len(skills)
    summary["skill_ids_activated"] = list(set(e.params[1] for e in skills))

    # HP at start and end
    if rd.frames:
        first_frame = rd.frames[0]
        last_frame = rd.frames[-1]
        if idx < len(first_frame.horse_frames):
            summary["hp_start"] = first_frame.horse_frames[idx].hp
        if idx < len(last_frame.horse_frames):
            summary["hp_end"] = last_frame.horse_frames[idx].hp

    return summary


# ── Main API ───────────────────────────────────────────────────────────


def try_process_race(record: dict, include_frames: str = "sampled") -> dict | None:
    """
    Attempt to extract and process race simulation data from a network record.

    Args:
        record: A network event record dict (must have "msgpack_decoded" or
                similar decoded data).
        include_frames: "all", "sampled", or "none" for frame data verbosity.

    Returns:
        A structured race data dict, or None if no race data found.
    """
    api_name = record.get("api", "")
    decoded = record.get("msgpack_decoded")

    if not decoded or not isinstance(decoded, dict):
        return None

    # Check if this is a race-related API
    if not (is_race_api(api_name) or is_race_result_api(api_name)):
        # Also check if decoded data contains race simulation data
        sim_data = _extract_race_simulate_data(decoded)
        if sim_data is None:
            return None
    else:
        sim_data = _extract_race_simulate_data(decoded)

    race_record: dict = {
        "event": "race_simulation",
        "api": api_name,
    }

    # Extract horse info
    horse_info = _extract_horse_info(decoded)
    if horse_info:
        race_record["horse_count"] = len(horse_info)
        race_record["horses"] = [
            {
                "frame_order": h.get("frame_order", i + 1),
                "chara_id": h.get("chara_id"),
                "card_id": h.get("card_id"),
                "speed": h.get("speed"),
                "stamina": h.get("stamina"),
                "power": h.get("pow") or h.get("power"),
                "guts": h.get("guts"),
                "wiz": h.get("wiz"),
                "running_style": h.get("running_style"),
                "motivation": h.get("motivation"),
                "popularity": h.get("popularity"),
                "skill_count": len(h.get("skill_array", [])),
                "proper_ground_turf": h.get("proper_ground_turf"),
                "proper_ground_dirt": h.get("proper_ground_dirt"),
                "proper_running_style_nige": h.get("proper_running_style_nige"),
                "proper_running_style_senko": h.get("proper_running_style_senko"),
                "proper_running_style_sashi": h.get("proper_running_style_sashi"),
                "proper_running_style_oikomi": h.get("proper_running_style_oikomi"),
                "proper_distance_short": h.get("proper_distance_short"),
                "proper_distance_mile": h.get("proper_distance_mile"),
                "proper_distance_middle": h.get("proper_distance_middle"),
                "proper_distance_long": h.get("proper_distance_long"),
            }
            for i, h in enumerate(horse_info)
        ]

    # Parse simulation binary
    if sim_data:
        try:
            rd = deserialize_from_base64(sim_data)
            race_record["simulation"] = race_data_to_dict(rd, include_frames)

            # Higher-level analysis
            race_record["skill_activations"] = _extract_skill_activations(rd)
            race_record["compete_events"] = _extract_compete_events(rd)
            race_record["pace_down_segments"] = {
                str(k): v for k, v in _detect_pace_down_segments(rd).items()
            }
            race_record["phases"] = _detect_phases(rd)

            # Per-horse summaries
            summaries = []
            for i in range(rd.horse_num):
                s = _summarize_horse(rd, i)
                if s:
                    summaries.append(s)
            race_record["horse_summaries"] = summaries

            log.info(
                "  [race] Parsed race: %d horses, %d frames, %d events, %d skill activations",
                rd.horse_num,
                rd.frame_count,
                rd.event_count,
                len(race_record["skill_activations"]),
            )
        except Exception as e:
            race_record["simulation_parse_error"] = str(e)
            log.warning("  [race] Failed to parse race simulation data: %s", e)
    else:
        # No simulation binary but we have horse info — still useful
        if horse_info:
            log.info("  [race] Race API detected but no simulation binary (horse info only)")
        else:
            return None

    return race_record


def try_process_race_from_raw(raw_bytes: bytes, api_name: str = "") -> dict | None:
    """
    Attempt to parse race simulation data directly from raw bytes
    (e.g. if we have the binary blob itself, not base64).
    """
    try:
        rd = deserialize_from_bytes(raw_bytes)
    except Exception as e:
        log.debug("  [race] Raw bytes not race simulation data: %s", e)
        return None

    race_record: dict = {
        "event": "race_simulation",
        "api": api_name,
        "simulation": race_data_to_dict(rd, "sampled"),
        "skill_activations": _extract_skill_activations(rd),
        "compete_events": _extract_compete_events(rd),
        "pace_down_segments": {str(k): v for k, v in _detect_pace_down_segments(rd).items()},
        "phases": _detect_phases(rd),
        "horse_summaries": [
            s for i in range(rd.horse_num) if (s := _summarize_horse(rd, i)) is not None
        ],
    }

    log.info(
        "  [race] Parsed raw race: %d horses, %d frames, %d events",
        rd.horse_num,
        rd.frame_count,
        rd.event_count,
    )
    return race_record


# ── Dump-frame race processor ──────────────────────────────────────────


def process_dump_race_frames(
    records: list[dict],
    lifecycle_records: list[dict] | None = None,
    skill_records: list[dict] | None = None,
) -> dict | None:
    """
    Assemble individual dump frame records from RaceSimulateHorseFrameData.Deserialize
    into a structured race analysis.

    The dump hooks capture each horse's frame data as the game deserialises
    the race simulation binary.  Records arrive in sequence: all horses for
    frame 0, then all horses for frame 1, etc.  Horses are identified by
    their consistent LanePosition value across frames.

    Args:
        records: List of dump event dicts with fields:
                 {Distance, LanePosition, Speed, Hp, TemptationMode, BlockFrontHorseIndex}
        lifecycle_records: Optional race_lifecycle events (OnFinish, etc.)
        skill_records: Optional race_skill_activate events

    Returns:
        A structured race analysis dict, or None if insufficient data.
    """
    if not records or len(records) < 2:
        return None

    # ── Step 1: Identify horses by unique LanePosition ─────────────────
    # Collect all unique lane positions in order of first appearance
    lane_order: list[float] = []
    lane_set: set[float] = set()
    for rec in records:
        fields = rec.get("fields", rec)
        lane = fields.get("LanePosition")
        if lane is not None and lane not in lane_set:
            lane_order.append(lane)
            lane_set.add(lane)

    num_horses = len(lane_order)
    if num_horses == 0:
        return None

    # Map lane position → horse index
    lane_to_idx = {lane: idx for idx, lane in enumerate(lane_order)}

    # ── Step 2: Group records into frames ───────────────────────────────
    # Records arrive sequentially: horses 0..N-1 for frame 0, then frame 1, etc.
    # We group by cycling through all horses.
    frames: list[dict[int, dict]] = []
    current_frame: dict[int, dict] = {}
    seen_in_frame: set[int] = set()

    for rec in records:
        fields = rec.get("fields", rec)
        lane = fields.get("LanePosition")
        if lane is None or lane not in lane_to_idx:
            continue
        idx = lane_to_idx[lane]

        # If we've already seen this horse in the current frame, start a new frame
        if idx in seen_in_frame:
            if current_frame:
                frames.append(current_frame)
            current_frame = {}
            seen_in_frame = set()

        current_frame[idx] = {
            "distance": fields.get("Distance", 0),
            "lane_position": lane,
            "speed": fields.get("Speed", 0),
            "hp": fields.get("Hp", 0),
            "temptation_mode": fields.get("TemptationMode", 0),
            "block_front": fields.get("BlockFrontHorseIndex", -1),
        }
        seen_in_frame.add(idx)

    # Don't forget the last frame
    if current_frame:
        frames.append(current_frame)

    if not frames:
        return None

    log.info(
        "  [race-dump] Assembled %d frames x %d horses from %d dump records",
        len(frames),
        num_horses,
        len(records),
    )

    # ── Step 3: Build per-horse time series ────────────────────────────
    horse_series: dict[int, list[dict]] = defaultdict(list)
    for frame_idx, frame in enumerate(frames):
        for horse_idx, data in frame.items():
            horse_series[horse_idx].append(
                {
                    "frame": frame_idx,
                    **data,
                }
            )

    # ── Step 4: Compute per-horse summaries ────────────────────────────
    horse_summaries = []
    for horse_idx in range(num_horses):
        series = horse_series.get(horse_idx, [])
        if not series:
            continue

        first = series[0]
        last = series[-1]

        # Max distance reached
        max_dist = max(s["distance"] for s in series)

        # HP consumed
        hp_start = first["hp"]
        hp_end = last["hp"]
        hp_consumed = hp_start - hp_end

        # Speed statistics
        speeds = [s["speed"] for s in series if s["speed"] > 0]
        avg_speed = sum(speeds) / len(speeds) if speeds else 0
        max_speed = max(speeds) if speeds else 0
        min_speed = min(speeds) if speeds else 0

        # Detect pace-down segments (TemptationMode != 0)
        pace_down_segments = []
        current_pd = None
        for s in series:
            if s["temptation_mode"] != 0:
                if current_pd is None:
                    current_pd = {
                        "start_frame": s["frame"],
                        "start_distance": round(s["distance"], 2),
                        "mode": s["temptation_mode"],
                    }
                current_pd["end_frame"] = s["frame"]
                current_pd["end_distance"] = round(s["distance"], 2)
            else:
                if current_pd is not None:
                    current_pd["duration_frames"] = (
                        current_pd["end_frame"] - current_pd["start_frame"] + 1
                    )
                    pace_down_segments.append(current_pd)
                    current_pd = None
        if current_pd is not None:
            current_pd["duration_frames"] = current_pd["end_frame"] - current_pd["start_frame"] + 1
            pace_down_segments.append(current_pd)

        # Blocking events (frames where BlockFrontHorseIndex != -1)
        blocked_frames = sum(1 for s in series if s["block_front"] != -1)

        summary = {
            "horse_index": horse_idx,
            "lane_position": round(first["lane_position"], 4),
            "max_distance": round(max_dist, 2),
            "hp_start": hp_start,
            "hp_end": hp_end,
            "hp_consumed": hp_consumed,
            "avg_speed": round(avg_speed, 4),
            "max_speed": round(max_speed, 4),
            "min_speed": round(min_speed, 4),
            "total_frames": len(series),
            "pace_down_segments": pace_down_segments,
            "total_pace_down_frames": sum(seg["duration_frames"] for seg in pace_down_segments),
            "blocked_frames": blocked_frames,
        }
        horse_summaries.append(summary)

    # ── Step 5: Race-level analysis ────────────────────────────────────

    # Estimate total race distance from max distance across all horses
    total_distance = max((s["max_distance"] for s in horse_summaries), default=0)

    # Phase boundaries
    phases = {}
    if total_distance > 0:
        phases = {
            "total_distance": round(total_distance, 2),
            "phase_1_end": round(total_distance / 6, 2),
            "phase_2_end": round(total_distance * 2 / 3, 2),
            "phase_3_end": round(total_distance * 5 / 6, 2),
        }

    # Finish order: sort horses by max distance (desc) — in a complete race
    # all horses finish, but if interrupted we rank by progress
    finish_order = sorted(
        horse_summaries,
        key=lambda h: -h["max_distance"],
    )
    for rank, h in enumerate(finish_order, 1):
        h["estimated_rank"] = rank

    # ── Step 6: Sampled frame data for output ──────────────────────────
    # Output a subset of frames (every Nth) to keep the record manageable
    total_frames = len(frames)
    sample_interval = max(1, total_frames // 30)  # ~30 samples
    sampled_frames = []
    for fi in range(0, total_frames, sample_interval):
        frame = frames[fi]
        sampled = {"frame_index": fi}
        for horse_idx, data in sorted(frame.items()):
            sampled[f"horse_{horse_idx}"] = {
                "distance": round(data["distance"], 2),
                "speed": round(data["speed"], 4),
                "hp": data["hp"],
                "temptation": data["temptation_mode"],
            }
        sampled_frames.append(sampled)

    # ── Step 7: Include lifecycle and skill data ───────────────────────
    lifecycle_info = []
    if lifecycle_records:
        for rec in lifecycle_records:
            info = {
                "event": rec.get("event"),
                "class": rec.get("class"),
                "_ts": rec.get("_ts"),
            }
            # Include any field_ prefixed keys
            for k, v in rec.items():
                if k.startswith("field_"):
                    info[k] = v
            lifecycle_info.append(info)

    skill_info = []
    if skill_records:
        for rec in skill_records:
            info = {
                "event": rec.get("event"),
                "class": rec.get("class"),
                "_ts": rec.get("_ts"),
            }
            for k, v in rec.items():
                if k.startswith("field_"):
                    info[k] = v
            skill_info.append(info)

    # Last spurt distances from lifecycle OnFinish events
    last_spurt_distances = []
    if lifecycle_records:
        for rec in lifecycle_records:
            cls = rec.get("class", "")
            if "OnFinish" in cls:
                lsd = rec.get("field__lastSpurtStartDistance")
                if lsd is not None:
                    last_spurt_distances.append(round(lsd, 2))

    # ── Assemble the result ────────────────────────────────────────────
    result: dict = {
        "event": "race_analysis_from_dump",
        "source": "RaceSimulateHorseFrameData.Deserialize",
        "num_horses": num_horses,
        "total_frames": total_frames,
        "total_dump_records": len(records),
        "estimated_total_distance": round(total_distance, 2),
        "phases": phases,
        "horse_summaries": horse_summaries,
        "sampled_frames": sampled_frames,
    }

    if last_spurt_distances:
        result["last_spurt_distances"] = last_spurt_distances
    if lifecycle_info:
        result["lifecycle_events"] = lifecycle_info
    if skill_info:
        result["skill_activations"] = skill_info

    log.info(
        "  [race-dump] Analysis: %d horses, %d frames, distance=%.0f, %d skills, %d lifecycle",
        num_horses,
        total_frames,
        total_distance,
        len(skill_info),
        len(lifecycle_info),
    )

    return result
