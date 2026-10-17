"""Arbeitnow public API. Their terms: do not abuse it and link back to Arbeitnow.
Most of their listings are on-site jobs in Germany, so only `remote: true` ones are kept."""

from __future__ import annotations

from datetime import UTC, datetime

from ..models import Listing
from ..skills import extract

NAME = "arbeitnow"
LABEL = "Arbeitnow"
HOME = "https://www.arbeitnow.com"
URL = "https://www.arbeitnow.com/api/job-board-api"
PAGES = 3


def fetch(client):
    jobs = []
    for page in range(1, PAGES + 1):
        data = client.get_json(URL, params={"page": page})
        jobs.extend(data.get("data", []))
        if not (data.get("links") or {}).get("next"):
            break
    return {"data": jobs}


def parse(raw: dict) -> list[Listing]:
    out = []
    for job in raw.get("data", []):
        if not job.get("remote"):
            continue
        skills = extract(
            job.get("title", ""), " ".join(job.get("tags") or []), job.get("description", "")
        )
        if not skills:
            continue
        posted = datetime.fromtimestamp(int(job["created_at"]), UTC).date().isoformat()
        out.append(
            Listing(
                source=NAME,
                source_id=job["slug"],
                title=job["title"].strip(),
                company=(job.get("company_name") or "").strip(),
                url=job["url"],
                posted_at=posted,
                skills=skills,
                location=job.get("location") or "",
            )
        )
    return out
