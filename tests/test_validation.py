from factorydb.store import coverage, load_all
from factorydb.validate import validate


def test_repository_data_is_valid():
    result = validate()
    assert result["ok"] is True


def test_all_iso_country_profiles_exist():
    report = coverage(load_all())
    assert report["country_profiles"] == 249


def test_no_factory_has_missing_source():
    for row in load_all()["facilities"]:
        assert row.sources
        assert str(row.sources[0].url).startswith("https://")


def test_factory_records_are_not_empty():
    report = coverage(load_all())
    assert report["factory_records"] > 0
    assert report["factory_covered_countries"] > 0
