"""
SQLite store for crawled player data.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

SCHEMA = Path(__file__).parent / "schema.sql"
DEFAULT_DB = Path(__file__).parent.parent / "crawler.db"


class Store:
    def __init__(self, path: str | Path = DEFAULT_DB) -> None:
        self.path = Path(path)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self._apply_schema()

    def _apply_schema(self) -> None:
        sql = SCHEMA.read_text(encoding="utf-8")
        self.conn.executescript(sql)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    # ── Queue management ──────────────────────────────────────────────────

    def enqueue(self, viewer_ids: list[int], source: str = "recommend") -> int:
        """Add viewer_ids to the crawl queue. Returns count actually inserted."""
        now = int(time.time())
        added = 0
        for vid in viewer_ids:
            try:
                self.conn.execute(
                    "INSERT OR IGNORE INTO crawl_queue (viewer_id, state, added_at) VALUES (?, 'pending', ?)",
                    (vid, now),
                )
                self.conn.execute(
                    "INSERT OR IGNORE INTO seeds (viewer_id, source, added_at) VALUES (?, ?, ?)",
                    (vid, source, now),
                )
                added += self.conn.execute("SELECT changes()").fetchone()[0]
            except sqlite3.Error:
                pass
        self.conn.commit()
        return added

    def next_pending(self, limit: int = 50) -> list[int]:
        rows = self.conn.execute(
            "SELECT viewer_id FROM crawl_queue WHERE state = 'pending' ORDER BY added_at LIMIT ?",
            (limit,),
        ).fetchall()
        return [r["viewer_id"] for r in rows]

    def mark_done(self, viewer_id: int) -> None:
        now = int(time.time())
        self.conn.execute(
            "UPDATE crawl_queue SET state = 'done', done_at = ? WHERE viewer_id = ?",
            (now, viewer_id),
        )
        self.conn.commit()

    def mark_error(self, viewer_id: int) -> None:
        self.conn.execute(
            "UPDATE crawl_queue SET state = 'error' WHERE viewer_id = ?",
            (viewer_id,),
        )
        self.conn.commit()

    def queue_stats(self) -> dict:
        rows = self.conn.execute(
            "SELECT state, COUNT(*) AS n FROM crawl_queue GROUP BY state"
        ).fetchall()
        return {r["state"]: r["n"] for r in rows}

    def already_queued(self, viewer_id: int) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM crawl_queue WHERE viewer_id = ?", (viewer_id,)
        ).fetchone()
        return row is not None

    # ── Player upsert ─────────────────────────────────────────────────────

    def upsert_player(self, data: dict) -> None:
        """
        Upsert a player record from a friend/search or pre_single_mode response.

        Expected keys (all optional except viewer_id):
          viewer_id, display_name,
          borrow_card_id, borrow_card_level, borrow_card_limit_break,
          profile_chara_id, profile_card_id, profile_rank,
          raw_json (dict → will be json-dumped)
        """
        now = int(time.time())
        vid = data["viewer_id"]
        raw = json.dumps(data.get("raw_json"), ensure_ascii=False) if data.get("raw_json") else None

        self.conn.execute(
            """
            INSERT INTO players
                (viewer_id, display_name,
                 borrow_card_id, borrow_card_level, borrow_card_limit_break,
                 profile_chara_id, profile_card_id, profile_rank,
                 first_seen, last_seen, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(viewer_id) DO UPDATE SET
                display_name          = excluded.display_name,
                borrow_card_id        = excluded.borrow_card_id,
                borrow_card_level     = excluded.borrow_card_level,
                borrow_card_limit_break = excluded.borrow_card_limit_break,
                profile_chara_id      = excluded.profile_chara_id,
                profile_card_id       = excluded.profile_card_id,
                profile_rank          = excluded.profile_rank,
                last_seen             = excluded.last_seen,
                raw_json              = excluded.raw_json
            """,
            (
                vid,
                data.get("display_name"),
                data.get("borrow_card_id"),
                data.get("borrow_card_level"),
                data.get("borrow_card_limit_break"),
                data.get("profile_chara_id"),
                data.get("profile_card_id"),
                data.get("profile_rank"),
                now,
                now,
                raw,
            ),
        )
        self.conn.commit()

    def player_count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM players").fetchone()[0]
