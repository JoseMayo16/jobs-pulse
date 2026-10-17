"""Common shape every source is normalized into."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field


def slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


@dataclass
class Listing:
    source: str
    source_id: str
    title: str
    company: str
    url: str
    posted_at: str  # ISO date, YYYY-MM-DD
    skills: list[str]
    location: str = ""
    salary_min: int | None = None
    salary_max: int | None = None
    first_seen: str = ""
    last_seen: str = ""
    also_on: list[str] = field(default_factory=list)

    @property
    def key(self) -> str:
        return f"{self.source}:{self.source_id}"

    @property
    def fingerprint(self) -> str:
        """Same company + same title = same job, even when posted on two boards."""
        return f"{slug(self.company)}|{slug(self.title)}"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Listing:
        return cls(**data)
