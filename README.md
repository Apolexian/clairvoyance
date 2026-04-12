# Clairvoyance

Passive background data collector for Uma Musume Pretty Derby.

Hooks into the running game via Frida and silently captures skill activations,
event text, proc chances, race results, network traffic, and other game data —
then organises everything into structured session logs for guide writers to
reference later.

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/)
- Uma Musume running (Windows/Steam or Linux)

## Quick Start (test machine, no Make)

```bash
uv run run.py                    # full pipeline: discover → analyse → dump
uv run run.py --skip-discover    # reuse existing class_dump.json
uv run run.py --step discover    # only discovery
uv run run.py --step analyse     # only analysis
uv run run.py --step dump        # only dump collector
uv run gui.py                    # launch native desktop app
```

## Workflow

```
1. Discover  →  2. Analyse  →  3. Collect / Dump
```

### 1. Discover — scan the game binary

```bash
uv run discover.py --all           # full Gallop namespace + keyword + signature scan
uv run discover.py                  # keyword + signature scan only
uv run discover.py --trace          # live-trace: log method call frequency while playing
```

Outputs `discovery/class_dump.json` — every class in the game with methods,
fields, offsets, and types.

### 2. Analyse — score and filter the dump

```bash
make analyse
```

Reads `class_dump.json` and produces:

- **`discovery/analysis.md`** — human-readable report, top classes per domain
- **`discovery/interesting.json`** — filtered/scored JSON for the dump module

### 3. Collect — capture data while playing

```bash
# Targeted hooks (skills, events, races, network)
uv run collect.py

# Data-driven dump — reads field layouts from interesting.json,
# hooks top-scored classes, dumps all field values at runtime
uv run collect.py --modules dump --label my-session
uv run collect.py --modules dump --dump-min-score 40 --dump-max-classes 50

# Combine modules
uv run collect.py --modules dump network skills

# Network capture only
uv run collect.py --modules network
```

Session output:

```
sessions/<timestamp>_<label>/
  manifest.json       # session metadata, modules, hook counts
  skills.jsonl        # skill activations + lottery/proc results
  events.jsonl        # training/story events + choices
  races.jsonl         # race results + conditions
  network.jsonl       # API traffic (SSL, MsgPack, Cute.Http tasks)
  raw.jsonl           # anything else
```

## Makefile

```bash
make fmt              # format Python (ruff) + JS (prettier)
make lint             # lint Python
make check            # CI check — fails if anything is unformatted
make clean            # remove logs + sessions + build artifacts (keeps discovery/)
make nuke             # remove everything including discovery/
make analyse          # run analyse.py on discovery/class_dump.json
make dump             # run collector with dump module
make gui              # launch native desktop GUI
make build-win        # build standalone Windows distribution
make install-hooks    # install pre-commit git hooks
```

## GUI (Native Desktop App)

```bash
uv run gui.py                    # launch native window
uv run gui.py --browser          # fallback: open in browser instead
```

Opens a native OS window (WebKit on macOS, EdgeChromium on Windows) — no
browser required, just double-click to launch.

Features:
- **Setup** — Scan game binary and analyse classes directly from the app
- **Record** — Start/stop data collection sessions from the app
- **Browse sessions** — See all saved sessions with record counts
- **Session timeline** — View network events, filter by API name, see game state changes
- **Race analysis** — Per-horse stats table, finish order, HP usage, pace-down segments
- **Race charts** — Frame-by-frame distance, speed, and HP charts for all runners
- **🏇 Race Replay** — Animated canvas visualization of the race:
  - Horses run across the track in real time with color-coded dots
  - Skill activations pop up above each horse as they fire
  - HP bars under each horse, speed/distance stats in info panel
  - Play/pause, frame step, scrub timeline, speed control (0.25×–8×)
  - Phase boundary zones (opening/mid/final/spurt) shown as background bands
  - Keyboard shortcuts: Space=play, ←→=step, ↑↓=speed, Home/End=jump

## Standalone Windows Build

Ship Clairvoyance as a standalone `.exe` that users can run without installing
Python or uv. Built with PyInstaller.

