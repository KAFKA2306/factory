from __future__ import annotations

import argparse
import json

from .store import DATA, coverage, load_all

FORBIDDEN = ("sample", "dummy", "placeholder", "example corp", "架空", "ダミー", "サンプル")


def _scan_forbidden() -> list[str]:
    errors: list[str] = []
    for path in DATA.rglob("*"):
        if not path.is_file() or path.suffix not in {".json", ".jsonl"}:
            continue
        text = path.read_text(encoding="utf-8").casefold()
        for token in FORBIDDEN:
            if token.casefold() in text:
                errors.append(f"{path}: forbidden token {token!r}")
    return errors


def validate(require_factory_every_country: bool = False) -> dict:
    data = load_all()
    errors = _scan_forbidden()
    countries = {row.iso2 for row in data["countries"]}
    if len(countries) != 249:
        errors.append(f"country shards must contain 249 ISO entries; got {len(countries)}")

    company_ids = {row.id for row in data["companies"]}
    facility_ids = {row.id for row in data["facilities"]}
    for facility in data["facilities"]:
        if facility.company_id not in company_ids:
            errors.append(f"{facility.id}: unknown company_id {facility.company_id}")
        if facility.country_code not in countries:
            errors.append(f"{facility.id}: unknown country_code {facility.country_code}")
    for asset in data["assets"]:
        if asset.facility_id not in facility_ids:
            errors.append(f"{asset.id}: unknown facility_id {asset.facility_id}")
    for investment in data["investments"]:
        if investment.company_id not in company_ids:
            errors.append(f"{investment.id}: unknown company_id {investment.company_id}")
        for facility_id in investment.facility_ids:
            if facility_id not in facility_ids:
                errors.append(f"{investment.id}: unknown facility_id {facility_id}")

    report = coverage(data)
    if require_factory_every_country and report["factory_missing_countries"]:
        errors.append(
            "factory coverage gate failed: "
            f"{report['factory_missing_countries']} countries have zero factory records"
        )

    result = {"ok": not errors, "errors": errors, "coverage": report}
    if errors:
        raise SystemExit(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-factory-every-country", action="store_true")
    args = parser.parse_args()
    print(json.dumps(validate(args.require_factory_every_country), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
