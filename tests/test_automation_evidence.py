from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "automation.jsonl"
SOURCES = ROOT / "data" / "robotics-sources.json"

REQUIRED = {
    "company_id",
    "facility_id",
    "company",
    "factory",
    "country",
    "equipment_type",
    "status",
    "deployment_stage",
    "observed_at",
    "description",
    "source_id",
    "source_publisher",
    "source_url",
    "source_retrieved_at",
}
VALID_STATUS = {"planned", "ordered", "installed", "operational", "retired"}


def load_rows() -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in DATA.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_automation_evidence_contract_and_coverage() -> None:
    rows = load_rows()
    assert rows
    assert len({row["company_id"] for row in rows}) >= 10
    assert len({row["facility_id"] for row in rows}) >= 30
    for row in rows:
        assert REQUIRED <= row.keys()
        assert row["status"] in VALID_STATUS
        assert str(row["source_url"]).startswith("https://")
        assert str(row["company_id"]).startswith("company:")
        assert str(row["facility_id"]).startswith("facility:")
        assert row["description"]
        assert "robot_count" not in row
        if "quantity" in row:
            assert isinstance(row["quantity"], (int, float))
            assert row["quantity"] > 0
            assert row.get("quantity_unit")
            assert row.get("quantity_qualifier")


def test_sources_are_primary_and_exactly_joined_to_records() -> None:
    source_doc = json.loads(SOURCES.read_text(encoding="utf-8"))
    source_rows = source_doc["sources"]
    sources = {row["source_id"]: row for row in source_rows}
    assert len(sources) == len(source_rows)
    assert len(sources) >= 10
    for row in load_rows():
        source = sources[row["source_id"]]
        assert row["source_url"] == source["source_url"]
        assert row["source_publisher"] == source["publisher"]


def test_planned_and_installed_states_remain_distinct() -> None:
    rows = load_rows()
    statuses = {row["status"] for row in rows}
    assert "planned" in statuses
    assert "ordered" in statuses
    assert "installed" in statuses
    assert "operational" in statuses
    for row in rows:
        if row["status"] == "planned":
            assert row["deployment_stage"] not in {"production", "series_operation"}
