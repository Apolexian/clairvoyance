#!/usr/bin/env python3
"""
Analyse master.mdb — discover all text_data categories and cross-reference them
against actual table ID columns to find definitive category → table mappings.

Usage:
    python analyse_masterdb.py                  # uses ./master.mdb
    python analyse_masterdb.py /path/to/master.mdb
"""

import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

# ── Locate DB ──────────────────────────────────────────────────────────

DB_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "master.mdb"
if not DB_PATH.is_file():
    print(f"ERROR: {DB_PATH} not found")
    sys.exit(1)

conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
conn.row_factory = sqlite3.Row

HR = "─" * 80


# ═══════════════════════════════════════════════════════════════════════
#  1. List all tables + their columns
# ═══════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 80}")
print("  SECTION 1: ALL TABLES")
print(f"{'═' * 80}\n")

tables = [
    r[0]
    for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
]

# For each table, get columns and row count
table_info: dict[str, list[dict]] = {}
table_counts: dict[str, int] = {}
id_columns: dict[str, list[str]] = {}  # table → list of id-like columns

for t in tables:
    try:
        cols = conn.execute(f'PRAGMA table_info("{t}")').fetchall()
    except Exception:
        continue
    col_list = [{"name": c["name"], "type": c["type"], "pk": bool(c["pk"])} for c in cols]
    table_info[t] = col_list

    try:
        cnt = conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
    except Exception:
        cnt = 0
    table_counts[t] = cnt

    # Find id-like columns
    ids = []
    for c in col_list:
        cn = c["name"].lower()
        if cn == "id" or cn.endswith("_id"):
            ids.append(c["name"])
    if ids:
        id_columns[t] = ids

print(f"Total tables: {len(tables)}\n")
for t in tables:
    cols = table_info.get(t, [])
    cnt = table_counts.get(t, 0)
    col_names = ", ".join(c["name"] for c in cols)
    ids = id_columns.get(t, [])
    id_str = f"  ← ID cols: {ids}" if ids else ""
    print(f"  {t:50s} ({cnt:>6,} rows)  [{col_names}]{id_str}")


# ═══════════════════════════════════════════════════════════════════════
#  2. text_data category census
# ═══════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 80}")
print("  SECTION 2: text_data CATEGORIES (category → row count)")
print(f"{'═' * 80}\n")

cat_rows = conn.execute(
    "SELECT category, COUNT(*) as cnt FROM text_data GROUP BY category ORDER BY category"
).fetchall()

categories = []
for r in cat_rows:
    cat, cnt = r["category"], r["cnt"]
    categories.append(cat)
    print(f"  category {cat:>4d}  →  {cnt:>6,} entries")

print(f"\n  Total categories: {len(categories)}")


# ═══════════════════════════════════════════════════════════════════════
#  3. Sample rows per category
# ═══════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 80}")
print("  SECTION 3: SAMPLE ROWS PER CATEGORY (up to 5)")
print(f"{'═' * 80}")

for cat in categories:
    samples = conn.execute(
        'SELECT "index", text FROM text_data WHERE category = ? ORDER BY "index" LIMIT 5',
        (cat,),
    ).fetchall()
    print(f"\n  ── Category {cat} ──")
    for s in samples:
        idx, text = s["index"], s["text"]
        # Truncate long text
        display = text[:80] + "…" if len(text) > 80 else text
        print(f"    index={idx:>12d}  │ {display}")


# ═══════════════════════════════════════════════════════════════════════
#  4. Cross-reference: which category maps to which table's ID column?
# ═══════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 80}")
print("  SECTION 4: CROSS-REFERENCE (category index values vs table ID columns)")
print(f"{'═' * 80}\n")

# Load all index values per category
cat_indices: dict[int, set[int]] = {}
for cat in categories:
    rows = conn.execute(
        'SELECT DISTINCT "index" FROM text_data WHERE category = ?', (cat,)
    ).fetchall()
    cat_indices[cat] = {r[0] for r in rows}

