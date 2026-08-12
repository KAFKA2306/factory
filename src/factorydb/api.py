from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import queries
from .mcp_server import mcp

mcp_http_app = mcp.streamable_http_app()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    async with mcp.session_manager.run():
        yield


app = FastAPI(
    title="FactoryDB API",
    version="0.2.0",
    description="Official-source global factory, asset, process, investment and financial database.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Mcp-Session-Id"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/coverage")
def get_coverage() -> dict:
    return queries.coverage_summary()


@app.get("/v1/coverage-resolutions")
def get_coverage_resolutions() -> list[dict]:
    return queries.coverage_resolutions()


@app.get("/v1/countries")
def get_countries() -> list[dict]:
    return queries.countries()


@app.get("/v1/companies")
def get_companies() -> list[dict]:
    return queries.companies()


@app.get("/v1/facilities")
def get_facilities(
    country: str | None = Query(default=None, min_length=2, max_length=2),
    process: str | None = None,
    product: str | None = None,
) -> list[dict]:
    return queries.facilities(country=country, process=process, product=product)


@app.get("/v1/facilities/{facility_id}")
def get_facility(facility_id: str) -> dict:
    item = queries.facility(facility_id)
    if item is None:
        raise HTTPException(status_code=404, detail="facility not found")
    return item


@app.get("/v1/products")
def get_products() -> list[dict]:
    return queries.products()


@app.get("/v1/processes")
def get_processes() -> list[dict]:
    return queries.processes()


@app.get("/v1/assets")
def get_assets() -> list[dict]:
    return queries.assets()


@app.get("/v1/investments")
def get_investments() -> list[dict]:
    return queries.investments()


@app.get("/v1/financials")
def get_financials() -> list[dict]:
    return queries.financials()


@app.get("/v1/ontology")
def get_ontology() -> list[dict]:
    return queries.ontology()


# Mount last: Starlette routes are matched in order and Mount("/") catches all remaining paths.
app.mount("/", mcp_http_app)


def main() -> None:
    uvicorn.run("factorydb.api:app", host="0.0.0.0", port=8000, reload=False)
