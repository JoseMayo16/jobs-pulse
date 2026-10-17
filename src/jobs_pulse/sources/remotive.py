"""Remotive public API. Their terms: link back to each job and name Remotive as the source,
and call the API at most 4 times a day. https://remotive.com/api-documentation"""

from __future__ import annotations

from ..models import Listing
from ..skills import extract

NAME = "remotive"
LABEL = "Remotive"
HOME = "https://remotive.com"
URL = "https://remotive.com/api/remote-jobs"


def fetch(client):
    return client.get_json(URL)


def parse(raw: dict) -> list[Listing]:
    out = []
    for job in raw.get("jobs", []):
        skills = extract(
            job.get("title", ""), " ".join(job.get("tags") or []), job.get("description", "")
        )
        if not skills:
            continue
        out.append(
            Listing(
                source=NAME,
                source_id=str(job["id"]),
                title=job["title"].strip(),
                company=job.get("company_name", "").strip(),
                url=job["url"],
                posted_at=(job.get("publication_date") or "")[:10],
                skills=skills,
                location=job.get("candidate_required_location") or "",
            )
        )
    return out