### Building (on Windows)

```bash
# Install build dependencies
pip install pyinstaller

# Run the build script
python build_win.py
```

### Output

```
dist/Clairvoyance/
  Clairvoyance.exe      ← double-click to launch
  collect.exe            ← data collector (launched by GUI)
  discover.exe           ← binary scanner (launched by GUI)
  analyse.exe            ← class analyser (launched by GUI)
  _internal/             ← shared runtime (Python + deps)
  sessions/              ← created at runtime
  discovery/             ← created at runtime
```

Zip the `dist/Clairvoyance/` folder and distribute. Users extract it,
double-click `Clairvoyance.exe`, and they're running.

## How It Works

### Discovery (`discover.py`)

Scans every class in `GameAssembly.dll` / `libil2cpp.so` using three strategies:

1. **Keyword** — class name contains skill, race, event, training, etc.
2. **Namespace** (`--all`) — every class in the `Gallop` namespace
3. **Signature** — class has methods/fields named Activate, Deserialize, SkillId, etc.

The `--trace` flag hooks entry-point methods and logs call frequency during
gameplay — tells you which classes are actually active vs dead code.

### Analysis (`analyse.py`)

Scores every discovered class by how useful it is for guide writing:

| Signal | Points |
|--------|-------:|
| Has Activate, LotActivate, BeginRace, Deserialize, etc. | +10/method |
| Has SkillId, AbilityType, RaceResult fields | +8/field |
| Is a `*Request`/`*Response`/`*Task` (API pattern) | +15 |
| Is a `*Formatter` (MsgPack serializer) | +10 |
| Is `Master*` (game master data) | +8 |
| Compiler-generated / library noise | -100 |

### Collection (`collect.py`)

Modular hook system — pick what you need:

| Module | What it captures |
|--------|-----------------|
| `skills` | Skill activation, lottery/proc rolls, trigger checks |
| `events` | Training/story events, user choices, view transitions |
| `races` | Race lifecycle, results, jikkyo commentary |
| `network` | SSL read/write, MsgPack formatters, Cute.Http API tasks |
| `dump` | Data-driven: reads all fields from top-scored classes at runtime |

The `dump` module is the most powerful — it uses the field layouts from
`interesting.json` to read actual game state (stats, IDs, aptitudes, etc.)
whenever a hooked method fires.

### Network Capture (3 layers)

1. **SSL_read / SSL_write** — hooks TLS plaintext inside the process (no MITM needed)
2. **MsgPack Formatters** — hooks `Gallop.MsgPack.Formatters.*.Serialize/Deserialize`
3. **Cute.Http base class** — hooks `Send`/`Deserialize`/`OnError` on the HTTP task base class, identifies concrete task by reading the il2cpp class name at runtime

## Project Structure

```
clairvoyance/
  run.py                  # all-in-one: discover → analyse → dump
  discover.py             # Phase 1: class scanner + live tracer
  analyse.py              # Phase 1.5: score and filter class dump
  collect.py              # Phase 2: modular background collector
  Makefile                # fmt, lint, clean, analyse, dump
  pyproject.toml          # dependencies + ruff config
  js/
    il2cpp_helpers.js     # shared il2cpp reflection engine
    discover_scan.js      # keyword + namespace + signature scan
    discover_trace.js     # live-trace hooks for call frequency
    hook_skills.js        # skill activation + lottery hooks
    hook_events.js        # event/story hooks
    hook_races.js         # race lifecycle hooks
    hook_network.js       # SSL + MsgPack + Cute.Http hooks
    hook_dump.js          # data-driven field dumper
  lib/
    __init__.py
    attach.py             # process finder + Frida attach with retry
    session.py            # session directory + JSONL writer
  discovery/              # output from discover.py + analyse.py
  sessions/               # output from collect.py
```

## Logging

Each script writes two log files:

| File | Contents |
|------|----------|
| `discover.log` / `collect.log` | Important events, errors, summaries |
| `discover_js.log` / `collect_js.log` | Verbose Frida JS console output |

Errors appear in both. JS noise stays out of the main log and console.
