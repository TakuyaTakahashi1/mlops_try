from __future__ import annotations

import argparse

from automation.comments_core import fetch_latest_comments, write_csvs


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--url", required=True, help="コメントを取得するページURL")
    p.add_argument("--outdir", default="data")
    p.add_argument("--take", type=int, default=5)
    args = p.parse_args()

    comments = fetch_latest_comments(args.url, take=args.take)
    write_csvs(comments, outdir=args.outdir)

    print(f"[OK] collected={len(comments)} -> {args.outdir}/comments.csv (dedup)")
    for i, c in enumerate(comments, 1):
        print(f"[{i}] {c.posted_at or 'unknown'} | {c.author or '-'} | {c.content[:80]}")


if __name__ == "__main__":
    main()
