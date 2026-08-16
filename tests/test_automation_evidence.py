import json
from pathlib import Path


REQUIRED = {"company", "factory", "country", "equipment_type", "status", "observed_at", "source_url"}
VALID_STATUS = {"planned", "ordered", "installed", "operational", "retired"}


def test_automation_records_have_provenance_and_explicit_status():
    path = Path(__file__).resolve().parents[1] / "data" / "automation.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert rows
    for row in rows:
        assert REQUIRED <= row.keys()
        assert row["status"] in VALID_STATUS
        assert row["source_url"].startswith("https://")
        assert "robot_count" not in row  # do not invent undisclosed counts
