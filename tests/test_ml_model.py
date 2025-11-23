from __future__ import annotations

from pathlib import Path

from ml_sample.model import CLASS_LABELS, MODEL_PATH, ensure_model, predict, train_and_save


def test_train_and_save_creates_model(tmp_path: Path) -> None:
    # 一時ディレクトリにモデルを作らせる
    tmp_model = tmp_path / "iris.joblib"
    out = train_and_save(model_path=tmp_model)
    assert out == tmp_model
    assert tmp_model.exists()


def test_ensure_model_creates_when_missing(tmp_path: Path) -> None:
    tmp_model = tmp_path / "iris.joblib"
    assert not tmp_model.exists()
    out = ensure_model(model_path=tmp_model)
    assert out == tmp_model
    assert tmp_model.exists()


def test_predict_returns_class_and_label() -> None:
    # 本体の MODEL_PATH にモデルが無ければ作る
    ensure_model(MODEL_PATH)
    cls, label = predict(5.1, 3.5, 1.4, 0.2)
    assert cls in {0, 1, 2}
    assert label in set(CLASS_LABELS)
