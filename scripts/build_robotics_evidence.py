from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data" / "automation.jsonl"
SOURCES = ROOT / "data" / "robotics-sources.json"
DEFAULT_DATA_ROOT = ROOT / "data" / "robotics"
DEFAULT_API_DIR = ROOT / "api" / "v1" / "robotics"
VALID_STATUS = {"planned", "ordered", "installed", "operational", "retired"}
USER_AGENT = "KAFKA2306 factory robotics evidence 137051370+KAFKA2306@users.noreply.github.com"


def canonical_json(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def normalized_text(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="replace")
    text = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return " ".join(html.unescape(text).split())


def validate_ledger(rows: list[dict[str, Any]], sources: dict[str, dict[str, Any]]) -> None:
    required = {
        "company_id", "facility_id", "company", "factory", "country", "equipment_type",
        "status", "deployment_stage", "observed_at", "description", "source_id",
    }
    for row in rows:
        missing = required - row.keys()
        if missing:
            raise ValueError(f"automation record missing {sorted(missing)}: {row}")
        if row["status"] not in VALID_STATUS:
            raise ValueError(f"invalid automation status: {row['status']}")
        if row["source_id"] not in sources:
            raise ValueError(f"unknown source_id {row['source_id']}")
        if "quantity" in row:
            if not isinstance(row["quantity"], (int, float)) or row["quantity"] <= 0:
                raise ValueError(f"invalid disclosed quantity: {row}")
            if not row.get("quantity_unit") or not row.get("quantity_qualifier"):
                raise ValueError(f"quantity lacks unit/qualifier: {row}")
        if row.get("status") == "planned" and row.get("deployment_stage") in {"production", "series_operation"}:
            raise ValueError(f"planned record mislabeled as production: {row}")
    if len({row["company_id"] for row in rows}) < 10:
        raise ValueError("robotics evidence must cover at least 10 companies")
    if len({row["facility_id"] for row in rows}) < 30:
        raise ValueError("robotics evidence must cover at least 30 factories")


def fetch_source(source: dict[str, Any], data_root: Path) -> dict[str, Any]:
    request = urllib.request.Request(
        source["source_url"],
        headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"},
    )
    raw = b""
    content_type = "application/octet-stream"
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            print(f"fetch {source['source_id']} attempt {attempt}/3", flush=True)
            with urllib.request.urlopen(request, timeout=35) as response:
                raw = response.read()
                content_type = response.headers.get_content_type()
            break
        except (TimeoutError, urllib.error.URLError) as exc:
            last_error = exc
            if attempt < 3:
                time.sleep(attempt)
    else:
        raise RuntimeError(f"primary source unavailable: {source['source_id']}") from last_error
    if len(raw) < 800:
        raise ValueError(f"primary source unexpectedly small: {source['source_id']}")
    text = normalized_text(raw).casefold()
    missing = [marker for marker in source["required_markers"] if marker.casefold() not in text]
    if missing:
        raise ValueError(f"source markers missing for {source['source_id']}: {missing}")
    digest = sha256(raw)
    objects = data_root / "raw" / "objects"
    objects.mkdir(parents=True, exist_ok=True)
    suffix = ".html" if content_type in {"text/html", "application/xhtml+xml"} else ".bin"
    path = objects / f"{digest}{suffix}"
    if not path.exists():
        path.write_bytes(raw)
    return {
        "source_id": source["source_id"],
        "publisher": source["publisher"],
        "source_url": source["source_url"],
        "published_at": source["published_at"],
        "sha256": digest,
        "size_bytes": len(raw),
        "content_type": content_type,
        "evidence_path": path.relative_to(data_root).as_posix(),
        "verified_markers": source["required_markers"],
    }


def collect(sources: list[dict[str, Any]], data_root: Path) -> dict[str, Any]:
    manifest = {
        "schema_version": 1,
        "retrieved_at": datetime.now(UTC).isoformat(),
        "sources": [fetch_source(source, data_root) for source in sources],
    }
    payload = canonical_json(manifest)
    manifests = data_root / "raw" / "manifests"
    manifests.mkdir(parents=True, exist_ok=True)
    (manifests / f"{sha256(payload)}.json").write_bytes(payload)
    (data_root / "raw" / "latest-manifest.json").write_bytes(payload)
    return manifest


def verify_manifest(data_root: Path) -> dict[str, Any]:
    manifest = json.loads((data_root / "raw" / "latest-manifest.json").read_text(encoding="utf-8"))
    for source in manifest["sources"]:
        raw = (data_root / source["evidence_path"]).read_bytes()
        if sha256(raw) != source["sha256"]:
            raise ValueError(f"raw hash mismatch: {source['source_id']}")
    return manifest


def load_core_ids() -> tuple[set[str], set[str]]:
    company_ids: set[str] = set()
    for path in sorted((ROOT / "data").glob("companies*.jsonl")):
        for row in load_jsonl(path):
            company_ids.add(row["id"])
    facility_ids: set[str] = set()
    for path in sorted((ROOT / "data" / "facilities").glob("*.jsonl")):
        for row in load_jsonl(path):
            facility_ids.add(row["id"])
    return company_ids, facility_ids


def build_views(rows: list[dict[str, Any]], manifest: dict[str, Any], api_dir: Path) -> dict[str, Any]:
    source_map = {row["source_id"]: row for row in manifest["sources"]}
    company_ids, facility_ids = load_core_ids()
    enriched = []
    for row in rows:
        source = source_map[row["source_id"]]
        enriched.append({
            **row,
            "source_publisher": source["publisher"],
            "source_url": source["source_url"],
            "source_published_at": source["published_at"],
            "source_sha256": source["sha256"],
            "source_evidence_path": source["evidence_path"],
            "source_retrieved_at": manifest["retrieved_at"],
            "factorydb_core_company_match": row["company_id"] in company_ids,
            "factorydb_core_facility_match": row["facility_id"] in facility_ids,
        })

    by_company: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_country: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_status: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_equipment: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in enriched:
        by_company[row["company_id"]].append(row)
        by_country[row["country"]].append(row)
        by_status[row["status"]].append(row)
        by_equipment[row["equipment_type"]].append(row)

    coverage = {
        "observation_count": len(enriched),
        "company_count": len({row["company_id"] for row in enriched}),
        "factory_count": len({row["facility_id"] for row in enriched}),
        "country_count": len({row["country"] for row in enriched}),
        "primary_source_count": len(manifest["sources"]),
        "core_company_match_count": len({row["company_id"] for row in enriched if row["factorydb_core_company_match"]}),
        "core_factory_match_count": len({row["facility_id"] for row in enriched if row["factorydb_core_facility_match"]}),
        "status_counts": dict(sorted(Counter(row["status"] for row in enriched).items())),
        "equipment_type_counts": dict(sorted(Counter(row["equipment_type"] for row in enriched).items())),
    }
    identity = {
        "schema_version": 1,
        "core_company_matches": sorted({row["company_id"] for row in enriched if row["factorydb_core_company_match"]}),
        "core_factory_matches": sorted({row["facility_id"] for row in enriched if row["factorydb_core_facility_match"]}),
        "companies_not_in_core": sorted({row["company_id"] for row in enriched if not row["factorydb_core_company_match"]}),
        "factories_not_in_core": sorted({row["facility_id"] for row in enriched if not row["factorydb_core_facility_match"]}),
        "rule": "A false core match is explicit; robotics identity is never silently claimed to exist in the FactoryDB core tables.",
    }
    api_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "records.json": {"schema_version": 1, "records": enriched},
        "by-company.json": {"schema_version": 1, "groups": dict(sorted(by_company.items()))},
        "by-country.json": {"schema_version": 1, "groups": dict(sorted(by_country.items()))},
        "by-status.json": {"schema_version": 1, "groups": dict(sorted(by_status.items()))},
        "by-equipment-type.json": {"schema_version": 1, "groups": dict(sorted(by_equipment.items()))},
        "identity-coverage.json": identity,
        "provenance.json": manifest,
    }
    for name, payload in outputs.items():
        (api_dir / name).write_bytes(canonical_json(payload))
    index = {
        "schema_version": 1,
        "dataset": "Factory-level robotics and automation primary evidence",
        "retrieved_at": manifest["retrieved_at"],
        "coverage": coverage,
        "views": {name.removesuffix(".json").replace("-", "_"): name for name in outputs},
        "rules": [
            "planned, ordered, installed and operational are distinct states",
            "quantities are present only when explicitly disclosed by the primary source",
            "group-level robot totals are not allocated to individual factories",
            "FactoryDB core identity matches are explicit and unmatched robotics identities remain visible",
        ],
    }
    (api_dir / "index.json").write_bytes(canonical_json(index))
    print(json.dumps(coverage, sort_keys=True))
    return index


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--api-dir", type=Path, default=DEFAULT_API_DIR)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    rows = load_jsonl(LEDGER)
    source_doc = json.loads(SOURCES.read_text(encoding="utf-8"))
    source_list = source_doc["sources"]
    source_map = {row["source_id"]: row for row in source_list}
    if len(source_map) != len(source_list):
        raise ValueError("duplicate robotics source_id")
    validate_ledger(rows, source_map)
    manifest = verify_manifest(args.data_root) if args.offline else collect(source_list, args.data_root)
    build_views(rows, manifest, args.api_dir)


if __name__ == "__main__":
    main()
