from __future__ import annotations

import csv
import hashlib
import os
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
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

HTTP_TIMEOUT = 20
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
    posted_at: str | None  # ISO (UTC) or None
    collected_at: str  # ISO (UTC)

    @staticmethod
    def mk_id(source_url: str, content: str, posted_at: str | None) -> str:
        base = f"{source_url}|{posted_at or ''}|{content.strip()}"
        return hashlib.sha1(base.encode("utf-8")).hexdigest()


# 例: 2025-10-13 (月) 22:56:57
JST_COMMENT_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})\s+\([^)]*\)\s+(\d{2}):(\d{2}):(\d{2})")


def _extract_datetime_any(text: str) -> str | None:
    """
    ページの日本語表記日時（JST）や 2025/10/13 22:56 などを拾って UTC ISO へ。
    """
    m = JST_COMMENT_RE.search(text)
    if m:
        yyyy, MM, dd, hh, mi, ss = map(int, m.groups())
        jst = timezone(timedelta(hours=9))
        dt = datetime(yyyy, MM, dd, hh, mi, ss, tzinfo=jst).astimezone(UTC)
        return dt.isoformat()

    # フォールバック: 2025/10/13 22:56（秒なし）
    m2 = re.search(r"(\d{4})/(\d{1,2})/(\d{1,2})\s+(\d{1,2}):(\d{2})", text)
    if m2:
        yyyy, MM, dd, hh, mi = map(int, m2.groups())
        jst = timezone(timedelta(hours=9))
        dt = datetime(yyyy, MM, dd, hh, mi, 0, tzinfo=jst).astimezone(UTC)
        return dt.isoformat()
    return None


def _posted_at_from_node(node: Tag) -> str | None:
    """
    ノード内の .comment_date や <time> から日時文字列を抽出し UTC ISO へ。
    mypy のために AttributeValueList を避けるガードを置く。
    """
    # 1) <span class="comment_date">…</span>
    cdate = node.select_one(".comment_date")
    if isinstance(cdate, Tag):
        text = cdate.get_text(" ", strip=True)
        if text:
            iso = _extract_datetime_any(text)
            if iso:
                return iso

    # 2) <time datetime="...">
    t = node.find("time")
    if isinstance(t, Tag):
        raw_val = t.get("datetime")
        dt_attr: str | None = raw_val if isinstance(raw_val, str) else None
        if dt_attr:
            # datatime 属性は UTC 相当想定。形式が不定のため、失敗時は無視。
            try:
                # ここで秒やタイムゾーン有無に揺れがある想定なので、雑に置換して重み付け
                # （ISOの場合はそのまま通る）
                return datetime.fromisoformat(dt_attr).astimezone(UTC).isoformat()
            except Exception:
                pass
        # テキストにも日時が入るケース
        txt = t.get_text(" ", strip=True)
        iso = _extract_datetime_any(txt)
        if iso:
            return iso

    # 3) ノード全体テキストから最後の手掛かり
    txt = node.get_text(" ", strip=True)
    return _extract_datetime_any(txt)


def fetch_latest_comments(url: str, take: int = 5) -> list[Comment]:
    """
    - “最新の20件を表示しています” ブロック（フォーム直下）を最優先:
        selector: form.pcmt ul li.pcmt
    - 一般的コメントの予備: #comments, #comment, .comments, .commentlist など
    """
    s = make_session()
    last_err: Exception | None = None

    for attempt in range(MAX_RETRIES):
        try:
            r = s.get(url, timeout=HTTP_TIMEOUT)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")

            # まず「最新の20件」フォーム配下リスト
            items: list[Tag] = cast(list[Tag], soup.select("form.pcmt ul li.pcmt"))

            # それでもゼロなら一般的コンテナから拾う
            if not items:
                containers = cast(
                    list[Tag],
                    soup.select(
                        "#comments, #comment, .comments, .commentlist, .pcomment, .comment-area"
                    ),
                )
                for c in containers:
                    items.extend(cast(list[Tag], c.select("li")))
                    items.extend(cast(list[Tag], c.select(".comment")))
                    items.extend(cast(list[Tag], c.select(".comment-item")))
                if not items and containers:
                    items = containers  # container 自体が一件

            comments: list[Comment] = []
            now_iso = datetime.now(UTC).isoformat()

            for node in items:
                # 連投対策で整形したテキスト
                text = " ".join(node.get_text(" ", strip=True).split())
                if not text:
                    continue

                # author は明確に取れないことが多いので None を基本（必要なら強化）
                author_node = node.select_one(".author, .comment-author, .commenter, .name")
                author = author_node.get_text(strip=True) if isinstance(author_node, Tag) else None

                posted_iso = _posted_at_from_node(node)

                cid = Comment.mk_id(url, text, posted_iso)
                comment_obj = Comment(
                    comment_id=cid,
                    source_url=url,
                    author=author,
                    content=text,
                    posted_at=posted_iso,
                    collected_at=now_iso,
                )
                comments.append(comment_obj)

            # 重複除去
            uniq: dict[str, Comment] = {}
            for c in comments:
                uniq[c.comment_id] = c

            return list(uniq.values())[:take]

        except Exception as e:  # noqa: BLE001
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
