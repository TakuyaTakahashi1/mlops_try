from __future__ import annotations

import json
from pathlib import Path

from ml_sample.eval import IrisEvaluationResult, evaluate_iris_model


def test_evaluate_iris_model_creates_metrics_files(tmp_path: Path) -> None:
    """評価を実行するとメトリクスファイルが2つ作られることを確認する。"""
    result: IrisEvaluationResult = evaluate_iris_model(output_dir=tmp_path)

    # 時刻付きファイルが存在すること
    assert result.metrics_path.exists(), "metrics_path が存在しません"

    # iris-latest.json も作られていること
    latest_path = tmp_path / "iris-latest.json"
    assert latest_path.exists(), "iris-latest.json が作成されていません"

    # JSON として読み込めて、accuracy が 0〜1 の範囲にあること
    data = json.loads(result.metrics_path.read_text(encoding="utf-8"))
    assert "accuracy" in data
    assert 0.0 <= data["accuracy"] <= 1.0
    assert data["n_samples"] > 0
