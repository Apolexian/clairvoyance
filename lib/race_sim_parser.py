"""
Race Simulation Binary Data Parser
───────────────────────────────────
Ports hakuraku's RaceDataParser.ts to Python.

The game stores race simulation as a custom binary blob (NOT MsgPack).
It's gzip-compressed and base64-encoded inside the MsgPack API response.

Binary layout (all little-endian):
  Header:      i32 maxLength, i32 version                          (8 bytes)
  RaceStruct:  f32 distanceDiffMax, i32 horseNum,
               i32 horseFrameSize, i32 horseResultSize             (16 bytes)
  Padding1:    i32 size + <size> bytes
  FrameBlock:  i32 frameCount, i32 frameSize, then frameCount frames
    Frame:     f32 time + horseNum x HorseFrame
    HorseFrame: f32 distance, u16 lanePos, u16 speed,
                u16 hp, i8 temptationMode, i8 blockFrontHorseIndex (12 bytes)
  Padding2:    i32 size + <size> bytes
  HorseResults: horseNum x HorseResult
    HorseResult: i32 finishOrder, f32 finishTime, f32 finishDiffTime,
                 f32 startDelayTime, u8 gutsOrder, u8 wizOrder,
                 f32 lastSpurtStartDistance, u8 runningStyle,
                 i32 defeat, f32 finishTimeRaw                    (31 bytes)
  Padding3:    i32 size + <size> bytes
  EventBlock:  i32 eventCount, then eventCount events
    Event:     i16 eventSize, then:
               f32 frameTime, i8 type, i8 paramCount,
               paramCount x i32 param
"""

from __future__ import annotations

import base64
import gzip
import logging
import struct
from dataclasses import dataclass, field
from enum import IntEnum

log = logging.getLogger("clairvoyance")


# ── Enums ──────────────────────────────────────────────────────────────


class TemptationMode(IntEnum):
    NULL = 0
    POSITION_SASHI = 1
    POSITION_SENKO = 2
    POSITION_NIGE = 3
    BOOST = 4


class RunningStyle(IntEnum):
    NONE = 0
    NIGE = 1  # Front-runner
    SENKO = 2  # Stalker
    SASHI = 3  # Betweener
    OIKOMI = 4  # Chaser


class SimulateEventType(IntEnum):
    SCORE = 0
    CHALLENGE_MATCH_POINT = 1
    NOUSE_2 = 2
    SKILL = 3
    COMPETE_TOP = 4
    COMPETE_FIGHT = 5
    RELEASE_CONSERVE_POWER = 6
    STAMINA_LIMIT_BREAK_BUFF = 7
    COMPETE_BEFORE_SPURT = 8
    STAMINA_KEEP = 9
    SECURE_LEAD = 10


# ── Data classes ───────────────────────────────────────────────────────


@dataclass
class RaceSimulateHeader:
    max_length: int = 0
    version: int = 0


@dataclass
class HorseFrame:
    distance: float = 0.0
    lane_position: int = 0
    speed: int = 0
    hp: int = 0
    temptation_mode: int = 0
    block_front_horse_index: int = 0


@dataclass
class Frame:
    time: float = 0.0
    horse_frames: list[HorseFrame] = field(default_factory=list)


@dataclass
class HorseResult:
    finish_order: int = 0
    finish_time: float = 0.0
    finish_diff_time: float = 0.0
    start_delay_time: float = 0.0
    guts_order: int = 0
    wiz_order: int = 0
    last_spurt_start_distance: float = 0.0
    running_style: int = 0  # RunningStyle enum
    defeat: int = 0
    finish_time_raw: float = 0.0


@dataclass
class RaceEvent:
    frame_time: float = 0.0
    type: int = 0  # SimulateEventType enum
    param_count: int = 0
    params: list[int] = field(default_factory=list)


@dataclass
class RaceSimulateData:
    header: RaceSimulateHeader = field(default_factory=RaceSimulateHeader)
    distance_diff_max: float = 0.0
    horse_num: int = 0
    horse_frame_size: int = 0
    horse_result_size: int = 0
    frame_count: int = 0
    frame_size: int = 0
    frames: list[Frame] = field(default_factory=list)
    horse_results: list[HorseResult] = field(default_factory=list)
    event_count: int = 0
    events: list[RaceEvent] = field(default_factory=list)


