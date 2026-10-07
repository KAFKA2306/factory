from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import urlopen


def get(path: str, params: dict[str, str] | None = None):
    query = f"?{urlencode(params)}" if params else ""
    with urlopen(f"http://127.0.0.1:8000{path}{query}", timeout=10) as response:
        return json.load(response)


health = get("/health")
assert health == {"status": "ok", "storage": "postgresql", "search": "opensearch"}

companies = get("/v1/companies", {"country": "JP", "limit": "20"})
assert any(row["id"] == "company:toyota-motor-corporation" for row in companies)

facilities = get("/v1/facilities", {"query": "Toyota", "limit": "20"})
assert any(row["id"] == "facility:toyota-motomachi" for row in facilities)

facility = get("/v1/facilities/toyota-motomachi")
assert facility["id"] == "facility:toyota-motomachi"

print(
    json.dumps(
        {
            "health": health,
            "company_hits": len(companies),
            "facility_hits": len(facilities),
            "facility": facility["id"],
        },
        ensure_ascii=False,
    )
)
