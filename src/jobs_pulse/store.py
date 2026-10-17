"""Persistence. The repo itself is the database: listings live in a JSON Lines file sorted
by key, so each daily commit shows exactly which jobs appeared or disappeared."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from .models import Listing

KEEP_DAYS = 120


def load_listings(path: Path) -> dict[str, Listing]:
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            listing = Listing.from_dict(json.loads(line))
            out[listing.key] = listing
    return out


def save_listings(path: Path, listings: dict[str, Listing]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(listings[k].to_dict(), ensure_ascii=False, sort_keys=True)
        for k in sorted(listings)
    ]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def merge(existing: dict[str, Listing], fresh: list[Listing], today: date) -> dict[str, int]:
    """Fold a fetch into the store, in place. Returns counts for the run log.

    - Already known (same source + id): refresh it and bump `last_seen`.
    - Same company and title already stored from another board: it is a duplicate,
      so the other board is recorded in `also_on` instead of adding a second row.
    - Anything else is new.
    """
    stamp = today.isoformat()
    by_fingerprint = {item.fingerprint: item for item in existing.values()}
    stats = {"new": 0, "seen": 0, "duplicate": 0}

    for item in fresh:
        known = existing.get(item.key)
        if known:
            known.title, known.skills, known.url = item.title, item.skills, item.url
            known.last_seen = stamp
            stats["seen"] += 1
            continue
        twin = by_fingerprint.get(item.fingerprint)
        if twin and twin.source != item.source:
            if item.source not in twin.also_on:
                twin.also_on.append(item.source)
            twin.last_seen = stamp
            stats["duplicate"] += 1
            continue
        item.first_seen = item.last_seen = stamp
        existing[item.key] = item
        by_fingerprint[item.fingerprint] = item
        stats["new"] += 1
    return stats


def prune(listings: dict[str, Listing], today: date, keep_days: int = KEEP_DAYS) -> int:
    cutoff = (today - timedelta(days=keep_days)).isoformat()
    stale = [k for k, v in listings.items() if v.last_seen < cutoff]
    for k in stale:
        del listings[k]
    return len(stale)


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data, indent: int | None = 1) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=indent, sort_keys=True)
    path.write_text(text + "\n", encoding="utf-8")
