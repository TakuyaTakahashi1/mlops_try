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

# ---- HTTP ----

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


# ---- Model ----


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


# ---- Parse helpers ----

# 例: "2025-10-13 (月) 22:56:57"
JST_COMMENT_DT = re.compile(r"(\d{4}-\d{2}-\d{2})\s*\(.+?\)\s*(\d{2}:\d{2}:\d{2})")

# 旧汎用（yyyy/mm/dd HH:MM / yyyy-mm-dd HH:MM）
DATE_PATTERNS_FALLBACK = [
    re.compile(r"\d{4}/\d{1,2}/\d{1,2}\s+\d{1,2}:\d{2}"),
    re.compile(r"\d{4}-\d{1,2}-\d{1,2}\s+\d{1,2}:\d{2}"),
]


def _extract_datetime_loose(text: str) -> str | None:
    """旧フォールバックの簡易抽出（秒なし・UTC扱い）"""
    for pat in DATE_PATTERNS_FALLBACK:
        m = pat.search(text)
        if not m:
            continue
        raw = m.group(0).replace("-", "/")
        g = re.match(r"(\d{4})/(\d{1,2})/(\d{1,2})\s+(\d{1,2}):(\d{2})", raw)
        if not g:
            continue
        yyyy, mm, dd, hh, mi = g.groups()
        dt = datetime(int(yyyy), int(mm), int(dd), int(hh), int(mi), tzinfo=UTC)
        return dt.isoformat()
    return None


def _parse_jst_datetime(text: str) -> str | None:
    """「YYYY-MM-DD (曜) HH:MM:SS」を +09:00 の ISO 文字列で返す。"""
    m = JST_COMMENT_DT.search(text)
    if not m:
        return None
    d, t = m.groups()
    return f"{d}T{t}+09:00"


def _clean_content(text: str) -> str:
    """本文から日時やIDノイズを除去して整形。"""
    t = " ".join(text.split())
    # 末尾の ID 表記などを除去（例: [ID:xxxx] / [#1234]）
    t = re.sub(r"\s*\[ID:[^\]]+\]\s*$", "", t)
    t = re.sub(r"\s*\[#\w+\]\s*$", "", t)
    # 日時文字列の重複を弱めに除去（完全一致でなくてもOK）
    t = JST_COMMENT_DT.sub("", t).strip()
    return t


# ---- Scrape ----


def fetch_latest_comments(url: str, take: int = 5) -> list[Comment]:
    """対象URLから最新コメントを取得（デフォルト5件）。"""
    s = make_session()
    last_err: Exception | None = None

    for attempt in range(MAX_RETRIES):
        try:
            r = s.get(url, timeout=HTTP_TIMEOUT)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")

            # 1) このサイトの“確実に当たる”優先セレクタ
            #    <form class="pcmt"> ... <ul class="list1 ..."><li class="pcmt">...</li>
            items: list[Tag] = cast(list[Tag], soup.select("form.pcmt ul li.pcmt"))

            # 2) 汎用フォールバック（他サイトでも効くパターン）
            if not items:
                containers = list(
                    cast(
                        list[Tag],
                        soup.select(
                            "#comments, #comment, .comments, "
                            ".commentlist, .pcomment, .comment-area"
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
                for c in containers:
                    items.extend(cast(list[Tag], c.select("li")))
                    items.extend(cast(list[Tag], c.select(".comment")))
                    items.extend(cast(list[Tag], c.select(".comment-item")))
                if not items and containers:
                    items = containers

            now_iso = datetime.now(UTC).isoformat()
            out: list[Comment] = []

            for node in items[: max(take, 0) or 0]:
                full_text = node.get_text(" ", strip=True)
                if not full_text:
                    continue

                # 著者（無ければNoneでOK）
                author_node = node.select_one(
                    ".author, .comment-author, .commenter, .name, cite.fn, .comment-name"
                )
                author = author_node.get_text(strip=True) if author_node else None

                # 日時（このサイトは span.comment_date が信頼できる）
                dt_node = node.select_one("span.comment_date")
                if dt_node:
                    posted_at = _parse_jst_datetime(dt_node.get_text(" ", strip=True))
                else:
                    # time要素 or 旧フォールバック
                    time_node = node.find("time")
                    posted_at = None
                    if time_node:
                        posted_at = time_node.get("datetime") or _extract_datetime_loose(
                            time_node.get_text(" ", strip=True)
                        )
                    if not posted_at:
                        posted_at = _parse_jst_datetime(full_text) or _extract_datetime_loose(
                            full_text
                        )

                content = _clean_content(full_text)
                cid = Comment.mk_id(url, content, posted_at)

                out.append(
                    Comment(
                        comment_id=cid,
                        source_url=url,
                        author=author,
                        content=content,
                        posted_at=posted_at,
                        collected_at=now_iso,
                    )
                )

            # 重複除去
            uniq: dict[str, Comment] = {}
            for c in out:
                uniq[c.comment_id] = c
            return list(uniq.values())[:take]

        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(1.5 * (attempt + 1))

    raise RuntimeError(f"failed to fetch comments: {last_err}")


# ---- CSV I/O ----


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
