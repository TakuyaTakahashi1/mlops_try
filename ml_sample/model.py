from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
from sklearn.datasets import load_iris
from sklearn.linear_model import LogisticRegression

# プロジェクト直下に models/iris.joblib を置く
MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "iris.joblib"

# クラス番号 -> ラベル名
CLASS_LABELS: tuple[str, str, str] = ("setosa", "versicolor", "virginica")


def train_and_save(model_path: Path | None = None) -> Path:
    """Iris データでロジスティック回帰モデルを学習して保存する。"""
    if model_path is None:
        model_path = MODEL_PATH

    data = load_iris()
    X = data["data"]
    y = data["target"]

    clf = LogisticRegression(max_iter=200)
    clf.fit(X, y)

    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, model_path)
    return model_path


def load_model(model_path: Path | None = None):
    """保存済みモデルを読み込む。"""
    if model_path is None:
        model_path = MODEL_PATH
    return joblib.load(model_path)


def ensure_model(model_path: Path | None = None) -> Path:
    """モデルファイルが無ければ学習して作成し、そのパスを返す。"""
    if model_path is None:
        model_path = MODEL_PATH
    if not model_path.exists():
        return train_and_save(model_path)
    return model_path


def predict(
    sepal_length: float,
    sepal_width: float,
    petal_length: float,
    petal_width: float,
) -> tuple[int, str]:
    """4つの特徴量から Iris のクラス番号とラベル名を予測する。"""
    ensure_model()
    model = load_model()
    X = np.array([[sepal_length, sepal_width, petal_length, petal_width]], dtype=float)
    pred = model.predict(X)
    cls = int(pred[0])
    if 0 <= cls < len(CLASS_LABELS):
        label = CLASS_LABELS[cls]
    else:
        label = "unknown"
    return cls, label


def main() -> int:
    """CLI 用: モデルを学習してパスを表示する。"""
    path = train_and_save()
    print(f"[OK] trained iris model -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