# Load ID values for each table.id_col pair (only non-empty tables with id columns)
table_id_sets: dict[str, set[int]] = {}  # "table.column" → set of values
for t, cols in id_columns.items():
    if table_counts.get(t, 0) == 0:
        continue
    for col in cols:
        key = f"{t}.{col}"
        try:
            rows = conn.execute(f'SELECT DISTINCT "{col}" FROM "{t}" LIMIT 50000').fetchall()
            vals = set()
            for r in rows:
                v = r[0]
                if isinstance(v, int):
                    vals.add(v)
            if vals:
                table_id_sets[key] = vals
        except Exception:
            pass

# For each category, find the best matching table.column by overlap
print(
    f"  {'Category':>8s}  {'Table.Column':<50s}  {'Overlap':>8s}  {'Cat Size':>8s}  {'Tbl Size':>8s}"
)
print(f"  {'─' * 8}  {'─' * 50}  {'─' * 8}  {'─' * 8}  {'─' * 8}")

matches_by_cat: dict[int, list] = defaultdict(list)

for cat in categories:
    cat_set = cat_indices[cat]
    if not cat_set:
        continue
    for tkey, tbl_set in table_id_sets.items():
        overlap = len(cat_set & tbl_set)
        if overlap == 0:
            continue
        # Overlap as fraction of the smaller set
        min_size = min(len(cat_set), len(tbl_set))
        pct = overlap / min_size * 100 if min_size > 0 else 0
        if pct >= 10:  # 10% threshold to reduce noise
            matches_by_cat[cat].append((pct, overlap, tkey, len(cat_set), len(tbl_set)))

for cat in categories:
    matches = matches_by_cat.get(cat, [])
    matches.sort(key=lambda x: -x[0])
    for pct, _overlap, tkey, cat_sz, tbl_sz in matches[:3]:
        print(f"  {cat:>8d}  {tkey:<50s}  {pct:>7.1f}%  {cat_sz:>8,}  {tbl_sz:>8,}")


# ═══════════════════════════════════════════════════════════════════════
#  5. Validate our current master_db.py mappings
# ═══════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 80}")
print("  SECTION 5: VALIDATE CURRENT master_db.py CATEGORY CONSTANTS")
print(f"{'═' * 80}\n")

# Our current mappings from master_db.py
KNOWN = {
    4: "CATEGORY_CARD_NAME_FULL — [Title] CharaName via card_data.id",
    5: "CATEGORY_CARD_TITLE — [Title] via card_data.id",
    6: "CATEGORY_CHARA_NAME — character names via chara_data.id",
    7: "CATEGORY_CHARA_CV — voice actor via chara_data.id",
    13: "CATEGORY_GACHA_TEXT — gacha banner text via gacha_data.id",
    14: "CATEGORY_DRESS_NAME — dress names via dress_data.id",
    16: "CATEGORY_SONG_NAME — song/live via live_data.music_id",
    23: "CATEGORY_ITEM_NAME — item names via item_data.id",
    24: "CATEGORY_ITEM_COMMENT — item descriptions via item_data.id",
    28: "CATEGORY_RACE_INSTANCE_NAME — race instance via race_instance.id",
    32: "CATEGORY_RACE_NAME — race names via race.id",
    34: "CATEGORY_RACE_TRACK_NAME — race track names via race_track.id",
    47: "CATEGORY_SKILL_NAME — skill names via skill_data.id",
    48: "CATEGORY_SKILL_DESC — skill descriptions via skill_data.id",
    59: "CATEGORY_MOB_NAME — mob names via mob_data.mob_id",
    64: "CATEGORY_GIFT_MESSAGE — gift messages via gift_message.id",
    67: "CATEGORY_MISSION_NAME — mission names via mission_data.id",
    70: "CATEGORY_LOGIN_BONUS_NAME — login bonus names via login_bonus_data.id",
    76: "CATEGORY_SUPPORT_CARD_TITLE — support card titles via support_card_data.id",
    94: "CATEGORY_MAIN_STORY_TITLE — main story episodes via main_story_data.id",
    111: "CATEGORY_EPITHET_NAME — epithet/saddle names",
    113: "CATEGORY_PIECE_NAME — piece/character shards via piece_data.id",
    121: "CATEGORY_SM_CHARA_GRADE — single mode chara grade",
    147: "CATEGORY_SCENARIO_NAME — scenario/training skill names",
    148: "CATEGORY_TS_SCORE_BONUS — team stadium score bonus",
    155: "CATEGORY_SC_UNIQUE_EFFECT — support card unique effect",
    181: "CATEGORY_STORY_NAME — story names (general)",
    189: "CATEGORY_STORY_EVENT_TITLE — story event titles",
    190: "CATEGORY_STORY_EVENT_MISSION — story event mission names",
    191: "CATEGORY_STORY_EVENT_EPISODE — story event episode titles",
    225: "(legacy) CATEGORY_ITEM_NAME fallback",
}

