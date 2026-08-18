# AGENTS.md

This file applies to the whole repository. Use it as a short index; detailed rules live in the repository itself.

## Read first

- `README.md` — product scope, current interfaces, and repository map.
- `docs/data-policy.md` — allowed sources and data-quality rules.
- `docs/architecture.md` — canonical data, generated outputs, REST, MCP, and Pages boundaries.

## Preserve these invariants

- `data/*.jsonl` and `data/countries/*.jsonl` are canonical; `web/catalog.json` is generated.
- Use official primary sources allowed by `docs/data-policy.md`. Do not add fabricated, placeholder, inferred, or secondary-source-only facts.
- Keep physical plants, manufacturing companies, and site groups as distinct entities.
- Keep `unknown` / unresolved coverage distinct from `verified_no_qualifying_factory`.
- The current factory-country coverage scope is capped at 179 countries/territories unless a dedicated scope change explicitly revises it.
- Keep source URL, publisher, retrieval date, and evidence attached to accepted factual records.
- REST, MCP, and the public catalog must read the same canonical data rather than creating separate truths.

## Verify changes

Run the checks that apply to the change; repository CI runs the full set:

```bash
ruff check .
pytest
python -m factorydb.validate
python -m factorydb.coverage_validation
python scripts/build_catalog.py
test -s web/catalog.json
python -m json.tool web/catalog.json > /dev/null
```

Do not weaken validation to make a change pass. If a required check cannot run, record the blocker and leave that result unverified.

Keep pull requests focused, keep generated output reproducible from canonical inputs, and prefer deleting duplication over adding another source of truth.
