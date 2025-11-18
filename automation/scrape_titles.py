from __future__ import annotations

import csv
from collections.abc import Iterable
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from observability import log_event, time_block

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
    return " ".join(s.split())


def _attr_text(val: object) -> str | None:
    if val is None:
        return None
    if isinstance(val, str):
        return _squash_ws(val)
    if isinstance(val, list | tuple):
        joined = " ".join(str(x) for x in val)
        return _squash_ws(joined)
    return _squash_ws(str(val))


def _extract_title(html: bytes) -> str | None:
    soup = BeautifulSoup(html, "lxml")

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


def _create_session() -> requests.Session:
    sess = requests.Session()
    retries = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset({"HEAD", "GET", "OPTIONS"}),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries)
    sess.mount("http://", adapter)
    sess.mount("https://", adapter)
    sess.headers.update(HEADERS)
    return sess


def _fetch(session: requests.Session, url: str) -> str | None:
    try:
        r = session.get(url, timeout=TIMEOUT, allow_redirects=True)
        r.raise_for_status()
        return _extract_title(r.content)
    except requests.exceptions.RequestException as e:
        print(f"[ERR] {url} -> {e.__class__.__name__}: {e}")
        return None


def _now_iso() -> str:
    return datetime.now(UTC).astimezone().isoformat(timespec="seconds")


def _write_csv(rows: Iterable[tuple[str, str, str]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "url", "title", "fetched_at"])
        for d, u, t in rows:
            w.writerow([d, u, t, _now_iso()])


def _read_existing(p: Path) -> list[tuple[str, str, str]]:
    if not p.exists():
        return []
    out: list[tuple[str, str, str]] = []
    with p.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            d = (row.get("date") or "").strip()
            u = (row.get("url") or "").strip()
            t = (row.get("title") or "").strip()
            if d and u and t:
                out.append((d, u, t))
    return out


def _dedup_merge(
    base: Iterable[tuple[str, str, str]],
    add: Iterable[tuple[str, str, str]],
) -> list[tuple[str, str, str]]:
    """baseにaddをマージ。キー=(date,url,title) で重複排除。"""
    seen: set[tuple[str, str, str]] = set(base)
    merged: list[tuple[str, str, str]] = list(base)
    for row in add:
        if row not in seen:
            merged.append(row)
            seen.add(row)
    return merged


def main() -> int:
    root = _repo_root()
    targets_path = root / "automation" / "targets.txt"
    daily_dir = root / "data" / "daily"
    cumulative_csv = root / "data" / "titles.csv"

    if not targets_path.exists():
        print(f"[ERR] not found: {targets_path}")
        log_event(
            "scrape_titles_abort",
            reason="targets_not_found",
            targets_path=str(targets_path),
        )
        return 2

    urls = _read_targets(targets_path)
    if not urls:
        print("[ERR] no valid urls in automation/targets.txt")
        log_event(
            "scrape_titles_abort",
            reason="no_valid_urls",
            targets_path=str(targets_path),
        )
        return 2

    log_event(
        "scrape_titles_targets_loaded",
        targets_path=str(targets_path),
        targets_count=len(urls),
    )

    sess = _create_session()
    today = date.today().isoformat()

    # 以降の処理全体を time_block で計測
    with time_block(
        "scrape_titles",
        date=today,
        targets_count=len(urls),
    ):
        # 取得（同一URLは1回だけ）
        seen_url: set[str] = set()
        new_rows: list[tuple[str, str, str]] = []
        for url in urls:
            if url in seen_url:
                continue
            seen_url.add(url)
            title = _fetch(sess, url)
            if title:
                print(f"[OK] {url} -> {title}")
                new_rows.append((today, url, title))
            else:
                print(f"[SKIP] {url} -> title not found")

        # 日次CSV
        daily_dir.mkdir(parents=True, exist_ok=True)
        daily_csv = daily_dir / f"titles-{today.replace('-', '')}.csv"
        _write_csv(new_rows, daily_csv)

        # 累積CSV（過去とマージして重複排除）
        existing = _read_existing(cumulative_csv)
        merged = _dedup_merge(existing, new_rows)
        _write_csv(merged, cumulative_csv)

        print(
            f"[OK] daily_rows={len(new_rows)} written: {daily_csv} / "
            f"cumulative_rows={len(merged)} -> {cumulative_csv}"
        )

        log_event(
            "scrape_titles_summary",
            date=today,
            targets_count=len(urls),
            daily_rows=len(new_rows),
            cumulative_rows=len(merged),
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
