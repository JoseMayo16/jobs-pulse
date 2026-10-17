import json
from pathlib import Path

from jobs_pulse.sources import arbeitnow, hn, remoteok, remotive

FIXTURES = Path(__file__).parent / "fixtures"


def load(name):
    return json.loads((FIXTURES / name).read_text())


def test_remotive_keeps_only_dev_jobs():
    jobs = remotive.parse(load("remotive.json"))
    assert [j.source_id for j in jobs] == ["101", "103"]
    backend = jobs[0]
    assert backend.company == "Acme Labs"
    assert backend.posted_at == "2026-10-08"
    assert backend.url.startswith("https://remotive.com/")
    assert {"Python", "Django", "PostgreSQL", "AWS"} <= set(backend.skills)
    assert {"Vue", "TypeScript", "Tailwind"} <= set(jobs[1].skills)


def test_remoteok_skips_legal_notice_and_zero_salaries():
    jobs = remoteok.parse(load("remoteok.json"))
    assert [j.source_id for j in jobs] == ["201", "203"]
    go = jobs[0]
    assert (go.salary_min, go.salary_max) == (90000, 130000)
    assert set(go.skills) == {"Go", "Docker"}  # the "kubernetes" tag is ignored
    assert jobs[1].salary_min is None


def test_arbeitnow_keeps_only_remote_jobs():
    jobs = arbeitnow.parse(load("arbeitnow.json"))
    assert len(jobs) == 1
    assert jobs[0].source_id == "laravel-dev-berlin-1"
    assert jobs[0].posted_at == "2026-10-11"
    assert {"PHP", "Laravel", "MySQL"} <= set(jobs[0].skills)


def test_hn_finds_only_who_is_hiring_threads():
    assert hn.parse_threads(load("hn_search.json")) == {
        "2026-10": "49922569",
        "2026-09": "49522897",
    }


def test_hn_summary_counts_top_level_posts_only():
    summary = hn.summarize(load("hn_item.json"))
    assert summary["posts"] == 3  # the deleted post and the nested reply are ignored
    assert summary["remote"] == 2
    assert summary["skills"]["Python"] == 1
    assert summary["skills"]["Go"] == 1  # "Go to our site" does not count twice
    assert "Java" not in summary["skills"]
