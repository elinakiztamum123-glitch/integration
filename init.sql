-- Инициализация базы данных исторических данных
CREATE TABLE IF NOT EXISTS spares (
    spare_code      VARCHAR(50) PRIMARY KEY,
    spare_name      VARCHAR(255),
    spare_description TEXT,
    spare_type      VARCHAR(50),
    spare_status    VARCHAR(50),
    price           VARCHAR(50),
    quantity        INTEGER,
    updated_at      VARCHAR(100),
    synced_at       TIMESTAMP DEFAULT NOW()
);
