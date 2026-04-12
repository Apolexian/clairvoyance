"""
Session directory management and JSONL writer for clairvoyance.
"""

from __future__ import annotations

import contextlib
import json
import logging
import sys
from datetime import datetime, timezone
from io import TextIOWrapper
from pathlib import Path

log = logging.getLogger("clairvoyance")

_FROZEN = getattr(sys, "frozen", False)

if _FROZEN:
    # PyInstaller: working directories live next to the .exe, not in _MEIPASS
    _APP_DIR = Path(sys.executable).resolve().parent
else:
    _APP_DIR = Path(__file__).resolve().parent.parent

SESSIONS_DIR = _APP_DIR / "sessions"
DISCOVERY_DIR = _APP_DIR / "discovery"


def _ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


class Session:
    """
    Manages a single collection session.

    Creates a timestamped directory and provides writers for each data domain.
    """

    def __init__(self, label: str = ""):
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
        name = f"{ts}_{label}" if label else ts
        self.dir = _ensure_dir(SESSIONS_DIR / name)
        self._files: dict[str, TextIOWrapper] = {}
        self._counts: dict[str, int] = {}
        log.info("Session directory: %s", self.dir)

    def write(self, domain: str, record: dict) -> None:
        """Append a JSON record to `<domain>.jsonl`."""
        if domain not in self._files:
            path = self.dir / f"{domain}.jsonl"
            self._files[domain] = path.open("a", encoding="utf-8")
            self._counts[domain] = 0

        record.setdefault("_ts", datetime.now(timezone.utc).isoformat())
        line = json.dumps(record, ensure_ascii=False, default=str)
        self._files[domain].write(line + "\n")
        self._files[domain].flush()
        self._counts[domain] += 1

    def write_manifest(self, **extra: object) -> None:
        """Write manifest.json with session metadata."""
        manifest = {
            "created": datetime.now(timezone.utc).isoformat(),
            "counts": dict(self._counts),
            **extra,
        }
        (self.dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

    @property
    def counts(self) -> dict[str, int]:
        return dict(self._counts)

    def close(self) -> None:
        for f in self._files.values():
            with contextlib.suppress(Exception):
                f.close()
        self._files.clear()


def save_discovery(filename: str, data: object) -> Path:
    """Save a discovery artifact (e.g. class_dump.json) to the discovery dir."""
    d = _ensure_dir(DISCOVERY_DIR)
    path = d / filename
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    log.info("Saved discovery artifact: %s", path)
    return path
