from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from automation import scrape_titles


def _cmd_scrape_titles(args: argparse.Namespace) -> int:
    """既存のタイトルスクレイピング."""
    return scrape_titles.main()


def _cmd_train_iris(args: argparse.Namespace) -> int:
    """
    Iris モデルの再学習コマンド.

    - リポジトリルートを sys.path に追加して ml_sample を import
    - ml_sample.model.ensure_model() などを呼び出して models/iris.joblib を保存
    """
    try:
        # プロジェクトルートを import パスに追加
        project_root = Path(__file__).resolve().parents[1]
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        # ml_sample/model.py から学習用の関数を呼ぶ想定
        from ml_sample import model  # type: ignore[import]

        if hasattr(model, "ensure_model"):
            path = model.ensure_model()
        elif hasattr(model, "train_and_save"):
            path = model.train_and_save()
        else:
            raise RuntimeError(
                "ml_sample.model に ensure_model() も train_and_save() も見つかりませんでした。"
            )

        p = Path(path)
        print(f"[OK] trained Iris model saved to: {p}")
        return 0
    except Exception as e:  # pragma: no cover - 失敗時はメッセージだけ
        print(f"[ERR] failed to train iris model: {e}")
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mlops-try",
        description="Utilities for the mlops_try project (scraping, ML training, etc.).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # A: scrape-titles
    p_scrape = sub.add_parser(
        "scrape-titles",
        help="Scrape article titles and update CSV files.",
    )
    p_scrape.set_defaults(func=_cmd_scrape_titles)

    # B: train-iris
    p_train = sub.add_parser(
        "train-iris",
        help="Train Iris ML model and save it under models/iris.joblib.",
    )
    p_train.set_defaults(func=_cmd_train_iris)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 1
    return int(func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
