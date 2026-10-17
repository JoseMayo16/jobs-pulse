"""Turn the stored listings and HN monthly counts into the single JSON the dashboard reads.

Board numbers are computed with SQL over an in-memory SQLite copy of the listings.
"""

from __future__ import annotations

import sqlite3
import statistics
from datetime import UTC, date, datetime, timedelta

from .models import Listing
from .skills import CATEGORIES

BOARD_WINDOW_DAYS = 30
HN_MONTHS = 24
LATEST_LIMIT = 80
MIN_SALARY_SAMPLES = 5


def _load_db(listings: dict[str, Listing]) -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    db.executescript("""
        CREATE TABLE listing (
            key TEXT PRIMARY KEY, source TEXT, title TEXT, company TEXT, url TEXT,
            location TEXT, posted_at TEXT, first_seen TEXT, last_seen TEXT,
            salary_min INTEGER, salary_max INTEGER
        );
        CREATE TABLE listing_skill (key TEXT, skill TEXT, PRIMARY KEY (key, skill));
    """)
    db.executemany(
        "INSERT INTO listing VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [
            (
                x.key,
                x.source,
                x.title,
                x.company,
                x.url,
                x.location,
                x.posted_at,
                x.first_seen,
                x.last_seen,
                x.salary_min,
                x.salary_max,
            )
            for x in listings.values()
        ],
    )
    db.executemany(
        "INSERT INTO listing_skill VALUES (?,?)",
        [(x.key, s) for x in listings.values() for s in x.skills],
    )
    return db


def boards_summary(listings: dict[str, Listing], today: date) -> dict:
    db = _load_db(listings)
    since = (today - timedelta(days=BOARD_WINDOW_DAYS)).isoformat()

    total = db.execute("SELECT COUNT(*) FROM listing WHERE last_seen >= ?", (since,)).fetchone()[0]
    rows = db.execute(
        """
        SELECT s.skill, COUNT(*) AS n
        FROM listing_skill s JOIN listing l USING (key)
        WHERE l.last_seen >= ?
        GROUP BY s.skill ORDER BY n DESC, s.skill
    """,
        (since,),
    ).fetchall()
    skills = [
        {
            "name": name,
            "category": CATEGORIES.get(name, "other"),
            "count": n,
            "share": round(n / total, 4) if total else 0,
        }
        for name, n in rows
    ]

    salary_rows = db.execute(
        """
        SELECT s.skill, l.salary_min, l.salary_max
        FROM listing_skill s JOIN listing l USING (key)
        WHERE l.last_seen >= ? AND (l.salary_min IS NOT NULL OR l.salary_max IS NOT NULL)
    """,
        (since,),
    ).fetchall()
    by_skill: dict[str, list[float]] = {}
    for name, low, high in salary_rows:
        values = [v for v in (low, high) if v]
        by_skill.setdefault(name, []).append(sum(values) / len(values))
    salary = sorted(
        (
            {"name": k, "median": round(statistics.median(v)), "samples": len(v)}
            for k, v in by_skill.items()
            if len(v) >= MIN_SALARY_SAMPLES
        ),
        key=lambda r: -r["median"],
    )

    latest_since = (today - timedelta(days=1)).isoformat()
    latest = [
        {
            "title": x.title,
            "company": x.company,
            "url": x.url,
            "source": x.source,
            "posted_at": x.posted_at,
            "location": x.location,
            "skills": x.skills,
        }
        for x in sorted(
            (x for x in listings.values() if x.last_seen >= latest_since),
            key=lambda x: (x.posted_at, x.key),
            reverse=True,
        )[:LATEST_LIMIT]
    ]

    per_source = dict(
        db.execute(
            "SELECT source, COUNT(*) FROM listing WHERE last_seen >= ? GROUP BY source", (since,)
        ).fetchall()
    )
    db.close()
    return {
        "window_days": BOARD_WINDOW_DAYS,
        "total": total,
        "skills": skills,
        "salary": salary,
        "latest": latest,
        "per_source": per_source,
    }


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def hn_summary(months: dict[str, dict], current_month: str = "") -> dict:
    keys = sorted(k for k, v in months.items() if v.get("posts"))[-HN_MONTHS:]
    if not keys:
        return {"months": [], "posts": [], "remote_share": [], "skills": {}, "movers": None}

    names = sorted({s for k in keys for s in months[k]["skills"]})
    share = {
        name: [round(months[k]["skills"].get(name, 0) / months[k]["posts"], 4) for k in keys]
        for name in names
    }

    # Last 3 complete months against the same 3 months one year earlier, when the history
    # reaches. The month in progress is left out: its thread is still filling up.
    movers = None
    end = len(keys) - 1 if keys[-1] == current_month else len(keys)
    if end >= 15:
        now_idx, before_idx = range(end - 3, end), range(end - 15, end - 12)
        rows = []
        for name in names:
            now = _avg([share[name][i] for i in now_idx])
            before = _avg([share[name][i] for i in before_idx])
            if max(now, before) >= 0.02:
                rows.append(
                    {
                        "name": name,
                        "now": round(now, 4),
                        "before": round(before, 4),
                        "delta": round(now - before, 4),
                    }
                )
        rows.sort(key=lambda r: r["delta"], reverse=True)
        movers = {
            "now": [keys[i] for i in now_idx],
            "before": [keys[i] for i in before_idx],
            "rising": [r for r in rows if r["delta"] > 0][:8],
            "falling": sorted((r for r in rows if r["delta"] < 0), key=lambda r: r["delta"])[:8],
        }

    return {
        "months": keys,
        "posts": [months[k]["posts"] for k in keys],
        "remote_share": [round(months[k]["remote"] / months[k]["posts"], 4) for k in keys],
        "skills": share,
        "movers": movers,
    }


def build(
    listings: dict[str, Listing], hn_months: dict[str, dict], sources: list[dict], today: date
) -> dict:
    return {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "today": today.isoformat(),
        "sources": sources,
        "categories": CATEGORIES,
        "boards": boards_summary(listings, today),
        "hn": hn_summary(hn_months, today.strftime("%Y-%m")),
    }
