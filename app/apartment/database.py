import os

import psycopg2
from psycopg2.extras import RealDictCursor


def connect():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "postgres"),
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ.get("DB_NAME", "apartment"),
        user=os.environ.get("DB_USER", "apartment_app"),
        password=os.environ["DB_PASSWORD"],
        connect_timeout=4,
        cursor_factory=RealDictCursor,
    )


def initialize_schema():
    statements = [
        """
        CREATE TABLE IF NOT EXISTS residents (
            id BIGSERIAL PRIMARY KEY,
            apartment_no VARCHAR(20) NOT NULL UNIQUE,
            full_name VARCHAR(120) NOT NULL,
            phone VARCHAR(24) NOT NULL,
            email VARCHAR(160),
            status VARCHAR(20) NOT NULL DEFAULT 'Đang ở',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS fees (
            id BIGSERIAL PRIMARY KEY,
            resident_id BIGINT NOT NULL REFERENCES residents(id) ON DELETE CASCADE,
            title VARCHAR(120) NOT NULL,
            amount NUMERIC(12, 0) NOT NULL CHECK (amount >= 0),
            due_date DATE NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'Chưa thu'
                CHECK (status IN ('Chưa thu', 'Đã thu')),
            paid_at TIMESTAMPTZ
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS announcements (
            id BIGSERIAL PRIMARY KEY,
            title VARCHAR(180) NOT NULL,
            body TEXT NOT NULL,
            published_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS complaints (
            id BIGSERIAL PRIMARY KEY,
            resident_name VARCHAR(120) NOT NULL,
            apartment_no VARCHAR(20) NOT NULL,
            category VARCHAR(60) NOT NULL,
            content TEXT NOT NULL,
            status VARCHAR(24) NOT NULL DEFAULT 'Mới tiếp nhận'
                CHECK (status IN ('Mới tiếp nhận', 'Đang xử lý', 'Đã giải quyết')),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """,
        """
        INSERT INTO residents (apartment_no, full_name, phone, email)
        VALUES
          ('A-101', 'Nguyễn Minh An', '0901000101', 'an@example.local'),
          ('A-202', 'Trần Thu Hà', '0902000202', 'ha@example.local'),
          ('B-305', 'Lê Quốc Bảo', '0903000305', 'bao@example.local'),
          ('C-408', 'Phạm Ngọc Linh', '0904000408', 'linh@example.local')
        ON CONFLICT (apartment_no) DO NOTHING
        """,
        """
        INSERT INTO fees (resident_id, title, amount, due_date)
        SELECT r.id, 'Phí quản lý tháng 10/2026', 850000, DATE '2026-10-15'
        FROM residents r
        WHERE r.apartment_no IN ('A-101', 'A-202', 'B-305')
          AND NOT EXISTS (
            SELECT 1 FROM fees f
            WHERE f.resident_id = r.id AND f.title = 'Phí quản lý tháng 10/2026'
          )
        """,
        """
        INSERT INTO fees (resident_id, title, amount, due_date, status, paid_at)
        SELECT r.id, 'Phí gửi xe tháng 10/2026', 120000, DATE '2026-10-10',
               'Đã thu', now()
        FROM residents r
        WHERE r.apartment_no = 'C-408'
          AND NOT EXISTS (
            SELECT 1 FROM fees f
            WHERE f.resident_id = r.id AND f.title = 'Phí gửi xe tháng 10/2026'
          )
        """,
        """
        INSERT INTO announcements (title, body)
        SELECT 'Bảo trì thang máy khu A', 'Thang máy khu A được bảo trì từ 09:00 đến 11:00 ngày 12/10. Cư dân vui lòng sử dụng thang máy khu B trong thời gian này.'
        WHERE NOT EXISTS (
            SELECT 1 FROM announcements WHERE title = 'Bảo trì thang máy khu A'
        )
        """,
    ]
    with connect() as conn:
        with conn.cursor() as cur:
            for statement in statements:
                cur.execute(statement)


def query(sql, params=()):
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            if cur.description:
                return cur.fetchall()
            return cur.rowcount


def one(sql, params=()):
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()