# ── Constants ──────────────────────────────────────────────────────────

RACE_STRUCT_SIZE = 16
EVENT_STRUCT_SIZE = 6
HORSE_FRAME_SIZE = 12
HORSE_RESULT_CORE_SIZE = 39  # JP format


# ── Binary reader helpers ──────────────────────────────────────────────


def _read_f32(data: bytes, offset: int) -> float:
    return struct.unpack_from("<f", data, offset)[0]


def _read_i32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<i", data, offset)[0]


def _read_u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def _read_i16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<h", data, offset)[0]


def _read_u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def _read_u8(data: bytes, offset: int) -> int:
    return data[offset]


def _read_i8(data: bytes, offset: int) -> int:
    v = data[offset]
    return v - 256 if v > 127 else v


# ── Standard format parser (global server) ─────────────────────────────


def _deserialize_horse_frame(data: bytes, offset: int) -> HorseFrame:
    return HorseFrame(
        distance=_read_f32(data, offset),
        lane_position=_read_u16(data, offset + 4),
        speed=_read_u16(data, offset + 6),
        hp=_read_u16(data, offset + 8),
        temptation_mode=_read_i8(data, offset + 10),
        block_front_horse_index=_read_i8(data, offset + 11),
    )


def _deserialize_frame(data: bytes, offset: int, horse_num: int, horse_frame_size: int) -> Frame:
    frame = Frame(time=_read_f32(data, offset))
    offset += 4
    for _ in range(horse_num):
        frame.horse_frames.append(_deserialize_horse_frame(data, offset))
        offset += horse_frame_size
    return frame


def _deserialize_horse_result(data: bytes, offset: int) -> HorseResult:
    return HorseResult(
        finish_order=_read_i32(data, offset),
        finish_time=_read_f32(data, offset + 4),
        finish_diff_time=_read_f32(data, offset + 8),
        start_delay_time=_read_f32(data, offset + 12),
        guts_order=_read_u8(data, offset + 16),
        wiz_order=_read_u8(data, offset + 17),
        last_spurt_start_distance=_read_f32(data, offset + 18),
        running_style=_read_u8(data, offset + 22),
        defeat=_read_i32(data, offset + 23),
        finish_time_raw=_read_f32(data, offset + 27),
    )


def _deserialize_event(data: bytes, offset: int) -> tuple[RaceEvent, int]:
    frame_time = _read_f32(data, offset)
    event_type = _read_i8(data, offset + 4)
    param_count = _read_i8(data, offset + 5)
    params = []
    cursor = offset + EVENT_STRUCT_SIZE
    for _ in range(param_count):
        params.append(_read_i32(data, cursor))
        cursor += 4
    event = RaceEvent(
        frame_time=frame_time,
        type=event_type,
        param_count=param_count,
        params=params,
    )
    return event, cursor


def deserialize(data: bytes) -> RaceSimulateData:
    """Parse the standard (global server) race simulation binary format."""
    if len(data) < 8:
        raise ValueError("Data too short for header")

    # Header
    max_length = _read_i32(data, 0)
    if 4 + max_length > len(data):
        raise ValueError(f"Header maxLength {max_length} exceeds data size {len(data)}")
    version = _read_i32(data, 4)
    header = RaceSimulateHeader(max_length=max_length, version=version)
    offset = 4 + max_length

    # Race struct
    if offset + RACE_STRUCT_SIZE > len(data):
        raise ValueError("Data too short for race struct")
    distance_diff_max = _read_f32(data, offset)
    horse_num = _read_i32(data, offset + 4)
    horse_frame_size = _read_i32(data, offset + 8)
    horse_result_size = _read_i32(data, offset + 12)
    offset += RACE_STRUCT_SIZE

    result = RaceSimulateData(
        header=header,
        distance_diff_max=distance_diff_max,
        horse_num=horse_num,
        horse_frame_size=horse_frame_size,
        horse_result_size=horse_result_size,
    )

    # Padding 1
    pad1_size = _read_i32(data, offset)
    offset += 4 + pad1_size

    # Frame block
    frame_count = _read_i32(data, offset)
    frame_size = _read_i32(data, offset + 4)
    offset += 8
    result.frame_count = frame_count
    result.frame_size = frame_size

    for _ in range(frame_count):
        result.frames.append(_deserialize_frame(data, offset, horse_num, horse_frame_size))
        offset += frame_size

    # Padding 2
    pad2_size = _read_i32(data, offset)
    offset += 4 + pad2_size

    # Horse results
    for _ in range(horse_num):
        result.horse_results.append(_deserialize_horse_result(data, offset))
        offset += horse_result_size

    # Padding 3
    pad3_size = _read_i32(data, offset)
    offset += 4 + pad3_size

    # Events
    event_count = _read_i32(data, offset)
    offset += 4
    result.event_count = event_count

    for _ in range(event_count):
        event_size = _read_i16(data, offset)
        offset += 2
        event, _new_offset = _deserialize_event(data, offset)
        result.events.append(event)
        offset += event_size

    return result


