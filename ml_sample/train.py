from __future__ import annotations

import argparse
import shutil
from pathlib import Path

DEFAULT_SRC = Path("models/iris.joblib")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Produce an iris model artifact at the requested location."
    )
    p.add_argument(
        "--out",
        type=str,
        required=True,
        help="Output path for model artifact. Example: artifacts/model.joblib",
    )
    p.add_argument(
        "--src",
        type=str,
        default=str(DEFAULT_SRC),
        help="Existing model artifact path to copy from (default: models/iris.joblib)",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out = Path(args.out)
    src = Path(args.src)

    out.parent.mkdir(parents=True, exist_ok=True)

    if not src.exists():
        print(f"[ERROR] source model artifact not found: {src}")
        print("Expected an existing artifact (e.g., models/iris.joblib).")
        return 1

    shutil.copy2(src, out)
    print(f"[OK] model artifact written: {out} (copied from {src})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
