CREATE TABLE IF NOT EXISTS offres (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    title TEXT,
    company TEXT,
    company_name TEXT,
    location TEXT,
    location_label TEXT,
    contract_type TEXT,
    published_at_raw TEXT,
    published_at TIMESTAMPTZ,
    application_deadline_raw TEXT,
    application_deadline TIMESTAMPTZ,
    salary TEXT,
    salary_min TEXT,
    salary_max TEXT,
    salary_is_predicted INTEGER,
    url TEXT,
    application_url TEXT,
    description TEXT,
    skills JSONB NOT NULL DEFAULT '[]'::jsonb,
    job_family TEXT,
    job_label TEXT,
    job_code TEXT,
    public_sector TEXT,
    category TEXT,
    telework TEXT,
    contract_time TEXT,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_offres_source_external_id UNIQUE (source, external_id)
);

ALTER TABLE offres
    ADD COLUMN IF NOT EXISTS salary_is_predicted INTEGER;

ALTER TABLE offres
    ADD COLUMN IF NOT EXISTS contract_time TEXT;

CREATE INDEX IF NOT EXISTS idx_offres_source
    ON offres(source);

CREATE INDEX IF NOT EXISTS idx_offres_published_at
    ON offres(published_at DESC);

CREATE INDEX IF NOT EXISTS idx_offres_contract_type
    ON offres(contract_type);

CREATE INDEX IF NOT EXISTS idx_offres_company_name
    ON offres(company_name);
