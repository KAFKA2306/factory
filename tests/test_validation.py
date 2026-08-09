from factorydb.coverage_validation import validate_coverage_resolutions
from factorydb.store import coverage, load_all
from factorydb.validate import validate


def test_repository_data_is_valid():
    result = validate()
    assert result["ok"] is True


def test_coverage_resolutions_are_valid():
    result = validate_coverage_resolutions()
    assert result["ok"] is True


def test_all_iso_country_profiles_exist():
    report = coverage(load_all())
    assert report["country_profiles"] == 249


def test_no_factory_has_missing_source():
    for row in load_all()["facilities"]:
        assert row.sources
        assert str(row.sources[0].url).startswith("https://")


def test_no_coverage_resolution_has_missing_source():
    for row in load_all()["coverage_resolutions"]:
        assert row.sources
        assert all(str(source.url).startswith("https://") for source in row.sources)


def test_factory_records_are_not_empty():
    report = coverage(load_all())
    assert report["factory_records"] > 0
    assert report["factory_covered_countries"] > 0


def test_coverage_partition_is_complete_and_disjoint():
    report = coverage(load_all())
    covered = set(report["covered_country_codes"])
    resolved_no_factory = set(
        report["verified_no_qualifying_factory_country_codes"]
    )
    missing = set(report["missing_country_codes"])

    assert covered.isdisjoint(resolved_no_factory)
    assert covered.isdisjoint(missing)
    assert resolved_no_factory.isdisjoint(missing)
    assert len(covered | resolved_no_factory | missing) == 249


def test_known_non_factory_territories_have_official_resolutions():
    report = coverage(load_all())
    codes = set(report["verified_no_qualifying_factory_country_codes"])
    assert {"AQ", "BV", "GS", "HM"}.issubset(codes)
