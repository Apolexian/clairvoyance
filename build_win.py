"""
Build script — packages Clairvoyance into a standalone Windows distribution.

Usage (run on Windows with PyInstaller installed):
  python build_win.py

Produces:
  dist/Clairvoyance/
    Clairvoyance.exe      ← main GUI (double-click this)
    collect.exe            ← data collector (launched by GUI)
    discover.exe           ← binary scanner (launched by GUI)
    analyse.exe            ← analysis tool (launched by GUI)
    sessions/              ← created at runtime
    discovery/             ← created at runtime
    _internal/             ← PyInstaller shared runtime

Prerequisites:
  pip install pyinstaller flask pywebview frida frida-tools msgpack
  pip install UnityPy          # optional — enables event choice text extraction
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
DIST = HERE / "dist" / "Clairvoyance"
BUILD = HERE / "build"
ICON_PNG = HERE / "static" / "main_small_icon.png"
ICON_ICO = BUILD / "clairvoyance.ico"

# PyInstaller flags shared across all builds
COMMON = [
    "--noconfirm",
    "--clean",
    f"--distpath={DIST}",
    f"--workpath={BUILD}",
    f"--specpath={BUILD}",
    # Collect frida's native agent binaries
    "--collect-all=frida",
    "--hidden-import=frida",
    "--hidden-import=msgpack",
    "--hidden-import=flask",
    "--hidden-import=engineio",
]


def run(cmd: list[str], label: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"  > {' '.join(cmd)}")
    print(f"{'=' * 60}\n")
    result = subprocess.run(
        cmd, cwd=str(HERE), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    print(result.stdout)  # print PyInstaller output live
    if result.returncode != 0:
        print(f"\n  FAILED: {label} (exit {result.returncode})")
        sys.exit(1)
    print(f"  OK: {label} done.")


def build_gui():
    """Build the main Clairvoyance GUI as a windowed app."""
    extra_imports = [
        # extract_story_text is imported at runtime inside a try/except,
        # so PyInstaller's static analysis won't find it automatically.
        "--hidden-import=extract_story_text",
    ]

    # If UnityPy is installed, bundle it so story extraction works in the frozen build
    try:
        import UnityPy  # noqa: F401

        extra_imports += [
            "--collect-all=UnityPy",
            "--hidden-import=UnityPy",
        ]
        print("  UnityPy detected — will be bundled for story extraction")
    except ImportError:
        print("  UnityPy not installed — story extraction will not be available in build")

    run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            *COMMON,
            "--name=Clairvoyance",
            "--windowed",  # no console window
            f"--icon={ICON_ICO}",
            # Bundle data files
            f"--add-data={HERE / 'templates'};templates",
            f"--add-data={HERE / 'static'};static",
            f"--add-data={HERE / 'js'};js",
            # Hidden imports for pywebview
            "--hidden-import=webview",
            "--hidden-import=clr_loader",
            "--hidden-import=pythonnet",
            # Ensure local modules are discoverable
            f"--paths={HERE}",
            *extra_imports,
            "gui.py",
        ],
        "Building Clairvoyance.exe (GUI)",
    )


def build_tool(script: str, name: str):
    add_data = []
    js_path = HERE / "js"
    if name in ("collect", "discover"):
        add_data = [f"--add-data={js_path};js"]

    run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            *COMMON,
            f"--name={name}",
            "--console",
            *add_data,
            script,
        ],
        f"Building {name}.exe",
    )


def post_build():
    """Move all .exe files to the top-level dist folder so they're siblings."""
    # PyInstaller --onedir puts each build into a <name>/ subdirectory under
    # the distpath, so after all four builds we have:
    #
    #   dist/Clairvoyance/Clairvoyance/Clairvoyance.exe   + _internal/
    #   dist/Clairvoyance/collect/collect.exe              + _internal/
    #   dist/Clairvoyance/discover/discover.exe            + _internal/
    #   dist/Clairvoyance/analyse/analyse.exe              + _internal/
    #
    # We want everything flat at dist/Clairvoyance/ sharing one _internal/.

    # ── Step 1: Hoist the GUI exe + _internal out of its nested subdir ──
    gui_subdir = DIST / "Clairvoyance"
    if gui_subdir.is_dir():
        gui_exe = gui_subdir / "Clairvoyance.exe"
        gui_internal = gui_subdir / "_internal"
        if gui_exe.exists():
            print(f"  Moving {gui_exe} -> {DIST / 'Clairvoyance.exe'}")
            shutil.move(str(gui_exe), str(DIST / "Clairvoyance.exe"))
        if gui_internal.is_dir():
            print(f"  Moving {gui_internal} -> {DIST / '_internal'}")
            shutil.move(str(gui_internal), str(DIST / "_internal"))
        shutil.rmtree(str(gui_subdir), ignore_errors=True)

    # ── Step 2: Hoist each tool exe and merge its _internal ─────────────
    for tool in ("collect", "discover", "analyse"):
        tool_dir = DIST / tool
        if tool_dir.is_dir():
            exe = tool_dir / f"{tool}.exe"
            if exe.exists():
                dest = DIST / f"{tool}.exe"
                print(f"  Moving {exe} -> {dest}")
                shutil.move(str(exe), str(dest))
            # Merge any unique files from tool's _internal into main _internal
            tool_internal = tool_dir / "_internal"
            main_internal = DIST / "_internal"
            if tool_internal.is_dir() and main_internal.is_dir():
                for f in tool_internal.rglob("*"):
                    if f.is_file():
                        rel = f.relative_to(tool_internal)
                        target = main_internal / rel
                        if not target.exists():
                            target.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(str(f), str(target))
            # Clean up the tool subdirectory
            shutil.rmtree(str(tool_dir), ignore_errors=True)

    # ── Step 3: Create placeholder directories ──────────────────────────
    (DIST / "sessions").mkdir(exist_ok=True)
    (DIST / "discovery").mkdir(exist_ok=True)

    # ── Verify final layout ─────────────────────────────────────────────
    expected = ["Clairvoyance.exe", "collect.exe", "discover.exe", "analyse.exe", "_internal"]
    missing = [name for name in expected if not (DIST / name).exists()]
    if missing:
        print(f"\n  WARNING: Missing in output: {missing}")
    else:
        print(f"\n  All executables verified in {DIST}")

    print(f"\n{'=' * 60}")
    print("  Build complete!")
    print(f"  Output: {DIST}")
    print("  Ship as: Clairvoyance.zip")
    print(f"{'=' * 60}")


def generate_icon():
    """Convert main_small_icon.png to multi-size .ico for the Windows executable."""
    BUILD.mkdir(parents=True, exist_ok=True)
    img = Image.open(ICON_PNG).convert("RGBA")
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(str(ICON_ICO), format="ICO", sizes=sizes)
    print(f"  Generated icon: {ICON_ICO}")


def main():
    # Generate .ico from PNG
    generate_icon()

    # Clean previous build
    if DIST.exists():
        print(f"Removing previous build: {DIST}")
        shutil.rmtree(str(DIST))

    # Build everything
    build_gui()
    build_tool("collect.py", "collect")
    build_tool("discover.py", "discover")
    build_tool("analyse.py", "analyse")
    post_build()


if __name__ == "__main__":
    main()
