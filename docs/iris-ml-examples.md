# Iris ML API サンプル集

このドキュメントは、`/ml/iris/predict` エンドポイントを実際に叩くときのサンプルをまとめたもの。

前提:

- モデルが学習済みであること（`mlops-try train-iris` 済み）
- FastAPI サーバが起動していること

```bash
# モデルの学習
source .venv/bin/activate
mlops-try train-iris

# API サーバ起動
uvicorn main:app --reload
# → http://127.0.0.1:8000 で待ち受け
1. curl での呼び出し例
bash
コードをコピーする
curl -X POST "http://127.0.0.1:8000/ml/iris/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "sepal_length": 5.1,
    "sepal_width": 3.5,
    "petal_length": 1.4,
    "petal_width": 0.2
  }'
想定されるレスポンスのイメージ（実際のフィールド名は実装に依存）:

json
コードをコピーする
{
  "class_name": "setosa",
  "class_id": 0,
  "detail": {
    "sepal_length": 5.1,
    "sepal_width": 3.5,
    "petal_length": 1.4,
    "petal_width": 0.2
  }
}
2. Python (httpx) からの呼び出し例
python
コードをコピーする
import httpx

payload = {
    "sepal_length": 5.1,
    "sepal_width": 3.5,
    "petal_length": 1.4,
    "petal_width": 0.2,
}

resp = httpx.post("http://127.0.0.1:8000/ml/iris/predict", json=payload)
resp.raise_for_status()
data = resp.json()

print(data)
# 例:
# {'class_name': 'setosa', 'class_id': 0, ...}
3. エラー例（バリデーション）
例えば、sepal_length を文字列にしてしまうと 422 (Unprocessable Entity) になる。

bash
コードをコピーする
curl -X POST "http://127.0.0.1:8000/ml/iris/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "sepal_length": "5.1",
    "sepal_width": 3.5,
    "petal_length": 1.4,
    "petal_width": 0.2
  }'
FastAPI / Pydantic によって、型エラーとしてレスポンスが返る（バリデーションエラー）。

4. 自分用メモ
まずは mlops-try train-iris を実行してモデルファイルを作っておく。

その後に API を起動し、/ml/iris/predict に対して curl や httpx でリクエストを送る。

Iris デモは「本番用 ML サービス」ではなく、
scikit-learn + FastAPI + CLI をつなげる練習台として使う。
