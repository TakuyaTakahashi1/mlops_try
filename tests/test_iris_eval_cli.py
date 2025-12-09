from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_eval_cli_creates_metrics_and_prints_accuracy(tmp_path: Path) -> None:
    """CLI から評価を実行すると、メトリクスと Accuracy 表示が行われることを確認する。"""
    result = subprocess.run(
        [sys.executable, "-m", "ml_sample.eval_cli", "--output-dir", str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    # 標準出力にキーワードが含まれていること
    stdout = result.stdout
    assert "Metrics saved to:" in stdout
    assert "Accuracy:" in stdout

    # 出力ディレクトリにメトリクスファイルが作成されていること
    files = list(tmp_path.iterdir())
    assert files, "output_dir にファイルが作成されていません"

    latest_path = tmp_path / "iris-latest.json"
    assert latest_path.exists(), "iris-latest.json が作成されていません"