existing_cats = set(cat for cat, _ in cat_rows)
for cat_num, label in sorted(KNOWN.items()):
    exists = cat_num in existing_cats
    count = 0
    if exists:
        for r in cat_rows:
            if r["category"] == cat_num:
                count = r["cnt"]
                break
    status = f"✅ {count:>6,} rows" if exists else "❌ NOT FOUND"
    print(f"  cat {cat_num:>4d}  {status}  │ {label}")

# Show categories in the DB that we DON'T have mappings for
unmapped = existing_cats - set(KNOWN.keys())
if unmapped:
    print(f"\n  ── Categories in DB with NO mapping in master_db.py ({len(unmapped)}) ──")
    for cat in sorted(unmapped):
        count = 0
        for r in cat_rows:
            if r["category"] == cat:
                count = r["cnt"]
                break
        # Show a sample
        sample = conn.execute(
            'SELECT "index", text FROM text_data WHERE category = ? ORDER BY "index" LIMIT 2',
            (cat,),
        ).fetchall()
        sample_str = " | ".join(f"{s['index']}={s['text'][:40]}" for s in sample)
        print(f"    cat {cat:>4d}  ({count:>6,} rows)  samples: {sample_str}")


# ═══════════════════════════════════════════════════════════════════════
#  6. Investigate choice-related categories from UmamusumeExplorer
#     TextCategory.cs:
#       267 = SingleModeGainSelectChoiceLabel
#       394 = MasterSingleModeEventChoiceRewardTitle
#       181 = SingleModeStoryTitle  (already used)
#     Can we get choice text straight from text_data instead of parsing
#     asset bundles?
# ═══════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 80}")
print("  SECTION 6: CHOICE-TEXT CATEGORIES (267, 394) vs STORY DATA")
print(f"{'═' * 80}\n")

CHOICE_CATS = {
    267: "SingleModeGainSelectChoiceLabel",
    394: "MasterSingleModeEventChoiceRewardTitle",
    181: "SingleModeStoryTitle (existing)",
}

for cat_id, label in sorted(CHOICE_CATS.items()):
    rows = conn.execute("SELECT COUNT(*) FROM text_data WHERE category = ?", (cat_id,)).fetchall()
    count = rows[0][0] if rows else 0
    print(f"  Category {cat_id} ({label}): {count:,} rows")
    if count > 0:
        samples = conn.execute(
            'SELECT "index", text FROM text_data WHERE category = ? ORDER BY "index" LIMIT 10',
            (cat_id,),
        ).fetchall()
        for s in samples:
            display = s["text"][:80] + "…" if len(s["text"]) > 80 else s["text"]
            print(f"    index={s['index']:>12d}  │ {display}")
    print()

# ── Check if cat 267 indices match story_ids in single_mode_story_data ──
print(f"  {HR}")
print("  Cross-referencing category 267 indices against single_mode_story_data...")

has_smsd = "single_mode_story_data" in tables
has_smcs = "single_mode_conclusion_set" in tables

