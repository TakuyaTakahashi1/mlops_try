from __future__ import annotations

import csv
from collections.abc import Iterable
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

TIMEOUT = 10  # seconds
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read_targets(p: Path) -> list[str]:
    urls: list[str] = []
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parsed = urlparse(line)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            urls.append(line)
        else:
            print(f"[SKIP] invalid url format: {line}")
    return urls


def _squash_ws(s: str) -> str:
    """連続空白/改行を1スペースに圧縮。"""
    return " ".join(s.split())


def _attr_text(val: object) -> str | None:
    """BeautifulSoupの属性値（str / list等）を必ずstrへ正規化。"""
    if val is None:
        return None
    if isinstance(val, str):
        return _squash_ws(val)
    if isinstance(val, list | tuple):
        joined = " ".join(str(x) for x in val)
        return _squash_ws(joined)
    # その他の型も最後は文字列化
    return _squash_ws(str(val))


def _extract_title(html: bytes) -> str | None:
    soup = BeautifulSoup(html, "lxml")

    # 優先: og:title → <title> → <h1> → meta[name=title]
    og = soup.find("meta", property="og:title")
    if isinstance(og, Tag):
        t = _attr_text(og.get("content"))
        if t:
            return t

    if soup.title and soup.title.string:
        return _squash_ws(soup.title.string)

    h1 = soup.find("h1")
    if isinstance(h1, Tag):
        text = h1.get_text(separator=" ", strip=True)
        if text:
            return _squash_ws(text)

    mt = soup.find("meta", attrs={"name": "title"})
    if isinstance(mt, Tag):
        t = _attr_text(mt.get("content"))
        if t:
            return t

    return None


def _fetch(url: str) -> str | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        r.raise_for_status()
        return _extract_title(r.content)
    except requests.exceptions.RequestException as e:
        print(f"[ERR] {url} -> {e.__class__.__name__}: {e}")
        return None


def _now_iso() -> str:
    # 例: 2025-08-22T16:45:03+09:00
    return datetime.now(UTC).astimezone().isoformat(timespec="seconds")


def _write_csv(rows: Iterable[tuple[str, str, str]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "url", "title", "fetched_at"])
        for d, u, t in rows:
            writer.writerow([d, u, t, _now_iso()])


def main() -> int:
    root = _repo_root()
    targets_path = root / "automation" / "targets.txt"
    out_csv = root / "data" / "titles.csv"

    if not targets_path.exists():
        print(f"[ERR] not found: {targets_path}")
        return 2

    urls = _read_targets(targets_path)
    if not urls:
        print("[ERR] no valid urls in automation/targets.txt")
        return 2

    today = date.today().isoformat()
    result_rows: list[tuple[str, str, str]] = []

    for url in urls:
        title = _fetch(url)
        if title:
            print(f"[OK] {url} -> {title}")
            result_rows.append((today, url, title))
        else:
            print(f"[SKIP] {url} -> title not found")

    _write_csv(result_rows, out_csv)
    print(f"[OK] rows={len(result_rows)} written: {out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
