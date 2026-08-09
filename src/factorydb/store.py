from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from .models import (
    Asset,
    Company,
    Country,
    CoverageResolution,
    Facility,
    FinancialSnapshot,
    Investment,
)

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"


def load_jsonl[T: BaseModel](pattern: str, model: type[T]) -> list[T]:
    paths = sorted(DATA.glob(pattern))
    if not paths:
        raise FileNotFoundError(f"no data files matched {pattern!r}")
    rows: list[T] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    rows.append(model.model_validate_json(line))
                except Exception as exc:
                    raise ValueError(f"{path}:{line_number}: {exc}") from exc
    return rows


def load_all() -> dict[str, Any]:
    return {
        "countries": load_jsonl("countries/*.jsonl", Country),
        "companies": load_jsonl("companies*.jsonl", Company),
        "facilities": load_jsonl("facilities/*.jsonl", Facility),
        "coverage_resolutions": load_jsonl(
            "coverage_resolutions.jsonl", CoverageResolution
        ),
        "assets": load_jsonl("assets.jsonl", Asset),
        "investments": load_jsonl("investments.jsonl", Investment),
        "financials": load_jsonl("financials.jsonl", FinancialSnapshot),
        "ontology": json.loads((DATA / "ontology" / "terms.json").read_text(encoding="utf-8")),
    }


def coverage(data: dict[str, Any]) -> dict[str, Any]:
    country_codes = {row.iso2 for row in data["countries"]}
    facility_counts = {code: 0 for code in country_codes}
    for facility in data["facilities"]:
        facility_counts[facility.country_code] = facility_counts.get(facility.country_code, 0) + 1

    covered = sorted(code for code, count in facility_counts.items() if count > 0)
    zero_factory = sorted(code for code, count in facility_counts.items() if count == 0)
    verified_no_factory = sorted(
        row.country_code
        for row in data["coverage_resolutions"]
        if row.status == "verified_no_qualifying_factory"
    )
    resolved = sorted(set(covered) | set(verified_no_factory))
    unresolved = sorted(country_codes - set(resolved))

    return {
        "country_profiles": len(country_codes),
        "factory_records": len(data["facilities"]),
        "factory_covered_countries": len(covered),
        "factory_missing_countries": len(zero_factory),
        "verified_no_qualifying_factory_countries": len(verified_no_factory),
        "coverage_resolved_countries": len(resolved),
        "coverage_missing_countries": len(unresolved),
        "covered_country_codes": covered,
        "zero_factory_country_codes": zero_factory,
        "verified_no_qualifying_factory_country_codes": verified_no_factory,
        "resolved_country_codes": resolved,
        "missing_country_codes": unresolved,
    }
