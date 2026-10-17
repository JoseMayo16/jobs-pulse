"""Command line entry point. Run it from the repository root.

jobs-pulse run                 fetch boards + HN, merge, write the dashboard data
jobs-pulse run --offline       rebuild the dashboard data from what is stored
jobs-pulse hn --months 24      (re)fetch HN history; also done by `run` for missing months
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from . import aggregate, store
from .http import PoliteClient
from .sources import BOARDS, hn

# Data lives in the repository the command runs from: CI checks it out and runs
# `jobs-pulse run` at its root. Deriving it from __file__ would point inside
# site-packages once the package is installed, and the run would start empty.
LISTINGS = Path("data") / "listings.jsonl"
HN_MONTHS = Path("data") / "hn_months.json"
SUMMARY = Path("site") / "data" / "summary.json"

log = logging.getLogger("jobs_pulse")


def update_boards(client, listings, today) -> list[str]:
    failed = []
    for board in BOARDS:
        try:
            fresh = board.parse(board.fetch(client))
        except Exception as exc:  # one broken board must not stop the others
            log.error("%s failed: %s", board.NAME, exc)
            failed.append(board.NAME)
            continue
        stats = store.merge(listings, fresh, today)
        log.info(
            "%-10s %3d dev jobs  new=%d seen=%d duplicate=%d",
            board.NAME,
            len(fresh),
            stats["new"],
            stats["seen"],
            stats["duplicate"],
        )
    return failed


def update_hn(client, months: dict, wanted: int, refresh_all: bool = False) -> None:
    threads = hn.find_threads(client)
    recent = sorted(threads, reverse=True)[:wanted]
    current = recent[0] if recent else None
    for month in recent:
        if month in months and month != current and not refresh_all:
            continue
        months[month] = hn.summarize(hn.fetch_thread(client, threads[month]))
        log.info("hn %s  %d posts", month, months[month]["posts"])


def write_summary(listings, months, today) -> None:
    sources = [{"name": b.NAME, "label": b.LABEL, "url": b.HOME} for b in BOARDS]
    sources.append(
        {
            "name": "hn",
            "label": "Hacker News: Who is hiring?",
            "url": "https://news.ycombinator.com/submitted?id=whoishiring",
        }
    )
    store.save_json(SUMMARY, aggregate.build(listings, months, sources, today), indent=None)
    log.info("wrote %s", SUMMARY)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="jobs-pulse")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--offline", action="store_true")
    run.add_argument("--hn-months", type=int, default=aggregate.HN_MONTHS)
    hn_cmd = sub.add_parser("hn")
    hn_cmd.add_argument("--months", type=int, default=aggregate.HN_MONTHS)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    today = datetime.now(UTC).date()
    listings = store.load_listings(LISTINGS)
    months = store.load_json(HN_MONTHS, {})
    failed: list[str] = []

    if args.command == "hn" or not args.offline:
        with PoliteClient() as client:
            if args.command == "run":
                failed = update_boards(client, listings, today)
                dropped = store.prune(listings, today)
                if dropped:
                    log.info("pruned %d listings not seen for %d days", dropped, store.KEEP_DAYS)
                store.save_listings(LISTINGS, listings)
                wanted = args.hn_months
            else:
                wanted = args.months
            try:
                update_hn(client, months, wanted, refresh_all=args.command == "hn")
                store.save_json(HN_MONTHS, months)
            except Exception as exc:
                log.error("hn failed: %s", exc)
                failed.append("hn")

    write_summary(listings, months, today)
    if len(failed) == len(BOARDS) + 1:
        log.error("every source failed")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
