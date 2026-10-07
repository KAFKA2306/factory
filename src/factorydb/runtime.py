from __future__ import annotations

import importlib
import json
import os
import threading
from typing import Any

import httpx

from .store import load_all

DATABASE_URL = os.getenv("FACTORYDB_DATABASE_URL")
OPENSEARCH_URL = os.getenv("FACTORYDB_OPENSEARCH_URL")
OPENSEARCH_INDEX = os.getenv("FACTORYDB_OPENSEARCH_INDEX", "factorydb-facilities-v1")

_initialized = False
_lock = threading.Lock()


def database_enabled() -> bool:
    return bool(DATABASE_URL)


def opensearch_enabled() -> bool:
    return bool(OPENSEARCH_URL)


def _connect() -> Any:
    if not DATABASE_URL:
        raise RuntimeError("FACTORYDB_DATABASE_URL is not configured")
    psycopg = importlib.import_module("psycopg")
    return psycopg.connect(DATABASE_URL)


def _canonical_records() -> list[tuple[str, str, str | None, str]]:
    data = load_all()
    rows: list[tuple[str, str, str | None, str]] = []
    for collection in (
        "countries",
        "companies",
        "facilities",
        "coverage_resolutions",
        "assets",
        "investments",
        "financials",
    ):
        for model in data[collection]:
            payload = model.model_dump(mode="json")
            rows.append(
                (
                    collection,
                    str(payload["id"]),
                    payload.get("country_code") or payload.get("iso2"),
                    json.dumps(payload, ensure_ascii=False),
                )
            )
    return rows


def _bootstrap_postgres(records: list[tuple[str, str, str | None, str]]) -> None:
    with _connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS factorydb_records (
                collection TEXT NOT NULL,
                id TEXT NOT NULL,
                country_code TEXT,
                payload JSONB NOT NULL,
                PRIMARY KEY (collection, id)
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS factorydb_records_collection_country_idx
            ON factorydb_records (collection, country_code)
            """
        )
        cursor.execute("TRUNCATE factorydb_records")
        cursor.executemany(
            """
            INSERT INTO factorydb_records (collection, id, country_code, payload)
            VALUES (%s, %s, %s, %s::jsonb)
            """,
            records,
        )


def _bootstrap_opensearch() -> None:
    if not OPENSEARCH_URL:
        return

    facilities = [model.model_dump(mode="json") for model in load_all()["facilities"]]
    with httpx.Client(base_url=OPENSEARCH_URL, timeout=30.0) as client:
        if client.head(f"/{OPENSEARCH_INDEX}").status_code == 200:
            response = client.delete(f"/{OPENSEARCH_INDEX}")
            response.raise_for_status()

        response = client.put(
            f"/{OPENSEARCH_INDEX}",
            json={
                "mappings": {
                    "properties": {
                        "name": {"type": "text"},
                        "operator": {"type": "text"},
                        "products": {"type": "text"},
                        "processes": {"type": "keyword"},
                        "country_code": {"type": "keyword"},
                    }
                }
            },
        )
        response.raise_for_status()

        lines: list[str] = []
        for payload in facilities:
            lines.append(json.dumps({"index": {"_index": OPENSEARCH_INDEX, "_id": payload["id"]}}))
            lines.append(json.dumps(payload, ensure_ascii=False))
        bulk = client.post(
            "/_bulk?refresh=true",
            content="\n".join(lines) + "\n",
            headers={"content-type": "application/x-ndjson"},
        )
        bulk.raise_for_status()
        body = bulk.json()
        if body.get("errors"):
            raise RuntimeError("OpenSearch bulk indexing reported errors")


def initialize_runtime() -> None:
    global _initialized
    if _initialized or not DATABASE_URL:
        return
    with _lock:
        if _initialized:
            return
        records = _canonical_records()
        _bootstrap_postgres(records)
        _bootstrap_opensearch()
        _initialized = True


def collection(name: str) -> list[dict[str, Any]] | None:
    if not DATABASE_URL:
        return None
    initialize_runtime()
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT payload::text
            FROM factorydb_records
            WHERE collection = %s
            ORDER BY id
            """,
            (name,),
        ).fetchall()
    return [json.loads(row[0]) for row in rows]


def record(collection_name: str, record_id: str) -> dict[str, Any] | None:
    if not DATABASE_URL:
        return None
    initialize_runtime()
    with _connect() as connection:
        row = connection.execute(
            """
            SELECT payload::text
            FROM factorydb_records
            WHERE collection = %s AND id = %s
            """,
            (collection_name, record_id),
        ).fetchone()
    return json.loads(row[0]) if row else None


def facility_rows(
    *,
    country: str | None = None,
    ids: list[str] | None = None,
) -> list[dict[str, Any]] | None:
    if not DATABASE_URL:
        return None
    initialize_runtime()

    clauses = ["collection = %s"]
    params: list[Any] = ["facilities"]
    if country:
        clauses.append("country_code = %s")
        params.append(country.upper())
    if ids is not None:
        if not ids:
            return []
        placeholders = ", ".join(["%s"] * len(ids))
        clauses.append(f"id IN ({placeholders})")
        params.extend(ids)

    sql = (
        "SELECT payload::text FROM factorydb_records WHERE "
        + " AND ".join(clauses)
        + " ORDER BY id"
    )
    with _connect() as connection:
        rows = connection.execute(sql, params).fetchall()
    payloads = [json.loads(row[0]) for row in rows]
    if ids is not None:
        rank = {record_id: position for position, record_id in enumerate(ids)}
        payloads.sort(key=lambda row: rank.get(row["id"], len(rank)))
    return payloads


def search_facility_ids(query: str, limit: int) -> list[str]:
    if not OPENSEARCH_URL:
        return []
    initialize_runtime()
    with httpx.Client(base_url=OPENSEARCH_URL, timeout=10.0) as client:
        response = client.post(
            f"/{OPENSEARCH_INDEX}/_search",
            json={
                "size": limit,
                "_source": False,
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["name^3", "operator^2", "products", "processes"],
                    }
                },
            },
        )
        response.raise_for_status()
        return [hit["_id"] for hit in response.json()["hits"]["hits"]]


def health_status() -> dict[str, str]:
    status = {
        "status": "ok",
        "storage": "jsonl",
        "search": "python",
    }
    if not DATABASE_URL:
        return status

    initialize_runtime()
    with _connect() as connection:
        connection.execute("SELECT 1").fetchone()
    status["storage"] = "postgresql"

    if OPENSEARCH_URL:
        with httpx.Client(base_url=OPENSEARCH_URL, timeout=2.0) as client:
            response = client.get("/_cluster/health")
            response.raise_for_status()
        status["search"] = "opensearch"
    return status
