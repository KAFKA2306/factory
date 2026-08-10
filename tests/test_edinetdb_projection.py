from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "audit_edinetdb_projection.py"
SPEC = importlib.util.spec_from_file_location("audit_edinetdb_projection", MODULE_PATH)
assert SPEC and SPEC.loader
audit_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit_module
SPEC.loader.exec_module(audit_module)
compare_projection = audit_module.compare_projection
validate_projection = audit_module.validate_projection


def projection(records: list[dict]) -> dict:
    return {
        "schema_version": "edinetdb.consumer-projection.v1",
        "consumer": "KAFKA2306/factory",
        "projection_id": "factory-toyota-financials",
        "provider": "EDINET DB",
        "attribution": "Powered by EDINET DB",
        "request_fingerprint": "a" * 64,
        "response_sha256": "b" * 64,
        "fetched_at": "2026-08-10T00:00:00Z",
        "records": records,
    }


def test_projection_contract_requires_factory_consumer_and_attribution() -> None:
    payload = projection([])
    validate_projection(payload)

    bad = dict(payload)
    bad["consumer"] = "KAFKA2306/other"
    try:
        validate_projection(bad)
    except ValueError as exc:
        assert "consumer" in str(exc)
    else:
        raise AssertionError("wrong consumer must fail")


def test_projection_values_are_converted_from_yen_to_million() -> None:
    payload = projection(
        [
            {
                "fiscal_year": "2026",
                "revenue": 50_684_952_000_000,
                "operating_income": 3_766_216_000_000,
                "total_assets": 105_522_331_000_000,
                "total_liabilities": 64_502_263_000_000,
                "cf_operating": 5_472_920_000_000,
                "cf_investing": -1_520_307_000_000,
                "cf_financing": -536_659_000_000,
            }
        ]
    )
    canonical = [
        {
            "fiscal_year": "FY2026",
            "scale": "million",
            "metrics": {
                "sales_revenues": 50_684_952,
                "operating_income": 3_766_216,
                "total_assets": 105_522_331,
                "total_liabilities": 64_502_263,
                "cash_flow_from_operating_activities": 5_472_920,
                "cash_flow_from_investing_activities": -1_520_307,
                "cash_flow_from_financing_activities": -536_659,
            },
        }
    ]

    audit = compare_projection(payload, canonical)
    assert audit["status"] == "pass"
    assert audit["comparison_count"] == 7
    assert audit["mismatched_count"] == 0


def test_projection_audit_fails_closed_on_numeric_mismatch() -> None:
    payload = projection([{"fiscal_year": "FY2026", "total_assets": 100_000_000}])
    canonical = [
        {
            "fiscal_year": "FY2026",
            "scale": "million",
            "metrics": {"total_assets": 999},
        }
    ]
    audit = compare_projection(payload, canonical)
    assert audit["status"] == "fail"
    assert audit["mismatched_count"] == 1


def test_projection_contains_no_undeclared_bulk_payload(tmp_path: Path) -> None:
    payload = projection([{"fiscal_year": "2026", "total_assets": 100_000_000}])
    path = tmp_path / "projection.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    validate_projection(loaded)
    assert "raw_response" not in loaded
    assert "api_key" not in loaded
