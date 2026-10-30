"""Scan the Ariston technical menu for available operating parameters.

The ``menuItems`` endpoint can answer HTTP 500 for a whole request because
of one id the device does not know. The scanner requests ids in batches and
falls back to single ids for rejected batches. Requests fail fast (no
retries), run at most a few at a time, and the total number of requests and
the run time are capped, so the scan stays polite to the cloud.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
import time
from typing import Any

_LOGGER = logging.getLogger(__name__)

DEFAULT_FIRST_ID = 1
DEFAULT_LAST_ID = 500
INITIAL_BATCH_SIZE = 25
MAX_REQUESTS = 650
MAX_SECONDS = 600
REQUEST_PAUSE_SECONDS = 0.2
CONCURRENCY = 3


async def async_scan_menu_items(
    api: Any,
    gw_id: str,
    first_id: int = DEFAULT_FIRST_ID,
    last_id: int = DEFAULT_LAST_ID,
    *,
    max_requests: int = MAX_REQUESTS,
    max_seconds: float = MAX_SECONDS,
    pause_seconds: float = REQUEST_PAUSE_SECONDS,
    concurrency: int = CONCURRENCY,
) -> dict[str, Any]:
    """Return every menu item the cloud reports for ids in the given range.

    Each batch is requested at once; when the cloud rejects it, every id of
    that batch is requested on its own. Valid ids are usually sparse, so
    probing singles is cheaper than bisecting (at most one request per id).
    """
    started = time.monotonic()
    found: dict[Any, dict[str, Any]] = {}
    rejected: list[int] = []
    not_scanned: list[int] = []
    requests = 0
    semaphore = asyncio.Semaphore(max(1, concurrency))

    def budget_left() -> bool:
        return requests < max_requests and time.monotonic() - started <= max_seconds

    async def request(ids: list[int]) -> bool:
        """Request ids; return False when the cloud rejects the request."""
        nonlocal requests
        async with semaphore:
            if not budget_left():
                not_scanned.extend(ids)
                return True
            requests += 1
            try:
                items = await api.async_get_menu_items_by_ids(gw_id, ids)
            except Exception as err:  # noqa: BLE001 - a rejection is expected
                _LOGGER.debug("Menu items %s-%s rejected: %s", ids[0], ids[-1], err)
                return False
            finally:
                await asyncio.sleep(pause_seconds)
        for item in items or []:
            if isinstance(item, dict) and item.get("id") is not None:
                found[item["id"]] = item
        return True

    async def scan_single(item_id: int) -> None:
        if not await request([item_id]):
            rejected.append(item_id)

    async def scan_batch(ids: list[int]) -> None:
        if await request(ids):
            return
        await asyncio.gather(*(scan_single(item_id) for item_id in ids))

    batches = [
        list(range(start, min(start + INITIAL_BATCH_SIZE - 1, last_id) + 1))
        for start in range(first_id, last_id + 1, INITIAL_BATCH_SIZE)
    ]
    for batch in batches:
        await scan_batch(batch)

    items = [found[key] for key in sorted(found, key=lambda k: (str(type(k)), k))]
    return {
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "scanned_ids": f"{first_id}-{last_id}",
        "requests": requests,
        "duration_seconds": round(time.monotonic() - started, 1),
        "complete": not not_scanned,
        "items_found": len(items),
        "items": items,
        "rejected_ids": sorted(rejected),
        "not_scanned_ids": sorted(not_scanned),
    }
