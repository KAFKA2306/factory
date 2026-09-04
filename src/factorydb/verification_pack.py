from __future__ import annotations

import argparse
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from .store import DATA, load_all

EvidenceStatus = Literal["VERIFIED", "PARTIAL", "NOT_FOUND", "CONFLICT"]
CoverageStatus = Literal["factory_present", "verified_no_qualifying_factory", "unresolved"]


class EvidenceClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_id: str
    field: str
    value: Any = None
    evidence_status: EvidenceStatus
    source_urls: list[HttpUrl] = Field(default_factory=list)
    note: str | None = None


class CoverageState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    country_code: str
    status: CoverageStatus
    facility_count: int = Field(ge=0)
    source_urls: list[HttpUrl] = Field(default_factory=list)


class FacilityVerificationPack(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["factorydb.facility-verification-pack.v1"] = (
        "factorydb.facility-verification-pack.v1"
    )
    company_id: str
    company_name: str | None = None
    decision_status: EvidenceStatus
    claims: list[EvidenceClaim]
    coverage_states: list[CoverageState]
    caveats: list[str]


def _source_urls(row: Any) -> list[str]:
    payload = row.model_dump(mode="json")
    sources: list[dict[str, Any]] = []
    if payload.get("source"):
        sources.append(payload["source"])
    if payload.get("indicator_source"):
        sources.append(payload["indicator_source"])
    sources.extend(payload.get("sources", []))
    return sorted({item["url"] for item in sources})


def _claim(row: Any, field: str, value: Any | None = None) -> EvidenceClaim:
    payload = row.model_dump(mode="json")
    resolved_value = payload.get(field) if value is None else value
    urls = _source_urls(row)
    return EvidenceClaim(
        entity_id=row.id,
        field=field,
        value=resolved_value,
        evidence_status="VERIFIED" if urls else "PARTIAL",
        source_urls=urls,
        note=None if urls else "Canonical record exists but has no source citation.",
    )


def _automation_claims(company_id: str, facility_ids: set[str]) -> list[EvidenceClaim]:
    source_doc = json.loads((DATA / "robotics-sources.json").read_text(encoding="utf-8"))
    sources = source_doc.get("sources")
    if not isinstance(sources, list):
        raise TypeError("robotics-sources.json must contain a sources list")
    source_map = {source["source_id"]: source for source in sources}
    if len(source_map) != len(sources):
        raise ValueError("duplicate robotics source_id")

    claims: list[EvidenceClaim] = []
    with (DATA / "automation.jsonl").open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                observation = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"automation.jsonl:{line_number}: {exc}") from exc
            if observation.get("company_id") != company_id:
                continue
            facility_id = observation.get("facility_id")
            if facility_id not in facility_ids:
                continue
            source_id = observation.get("source_id")
            source = source_map.get(source_id)
            if source is None:
                raise ValueError(
                    f"automation.jsonl:{line_number}: unknown robotics source_id {source_id!r}"
                )
            source_url = source.get("source_url")
            if not source_url:
                raise ValueError(f"robotics source {source_id!r} has no source_url")
            value = {
                key: observation[key]
                for key in (
                    "equipment_type",
                    "status",
                    "deployment_stage",
                    "observed_at",
                    "description",
                    "quantity",
                    "quantity_unit",
                    "quantity_qualifier",
                    "performance_metric",
                )
                if key in observation
            }
            claims.append(
                EvidenceClaim(
                    entity_id=facility_id,
                    field="automation_observation",
                    value=value,
                    evidence_status="VERIFIED",
                    source_urls=[source_url],
                )
            )
    return claims


