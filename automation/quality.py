from __future__ import annotations

import datetime as dt
import os
import sqlite3
import sys
import textwrap
from dataclasses import dataclass

SQLITE_PATH = "data/titles.sqlite"  # articles(url, title, fetched_at)


@dataclass(frozen=True)
class Rules:
    min_new_rows: int = int(os.getenv("QC_MIN_NEW_ROWS", "1"))  # 今日増えた最小件数
    max_dup_rate: float = float(os.getenv("QC_MAX_DUP_RATE", "0.10"))  # 10%
    allow_empty_title: bool = False


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(SQLITE_PATH)


def _metrics(conn: sqlite3.Connection) -> dict[str, int | float]:
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM articles")
    rows = int(cur.fetchone()[0])

    cur.execute("SELECT COUNT(DISTINCT url) FROM articles")
    distinct_urls = int(cur.fetchone()[0])

    cur.execute("SELECT COUNT(*) FROM articles WHERE title IS NULL OR TRIM(title) = ''")
    empty_titles = int(cur.fetchone()[0])

    dup_rate = 0.0 if rows == 0 else 1.0 - (distinct_urls / rows)
    return {
        "rows": rows,
        "distinct_urls": distinct_urls,
        "dup_rate": dup_rate,
        "empty_titles": empty_titles,
    }


def _since_midnight(conn: sqlite3.Connection) -> int:
    # fetched_at の先頭10文字が今日の日付(UTC)のものをカウント
    cur = conn.cursor()
    start_date = dt.datetime.now(dt.UTC).date().isoformat()
    cur.execute("SELECT COUNT(*) FROM articles WHERE substr(fetched_at,1,10)=?", (start_date,))
    return int(cur.fetchone()[0])


def run_check(rules: Rules) -> tuple[bool, str]:
    if not os.path.exists(SQLITE_PATH):
        md = f"### Data Quality Report ❌\nDB not found: `{SQLITE_PATH}`"
        return False, md

    with _connect() as conn:
        m = _metrics(conn)
        new_rows_today = _since_midnight(conn)

    problems: list[str] = []
    if new_rows_today < rules.min_new_rows:
        problems.append(f"- 新規件数が少ない: **{new_rows_today} < {rules.min_new_rows}**")
    if m["dup_rate"] > rules.max_dup_rate:
        problems.append(f"- 重複率が高い: **{m['dup_rate']:.1%} > {rules.max_dup_rate:.1%}**")
    if not rules.allow_empty_title and m["empty_titles"] > 0:
        problems.append(f"- 空タイトルあり: **{m['empty_titles']}件**")

    ok = len(problems) == 0
    badge = "✅" if ok else "❌"
    problems_text = "\n".join(problems) if problems else "No problems detected."

    md = textwrap.dedent(
        f"""
        ### Data Quality Report {badge}
        - rows: **{m["rows"]}**
        - distinct_urls: **{m["distinct_urls"]}**
        - dup_rate: **{m["dup_rate"]:.1%}**
        - empty_titles: **{m["empty_titles"]}**
        - new_rows_today: **{new_rows_today}**

        **Rules**
        - min_new_rows: {rules.min_new_rows}
        - max_dup_rate: {rules.max_dup_rate:.2f}
        - allow_empty_title: {rules.allow_empty_title}

        {problems_text}
        """
    ).strip()
    return ok, md


def main() -> None:
    ok, md = run_check(Rules())
    print(md)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
