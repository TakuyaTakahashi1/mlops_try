from __future__ import annotations

import json
import logging
import time
from contextlib import contextmanager
from typing import Any

LOGGER_NAME = "mlops_app"

logger = logging.getLogger(LOGGER_NAME)
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(message)s"))
logger.handlers.clear()
logger.addHandler(handler)


def log_event(event: str, **fields: Any) -> None:
    """
    構造化ログを1行JSONで出すためのヘルパー。

    例:
        log_event("scrape_finished", count=123, duration_ms=456)
    """
    record: dict[str, Any] = {
        "event": event,
        "ts": time.time(),
        **fields,
    }
    logger.info(json.dumps(record, ensure_ascii=False))


@contextmanager
def time_block(event: str, **fields: Any):
    """
    処理時間を計測しつつ、成功/失敗も含めてログに出すコンテキストマネージャ。

    例:
        with time_block("scrape_titles", target="a16z"):
            run_scraper()
    """
    start = time.time()
    try:
        yield
        duration = time.time() - start
        log_event(
            event,
            duration_ms=int(duration * 1000),
            success=True,
            **fields,
        )
    except Exception as exc:  # noqa: BLE001
        duration = time.time() - start
        log_event(
            event,
            duration_ms=int(duration * 1000),
            success=False,
            error=str(exc),
            **fields,
        )
        raise
