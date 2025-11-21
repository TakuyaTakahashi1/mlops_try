from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
from sklearn.datasets import load_iris
from sklearn.linear_model import LogisticRegression

# プロジェクト直下に models/iris.joblib を置く
MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "iris.joblib"


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


def predict(
    sepal_length: float,
    sepal_width: float,
    petal_length: float,
    petal_width: float,
) -> int:
    """4つの特徴量から Iris のクラス（0/1/2）を予測する。"""
    model = load_model()
    X = np.array([[sepal_length, sepal_width, petal_length, petal_width]], dtype=float)
    pred = model.predict(X)
    return int(pred[0])


def main() -> int:
    """CLI 用: モデルを学習してパスを表示する。"""
    path = train_and_save()
    print(f"[OK] trained iris model -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
