from fastapi.testclient import TestClient

from factorydb.api import app

client = TestClient(app)


def test_coverage_endpoint_reports_real_inventory():
    response = client.get("/v1/coverage")
    assert response.status_code == 200
    payload = response.json()
    assert payload["country_profiles"] == 249
    assert payload["factory_records"] >= 37
    assert payload["factory_covered_countries"] >= 35
    assert payload["coverage_resolved_countries"] >= 39
    assert payload["coverage_missing_countries"] <= 210


def test_country_filter_returns_japan_factory():
    response = client.get("/v1/facilities", params={"country": "JP"})
    assert response.status_code == 200
    rows = response.json()
    assert any(row["id"] == "facility:toyota-motomachi" for row in rows)


def test_products_and_processes_are_derived_from_real_facilities():
    products = client.get("/v1/products").json()
    processes = client.get("/v1/processes").json()
    assert any(row["name"] == "Toyota Hilux" for row in products)
    assert any(row["name"] == "vehicle_assembly" for row in processes)


def test_financial_endpoint_exposes_balance_sheet_amounts():
    response = client.get("/v1/financials")
    assert response.status_code == 200
    row = response.json()[0]
    assert row["scale"] == "million"
    assert row["metrics"]["total_assets"] == 105522331
    assert row["metrics"]["total_liabilities"] == 64502263
