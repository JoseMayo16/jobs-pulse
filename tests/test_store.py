from datetime import date

from jobs_pulse.models import Listing
from jobs_pulse.store import load_listings, merge, prune, save_listings


def job(source="remotive", source_id="1", title="Backend Engineer", company="Acme", **kw):
    return Listing(
        source=source,
        source_id=source_id,
        title=title,
        company=company,
        url=f"https://example.com/{source}/{source_id}",
        posted_at="2026-10-01",
        skills=["Python"],
        **kw,
    )


def test_merge_adds_new_and_refreshes_known():
    store = {}
    stats = merge(store, [job()], date(2026, 10, 1))
    assert stats == {"new": 1, "seen": 0, "duplicate": 0}
    assert store["remotive:1"].first_seen == "2026-10-01"

    stats = merge(store, [job(title="Backend Engineer II")], date(2026, 10, 2))
    assert stats == {"new": 0, "seen": 1, "duplicate": 0}
    item = store["remotive:1"]
    assert (item.first_seen, item.last_seen, item.title) == (
        "2026-10-01",
        "2026-10-02",
        "Backend Engineer II",
    )


def test_merge_detects_same_job_on_another_board():
    store = {}
    merge(store, [job()], date(2026, 10, 1))
    stats = merge(
        store,
        [job(source="remoteok", source_id="99", company="ACME", title="Backend  Engineer")],
        date(2026, 10, 2),
    )
    assert stats["duplicate"] == 1
    assert list(store) == ["remotive:1"]
    assert store["remotive:1"].also_on == ["remoteok"]
    assert store["remotive:1"].last_seen == "2026-10-02"


def test_prune_drops_listings_not_seen_recently():
    store = {}
    merge(store, [job(source_id="old")], date(2026, 1, 1))
    merge(store, [job(source_id="new", title="Other")], date(2026, 10, 1))
    assert prune(store, date(2026, 10, 1), keep_days=120) == 1
    assert list(store) == ["remotive:new"]


def test_save_and_load_round_trip_sorted(tmp_path):
    store = {}
    merge(store, [job(source_id="b", title="B"), job(source_id="a", title="A")], date(2026, 10, 1))
    path = tmp_path / "listings.jsonl"
    save_listings(path, store)
    lines = path.read_text().splitlines()
    assert ['"source_id": "a"' in lines[0], '"source_id": "b"' in lines[1]] == [True, True]
    assert load_listings(path) == store
