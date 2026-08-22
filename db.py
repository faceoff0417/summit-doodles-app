import sqlite3
import os
import secrets

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# On a host with a persistent disk (e.g. Render), set DATA_DIR to the
# disk's mount path so the database, uploaded photos, and the session
# secret key all survive redeploys. Left unset, everything stays local
# to this folder -- exactly today's behavior.
DATA_DIR = os.environ.get("DATA_DIR", BASE_DIR)
INSTANCE_DIR = os.path.join(DATA_DIR, "instance")
DB_PATH = os.path.join(INSTANCE_DIR, "summitdoodles.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    os.makedirs(INSTANCE_DIR, exist_ok=True)
    conn = get_db()
    with open(os.path.join(BASE_DIR, "schema.sql"), "r") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


def new_token():
    return secrets.token_urlsafe(18)
