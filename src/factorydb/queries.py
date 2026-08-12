from __future__ import annotations

from typing import Any

from .store import coverage, load_all

MAX_RESULTS = 100


def _bounded_limit(limit: int) -> int:
    if not 1 <= limit <= MAX_RESULTS:
        raise ValueError(f"limit must be between 1 and {MAX_RESULTS}")
    return limit


def _dump(rows: list[Any]) -> list[dict[str, Any]]:
    return [row.model_dump(mode="json") for row in rows]


def coverage_summary() -> dict[str, Any]:
    return coverage(load_all())


def coverage_resolutions() -> list[dict[str, Any]]:
    return _dump(load_all()["coverage_resolutions"])


def countries() -> list[dict[str, Any]]:
    return _dump(load_all()["countries"])


def companies() -> list[dict[str, Any]]:
    return _dump(load_all()["companies"])


def search_companies(
    query: str | None = None,
    country: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    rows = load_all()["companies"]
    if country:
        code = country.upper()
        rows = [row for row in rows if row.country_code == code]
    if query:
        token = query.casefold().strip()
        rows = [
            row
            for row in rows
            if token in row.legal_name.casefold() or token in str(row.website).casefold()
        ]
    return _dump(rows[: _bounded_limit(limit)])


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
    return _dump([row for row in load_all()["facilities"] if row.id in wanted])


def products() -> list[dict[str, Any]]:
    rows = load_all()["facilities"]
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        for name in row.products:
            item = result.setdefault(
                name,
                {"name": name, "facility_ids": [], "country_codes": set()},
            )
            item["facility_ids"].append(row.id)
            item["country_codes"].add(row.country_code)
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
    rows = load_all()["facilities"]
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        for name in row.processes:
            item = result.setdefault(
                name,
                {"name": name, "facility_ids": [], "country_codes": set()},
            )
            item["facility_ids"].append(row.id)
            item["country_codes"].add(row.country_code)
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


def assets() -> list[dict[str, Any]]:
    return _dump(load_all()["assets"])


def investments() -> list[dict[str, Any]]:
    return _dump(load_all()["investments"])


def financials() -> list[dict[str, Any]]:
    return _dump(load_all()["financials"])


def ontology() -> list[dict[str, Any]]:
    return load_all()["ontology"]


def country_coverage(country: str | None = None) -> dict[str, Any]:
    data = load_all()
    summary = coverage(data)
    if country is None:
        return summary

    code = country.upper()
    country_row = next((row for row in data["countries"] if row.iso2 == code), None)
    if country_row is None:
        raise ValueError(f"unknown ISO 3166-1 alpha-2 country code: {country}")

    country_facilities = [row for row in data["facilities"] if row.country_code == code]
    resolution = next(
        (row for row in data["coverage_resolutions"] if row.country_code == code),
        None,
    )
    if country_facilities:
        status = "factory_present"
    elif resolution is not None:
        status = resolution.status
    else:
        status = "unresolved"

    return {
        "country_code": code,
        "country": country_row.model_dump(mode="json"),
        "status": status,
        "facility_count": len(country_facilities),
        "facility_ids": sorted(row.id for row in country_facilities),
        "resolution": resolution.model_dump(mode="json") if resolution else None,
    }


def source_evidence(entity_id: str) -> dict[str, Any]:
    data = load_all()
    for collection in (
        "countries",
        "companies",
        "facilities",
        "coverage_resolutions",
        "assets",
        "investments",
        "financials",
    ):
        for row in data[collection]:
            if row.id != entity_id:
                continue
            payload = row.model_dump(mode="json")
            citations: list[dict[str, Any]] = []
            if payload.get("source"):
                citations.append(payload["source"])
            if payload.get("indicator_source"):
                citations.append(payload["indicator_source"])
            citations.extend(payload.get("sources", []))
            return {
                "found": True,
                "entity_id": entity_id,
                "collection": collection,
                "citations": citations,
            }
    return {"found": False, "entity_id": entity_id, "collection": None, "citations": []}


def data_health() -> dict[str, Any]:
    data = load_all()
    source_dates: list[str] = []
    for collection in (
        "countries",
        "companies",
        "facilities",
        "coverage_resolutions",
        "assets",
        "investments",
        "financials",
    ):
        for row in data[collection]:
            payload = row.model_dump(mode="json")
            if payload.get("source"):
                source_dates.append(payload["source"]["retrieved_at"])
            if payload.get("indicator_source"):
                source_dates.append(payload["indicator_source"]["retrieved_at"])
            source_dates.extend(item["retrieved_at"] for item in payload.get("sources", []))

    return {
        "schema_version": "factorydb.data-health.v1",
        "collections": {
            "countries": len(data["countries"]),
            "companies": len(data["companies"]),
            "facilities": len(data["facilities"]),
            "coverage_resolutions": len(data["coverage_resolutions"]),
            "assets": len(data["assets"]),
            "investments": len(data["investments"]),
            "financials": len(data["financials"]),
            "ontology_terms": len(data["ontology"]),
        },
        "source_retrieved_through": max(source_dates) if source_dates else None,
        "coverage": coverage(data),
    }
