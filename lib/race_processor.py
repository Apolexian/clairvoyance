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

from . import course_data as cd
from .race_sim_parser import (
    RaceSimulateData,
    RunningStyle,
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
    """Extract the base64-encoded race simulation data field.

    The game has used different names across versions:
    - race_scenario (current, confirmed by CarrotJuicer)
    - race_simulate_data (older)
    - simulate_data (alternative)
    """
    for key in ("race_scenario", "race_simulate_data", "simulate_data", "race_result_info"):
        result = _find_key_recursive(decoded, key)
        if result is not None:
            if isinstance(result, str):
                return result
            # It might be nested inside another dict
            if isinstance(result, dict):
                for sub_key in ("race_scenario", "race_simulate_data", "simulate_data"):
                    if sub_key in result and isinstance(result[sub_key], str):
                        return result[sub_key]
    return None


# ── Build structured race record ──────────────────────────────────────


def _interpolate_distance(rd: RaceSimulateData, horse_idx: int, time: float) -> float:
    """Interpolate a horse's distance at a given time from frame data."""
    if not rd.frames:
        return 0.0
    if time <= rd.frames[0].time:
        hf = rd.frames[0].horse_frames
        return hf[horse_idx].distance if horse_idx < len(hf) else 0.0
    if time >= rd.frames[-1].time:
        hf = rd.frames[-1].horse_frames
        return hf[horse_idx].distance if horse_idx < len(hf) else 0.0
    # Binary search
    lo, hi = 0, len(rd.frames) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if rd.frames[mid].time <= time:
            lo = mid
        else:
            hi = mid - 1
    f1, f2 = rd.frames[lo], rd.frames[min(lo + 1, len(rd.frames) - 1)]
    dt = f2.time - f1.time
    if dt <= 0 or horse_idx >= len(f1.horse_frames) or horse_idx >= len(f2.horse_frames):
        return f1.horse_frames[horse_idx].distance if horse_idx < len(f1.horse_frames) else 0.0
    ratio = (time - f1.time) / dt
    d1 = f1.horse_frames[horse_idx].distance
    d2 = f2.horse_frames[horse_idx].distance
    return d1 + (d2 - d1) * ratio


def _compute_skill_duration(
    event_frame_time: float, params: list[int], race_distance: float
) -> float:
    """
    Compute skill duration in seconds.

    For non-zero frame_time, prefer the server-reported duration in param[2].
    Fallback to 2.0s (matching Hakuraku's getSkillDurationSecs).
    """
    if len(params) < 3:
        return 2.0
    duration_raw = params[2]
    if abs(event_frame_time) > 1e-9:
        # Server-reported duration
        if duration_raw > 0:
            return duration_raw / 10000.0
        return 2.0
    # frame_time == 0: baseTime-based formula would need skill DB; use 2.0 fallback
    if duration_raw > 0:
        return (duration_raw / 10000.0) * (race_distance / 1000.0)
    return 2.0


def _extract_skill_activations(rd: RaceSimulateData, race_distance: float = 0) -> list[dict]:
    """Extract all skill activation events with computed durations and distance ranges."""
    activations = []
    for event in rd.events:
        if event.type == SimulateEventType.SKILL and len(event.params) >= 2:
            horse_idx = event.params[0]
            duration_secs = _compute_skill_duration(event.frame_time, event.params, race_distance)
            act: dict = {
                "frame_time": round(event.frame_time, 4),
                "horse_index": horse_idx,
                "skill_id": event.params[1],
                "duration_secs": round(duration_secs, 2),
                "start_distance": round(_interpolate_distance(rd, horse_idx, event.frame_time), 2),
                "end_distance": round(
                    _interpolate_distance(rd, horse_idx, event.frame_time + duration_secs), 2
                ),
            }
            if len(event.params) >= 3:
                act["duration_raw"] = event.params[2]
            if len(event.params) >= 4:
                act["cooldown_raw"] = event.params[3]
            if len(event.params) >= 5:
                act["target_mask"] = event.params[4]
            activations.append(act)
    return activations


# ── Compete event constants (from Hakuraku analysisUtils.ts) ───────────
_DUELING_HP_THRESHOLD_RATIO = 0.05
_SPOT_STRUGGLE_DIST_RATIO = 9 / 24
_SPOT_STRUGGLE_GUTS_DUR_BASE = 700
_SPOT_STRUGGLE_GUTS_DUR_EXPONENT = 0.5
_SPOT_STRUGGLE_GUTS_DUR_SCALE = 0.012


def _extract_compete_events(
    rd: RaceSimulateData,
    horse_guts: dict[int, int] | None = None,
    race_distance: float = 0,
) -> list[dict]:
    """
    Extract compete/dueling events with computed durations.

    - COMPETE_FIGHT (Dueling): ends when horse HP drops below 5% of start HP.
    - COMPETE_TOP (Spot Struggle): duration from guts formula, capped at 9/24 distance.
    - COMPETE_BEFORE_SPURT: labeled event.
    """
    competes = []
    start_hp: dict[int, int] = {}
    if rd.frames:
        for hi in range(rd.horse_num):
            if hi < len(rd.frames[0].horse_frames):
                start_hp[hi] = rd.frames[0].horse_frames[hi].hp

    for event in rd.events:
        if event.type not in (
            SimulateEventType.COMPETE_TOP,
            SimulateEventType.COMPETE_FIGHT,
            SimulateEventType.COMPETE_BEFORE_SPURT,
        ):
            continue
        horse_idx = event.params[0] if event.params else -1
        entry: dict = {
            "frame_time": round(event.frame_time, 4),
            "type": event_type_name(event.type),
            "type_id": event.type,
            "horse_index": horse_idx,
            "params": event.params,
        }

        if event.type == SimulateEventType.COMPETE_FIGHT and horse_idx >= 0:
            # Dueling: walk frames until HP < 5% of start
            hp_threshold = start_hp.get(horse_idx, 0) * _DUELING_HP_THRESHOLD_RATIO
            end_time = rd.frames[-1].time if rd.frames else event.frame_time
            for frame in rd.frames:
                if frame.time < event.frame_time:
                    continue
                if (
                    horse_idx < len(frame.horse_frames)
                    and frame.horse_frames[horse_idx].hp < hp_threshold
                ):
                    end_time = frame.time
                    break
            duration = round(end_time - event.frame_time, 4)
            entry["duration"] = duration
            entry["label"] = "Dueling"
            entry["start_distance"] = round(
                _interpolate_distance(rd, horse_idx, event.frame_time), 2
            )
            entry["end_distance"] = round(
                _interpolate_distance(rd, horse_idx, event.frame_time + duration), 2
            )

        elif event.type == SimulateEventType.COMPETE_TOP and horse_idx >= 0:
            # Spot Struggle (Lead Competition / CompeteTop):
            # Speed bonus: (500 * guts)^0.6 * 0.0001 m/s
            # Duration:    (700 * guts)^0.5 * 0.012 s
            # Ends at 9th section (9/24 of race distance) regardless
            # HP consumption: FR 1.4x, FR+Rushed 3.6x, Oonige 3.5x, Oonige+Rushed 7.7x
            guts = (horse_guts or {}).get(horse_idx, 0)
            if guts > 0:
                guts_duration = (
                    _SPOT_STRUGGLE_GUTS_DUR_BASE * guts
                ) ** _SPOT_STRUGGLE_GUTS_DUR_EXPONENT * _SPOT_STRUGGLE_GUTS_DUR_SCALE
                speed_bonus = (500 * guts) ** 0.6 * 0.0001
                entry["speed_bonus"] = round(speed_bonus, 4)
                entry["guts_stat"] = guts
            else:
                guts_duration = 3.0  # reasonable fallback

            # Cap at 9/24 distance threshold (9th section)
            if race_distance > 0 and rd.frames:
                dist_threshold = _SPOT_STRUGGLE_DIST_RATIO * race_distance
                dist_threshold_time = rd.frames[-1].time
                for frame in rd.frames:
                    if (
                        horse_idx < len(frame.horse_frames)
                        and frame.horse_frames[horse_idx].distance >= dist_threshold
                    ):
                        dist_threshold_time = frame.time
                        break
                if event.frame_time < dist_threshold_time:
                    guts_duration = min(guts_duration, dist_threshold_time - event.frame_time)
                else:
                    guts_duration = 0  # event started past threshold

            entry["duration"] = round(guts_duration, 4)
            entry["label"] = "Spot Struggle"
            entry["start_distance"] = round(
                _interpolate_distance(rd, horse_idx, event.frame_time), 2
            )
            entry["end_distance"] = round(
                _interpolate_distance(rd, horse_idx, event.frame_time + guts_duration), 2
            )

        elif event.type == SimulateEventType.COMPETE_BEFORE_SPURT:
            entry["label"] = "Compete (Before Spurt)"

        competes.append(entry)

    return competes


def _detect_rushed_segments(rd: RaceSimulateData) -> dict[int, list[dict]]:
    """
    Detect rushed (掛かり / kakari / temptation) segments for each horse.

    temptation_mode != 0 in the frame data means the horse is in the
    rushed state.  This is NOT pace down mode — pace down is a separate
    speed-based mechanic.

    Rushed: HP consumption 1.6x, forced position keep strategy change,
    succeeds all position keep wisdom rolls.
    Chance: (6.5 / log10(0.1 * Wiz + 1))^2 %  (自制心 reduces by flat 3%).
    Rolled pre-race; if triggered, activates in a random section 2-9.

    Forced strategies by original running style:
      Front Runner (Nige)  → speed up mode (BOOST = 4)
      Stalker (Senko)      → Nige (POSITION_NIGE = 3)
      Betweener (Sashi)    → 75% Nige (3), 25% Senko (2)
      Chaser (Oikomi)      → 70% Nige (3), 20% Senko (2), 10% Sashi (1)

    Mode values: 1=POSITION_SASHI, 2=POSITION_SENKO, 3=POSITION_NIGE, 4=BOOST
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


# ── Pace Down mode detection ──────────────────────────────────────────
#
# Pace Down is a position-keep mechanic (NOT temptation/rushed).
# When a non-front-runner is too close to the leader during the PK zone,
# the game multiplies their base target speed by 0.915.
# This is not stored in frame data, so we detect it heuristically.

_PD_MULTIPLIER = 0.915
_PD_PK_END_RATIO = 10 / 24  # Position keep zone ends at this fraction

# Base speed formula: 20 - (distance - 2000) / 1000
_PD_BASE_SPEED_CONST = 20.0
_PD_BASE_SPEED_OFFSET = 2000
_PD_BASE_SPEED_SCALE = 1000

# Strategy phase coefficients [Early (phase 0), Mid (phase 1)]
# Only phases 0-1 matter since pace down only happens during PK.
_PD_PHASE_COEFFS: dict[int, tuple[float, float]] = {
    1: (1.0, 0.98),  # NIGE (Front Runner) — included for completeness
    2: (0.978, 0.991),  # SENKO (Stalker)
    3: (0.938, 0.998),  # SASHI (Betweener)
    4: (0.931, 1.0),  # OIKOMI (Chaser)
}

# Position keep target ranges (meters behind leader) per strategy.
# (min_behind, max_behind) — if horse is closer than min, pace down triggers.
# min/max are multiplied by course_factor for longer courses.
_PD_PK_RANGES: dict[int, tuple[float, float]] = {
    2: (3.0, 5.0),  # SENKO
    3: (6.5, 7.0),  # SASHI
    4: (7.5, 8.0),  # OIKOMI
}

# Course factor: 1 + (distance - 1000) * 0.0008
_PD_CF_BASE = 1000
_PD_CF_SCALE = 0.0008

# Detection thresholds
_PD_SPEED_UPPER_RATIO = 1.06  # Speed must be below theoretical_pd * this
_PD_EXIT_ACCEL = 0.2  # Acceleration above this forces exit
_PD_EXIT_SPEED_RATIO = 1.02  # Speed must be above theoretical_pd * this for accel exit
_PD_MIN_DURATION = 0.3  # Minimum segment duration (seconds) to report


def _detect_pace_down_segments(
    rd: RaceSimulateData,
    race_distance: float,
) -> dict[int, list[dict]]:
    """
    Detect pace down segments using speed + position heuristics.

    Pace Down occurs during position keep phase when a non-front-runner
    is too close to the leader for its running style.  The game reduces
    target speed by multiplying the base by 0.915.

    Detection approach (simplified, not stat-model-dependent):
      1. Only check during PK zone (first 10/24 of race distance)
      2. Only non-front-runners can pace down
      3. Compute leader distance each frame
      4. If horse is closer to leader than PK range minimum for its style:
         compute theoretical pace-down speed = baseSpeed * phaseCoeff * 0.915
      5. If actual speed is within the pace-down speed band, flag the frame
      6. Build contiguous segments with min duration filter

    Returns dict of horse_index → list of segment dicts.
    """
    segments: dict[int, list[dict]] = {}
    if not rd.frames or len(rd.frames) < 2 or race_distance <= 0:
        return segments

    pk_end_dist = _PD_PK_END_RATIO * race_distance
    course_factor = 1 + (race_distance - _PD_CF_BASE) * _PD_CF_SCALE
    base_speed = (
        _PD_BASE_SPEED_CONST - (race_distance - _PD_BASE_SPEED_OFFSET) / _PD_BASE_SPEED_SCALE
    )

    # Identify which horses are front-runners (NIGE) or oonige
    oonige_horses: set[int] = set()
    _OONIGE_SKILL_ID = 202051
    for event in rd.events:
        if (
            event.type == SimulateEventType.SKILL
            and len(event.params) >= 2
            and event.params[1] == _OONIGE_SKILL_ID
        ):
            oonige_horses.add(event.params[0])

    for horse_idx in range(rd.horse_num):
        if horse_idx >= len(rd.horse_results):
            continue
        style = rd.horse_results[horse_idx].running_style

        # Front runners and oonige never pace down
        if style == RunningStyle.NIGE or horse_idx in oonige_horses:
            continue

        pk_range = _PD_PK_RANGES.get(style)
        if pk_range is None:
            continue
        pk_min_behind = pk_range[0] * course_factor
        phase_coeffs = _PD_PHASE_COEFFS.get(style, (0.978, 0.991))

        horse_segments: list[dict] = []
        current_seg: dict | None = None

        for fi in range(len(rd.frames) - 1):
            frame = rd.frames[fi]
            next_frame = rd.frames[fi + 1]
            if horse_idx >= len(frame.horse_frames) or horse_idx >= len(next_frame.horse_frames):
                continue

            hf = frame.horse_frames[horse_idx]
            hf_next = next_frame.horse_frames[horse_idx]
            dist = hf.distance
            time = frame.time
            dt = next_frame.time - time
            if dt <= 0:
                continue

            speed = hf.speed / 100.0  # u16 → m/s
            speed_next = hf_next.speed / 100.0
            accel = (speed_next - speed) / dt

            # Only detect in PK zone
            if dist >= pk_end_dist:
                if current_seg is not None:
                    _close_pd_seg(current_seg, time, dist, horse_segments)
                    current_seg = None
                break

            # Find leader distance this frame
            leader_dist = 0.0
            for hf2 in frame.horse_frames:
                if hf2.distance > leader_dist:
                    leader_dist = hf2.distance

            dist_behind_leader = leader_dist - dist

            # Not close enough to leader → not pacing down
            if dist_behind_leader >= pk_min_behind:
                if current_seg is not None:
                    _close_pd_seg(current_seg, time, dist, horse_segments)
                    current_seg = None
                continue

            # Compute theoretical pace-down target speed for this frame
            # Phase: 0 = early (< distance/6), 1 = mid (< distance*2/3)
            if dist < race_distance / 6:
                phase_coeff = phase_coeffs[0]
            else:
                phase_coeff = phase_coeffs[1]

            theoretical_pd_speed = base_speed * phase_coeff * _PD_MULTIPLIER

            # Check if actual speed is in the pace-down speed band
            is_pd_frame = speed < theoretical_pd_speed * _PD_SPEED_UPPER_RATIO

            # Exit if clearly accelerating out of pace-down territory
            if accel > _PD_EXIT_ACCEL and speed > theoretical_pd_speed * _PD_EXIT_SPEED_RATIO:
                is_pd_frame = False
            # Exit if speed is well above pace-down territory
            if speed > theoretical_pd_speed * _PD_SPEED_UPPER_RATIO:
                is_pd_frame = False

            if is_pd_frame:
                if current_seg is None:
                    current_seg = {
                        "start_time": round(time, 4),
                        "start_distance": round(dist, 2),
                    }
                current_seg["end_time"] = round(time, 4)
                current_seg["end_distance"] = round(dist, 2)
            else:
                if current_seg is not None:
                    _close_pd_seg(current_seg, time, dist, horse_segments)
                    current_seg = None

        # Close any open segment
        if current_seg is not None:
            last_f = rd.frames[-1]
            last_t = last_f.time
            last_d = (
                last_f.horse_frames[horse_idx].distance
                if horse_idx < len(last_f.horse_frames)
                else current_seg.get("end_distance", 0)
            )
            _close_pd_seg(current_seg, last_t, last_d, horse_segments)

        if horse_segments:
            segments[horse_idx] = horse_segments

    return segments


def _close_pd_seg(seg: dict, end_time: float, end_dist: float, out: list[dict]) -> None:
    """Finalize a pace-down segment and append if long enough."""
    seg["end_time"] = round(end_time, 4)
    seg["end_distance"] = round(end_dist, 2)
    seg["duration"] = round(seg["end_time"] - seg["start_time"], 4)
    if seg["duration"] >= _PD_MIN_DURATION:
        out.append(seg)


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


_LATE_START_ACCEL_THRESHOLD = 0.0001  # m/s²  (from Hakuraku useCharaTableData.ts)


def _summarize_horse(
    rd: RaceSimulateData,
    idx: int,
    race_distance: float = 0,
    compete_events: list[dict] | None = None,
    rushed_segments: dict[int, list[dict]] | None = None,
    pace_down_segments: dict[int, list[dict]] | None = None,
) -> dict | None:
    """Build a per-horse summary from simulation data with rich analysis."""
    if idx >= len(rd.horse_results):
        return None

    hr = rd.horse_results[idx]

    # ── Late start: frame-based detection ──────────────────────────────
    start_delay_ms = round(hr.start_delay_time * 1000, 1)
    is_late_start = False
    if len(rd.frames) >= 2:
        f0, f1 = rd.frames[0], rd.frames[1]
        if idx < len(f0.horse_frames) and idx < len(f1.horse_frames):
            v0 = f0.horse_frames[idx].speed / 100.0
            v1 = f1.horse_frames[idx].speed / 100.0
            dt = f1.time - f0.time
            if dt > 0:
                accel = (v1 - v0) / dt
                if accel < _LATE_START_ACCEL_THRESHOLD:
                    is_late_start = True
    # Also flag via the classic threshold as fallback
    if hr.start_delay_time >= 0.08:
        is_late_start = True

    # ── Last spurt delay ───────────────────────────────────────────────
    spurt_delay_m = None
    has_spurt = hr.last_spurt_start_distance > 0
    if has_spurt and race_distance > 0:
        phase_3_start = race_distance * 2 / 3
        spurt_delay_m = round(hr.last_spurt_start_distance - phase_3_start, 1)

    # ── HP outcome ─────────────────────────────────────────────────────
    hp_outcome: dict | None = None
    hp_start = 0
    hp_end = 0
    if rd.frames:
        first_frame = rd.frames[0]
        last_frame = rd.frames[-1]
        if idx < len(first_frame.horse_frames):
            hp_start = first_frame.horse_frames[idx].hp
        if idx < len(last_frame.horse_frames):
            hp_end = last_frame.horse_frames[idx].hp

        # Detect death: find first frame where HP == 0
        death_frame = None
        for frame in rd.frames:
            if idx < len(frame.horse_frames) and frame.horse_frames[idx].hp == 0:
                death_frame = frame
                break

        if death_frame and race_distance > 0:
            death_dist = death_frame.horse_frames[idx].distance
            remaining = race_distance - death_dist
            if remaining > 0.1:
                hp_outcome = {
                    "type": "died",
                    "death_distance": round(death_dist, 1),
                    "remaining_distance": round(remaining, 1),
                    "hp_start": hp_start,
                }
            else:
                hp_outcome = {
                    "type": "survived",
                    "hp_remaining": hp_end,
                    "hp_pct": round(hp_end / hp_start * 100, 1) if hp_start > 0 else 0,
                    "hp_start": hp_start,
                }
        else:
            hp_outcome = {
                "type": "survived",
                "hp_remaining": hp_end,
                "hp_pct": round(hp_end / hp_start * 100, 1) if hp_start > 0 else 0,
                "hp_start": hp_start,
            }

    # ── Aggregate timing stats ─────────────────────────────────────────
    dueling_time = 0.0
    spot_struggle_time = 0.0
    if compete_events:
        for ce in compete_events:
            if ce.get("horse_index") != idx:
                continue
            dur = ce.get("duration", 0)
            if ce.get("type_id") == SimulateEventType.COMPETE_FIGHT:
                dueling_time += dur
            elif ce.get("type_id") == SimulateEventType.COMPETE_TOP:
                spot_struggle_time += dur

    rushed_total_time = 0.0
    rushed_boost_segments: list[dict] = []
    if rushed_segments and idx in rushed_segments:
        for seg in rushed_segments[idx]:
            rushed_total_time += seg.get("duration", 0)
            # Track BOOST variant separately (speed boost rush)
            if seg.get("mode_id") == 4:  # TemptationMode.BOOST
                rushed_boost_segments.append(seg)

    pace_down_total_time = 0.0
    if pace_down_segments and idx in pace_down_segments:
        for seg in pace_down_segments[idx]:
            pace_down_total_time += seg.get("duration", 0)

    summary: dict = {
        "horse_index": idx,
        "finish_order": hr.finish_order,
        "finish_time": round(hr.finish_time, 4),
        "finish_time_raw": round(hr.finish_time_raw, 4),
        "finish_diff_time": round(hr.finish_diff_time, 4),
        "start_delay_time": round(hr.start_delay_time, 4),
        "start_delay_ms": start_delay_ms,
        "is_late_start": is_late_start,
        "running_style": running_style_name(hr.running_style),
        "running_style_id": hr.running_style,
        "last_spurt_start_distance": round(hr.last_spurt_start_distance, 2),
        "has_spurt": has_spurt,
        "spurt_delay_m": spurt_delay_m,
        "guts_order": hr.guts_order,
        "wiz_order": hr.wiz_order,
        "defeat": hr.defeat,
        "hp_start": hp_start,
        "hp_end": hp_end,
        "hp_outcome": hp_outcome,
        "dueling_time": round(dueling_time, 1),
        "spot_struggle_time": round(spot_struggle_time, 1),
        "rushed_total_time": round(rushed_total_time, 1),
        "rushed_boost_segments": rushed_boost_segments,
        "pace_down_total_time": round(pace_down_total_time, 1),
    }

    # Count skill activations for this horse
    skills = [
        e
        for e in rd.events
        if e.type == SimulateEventType.SKILL and len(e.params) >= 2 and e.params[0] == idx
    ]
    summary["skill_activation_count"] = len(skills)
    skill_ids = list(set(e.params[1] for e in skills))
    summary["skill_ids_activated"] = skill_ids

    # Detect oonige (大逃げ) — skill ID 202051
    _OONIGE_SKILL_ID = 202051
    is_oonige = _OONIGE_SKILL_ID in skill_ids
    summary["is_oonige"] = is_oonige
    if is_oonige:
        summary["running_style"] = "OONIGE"

    # Spot struggle HP consumption multiplier annotation
    # Front Runner (NIGE): 1.4x, Oonige: 3.5x
    # If rushed simultaneously: FR 3.6x, Oonige 7.7x
    is_front_runner = hr.running_style == RunningStyle.NIGE or is_oonige
    if is_front_runner and spot_struggle_time > 0:
        if is_oonige:
            summary["spot_struggle_hp_mult"] = "3.5x (oonige)"
        else:
            summary["spot_struggle_hp_mult"] = "1.4x (front runner)"

    return summary


# ── Main API ───────────────────────────────────────────────────────────


def _extract_race_metadata(decoded: dict) -> dict:
    """Extract race-level metadata: program_id, weather, ground_condition, etc.

    These live at various levels depending on the API endpoint.
    """
    meta: dict = {}
    data = decoded.get("data", decoded)

    # race_start_info often contains the race details
    rsi = _find_key_recursive(data, "race_start_info")
    if isinstance(rsi, dict):
        for key in ("program_id", "race_instance_id", "weather", "ground_condition"):
            if rsi.get(key) is not None:
                meta[key] = rsi[key]

    # Top-level or data-level fields
    for key in (
        "program_id",
        "race_instance_id",
        "weather",
        "ground_condition",
        "race_id",
    ):
        if key not in meta:
            val = _find_key_recursive(data, key, max_depth=3)
            if val is not None and not isinstance(val, (dict, list)):
                meta[key] = val

    return meta


def try_process_race(record: dict, include_frames: str = "all") -> dict | None:
    """
    Attempt to extract and process race simulation data from a network record.

    Args:
        record: A network event record dict (must have "msgpack_decoded" or
                similar decoded data).
        include_frames: "all" or "none" for frame data verbosity.

    Returns:
        A structured race data dict, or None if no race data found.
    """
    api_name = record.get("api", "")
    decoded = record.get("msgpack_decoded")

    if not decoded or not isinstance(decoded, dict):
        return None

    is_race = is_race_api(api_name) or is_race_result_api(api_name)

    # Check if this is a race-related API
    if not is_race:
        # Also check if decoded data contains race simulation data
        sim_data = _extract_race_simulate_data(decoded)
        if sim_data is None:
            return None
        log.info("  [race] Found race_simulate_data in non-race API: %s", api_name)
    else:
        sim_data = _extract_race_simulate_data(decoded)
        if sim_data is None:
            # Log the top-level keys so we can see what the response looks like
            top_keys = list(decoded.keys())[:20] if isinstance(decoded, dict) else []
            data_obj = decoded.get("data", {})
            data_keys = list(data_obj.keys())[:20] if isinstance(data_obj, dict) else []
            log.warning(
                "  [race] Race API '%s' detected but no race_simulate_data found. "
                "Top keys: %s, data keys: %s",
                api_name,
                top_keys,
                data_keys,
            )
        else:
            log.info(
                "  [race] Found race_simulate_data in %s (len=%d)",
                api_name,
                len(sim_data) if sim_data else 0,
            )

    race_record: dict = {
        "event": "race_simulation",
        "api": api_name,
    }

    # Extract race-level metadata (program_id, weather, ground_condition, etc.)
    race_meta = _extract_race_metadata(decoded)
    if race_meta:
        race_record["race_metadata"] = race_meta

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

    # Build a lookup: frame_order -> horse info (chara_id, card_id)
    horse_lookup: dict[int, dict] = {}
    for h in race_record.get("horses", []):
        fo = h.get("frame_order")
        if fo is not None:
            horse_lookup[fo] = h

    # Parse simulation binary
    if sim_data:
        try:
            rd = deserialize_from_base64(sim_data)
            race_record["simulation"] = race_data_to_dict(rd, include_frames)

            # Compute race distance and phases first
            phases = _detect_phases(rd)
            race_record["phases"] = phases
            race_distance = phases.get("total_distance", 0)

            # ── Course detection ───────────────────────────────────────
            meta = race_record.get("race_metadata", {})
            course_id = cd.guess_course_id(
                race_distance=int(race_distance),
                program_id=meta.get("program_id"),
                race_instance_id=meta.get("race_instance_id"),
            )
            if course_id:
                profile = cd.build_course_profile(course_id)
                if profile:
                    race_record["course_profile"] = profile
                    log.info(
                        "  [race] Detected course %s: %s %dm %s",
                        course_id,
                        profile["surface_name"],
                        profile["distance"],
                        profile["distance_type_name"],
                    )

            # Build guts lookup: horse_index (0-based) -> guts stat
            horse_guts: dict[int, int] = {}
            for h in race_record.get("horses", []):
                fo = h.get("frame_order")
                if fo is not None and h.get("guts"):
                    horse_guts[fo - 1] = h["guts"]  # frame_order is 1-based

            # Higher-level analysis
            race_record["skill_activations"] = _extract_skill_activations(rd, race_distance)

            rushed_raw = _detect_rushed_segments(rd)
            race_record["rushed_segments"] = {str(k): v for k, v in rushed_raw.items()}

            pace_down_raw = _detect_pace_down_segments(rd, race_distance)
            race_record["pace_down_segments"] = {str(k): v for k, v in pace_down_raw.items()}

            compete_events = _extract_compete_events(rd, horse_guts, race_distance)
            race_record["compete_events"] = compete_events

            # Per-horse summaries — enrich with chara_id / card_id from horse info
            summaries = []
            for i in range(rd.horse_num):
                s = _summarize_horse(
                    rd,
                    i,
                    race_distance=race_distance,
                    compete_events=compete_events,
                    rushed_segments={k: v for k, v in rushed_raw.items()},
                    pace_down_segments={k: v for k, v in pace_down_raw.items()},
                )
                if s:
                    # frame_order is 1-based, horse_index is 0-based
                    h_info = horse_lookup.get(i + 1)
                    if h_info:
                        s["chara_id"] = h_info.get("chara_id")
                        s["card_id"] = h_info.get("card_id")
                        s["guts_stat"] = h_info.get("guts")
                    summaries.append(s)
            race_record["horse_summaries"] = summaries

            log.info(
                "  [race] Parsed race: %d horses, %d frames, %d events, "
                "%d skill activations, %d compete events",
                rd.horse_num,
                rd.frame_count,
                rd.event_count,
                len(race_record["skill_activations"]),
                len(compete_events),
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

    phases = _detect_phases(rd)
    race_distance = phases.get("total_distance", 0)
    rushed_raw = _detect_rushed_segments(rd)
    pace_down_raw = _detect_pace_down_segments(rd, race_distance)
    compete_events = _extract_compete_events(rd, race_distance=race_distance)

    race_record: dict = {
        "event": "race_simulation",
        "api": api_name,
        "simulation": race_data_to_dict(rd, "sampled"),
        "skill_activations": _extract_skill_activations(rd, race_distance),
        "compete_events": compete_events,
        "rushed_segments": {str(k): v for k, v in rushed_raw.items()},
        "pace_down_segments": {str(k): v for k, v in pace_down_raw.items()},
        "phases": phases,
        "horse_summaries": [
            s
            for i in range(rd.horse_num)
            if (
                s := _summarize_horse(
                    rd,
                    i,
                    race_distance=race_distance,
                    compete_events=compete_events,
                    rushed_segments={k: v for k, v in rushed_raw.items()},
                    pace_down_segments={k: v for k, v in pace_down_raw.items()},
                )
            )
            is not None
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
    the race simulation binary.  Records arrive sequentially: all N horses
    for frame 0, then all N horses for frame 1, etc.

    IMPORTANT: LanePosition is NOT a stable horse identifier — it changes
    every frame as horses move laterally.  We detect horse count from the
    first frame and use sequential chunking (every N records = 1 frame).

    The game may deserialise the binary twice (preview + playback), producing
    duplicate data which we detect and deduplicate.

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

    # ── Step 1: Detect horse count from the first frame ─────────────────
    # The first frame has all horses at Distance ≈ 0.  We find horse_count
    # by looking for the first record whose (LanePosition, Hp) matches
    # record[0] — that's horse 0 appearing again in frame 1.
    first = records[0].get("fields", records[0])
    first_lane = first.get("LanePosition")
    first_hp = first.get("Hp")

    num_horses = 0
    for i in range(1, min(len(records), 50)):  # cap search at 50
        fields = records[i].get("fields", records[i])
        if fields.get("LanePosition") == first_lane and fields.get("Hp") == first_hp:
            num_horses = i
            break

    if num_horses < 2:
        # Fallback: count unique initial LanePositions (frame 0 all have Distance=0)
        seen_lanes: list[float] = []
        for rec in records:
            fields = rec.get("fields", rec)
            lane = fields.get("LanePosition")
            dist = fields.get("Distance", 0)
            if dist > 0.5:
                break  # past frame 0
            if lane is not None and lane not in seen_lanes:
                seen_lanes.append(lane)
            elif lane in seen_lanes:
                break  # wrapped around
        num_horses = len(seen_lanes) if len(seen_lanes) >= 2 else 0

    if num_horses < 2:
        log.warning("  [race-dump] Could not detect horse count from %d records", len(records))
        return None

    log.info("  [race-dump] Detected %d horses from initial frame pattern", num_horses)

    # ── Step 2: Group records into sequential frames ────────────────────
    # Every num_horses consecutive records = one frame.
    # Horse index within frame = position % num_horses.
    total_records = len(records)
    total_possible_frames = total_records // num_horses

    if total_possible_frames < 2:
        log.warning(
            "  [race-dump] Only %d records for %d horses — not enough frames",
            total_records,
            num_horses,
        )
        return None

    frames: list[list[dict]] = []  # frames[f][h] = horse data
    for fi in range(total_possible_frames):
        frame_data: list[dict] = []
        base = fi * num_horses
        for hi in range(num_horses):
            rec = records[base + hi]
            fields = rec.get("fields", rec)
            frame_data.append(
                {
                    "distance": fields.get("Distance", 0),
                    "lane_position": fields.get("LanePosition", 0),
                    "speed": fields.get("Speed", 0),
                    "hp": fields.get("Hp", 0),
                    "temptation_mode": fields.get("TemptationMode", 0),
                    "block_front": fields.get("BlockFrontHorseIndex", -1),
                }
            )
        frames.append(frame_data)

    # ── Step 3: Detect and remove duplicate deserialization ──────────────
    # The game often deserialises the binary twice (preview + playback).
    # If the first and second halves look identical, keep only one.
    if len(frames) >= 4 and len(frames) % 2 == 0:
        half = len(frames) // 2
        # Compare a few sampled frames from each half
        is_duplicate = True
        for check_idx in [0, half // 4, half // 2, half - 1]:
            if check_idx >= half:
                break
            f1 = frames[check_idx]
            f2 = frames[half + check_idx]
            for hi in range(num_horses):
                if (
                    abs(f1[hi]["distance"] - f2[hi]["distance"]) > 0.01
                    or abs(f1[hi]["hp"] - f2[hi]["hp"]) > 1
                ):
                    is_duplicate = False
                    break
            if not is_duplicate:
                break
        if is_duplicate:
            log.info(
                "  [race-dump] Detected double deserialization — using first half (%d frames)", half
            )
            frames = frames[:half]

    total_frames = len(frames)
    log.info(
        "  [race-dump] Assembled %d frames x %d horses from %d dump records",
        total_frames,
        num_horses,
        total_records,
    )

    # ── Step 4: Build per-horse time series ────────────────────────────
    horse_series: dict[int, list[dict]] = defaultdict(list)
    for frame_idx, frame in enumerate(frames):
        for horse_idx, data in enumerate(frame):
            horse_series[horse_idx].append(
                {
                    "frame": frame_idx,
                    **data,
                }
            )

    # ── Step 5: Compute per-horse summaries ────────────────────────────
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

        # Detect rushed (掛かり) segments (TemptationMode != 0)
        rushed_segments = []
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
                    rushed_segments.append(current_pd)
                    current_pd = None
        if current_pd is not None:
            current_pd["duration_frames"] = current_pd["end_frame"] - current_pd["start_frame"] + 1
            rushed_segments.append(current_pd)

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
            "rushed_segments": rushed_segments,
            "total_rushed_frames": sum(seg["duration_frames"] for seg in rushed_segments),
            "blocked_frames": blocked_frames,
        }
        horse_summaries.append(summary)

    # ── Step 6: Race-level analysis ────────────────────────────────────

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

    # ── Step 7: Sampled frame data for output ──────────────────────────
    # Output a subset of frames (every Nth) to keep the record manageable
    sample_interval = max(1, total_frames // 30)  # ~30 samples
    sampled_frames = []
    for fi in range(0, total_frames, sample_interval):
        frame = frames[fi]
        sampled: dict = {"frame_index": fi}
        for horse_idx, data in enumerate(frame):
            sampled[f"horse_{horse_idx}"] = {
                "distance": round(data["distance"], 2),
                "speed": round(data["speed"], 4),
                "hp": data["hp"],
                "temptation": data["temptation_mode"],
            }
        sampled_frames.append(sampled)

    # ── Step 8: Include lifecycle and skill data ───────────────────────
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
            # Capture the new structured fields
            for key in (
                "source",
                "skill_id",
                "skill_id_arg2",
                "horse_index",
                "arg1_int",
                "skillId",
                "level",
            ):
                if key in rec:
                    info[key] = rec[key]
            # Capture arg1_ probed fields (int32_at_0x... patterns)
            for k, v in rec.items():
                if k.startswith("arg1_") or k.startswith("field_"):
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
