from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from joblib import load
from sklearn.datasets import load_iris
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

from .model import ensure_model


def _load_iris_model() -> Any:
    """
    Iris 用の学習済みモデルを返すヘルパー。

    - ensure_model() が Path を返す場合は joblib.load() で読み込む
    - 既に推論可能なオブジェクトを返す場合はそのまま使う
    """
    model_or_path = ensure_model()
    if isinstance(model_or_path, Path):
        return load(model_or_path)
    return model_or_path


@dataclass
class IrisEvaluationResult:
    """Iris モデル評価の結果を表すデータクラス。"""

    metrics_path: Path
    accuracy: float


def evaluate_iris_model(output_dir: Path | None = None) -> IrisEvaluationResult:
    """
    Iris モデルを評価し、メトリクスを JSON に保存する。

    - output_dir が指定されていればそこに保存
    - 指定されなければ ./metrics 配下に保存
    - 時刻付きファイルと iris-latest.json の 2 つを出力
    """
    iris = load_iris()
    X = iris["data"]
    y_true = iris["target"]

    model: Any = _load_iris_model()
    y_pred = model.predict(X)

    accuracy = float(accuracy_score(y_true, y_pred))
    report = classification_report(y_true, y_pred, output_dict=True)
    cm = confusion_matrix(y_true, y_pred).tolist()

    created_at = datetime.now(UTC).isoformat()

    metrics: dict[str, Any] = {
        "created_at": created_at,
        "n_samples": int(len(y_true)),
        "accuracy": accuracy,
        "classification_report": report,
        "confusion_matrix": cm,
    }

    target_dir = output_dir or Path("metrics")
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    metrics_path = target_dir / f"iris-{timestamp}.json"
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    latest_path = target_dir / "iris-latest.json"
    latest_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    return IrisEvaluationResult(metrics_path=metrics_path, accuracy=accuracy)
