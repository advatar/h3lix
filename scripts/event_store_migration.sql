-- Minimal table for Postgres/Timescale event storage
CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    participant_id TEXT NOT NULL,
    stream_type TEXT NOT NULL,
    aligned_timestamp TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ NOT NULL,
    record JSONB NOT NULL
);

-- Optional Timescale hypertable conversion (requires Timescale extension)
-- SELECT create_hypertable('events', by_range('aligned_timestamp'), if_not_exists => TRUE);
