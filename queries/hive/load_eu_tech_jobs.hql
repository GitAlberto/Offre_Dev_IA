DROP VIEW IF EXISTS eu_tech_jobs_france;
DROP VIEW IF EXISTS offres_historique;
DROP TABLE IF EXISTS eu_tech_jobs_raw;

CREATE EXTERNAL TABLE eu_tech_jobs_raw (
    id STRING,
    company_slug STRING,
    title STRING,
    url STRING,
    location STRING,
    countries ARRAY<STRING>,
    remote_policy STRING,
    seniority STRING,
    role_family STRING,
    salary_min DOUBLE,
    salary_max DOUBLE,
    salary_currency STRING,
    salary_period STRING,
    stack ARRAY<STRING>,
    posted_at STRING,
    source STRING
)
STORED AS PARQUET
LOCATION 'file:///opt/hive/ext-data/eu_tech_jobs/latest';

CREATE VIEW eu_tech_jobs_france AS
SELECT
    id,
    company_slug,
    title,
    url,
    location,
    countries,
    remote_policy,
    seniority,
    role_family,
    salary_min,
    salary_max,
    salary_currency,
    salary_period,
    stack,
    posted_at,
    source
FROM eu_tech_jobs_raw
WHERE array_contains(countries, 'FR')
   OR lower(location) LIKE '%france%'
   OR lower(location) LIKE '%paris%';

CREATE VIEW offres_historique AS
SELECT
    id,
    title,
    location AS region,
    remote_policy,
    seniority,
    role_family,
    salary_min,
    salary_max,
    salary_currency,
    salary_period,
    posted_at,
    source,
    competence
FROM eu_tech_jobs_france
LATERAL VIEW OUTER explode(stack) competences AS competence;
