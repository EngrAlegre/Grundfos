import sqlite3
import hashlib
import json
import time
import os
from src.config import CACHE_DIR

DB_PATH = os.path.join(CACHE_DIR, "pump_cache.db")

TTL_SEARCH = 86400 * 1
TTL_PAGE = 86400 * 7
TTL_EXTRACTION = 0


def _get_conn():
    os.makedirs(CACHE_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS cache "
        "(key TEXT PRIMARY KEY, value TEXT, ts REAL, category TEXT)"
    )
    return conn


def _make_key(*parts):
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode()).hexdigest()


def cache_get(category: str, *key_parts):
    ttl = {"search": TTL_SEARCH, "page": TTL_PAGE, "extraction": TTL_EXTRACTION}.get(
        category, 0
    )
    conn = _get_conn()
    key = _make_key(category, *key_parts)
    row = conn.execute(
        "SELECT value, ts FROM cache WHERE key = ? AND category = ?", (key, category)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    if ttl > 0 and (time.time() - row[1]) > ttl:
        return None
    return json.loads(row[0])


def cache_set(category: str, value, *key_parts):
    conn = _get_conn()
    key = _make_key(category, *key_parts)
    conn.execute(
        "INSERT OR REPLACE INTO cache (key, value, ts, category) VALUES (?, ?, ?, ?)",
        (key, json.dumps(value), time.time(), category),
    )
    conn.commit()
    conn.close()
