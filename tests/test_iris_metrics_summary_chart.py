from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _write_metrics(path: Path, created_at: str, accuracy: float) -> None:
    data = {
        "created_at": created_at,
        "accuracy": accuracy,
        "n_samples": 150,
        "classification_report": {},
        "confusion_matrix": [],
    }
    path.write_text(json.dumps(data), encoding="utf-8")


def test_metrics_summary_ascii_chart_output(tmp_path: Path) -> None:
    metrics_dir = tmp_path / "metrics"
    metrics_dir.mkdir()

    older = metrics_dir / "iris-20251201-000000.json"
    newer = metrics_dir / "iris-20251202-000000.json"

    _write_metrics(
        older,
        created_at="2025-12-01T00:00:00+00:00",
        accuracy=0.90,
    )
    _write_metrics(
        newer,
        created_at="2025-12-02T00:00:00+00:00",
        accuracy=0.95,
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ml_sample.metrics_summary",
            "--metrics-dir",
            str(metrics_dir),
            "--ascii-chart",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    lines = [line for line in result.stdout.strip().splitlines() if line]

    # 先頭のヘッダ
    assert lines[0] == "Iris accuracy chart"
    assert lines[1].startswith("----------------")

    # 2 行目以降に日付と accuracy が含まれていること
    joined = "\n".join(lines)
    assert "2025-12-01" in joined
    assert "2025-12-02" in joined
    assert "(0.9000)" in joined
    assert "(0.9500)" in joined
