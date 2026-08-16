from factorydb.store import load_all


def test_verified_gm_company_facilities_and_exact_amount_investments() -> None:
    data = load_all()

    companies = {row.id: row for row in data["companies"]}
    facilities = {row.id: row for row in data["facilities"]}
    investments = {row.id: row for row in data["investments"]}

    assert companies["company:general-motors-company"].legal_name == "General Motors Company"

    expected_facilities = {
        "facility:gm-romulus-propulsion-systems",
        "facility:gm-toledo-propulsion-systems",
        "facility:gm-saginaw-metal-casting-operations",
    }
    assert expected_facilities <= facilities.keys()
    assert all(
        facilities[facility_id].company_id == "company:general-motors-company"
        for facility_id in expected_facilities
    )

    romulus = investments["investment:gm-romulus-transmission-2026-300m"]
    assert romulus.amount == 300_000_000
    assert romulus.facility_ids == ["facility:gm-romulus-propulsion-systems"]

    toledo = investments["investment:gm-toledo-transmission-2026-40m"]
    assert toledo.amount == 40_000_000
    assert toledo.facility_ids == ["facility:gm-toledo-propulsion-systems"]

    # GM's individual Saginaw announcement says "over $150 million". The current
    # Investment model cannot represent a lower-bound amount, so fail closed and
    # require no exact-amount Saginaw investment record until that semantic exists.
    assert not any(
        row.facility_ids == ["facility:gm-saginaw-metal-casting-operations"]
        for row in data["investments"]
    )
