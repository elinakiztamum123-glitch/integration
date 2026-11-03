"""
Интеграционное приложение: Синхронизация CMS, БД исторических данных и Report API
Дисциплина: Интеграция систем
Студент: Баймурзина Элина Данисовна
studentId: 2
Логин: student2
"""

import os
import sys
import json
import sqlite3
import base64
import urllib.request
import urllib.error
from datetime import datetime, timezone

API_BASE = os.getenv("COURSE_API_BASE_URL", "http://77.67.89.207:8080")
USERNAME = os.getenv("COURSE_API_USERNAME", "student2")
PASSWORD = os.getenv("COURSE_API_PASSWORD", "Yg4@;{9iW=d)")
STUDENT_ID = int(os.getenv("COURSE_STUDENT_ID", "2"))
DB_PATH = os.getenv("SQLITE_DB_PATH", "spares_history.db")

CSV_FIELDS = [
    "spareCode",
    "spareName",
    "spareDescription",
    "spareType",
    "spareStatus",
    "price",
    "quantity",
    "updatedAt"
]

def init_db(conn):
    """Инициализация схемы БД исторических данных (SQLite / PostgreSQL)"""
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS spares_history (
        spare_code        TEXT PRIMARY KEY,
        spare_name        TEXT NOT NULL,
        spare_description TEXT,
        spare_type        TEXT,
        spare_status      TEXT,
        price             TEXT,
        quantity          INTEGER,
        updated_at        TEXT,
        first_seen_at     TEXT,
        last_synced_at    TEXT,
        is_deleted        INTEGER DEFAULT 0,
        deleted_at        TEXT
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_spares_deleted ON spares_history (is_deleted)")
    conn.commit()

def get_auth_token():
    """Получение Bearer токена авторизации (POST /auth/token)"""
    url = f"{API_BASE}/auth/token"
    payload = json.dumps({"username": USERNAME, "password": PASSWORD}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["token"]
    except urllib.error.HTTPError as e:
        print(f"Ошибка получения токена: {e.code} {e.read().decode('utf-8')}")
        raise

def fetch_cms_spares():
    """Поток данных №1: Получение деталей из CMS API с поддержкой пагинации"""
    credentials = f"{USERNAME}:{PASSWORD}"
    encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Accept": "application/json"
    }

    all_spares = []
    page = 0
    size = 10

    while True:
        url = f"{API_BASE}/cms/spares?page={page}&size={size}"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if not data:
                    break
                all_spares.extend(data)
                if len(data) < size:
                    break
                page += 1
        except urllib.error.HTTPError as e:
            print(f"Ошибка запроса к CMS (страница {page}): {e.code}")
            raise

    return all_spares

def sync_spares_to_db(conn, cms_spares):
    """
    Синхронизация CMS -> БД исторических данных:
    - Новые детали вставляются
    - Существующие детали обновляются
    - Пропавшие из CMS детали сохраняются в БД с флагом is_deleted = 1 (историчность)
    """
    cur = conn.cursor()
    now_str = datetime.now(timezone.utc).isoformat()

    cms_map = {item["spareCode"]: item for item in cms_spares}

    cur.execute("SELECT spare_code, spare_name, spare_description, spare_type, spare_status, price, quantity, updated_at, is_deleted FROM spares_history")
    db_rows = {row[0]: row for row in cur.fetchall()}

    inserted = 0
    updated = 0
    deleted = 0

    for code, item in cms_map.items():
        if code not in db_rows:
            cur.execute("""
            INSERT INTO spares_history (
                spare_code, spare_name, spare_description, spare_type,
                spare_status, price, quantity, updated_at,
                first_seen_at, last_synced_at, is_deleted, deleted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL)
            """, (
                item.get("spareCode"),
                item.get("spareName"),
                item.get("spareDescription"),
                item.get("spareType"),
                item.get("spareStatus"),
                str(item.get("price")),
                item.get("quantity"),
                item.get("updatedAt"),
                now_str,
                now_str
            ))
            inserted += 1
        else:
            cur.execute("""
            UPDATE spares_history SET
                spare_name = ?,
                spare_description = ?,
                spare_type = ?,
                spare_status = ?,
                price = ?,
                quantity = ?,
                updated_at = ?,
                last_synced_at = ?,
                is_deleted = 0,
                deleted_at = NULL
            WHERE spare_code = ?
            """, (
                item.get("spareName"),
                item.get("spareDescription"),
                item.get("spareType"),
                item.get("spareStatus"),
                str(item.get("price")),
                item.get("quantity"),
                item.get("updatedAt"),
                now_str,
                code
            ))
            updated += 1

    # Обработка удаленных деталей (детали в БД, которых больше нет в CMS)
    for code in db_rows:
        if code not in cms_map and db_rows[code][8] == 0:
            cur.execute("""
            UPDATE spares_history SET
                is_deleted = 1,
                deleted_at = ?,
                last_synced_at = ?
            WHERE spare_code = ?
            """, (now_str, now_str, code))
            deleted += 1

    conn.commit()
    print(f"Синхронизация с БД завершена: Добавлено: {inserted}, Обновлено: {updated}, Помечено удаленными: {deleted}")

def natural_sort_key(code):
    import re
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', code)]

def escape_csv_val(val):
    if val is None:
        return ""
    s = str(val)
    if any(c in s for c in [';', '"', '\r', '\n']):
        return '"' + s.replace('"', '""') + '"'
    return s

def generate_csv_report(conn):
    """
    Поток данных №2: Формирование CSV файла из БД исторических данных.
    Требования к формату:
    - Без заголовка
    - Разделитель ';'
    - Кодировка UTF-8 (без BOM)
    - Перенос строки '\n'
    - Колонки: spareCode;spareName;spareDescription;spareType;spareStatus;price;quantity;updatedAt
    """
    cur = conn.cursor()
    cur.execute("""
    SELECT spare_code, spare_name, spare_description, spare_type,
           spare_status, price, quantity, updated_at
    FROM spares_history
    WHERE is_deleted = 0
    """)
    rows = cur.fetchall()

    sorted_rows = sorted(rows, key=lambda r: natural_sort_key(r[0]))

    lines = []
    for r in sorted_rows:
        line = ";".join(escape_csv_val(val) for val in r)
        lines.append(line)

    csv_text = "\n".join(lines)
    return csv_text.encode("utf-8"), len(lines)

def send_report(token, csv_bytes):
    """Отправка сформированного CSV в Report API (POST /report/csv)"""
    url = f"{API_BASE}/report/csv"
    req = urllib.request.Request(
        url,
        data=csv_bytes,
        headers={
            "Content-Type": "text/csv; charset=utf-8",
            "Authorization": f"Bearer {token}"
        }
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def check_results():
    """Проверка оценки в системе (GET /students/{studentId}/results)"""
    url = f"{API_BASE}/students/{STUDENT_ID}/results"
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read().decode("utf-8"))

def main():
    print("=" * 60)
    print("Интеграционное приложение: Синхронизация CMS, БД и Report API")
    print(f"Студент: Баймурзина Элина Данисовна (ID: {STUDENT_ID}, login: {USERNAME})")
    print("=" * 60)

    # 1. Инициализация БД
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    # 2. Поток 1: CMS API -> БД исторических данных
    print("\n[Шаг 1] Получение деталей из CMS API...")
    cms_spares = fetch_cms_spares()
    print(f"Получено деталей из CMS: {len(cms_spares)}")

    print("\n[Шаг 2] Синхронизация с БД исторических данных...")
    sync_spares_to_db(conn, cms_spares)

    # 3. Поток 2: БД -> CSV -> Report API
    print("\n[Шаг 3] Формирование CSV отчета из БД...")
    csv_bytes, row_count = generate_csv_report(conn)
    print(f"Сформирован CSV: {row_count} строк, {len(csv_bytes)} байт")

    with open("report_latest.csv", "wb") as f:
        f.write(csv_bytes)
    print("Файл сохранен: report_latest.csv")

    print("\n[Шаг 4] Получение токена авторизации...")
    token = get_auth_token()
    print(f"Токен получен: {token[:8]}...")

    print("\n[Шаг 5] Отправка отчета в Report API...")
    report_response = send_report(token, csv_bytes)
    print("Ответ Report API:")
    print(json.dumps(report_response, ensure_ascii=False, indent=2))

    print("\n[Шаг 6] Проверка итоговой оценки студента...")
    result = check_results()
    print("Результат проверки:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("\n" + "=" * 60)
    print(f"ИТОГОВАЯ ОЦЕНКА: {result.get('result')} / 5")
    print(f"СООБЩЕНИЕ СИНХРОНИЗАЦИИ: {result.get('lastSyncMessage')}")
    print("=" * 60)

    conn.close()

if __name__ == "__main__":
    main()