if has_smsd:
    smsd_cols = [c["name"] for c in table_info.get("single_mode_story_data", [])]
    print(f"  single_mode_story_data columns: {smsd_cols}")
    smsd_count = table_counts.get("single_mode_story_data", 0)
    print(f"  single_mode_story_data rows: {smsd_count:,}")

    # Get all story_ids from the table
    smsd_story_ids = {
        r[0]
        for r in conn.execute("SELECT DISTINCT story_id FROM single_mode_story_data").fetchall()
    }
    smsd_ids = {
        r[0] for r in conn.execute("SELECT DISTINCT id FROM single_mode_story_data").fetchall()
    }

    cat267_indices = {
        r[0]
        for r in conn.execute(
            'SELECT DISTINCT "index" FROM text_data WHERE category = 267'
        ).fetchall()
    }

    if cat267_indices:
        overlap_story = len(cat267_indices & smsd_story_ids)
        overlap_id = len(cat267_indices & smsd_ids)
        print(f"\n  Category 267 has {len(cat267_indices):,} distinct indices")
        print(f"  Overlap with single_mode_story_data.story_id: {overlap_story:,}")
        print(f"  Overlap with single_mode_story_data.id:       {overlap_id:,}")

        # Check if indices look like story_ids (typically 8-9 digits starting with 2-8)
        sample_indices = sorted(cat267_indices)[:10]
        print(f"  Sample cat 267 indices: {sample_indices}")
        sample_story_ids = sorted(smsd_story_ids)[:10]
        print(f"  Sample story_ids:       {sample_story_ids}")
    else:
        print("  Category 267 is empty — no choice labels in text_data")
else:
    print("  ❌ single_mode_story_data table NOT FOUND")

# ── Check conclusion_set to understand branch counts ──────────────────
print(f"\n  {HR}")
if has_smcs:
    smcs_cols = [c["name"] for c in table_info.get("single_mode_conclusion_set", [])]
    print(f"  single_mode_conclusion_set columns: {smcs_cols}")
    smcs_count = table_counts.get("single_mode_conclusion_set", 0)
    print(f"  single_mode_conclusion_set rows: {smcs_count:,}")

    # How many story_ids have >1 conclusion (i.e. actual choices)?
    multi = conn.execute(
        "SELECT story_id, COUNT(DISTINCT conclusion_id) as n "
        "FROM single_mode_conclusion_set "
        "GROUP BY story_id HAVING n > 1 "
        "ORDER BY n DESC"
    ).fetchall()
    print(f"  Stories with >1 branch (actual choices): {len(multi):,}")
    if multi:
        print(f"  Max branches: {multi[0]['n']} (story_id={multi[0]['story_id']})")
        # Show a few
        for r in multi[:5]:
            sid, n = r["story_id"], r["n"]
            # Check if this story_id has text in cat 267
            t267 = conn.execute(
                'SELECT text FROM text_data WHERE category = 267 AND "index" = ?',
                (sid,),
            ).fetchall()
            # Also check cat 181
            t181 = conn.execute(
                'SELECT text FROM text_data WHERE category = 181 AND "index" = ?',
                (sid,),
            ).fetchall()
            txt267 = t267[0]["text"][:50] if t267 else "(none)"
            txt181 = t181[0]["text"][:50] if t181 else "(none)"
            print(f"    story_id={sid}  branches={n}  cat267='{txt267}'  cat181='{txt181}'")
else:
    print("  ❌ single_mode_conclusion_set table NOT FOUND")

# ── Look for any other choice/event related tables ────────────────────
print(f"\n  {HR}")
print("  Tables with 'choice' or 'event' or 'conclusion' in name:")
for t in tables:
    tl = t.lower()
    if "choice" in tl or "conclusion" in tl or ("event" in tl and "single" in tl):
        cols = [c["name"] for c in table_info.get(t, [])]
        cnt = table_counts.get(t, 0)
        print(f"    {t:55s} ({cnt:>6,} rows)  [{', '.join(cols)}]")
        # Show a few sample rows
        if cnt > 0:
            sample_rows = conn.execute(f'SELECT * FROM "{t}" LIMIT 3').fetchall()
            for sr in sample_rows:
                print(f"      → {dict(sr)}")


conn.close()
print(f"\n{'═' * 80}")
print("  Done.")
print(f"{'═' * 80}\n")
