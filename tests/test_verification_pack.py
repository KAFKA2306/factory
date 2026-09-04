import json
from html import unescape
from pathlib import Path
from urllib.parse import unquote

from factorydb.verification_pack import (
    build_facility_verification_pack,
    render_markdown,
)


def test_toyota_pack_is_source_backed_and_decision_ready():
    pack = build_facility_verification_pack("company:toyota-motor-corporation")

    assert pack.company_name == "Toyota Motor Corporation"
    assert pack.decision_status == "VERIFIED"
    assert any(claim.entity_id == "facility:toyota-motomachi" for claim in pack.claims)
    assert any(claim.entity_id == "investment:toyota-texas-2026-3.6b" for claim in pack.claims)
    assert all(claim.source_urls for claim in pack.claims if claim.evidence_status == "VERIFIED")
    automation_claims = [claim for claim in pack.claims if claim.field == "automation_observation"]
    assert len(automation_claims) == 1
    assert automation_claims[0].entity_id == "facility:toyota-motomachi"
    assert automation_claims[0].value["equipment_type"] == "vehicle_logistics_robot"
    assert automation_claims[0].value["status"] == "operational"
    assert str(automation_claims[0].source_urls[0]).startswith(
        "https://global.toyota/en/newsroom/corporate/39758451.html"
    )
    assert any(
        state.country_code == "JP" and state.status == "factory_present"
        for state in pack.coverage_states
    )
    assert any(
        state.country_code == "US" and state.status == "factory_present"
        for state in pack.coverage_states
    )


def test_robotics_observations_require_exact_core_facility_identity():
    pack = build_facility_verification_pack("company:bmw-ag")
    automation_claims = [claim for claim in pack.claims if claim.field == "automation_observation"]

    assert {claim.entity_id for claim in automation_claims} == {
        "facility:bmw-plant-debrecen",
        "facility:bmw-plant-munich",
        "facility:bmw-plant-steyr",
    }
    assert not any(claim.entity_id == "facility:bmw-plant-leipzig" for claim in automation_claims)
    assert all(claim.evidence_status == "VERIFIED" for claim in automation_claims)
    assert all(claim.source_urls for claim in automation_claims)


def test_unknown_company_fails_closed_without_claiming_nonexistence():
    pack = build_facility_verification_pack("company:not-in-factorydb")

    assert pack.decision_status == "NOT_FOUND"
    assert pack.claims[0].evidence_status == "NOT_FOUND"
    assert "not evidence" in pack.caveats[0].lower()


def test_pack_is_deterministic_json_and_markdown():
    first = build_facility_verification_pack("company:toyota-motor-corporation")
    second = build_facility_verification_pack("company:toyota-motor-corporation")

    first_json = json.dumps(first.model_dump(mode="json"), sort_keys=True)
    second_json = json.dumps(second.model_dump(mode="json"), sort_keys=True)
    assert first_json == second_json
    assert render_markdown(first) == render_markdown(second)
    assert "not a certification" in render_markdown(first)


def test_public_site_links_sample_and_qualified_inquiry():
    html = Path("web/index.html").read_text(encoding="utf-8")
    decoded = unquote(unescape(html))

    assert 'href="facility-verification-pack.md"' in html
    assert 'href="facility-verification-pack.json"' in html
    assert "github.com/KAFKA2306/factory/issues/new?title=" in html
    for field in (
        "組織・役割",
        "対象企業数",
        "対象企業・地域（公開情報のみ）",
        "用途",
        "希望時期",
        "相談内容",
    ):
        assert f"{field}:" in decoded
    assert "vendor master" in decoded
    assert "非公開サプライヤー情報" in decoded