# ── JP format parser (heuristic block detection) ───────────────────────


def _is_plausible_horse_frame(data: bytes, offset: int) -> bool:
    if offset + HORSE_FRAME_SIZE > len(data):
        return False
    try:
        distance = _read_f32(data, offset)
        lane_pos = _read_u16(data, offset + 4)
        speed = _read_u16(data, offset + 6)
        hp = _read_u16(data, offset + 8)
        return 0 <= distance <= 10000 and lane_pos <= 20000 and speed <= 10000 and hp <= 6000
    except (struct.error, IndexError):
        return False


def _is_valid_frame_start(data: bytes, offset: int, horse_num: int) -> bool:
    frame_size = 4 + horse_num * HORSE_FRAME_SIZE
    if offset < 32 or offset + frame_size > len(data):
        return False
    try:
        frame_time = _read_f32(data, offset)
        if frame_time < 0 or frame_time > 200:
            return False
    except (struct.error, IndexError):
        return False
    horse_start = offset + 4
    for i in range(horse_num):
        ho = horse_start + i * HORSE_FRAME_SIZE
        if not _is_plausible_horse_frame(data, ho):
            return False
    return True


def _normalize_lane_position(value: int) -> int:
    return max(0, min(10000, value))


def _normalize_speed(value: int) -> int:
    return max(0, value)


def _read_horse_frame_jp(data: bytes, offset: int) -> HorseFrame:
    distance = _read_f32(data, offset)
    lane_pos_raw = _read_u16(data, offset + 4)
    speed_raw = _read_u16(data, offset + 6)
    hp = _read_u16(data, offset + 8)
    tempt_raw = _read_u16(data, offset + 10)
    lane_position = _normalize_lane_position(lane_pos_raw)
    speed = _normalize_speed(speed_raw)
    temptation_mode = tempt_raw & 0xFF
    block_front = tempt_raw >> 8 & 0xFF
    if block_front > 127:
        block_front -= 256
    return HorseFrame(
        distance=distance,
        lane_position=lane_position,
        speed=speed,
        hp=hp,
        temptation_mode=temptation_mode,
        block_front_horse_index=block_front,
    )


def _read_frame_jp(data: bytes, offset: int, horse_num: int) -> Frame:
    frame = Frame(time=_read_f32(data, offset))
    ho = offset + 4
    for _ in range(horse_num):
        frame.horse_frames.append(_read_horse_frame_jp(data, ho))
        ho += HORSE_FRAME_SIZE
    return frame


def _find_next_block_start(
    data: bytes, search_start: int, horse_num: int, last_time: float
) -> int | None:
    frame_size = 4 + horse_num * HORSE_FRAME_SIZE
    offset = search_start
    while offset <= len(data) - frame_size:
        if _is_valid_frame_start(data, offset, horse_num):
            try:
                ft = _read_f32(data, offset)
            except (struct.error, IndexError):
                offset += 4
                continue
            if ft <= last_time:
                offset += 4
                continue
            next_off = offset + frame_size
            if _is_valid_frame_start(data, next_off, horse_num):
                try:
                    nt = _read_f32(data, next_off)
                except (struct.error, IndexError):
                    offset += 4
                    continue
                if ft < nt <= 200:
                    return offset
            prev_off = offset - frame_size
            if prev_off < search_start and ft > last_time:
                return offset
        offset += 4
    return None


