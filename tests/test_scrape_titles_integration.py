from __future__ import annotations

import csv
from typing import cast

from requests import Session

from automation import scrape_titles as st


# ---- ダミーHTTPレスポンスとセッション ----
class _DummyResp:
    def __init__(self, content: bytes, ok: bool = True) -> None:
        self.content = content
        self._ok = ok
    def raise_for_status(self) -> None:
        if not self._ok:
            raise Exception("boom")

class _SessOK:
    def get(self, url: str, timeout: int, allow_redirects: bool):
        # URLで出し分け（テストしやすいようタイトルを固定）
        if "one" in url:
            return _DummyResp(b"<title>One</title>", ok=True)
        return _DummyResp(b"<title>Two</title>", ok=True)

# ---- 低レベル関数のI/O系 ----
def test_read_existing_roundtrip(tmp_path) -> None:
    p = tmp_path / "x.csv"
    with p.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "url", "title", "fetched_at"])
        w.writerow(["2025-01-01", "https://ex", "Hello", "2025-01-01T00:00:00+09:00"])
    got = st._read_existing(p)
    assert got == [("2025-01-01", "https://ex", "Hello")]

def test_create_session_headers() -> None:
    s = st._create_session()
    assert isinstance(s, Session)
    # 共通ヘッダが付与されていることだけ軽く確認
    assert "User-Agent" in s.headers

# ---- main の正常系：日次CSVと累積CSVを生成 ----
def test_main_end_to_end(tmp_path, monkeypatch) -> None:
    repo = tmp_path
    (repo / "automation").mkdir(parents=True)
    (repo / "data").mkdir(parents=True)
    # 2URL（同日に2行出る想定）
    (repo / "automation" / "targets.txt").write_text(
        "https://site/one\nhttps://site/two\n", encoding="utf-8"
    )
    # ルート・セッション・時刻を固定化
    monkeypatch.setattr(st, "_repo_root", lambda: repo)
    monkeypatch.setattr(st, "_create_session", lambda: cast(Session, _SessOK()))
    monkeypatch.setattr(st, "_now_iso", lambda: "2025-01-01T00:00:00+09:00")

    rc = st.main()
    assert rc == 0
    # 日次CSVができる
    daily_dir = repo / "data" / "daily"
    daily_files = list(daily_dir.glob("titles-*.csv"))
    assert daily_files, "daily csv not created"
    # 累積CSVができて、ヘッダ+2行以上
    cum_lines = (repo / "data" / "titles.csv").read_text(encoding="utf-8").splitlines()
    assert cum_lines[0] == "date,url,title,fetched_at"
    assert len(cum_lines) >= 3

# ---- main の異常系：targets.txt 不在 → rc=2 ----
def test_main_missing_targets(tmp_path, monkeypatch) -> None:
    repo = tmp_path
    (repo / "automation").mkdir(parents=True)
    monkeypatch.setattr(st, "_repo_root", lambda: repo)
    rc = st.main()
    assert rc == 2

# ---- main の異常系：有効URLが1つも無い → rc=2 ----
def test_main_no_valid_urls(tmp_path, monkeypatch) -> None:
    repo = tmp_path
    (repo / "automation").mkdir(parents=True)
    (repo / "automation" / "targets.txt").write_text("# comment only\nftp://bad\n", encoding="utf-8")
    monkeypatch.setattr(st, "_repo_root", lambda: repo)
    rc = st.main()
    assert rc == 2
