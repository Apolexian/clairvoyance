#!/usr/bin/env python3
"""
Composite support card images with frame, rarity badge, and type icon.

Takes raw support card textures (tex_support_card_{id}) and composites them
with the appropriate frame, rarity badge, and training type icon into a
single ready-to-display webp.

Usage (standalone):
  uv run compose_cards.py                          # process all in static/cards/
  uv run compose_cards.py --input dump-jp/ --output static/cards/composite/
  uv run compose_cards.py --ids 30277 30278

Usage (as library):
  from compose_cards import composite_support_cards
  composite_support_cards(input_dir, output_dir)
"""

from __future__ import annotations

import logging
import re
import sqlite3
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore[assignment]

log = logging.getLogger("compose_cards")

APP_DIR = Path(__file__).resolve().parent
OVERLAY_DIR = APP_DIR / "static" / "overlay"
FRAME_DIR = OVERLAY_DIR / "frame"
RARITY_DIR = OVERLAY_DIR / "rarity"
TYPE_ICON_DIR = OVERLAY_DIR / "type"

# Output canvas: 3:4 aspect, matching the umaguide composite dimensions
WIDTH = 1440
HEIGHT = 1920

# The frame border is ~3.2% thick. In-game the frame extends outward from
# the art edge, so the art fills only the inner opening of the frame.
# We inset the art slightly less than the full border width so it tucks
# behind the frame edge with no visible gap.
FRAME_BORDER_FRAC = 0.032  # actual frame border thickness
ART_INSET_FRAC = 0.018     # art inset (smaller than border to overlap behind frame)

# Layout positions (matching umaguide CSS percentages)
TYPE_ICON_SIZE = round(WIDTH * 0.25)  # top-right, 25% width
RARITY_LEFT = round(WIDTH * 0.05)
RARITY_WIDTH = round(WIDTH * 0.30)
CORNER_RADIUS_FRAC = 0.12  # border-radius: 12%

# Rarity mapping: DB value → display string
RARITY_MAP = {1: "R", 2: "SR", 3: "SSR"}

# command_id → type icon name (matches filenames in static/overlay/type/)
COMMAND_TYPE_MAP = {
    101: "speed",
    102: "power",
    103: "guts",
    105: "stamina",
    106: "wit",
}

# support_card_type overrides (2=friend/pal, 3=group)
SUPPORT_TYPE_OVERRIDE = {
    2: "pal",
    3: "group",
}


def _load_card_metadata(master_db: Path | None = None) -> dict[int, dict]:
    """Load support card rarity and type from master.mdb.

    Returns {card_id: {"rarity": "SSR", "type_icon": "speed"}}.
    """
    if master_db is None:
        master_db = APP_DIR / "master.mdb"
    if not master_db.is_file():
        log.warning("master.mdb not found at %s", master_db)
        return {}

    conn = sqlite3.connect(str(master_db))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, rarity, command_id, support_card_type FROM support_card_data"
    ).fetchall()
    conn.close()

    meta = {}
    for row in rows:
        card_id = row["id"]
        rarity_str = RARITY_MAP.get(row["rarity"], "R")
        sc_type = row["support_card_type"]

        if sc_type in SUPPORT_TYPE_OVERRIDE:
            type_icon = SUPPORT_TYPE_OVERRIDE[sc_type]
        else:
            type_icon = COMMAND_TYPE_MAP.get(row["command_id"], "speed")

        meta[card_id] = {"rarity": rarity_str, "type_icon": type_icon}

    return meta


def _make_rounded_mask(width: int, height: int, radius: int) -> Image.Image:
    """Create a rounded rectangle alpha mask."""
    mask = Image.new("L", (width, height), 0)
    # Use a simple approach: draw a rounded rect via ellipse corners
    from PIL import ImageDraw

    draw = ImageDraw.Draw(mask)
    # Draw the inner rect and corner circles
    draw.rounded_rectangle([0, 0, width - 1, height - 1], radius=radius, fill=255)
    return mask


