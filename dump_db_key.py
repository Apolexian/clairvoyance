#!/usr/bin/env python3
"""
Attach to running Uma Musume and capture the sqlite3_key call to extract
the current meta DB decryption key.

Usage:
  1. Launch the game
  2. Run: python3 dump_db_key.py
  3. Key bytes will be printed when the game opens the meta DB
"""
import sys
import time
import json
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent

def main():
    try:
        import frida
    except ImportError:
        print("ERROR: frida not installed. Run: pip install frida")
        sys.exit(1)

    script_path = APP_DIR / "js" / "dump_db_key.js"
    script_src = script_path.read_text(encoding="utf-8")

    print("[*] Looking for Uma Musume process...")
    device = frida.get_local_device()

    target_pid = None
    for proc in device.enumerate_processes():
        name = (proc.name or "").lower()
        if "uma" in name or "derby" in name:
            print(f"[*] Found process: {proc.name} (pid={proc.pid})")
            target_pid = proc.pid
            break

    if target_pid is None:
        print("ERROR: Uma Musume process not found. Launch the game first.")
        sys.exit(1)

    print(f"[*] Attaching to pid {target_pid}...")
    session = device.attach(target_pid)

    script = session.create_script(script_src)

    def on_message(message, data):
        mtype = message.get("type", "")
        if mtype == "send":
            payload = message.get("payload", {})
            if payload.get("type") == "db_key":
                key_hex = payload["key"]
                n_key = payload["nKey"]
                method = payload.get("method", "unknown")
                print(f"\n{'='*60}")
                print(f"[KEY CAPTURED] {method}")
                print(f"  nKey  = {n_key}")
                print(f"  hex   = {key_hex}")
                print(f"  bytes = [{', '.join(f'0x{key_hex[i:i+2].upper()}' for i in range(0, len(key_hex), 2))}]")
                print(f"{'='*60}\n")
        elif mtype == "error":
            print(f"[ERROR] {message.get('description', message)}")
        elif mtype == "log":
            print(message.get("payload", ""))

    script.on("message", on_message)
    script.load()

    print("[*] Hooks installed. Waiting for key (Ctrl+C to stop)...")
    print("[*] Tip: If the game is already running and meta is already open,")
    print("    you may need to restart the game.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Detaching...")
        session.detach()

if __name__ == "__main__":
    main()
