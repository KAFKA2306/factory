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

## Autonomous execution

1. Re-read current `main`, README, open Issues/PRs, canonical factory/robotics data, workflows/tests and public interfaces before choosing work.
2. Continue one existing canonical workline for the same outcome before creating another collector, dataset, branch or Issue.
3. Prefer newly verified factory/robotics records, identity/status corrections, reproducible adoption/coverage views, public task completion, then simplification that removes duplicate/manual work.
4. Require source, identity, status and period comparability before aggregating. Announced, ordered, installed, commissioned and operating automation are distinct states.
5. Cross-repository ARK or investment forecast comparison belongs in `investor2`; do not copy forecast authority here or infer installed fleets/productivity/ROI from announcements.
6. Stop at the fixed point. If no new primary evidence or executable user/data delta exists, make no repository change.

Do not execute trades, procurement, transfers or account actions. Unobserved source, CI, deployment or real-world operational outcomes remain unverified.

## Merge and release are separate

### PR merge conditions

A PR may merge when the bounded repository-local change is correct on the exact reviewed revision: canonical data/source rules hold, relevant validation/tests pass, generated catalog/output is reproducible when affected, and no unresolved review or correctness blocker remains.

A production Pages URL, a future factory/robotics observation, live source refresh after merge, or real-world installation/operation evidence is **not** a merge condition unless the PR specifically changes the release mechanism and pre-merge validation of that mechanism belongs to the bounded change.

### Product/data release conditions

Release is a separate post-merge decision. Treat factory data/catalog/API as released only after the merged `main` revision is read back and every release surface in scope is actually verified, including generated catalog consistency, REST/MCP/public Pages when applicable, deployment identity, fresh source acquisition when required, and rollback/rebuild path.

A merged PR does not prove production release or real-world adoption. A release/deployment/source blocker may block release without invalidating a correctly merged repository change. Report merge and release independently.

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

These checks are merge evidence for repository correctness. Production/public read-back is separate release evidence. Do not weaken validation to make a change pass. If a required check cannot run, record the blocker and leave that result unverified.

Keep pull requests focused, keep generated output reproducible from canonical inputs, and prefer deleting duplication over adding another source of truth.

## Completion report

Report verified factory/robotics evidence or user capability Before -> After, primary/canonical evidence, Issue/PR/commit/check evidence, then report `merged` and `released` separately with direct evidence for each. Include duplicate/manual work removed and the remaining verified blocker.