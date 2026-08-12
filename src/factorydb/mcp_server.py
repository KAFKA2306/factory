from __future__ import annotations

from typing import Any

from mcp.server import MCPServer

from . import queries

MCP_SCHEMA_VERSION = "factorydb.mcp.v1"

mcp = MCPServer(
    "FactoryDB",
    version="0.2.0",
    instructions=(
        "Read-only access to FactoryDB canonical data. "
        "Values are returned from the same deterministic query layer used by the REST API. "
        "Do not infer missing facts; use source evidence and coverage status as returned."
    ),
)


def _collection(name: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": MCP_SCHEMA_VERSION,
        "collection": name,
        "count": len(items),
        "items": items,
    }


@mcp.tool()
def search_companies(
    query: str | None = None,
    country: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Search companies by legal name, website token, and optional ISO alpha-2 country."""
    return _collection("companies", queries.search_companies(query, country, limit))


@mcp.tool()
def search_facilities(
    query: str | None = None,
    country: str | None = None,
    process: str | None = None,
    product: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Search factories and manufacturing sites with deterministic filters."""
    return _collection(
        "facilities",
        queries.facilities(
            country=country,
            process=process,
            product=product,
            query=query,
            limit=limit,
        ),
    )


@mcp.tool()
def get_facility(facility_id: str) -> dict[str, Any]:
    """Get one facility by canonical ID, preserving its primary-source citations."""
    item = queries.facility(facility_id)
    return {
        "schema_version": MCP_SCHEMA_VERSION,
        "found": item is not None,
        "facility": item,
    }


@mcp.tool()
def get_facilities_batch(facility_ids: list[str]) -> dict[str, Any]:
    """Get up to 100 facilities by canonical IDs in one read-only call."""
    return _collection("facilities", queries.facilities_batch(facility_ids))


@mcp.tool()
def get_country_coverage(country: str | None = None) -> dict[str, Any]:
    """Get global coverage or one country's factory/verified-no-factory resolution status."""
    return {
        "schema_version": MCP_SCHEMA_VERSION,
        "coverage": queries.country_coverage(country),
    }


@mcp.tool()
def get_coverage_resolution(country: str) -> dict[str, Any]:
    """Get the official-source no-qualifying-factory resolution for one country, if present."""
    code = country.upper()
    item = next(
        (row for row in queries.coverage_resolutions() if row["country_code"] == code),
        None,
    )
    return {
        "schema_version": MCP_SCHEMA_VERSION,
        "found": item is not None,
        "resolution": item,
    }


@mcp.tool()
def get_products(limit: int = 100) -> dict[str, Any]:
    """List product names deterministically derived from canonical facility records."""
    if not 1 <= limit <= queries.MAX_RESULTS:
        raise ValueError(f"limit must be between 1 and {queries.MAX_RESULTS}")
    return _collection("products", queries.products()[:limit])


@mcp.tool()
def get_processes(limit: int = 100) -> dict[str, Any]:
    """List manufacturing processes deterministically derived from canonical facilities."""
    if not 1 <= limit <= queries.MAX_RESULTS:
        raise ValueError(f"limit must be between 1 and {queries.MAX_RESULTS}")
    return _collection("processes", queries.processes()[:limit])


@mcp.tool()
def get_assets() -> dict[str, Any]:
    """List recorded manufacturing assets and their source citations."""
    return _collection("assets", queries.assets())


@mcp.tool()
def get_investments() -> dict[str, Any]:
    """List recorded investments and their source citations."""
    return _collection("investments", queries.investments())


@mcp.tool()
def get_financials() -> dict[str, Any]:
    """List financial snapshots with accounting basis, scale, period, and citations."""
    return _collection("financials", queries.financials())


@mcp.tool()
def get_ontology() -> dict[str, Any]:
    """List the canonical process and asset ontology terms used by FactoryDB."""
    return _collection("ontology", queries.ontology())


@mcp.tool()
def get_source_evidence(entity_id: str) -> dict[str, Any]:
    """Return source citations for one canonical entity without recomputing the entity."""
    return {
        "schema_version": MCP_SCHEMA_VERSION,
        "evidence": queries.source_evidence(entity_id),
    }


@mcp.tool()
def get_data_health() -> dict[str, Any]:
    """Return collection counts, latest source retrieval date, and coverage health."""
    return queries.data_health()


def main() -> None:
    """Run the MCP server standalone on localhost for development."""
    mcp.run("streamable-http", host="127.0.0.1", port=8001)
