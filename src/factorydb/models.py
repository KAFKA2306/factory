from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceCitation(StrictModel):
    publisher: str = Field(min_length=2)
    url: HttpUrl
    retrieved_at: date
    evidence: str = Field(min_length=8)


class Country(StrictModel):
    id: str
    iso2: str = Field(pattern=r"^[A-Z]{2}$")
    iso3: str = Field(pattern=r"^[A-Z]{3}$")
    numeric: str = Field(pattern=r"^\d{3}$")
    name: str
    official_name: str | None = None
    indicators: dict[str, Any] = Field(default_factory=dict)
    indicator_source: SourceCitation | None = None
    source: SourceCitation


class Company(StrictModel):
    id: str
    legal_name: str
    country_code: str = Field(pattern=r"^[A-Z]{2}$")
    website: HttpUrl
    industry_codes: list[str] = Field(min_length=1)
    sources: list[SourceCitation] = Field(min_length=1)


class Facility(StrictModel):
    id: str
    company_id: str
    name: str
    operator: str
    country_code: str = Field(pattern=r"^[A-Z]{2}$")
    facility_type: Literal["factory", "manufacturing_entity", "industrial_park"]
    granularity: Literal["physical_plant", "manufacturing_company", "site_group"]
    status: Literal["planned", "under_construction", "operational", "suspended", "closed"]
    production_start: str | None = None
    products: list[str] = Field(min_length=1)
    processes: list[str] = Field(min_length=1)
    sources: list[SourceCitation] = Field(min_length=1)
    notes: str | None = None

    @field_validator("production_start")
    @classmethod
    def validate_month(cls, value: str | None) -> str | None:
        if value is not None and not __import__("re").match(r"^\d{4}(-\d{2})?$", value):
            raise ValueError("production_start must be YYYY or YYYY-MM")
        return value


class Asset(StrictModel):
    id: str
    facility_id: str
    asset_type: str
    name: str
    status: Literal["announced", "under_construction", "operational", "retired"]
    evidence_date: str | None = None
    sources: list[SourceCitation] = Field(min_length=1)


class Investment(StrictModel):
    id: str
    company_id: str
    facility_ids: list[str]
    announcement_date: date
    amount: float = Field(gt=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    purpose: list[str] = Field(min_length=1)
    status: Literal["announced", "approved", "in_progress", "completed", "cancelled"]
    scope_note: str | None = None
    sources: list[SourceCitation] = Field(min_length=1)


class FinancialSnapshot(StrictModel):
    id: str
    company_id: str
    period_end: date
    fiscal_year: str
    accounting_standard: Literal["IFRS", "US_GAAP", "JGAAP", "OTHER"]
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    metrics: dict[str, float] = Field(min_length=1)
    sources: list[SourceCitation] = Field(min_length=1)
