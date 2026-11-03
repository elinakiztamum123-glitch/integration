-- Схема базы данных исторических данных (PostgreSQL)
-- Обеспечивает сохранение историчности (мягкое удаление выбывших из CMS деталей через is_deleted)

CREATE TABLE IF NOT EXISTS spares_history (
    id             VARCHAR(50) PRIMARY KEY,      -- Идентификатор spareCode
    name           TEXT        NOT NULL,         -- Название spareName
    description    TEXT,                         -- Описание spareDescription
    type           VARCHAR(50),                  -- Тип spareType
    status         VARCHAR(50),                  -- Статус spareStatus
    price          NUMERIC(12, 2),               -- Цена price
    quantity       INTEGER,                      -- Остаток на складе quantity
    updated_at     TEXT,                         -- Дата обновления в CMS (updatedAt)
    last_synced_at TIMESTAMPTZ DEFAULT NOW(),    -- Время последней успешной синхронизации
    is_deleted     BOOLEAN     DEFAULT FALSE,    -- Флаг выбытия детали из CMS
    deleted_at     TIMESTAMPTZ                   -- Время выбытия детали
);

CREATE INDEX IF NOT EXISTS idx_spares_history_deleted ON spares_history (is_deleted);

