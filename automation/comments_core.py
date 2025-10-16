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
from bs4.element import Tag, NavigableString

# --- HTTP / Fetch -------------------------------------------------------------

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "ja-JP,ja;q=0.9,en;q=0.8",
    # キャッシュ無効化（CDN/RP 回避）
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
}

HTTP_TIMEOUT = 20
MAX_RETRIES = 3


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(DEFAULT_HEADERS)
    return s


def _fetch_html(url: str) -> str:
    """
    強いキャッシュバイパスつきでHTMLを取得。
    """
    s = make_session()
    # タイムスタンプを付与してCDNキャッシュも避ける
    r = s.get(url, params={"_": int(time.time())}, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    return r.text


# --- モデル -------------------------------------------------------------------

@dataclass
class Comment:
    comment_id: str
    source_url: str
    author: str | None
    content: str
    posted_at: str | None  # ISO文字列 or None
    collected_at: str      # UTC ISO

    @staticmethod
    def mk_id(source_url: str, content: str, posted_at: str | None) -> str:
        base = f"{source_url}|{posted_at or ''}|{content.strip()}"
        return hashlib.sha1(base.encode("utf-8")).hexdigest()


# --- パース系ユーティリティ ----------------------------------------------------

# 例: "2025-10-14 (火) 00:55:22" / "2025-10-14 (火) 00:55"
RE_JA_DT = re.compile(
    r"(?P<y>\d{4})-(?P<m>\d{1,2})-(?P<d>\d{1,2}).*?(?P<h>\d{1,2}):(?P<mi>\d{2})(?::(?P<s>\d{2}))?"
)

# 例: "2025/10/14 00:55" / "2025-10-14 00:55"
RE_SIMPLE_DT = re.compile(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})\s+(\d{1,2}):(\d{2})")


def _to_utc_iso_from_jst(y: int, m: int, d: int, h: int, mi: int, s: int = 0) -> str:
    jst = timezone(timedelta(hours=9))
    dt = datetime(y, m, d, h, mi, s, tzinfo=jst)
    return dt.astimezone(UTC).isoformat()


def _extract_datetime(text: str) -> str | None:
    """
    テキストから日時を抽出してUTC ISOにして返す。
    まず日本語表記（曜日や秒を含む）を試し、次にシンプルな表記を試す。
    成功しなければ None。
    """
    m = RE_JA_DT.search(text)
    if m:
        y = int(m.group("y"))
        mo = int(m.group("m"))
        d = int(m.group("d"))
        h = int(m.group("h"))
        mi = int(m.group("mi"))
        s = int(m.group("s") or 0)
        return _to_utc_iso_from_jst(y, mo, d, h, mi, s)

    m2 = RE_SIMPLE_DT.search(text.replace("-", "/"))
    if m2:
        y, mo, d, h, mi = map(int, m2.groups())
        return _to_utc_iso_from_jst(y, mo, d, h, mi, 0)

    return None


def _text_collapse(node: Tag | NavigableString | None) -> str:
    if not node:
        return ""
    if isinstance(node, NavigableString):
        return " ".join(str(node).split())
    return " ".join(node.get_text(" ", strip=True).split())


# --- メイン処理 ----------------------------------------------------------------

def fetch_latest_comments(url: str, take: int = 5) -> list[Comment]:
    """
    指定URLから最新コメントを最大 `take` 件取得。
    優先: 対象サイトの「最新20件」ブロック (form.pcmt ul li.pcmt)
    フォールバック: 汎用的なコメントセレクタ
    """
    last_err: Exception | None = None

    for attempt in range(MAX_RETRIES):
        try:
            html = _fetch_html(url)
            soup = BeautifulSoup(html, "lxml")

            # 1) 対象サイトの「最新20件」優先
            li_nodes: list[Tag] = cast(list[Tag], soup.select("form.pcmt ul li.pcmt"))

            comments: list[Comment] = []
            now_iso = datetime.now(UTC).isoformat()

            if li_nodes:
                for li in li_nodes:
                    text = _text_collapse(li)
                    if not text:
                        continue

                    # authorは匿名掲示板形式なので空にする（必要なら抽出ロジック追加）
                    author = None

                    # 日付は .comment_date を優先→無ければ全文から抽出
                    tnode = li.select_one(".comment_date")
                    dt = _extract_datetime(_text_collapse(tnode)) or _extract_datetime(text)

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

            # 2) フォールバック（一般的なコメント領域）
            if not comments:
                # コメントコンテナ候補
                containers = list(
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
                        containers = [nxt] if isinstance(nxt, Tag) else []

                items: list[Tag] = []
                for cont in containers:
                    items.extend(cast(list[Tag], cont.select("li")))
                    items.extend(cast(list[Tag], cont.select(".comment")))
                    items.extend(cast(list[Tag], cont.select(".comment-item")))
                if not items and containers:
                    items = containers

                for node in items:
                    text = _text_collapse(node)
                    if not text:
                        continue
                    author_node = node.select_one(".author, .comment-author, .commenter, .name")
                    author = _text_collapse(author_node) or None

                    dt: str | None = None
                    time_node = node.find("time")
                    if isinstance(time_node, Tag):
                        attr = time_node.get("datetime")
                        dt = attr if isinstance(attr, str) else None
                        if not dt:
                            dt = _extract_datetime(_text_collapse(time_node))
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

            # 重複除去して先頭 take 件
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
