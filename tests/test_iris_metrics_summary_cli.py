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


def test_metrics_summary_tsv_output(tmp_path: Path) -> None:
    metrics_dir = tmp_path / "metrics"
    metrics_dir.mkdir()

    older = metrics_dir / "iris-20251201-000000.json"
    newer = metrics_dir / "iris-20251202-000000.json"
    latest = metrics_dir / "iris-latest.json"

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
    _write_metrics(
        latest,
        created_at="2025-12-03T00:00:00+00:00",
        accuracy=0.99,
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ml_sample.metrics_summary",
            "--metrics-dir",
            str(metrics_dir),
            "--tsv",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    lines = [line for line in result.stdout.strip().splitlines() if line]

    assert lines[0] == "created_at_utc\taccuracy\tfile"
    # older/newer の順で並んでいること
    assert "\t0.9000\tiris-20251201-000000.json" in lines[1]
    assert "\t0.9500\tiris-20251202-000000.json" in lines[2]
    # latest は履歴には含まれない
    joined = "\n".join(lines)
    assert "iris-latest.json" not in joined
