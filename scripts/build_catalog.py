from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from factorydb.store import coverage, load_all


def dump(rows):
    return [row.model_dump(mode="json") if hasattr(row, "model_dump") else row for row in rows]


def main() -> None:
    data = load_all()
    payload = {
        "generated_from": "repository JSONL",
        "coverage": coverage(data),
        "countries": dump(data["countries"]),
        "companies": dump(data["companies"]),
        "facilities": dump(data["facilities"]),
        "coverage_resolutions": dump(data["coverage_resolutions"]),
        "assets": dump(data["assets"]),
        "investments": dump(data["investments"]),
        "financials": dump(data["financials"]),
        "ontology": data["ontology"],
    }
    (ROOT / "web" / "catalog.json").write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
