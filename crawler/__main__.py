"""
Uma Musume friend graph crawler.

Usage:
  python -m crawler                    # single worker, auto-create account
  python -m crawler --workers 5        # 5 parallel workers, shared DB
  python -m crawler --stats            # print DB stats and exit
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import threading
import time
from pathlib import Path


def _load_dotenv() -> None:
    for candidate in [
        Path(__file__).parent.parent / ".env",
        Path("/data/.env"),
    ]:
        if candidate.exists():
            for line in candidate.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
            break


_load_dotenv()

DEFAULT_ACCOUNTS_DIR = Path(__file__).parent.parent / "crawler_accounts"
DEFAULT_DB = Path(__file__).parent.parent / "crawler.db"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(threadName)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("crawler")


def _inject_steam_creds(cfg: dict) -> dict:
    """Fill steam_username / steam_password from env if not already in config."""
    if not cfg.get("steam_username"):
        cfg["steam_username"] = os.environ.get("STEAM_USERNAME", "")
    if not cfg.get("steam_password"):
        cfg["steam_password"] = os.environ.get("STEAM_PASSWORD", "")
    return cfg


def _make_client(cfg_path: Path) -> "UmaClient":
    from .client import UmaClient

    if cfg_path.exists():
        log.info("Loading account from %s", cfg_path.name)
        import json
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
        return UmaClient(_inject_steam_creds(cfg))

    log.info("Creating new guest account → %s", cfg_path.name)
    client = UmaClient(_inject_steam_creds({}))
    try:
        client.signup()
    except RuntimeError as exc:
        if "APP-VER" in str(exc):
            log.error("%s", exc)
            log.error("Run: python get_versions.py  (with game open), then retry.")
            sys.exit(1)
        raise
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    client.save_config(cfg_path)
    log.info("Account created: viewer_id=%s", client.viewer_id)
    return client


def _worker(worker_id: int, cfg_path: Path, db_path: Path, interval: float, batch_size: int) -> None:
    from .client import UmaClient
    from .store import Store
    from .crawl import run_loop

    threading.current_thread().name = f"w{worker_id}"

    client = _make_client(cfg_path)

    log.info("Logging in as viewer_id=%s", client.viewer_id)
    client.login()
    log.info("Login OK")

    # Stagger workers so they don't all hammer recommend at the same time
    time.sleep(worker_id * 1.5)

    store = Store(db_path)
    try:
        run_loop(client, store, batch_size=batch_size, call_interval=interval)
    finally:
        store.close()


def cmd_stats(args: argparse.Namespace) -> None:
    from .store import Store
    store = Store(args.db)
    stats = store.queue_stats()
    print(f"Players indexed : {store.player_count()}")
    print(f"Queue pending   : {stats.get('pending', 0)}")
    print(f"Queue done      : {stats.get('done', 0)}")
    print(f"Queue error     : {stats.get('error', 0)}")
    store.close()


def cmd_run(args: argparse.Namespace) -> None:
    accounts_dir = Path(args.accounts_dir)
    db_path = Path(args.db)
    n = args.workers

    if n == 1:
        cfg_path = accounts_dir / "account_0.json"
        _worker(0, cfg_path, db_path, args.interval, args.batch_size)
        return

    threads = []
    for i in range(n):
        cfg_path = accounts_dir / f"account_{i}.json"
        t = threading.Thread(
            target=_worker,
            args=(i, cfg_path, db_path, args.interval, args.batch_size),
            daemon=True,
        )
        threads.append(t)

    log.info("Starting %d workers...", n)
    for t in threads:
        t.start()

    try:
        while any(t.is_alive() for t in threads):
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Interrupted — waiting for workers to finish current call...")
        for t in threads:
            t.join(timeout=5)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Uma Musume friend graph crawler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of parallel crawler accounts (default: 1)",
    )
    parser.add_argument(
        "--accounts-dir",
        default=str(DEFAULT_ACCOUNTS_DIR),
        help=f"Directory for per-worker account configs (default: {DEFAULT_ACCOUNTS_DIR})",
    )
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB),
        help=f"Path to SQLite database (default: {DEFAULT_DB})",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Print DB stats and exit",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Queue batch size per worker (default: 50)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.6,
        help="Minimum seconds between API calls per worker (default: 0.6)",
    )

    args = parser.parse_args()

    if args.stats:
        cmd_stats(args)
        return

    cmd_run(args)


if __name__ == "__main__":
    main()
