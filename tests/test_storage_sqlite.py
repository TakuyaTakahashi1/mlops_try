import sqlite3

from automation.storage import query_count, upsert_articles


def test_schema_and_upsert(tmp_path, monkeypatch):
    from automation import storage

    monkeypatch.setattr(storage, "SQLITE_PATH", tmp_path / "test.sqlite")
    conn = storage.open_db()
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='articles'")
    assert cur.fetchone() is not None
    n = upsert_articles(
        [{"url": "https://ex.com/a", "title": "A"}, {"url": "https://ex.com/a", "title": "A-dup"}]
    )
    assert n == 2
    assert query_count() == 1
    cur = sqlite3.connect(str(storage.SQLITE_PATH)).cursor()
    cur.execute("SELECT title FROM articles WHERE url='https://ex.com/a'")
    assert cur.fetchone()[0] == "A-dup"
