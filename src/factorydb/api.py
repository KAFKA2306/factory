from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .store import coverage, load_all

app = FastAPI(
    title="FactoryDB API",
    version="0.1.0",
    description="Official-source global factory, asset, process, investment and financial database.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/coverage")
def get_coverage() -> dict:
    return coverage(load_all())


@app.get("/v1/countries")
def get_countries() -> list[dict]:
    return [row.model_dump(mode="json") for row in load_all()["countries"]]


@app.get("/v1/companies")
def get_companies() -> list[dict]:
    return [row.model_dump(mode="json") for row in load_all()["companies"]]


@app.get("/v1/facilities")
def get_facilities(
    country: str | None = Query(default=None, min_length=2, max_length=2),
    process: str | None = None,
    product: str | None = None,
) -> list[dict]:
    rows = load_all()["facilities"]
    if country:
        rows = [row for row in rows if row.country_code == country.upper()]
    if process:
        rows = [row for row in rows if process in row.processes]
    if product:
        token = product.casefold()
        rows = [row for row in rows if any(token in item.casefold() for item in row.products)]
    return [row.model_dump(mode="json") for row in rows]


@app.get("/v1/facilities/{facility_id}")
def get_facility(facility_id: str) -> dict:
    key = facility_id if facility_id.startswith("facility:") else f"facility:{facility_id}"
    for row in load_all()["facilities"]:
        if row.id == key:
            return row.model_dump(mode="json")
    raise HTTPException(status_code=404, detail="facility not found")


@app.get("/v1/assets")
def get_assets() -> list[dict]:
    return [row.model_dump(mode="json") for row in load_all()["assets"]]


@app.get("/v1/investments")
def get_investments() -> list[dict]:
    return [row.model_dump(mode="json") for row in load_all()["investments"]]


@app.get("/v1/financials")
def get_financials() -> list[dict]:
    return [row.model_dump(mode="json") for row in load_all()["financials"]]


@app.get("/v1/ontology")
def get_ontology() -> list[dict]:
    return load_all()["ontology"]


def main() -> None:
    uvicorn.run("factorydb.api:app", host="0.0.0.0", port=8000, reload=False)
