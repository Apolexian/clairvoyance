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
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIST = HERE / "dist" / "Clairvoyance"
BUILD = HERE / "build"

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
    result = subprocess.run(cmd, cwd=str(HERE))
    if result.returncode != 0:
        print(f"\n  ✗ {label} failed (exit {result.returncode})")
        sys.exit(1)
    print(f"  ✓ {label} done.")


def build_gui():
    """Build the main Clairvoyance GUI as a windowed app."""
    run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            *COMMON,
            "--name=Clairvoyance",
            "--windowed",  # no console window
            "--icon=NONE",  # TODO: add icon later
            # Bundle data files
            f"--add-data=templates{os.pathsep}templates",
            f"--add-data=static{os.pathsep}static",
            f"--add-data=js{os.pathsep}js",
            # Hidden imports for pywebview
            "--hidden-import=webview",
            "--hidden-import=clr_loader",
            "--hidden-import=pythonnet",
            "gui.py",
        ],
        "Building Clairvoyance.exe (GUI)",
    )


def build_tool(script: str, name: str):
    """Build a subprocess tool as a console app."""
    add_data = []
    # collect.py needs the js/ directory for Frida scripts
    if name == "collect":
        add_data = [f"--add-data=js{os.pathsep}js"]
    # discover.py needs the js/ directory too
    if name == "discover":
        add_data = [f"--add-data=js{os.pathsep}js"]

    run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            *COMMON,
            f"--name={name}",
            "--console",  # needs stdout for log streaming
            *add_data,
            script,
        ],
        f"Building {name}.exe",
    )


def post_build():
    """Move tool .exe files up into the main dist folder so they're siblings."""
    # PyInstaller puts each build into dist/Clairvoyance/<name>/
    # but with --distpath=dist/Clairvoyance they end up as:
    #   dist/Clairvoyance/Clairvoyance.exe  (onedir contents)
    #   dist/Clairvoyance/collect/collect.exe
    #   dist/Clairvoyance/discover/discover.exe
    #   dist/Clairvoyance/analyse/analyse.exe
    #
    # We want all .exe files at the top level sharing _internal/.
    # The simplest approach: build the GUI first (it creates _internal/),
    # then for each tool, just move the .exe up.

    for tool in ("collect", "discover", "analyse"):
        tool_dir = DIST / tool
        if tool_dir.is_dir():
            exe = tool_dir / f"{tool}.exe"
            if exe.exists():
                dest = DIST / f"{tool}.exe"
                print(f"  Moving {exe} → {dest}")
                shutil.move(str(exe), str(dest))
            # Move any unique DLLs from tool's _internal to main _internal
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

    # Create placeholder directories
    (DIST / "sessions").mkdir(exist_ok=True)
    (DIST / "discovery").mkdir(exist_ok=True)

    print(f"\n{'=' * 60}")
    print("  ✓ Build complete!")
    print(f"  Output: {DIST}")
    print("  Ship as: Clairvoyance.zip")
    print(f"{'=' * 60}")


def main():
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
