BEGIN;

DROP SCHEMA IF EXISTS factorydb_projection CASCADE;
CREATE SCHEMA factorydb_projection;

CREATE TABLE factorydb_projection.companies (
    id text PRIMARY KEY,
    legal_name text NOT NULL,
    country_code text NOT NULL,
    website text NOT NULL,
    industry_codes jsonb NOT NULL,
    sources jsonb NOT NULL
);

CREATE TABLE factorydb_projection.facilities (
    id text PRIMARY KEY,
    company_id text NOT NULL REFERENCES factorydb_projection.companies(id),
    name text NOT NULL,
    operator text NOT NULL,
    country_code text NOT NULL,
    facility_type text NOT NULL,
    granularity text NOT NULL,
    status text NOT NULL,
    production_start text,
    products jsonb NOT NULL,
    processes jsonb NOT NULL,
    sources jsonb NOT NULL,
    notes text,
    scale_metrics jsonb NOT NULL
);

WITH company_docs AS (
    SELECT line::jsonb AS doc
    FROM regexp_split_to_table(
        pg_read_file('/tmp/factorydb-companies.jsonl'),
        E'\n'
    ) AS t(line)
    WHERE btrim(line) <> ''
)
INSERT INTO factorydb_projection.companies (
    id,
    legal_name,
    country_code,
    website,
    industry_codes,
    sources
)
SELECT
    doc ->> 'id',
    doc ->> 'legal_name',
    doc ->> 'country_code',
    doc ->> 'website',
    doc -> 'industry_codes',
    doc -> 'sources'
FROM company_docs
ORDER BY doc ->> 'id';

WITH facility_docs AS (
    SELECT line::jsonb AS doc
    FROM regexp_split_to_table(
        pg_read_file('/tmp/factorydb-facilities.jsonl'),
        E'\n'
    ) AS t(line)
    WHERE btrim(line) <> ''
)
INSERT INTO factorydb_projection.facilities (
    id,
    company_id,
    name,
    operator,
    country_code,
    facility_type,
    granularity,
    status,
    production_start,
    products,
    processes,
    sources,
    notes,
    scale_metrics
)
SELECT
    doc ->> 'id',
    doc ->> 'company_id',
    doc ->> 'name',
    doc ->> 'operator',
    doc ->> 'country_code',
    doc ->> 'facility_type',
    doc ->> 'granularity',
    doc ->> 'status',
    NULLIF(doc ->> 'production_start', ''),
    doc -> 'products',
    doc -> 'processes',
    doc -> 'sources',
    NULLIF(doc ->> 'notes', ''),
    COALESCE(doc -> 'scale_metrics', '{}'::jsonb)
FROM facility_docs
ORDER BY doc ->> 'id';

CREATE INDEX facilities_company_id_idx
    ON factorydb_projection.facilities(company_id);
CREATE INDEX facilities_country_code_idx
    ON factorydb_projection.facilities(country_code);
CREATE INDEX facilities_status_idx
    ON factorydb_projection.facilities(status);
CREATE INDEX facilities_products_gin_idx
    ON factorydb_projection.facilities USING gin(products);
CREATE INDEX facilities_processes_gin_idx
    ON factorydb_projection.facilities USING gin(processes);
CREATE INDEX facilities_sources_gin_idx
    ON factorydb_projection.facilities USING gin(sources);

COMMIT;
