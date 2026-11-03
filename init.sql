-- ====================================================================
-- База данных исторических данных (PostgreSQL)
-- Дисциплина: Интеграция систем
-- Студент: Баймурзина Элина Данисовна (studentId: 2)
-- ====================================================================

CREATE TABLE IF NOT EXISTS spares_history (
    spare_code        VARCHAR(50) PRIMARY KEY,      -- Код запасной части (SPARE-1, SPARE-2...)
    spare_name        TEXT        NOT NULL,         -- Название детали
    spare_description TEXT,                         -- Описание
    spare_type        VARCHAR(50),                  -- Тип детали (ENGINE, GEARBOX, BRAKE, CLUTCH, BATTERY, TIRE, RADIATOR)
    spare_status      VARCHAR(50),                  -- Статус детали (AVAILABLE, RESERVED, OUT_OF_STOCK, IN_TRANSIT, DAMAGED)
    price             NUMERIC(12, 2),               -- Цена запасной части
    quantity          INTEGER,                      -- Количество на складе
    updated_at        TEXT,                         -- Дата обновления в CMS
    first_seen_at     TIMESTAMPTZ DEFAULT NOW(),    -- Время первой фиксации записи в исторической БД
    last_synced_at    TIMESTAMPTZ DEFAULT NOW(),    -- Время последней синхронизации
    is_deleted        BOOLEAN     DEFAULT FALSE,    -- Флаг удаления детали из CMS (сохранение историчности)
    deleted_at        TIMESTAMPTZ                   -- Дата выбытия из CMS
);

CREATE INDEX IF NOT EXISTS idx_spares_history_deleted ON spares_history (is_deleted);
