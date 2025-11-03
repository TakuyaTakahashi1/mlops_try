from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

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
    cur.execute("CREATE INDEX IF NOT EXISTS idx_articles_fetched_at ON articles(fetched_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_articles_title ON articles(title)")
    # FTS5（全文検索）
    cur.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts
        USING fts5(url, title, tokenize='unicode61');
    """)
    cur.execute("""
        CREATE TRIGGER IF NOT EXISTS articles_ai AFTER INSERT ON articles BEGIN
            INSERT INTO articles_fts(rowid, url, title)
            VALUES (abs(random()), NEW.url, NEW.title);
        END;
    """)
    cur.execute("""
        CREATE TRIGGER IF NOT EXISTS articles_ad AFTER DELETE ON articles BEGIN
            DELETE FROM articles_fts WHERE url = OLD.url;
        END;
    """)
    cur.execute("""
        CREATE TRIGGER IF NOT EXISTS articles_au AFTER UPDATE ON articles BEGIN
            DELETE FROM articles_fts WHERE url = OLD.url;
            INSERT INTO articles_fts(rowid, url, title)
            VALUES (abs(random()), NEW.url, NEW.title);
        END;
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


def search_articles(
    q: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 50,
    offset: int = 0,
    order: str = "desc",
) -> pd.DataFrame:
    """
    ISO文字列の fetched_at を使って期間フィルタ。
    q があれば title / url に対して LIKE（部分一致、大文字小文字区別なし）。
    order は 'asc' か 'desc'。
    """
    conn = open_db()
    try:
        params: list[Any] = []
        where = ["1=1"]
        if date_from:
            where.append("fetched_at >= ?")
            params.append(date_from)
        if date_to:
            where.append("fetched_at < ?")
            params.append(date_to)
        if q:
            where.append("(LOWER(title) LIKE ? OR LOWER(url) LIKE ?)")
            like = f"%{q.lower()}%"
            params.extend([like, like])
        order_sql = "DESC" if str(order).lower() != "asc" else "ASC"
        sql = f"""
            SELECT url, title, fetched_at
            FROM articles
            WHERE {" AND ".join(where)}
            ORDER BY fetched_at {order_sql}
            LIMIT ? OFFSET ?
        """
        params.extend([int(limit), int(offset)])
        import pandas as pd  # 安全のため明示（上でもimportしてるが二重でもOK）

        df = pd.read_sql_query(sql, conn, params=tuple(params))
        return df
    finally:
        conn.close()


def fts_rebuild() -> int:
    """articles 全件で FTS を作り直す。"""
    conn = open_db()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM articles_fts")
        cur.execute("SELECT url, title FROM articles")
        rows = cur.fetchall()
        cur.executemany(
            "INSERT INTO articles_fts(rowid, url, title) VALUES (abs(random()), ?, ?)",
            rows,
        )
        conn.commit()
        return len(rows)
    finally:
        conn.close()


def fts_search_articles(q: str, limit: int = 50, offset: int = 0) -> pd.DataFrame:
    """FTS5 で全文検索（BM25順）。"""
    conn = open_db()
    try:
        sql = """
            SELECT a.url, a.title, a.fetched_at
            FROM articles a
            JOIN articles_fts ON articles_fts.url = a.url
            WHERE articles_fts MATCH ?
            ORDER BY bm25(articles_fts) ASC
            LIMIT ? OFFSET ?
        """
        return pd.read_sql_query(sql, conn, params=(q, int(limit), int(offset)))
    finally:
        conn.close()
