from __future__ import annotations

import json

from .store import coverage, load_all

FACTORY_COVERAGE_SCOPE_CAP = 179


def validate_coverage_resolutions() -> dict:
    data = load_all()
    errors: list[str] = []
    country_codes = {row.iso2 for row in data["countries"]}
    facility_country_codes = {row.country_code for row in data["facilities"]}
    resolution_codes = [row.country_code for row in data["coverage_resolutions"]]

    duplicate_codes = sorted(
        {code for code in resolution_codes if resolution_codes.count(code) > 1}
    )
    if duplicate_codes:
        errors.append(f"duplicate coverage resolution country codes: {duplicate_codes}")

    for resolution in data["coverage_resolutions"]:
        if resolution.country_code not in country_codes:
            errors.append(f"{resolution.id}: unknown country_code {resolution.country_code}")
        if resolution.country_code in facility_country_codes:
            errors.append(f"{resolution.id}: country already has a qualifying facility record")

    report = coverage(data)
    if report["factory_covered_countries"] > FACTORY_COVERAGE_SCOPE_CAP:
        errors.append(
            "factory coverage scope cap exceeded: "
            f"{report['factory_covered_countries']} > {FACTORY_COVERAGE_SCOPE_CAP}"
        )

    result = {
        "ok": not errors,
        "errors": errors,
        "policy": {"factory_coverage_scope_cap": FACTORY_COVERAGE_SCOPE_CAP},
        "coverage": report,
    }
    if errors:
        raise SystemExit(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main() -> None:
    print(
        json.dumps(
            validate_coverage_resolutions(),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