def composite_single_card(
    art_path: Path,
    card_id: int,
    rarity: str,
    type_icon_name: str,
    output_path: Path,
    *,
    include_frame: bool = True,
) -> Path | None:
    """Composite a single support card. Returns output path on success.

    Args:
        include_frame: If True, overlay the rarity frame on the art.
            Set to False for thumbnail images that already have the frame baked in.
    """
    if Image is None:
        log.error("Pillow is required for composition")
        return None

    # Load card art
    try:
        art = Image.open(art_path).convert("RGBA")
    except Exception as e:
        log.warning("Failed to open %s: %s", art_path, e)
        return None

    canvas = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))

    if include_frame:
        # Art is inset so the frame border wraps around it (extends outward).
        # Use a slightly smaller inset than the full border so art tucks
        # behind the frame edge — no gaps.
        border_x = round(WIDTH * ART_INSET_FRAC)
        border_y = round(HEIGHT * ART_INSET_FRAC)
        art_w = WIDTH - 2 * border_x
        art_h = HEIGHT - 2 * border_y
        art = art.resize((art_w, art_h), Image.LANCZOS)

        # Rounded corners on the inset art
        radius = round(art_w * CORNER_RADIUS_FRAC)
        mask = _make_rounded_mask(art_w, art_h, radius)
        canvas.paste(art, (border_x, border_y), mask)

        # Overlay frame at full canvas size
        frame_path = FRAME_DIR / f"{rarity}frame.webp"
        if frame_path.is_file():
            frame = Image.open(frame_path).convert("RGBA")
            frame = frame.resize((WIDTH, HEIGHT), Image.LANCZOS)
            canvas = Image.alpha_composite(canvas, frame)
        else:
            log.debug("Frame not found: %s", frame_path)
    else:
        # Thumb already has frame — just resize to canvas with rounded corners
        art = art.resize((WIDTH, HEIGHT), Image.LANCZOS)
        radius = round(WIDTH * CORNER_RADIUS_FRAC)
        mask = _make_rounded_mask(WIDTH, HEIGHT, radius)
        canvas.paste(art, (0, 0), mask)

    # Load and overlay type icon (top-right)
    type_path = TYPE_ICON_DIR / f"{type_icon_name}.png"
    if type_path.is_file():
        type_icon = Image.open(type_path).convert("RGBA")
        type_icon = type_icon.resize((TYPE_ICON_SIZE, TYPE_ICON_SIZE), Image.LANCZOS)
        # Paste at top-right
        icon_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        icon_layer.paste(type_icon, (WIDTH - TYPE_ICON_SIZE, 0))
        canvas = Image.alpha_composite(canvas, icon_layer)
    else:
        log.debug("Type icon not found: %s", type_path)

    # Load and overlay rarity badge (top-left area)
    rarity_path = RARITY_DIR / f"{rarity}.webp"
    if rarity_path.is_file():
        rarity_img = Image.open(rarity_path).convert("RGBA")
        # Scale to RARITY_WIDTH, preserving aspect ratio
        rw, rh = rarity_img.size
        target_h = round(RARITY_WIDTH * (rh / rw))
        rarity_img = rarity_img.resize((RARITY_WIDTH, target_h), Image.LANCZOS)
        rarity_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        rarity_layer.paste(rarity_img, (RARITY_LEFT, 0))
        canvas = Image.alpha_composite(canvas, rarity_layer)
    else:
        log.debug("Rarity badge not found: %s", rarity_path)

    # Save as webp
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(str(output_path), "WEBP", quality=90)
    return output_path


