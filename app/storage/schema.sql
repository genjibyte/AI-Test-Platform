CREATE TABLE IF NOT EXISTS jobs (
    id                TEXT PRIMARY KEY,
    git_url           TEXT NOT NULL,
    branch            TEXT,
    commit_sha        TEXT,
    status            TEXT NOT NULL,
    error             TEXT,
    build_outcome     TEXT,
    project_json      TEXT,
    test_result_json  TEXT,
    coverage_json     TEXT,
    stages_json       TEXT,
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at);
