from __future__ import annotations

import argparse

import pandas as pd

from automation.storage import search_articles


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--q", type=str, default=None, help="keyword (LIKE match, case-insensitive)")
    ap.add_argument(
        "--date-from", type=str, default=None, help="inclusive ISO like 2025-10-01T00:00:00"
    )
    ap.add_argument(
        "--date-to", type=str, default=None, help="exclusive ISO like 2025-11-01T00:00:00"
    )
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--order", type=str, default="desc", choices=["asc", "desc"])
    ap.add_argument("--fmt", type=str, default="table", choices=["table", "csv", "json"])
    args = ap.parse_args(argv)

    df = search_articles(
        q=args.q,
        date_from=args.date_from,
        date_to=args.date_to,
        limit=args.limit,
        offset=args.offset,
        order=args.order,
    )

    if args.fmt == "csv":
        print(df.to_csv(index=False))
    elif args.fmt == "json":
        print(df.to_json(orient="records", force_ascii=False))
    else:
        # pretty table（pandasの出力で簡易表示）
        with pd.option_context("display.max_rows", None, "display.max_colwidth", 200):
            print(df)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
