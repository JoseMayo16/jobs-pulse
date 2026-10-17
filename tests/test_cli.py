import json
import shutil
from pathlib import Path

from jobs_pulse.cli import main

REPO = Path(__file__).resolve().parents[1]


def test_offline_run_reads_and_writes_the_current_directory(tmp_path, monkeypatch):
    """Regression: paths once came from __file__, so an installed package wrote into
    site-packages and the daily run never saw the repository's data."""
    shutil.copytree(REPO / "data", tmp_path / "data")
    monkeypatch.chdir(tmp_path)

    assert main(["run", "--offline"]) == 0

    summary = json.loads((tmp_path / "site" / "data" / "summary.json").read_text())
    stored = sum(1 for _ in (tmp_path / "data" / "listings.jsonl").open())
    assert summary["hn"]["months"]
    assert stored > 0
