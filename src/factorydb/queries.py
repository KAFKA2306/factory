from __future__ import annotations

from typing import Any

from .provenance import PROVENANCE_SCHEMA_VERSION, citation_provenance
from .store import coverage, load_all

MAX_RESULTS = 100
SOURCE_COLLECTIONS = (
    "countries",
    "companies",
    "facilities",
    "coverage_resolutions",
    "assets",
    "investments",
    "financials",
)


def _bounded_limit(limit: int) -> int:
    if not 1 <= limit <= MAX_RESULTS:
        raise ValueError(f"limit must be between 1 and {MAX_RESULTS}")
    return limit


def _dump(rows: list[Any]) -> list[dict[str, Any]]:
    return [row.model_dump(mode="json") for row in rows]


def _citations(payload: dict[str, Any]) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    if payload.get("source"):
        citations.append(payload["source"])
    if payload.get("indicator_source"):
        citations.append(payload["indicator_source"])
    citations.extend(payload.get("sources", []))
    return citations


def coverage_summary() -> dict[str, Any]:
    return coverage(load_all())


def _collection(name: str) -> list[dict[str, Any]]:
    runtime_rows = runtime.collection(name)
    if runtime_rows is not None:
        return runtime_rows
    return _dump(load_all()[name])


def coverage_resolutions() -> list[dict[str, Any]]:
    return _collection("coverage_resolutions")


def countries() -> list[dict[str, Any]]:
    return _collection("countries")


def companies() -> list[dict[str, Any]]:
    return _collection("companies")


def search_companies(
    query: str | None = None,
    country: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    rows = companies()
    if country:
        code = country.upper()
        rows = [row for row in rows if row["country_code"] == code]
    if query:
        token = query.casefold().strip()
        rows = [
            row
            for row in rows
            if token in row["legal_name"].casefold() or token in str(row["website"]).casefold()
        ]
    return rows[: _bounded_limit(limit)]


def facilities(
    country: str | None = None,
    process: str | None = None,
    product: str | None = None,
    query: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    rows = load_all()["facilities"]
    if country:
        code = country.upper()
        rows = [row for row in rows if row.country_code == code]
    if process:
        rows = [row for row in rows if process in row.processes]
    if product:
        token = product.casefold()
        rows = [row for row in rows if any(token in item.casefold() for item in row.products)]
    if query:
        token = query.casefold().strip()
        rows = [
            row
            for row in rows
            if token in row.name.casefold()
            or token in row.operator.casefold()
            or any(token in item.casefold() for item in row.products)
            or any(token in item.casefold() for item in row.processes)
        ]
    if limit is not None:
        rows = rows[: _bounded_limit(limit)]
    return _dump(rows)


def facility(facility_id: str) -> dict[str, Any] | None:
    key = facility_id if facility_id.startswith("facility:") else f"facility:{facility_id}"
    runtime_row = runtime.record("facilities", key)
    if runtime_row is not None:
        return runtime_row
    for row in load_all()["facilities"]:
        if row.id == key:
            return row.model_dump(mode="json")
    return None


def facilities_batch(facility_ids: list[str]) -> list[dict[str, Any]]:
    if not 1 <= len(facility_ids) <= MAX_RESULTS:
        raise ValueError(f"facility_ids must contain between 1 and {MAX_RESULTS} IDs")
    wanted = {
        value if value.startswith("facility:") else f"facility:{value}" for value in facility_ids
    }
    runtime_rows = runtime.facility_rows(ids=sorted(wanted))
    if runtime_rows is not None:
        return runtime_rows
    return _dump([row for row in load_all()["facilities"] if row.id in wanted])


def products() -> list[dict[str, Any]]:
    rows = facilities()
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        for name in row["products"]:
            item = result.setdefault(
                name,
                {"name": name, "facility_ids": [], "country_codes": set()},
            )
            item["facility_ids"].append(row["id"])
            item["country_codes"].add(row["country_code"])
    return [
        {
            "name": item["name"],
            "facility_count": len(item["facility_ids"]),
            "country_count": len(item["country_codes"]),
            "facility_ids": sorted(item["facility_ids"]),
            "country_codes": sorted(item["country_codes"]),
        }
        for item in sorted(result.values(), key=lambda value: value["name"])
    ]
def processes() -> list[dict[str, Any]]:
    rows = facilities()
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        for name in row["processes"]:
            item = result.setdefault(
                name,
                {"name": name, "facility_ids": [], "country_codes": set()},
            )
            item["facility_ids"].append(row["id"])
            item["country_codes"].add(row["country_code"])
    return [
        {
            "name": item["name"],
            "facility_count": len(item["facility_ids"]),
            "country_count": len(item["country_codes"]),
            "facility_ids": sorted(item["facility_ids"]),
            "country_codes": sorted(item["country_codes"]),
        }
        for item in sorted(result.values(), key=lambda value: value["name"])
    ]