def _comprehensive_block_detection(data: bytes, horse_num: int) -> list[Frame]:
    frame_size = 4 + horse_num * HORSE_FRAME_SIZE
    all_frames: list[Frame] = []

    current_start = (
        32
        if _is_valid_frame_start(data, 32, horse_num)
        else _find_next_block_start(data, 32, horse_num, -1.0)
    )
    last_time = -1.0

    while current_start is not None:
        current_offset = current_start
        block_count = 0
        while _is_valid_frame_start(data, current_offset, horse_num):
            ft = _read_f32(data, current_offset)
            if ft <= last_time:
                break
            all_frames.append(_read_frame_jp(data, current_offset, horse_num))
            last_time = ft
            current_offset += frame_size
            block_count += 1
        if block_count == 0:
            break
        current_start = _find_next_block_start(data, current_offset, horse_num, last_time)

    # Sort and deduplicate
    all_frames.sort(key=lambda f: f.time)
    seen = set()
    unique: list[Frame] = []
    for frame in all_frames:
        key = round(frame.time * 1_000_000)
        if key not in seen:
            seen.add(key)
            unique.append(frame)
    return unique


def _read_horse_result_jp(data: bytes, offset: int) -> tuple[HorseResult, int]:
    if offset + HORSE_RESULT_CORE_SIZE > len(data):
        raise ValueError("Data too short for JP horse result")

    finish_order = _read_i32(data, offset)
    finish_time = _read_f32(data, offset + 4)
    finish_diff_time = _read_f32(data, offset + 8)
    start_delay_time = _read_f32(data, offset + 12)
    guts_packed = _read_u16(data, offset + 16)
    last_spurt_start_distance = _read_f32(data, offset + 18)
    running_style_raw = _read_u8(data, offset + 22)
    defeat = _read_i32(data, offset + 23)
    finish_time_raw = _read_f32(data, offset + 27)
    # offset+31..+34 = other fields, offset+35 = noActivateSkillCount
    no_activate_skill_count = _read_i32(data, offset + 35)
    if no_activate_skill_count < 0 or no_activate_skill_count > 512:
        raise ValueError("Invalid JP horse result: noActivateSkillCount out of range")

    next_offset = offset + HORSE_RESULT_CORE_SIZE + no_activate_skill_count * 5
    if next_offset > len(data):
        raise ValueError("Data too short for JP horse result skills")

    running_style = running_style_raw if 1 <= running_style_raw <= 4 else 0

    result = HorseResult(
        finish_order=finish_order,
        finish_time=finish_time,
        finish_diff_time=finish_diff_time,
        start_delay_time=start_delay_time,
        guts_order=guts_packed & 0xFF,
        wiz_order=(guts_packed >> 8) & 0xFF,
        last_spurt_start_distance=last_spurt_start_distance,
        running_style=running_style,
        defeat=defeat,
        finish_time_raw=finish_time_raw,
    )
    return result, next_offset


def _parse_horse_results_near_offset(
    data: bytes, start_guess: int, horse_num: int
) -> tuple[list[HorseResult], int | None]:
    end = min(start_guess + 128, len(data) - 1)
    for start_offset in range(start_guess, end, 4):
        results: list[HorseResult] = []
        offset = start_offset
        ok = True
        for _ in range(horse_num):
            try:
                r, offset = _read_horse_result_jp(data, offset)
                results.append(r)
            except (ValueError, struct.error, IndexError):
                ok = False
                break
        if not ok:
            continue
        finish_orders = set(r.finish_order for r in results)
        if len(finish_orders) != horse_num:
            continue
        return results, offset
    return [], None


def _is_plausible_event(type_id: int, frame_time: float, param_count: int) -> bool:
    return 0 <= frame_time <= 1000 and 0 <= type_id <= 255 and param_count <= 64


def _read_event_jp(data: bytes, offset: int) -> tuple[RaceEvent, int, int]:
    """Returns (event, typeId, nextOffset)."""
    if offset + 6 > len(data):
        raise ValueError("Data too short for JP event")
    frame_time = _read_f32(data, offset)
    type_id = _read_u8(data, offset + 4)
    param_count = _read_u8(data, offset + 5)
    if param_count > 64:
        raise ValueError("Invalid JP event param count")
    cursor = offset + EVENT_STRUCT_SIZE
    if cursor + param_count * 4 + 3 > len(data):
        raise ValueError("Data too short for JP event params")
    params = []
    for _ in range(param_count):
        params.append(_read_i32(data, cursor))
        cursor += 4
    cursor += 3  # JP format has 3 trailing bytes per event
    event = RaceEvent(
        frame_time=frame_time,
        type=type_id,
        param_count=param_count,
        params=params,
    )
    return event, type_id, cursor