def build_facility_verification_pack(company_id: str) -> FacilityVerificationPack:
    data = load_all()
    key = company_id if company_id.startswith("company:") else f"company:{company_id}"
    matching_companies = [row for row in data["companies"] if row.id == key]

    if not matching_companies:
        return FacilityVerificationPack(
            company_id=key,
            decision_status="NOT_FOUND",
            claims=[
                EvidenceClaim(
                    entity_id=key,
                    field="entity",
                    value=None,
                    evidence_status="NOT_FOUND",
                    note="No canonical company record exists in FactoryDB.",
                )
            ],
            coverage_states=[],
            caveats=[
                "NOT_FOUND means no canonical FactoryDB record was found; it is not evidence that the company does not exist."
            ],
        )

    if len(matching_companies) > 1:
        return FacilityVerificationPack(
            company_id=key,
            decision_status="CONFLICT",
            claims=[
                EvidenceClaim(
                    entity_id=key,
                    field="entity",
                    value=None,
                    evidence_status="CONFLICT",
                    note="Multiple canonical company records share the same ID.",
                )
            ],
            coverage_states=[],
            caveats=["Resolve duplicate canonical identity before using this pack for a decision."],
        )

    company = matching_companies[0]
    facilities = [row for row in data["facilities"] if row.company_id == key]
    facility_ids = {row.id for row in facilities}
    assets = [row for row in data["assets"] if row.facility_id in facility_ids]
    investments = [row for row in data["investments"] if row.company_id == key]
    financials = [row for row in data["financials"] if row.company_id == key]

    claims = [
        _claim(company, "legal_name"),
        _claim(company, "country_code"),
        _claim(company, "website"),
        _claim(company, "industry_codes"),
    ]

    for facility in facilities:
        for field in (
            "name",
            "operator",
            "country_code",
            "facility_type",
            "granularity",
            "status",
            "production_start",
            "products",
            "processes",
            "scale_metrics",
        ):
            value = facility.model_dump(mode="json").get(field)
            if value not in (None, {}, []):
                claims.append(_claim(facility, field))

    claims.extend(_automation_claims(key, facility_ids))

    if assets:
        for asset in assets:
            for field in ("name", "asset_type", "status", "evidence_date"):
                value = asset.model_dump(mode="json").get(field)
                if value is not None:
                    claims.append(_claim(asset, field))
    else:
        claims.append(
            EvidenceClaim(
                entity_id=key,
                field="assets",
                value=[],
                evidence_status="NOT_FOUND",
                note="No canonical asset records are linked to this company's facilities; this is not evidence of absence.",
            )
        )

    if investments:
        for investment in investments:
            for field in (
                "announcement_date",
                "amount",
                "currency",
                "purpose",
                "status",
                "facility_ids",
                "expected_impacts",
            ):
                value = investment.model_dump(mode="json").get(field)
                if value not in (None, {}, []):
                    claims.append(_claim(investment, field))
    else:
        claims.append(
            EvidenceClaim(
                entity_id=key,
                field="investments",
                value=[],
                evidence_status="NOT_FOUND",
                note="No canonical investment records are linked to this company; this is not evidence of absence.",
            )
        )

    if financials:
        for snapshot in financials:
            for field in (
                "period_end",
                "fiscal_year",
                "accounting_standard",
                "currency",
                "metrics",
            ):
                claims.append(_claim(snapshot, field))

    relevant_codes = sorted({company.country_code, *(row.country_code for row in facilities)})
    coverage_states: list[CoverageState] = []
    for code in relevant_codes:
        country_facilities = [row for row in data["facilities"] if row.country_code == code]
        resolution = next(
            (row for row in data["coverage_resolutions"] if row.country_code == code),
            None,
        )
        if country_facilities:
            coverage_states.append(
                CoverageState(
                    country_code=code,
                    status="factory_present",
                    facility_count=len(country_facilities),
                    source_urls=sorted(
                        {url for row in country_facilities for url in _source_urls(row)}
                    ),
                )
            )
        elif resolution is not None:
            coverage_states.append(
                CoverageState(
                    country_code=code,
                    status="verified_no_qualifying_factory",
                    facility_count=0,
                    source_urls=_source_urls(resolution),
                )
            )
        else:
            coverage_states.append(
                CoverageState(
                    country_code=code,
                    status="unresolved",
                    facility_count=0,
                )
            )

    has_partial_claim = any(claim.evidence_status == "PARTIAL" for claim in claims)
    has_unresolved_coverage = any(state.status == "unresolved" for state in coverage_states)
    decision_status: EvidenceStatus = (
        "VERIFIED"
        if facilities and not has_partial_claim and not has_unresolved_coverage
        else "PARTIAL"
    )

    return FacilityVerificationPack(
        company_id=key,
        company_name=company.legal_name,
        decision_status=decision_status,
        claims=claims,
        coverage_states=coverage_states,
        caveats=[
            "This pack summarizes canonical FactoryDB evidence for pre-screening; it is not a certification, audit pass, or supplier recommendation.",
            "NOT_FOUND means FactoryDB has no linked canonical record; it must not be interpreted as proof that the real-world fact is absent.",
            "Automation observations are included only when the robotics facility ID exactly matches a canonical FactoryDB facility ID; unmatched company or facility observations are excluded rather than inferred.",
            "Source URLs identify the evidence used by the canonical record; verify the source again for time-sensitive decisions.",
        ],
    )


def render_markdown(pack: FacilityVerificationPack) -> str:
    lines = [
        f"# Facility Verification Pack: {pack.company_name or pack.company_id}",
        "",
        f"- Company ID: `{pack.company_id}`",
        f"- Evidence decision: **{pack.decision_status}**",
        f"- Schema: `{pack.schema_version}`",
        "",
        "## Evidence claims",
        "",
        "| Entity | Field | Status | Value | Sources |",
        "|---|---|---|---|---|",
    ]
    for claim in pack.claims:
        value = json.dumps(claim.value, ensure_ascii=False, sort_keys=True)
        sources = "<br>".join(str(url) for url in claim.source_urls) or "—"
        note = f" ({claim.note})" if claim.note else ""
        lines.append(
            f"| `{claim.entity_id}` | `{claim.field}` | **{claim.evidence_status}**{note} | `{value}` | {sources} |"
        )

    lines.extend(
        [
            "",
            "## Coverage state",
            "",
            "| Country | State | Facility records | Sources |",
            "|---|---|---:|---|",
        ]
    )
    for state in pack.coverage_states:
        sources = "<br>".join(str(url) for url in state.source_urls) or "—"
        lines.append(
            f"| `{state.country_code}` | **{state.status}** | {state.facility_count} | {sources} |"
        )

    lines.extend(["", "## Caveats", ""])
    lines.extend(f"- {item}" for item in pack.caveats)
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a source-backed Facility Verification Pack")
    parser.add_argument("--company", required=True, help="Canonical company ID or ID suffix")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args()

    pack = build_facility_verification_pack(args.company)
    if args.format == "markdown":
        print(render_markdown(pack), end="")
    else:
        print(pack.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
