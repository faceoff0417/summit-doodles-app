"""One-time, non-destructive migration that brings an existing
instance/summitdoodles.db up to the latest schema (new tables + new
columns) WITHOUT touching any existing rows -- safe to run on a database
that already has real dogs, photos, applications, etc. in it.

Run with: python3 migrate.py
Safe to run more than once (every step checks before it acts).
"""
import sqlite3
from db import get_db

NEW_TABLES_SQL = [
    """CREATE TABLE IF NOT EXISTS reminders (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_type     TEXT NOT NULL CHECK (entity_type IN ('dog','puppy')),
        entity_id       INTEGER NOT NULL,
        title           TEXT NOT NULL,
        due_date        TEXT,
        done            INTEGER NOT NULL DEFAULT 0,
        created_at      TEXT NOT NULL DEFAULT (datetime('now'))
    )""",
    """CREATE TABLE IF NOT EXISTS heat_cycles (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        dog_id          INTEGER NOT NULL REFERENCES dogs(id) ON DELETE CASCADE,
        start_date      TEXT NOT NULL,
        progesterone    REAL,
        notes           TEXT,
        created_at      TEXT NOT NULL DEFAULT (datetime('now'))
    )""",
    """CREATE TABLE IF NOT EXISTS semen_inventory (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        dog_id          INTEGER NOT NULL REFERENCES dogs(id) ON DELETE CASCADE,
        kind            TEXT NOT NULL CHECK (kind IN ('Fresh','Chilled','Frozen')),
        quantity        INTEGER DEFAULT 1,
        location        TEXT,
        collected_date  TEXT,
        notes           TEXT,
        created_at      TEXT NOT NULL DEFAULT (datetime('now'))
    )""",
    """CREATE TABLE IF NOT EXISTS documents (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_type     TEXT NOT NULL CHECK (entity_type IN ('dog','litter','reservation','general')),
        entity_id       INTEGER,
        title           TEXT NOT NULL,
        category        TEXT,
        filename        TEXT NOT NULL,
        uploaded_at     TEXT NOT NULL DEFAULT (datetime('now'))
    )""",
    """CREATE TABLE IF NOT EXISTS notes (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_type     TEXT NOT NULL CHECK (entity_type IN ('application','reservation','contact')),
        entity_id       INTEGER NOT NULL,
        body            TEXT NOT NULL,
        due_date        TEXT,
        done            INTEGER NOT NULL DEFAULT 0,
        created_at      TEXT NOT NULL DEFAULT (datetime('now'))
    )""",
    """CREATE TABLE IF NOT EXISTS invoices (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        reservation_id  INTEGER NOT NULL REFERENCES reservations(id) ON DELETE CASCADE,
        description     TEXT NOT NULL,
        amount          REAL NOT NULL,
        status          TEXT NOT NULL DEFAULT 'Due' CHECK (status IN ('Due','Paid')),
        due_date        TEXT,
        paid_at         TEXT,
        created_at      TEXT NOT NULL DEFAULT (datetime('now'))
    )""",
    """CREATE TABLE IF NOT EXISTS expenses (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        category        TEXT NOT NULL,
        description     TEXT,
        amount          REAL NOT NULL,
        expense_date    TEXT NOT NULL,
        litter_id       INTEGER REFERENCES litters(id) ON DELETE SET NULL,
        created_at      TEXT NOT NULL DEFAULT (datetime('now'))
    )""",
    """CREATE TABLE IF NOT EXISTS campaigns (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        channel         TEXT NOT NULL CHECK (channel IN ('Social','Email')),
        title           TEXT NOT NULL,
        body            TEXT,
        status          TEXT NOT NULL DEFAULT 'Draft' CHECK (status IN ('Draft','Scheduled','Sent')),
        scheduled_for   TEXT,
        sent_at         TEXT,
        created_at      TEXT NOT NULL DEFAULT (datetime('now'))
    )""",
    """CREATE TABLE IF NOT EXISTS site_settings (
        key             TEXT PRIMARY KEY,
        value           TEXT
    )""",
]

NEW_COLUMNS = [
    ("litters", "coi_percent", "REAL"),
    ("litters", "coi_notes", "TEXT"),
    ("reservations", "buyer_signature", "TEXT"),
    ("reservations", "buyer_signature_date", "TEXT"),
    ("reservations", "feeding_schedule", "TEXT"),
    ("reservations", "training_notes", "TEXT"),
    ("reservations", "registration_status", "TEXT NOT NULL DEFAULT 'Pending'"),
    ("reservations", "go_home_sent", "INTEGER DEFAULT 0"),
]


def run():
    conn = get_db()
    for stmt in NEW_TABLES_SQL:
        conn.execute(stmt)
    for table, column, coltype in NEW_COLUMNS:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")
            print(f"added column {table}.{column}")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e):
                pass  # already migrated
            else:
                raise
    conn.commit()
    conn.close()
    print("Migration complete -- existing data untouched.")


if __name__ == "__main__":
    run()
