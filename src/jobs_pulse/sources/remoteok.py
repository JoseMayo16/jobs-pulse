"""Remote OK public API. Their terms: link back to the job URL and mention Remote OK as the
source; do not use their logo. The first element of the response is that legal notice."""

from __future__ import annotations

from ..models import Listing
from ..skills import extract

NAME = "remoteok"
LABEL = "Remote OK"
HOME = "https://remoteok.com"
URL = "https://remoteok.com/api"


def fetch(client):
    return client.get_json(URL)


def _salary(value) -> int | None:
    try:
        value = int(value)
    except (TypeError, ValueError):
        return None
    return value or None


def parse(raw: list) -> list[Listing]:
    out = []
    for job in raw:
        if "id" not in job or "position" not in job:
            continue  # legal notice
        # Their tags are attached generously (a clinical data manager tagged "dev",
        # "sys admin", "testing"), so skills come from the title and description only.
        skills = extract(job["position"], job.get("description", ""))
        if not skills:
            continue
        out.append(
            Listing(
                source=NAME,
                source_id=str(job["id"]),
                title=job["position"].strip(),
                company=(job.get("company") or "").strip(),
                url=job["url"],
                posted_at=(job.get("date") or "")[:10],
                skills=skills,
                location=job.get("location") or "",
                salary_min=_salary(job.get("salary_min")),
                salary_max=_salary(job.get("salary_max")),
            )
        )
    return out
