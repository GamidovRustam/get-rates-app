PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS observations (
    series_id   TEXT NOT NULL,
    obs_date    TEXT NOT NULL,  -- YYYY-MM-DD
    value       REAL NOT NULL,
    received_at TEXT NOT NULL,
    PRIMARY KEY (series_id, obs_date)
);

CREATE INDEX IF NOT EXISTS ix_observations_date ON observations (obs_date);

