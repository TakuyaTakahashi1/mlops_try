from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import httpx

WIKI_URL = "https://kamikouryaku.net/nightreign_eldenring/"


@dataclass
class NightreignLatestUpdate:
    """攻略Wikiの最新アップデート情報を表すデータクラス。"""

    date_text: str
    title: str
    app_version: str | None
    regulation_version: str | None
    url: str


# 例:
# [2025.12.17]アップデートファイル配信のお知らせ(App Ver. 1.031 / Regulation Ver. 1.03.2)
_DATE_AND_TITLE_RE = re.compile(
    r"\[(\d{4}\.\d{2}\.\d{2})\](.+?App Ver\.\s*[0-9.]+\s*/\s*Regulation Ver\.\s*[0-9.]+)",
    re.DOTALL,
)

_VERSIONS_RE = re.compile(
    r"App Ver\.\s*([0-9.]+)\s*/\s*Regulation Ver\.\s*([0-9.]+)",
)

_DETAIL_URL_RE = re.compile(
    r"https://nightreign\.eldenring\.jp/article/\d+_1\.html",
)


def parse_latest_update(html: str) -> NightreignLatestUpdate:
    """攻略WikiトップのHTMLから「最新アップデート」の一番上を抜き出す。

    - まず「最新アップデート」というセクションを探し、
      その中から `[YYYY.MM.DD]...App Ver.../ Regulation Ver...` を抽出する。
    """
    section_index = html.find("最新アップデート")
    if section_index == -1:
        raise ValueError("「最新アップデート」セクションが見つかりませんでした")

    section_html = html[section_index:]

    date_and_title_match = _DATE_AND_TITLE_RE.search(section_html)
    if not date_and_title_match:
        raise ValueError("最新アップデートの見出しが見つかりませんでした")

    date_text = date_and_title_match.group(1)
    title_part = date_and_title_match.group(2).strip()

    version_match = _VERSIONS_RE.search(title_part)
    if version_match:
        app_version = version_match.group(1)
        regulation_version = version_match.group(2)
    else:
        app_version = None
        regulation_version = None

    url_match = _DETAIL_URL_RE.search(section_html)
    if not url_match:
        raise ValueError("アップデート詳細へのURLが見つかりませんでした")

    url = url_match.group(0)

    return NightreignLatestUpdate(
        date_text=date_text,
        title=title_part,
        app_version=app_version,
        regulation_version=regulation_version,
        url=url,
    )


def fetch_latest_update(
    client: httpx.Client | None = None,
) -> NightreignLatestUpdate:
    """実際にWebからHTMLを取得して最新アップデート情報を返す。"""
    local_client = client or httpx.Client(
        follow_redirects=True,
        timeout=10.0,
    )
    resp = local_client.get(WIKI_URL)
    resp.raise_for_status()
    return parse_latest_update(resp.text)


def save_latest_update_json(path: Path) -> None:
    """最新アップデート情報をJSONファイルとして保存するヘルパー。"""
    update = fetch_latest_update()
    path.write_text(
        json.dumps(asdict(update), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    """CLI入口: JSONで最新アップデート情報を標準出力する。"""
    update = fetch_latest_update()
    print(json.dumps(asdict(update), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
