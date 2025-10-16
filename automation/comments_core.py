from __future__ import annotations

import csv
import hashlib
import os
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast

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
    posted_at: str | None  # ISO文字列 or None（UTC想定）
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
            soup = BeautifulSoup(r.text, "lxml")

            # コメントコンテナ候補
            containers: list[Tag] = list(
                cast(
                    list[Tag],
                    soup.select(
                        "#comments, #comment, .comments, .commentlist, .pcomment, .comment-area"
                    ),
                )
            )
            if not containers:
                h = soup.find(
                    lambda tag: tag.name in ("h2", "h3", "h4") and "コメント" in tag.get_text()
                )
                if h:
                    nxt = h.find_next(["ul", "ol", "div"])
                    if isinstance(nxt, Tag):
                        containers = [nxt]
                    else:
                        containers = []

            # 各コンテナからコメント要素を拾う
            item_nodes: list[Tag] = []
            for container in containers:
                item_nodes.extend(cast(list[Tag], container.select("li")))
                item_nodes.extend(cast(list[Tag], container.select(".comment")))
                item_nodes.extend(cast(list[Tag], container.select(".comment-item")))

            # PukiWiki の「最新20件」ブロックを優先
            latest_block_nodes = cast(list[Tag], soup.select("form.pcmt ul li.pcmt"))
            if latest_block_nodes:
                item_nodes = latest_block_nodes

            # container 自体が1件のケース
            if not item_nodes and containers:
                item_nodes = containers

            comments: list[Comment] = []
            now_iso = datetime.now(UTC).isoformat()

            for item_node in item_nodes:
                text = " ".join(item_node.get_text(" ", strip=True).split())
                if not text:
                    continue

                author_node = item_node.select_one(".author, .comment-author, .commenter, .name")
                author = author_node.get_text(strip=True) if isinstance(author_node, Tag) else None

                dt: str | None = None
                time_node = item_node.find("time")
                if isinstance(time_node, Tag):
                    dt_attr = time_node.get("datetime")
                    dt_str = dt_attr if isinstance(dt_attr, str) else None
                    dt = dt_str or _extract_datetime(time_node.get_text(" ", strip=True))
                if not dt:
                    dt = _extract_datetime(text)

                cm = Comment(
                    comment_id=Comment.mk_id(url, text, dt),
                    source_url=url,
                    author=author,
                    content=text,
                    posted_at=dt,
                    collected_at=now_iso,
                )
                comments.append(cm)

            # 重複除去（comment_id でユニーク化）
            uniq: dict[str, Comment] = {}
            for cm in comments:
                uniq[cm.comment_id] = cm

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
        header = ["comment_id", "source_url", "author", "content", "posted_at", "collected_at"]
        exists = os.path.exists(path)
        with open(path, mode, newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if not exists or mode == "w":
                w.writerow(header)
            for cm in data:
                w.writerow(
                    [
                        cm.comment_id,
                        cm.source_url,
                        cm.author or "",
                        cm.content,
                        cm.posted_at or "",
                        cm.collected_at,
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
    new_rows = [cm for cm in rows if cm.comment_id not in seen]
    if not os.path.exists(cum):
        dump(cum, rows, "w")
    elif new_rows:
        dump(cum, new_rows, "a")
