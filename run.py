# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "frida",
# ]
# ///

"""
Clairvoyance — All-in-one runner for the test machine.

Runs the full pipeline:
  1. Discover (--all) → discovery/class_dump.json
  2. Analyse           → discovery/analysis.md + interesting.json
  3. Dump              → sessions/<ts>/  (field snapshots while you play)

Usage:
  uv run run.py                # full pipeline
  uv run run.py --skip-discover  # reuse existing class_dump.json
  uv run run.py --step discover  # only run discovery
  uv run run.py --step analyse   # only run analysis
  uv run run.py --step dump      # only run dump collector
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DISCOVERY_DIR = os.path.join(SCRIPT_DIR, "discovery")
CLASS_DUMP = os.path.join(DISCOVERY_DIR, "class_dump.json")
INTERESTING = os.path.join(DISCOVERY_DIR, "interesting.json")

PYTHON = sys.executable  # use the same Python that's running this script


def run(cmd: list[str], label: str) -> bool:
    """Run a command, print its output live, return True on success."""
    print()
    print("=" * 60)
    print(f"  {label}")
    print("=" * 60)
    print(f"  > {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, cwd=SCRIPT_DIR)

    if result.returncode != 0:
        print(f"\n  [X] {label} failed (exit code {result.returncode})")
        return False

    print(f"\n  [OK] {label} complete.")
    return True


def step_discover() -> bool:
    return run(
        [PYTHON, "discover.py", "--all"],
        "Phase 1: Discovery (scanning game binary)",
    )


def step_analyse() -> bool:
    if not os.path.exists(CLASS_DUMP):
        print(f"\n  [X] {CLASS_DUMP} not found. Run discovery first.")
        return False

    return run(
        [PYTHON, "analyse.py"],
        "Phase 2: Analysis (scoring classes)",
    )


def step_dump() -> bool:
    if not os.path.exists(INTERESTING):
        print(f"\n  [X] {INTERESTING} not found. Run analysis first.")
        return False

    return run(
        [PYTHON, "collect.py", "--modules", "dump", "network", "--label", "run"],
        "Phase 3: Dump (capturing game state — play the game, Ctrl+C to stop)",
    )


def main():
    parser = argparse.ArgumentParser(description="Clairvoyance all-in-one runner")
    parser.add_argument(
        "--step",
        choices=["discover", "analyse", "dump"],
        help="Run only a specific step",
    )
    parser.add_argument(
        "--skip-discover",
        action="store_true",
        help="Skip discovery if class_dump.json already exists",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  Clairvoyance — All-in-one Runner")
    print("=" * 60)

    # Single step mode
    if args.step:
        ok = {"discover": step_discover, "analyse": step_analyse, "dump": step_dump}[args.step]()
        sys.exit(0 if ok else 1)

    # Full pipeline
    if args.skip_discover and os.path.exists(CLASS_DUMP):
        print("\n  Skipping discovery (--skip-discover, class_dump.json exists)")
    else:
        if not step_discover():
            sys.exit(1)

    if not step_analyse():
        sys.exit(1)

    if not step_dump():
        sys.exit(1)

    print()
    print("=" * 60)
    print("  All done.")
    print("=" * 60)


if __name__ == "__main__":
    main()
