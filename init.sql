CREATE TABLE IF NOT EXISTS spares_history (
    id             VARCHAR(50) PRIMARY KEY,
    name           TEXT        NOT NULL,
    description    TEXT,
    type           VARCHAR(50), 
    status         VARCHAR(50),
    price          NUMERIC(12, 2),
    quantity       INTEGER, 
    updated_at     TEXT, 
    last_synced_at TIMESTAMPTZ DEFAULT NOW(),
    is_deleted     BOOLEAN     DEFAULT FALSE, 
    deleted_at     TIMESTAMPTZ 
);

CREATE INDEX IF NOT EXISTS idx_spares_history_deleted ON spares_history (is_deleted);
