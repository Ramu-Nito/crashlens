"""Pipeline entrypoint: ingest -> clean -> validate -> load warehouse.

Usage:
    python -m crashlens.pipeline               # full dataset (cached after first run)
    python -m crashlens.pipeline --limit 50000 # smaller pull for quick testing
    python -m crashlens.pipeline --refresh     # ignore cache, re-download
"""

from __future__ import annotations

import argparse
import logging
import sys

from crashlens import ingest, transform, validate

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("crashlens.pipeline")


def run(max_rows: int | None = None, use_cache: bool = True) -> int:
    logger.info("Step 1/4: ingest")
    raw = ingest.fetch_crashes(max_rows=max_rows, use_cache=use_cache)
    logger.info("Raw rows: %s", len(raw))

    logger.info("Step 2/4: clean")
    cleaned = transform.clean(raw)
    logger.info("Clean rows: %s (dropped %s)", len(cleaned), len(raw) - len(cleaned))

    logger.info("Step 3/4: validate")
    validated = validate.validate(cleaned)

    logger.info("Step 4/4: load warehouse")
    transform.load_warehouse(validated)
    logger.info("Pipeline complete.")
    return len(validated)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the crashlens data pipeline.")
    parser.add_argument("--limit", type=int, default=None, help="max rows to ingest")
    parser.add_argument("--refresh", action="store_true", help="ignore the raw cache")
    args = parser.parse_args()
    try:
        run(max_rows=args.limit, use_cache=not args.refresh)
    except Exception:
        logger.exception("Pipeline failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
