"""
BFS crawler over the Uma Musume friend graph.

Discovery strategy:
  1. Seed from friend/renew_recommend_list (server gives us viewer_ids for free)
  2. For each viewer_id in the queue, call friend/search to get their profile
  3. Any new viewer_ids found in responses get enqueued

Profile data extracted per player:
  - borrow support card (id, level, limit_break)
  - profile trained chara (chara_id, card_id, rank)
  - display name
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .client import UmaClient
    from .store import Store

log = logging.getLogger("crawler.crawl")

# Minimum delay between API calls (seconds)
MIN_CALL_INTERVAL = 0.5


def _extract_player(viewer_id: int, user_info: dict, card_data: dict | None = None) -> dict:
    """Parse a summary_user_info dict into our normalised player record."""
    sc_id = user_info.get("support_card_id")
    sc = card_data or {}

    # Some responses nest the card under user_support_card
    if not sc:
        sc = user_info.get("user_support_card") or {}

    trained = user_info.get("trained_chara_info") or {}

    return {
        "viewer_id": viewer_id,
        "display_name": user_info.get("name") or user_info.get("trainer_name"),
        "borrow_card_id": sc_id,
        "borrow_card_level": sc.get("level"),
        "borrow_card_limit_break": sc.get("limit_break_count"),
        "profile_chara_id": trained.get("chara_id"),
        "profile_card_id": trained.get("card_id"),
        "profile_rank": user_info.get("rank") or user_info.get("trainer_rank"),
        "raw_json": user_info,
    }


def _new_ids_from_response(data: dict) -> list[int]:
    """Pull any viewer_ids out of a response data dict."""
    ids: list[int] = []
    for key in ("summary_user_info_array", "friend_info_array"):
        for info in data.get(key) or []:
            vid = info.get("viewer_id")
            if vid:
                ids.append(int(vid))
    single = data.get("summary_user_info") or data.get("friend_info")
    if isinstance(single, dict):
        vid = single.get("viewer_id")
        if vid:
            ids.append(int(vid))
    return ids


def seed_from_recommend(client: "UmaClient", store: "Store", exclude: list[int] | None = None) -> int:
    """
    Call friend/renew_recommend_list and enqueue returned viewer_ids.
    Returns count of newly enqueued ids.
    """
    try:
        res = client.friend_recommend(exclude=exclude)
    except Exception as exc:
        log.warning("recommend failed: %s", exc)
        return 0

    data = res.get("data", {})
    ids = _new_ids_from_response(data)

    # Also check friend_support_card_data
    fsc = data.get("friend_support_card_data") or {}
    for info in fsc.get("summary_user_info_array") or []:
        vid = info.get("viewer_id")
        if vid:
            ids.append(int(vid))

    added = store.enqueue(ids, source="recommend")
    log.info("recommend: found %d ids, %d newly enqueued", len(ids), added)
    return added


def seed_from_pre_single_mode(client: "UmaClient", store: "Store") -> int:
    """
    Call pre_single_mode/index and process borrow card list directly,
    also enqueueing any viewer_ids found.
    """
    try:
        res = client.pre_single_mode()
    except Exception as exc:
        log.warning("pre_single_mode failed: %s", exc)
        return 0

    data = res.get("data", {})
    fsc = data.get("friend_support_card_data") or {}
    summaries = fsc.get("summary_user_info_array") or []
    card_array = fsc.get("support_card_data_array") or []

    card_by_key: dict[tuple, dict] = {}
    for sc in card_array:
        key = (sc.get("viewer_id"), sc.get("support_card_id"))
        card_by_key[key] = sc

    ids: list[int] = []
    for info in summaries:
        vid = info.get("viewer_id")
        sc_id = info.get("support_card_id")
        if not vid:
            continue
        vid = int(vid)
        ids.append(vid)
        card = card_by_key.get((vid, sc_id)) or {}
        player = _extract_player(vid, info, card)
        store.upsert_player(player)

    added = store.enqueue(ids, source="pre_single_mode")
    log.info("pre_single_mode: processed %d players, %d newly enqueued", len(summaries), added)
    return added


def process_one(client: "UmaClient", store: "Store", viewer_id: int) -> bool:
    """
    Fetch a player's profile via friend/search and store it.
    Returns True on success.
    """
    try:
        res = client.friend_search(viewer_id)
    except Exception as exc:
        log.warning("friend/search %d failed: %s", viewer_id, exc)
        store.mark_error(viewer_id)
        return False

    data = res.get("data", {})

    # Parse the profile
    user_info = data.get("summary_user_info")
    if not user_info and data.get("summary_user_info_array"):
        user_info = data["summary_user_info_array"][0]

    if user_info:
        card_array = data.get("support_card_data_array") or []
        sc_id = user_info.get("support_card_id")
        card = next(
            (c for c in card_array if c.get("support_card_id") == sc_id), {}
        )
        player = _extract_player(viewer_id, user_info, card)
        store.upsert_player(player)

    # Enqueue any new viewer_ids discovered in this response
    new_ids = _new_ids_from_response(data)
    if new_ids:
        newly = store.enqueue(
            [i for i in new_ids if not store.already_queued(i)],
            source=f"friend_of:{viewer_id}",
        )
        if newly:
            log.debug("  discovered %d new ids from viewer %d", newly, viewer_id)

    store.mark_done(viewer_id)
    return True


def run_loop(
    client: "UmaClient",
    store: "Store",
    *,
    batch_size: int = 50,
    call_interval: float = MIN_CALL_INTERVAL,
    reseed_every: int = 500,
) -> None:
    """
    Main crawl loop. Runs until interrupted.

    Seeds from recommend list, then processes queue in batches.
    Re-seeds every `reseed_every` processed players.
    """
    processed = 0

    log.info("Starting crawl loop")
    seed_from_pre_single_mode(client, store)
    seed_from_recommend(client, store)

    while True:
        stats = store.queue_stats()
        log.info(
            "Queue: pending=%d done=%d error=%d | players=%d",
            stats.get("pending", 0),
            stats.get("done", 0),
            stats.get("error", 0),
            store.player_count(),
        )

        batch = store.next_pending(batch_size)
        if not batch:
            log.info("Queue empty — re-seeding from recommend list...")
            added = seed_from_recommend(client, store)
            if not added:
                log.info("Recommend returned no new ids. Sleeping 60s...")
                time.sleep(60)
            continue

        for vid in batch:
            t0 = time.monotonic()
            process_one(client, store, vid)
            processed += 1

            elapsed = time.monotonic() - t0
            wait = max(0.0, call_interval - elapsed)
            if wait:
                time.sleep(wait)

            if processed % reseed_every == 0:
                log.info("Processed %d players — re-seeding...", processed)
                seed_from_recommend(client, store)
