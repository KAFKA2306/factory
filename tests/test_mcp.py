from __future__ import annotations

import asyncio

from mcp import Client

from factorydb import queries
from factorydb.mcp_server import mcp

EXPECTED_TOOLS = {
    "search_companies",
    "search_facilities",
    "get_facility",
    "get_facilities_batch",
    "get_country_coverage",
    "get_coverage_resolution",
    "get_products",
    "get_processes",
    "get_assets",
    "get_investments",
    "get_financials",
    "get_ontology",
    "get_source_evidence",
    "get_data_health",
}


def test_mcp_lists_standard_read_tools() -> None:
    async def run() -> None:
        async with Client(mcp) as client:
            result = await client.list_tools()
            names = {tool.name for tool in result.tools}
            assert EXPECTED_TOOLS <= names

    asyncio.run(run())


def test_mcp_facility_preserves_primary_source_evidence() -> None:
    async def run() -> None:
        async with Client(mcp) as client:
            result = await client.call_tool(
                "get_facility",
                {"facility_id": "toyota-motomachi"},
            )
            payload = result.structured_content
            assert payload is not None
            assert payload["found"] is True
            facility = payload["facility"]
            assert facility["id"] == "facility:toyota-motomachi"
            assert facility["sources"]
            assert facility["sources"][0]["url"].startswith("http")
            assert facility["sources"][0]["retrieved_at"]
            assert facility["sources"][0]["evidence"]

    asyncio.run(run())


def test_mcp_search_uses_same_query_semantics_as_rest_layer() -> None:
    expected = queries.facilities(country="JP", process="vehicle_assembly", limit=20)

    async def run() -> None:
        async with Client(mcp) as client:
            result = await client.call_tool(
                "search_facilities",
                {"country": "JP", "process": "vehicle_assembly", "limit": 20},
            )
            payload = result.structured_content
            assert payload is not None
            assert payload["items"] == expected
            assert payload["count"] == len(expected)

    asyncio.run(run())


def test_mcp_country_coverage_does_not_invent_missing_factory() -> None:
    unresolved = queries.coverage_summary()["missing_country_codes"]
    if not unresolved:
        return
    country = unresolved[0]

    async def run() -> None:
        async with Client(mcp) as client:
            result = await client.call_tool("get_country_coverage", {"country": country})
            payload = result.structured_content
            assert payload is not None
            assert payload["coverage"]["status"] == "unresolved"
            assert payload["coverage"]["facility_count"] == 0
            assert payload["coverage"]["resolution"] is None

    asyncio.run(run())


def test_mcp_evidence_matches_canonical_record() -> None:
    canonical = queries.facility("toyota-motomachi")
    assert canonical is not None

    async def run() -> None:
        async with Client(mcp) as client:
            result = await client.call_tool(
                "get_source_evidence",
                {"entity_id": "facility:toyota-motomachi"},
            )
            payload = result.structured_content
            assert payload is not None
            evidence = payload["evidence"]
            assert evidence["found"] is True
            assert evidence["collection"] == "facilities"
            assert evidence["citations"] == canonical["sources"]

    asyncio.run(run())
