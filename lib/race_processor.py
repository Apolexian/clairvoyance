"""
Race Data Processor
───────────────────
Takes decoded MsgPack API responses, detects race endpoints,
extracts and parses the race_simulate_data binary blob, and
produces structured race records.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

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


def _extract_horse_info(decoded: dict) -> Optional[list[dict]]:
    """Extract the race_horse_data_array from the decoded MsgPack response."""
    for key in ("race_horse_data_array", "race_horse_data"):
        result = _find_key_recursive(decoded, key)
        if result and isinstance(result, list):
            return result
    return None


def _extract_race_simulate_data(decoded: dict) -> Optional[str]:
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
            competes.append({
                "frame_time": round(event.frame_time, 4),
                "type": event_type_name(event.type),
                "horse_index": event.params[0] if event.params else -1,
                "params": event.params,
            })
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
        current_segment: Optional[dict] = None

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


def _summarize_horse(rd: RaceSimulateData, idx: int) -> Optional[dict]:
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
        e for e in rd.events
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


def try_process_race(record: dict, include_frames: str = "sampled") -> Optional[dict]:
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


def try_process_race_from_raw(raw_bytes: bytes, api_name: str = "") -> Optional[dict]:
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
        "pace_down_segments": {
            str(k): v for k, v in _detect_pace_down_segments(rd).items()
        },
        "phases": _detect_phases(rd),
        "horse_summaries": [
            s for i in range(rd.horse_num)
            if (s := _summarize_horse(rd, i)) is not None
        ],
    }

    log.info(
        "  [race] Parsed raw race: %d horses, %d frames, %d events",
        rd.horse_num, rd.frame_count, rd.event_count,
    )
    return race_record

