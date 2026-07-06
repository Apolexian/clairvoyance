#!/usr/bin/env python3
"""
Login to JP Uma Musume via Steam and fetch home timeline asset bundles.

Steps:
1. Get Steam session ticket for JP app (1522030)
2. Login / signup to get viewer_id + auth_key
3. Call home story endpoints to get bundle URLs or raw data
4. Save bundles to jp_home_bundles/

Usage:
    python fetch_jp_home_convos.py --username apoljp --password <pw>
"""
import argparse
import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "crawler"))

import crawler.client as _crawler_client
_crawler_client.BASE_URL = "https://api.games.umamusume.jp/umamusume/"
from crawler.client import UmaClient, build_profile, get_steam_ticket

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

JP_STEAM_APP_ID = 3564400
ACCOUNT_FILE = Path(__file__).parent / "crawler_accounts" / "jp_account.json"
OUT_DIR = Path(__file__).parent / "jp_home_bundles"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--username", required=True)
    ap.add_argument("--password", required=True)
    ap.add_argument("--code", default="")
    args = ap.parse_args()

    OUT_DIR.mkdir(exist_ok=True)

    # Load or create account
    if ACCOUNT_FILE.exists():
        cfg = json.loads(ACCOUNT_FILE.read_text())
        log.info("Loaded existing JP account (viewer_id=%s)", cfg.get("viewer_id"))
    else:
        log.info("No JP account found — will create new one after login")
        cfg = {}

    cfg["steam_username"] = args.username
    cfg["steam_password"] = args.password
    cfg["locale"] = "JPN"
    # Use global versions as starting point — server will 205 if wrong and client retries
    if not cfg.get("app_ver") or not cfg.get("res_ver"):
        global_versions = Path(__file__).parent / "versions.json"
        if global_versions.exists():
            v = json.loads(global_versions.read_text())
            cfg.setdefault("app_ver", v.get("app_ver", "1.22.1"))
            cfg.setdefault("res_ver", v.get("res_ver", "10006400"))
            log.info("Using versions app_ver=%s res_ver=%s", cfg["app_ver"], cfg["res_ver"])

    # Get Steam ticket for JP app
    log.info("Getting Steam ticket for JP app %d...", JP_STEAM_APP_ID)
    import subprocess, shutil
    _node_dir = Path(__file__).parent / "crawler"
    _ticket_js = _node_dir / "_ticket_gen.js"
    cmd = ["node", str(_ticket_js), "--username", args.username, "--password", args.password, "--appid", str(JP_STEAM_APP_ID)]
    if args.code:
        cmd += ["--code", args.code]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=str(_node_dir))
    if proc.returncode != 0:
        log.error("Steam ticket failed: %s", proc.stderr.strip())
        sys.exit(1)
    ticket_data = json.loads(proc.stdout.strip().split("\n")[-1])
    steam_id = ticket_data["steam_id"]
    ticket = ticket_data["session_ticket"]
    log.info("Steam ID: %s", steam_id)
    cfg["steam_id"] = steam_id
    cfg["steam_session_ticket"] = ticket

    client = UmaClient(cfg)
    client.steam_id = steam_id
    client.steam_ticket = ticket

    # Login
    log.info("Logging in...")
    if not client.auth_key_hex:
        client.signup()
        log.info("Signed up — viewer_id=%s", client.viewer_id)
    client._regen_sid()
    client.call("tool/start_session", {"attestation_type": 0, "device_token": None})
    resp = client.call("load/index", {"adid": ""})
    log.info("Logged in — viewer_id=%s", client.viewer_id)

    # Save account
    ACCOUNT_FILE.parent.mkdir(exist_ok=True)
    ACCOUNT_FILE.write_text(json.dumps(client.to_config(), indent=2))
    log.info("Saved account to %s", ACCOUNT_FILE)

    # Probe home story endpoints
    log.info("Probing home story endpoints...")

    # Try home/story or home_story endpoints
    endpoints_to_try = [
        ("home/story", {}),
        ("home/story/index", {}),
        ("home_story/index", {}),
        ("story/index", {"story_type": 1}),
        ("home/index", {}),
    ]

    for ep, payload in endpoints_to_try:
        try:
            log.info("Trying endpoint: %s", ep)
            r = client.call(ep, payload)
            log.info("Response keys: %s", list(r.get("data", r).keys()) if isinstance(r.get("data", r), dict) else type(r))
            out = OUT_DIR / f"response_{ep.replace('/', '_')}.json"
            out.write_text(json.dumps(r, indent=2, ensure_ascii=False))
            log.info("Saved to %s", out)
        except Exception as e:
            log.info("  -> %s: %s", ep, e)
        time.sleep(0.5)


if __name__ == "__main__":
    main()
