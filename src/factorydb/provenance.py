from __future__ import annotations

from hashlib import sha256
from typing import Any

PROVENANCE_SCHEMA_VERSION = "factorydb.provenance.v1"


def source_id(source_url: str) -> str:
    """Return a stable citation identifier without pretending it is a content hash."""
    digest = sha256(source_url.encode("utf-8")).hexdigest()[:24]
    return f"source:{digest}"


def citation_provenance(
    canonical_id: str,
    citation: dict[str, Any],
) -> dict[str, Any]:
    """Expose what FactoryDB knows and does not know about one source citation.

    Core FactoryDB records retain the official URL, publisher, retrieval date, and
    evidence text. They do not retain the downloaded source body, so `source_hash`
    must remain null instead of hashing citation metadata and mislabelling it as a
    source-content hash. Robotics raw-evidence hashes are maintained by its separate
    evidence ledger.
    """
    url = str(citation["url"])
    observed_at = citation["retrieved_at"]
    return {
        "canonical_id": canonical_id,
        "schema_version": PROVENANCE_SCHEMA_VERSION,
        "data_as_of": None,
        "generated_at": None,
        "source_type": "official_primary",
        "source_id": source_id(url),
        "source_url": url,
        "source_observed_at": observed_at,
        "source_hash": None,
        "freshness": "unknown",
        "stale": None,
        "null_reason": {
            "data_as_of": "source citation does not encode the source data period",
            "generated_at": "response is generated on demand without a persisted generation timestamp",
            "source_hash": "raw source body is not retained by the core citation model",
            "stale": "no source-specific freshness policy is defined",
        },
        "derivation_method": "canonical_record_source_citation",
        "basis": citation["evidence"],
        "provenance": citation,
    }
