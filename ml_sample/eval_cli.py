from __future__ import annotations

import argparse
import json
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
    parser.add_argument(
        "--model",
        type=Path,
        default=None,
        help="Path to model artifact (joblib). If omitted, ensure_model() is used.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Write metrics JSON to this single file as well (e.g., artifacts/metrics.json).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Iris モデル評価 CLI のエントリポイント。"""
    args = parse_args(argv)

    result = evaluate_iris_model(output_dir=args.output_dir, model_path=args.model)

    # --out が指定されていれば、そのパスにも metrics を保存する
    if args.out is not None:
        data = json.loads(result.metrics_path.read_text(encoding="utf-8"))
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

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
