from __future__ import annotations

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


def _format_row(record: IrisMetricsRecord) -> str:
    """テーブル用の 1 行をフォーマットする。"""
    ts = record.created_at.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    acc = f"{record.accuracy:.4f}"
    name = record.path.name
    return f"{ts}  |  {acc:>7}  |  {name}"


def main() -> int:
    """Iris 評価メトリクス履歴を一覧表示する CLI。"""
    metrics_dir = Path("metrics")
    records = load_iris_metrics_history(metrics_dir)

    if not records:
        print("No Iris metrics found in ./metrics")
        return 0

    print("created_at (UTC)        | accuracy | file")
    print("------------------------+----------+---------------------------")
    for rec in records:
        print(_format_row(rec))

    latest_path = metrics_dir / "iris-latest.json"
    if latest_path.exists():
        print()
        print(f"Latest: {latest_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
