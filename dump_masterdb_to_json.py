#!/usr/bin/env python3
"""
Dump every table in master.mdb to individual JSON files inside masterdb_readable/.

Usage:
    python dump_masterdb_to_json.py                  # uses ./master.mdb
    python dump_masterdb_to_json.py /path/to/master.mdb
"""

import json
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "master.mdb"
OUT_DIR = Path(__file__).parent / "masterdb_readable"

if not DB_PATH.is_file():
    print(f"ERROR: {DB_PATH} not found")
    sys.exit(1)

OUT_DIR.mkdir(exist_ok=True)

conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
conn.row_factory = sqlite3.Row

tables = [
    r[0]
    for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
]

print(f"Found {len(tables)} tables in {DB_PATH.name}\n")

summary = {}

for table in tables:
    try:
        rows = conn.execute(f'SELECT * FROM "{table}"').fetchall()
    except Exception as e:
        print(f"  ✗ {table}: {e}")
        continue

    columns = rows[0].keys() if rows else []
    data = [dict(r) for r in rows]

    payload = {
        "table": table,
        "row_count": len(data),
        "columns": list(columns),
        "rows": data,
    }

    out_file = OUT_DIR / f"{table}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    summary[table] = len(data)
    print(f"  ✓ {table}: {len(data):,} rows → {out_file.name}")

conn.close()

# Write an index file listing all tables and row counts
index = {
    "total_tables": len(summary),
    "tables": [{"name": t, "row_count": c, "file": f"{t}.json"} for t, c in summary.items()],
}
index_file = OUT_DIR / "_index.json"
with open(index_file, "w", encoding="utf-8") as f:
    json.dump(index, f, ensure_ascii=False, indent=2)

print(f"\nDone — {len(summary)} tables dumped to {OUT_DIR}/")
print(f"Index written to {index_file.name}")