def _parse_event_sequence_with_count(
    data: bytes, start_offset: int, event_count: int
) -> list[tuple[RaceEvent, int]]:
    events: list[tuple[RaceEvent, int]] = []
    offset = start_offset
    for _ in range(event_count):
        try:
            event, type_id, next_offset = _read_event_jp(data, offset)
            if not _is_plausible_event(type_id, event.frame_time, event.param_count):
                return events
            event_size = EVENT_STRUCT_SIZE + event.param_count * 4
            events.append((event, event_size))
            offset = next_offset
        except (ValueError, struct.error, IndexError):
            return events
    return events


def _parse_events_near_offset(
    data: bytes, start_guess: int, event_count: int
) -> list[tuple[RaceEvent, int]]:
    best: list[tuple[RaceEvent, int]] = []
    for padding in range(9):
        start_offset = start_guess + padding
        if start_offset >= len(data):
            break
        events = _parse_event_sequence_with_count(data, start_offset, event_count)
        if len(events) > len(best):
            best = events
        if len(events) == event_count:
            return events
    return best


def deserialize_jp(data: bytes) -> RaceSimulateData:
    """Parse the JP format race simulation binary (heuristic block detection)."""
    if len(data) < 24:
        raise ValueError("Data too short for JP format")

    # Header
    max_length = _read_i32(data, 0)
    version = _read_i32(data, 4)
    header = RaceSimulateHeader(max_length=max_length, version=version)
    offset = 4 + max_length

    if offset + RACE_STRUCT_SIZE > len(data):
        raise ValueError("Data too short for JP race struct")

    distance_diff_max = _read_f32(data, offset)
    horse_num = _read_i32(data, offset + 4)
    horse_frame_size = _read_i32(data, offset + 8)
    horse_result_size = _read_i32(data, offset + 12)
    offset += RACE_STRUCT_SIZE

    # Padding 1
    _padding_size_1 = _read_i32(data, offset)

    # Heuristic frame detection
    frames = _comprehensive_block_detection(data, horse_num)
    frame_size = 4 + horse_num * HORSE_FRAME_SIZE
    post_frame_offset = 32 + len(frames) * frame_size

    # Horse results
    horse_results: list[HorseResult] = []
    results_end_offset: int | None = None

    if post_frame_offset + 12 <= len(data):
        start_guess = post_frame_offset + 12
        horse_results, results_end_offset = _parse_horse_results_near_offset(
            data, start_guess, horse_num
        )

    if not horse_results:
        raise ValueError("Failed to parse JP horse results")

    # Events
    events: list[RaceEvent] = []
    if results_end_offset is not None and results_end_offset + 10 <= len(data):
        sim_sync_root = _read_i32(data, results_end_offset)
        sim_size = _read_i32(data, results_end_offset + 4)
        sim_version = _read_u16(data, results_end_offset + 8)

        if 0 <= sim_sync_root <= 1 and 0 <= sim_size <= 5000 and 0 <= sim_version <= 10000:
            parsed = _parse_events_near_offset(data, results_end_offset + 10, sim_size)
            events = [e for e, _ in parsed]

    return RaceSimulateData(
        header=header,
        distance_diff_max=distance_diff_max,
        horse_num=horse_num,
        horse_frame_size=horse_frame_size if horse_frame_size > 0 else HORSE_FRAME_SIZE,
        horse_result_size=horse_result_size,
        frame_count=len(frames),
        frame_size=frame_size,
        frames=frames,
        horse_results=horse_results,
        event_count=len(events),
        events=events,
    )


# ── Public API ─────────────────────────────────────────────────────────


def deserialize_from_bytes(raw: bytes) -> RaceSimulateData:
    """
    Deserialize race simulation data from raw bytes.
    Tries standard format first, falls back to JP heuristic format.
    """
    try:
        return deserialize(raw)
    except Exception as global_err:
        try:
            return deserialize_jp(raw)
        except Exception as jp_err:
            raise ValueError(
                f"Failed to parse race data. Global: {global_err}. JP: {jp_err}"
            ) from jp_err


