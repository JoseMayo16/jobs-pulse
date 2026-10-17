"""Technology dictionary and the matcher that tags each listing.

Each skill has a canonical name, a category and one or more regex patterns.
Patterns are case-insensitive unless the skill sets `case=True` (needed for
short, ambiguous words such as "Go").
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Skill:
    name: str
    category: str
    patterns: tuple[str, ...]
    case: bool = False


SKILLS: tuple[Skill, ...] = (
    # languages
    Skill("Python", "language", (r"\bpython\b",)),
    Skill("JavaScript", "language", (r"\bjavascript\b", r"\bes6\b")),
    Skill("TypeScript", "language", (r"\btypescript\b",)),
    Skill("Java", "language", (r"\bjava\b(?!\s*script)",)),
    # "Go" is a common English word, so only count it inside a list of technologies.
    Skill("Go", "language", (r"\b[Gg]olang\b", r"[,/|(]\s*Go\b", r"\bGo\s*[,/|)]"), case=True),
    Skill("Rust", "language", (r"\brust\b",)),
    Skill("Ruby", "language", (r"\bruby\b",)),
    Skill("PHP", "language", (r"\bphp\b",)),
    Skill("C#", "language", (r"(?<![\w#])c#", r"\.net\b", r"\bdotnet\b")),
    Skill("C++", "language", (r"(?<![\w+])c\+\+",)),
    Skill("Kotlin", "language", (r"\bkotlin\b",)),
    Skill("Swift", "language", (r"\bswift\b",)),
    Skill("Elixir", "language", (r"\belixir\b",)),
    Skill("Scala", "language", (r"\bscala\b",)),
    # frontend
    Skill("React", "frontend", (r"\breact(?:\.?js)?\b(?!\s*native)",)),
    Skill("React Native", "frontend", (r"\breact\s*native\b",)),
    Skill("Vue", "frontend", (r"\bvue(?:\.?js)?\b", r"\bnuxt\b")),
    Skill("Angular", "frontend", (r"\bangular\b",)),
    Skill("Svelte", "frontend", (r"\bsvelte(?:kit)?\b",)),
    Skill("Next.js", "frontend", (r"\bnext\.?js\b",)),
    Skill("Tailwind", "frontend", (r"\btailwind\b",)),
    # backend
    Skill("Node.js", "backend", (r"\bnode(?:\.?js)?\b",)),
    Skill("Django", "backend", (r"\bdjango\b",)),
    Skill("FastAPI", "backend", (r"\bfastapi\b",)),
    Skill("Flask", "backend", (r"\bflask\b",)),
    Skill("Rails", "backend", (r"\brails\b",)),
    Skill("Laravel", "backend", (r"\blaravel\b",)),
    Skill("Spring", "backend", (r"\bspring\s*(?:boot|framework)\b",)),
    Skill("GraphQL", "backend", (r"\bgraphql\b",)),
    # data
    Skill("PostgreSQL", "data", (r"\bpostgres(?:ql)?\b",)),
    Skill("MySQL", "data", (r"\bmysql\b",)),
    Skill("MongoDB", "data", (r"\bmongo(?:db)?\b",)),
    Skill("Redis", "data", (r"\bredis\b",)),
    Skill("Kafka", "data", (r"\bkafka\b",)),
    Skill("Spark", "data", (r"\bspark\b",)),
    Skill("Snowflake", "data", (r"\bsnowflake\b",)),
    Skill("dbt", "data", (r"\bdbt\b",)),
    # cloud and devops
    Skill("AWS", "cloud", (r"\baws\b", r"\bamazon web services\b")),
    Skill("GCP", "cloud", (r"\bgcp\b", r"\bgoogle cloud\b")),
    Skill("Azure", "cloud", (r"\bazure\b",)),
    Skill("Docker", "cloud", (r"\bdocker\b",)),
    Skill("Kubernetes", "cloud", (r"\bkubernetes\b", r"\bk8s\b")),
    Skill("Terraform", "cloud", (r"\bterraform\b",)),
    # AI
    Skill(
        "LLMs",
        "ai",
        (r"\bllms?\b", r"\blarge language models?\b", r"\bgenai\b", r"\bgenerative ai\b"),
    ),
    Skill("PyTorch", "ai", (r"\bpytorch\b",)),
    Skill("Machine Learning", "ai", (r"\bmachine learning\b", r"\bml\b")),
)

CATEGORIES = {s.name: s.category for s in SKILLS}

_COMPILED = tuple(
    (s.name, tuple(re.compile(p, 0 if s.case else re.IGNORECASE) for p in s.patterns))
    for s in SKILLS
)

_TAGS = re.compile(r"<[^>]+>")


def clean_text(raw: str) -> str:
    """HTML to plain text, good enough for keyword matching."""
    return html.unescape(_TAGS.sub(" ", raw or ""))


def extract(*texts: str) -> list[str]:
    """Return the canonical names of every skill mentioned in the given texts."""
    blob = " \n ".join(clean_text(t) for t in texts if t)
    return [name for name, regexes in _COMPILED if any(r.search(blob) for r in regexes)]