def composite_support_cards(
    input_dir: Path,
    output_dir: Path,
    card_ids: list[int] | None = None,
    master_db: Path | None = None,
    progress_callback=None,
) -> dict[int, str]:
    """Composite all support card images in input_dir.

    Discovers both tex_support_card_{id} (raw art, needs frame) and
    support_thumb_{id} (already has frame, just needs badges) files.
    Produces a composited webp for each.

    Returns {card_id: output_filename} for successfully composited cards.
    """
    if Image is None:
        log.error("Pillow is required. Install with: pip install Pillow")
        return {}

    metadata = _load_card_metadata(master_db)
    if not metadata:
        log.error("No card metadata available — cannot determine rarity/type")
        return {}

    # Discover input files: (card_id, path, needs_frame)
    tex_pattern = re.compile(r"tex_support_card_(\d+)\.(webp|png)$")
    thumb_pattern = re.compile(r"support_thumb_(\d+)\.(webp|png)$")
    # support_card_{id} (without tex_ prefix, not _s_) is also a thumbnail with frame
    card_thumb_pattern = re.compile(r"support_card_(\d+)\.(webp|png)$")

    # tex files: raw art, need frame + badges
    work: list[tuple[int, Path, bool]] = []
    seen_ids: set[int] = set()

    for f in input_dir.iterdir():
        m = tex_pattern.match(f.name)
        if m:
            cid = int(m.group(1))
            if card_ids is None or cid in card_ids:
                work.append((cid, f, True))  # needs frame
                seen_ids.add(cid)

    # thumb files: already have frame, just need rarity + type badges
    for f in input_dir.iterdir():
        m = thumb_pattern.match(f.name)
        if not m:
            m = card_thumb_pattern.match(f.name)
        if m:
            cid = int(m.group(1))
            if (card_ids is None or cid in card_ids) and cid not in seen_ids:
                work.append((cid, f, False))  # no frame needed
                seen_ids.add(cid)

    total = len(work)
    log.info("Found %d support card images to composite (%d tex, %d thumb)",
             total,
             sum(1 for _, _, nf in work if nf),
             sum(1 for _, _, nf in work if not nf))

    output_dir.mkdir(parents=True, exist_ok=True)
    results: dict[int, str] = {}
    processed = 0

    for cid, art_path, needs_frame in sorted(work):
        meta = metadata.get(cid)
        if not meta:
            log.warning("No metadata for card %d in master.mdb, skipping", cid)
            processed += 1
            continue

        out_file = output_dir / f"support_card_{cid}.webp"
        result = composite_single_card(
            art_path, cid, meta["rarity"], meta["type_icon"], out_file,
            include_frame=needs_frame,
        )
        if result:
            results[cid] = result.name

        processed += 1
        if progress_callback and processed % 10 == 0:
            progress_callback(processed, total, len(results))

    if progress_callback:
        progress_callback(total, total, len(results))

    log.info("Composited %d / %d support cards", len(results), total)
    return results


def main():
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(
        description="Composite support card images with frame, rarity, and type overlays."
    )
    parser.add_argument(
        "--input",
        default=None,
        help="Input directory with raw card textures (default: static/cards/)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output directory for composites (default: static/cards/composite/)",
    )
    parser.add_argument("--ids", nargs="*", type=int, help="Only composite these card IDs")
    parser.add_argument("--master-db", default=None, help="Path to master.mdb")
    args = parser.parse_args()

    input_dir = Path(args.input) if args.input else APP_DIR / "static" / "cards"
    output_dir = Path(args.output) if args.output else APP_DIR / "static" / "cards" / "composite"
    master_db = Path(args.master_db) if args.master_db else None

    if not input_dir.is_dir():
        log.error("Input directory not found: %s", input_dir)
        return

    def _progress(done, total, found):
        print(f"\r  {done}/{total} processed, {found} composited", end="", flush=True)

    results = composite_support_cards(
        input_dir, output_dir, card_ids=args.ids, master_db=master_db,
        progress_callback=_progress,
    )
    print(f"\n\nDone: {len(results)} composited cards in {output_dir}")


if __name__ == "__main__":
    main()
