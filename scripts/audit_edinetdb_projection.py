from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROJECTION_URL = (
    "https://raw.githubusercontent.com/KAFKA2306/semiconductor-earnings-model/main/"
    "data/edinetdb_projections/KAFKA2306__factory/factory-toyota-financials.json"
)
DEFAULT_CANONICAL = ROOT / "data" / "financials.jsonl"
DEFAULT_AUDIT = ROOT / "audit" / "edinetdb-projection-audit.json"
EXPECTED_CONSUMER = "KAFKA2306/factory"
EXPECTED_PROVIDER = "EDINET DB"
EXPECTED_ATTRIBUTION = "Powered by EDINET DB"

METRIC_MAP = {
    "revenue": "sales_revenues",
    "operating_income": "operating_income",
    "net_income": "net_income",
    "total_assets": "total_assets",
    "total_liabilities": "total_liabilities",
    "cf_operating": "cash_flow_from_operating_activities",
    "cf_investing": "cash_flow_from_investing_activities",
    "cf_financing": "cash_flow_from_financing_activities",
}

SCALE_DIVISORS = {
    "unit": 1.0,
    "thousand": 1_000.0,
    "million": 1_000_000.0,
    "billion": 1_000_000_000.0,
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: {exc}") from exc
    return rows


def fetch_projection(url: str) -> tuple[dict[str, Any], str]:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "KAFKA2306-factory-edinetdb-consumer/1.0",
        },
    )
    with urlopen(request, timeout=30) as response:
        body = response.read()
    return json.loads(body.decode("utf-8")), hashlib.sha256(body).hexdigest()


def load_projection(path: Path) -> tuple[dict[str, Any], str]:
    body = path.read_bytes()
    return json.loads(body.decode("utf-8")), hashlib.sha256(body).hexdigest()


def validate_projection(payload: dict[str, Any]) -> None:
    if payload.get("schema_version") != "edinetdb.consumer-projection.v1":
        raise ValueError("unsupported projection schema")
    if payload.get("consumer") != EXPECTED_CONSUMER:
        raise ValueError(f"projection consumer must be {EXPECTED_CONSUMER}")
    if payload.get("provider") != EXPECTED_PROVIDER:
        raise ValueError("unexpected projection provider")
    if payload.get("attribution") != EXPECTED_ATTRIBUTION:
        raise ValueError("EDINET DB attribution is missing")
    if not payload.get("request_fingerprint"):
        raise ValueError("projection request_fingerprint is required")
    if not payload.get("response_sha256"):
        raise ValueError("projection response_sha256 is required")
    records = payload.get("records")
    if not isinstance(records, list):
        raise ValueError("projection records must be a list")


def normalize_fiscal_year(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).upper().strip()
    if text.startswith("FY"):
        text = text[2:]
    digits = "".join(char for char in text if char.isdigit())
    if len(digits) >= 4:
        return f"FY{digits[:4]}"
    return None


def convert_yen_to_scale(value: Any, scale: str) -> float | None:
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    divisor = SCALE_DIVISORS.get(scale)
    if divisor is None:
        raise ValueError(f"unsupported canonical scale: {scale}")
    return float(value) / divisor


def compare_projection(
    projection: dict[str, Any],
    canonical_rows: list[dict[str, Any]],
    *,
    tolerance_scaled_units: float = 1.0,
) -> dict[str, Any]:
    by_fy = {
        normalize_fiscal_year(row.get("fiscal_year")): row
        for row in canonical_rows
        if normalize_fiscal_year(row.get("fiscal_year"))
    }
    comparisons: list[dict[str, Any]] = []

    for projected in projection.get("records", []):
        fiscal_year = normalize_fiscal_year(projected.get("fiscal_year"))
        canonical = by_fy.get(fiscal_year)
        if canonical is None:
            continue
        scale = canonical.get("scale", "unit")
        metrics = canonical.get("metrics", {})
        for source_key, canonical_key in METRIC_MAP.items():
            if source_key not in projected or canonical_key not in metrics:
                continue
            projected_scaled = convert_yen_to_scale(projected.get(source_key), scale)
            canonical_value = metrics.get(canonical_key)
            if projected_scaled is None or not isinstance(canonical_value, (int, float)):
                continue
            difference = projected_scaled - float(canonical_value)
            matched = math.isclose(
                projected_scaled,
                float(canonical_value),
                rel_tol=0.0,
                abs_tol=tolerance_scaled_units,
            )
            comparisons.append(
                {
                    "fiscal_year": fiscal_year,
                    "edinetdb_field": source_key,
                    "canonical_field": canonical_key,
                    "canonical_scale": scale,
                    "edinetdb_value_yen": projected[source_key],
                    "edinetdb_value_scaled": projected_scaled,
                    "canonical_value": canonical_value,
                    "difference_scaled": difference,
                    "matched": matched,
                }
            )

    matched = sum(1 for item in comparisons if item["matched"])
    mismatched = len(comparisons) - matched
    return {
        "schema_version": "factorydb.edinetdb-audit.v1",
        "projection_id": projection.get("projection_id"),
        "request_fingerprint": projection.get("request_fingerprint"),
        "edinetdb_response_sha256": projection.get("response_sha256"),
        "provider": projection.get("provider"),
        "attribution": projection.get("attribution"),
        "fetched_at": projection.get("fetched_at"),
        "comparison_count": len(comparisons),
        "matched_count": matched,
        "mismatched_count": mismatched,
        "status": "pass" if comparisons and mismatched == 0 else "fail",
        "comparisons": comparisons,
    }


def run(args: argparse.Namespace) -> int:
    if args.projection_file:
        projection, transport_sha256 = load_projection(Path(args.projection_file))
        projection_location = str(Path(args.projection_file))
    else:
        projection, transport_sha256 = fetch_projection(args.projection_url)
        projection_location = args.projection_url

    validate_projection(projection)
    canonical_rows = load_jsonl(Path(args.canonical))
    audit = compare_projection(
        projection,
        canonical_rows,
        tolerance_scaled_units=args.tolerance,
    )
    audit["projection_location"] = projection_location
    audit["projection_transport_sha256"] = transport_sha256

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: audit[key] for key in ("status", "comparison_count", "matched_count", "mismatched_count")}))

    if args.require_match and audit["status"] != "pass":
        return 1
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit FactoryDB canonical financials against the shared EDINETDB projection."
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--projection-file")
    source.add_argument("--projection-url", default=DEFAULT_PROJECTION_URL)
    parser.add_argument("--canonical", default=str(DEFAULT_CANONICAL))
    parser.add_argument("--output", default=str(DEFAULT_AUDIT))
    parser.add_argument("--tolerance", type=float, default=1.0)
    parser.add_argument("--require-match", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    sys.exit(run(parse_args()))
