from __future__ import annotations

from fastapi.testclient import TestClient

from main import app
from ml_sample.model import CLASS_LABELS

client = TestClient(app)


def test_ml_iris_predict_ok() -> None:
    payload = {
        "sepal_length": 5.1,
        "sepal_width": 3.5,
        "petal_length": 1.4,
        "petal_width": 0.2,
    }
    resp = client.post("/ml/iris/predict", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {"predicted_class", "predicted_label"}
    assert data["predicted_class"] in {0, 1, 2}
    assert data["predicted_label"] in set(CLASS_LABELS)


def test_ml_iris_predict_validation_error() -> None:
    # petal_width を欠けさせて 422 を確認
    payload = {
        "sepal_length": 5.1,
        "sepal_width": 3.5,
        "petal_length": 1.4,
    }
    resp = client.post("/ml/iris/predict", json=payload)
    assert resp.status_code == 422
