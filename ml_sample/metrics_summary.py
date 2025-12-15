from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class IrisMetricsRecord:
    """単一の Iris 評価メトリクスを表すレコード。"""

    created_at: datetime
    accuracy: float
    path: Path


def _iter_metrics_files(metrics_dir: Path) -> Iterable[Path]:
    """metrics_dir 配下の iris-*.json（latest 以外）を列挙する。"""
    if not metrics_dir.exists():
        # ジェネレータ関数なので値付き return は NG
        return

    for path in metrics_dir.glob("iris-*.json"):
        if path.name == "iris-latest.json":
            continue
        if not path.is_file():
            continue
        yield path


def load_iris_metrics_history(metrics_dir: Path | None = None) -> list[IrisMetricsRecord]:
    """
    Iris 評価メトリクスの履歴を読み込み、created_at 昇順で返す。

    - metrics_dir が None の場合は ./metrics を見る
    - 作成日時 created_at と accuracy を取り出してソート
    """
    base_dir = metrics_dir or Path("metrics")
    records: list[IrisMetricsRecord] = []

    for path in _iter_metrics_files(base_dir):
        data = json.loads(path.read_text(encoding="utf-8"))
        created_at_raw = data.get("created_at")
        accuracy_raw = data.get("accuracy")

        if not created_at_raw or accuracy_raw is None:
            # 想定外フォーマットはスキップ
            continue

        created_at = datetime.fromisoformat(created_at_raw)
        if created_at.tzinfo is None:
            # 念のため UTC を付与
            created_at = created_at.replace(tzinfo=UTC)

        accuracy = float(accuracy_raw)
        records.append(
            IrisMetricsRecord(
                created_at=created_at,
                accuracy=accuracy,
                path=path,
            ),
        )

    records.sort(key=lambda r: r.created_at)
    return records


def _format_row_table(record: IrisMetricsRecord) -> str:
    """テーブル用の 1 行をフォーマットする。"""
    ts = record.created_at.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    acc = f"{record.accuracy:.4f}"
    name = record.path.name
    return f"{ts}  |  {acc:>7}  |  {name}"


def _format_row_tsv(record: IrisMetricsRecord) -> str:
    """TSV 用の 1 行をフォーマットする。"""
    ts = record.created_at.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    acc = f"{record.accuracy:.4f}"
    name = record.path.name
    return f"{ts}\t{acc}\t{name}"


def _format_row_chart(record: IrisMetricsRecord) -> str:
    """ASCII チャート用の 1 行をフォーマットする。"""
    date_label = record.created_at.astimezone(UTC).strftime("%Y-%m-%d")
    # 0.0〜1.0 の accuracy を 0〜40 個のバーに変換
    bar_len = max(0, min(40, int(round(record.accuracy * 40))))
    bar = "#" * bar_len
    acc = f"{record.accuracy:.4f}"
    return f"{date_label} | {bar} ({acc})"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize Iris evaluation metrics history.",
    )
    parser.add_argument(
        "--metrics-dir",
        type=Path,
        default=Path("metrics"),
        help="Directory that contains iris-*.json (default: ./metrics)",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--tsv",
        action="store_true",
        help="Output summary in TSV format instead of table.",
    )
    group.add_argument(
        "--ascii-chart",
        action="store_true",
        help="Output accuracy as a simple ASCII bar chart.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Iris 評価メトリクス履歴を一覧表示する CLI。"""
    args = parse_args(argv)
    metrics_dir: Path = args.metrics_dir
    use_tsv: bool = args.tsv
    use_chart: bool = args.ascii_chart

    records = load_iris_metrics_history(metrics_dir)

    if not records:
        print(f"No Iris metrics found in {metrics_dir}")
        return 0

    if use_chart:
        print("Iris accuracy chart")
        print("-------------------")
        for rec in records:
            print(_format_row_chart(rec))
        return 0

    if use_tsv:
        print("created_at_utc\taccuracy\tfile")
        for rec in records:
            print(_format_row_tsv(rec))
    else:
        print("created_at (UTC)        | accuracy | file")
        print("------------------------+----------+---------------------------")
        for rec in records:
            print(_format_row_table(rec))

        latest_path = metrics_dir / "iris-latest.json"
        if latest_path.exists():
            print()
            print(f"Latest: {latest_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
