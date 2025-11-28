from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_iris_predict_valid_request() -> None:
    """正常系: 4つの特徴量を渡すと、200 と予測結果が返る。"""
    payload = {
        "sepal_length": 5.1,
        "sepal_width": 3.5,
        "petal_length": 1.4,
        "petal_width": 0.2,
    }
    resp = client.post("/ml/iris/predict", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert "predicted_class" in body
    assert "predicted_label" in body
    # 型だけ軽くチェック
    assert isinstance(body["predicted_class"], int)
    assert isinstance(body["predicted_label"], str)


def test_iris_predict_missing_field() -> None:
    """異常系: petal_width を欠けさせると 422 が返る。"""
    payload = {
        "sepal_length": 5.1,
        "sepal_width": 3.5,
        "petal_length": 1.4,
        # "petal_width" が無い
    }
    resp = client.post("/ml/iris/predict", json=payload)
    assert resp.status_code == 422


def test_iris_predict_invalid_type() -> None:
    """異常系: 数値のはずの項目に文字列を入れると 422 が返る。"""
    payload = {
        "sepal_length": "invalid",
        "sepal_width": 3.5,
        "petal_length": 1.4,
        "petal_width": 0.2,
    }
    resp = client.post("/ml/iris/predict", json=payload)
    assert resp.status_code == 422
