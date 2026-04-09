# Clairvoyance

Passive background data collector for Uma Musume Pretty Derby.

Hooks into the running game via Frida and silently captures skill activations,
event text, proc chances, race results, and other game data — then organises
everything into structured session logs for guide writers to reference later.

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Uma Musume running (Windows/Steam or Linux)

## Quick Start

```bash
# Phase 1 — Discover what the game exposes
uv run discover.py                # broad class scan → discovery/class_dump.json
uv run discover.py --trace        # live-trace: log method calls during gameplay

# Phase 2 — Collect data while playing
uv run collect.py                 # start background collector
uv run collect.py --dashboard     # with live TUI status
```

## How It Works

### Phase 1: Discovery (`discover.py`)

Scans every class in `GameAssembly.dll` / `libil2cpp.so` for keywords across
all guide-relevant domains (skills, events, races, training, story, etc.) and
dumps the full class layouts (methods + fields + offsets) to JSON.

The `--trace` flag hooks key entry points and logs which methods fire during
gameplay, sorted by call frequency — this tells you exactly what to target.

### Phase 2: Collection (`collect.py`)

Attaches targeted hooks to the methods discovered in Phase 1 and silently
records every interesting event to per-session JSONL files:

```
sessions/
  2026-04-09T12-00-00/
    manifest.json       # session metadata, game version, character
    skills.jsonl        # skill activations + lottery/proc results
    events.jsonl        # training/story events + choices
    races.jsonl         # race results + conditions
    raw.jsonl           # anything else interesting
```

## Project Structure

```
clairvoyance/
  discover.py           # Phase 1: broad class scanner + live tracer
  collect.py            # Phase 2: background data collector
  js/
    il2cpp_helpers.js   # shared il2cpp reflection engine
    discover_scan.js    # broad keyword scan across all assemblies
    discover_trace.js   # live-trace hooks for method call logging
    hook_skills.js      # skill activation + lottery hooks
    hook_events.js      # event/story hooks
    hook_races.js       # race result hooks
  lib/
    attach.py           # process finder + Frida attach logic
    session.py          # session directory + JSONL writer
  discovery/            # output from Phase 1 scans
  sessions/             # output from Phase 2 collection
```

