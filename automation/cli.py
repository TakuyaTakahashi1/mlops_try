from __future__ import annotations

import sys
from collections.abc import Sequence

from . import scrape_titles


def _print_usage() -> None:
    print("Usage: mlops-try <command>")
    print()
    print("Commands:")
    print("  scrape-titles   Scrape article titles defined in automation/targets.txt")


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the CLI.

    Examples:
        python -m automation.cli scrape-titles
        mlops-try scrape-titles   (after pip install -e .)
    """
    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        _print_usage()
        return 1

    cmd = argv[0]

    if cmd == "scrape-titles":
        return scrape_titles.main()

    print(f"Unknown command: {cmd}")
    print()
    _print_usage()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
