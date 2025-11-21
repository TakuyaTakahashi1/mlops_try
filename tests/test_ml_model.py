from __future__ import annotations

from pathlib import Path

from ml_sample.model import MODEL_PATH, predict, train_and_save


def test_train_and_save_creates_model(tmp_path: Path) -> None:
    # 一時ディレクトリにモデルを作らせる
    tmp_model = tmp_path / "iris.joblib"
    out = train_and_save(model_path=tmp_model)
    assert out == tmp_model
    assert tmp_model.exists()


def test_predict_returns_valid_class(monkeypatch) -> None:
    # モデルがまだ無ければ学習
    if not MODEL_PATH.exists():
        train_and_save()

    # 適当な特徴量を入れて 0/1/2 のどれかが返ることを確認
    pred = predict(5.1, 3.5, 1.4, 0.2)
    assert pred in {0, 1, 2}
