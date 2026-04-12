#!/usr/bin/env python3
"""One-shot diagnostic: dump the typetree structure of story timeline MonoBehaviours."""

import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import UnityPy

from extract_story_text import detect_game_dir, read_meta_entries

AB_KEY = bytes([0x53, 0x2B, 0x46, 0x31, 0xE4, 0xA7, 0xB9, 0x47, 0x3E, 0x7C, 0xFB])


def derive_bundle_key(entry_key):
    key_bytes = struct.pack("<q", entry_key)
    result = bytearray(len(AB_KEY) * 8)
    for i, b in enumerate(AB_KEY):
        for j in range(8):
            result[i * 8 + j] = b ^ key_bytes[j]
    return bytes(result)


def decrypt_bundle(file_path, entry_key):
    data = bytearray(file_path.read_bytes())
    if len(data) <= 256:
        return bytes(data)
    key = derive_bundle_key(entry_key)
    kl = len(key)
    for i in range(256, len(data)):
        data[i] ^= key[i % kl]
    return bytes(data)


def truncate(obj, depth=0, max_list=3):
    """Recursively truncate large structures for readable output."""
    if depth > 6:
        return "..."
    if isinstance(obj, dict):
        return {k: truncate(v, depth + 1, max_list) for k, v in list(obj.items())[:30]}
    if isinstance(obj, list):
        shown = [truncate(v, depth + 1, max_list) for v in obj[:max_list]]
        if len(obj) > max_list:
            shown.append(f"... ({len(obj)} items total)")
        return shown
    if isinstance(obj, bytes):
        return f"<bytes len={len(obj)}>"
    return obj


# ── Load first story bundle from meta ──

game_dir = detect_game_dir()
if not game_dir:
    print("ERROR: Can't find game dir. Pass it as arg or set config.json")
    sys.exit(1)

print(f"Game dir: {game_dir}")
entries = read_meta_entries(game_dir)
if not entries:
    print("ERROR: No story entries found in meta")
    sys.exit(1)

print(f"Found {len(entries)} story entries")
dat_dir = game_dir / "dat"

# Try a few bundles to find one with a BlockList MonoBehaviour
for idx, entry in enumerate(entries[:20]):
    h = entry["hash"]
    fp = dat_dir / h[:2] / h
    if not fp.is_file():
        continue

    print(f"\n{'=' * 60}")
    print(f"Bundle #{idx}: {fp.name}  entry_name={entry['name']}  key={entry['key']}")
    data = decrypt_bundle(fp, entry["key"]) if entry["key"] != 0 else fp.read_bytes()
    env = UnityPy.load(data)

    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            tree = obj.read_typetree()
        except Exception as e:
            print(f"  typetree error: {e}")
            continue
        if not isinstance(tree, dict):
            continue
        if "BlockList" not in tree:
            continue

        # Found one! Dump its structure
        print(f"\n  TOP-LEVEL KEYS: {list(tree.keys())}")
        print(
            f"  StoryId={tree.get('StoryId', '?')}  Title={tree.get('Title', '?')}  m_Name={tree.get('m_Name', '?')}"
        )

        bl = tree["BlockList"]
        print(f"\n  BlockList: {len(bl)} blocks")
        if bl:
            # Dump first block's full keys
            b0 = bl[0]
            print(f"  Block[0] type={type(b0).__name__}")
            if isinstance(b0, dict):
                print(f"  Block[0] KEYS: {list(b0.keys())}")
                # Show any key containing 'choice' or 'Choice'
                for k, v in b0.items():
                    if "choice" in k.lower() or "select" in k.lower():
                        print(f"  Block[0]['{k}'] = {truncate(v)}")
                # Dump full first block structure (truncated)
                print("\n  Block[0] FULL (truncated):")
                print(json.dumps(truncate(b0), indent=4, ensure_ascii=False, default=str))

            # Search ALL blocks for any with non-empty choice-like fields
            for bi, block in enumerate(bl):
                if not isinstance(block, dict):
                    continue
                for k, v in block.items():
                    if (
                        ("choice" in k.lower() or "select" in k.lower())
                        and v
                        and isinstance(v, list)
                        and len(v) > 0
                    ):
                        print(f"\n  Block[{bi}]['{k}'] has {len(v)} items!")
                        print(f"    First item: {truncate(v[0])}")
                        if isinstance(v[0], dict):
                            print(f"    First item KEYS: {list(v[0].keys())}")

        print("\n  Done with this bundle.")
        # Only need one MonoBehaviour per bundle
        break
    else:
        continue
    # Stop after first successful bundle dump
    if idx >= 5:
        break

print("\nDiagnostic complete.")
