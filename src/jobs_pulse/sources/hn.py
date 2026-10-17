"""Hacker News "Ask HN: Who is hiring?" monthly threads, through the public Algolia HN API.

Each top-level comment is one job post. Only aggregate counts per month are kept,
never the text of the posts.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime

from ..skills import clean_text, extract

SEARCH = "https://hn.algolia.com/api/v1/search_by_date"
ITEM = "https://hn.algolia.com/api/v1/items/{id}"
TITLE = re.compile(r"^Ask HN: Who is hiring\? \((\w+ \d{4})\)$")
REMOTE = re.compile(r"\bremote\b", re.IGNORECASE)


def find_threads(client) -> dict[str, str]:
    """Map 'YYYY-MM' to the thread id, newest first."""
    data = client.get_json(
        SEARCH,
        params={
            "tags": "story,author_whoishiring",
            "hitsPerPage": 100,
        },
    )
    return parse_threads(data)


def parse_threads(data: dict) -> dict[str, str]:
    threads = {}
    for hit in data.get("hits", []):
        match = TITLE.match(hit.get("title") or "")
        if match:
            month = datetime.strptime(match.group(1), "%B %Y").strftime("%Y-%m")
            threads[month] = str(hit["objectID"])
    return threads


def fetch_thread(client, thread_id: str) -> dict:
    return client.get_json(ITEM.format(id=thread_id))


def summarize(item: dict) -> dict:
    posts = [c for c in item.get("children", []) if c.get("text")]
    skills: Counter[str] = Counter()
    remote = 0
    for post in posts:
        text = post["text"]
        skills.update(extract(text))
        if REMOTE.search(clean_text(text)):
            remote += 1
    return {
        "thread_id": str(item.get("id", "")),
        "posts": len(posts),
        "remote": remote,
        "skills": dict(sorted(skills.items())),
    }
