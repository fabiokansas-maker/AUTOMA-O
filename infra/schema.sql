-- AUTOMA-O schema
-- Roda automaticamente no primeiro start do Postgres (volume montado em docker-entrypoint-initdb.d)

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE jobs (
    id              BIGSERIAL PRIMARY KEY,
    source          TEXT NOT NULL,                      -- linkedin, gupy, vagas, ...
    external_id     TEXT NOT NULL,                      -- ID nativo da plataforma
    title           TEXT NOT NULL,
    company         TEXT,
    location        TEXT,
    remote          BOOLEAN,
    salary_min      NUMERIC,
    salary_max      NUMERIC,
    salary_currency TEXT,
    posted_at       TIMESTAMPTZ,                        -- quando a plataforma diz que foi postada
    discovered_at   TIMESTAMPTZ NOT NULL DEFAULT now(), -- quando NÓS vimos pela primeira vez
    url             TEXT NOT NULL,
    apply_url       TEXT,
    description     TEXT,
    requirements    JSONB,                              -- [{skill, level, required}]
    raw             JSONB,                              -- payload completo cru pra reprocessar
    UNIQUE (source, external_id)
);
CREATE INDEX jobs_posted_at_idx     ON jobs (posted_at DESC);
CREATE INDEX jobs_discovered_at_idx ON jobs (discovered_at DESC);
CREATE INDEX jobs_title_trgm        ON jobs USING gin (title gin_trgm_ops);

CREATE TABLE match_results (
    job_id              BIGINT PRIMARY KEY REFERENCES jobs(id) ON DELETE CASCADE,
    score               INT NOT NULL CHECK (score BETWEEN 0 AND 100),
    requirements_met    JSONB,                          -- [{skill, evidence}]
    requirements_gap    JSONB,                          -- [{skill, severity}]
    summary             TEXT,
    llm_model           TEXT,
    llm_cost_usd        NUMERIC(10,6),
    evaluated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TYPE application_status AS ENUM (
    'draft', 'pending_user_approval', 'sent', 'failed',
    'responded', 'rejected', 'interview', 'offer'
);

CREATE TABLE applications (
    id              BIGSERIAL PRIMARY KEY,
    job_id          BIGINT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    status          application_status NOT NULL DEFAULT 'draft',
    cover_letter    TEXT,
    cv_version      TEXT,                               -- hash/identificador do CV usado
    submitted_at    TIMESTAMPTZ,
    responded_at    TIMESTAMPTZ,
    response_notes  TEXT,
    error           TEXT,                               -- se falhou ao submeter
    UNIQUE (job_id)
);
CREATE INDEX applications_status_idx ON applications (status, submitted_at DESC);

CREATE TABLE sources_health (
    source          TEXT PRIMARY KEY,
    last_run_at     TIMESTAMPTZ,
    last_success_at TIMESTAMPTZ,
    last_error      TEXT,
    jobs_seen_total BIGINT NOT NULL DEFAULT 0
);

-- View: dashboard diário
CREATE VIEW daily_metrics AS
SELECT
    date_trunc('day', discovered_at)::date AS day,
    source,
    COUNT(*)                                AS jobs_seen,
    COUNT(*) FILTER (WHERE m.score >= 70)   AS jobs_matched,
    COUNT(*) FILTER (WHERE a.status = 'sent') AS applications_sent
FROM jobs j
LEFT JOIN match_results m ON m.job_id = j.id
LEFT JOIN applications  a ON a.job_id = j.id
GROUP BY 1, 2
ORDER BY 1 DESC, 2;
