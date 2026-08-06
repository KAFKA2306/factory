#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "financials.jsonl"
USER_AGENT = "factorydb/0.1 contact=https://github.com/KAFKA2306/factory"
ISSUERS = [{"company_id": "company:toyota-motor-corporation", "cik": "0001094517", "currency": "JPY"}]
CONCEPTS = {
    "assets": ["Assets"],
    "liabilities": ["Liabilities"],
    "equity": ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"],
}


def fetch(cik: str) -> dict:
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=90) as response:
        return json.load(response)


def latest_fact(payload: dict, names: list[str], currency: str) -> dict | None:
    facts = payload.get("facts", {})
    for taxonomy in ("ifrs-full", "us-gaap"):
        concepts = facts.get(taxonomy, {})
        for name in names:
            concept = concepts.get(name)
            if not concept:
                continue
            units = concept.get("units", {})
            candidates = units.get(currency, []) or next(iter(units.values()), [])
            candidates = [
                row for row in candidates
                if row.get("form") in {"20-F", "10-K", "6-K"} and row.get("val") is not None
            ]
            if candidates:
                row = sorted(candidates, key=lambda x: (x.get("filed", ""), x.get("end", "")))[-1]
                return {"value": row["val"], "period_end": row.get("end"), "filed": row.get("filed"), "concept": f"{taxonomy}:{name}"}
    return None


def main() -> None:
    existing = [json.loads(line) for line in OUT.read_text(encoding="utf-8").splitlines() if line]
    existing = [row for row in existing if not row["id"].startswith("financial:sec:")]
    generated = []
    for issuer in ISSUERS:
        payload = fetch(issuer["cik"])
        metrics = {}
        period_end = None
        for key, names in CONCEPTS.items():
            fact = latest_fact(payload, names, issuer["currency"])
            if fact:
                metrics[key] = fact["value"]
                period_end = max(filter(None, [period_end, fact["period_end"]]))
        if metrics and period_end:
            generated.append({
                "id": f"financial:sec:{issuer['cik']}:{period_end}",
                "company_id": issuer["company_id"],
                "period_end": period_end,
                "fiscal_year": period_end[:4],
                "accounting_standard": "IFRS",
                "currency": issuer["currency"],
                "scale": "unit",
                "metrics": metrics,
                "sources": [{
                    "publisher": "U.S. Securities and Exchange Commission",
                    "url": f"https://data.sec.gov/api/xbrl/companyfacts/CIK{issuer['cik']}.json",
                    "retrieved_at": date.today().isoformat(),
                    "evidence": "SEC EDGAR Companyfacts XBRL API; latest filed annual or current facts",
                }],
            })
    OUT.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in existing + generated),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
