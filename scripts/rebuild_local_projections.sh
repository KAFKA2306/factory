#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

INDEX="factorydb-facilities-v1"
LOCAL_DIR="$ROOT/.local/projections"
BULK_FILE="$LOCAL_DIR/facilities.bulk.ndjson"
BULK_RESPONSE="$LOCAL_DIR/opensearch-bulk-response.json"
CREATE_RESPONSE="$LOCAL_DIR/opensearch-create-response.json"

mkdir -p "$LOCAL_DIR"

command -v docker >/dev/null 2>&1 || {
  echo "docker is required" >&2
  exit 1
}
command -v curl >/dev/null 2>&1 || {
  echo "curl is required" >&2
  exit 1
}
command -v uv >/dev/null 2>&1 || {
  echo "uv is required" >&2
  exit 1
}

docker compose up -d postgres opensearch

postgres_ready=0
for _ in $(seq 1 60); do
  if docker compose exec -T postgres pg_isready -U factorydb -d factorydb >/dev/null 2>&1; then
    postgres_ready=1
    break
  fi
  sleep 2
done
if [[ "$postgres_ready" != "1" ]]; then
  echo "PostgreSQL did not become ready" >&2
  exit 1
fi

opensearch_ready=0
for _ in $(seq 1 90); do
  if curl -fsS "http://127.0.0.1:9200" >/dev/null 2>&1; then
    opensearch_ready=1
    break
  fi
  sleep 2
done
if [[ "$opensearch_ready" != "1" ]]; then
  echo "OpenSearch did not become ready" >&2
  exit 1
fi

docker compose exec -T postgres sh -lc \
  'cat /canonical/companies*.jsonl > /tmp/factorydb-companies.jsonl && cat /canonical/facilities/*.jsonl > /tmp/factorydb-facilities.jsonl'

docker compose exec -T postgres \
  psql -v ON_ERROR_STOP=1 -U factorydb -d factorydb \
  < infra/postgres/rebuild.sql

: > "$BULK_FILE"
while IFS= read -r file; do
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    printf '{"index":{"_index":"%s"}}\n%s\n' "$INDEX" "$line" >> "$BULK_FILE"
  done < "$file"
done < <(find data/facilities -type f -name '*.jsonl' -print | sort)

delete_status="$(
  curl -sS \
    -o "$LOCAL_DIR/opensearch-delete-response.json" \
    -w '%{http_code}' \
    -X DELETE "http://127.0.0.1:9200/$INDEX"
)"
if [[ "$delete_status" != "200" && "$delete_status" != "404" ]]; then
  echo "OpenSearch index delete failed with HTTP $delete_status" >&2
  exit 1
fi

curl -fsS \
  -H 'Content-Type: application/json' \
  -X PUT \
  --data-binary @infra/opensearch/facilities-index.json \
  "http://127.0.0.1:9200/$INDEX" \
  > "$CREATE_RESPONSE"

curl -fsS \
  -H 'Content-Type: application/x-ndjson' \
  -X POST \
  --data-binary @"$BULK_FILE" \
  "http://127.0.0.1:9200/_bulk?refresh=true" \
  > "$BULK_RESPONSE"

if ! grep -q '"errors":false' "$BULK_RESPONSE"; then
  cat "$BULK_RESPONSE" >&2
  echo "OpenSearch bulk load reported errors" >&2
  exit 1
fi

canonical_companies="$(
  cat data/companies*.jsonl | sed '/^[[:space:]]*$/d' | wc -l | tr -d '[:space:]'
)"
canonical_facilities="$(
  cat data/facilities/*.jsonl | sed '/^[[:space:]]*$/d' | wc -l | tr -d '[:space:]'
)"
postgres_companies="$(
  docker compose exec -T postgres psql -At -U factorydb -d factorydb \
    -c 'SELECT count(*) FROM factorydb_projection.companies;' | tr -d '[:space:]'
)"
postgres_facilities="$(
  docker compose exec -T postgres psql -At -U factorydb -d factorydb \
    -c 'SELECT count(*) FROM factorydb_projection.facilities;' | tr -d '[:space:]'
)"
opensearch_facilities="$(
  curl -fsS "http://127.0.0.1:9200/$INDEX/_count" |
    uv run --locked python -c 'import json, sys; print(json.load(sys.stdin)["count"])'
)"

if [[ "$canonical_companies" != "$postgres_companies" ]]; then
  echo "company count mismatch: canonical=$canonical_companies postgres=$postgres_companies" >&2
  exit 1
fi
if [[ "$canonical_facilities" != "$postgres_facilities" ]]; then
  echo "facility count mismatch: canonical=$canonical_facilities postgres=$postgres_facilities" >&2
  exit 1
fi
if [[ "$canonical_facilities" != "$opensearch_facilities" ]]; then
  echo "facility count mismatch: canonical=$canonical_facilities opensearch=$opensearch_facilities" >&2
  exit 1
fi

printf 'Canonical companies: %s\n' "$canonical_companies"
printf 'PostgreSQL companies: %s\n' "$postgres_companies"
printf 'Canonical facilities: %s\n' "$canonical_facilities"
printf 'PostgreSQL facilities: %s\n' "$postgres_facilities"
printf 'OpenSearch facilities: %s\n' "$opensearch_facilities"
printf 'PostgreSQL: postgresql://factorydb:factorydb-local@127.0.0.1:5432/factorydb\n'
printf 'OpenSearch: http://127.0.0.1:9200/%s/_search\n' "$INDEX"
