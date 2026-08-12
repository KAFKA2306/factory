# AGENTS.md — FactoryDB BFV Kernel

> **Bound the work. Falsify necessity. Verify the Contract. Stop at the Fixed Point.**

This file applies to the entire repository. Treat `docs/data-policy.md` and `docs/architecture.md` as the detailed source of truth; this file defines the execution contract for agents changing FactoryDB.

## 1. Contract

Before changing files, define the smallest Contract that proves the requested outcome.

```text
Contract = Requested Outcome + smallest sufficient Acceptance Criteria
```

The Contract is both the minimum required result and the maximum allowed scope. Resolve ambiguity with the narrowest interpretation consistent with the issue, repository policy, and verified evidence.

### Functional Contract

A change must preserve the repository's functional truth model:

- `data/*.jsonl` and `data/countries/*.jsonl` are canonical data; `web/catalog.json` is generated output.
- Every accepted company, facility, asset, investment, financial record, or no-factory resolution must retain its source URL, publisher, retrieval date, and evidence text.
- Use official primary sources allowed by `docs/data-policy.md`. Do not add fabricated, sample, placeholder, inferred, or secondary-source-only facts.
- Preserve the distinction between a physical plant, a manufacturing company, and a site group.
- The current factory-country coverage scope is capped at **179 countries/territories**. Do not add coverage solely to reduce `coverage_missing_countries`.
- Expansion beyond the 179-country cap requires an explicit scope revision in a dedicated issue or PR; it is not routine maintenance.

### Non-Functional Contract

A change must keep the data and audits reproducible:

- Provenance must be recoverable from the committed canonical record without relying on chat history or uncommitted notes.
- Generated artifacts must be reproducible from committed canonical inputs with `python scripts/build_catalog.py`.
- Validation must be deterministic for a fixed checkout and must fail closed on schema, reference-integrity, duplicate-ID, forbidden-data, or scope-cap errors.
- Existing public API and generated-catalog semantics must not be weakened merely to make a check pass.
- Minimize unrelated file churn so that a reviewer can attribute every changed claim to the Contract.

### Operational Contract

A change must remain auditable, observable, and reversible:

- Work through Git commits and pull requests; do not hide required fixes behind ignored CI failures.
- Keep source evidence in the canonical record and verification evidence in CI/PR history.
- Preserve CI output for lint, tests, repository validation, coverage-state validation, catalog generation, and JSON validation.
- A rollback must be possible by reverting the change commit without hand-editing generated or remote state. Rebuild `web/catalog.json` from the reverted canonical checkout when needed.
- PR #11 is the canonical continuation line for this checkpoint. Its completion is governed by the scoped Contract and CI, not by driving country coverage to 249.

## 2. Falsification

For every proposed change, state the claim it is intended to satisfy and try deleting the change mentally or in the diff.

Keep a change only when removing it would make the Contract unprovable, break an existing verified invariant, or remove required evidence. Delete speculative abstractions, duplicate data, cosmetic churn, and unrelated cleanup.

For factual data claims, falsification means checking the cited official source against the exact legal entity, facility, product/process, status, date, and quantitative value being committed. If the source does not support the claim, reject the record or narrow the claim.

## 3. Verification

After changes, run the complete repository verification set applicable to the active implementation branch:

```bash
ruff check .
pytest
python -m factorydb.validate
python -m factorydb.coverage_validation
python scripts/build_catalog.py
test -s web/catalog.json
python -m json.tool web/catalog.json > /dev/null
```

Do not substitute a partial check for a required check. If a check cannot run, record the exact blocker and do not claim the affected Contract clause is verified.

## 4. Acceptance Evidence

Issue #5's repository-wide acceptance criteria are interpreted as follows:

1. **Factory data provenance is reproducible** — canonical records carry source URL, publisher, retrieval date, and evidence, and derived catalog data can be rebuilt from the checkout.
2. **Audits are replayable** — the verification commands above can be rerun against the same commit and canonical data.
3. **Rollback is possible** — changes are isolated in Git history and generated output is rebuilt from canonical data rather than treated as an independent source of truth.
4. **Observability is preserved** — CI and coverage reports expose validation failures and the current coverage state without converting uncovered countries into an automatic backlog.

## 5. Fixed Point

Stop when all Contract clauses have evidence, every surviving diff hunk is necessary to prove one of them, required verification passes, and deleting any remaining change would break that proof.

Do not continue with opportunistic improvements after the fixed point. Open a separate issue for distinct work.
