"""
Process finder and Frida attach logic for Uma Musume.
Extracted from umaexperiment/sp_modifier.py and UmaExtractor/py/extract_umas.py.
"""

from __future__ import annotations

import logging
import time

import frida

log = logging.getLogger("clairvoyance")

TARGET_PROCESS_NAMES = [
    "UmamusumePrettyDerby.exe",
    "UmamusumePrettyDerby",
]
PROCESS_KEYWORDS = ["uma", "musume", "derby", "cygames"]
MAX_WAIT_SECONDS = 120


def find_candidate_processes() -> list:
    """Return a list of processes whose names match Uma Musume keywords."""
    try:
        device = frida.get_local_device()
        processes = device.enumerate_processes()
    except Exception as e:
        log.warning("Could not enumerate processes: %s", e)
        return []

    candidates = []
    for proc in processes:
        name = (proc.name or "").lower()
        if any(kw in name for kw in PROCESS_KEYWORDS):
            candidates.append(proc)
    candidates.sort(key=lambda p: (p.name or "").lower())
    return candidates


def attach(timeout: int = MAX_WAIT_SECONDS) -> frida.core.Session | None:
    """
    Try to attach to the Uma Musume process.
    Tries exact process names first, then falls back to keyword matching.
    Retries until timeout.
    """
    deadline = time.monotonic() + timeout
    attempt = 0

    while time.monotonic() < deadline:
        attempt += 1
        errors: list[tuple[str, Exception]] = []

        # Try exact names
        for name in TARGET_PROCESS_NAMES:
            try:
                session = frida.attach(name)
                log.info("Attached to %s", name)
                return session
            except Exception as e:
                errors.append((name, e))

        # Try keyword matches
        candidates = find_candidate_processes()
        for proc in candidates:
            try:
                session = frida.attach(proc.pid)
                log.info("Attached to %s (pid %d)", proc.name, proc.pid)
                return session
            except Exception as e:
                errors.append((f"{proc.name} (pid {proc.pid})", e))

        if attempt == 1:
            log.info("Game not found yet, retrying every 3s (timeout %ds)...", timeout)
            if candidates:
                log.info(
                    "  Candidates seen: %s",
                    ", ".join(f"{p.name} (pid {p.pid})" for p in candidates[:5]),
                )
            else:
                log.info("  No matching processes found.")

        time.sleep(3)

    log.error("Could not attach to game within %ds.", timeout)
    return None
