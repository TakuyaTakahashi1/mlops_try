from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

import pandas as pd

DATA_DIR = Path("data")
SQLITE_PATH = DATA_DIR / "titles.sqlite"
PARQUET_DIR = DATA_DIR / "parquet"

SCHEMA_VERSION = 1


def _ensure_db(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER NOT NULL,
            applied_at TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            url TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            fetched_at TEXT NOT NULL
        )
    """)
    cur.execute("SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1")
    row = cur.fetchone()
    if row is None or row[0] < SCHEMA_VERSION:
        cur.execute(
            "INSERT INTO schema_version(version, applied_at) VALUES(?, ?)",
            (SCHEMA_VERSION, datetime.utcnow().isoformat(timespec="seconds")),
        )
    conn.commit()


def open_db() -> sqlite3.Connection:
    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(SQLITE_PATH))
    _ensure_db(conn)
    return conn


def upsert_articles(rows: Iterable[dict]) -> int:
    conn = open_db()
    cur = conn.cursor()
    count = 0
    for r in rows:
        url = r.get("url")
        title = r.get("title", "")
        fetched_at = r.get("fetched_at") or datetime.utcnow().isoformat(timespec="seconds")
        if not url:
            continue
        cur.execute(
            """
            INSERT INTO articles(url, title, fetched_at)
            VALUES(?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                title=excluded.title,
                fetched_at=excluded.fetched_at
        """,
            (url, title, fetched_at),
        )
        count += 1
    conn.commit()
    conn.close()
    return count


def query_count() -> int:
    conn = open_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM articles")
    n = int(cur.fetchone()[0])
    conn.close()
    return n


def write_parquet_daily(rows: Iterable[dict], date_str: str) -> Path:
    PARQUET_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    if "fetched_at" not in df.columns:
        df["fetched_at"] = pd.Timestamp.utcnow().isoformat(timespec="seconds")
    if "url" in df.columns:
        df = df.drop_duplicates(subset=["url"], keep="first")
    path = PARQUET_DIR / f"titles-{date_str}.parquet"
    df.to_parquet(path, index=False)
    return path


def read_parquet_concat() -> pd.DataFrame:
    if not PARQUET_DIR.exists():
        return pd.DataFrame(columns=["url", "title", "fetched_at"])
    files = sorted(PARQUET_DIR.glob("titles-*.parquet"))
    if not files:
        return pd.DataFrame(columns=["url", "title", "fetched_at"])
    dfs = [pd.read_parquet(p) for p in files]
    return pd.concat(dfs, ignore_index=True)


def migrate_from_csv() -> tuple[int, int]:
    db_count, pq_files = 0, 0
    cumu = DATA_DIR / "titles.csv"
    daily_files = sorted(DATA_DIR.glob("titles-*.csv"))
    rows_db: list[dict] = []
    if cumu.exists():
        df = pd.read_csv(cumu, dtype=str)
        if not df.empty:
            if "fetched_at" not in df.columns:
                df["fetched_at"] = pd.Timestamp.utcnow().isoformat(timespec="seconds")
            df = df.drop_duplicates(subset=["url"], keep="first")
            rows_db += df.to_dict(orient="records")
    for f in daily_files:
        df = pd.read_csv(f, dtype=str)
        if df.empty:
            continue
        if "fetched_at" not in df.columns:
            df["fetched_at"] = pd.Timestamp.utcnow().isoformat(timespec="seconds")
        df = df.drop_duplicates(subset=["url"], keep="first")
        rows = df.to_dict(orient="records")
        date_str = f.stem.split("-")[-1]
        write_parquet_daily(rows, date_str)
        pq_files += 1
        rows_db += rows
    if rows_db:
        db_count = upsert_articles(rows_db)
    return db_count, pq_files
