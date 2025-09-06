from typing import cast

import pytest
import requests
from requests import Session

from automation.scrape_titles import (
    _attr_text,
    _dedup_merge,
    _extract_title,
    _fetch,
    _read_targets,
)


def b(html: str) -> bytes:
    return html.encode("utf-8")


@pytest.mark.parametrize(
    "html, expected",
    [
        (b('<meta property="og:title" content="OG Title"><title>Ignored</title>'), "OG Title"),
        (b("<title>  Hello   World </title>"), "Hello World"),
        (b("<h1> Foo\nBar </h1>"), "Foo Bar"),
        (b('<meta name="title" content="Meta Title">'), "Meta Title"),
        (b("<p>No title here</p>"), None),
    ],
)
def test_extract_title_variants(html: bytes, expected: str | None) -> None:
    assert _extract_title(html) == expected


def test_attr_text_variants() -> None:
    assert _attr_text(" A   B ") == "A B"
    assert _attr_text(["A", "B"]) == "A B"
    assert _attr_text(("A", "B")) == "A B"
    assert _attr_text(None) is None
    assert _attr_text(123) == "123"


def test_read_targets_ignores_comments_invalid(tmp_path) -> None:
    p = tmp_path / "targets.txt"
    p.write_text(
        "# comment\n\nhttps://example.com\nftp://bad\nhttps;//broken\nhttp://ok.example\n",
        encoding="utf-8",
    )
    urls = _read_targets(p)
    assert urls == ["https://example.com", "http://ok.example"]


def test_dedup_merge() -> None:
    base = [("2025-01-01", "u1", "t1")]
    add = [("2025-01-01", "u1", "t1"), ("2025-01-02", "u2", "t2")]
    merged = _dedup_merge(base, add)
    assert merged == [("2025-01-01", "u1", "t1"), ("2025-01-02", "u2", "t2")]


class _DummyResp:
    def __init__(self, content: bytes, ok: bool = True) -> None:
        self.content = content
        self._ok = ok

    def raise_for_status(self) -> None:
        if not self._ok:
            raise requests.exceptions.HTTPError("boom")


class _DummySessionOK:
    def get(self, url: str, timeout: int, allow_redirects: bool):
        return _DummyResp(b("<title>Hi</title>"), ok=True)


class _DummySessionError:
    def get(self, url: str, timeout: int, allow_redirects: bool):
        raise requests.exceptions.ConnectTimeout("timeout")


def test_fetch_success() -> None:
    s = cast(Session, _DummySessionOK())
    assert _fetch(s, "https://example.com") == "Hi"


def test_fetch_error_returns_none() -> None:
    s = cast(Session, _DummySessionError())
    assert _fetch(s, "https://example.com") is None
