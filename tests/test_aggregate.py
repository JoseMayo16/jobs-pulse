from datetime import date

from jobs_pulse.aggregate import boards_summary, hn_summary
from jobs_pulse.models import Listing


def listing(i, skills, last_seen="2026-10-10", salary=None):
    low, high = salary or (None, None)
    return Listing(
        source="remoteok",
        source_id=str(i),
        title=f"Job {i}",
        company=f"Co {i}",
        url=f"https://example.com/{i}",
        posted_at="2026-10-01",
        skills=skills,
        first_seen="2026-10-01",
        last_seen=last_seen,
        salary_min=low,
        salary_max=high,
    )


def test_boards_summary_counts_skills_inside_the_window():
    items = [
        listing(1, ["Python", "Django"]),
        listing(2, ["Python"]),
        listing(3, ["Go"]),
        listing(4, ["Python"], last_seen="2026-08-01"),  # outside the 30-day window
    ]
    summary = boards_summary({x.key: x for x in items}, date(2026, 10, 10))
    assert summary["total"] == 3
    top = summary["skills"][0]
    assert (top["name"], top["count"], top["share"]) == ("Python", 2, round(2 / 3, 4))
    assert top["category"] == "language"
    assert {x["title"] for x in summary["latest"]} == {"Job 1", "Job 2", "Job 3"}


def test_salary_needs_enough_samples():
    items = [listing(i, ["Go"], salary=(100_000, 140_000)) for i in range(5)]
    items.append(listing(9, ["Rust"], salary=(200_000, None)))
    summary = boards_summary({x.key: x for x in items}, date(2026, 10, 10))
    assert summary["salary"] == [{"name": "Go", "median": 120_000, "samples": 5}]


def month(i):
    return f"{2025 + (i // 12)}-{i % 12 + 1:02d}"


def test_hn_summary_shares_and_movers():
    months = {}
    for i in range(16):
        rust = 10 if i >= 13 else 2
        months[month(i)] = {"posts": 100, "remote": 50, "skills": {"Rust": rust, "Java": 20 - i}}
    summary = hn_summary(months)
    assert summary["months"][0] == "2025-01"
    assert summary["skills"]["Rust"][-1] == 0.1
    assert summary["remote_share"] == [0.5] * 16

    movers = summary["movers"]
    assert movers["now"] == ["2026-02", "2026-03", "2026-04"]
    assert movers["before"] == ["2025-02", "2025-03", "2025-04"]
    assert [r["name"] for r in movers["rising"]] == ["Rust"]
    assert [r["name"] for r in movers["falling"]] == ["Java"]


def test_hn_summary_without_a_year_of_history_has_no_movers():
    months = {month(i): {"posts": 10, "remote": 1, "skills": {}} for i in range(6)}
    assert hn_summary(months)["movers"] is None


def test_hn_movers_skip_the_month_in_progress():
    months = {month(i): {"posts": 100, "remote": 50, "skills": {"Rust": 5}} for i in range(16)}
    movers = hn_summary(months, current_month="2026-04")["movers"]
    assert movers["now"] == ["2026-01", "2026-02", "2026-03"]
    assert movers["before"] == ["2025-01", "2025-02", "2025-03"]
    assert hn_summary(months, current_month="2026-04")["months"][-1] == "2026-04"
