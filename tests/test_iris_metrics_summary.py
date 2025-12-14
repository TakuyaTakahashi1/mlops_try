from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from ml_sample.metrics_summary import IrisMetricsRecord, load_iris_metrics_history


def _write_metrics(path: Path, created_at: str, accuracy: float) -> None:
    data = {
        "created_at": created_at,
        "accuracy": accuracy,
        "n_samples": 150,
        "classification_report": {},
        "confusion_matrix": [],
    }
    path.write_text(json.dumps(data), encoding="utf-8")


def test_load_iris_metrics_history_sorts_by_created_at(tmp_path: Path) -> None:
    # 古い方
    older = tmp_path / "iris-20251201-000000.json"
    _write_metrics(
        older,
        created_at="2025-12-01T00:00:00+00:00",
        accuracy=0.90,
    )

    # 新しい方
    newer = tmp_path / "iris-20251202-000000.json"
    _write_metrics(
        newer,
        created_at="2025-12-02T00:00:00+00:00",
        accuracy=0.95,
    )

    # latest は履歴からは除外される
    latest = tmp_path / "iris-latest.json"
    _write_metrics(
        latest,
        created_at="2025-12-03T00:00:00+00:00",
        accuracy=0.99,
    )

    records = load_iris_metrics_history(tmp_path)

    assert len(records) == 2
    assert isinstance(records[0], IrisMetricsRecord)
    assert records[0].path == older
    assert records[1].path == newer
    assert records[0].accuracy == 0.90
    assert records[1].accuracy == 0.95

    # created_at が datetime で、UTC 付きになっていること
    assert isinstance(records[0].created_at, datetime)
    assert records[0].created_at.tzinfo is not None
    assert records[0].created_at.tzinfo == UTC
