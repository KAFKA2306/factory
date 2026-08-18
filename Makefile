COVERAGE_REPORT ?= /tmp/factorydb-coverage-report.json

.PHONY: bootstrap check

bootstrap:
	uv sync --locked --extra dev
	@node --version

check:
	uv lock --check
	uv run --locked --extra dev ruff format --check src tests scripts
	uv run --locked --extra dev ruff check .
	uv run --locked --extra dev pyrefly check
	uv run --locked --extra dev pytest
	node --input-type=module --check < web/app.js
	node --check web/url-state.mjs
	node --test tests/web-url-state.test.mjs
	uv run --locked --extra dev python -m factorydb.validate
	uv run --locked --extra dev python -m factorydb.coverage_validation > "$(COVERAGE_REPORT)"
	python -m json.tool "$(COVERAGE_REPORT)" > /dev/null
	uv run --locked --extra dev python scripts/build_catalog.py
	test -s web/catalog.json
	python -m json.tool web/catalog.json > /dev/null
