"""
Course Data Loader
──────────────────
Loads static/course_data.json and provides lookup functions for
course details: slopes, corners, straights, surface, distance type.

This is the same data format used by Hakuraku's GameDataLoader.courseData.

Course ID format: 5-digit number TTTCC where:
  TTT = raceTrackId (first 3+ digits), CC = course variant
  e.g. 10101 = Track 10001, course 1, 1200m

Slope values: ±10000 = 1% grade
  positive = uphill, negative = downhill

Surface: 1 = turf, 2 = dirt

Distance type: 1 = short, 2 = mile, 3 = middle, 4 = long
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

log = logging.getLogger("clairvoyance")

# ── Locate the JSON file ───────────────────────────────────────────────

_FROZEN = getattr(sys, "frozen", False)
if _FROZEN:
    _BUNDLE_DIR = Path(sys._MEIPASS)  # type: ignore[attr-defined]
else:
    _BUNDLE_DIR = Path(__file__).resolve().parent.parent

_COURSE_DATA_PATH = _BUNDLE_DIR / "static" / "course_data.json"

# ── Cached data ────────────────────────────────────────────────────────

_course_data: dict[str, dict] | None = None


def _load() -> dict[str, dict]:
    global _course_data
    if _course_data is not None:
        return _course_data
    try:
        raw = _COURSE_DATA_PATH.read_text(encoding="utf-8")
        _course_data = json.loads(raw)
        log.info("Loaded course_data.json: %d courses", len(_course_data))
    except Exception as e:
        log.warning("Failed to load course_data.json: %s", e)
        _course_data = {}
    return _course_data


# ── Public API ─────────────────────────────────────────────────────────


def get_course(course_id: int | str) -> dict | None:
    """Get course data by ID. Returns None if not found."""
    data = _load()
    return data.get(str(course_id))


def get_slopes(course_id: int | str) -> list[dict]:
    """Get slope list for a course: [{start, length, slope}, ...]."""
    course = get_course(course_id)
    if not course:
        return []
    return course.get("slopes", [])


def get_corners(course_id: int | str) -> list[dict]:
    """Get corner list: [{start, length}, ...]."""
    course = get_course(course_id)
    if not course:
        return []
    return course.get("corners", [])


def get_straights(course_id: int | str) -> list[dict]:
    """Get straight list: [{start, end, frontType}, ...]."""
    course = get_course(course_id)
    if not course:
        return []
    return course.get("straights", [])


def get_surface(course_id: int | str) -> int:
    """Get surface type: 1=turf, 2=dirt, 0=unknown."""
    course = get_course(course_id)
    if not course:
        return 0
    return course.get("surface", 0)


def surface_name(surface: int) -> str:
    return {1: "Turf", 2: "Dirt"}.get(surface, "Unknown")


def distance_type_name(dt: int) -> str:
    return {1: "Short", 2: "Mile", 3: "Middle", 4: "Long"}.get(dt, "Unknown")


def find_courses_by_distance(distance: int) -> list[dict]:
    """Find all courses matching a given distance."""
    data = _load()
    results = []
    for cid, course in data.items():
        if course.get("distance") == distance:
            results.append({"course_id": cid, **course})
    return results


def guess_course_id(
    race_distance: int,
    program_id: int | None = None,
    race_instance_id: int | None = None,
) -> str | None:
    """
    Try to guess the course ID from available metadata.

    Strategy:
    1. If race_instance_id looks like a 5-digit course ID, use it directly.
    2. If program_id encodes a course ID, use it.
    3. Fall back to first course matching the distance.
    """
    data = _load()

    # Direct course ID match (race_instance_id is sometimes the course ID itself)
    if race_instance_id:
        rid_str = str(race_instance_id)
        if rid_str in data:
            return rid_str
        # Some APIs encode it differently — try last 5 digits
        if len(rid_str) > 5:
            suffix = rid_str[-5:]
            if suffix in data:
                return suffix

    # program_id can sometimes encode course information
    if program_id:
        pid_str = str(program_id)
        if pid_str in data:
            return pid_str

    # Fallback: first course matching distance
    if race_distance > 0:
        for cid, course in data.items():
            if course.get("distance") == race_distance:
                return cid

    return None


def get_slope_at_distance(course_id: int | str, distance: float) -> float:
    """Get the slope value at a given distance. Returns 0 if flat."""
    slopes = get_slopes(course_id)
    for s in slopes:
        if s["start"] <= distance < s["start"] + s["length"]:
            return s["slope"]
    return 0


def build_course_profile(course_id: int | str) -> dict | None:
    """
    Build a complete course profile dict for template rendering.
    Includes slope segments labeled as uphill/downhill/flat with percentages.
    """
    course = get_course(course_id)
    if not course:
        return None

    distance = course.get("distance", 0)
    slopes = course.get("slopes", [])
    corners = course.get("corners", [])
    straights = course.get("straights", [])

    # Build slope profile with human-readable labels
    slope_segments = []
    for s in slopes:
        grade_pct = abs(s["slope"]) / 10000
        direction = "downhill" if s["slope"] < 0 else "uphill"
        slope_segments.append(
            {
                "start": s["start"],
                "end": s["start"] + s["length"],
                "length": s["length"],
                "slope_raw": s["slope"],
                "grade_pct": round(grade_pct, 1),
                "direction": direction,
                "label": f"{'↓' if direction == 'downhill' else '↑'} {grade_pct:.1f}%",
            }
        )

    # Build corner/straight sections for track layout
    sections = []
    for c in corners:
        sections.append(
            {
                "type": "corner",
                "start": c["start"],
                "end": c["start"] + c["length"],
                "length": c["length"],
            }
        )
    for s in straights:
        sections.append(
            {
                "type": "straight",
                "subtype": "home" if s.get("frontType") == 1 else "back",
                "start": s["start"],
                "end": s["end"],
                "length": s["end"] - s["start"],
            }
        )
    sections.sort(key=lambda x: x["start"])

    return {
        "course_id": str(course_id),
        "distance": distance,
        "surface": course.get("surface", 0),
        "surface_name": surface_name(course.get("surface", 0)),
        "distance_type": course.get("distanceType", 0),
        "distance_type_name": distance_type_name(course.get("distanceType", 0)),
        "turn": "Right" if course.get("turn") == 1 else "Left",
        "lane_max": course.get("laneMax", 0),
        "slopes": slope_segments,
        "has_slopes": len(slope_segments) > 0,
        "corners": corners,
        "straights": straights,
        "sections": sections,
        "finish_time_min": course.get("finishTimeMin", 0),
        "finish_time_max": course.get("finishTimeMax", 0),
    }
