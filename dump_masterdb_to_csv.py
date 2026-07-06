#!/usr/bin/env python3
"""
Dump every table in a master.mdb to individual CSV files.

Usage:
    python dump_masterdb_to_csv.py <path-to-master.mdb> <output-dir>
"""

import csv
import sqlite3
import sys
from pathlib import Path

def dump(db_path: Path, out_dir: Path) -> None:
    if not db_path.is_file():
        print(f"ERROR: {db_path} not found")
        sys.exit(1)

    out_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    tables = [
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
    ]

    print(f"Found {len(tables)} tables in {db_path}\n")

    for table in tables:
        try:
            cursor = conn.execute(f'SELECT * FROM "{table}"')
        except Exception as e:
            print(f"  x {table}: {e}")
            continue

        rows = cursor.fetchall()
        columns = [d[0] for d in cursor.description]

        out_file = out_dir / f"{table}.csv"
        with open(out_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerows(rows)

        print(f"  ok {table}: {len(rows):,} rows -> {out_file.name}")

    conn.close()
    print(f"\nDone -- {len(tables)} tables dumped to {out_dir}/")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python dump_masterdb_to_csv.py <path-to-master.mdb> <output-dir>")
        sys.exit(1)
    dump(Path(sys.argv[1]), Path(sys.argv[2]))
