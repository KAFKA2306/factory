#!/usr/bin/env python3
from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
COUNTRY_DIR = ROOT / "data" / "countries"
INDICATORS = {
    "manufacturing_value_added_usd": "NV.IND.MANF.CD",
    "manufacturing_value_added_pct_gdp": "NV.IND.MANF.ZS",
    "industry_value_added_usd": "NV.IND.TOTL.CD",
    "population": "SP.POP.TOTL",
}
USER_AGENT = "factorydb/0.1 contact=https://github.com/KAFKA2306/factory"


def get_json(url: str) -> object:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=60) as response:
        return json.load(response)


def latest_value(iso2: str, indicator: str) -> dict | None:
    query = urlencode({"format": "json", "mrnev": 1, "per_page": 5})
    url = f"https://api.worldbank.org/v2/country/{iso2}/indicator/{indicator}?{query}"
    payload = get_json(url)
    if not isinstance(payload, list) or len(payload) < 2 or not payload[1]:
        return None
    row = next((item for item in payload[1] if item.get("value") is not None), None)
    if row is None:
        return None
    return {"value": row["value"], "year": int(row["date"]), "indicator": indicator, "source_url": url}


def main() -> None:
    files = sorted(COUNTRY_DIR.glob("*.jsonl"))
    rows_by_file = {
        path: [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
        for path in files
    }
    rows = [row for file_rows in rows_by_file.values() for row in file_rows]
    for index, row in enumerate(rows, 1):
        values = {}
        for key, indicator in INDICATORS.items():
            try:
                item = latest_value(row["iso2"], indicator)
            except Exception as exc:
                print(f"WARN {row['iso2']} {indicator}: {exc}")
                item = None
            if item:
                values[key] = item
            time.sleep(0.05)
        row["indicators"] = values
        row["indicator_source"] = {
            "publisher": "World Bank",
            "url": "https://api.worldbank.org/v2/",
            "retrieved_at": date.today().isoformat(),
            "evidence": "World Development Indicators API; latest non-null observation per indicator",
        }
        print(f"{index}/{len(rows)} {row['iso2']} {len(values)}")
    for path, file_rows in rows_by_file.items():
        path.write_text(
            "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in file_rows),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
