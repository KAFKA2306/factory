from fastapi.testclient import TestClient

from factorydb import queries
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


def test_rest_search_uses_the_shared_query_layer():
    params = {"country": "JP", "process": "vehicle_assembly", "query": "Toyota", "limit": 20}
    response = client.get("/v1/facilities", params=params)
    assert response.status_code == 200
    assert response.json() == queries.facilities(
        country="JP",
        process="vehicle_assembly",
        query="Toyota",
        limit=20,
    )


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


def test_source_evidence_exposes_known_and_unknown_provenance_explicitly():
    response = client.get("/v1/source-evidence/facility:toyota-motomachi")
    assert response.status_code == 200
    payload = response.json()
    assert payload["found"] is True
    assert payload["citations"]
    provenance = payload["provenance"][0]
    assert provenance["canonical_id"] == "facility:toyota-motomachi"
    assert provenance["source_type"] == "official_primary"
    assert provenance["source_url"].startswith("http")
    assert provenance["source_observed_at"]
    assert provenance["source_hash"] is None
    assert provenance["freshness"] == "unknown"
    assert provenance["stale"] is None
    assert "source_hash" in provenance["null_reason"]


def test_source_evidence_unknown_entity_fails_closed():
    response = client.get("/v1/source-evidence/facility:not-present")
    assert response.status_code == 404


def test_data_health_reports_provenance_limits_without_inventing_freshness():
    response = client.get("/v1/data-health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["provenance"]["citation_count"] > 0
    assert payload["provenance"]["source_content_hash_count"] == 0
    assert payload["provenance"]["freshness_policy"] == "not_defined"
    assert payload["coverage"]["factory_coverage_scope_cap"] == 179
