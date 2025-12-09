from __future__ import annotations

import argparse
from pathlib import Path

from .eval import evaluate_iris_model


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """コマンドライン引数をパースする。"""
    parser = argparse.ArgumentParser(
        description="Evaluate Iris model and export metrics as JSON files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("metrics"),
        help="Directory to store metrics JSON files (default: ./metrics)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Iris モデル評価 CLI のエントリポイント。"""
    args = parse_args(argv)

    result = evaluate_iris_model(output_dir=args.output_dir)

    metrics_path = result.metrics_path
    try:
        metrics_path = metrics_path.relative_to(Path.cwd())
    except ValueError:
        # カレントディレクトリ外の場合はそのまま表示
        pass

    print(f"Metrics saved to: {metrics_path}")
    print(f"Accuracy: {result.accuracy:.4f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
