from datetime import datetime, timedelta

from automation import storage


def test_search_filters_and_order(tmp_path, monkeypatch):
    # DBを一時ファイルに差し替え
    monkeypatch.setattr(storage, "SQLITE_PATH", tmp_path / "t.sqlite")
    # テストデータ投入（時系列 3件）
    base = datetime(2025, 10, 28, 12, 0, 0)
    rows = [
        {
            "url": "https://ex.com/a",
            "title": "Alpha Note",
            "fetched_at": (base - timedelta(days=2)).isoformat(timespec="seconds"),
        },
        {
            "url": "https://ex.com/b",
            "title": "Beta News",
            "fetched_at": (base - timedelta(days=1)).isoformat(timespec="seconds"),
        },
        {
            "url": "https://ex.com/c",
            "title": "Gamma Blog",
            "fetched_at": base.isoformat(timespec="seconds"),
        },
    ]
    storage.upsert_articles(rows)
    # キーワード
    df = storage.search_articles(q="news", limit=10)
    assert len(df) == 1 and df.iloc[0]["url"] == "https://ex.com/b"
    # 期間（from含む / toは未満）
    df2 = storage.search_articles(
        date_from=rows[1]["fetched_at"], date_to=rows[2]["fetched_at"], order="asc"
    )
    assert list(df2["url"]) == ["https://ex.com/b"]
    # 並び順 desc
    df3 = storage.search_articles(order="desc", limit=2)
    assert list(df3["url"]) == ["https://ex.com/c", "https://ex.com/b"]
