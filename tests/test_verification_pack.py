import json
from pathlib import Path

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
    assert all(
        claim.source_urls
        for claim in pack.claims
        if claim.evidence_status == "VERIFIED"
    )
    assert any(state.country_code == "JP" and state.status == "factory_present" for state in pack.coverage_states)
    assert any(state.country_code == "US" and state.status == "factory_present" for state in pack.coverage_states)


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

    assert 'href="facility-verification-pack.md"' in html
    assert 'href="facility-verification-pack.json"' in html
    assert "issues/new?title=" in html
    for field in ("組織・役割", "対象企業数", "対象企業・地域", "用途", "希望時期", "相談内容"):
        assert field in html or field.encode().hex() not in html
    assert "vendor master" in html
    assert "非公開サプライヤー情報" in html
