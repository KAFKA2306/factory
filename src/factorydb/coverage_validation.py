from __future__ import annotations

import argparse
import json

from .store import coverage, load_all


def validate_coverage_resolutions(require_complete: bool = False) -> dict:
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
            errors.append(
                f"{resolution.id}: unknown country_code {resolution.country_code}"
            )
        if resolution.country_code in facility_country_codes:
            errors.append(
                f"{resolution.id}: country already has a qualifying facility record"
            )

    report = coverage(data)
    if require_complete and report["coverage_missing_countries"]:
        errors.append(
            "resolved coverage gate failed: "
            f"{report['coverage_missing_countries']} countries lack either a factory record "
            "or an official-source no-factory resolution"
        )

    result = {"ok": not errors, "errors": errors, "coverage": report}
    if errors:
        raise SystemExit(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            validate_coverage_resolutions(require_complete=args.require_complete),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
