from __future__ import annotations

import argparse
from collections.abc import Iterable
from pathlib import Path

from automation.comments_core import fetch_latest_comments, write_csvs


def iter_urls(args: argparse.Namespace) -> Iterable[str]:
    if args.url:
        yield args.url.strip()
        return
    # fallback: targets ファイル（無ければエラー）
    targets = Path(args.targets)
    if not targets.exists():
        raise FileNotFoundError(f"targets file not found: {targets} (or pass --url)")
    for line in targets.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            yield line


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--url", help="single URL to scrape (overrides targets)")
    p.add_argument(
        "--targets",
        default="automation/comments_targets.txt",
        help="targets file (one URL per line)",
    )
    p.add_argument("--outdir", default="data")
    p.add_argument("--take", type=int, default=5)
    args = p.parse_args()

    urls: list[str] = list(iter_urls(args))
    all_rows = []
    for u in urls:
        rows = fetch_latest_comments(u, take=args.take)
        all_rows.extend(rows)

    write_csvs(all_rows, outdir=args.outdir)
    print(f"[OK] collected={len(all_rows)} -> {args.outdir}/comments.csv (dedup)")


if __name__ == "__main__":
    main()
