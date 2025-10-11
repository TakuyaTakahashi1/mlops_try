from __future__ import annotations

import csv
import hashlib
import os
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "ja-JP,ja;q=0.9,en;q=0.8",
}

HTTP_TIMEOUT = 15
MAX_RETRIES = 3


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(DEFAULT_HEADERS)
    return s


@dataclass
class Comment:
    comment_id: str
    source_url: str
    author: str | None
    content: str
    posted_at: str | None  # ISO文字列 or None
    collected_at: str  # UTC ISO

    @staticmethod
    def mk_id(source_url: str, content: str, posted_at: str | None) -> str:
        base = f"{source_url}|{posted_at or ''}|{content.strip()}"
        return hashlib.sha1(base.encode("utf-8")).hexdigest()


DATE_PATTERNS = [
    re.compile(r"\d{4}/\d{1,2}/\d{1,2}\s+\d{1,2}:\d{2}"),
    re.compile(r"\d{4}-\d{1,2}-\d{1,2}\s+\d{1,2}:\d{2}"),
]


def _extract_datetime(text: str) -> str | None:
    for pat in DATE_PATTERNS:
        m = pat.search(text)
        if m:
            raw = m.group(0).replace("-", "/")
            g = re.match(r"(\d{4})/(\d{1,2})/(\d{1,2})\s+(\d{1,2}):(\d{2})", raw)
            if not g:
                continue
            yyyy, mm, dd, hh, mi = g.groups()
            dt = datetime(int(yyyy), int(mm), int(dd), int(hh), int(mi), tzinfo=UTC)
            return dt.isoformat()
    return None


def fetch_latest_comments(url: str, take: int = 5) -> list[Comment]:
    s = make_session()
    last_err: Exception | None = None

    for attempt in range(MAX_RETRIES):
        try:
            r = s.get(url, timeout=HTTP_TIMEOUT)
            r.raise_for_status()
            html = r.text
            soup = BeautifulSoup(html, "lxml")

            # コメントコンテナ候補
            containers: list[Tag] = list(
                soup.select(
                    "#comments, #comment, .comments, .commentlist, .pcomment, .comment-area"
                )
            )
            if not containers:
                h = soup.find(
                    lambda tag: tag.name in ("h2", "h3", "h4") and "コメント" in tag.get_text()
                )
                if h:
                    nxt = h.find_next(["ul", "ol", "div"])
                    containers = [nxt] if isinstance(nxt, Tag) else []
                else:
                    containers = []

            # 各コンテナからコメント要素を拾う
            items: list[Tag] = []
            for c in containers:
                items.extend(c.select("li"))
                items.extend(c.select(".comment"))
                items.extend(c.select(".comment-item"))

            # container自体が1件（詳細直下に情報を持つ）ケース
            if not items and containers:
                items = containers

            comments: list[Comment] = []
            now_iso = datetime.now(UTC).isoformat()

            for node in items:
                text = " ".join(node.get_text(" ", strip=True).split())
                if not text:
                    continue

                author_node = node.select_one(".author, .comment-author, .commenter, .name")
                author = author_node.get_text(strip=True) if author_node else None

                dt: str | None = None
                time_node = node.find("time")
                if time_node:
                    dt = time_node.get("datetime") or _extract_datetime(
                        time_node.get_text(" ", strip=True)
                    )
                if not dt:
                    dt = _extract_datetime(text)

                cid = Comment.mk_id(url, text, dt)
                comments.append(
                    Comment(
                        comment_id=cid,
                        source_url=url,
                        author=author,
                        content=text,
                        posted_at=dt,
                        collected_at=now_iso,
                    )
                )

            # 重複除去
            uniq: dict[str, Comment] = {}
            for c in comments:
                uniq[c.comment_id] = c
            return list(uniq.values())[:take]

        except Exception as e:
            last_err = e
            time.sleep(1.5 * (attempt + 1))

    raise RuntimeError(f"failed to fetch comments: {last_err}")


def write_csvs(rows: list[Comment], outdir: str = "data") -> None:
    os.makedirs(outdir, exist_ok=True)
    ymd = datetime.now(UTC).strftime("%Y%m%d")
    daily = os.path.join(outdir, f"comments-{ymd}.csv")
    cum = os.path.join(outdir, "comments.csv")

    def dump(path: str, data: list[Comment], mode: str) -> None:
        header = [
            "comment_id",
            "source_url",
            "author",
            "content",
            "posted_at",
            "collected_at",
        ]
        exists = os.path.exists(path)
        with open(path, mode, newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if not exists or mode == "w":
                w.writerow(header)
            for c in data:
                w.writerow(
                    [
                        c.comment_id,
                        c.source_url,
                        c.author or "",
                        c.content,
                        c.posted_at or "",
                        c.collected_at,
                    ]
                )

    # 日次は毎回作り直し
    dump(daily, rows, "w")

    # 累積は重複排除で追記
    seen: set[str] = set()
    if os.path.exists(cum):
        with open(cum, newline="", encoding="utf-8") as f:
            for i, row in enumerate(csv.reader(f)):
                if i == 0 or not row:
                    continue
                seen.add(row[0])
    new_rows = [c for c in rows if c.comment_id not in seen]
    if not os.path.exists(cum):
        dump(cum, rows, "w")
    elif new_rows:
        dump(cum, new_rows, "a")
