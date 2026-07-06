"""Ingestion: pull crash records from the NYC Open Data Socrata API.

Handles paging, retries with exponential backoff, and local parquet caching so
repeat runs don't re-download the whole dataset.
"""

from __future__ import annotations

import logging
import time

import pandas as pd
import requests

from crashlens import config

logger = logging.getLogger(__name__)

PAGE_SIZE = 50_000
MAX_RETRIES = 4


def _fetch_page(offset: int, page_size: int, session: requests.Session) -> list[dict]:
    """Fetch one page from the Socrata API with retry + backoff."""
    params = {
        "$select": ",".join(config.SOCRATA_COLUMNS),
        "$where": f"crash_date >= '{config.MIN_CRASH_DATE}'",
        "$order": "collision_id",
        "$limit": page_size,
        "$offset": offset,
    }
    for attempt in range(MAX_RETRIES):
        try:
            resp = session.get(config.SOCRATA_URL, params=params, timeout=60)
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as exc:
            if attempt == MAX_RETRIES - 1:
                raise
            wait = 2**attempt
            logger.warning("Fetch failed (%s), retrying in %ss", exc, wait)
            time.sleep(wait)
    return []  # unreachable, keeps type checkers happy


def fetch_crashes(max_rows: int | None = None, use_cache: bool = True) -> pd.DataFrame:
    """Download crash records, paging through the API.

    Args:
        max_rows: stop after roughly this many rows (None = everything).
        use_cache: if the raw parquet cache exists, load it instead of hitting the API.
    """
    if use_cache and config.RAW_PARQUET.exists():
        logger.info("Loading cached raw data from %s", config.RAW_PARQUET)
        df = pd.read_parquet(config.RAW_PARQUET)
        return df.head(max_rows) if max_rows else df

    frames: list[pd.DataFrame] = []
    offset = 0
    session = requests.Session()

    while True:
        page_size = PAGE_SIZE if max_rows is None else min(PAGE_SIZE, max_rows - offset)
        if page_size <= 0:
            break
        rows = _fetch_page(offset, page_size, session)
        if not rows:
            break
        frames.append(pd.DataFrame(rows))
        logger.info("Fetched %s rows (offset %s)", len(rows), offset)
        offset += len(rows)
        if len(rows) < page_size:
            break

    if not frames:
        raise RuntimeError("API returned no rows — check the endpoint or filters.")

    df = pd.concat(frames, ignore_index=True)

    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(config.RAW_PARQUET, index=False)
    logger.info("Cached %s raw rows to %s", len(df), config.RAW_PARQUET)
    return df