def deserialize_from_base64(b64_str: str) -> RaceSimulateData:
    """
    Deserialize race simulation data from a base64-encoded, gzip-compressed string.
    This is the format used in API responses.
    """
    decoded = base64.b64decode(b64_str)
    try:
        inflated = gzip.decompress(decoded)
    except Exception:
        # May not be gzipped
        inflated = decoded
    return deserialize_from_bytes(inflated)


# ── Serialization to dict (for JSON output) ───────────────────────────


def running_style_name(style: int) -> str:
    names = {0: "NONE", 1: "NIGE", 2: "SENKO", 3: "SASHI", 4: "OIKOMI"}
    return names.get(style, f"UNKNOWN_{style}")


def temptation_mode_name(mode: int) -> str:
    names = {0: "NULL", 1: "POSITION_SASHI", 2: "POSITION_SENKO", 3: "POSITION_NIGE", 4: "BOOST"}
    return names.get(mode, f"UNKNOWN_{mode}")


def event_type_name(t: int) -> str:
    names = {
        0: "SCORE",
        1: "CHALLENGE_MATCH_POINT",
        2: "NOUSE_2",
        3: "SKILL",
        4: "COMPETE_TOP",
        5: "COMPETE_FIGHT",
        6: "RELEASE_CONSERVE_POWER",
        7: "STAMINA_LIMIT_BREAK_BUFF",
        8: "COMPETE_BEFORE_SPURT",
        9: "STAMINA_KEEP",
        10: "SECURE_LEAD",
    }
    return names.get(t, f"UNKNOWN_{t}")


def race_data_to_dict(rd: RaceSimulateData, include_frames: str = "all") -> dict:
    """
    Convert RaceSimulateData to a JSON-serializable dict.

    include_frames:
      "all"     - include every frame
      "none"    - omit frames entirely
    """
    d: dict = {
        "header": {"max_length": rd.header.max_length, "version": rd.header.version},
        "distance_diff_max": round(rd.distance_diff_max, 4),
        "horse_num": rd.horse_num,
        "frame_count": rd.frame_count,
    }

    # Frames
    if include_frames != "none" and rd.frames:
        sampled = rd.frames
        d["frames"] = [_frame_to_dict(f) for f in sampled]

    # Horse results
    d["horse_results"] = [_horse_result_to_dict(hr) for hr in rd.horse_results]

    # Events
    d["events"] = [_event_to_dict(e) for e in rd.events]
    d["event_count"] = rd.event_count

    return d


def _frame_to_dict(f: Frame) -> dict:
    return {
        "time": round(f.time, 4),
        "horses": [
            {
                "distance": round(hf.distance, 2),
                "lane_position": hf.lane_position,
                "speed": hf.speed,
                "hp": hf.hp,
                "temptation_mode": temptation_mode_name(hf.temptation_mode),
                "block_front_horse_index": hf.block_front_horse_index,
            }
            for hf in f.horse_frames
        ],
    }


def _horse_result_to_dict(hr: HorseResult) -> dict:
    return {
        "finish_order": hr.finish_order + 1,  # binary is 0-based; convert to 1-based
        "finish_time": round(hr.finish_time, 4),
        "finish_diff_time": round(hr.finish_diff_time, 4),
        "start_delay_time": round(hr.start_delay_time, 4),
        "is_late_start": hr.start_delay_time >= 0.08,  # ≥80ms = late start
        "guts_order": hr.guts_order,
        "wiz_order": hr.wiz_order,
        "last_spurt_start_distance": round(hr.last_spurt_start_distance, 2),
        "running_style": running_style_name(hr.running_style),
        "defeat": hr.defeat,
        "finish_time_raw": round(hr.finish_time_raw, 4),
    }


def _event_to_dict(e: RaceEvent) -> dict:
    d: dict = {
        "frame_time": round(e.frame_time, 4),
        "type": event_type_name(e.type),
        "type_id": e.type,
        "params": e.params,
    }
    # Annotate skill events
    if e.type == SimulateEventType.SKILL and len(e.params) >= 2:
        d["horse_index"] = e.params[0]
        d["skill_id"] = e.params[1]
        if len(e.params) >= 3:
            d["skill_duration_raw"] = e.params[2]
    # Annotate compete events
    elif e.type in (
        SimulateEventType.COMPETE_TOP,
        SimulateEventType.COMPETE_FIGHT,
        SimulateEventType.COMPETE_BEFORE_SPURT,
    ):
        if len(e.params) >= 1:
            d["horse_index"] = e.params[0]
    return d
