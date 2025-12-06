# Iris ML デモのメモ

このプロジェクトの ML デモ部分（Iris 分類）は、次の3レイヤで構成されている。

1. **モデル層 (`ml_sample/model.py`)**
   - scikit-learn の `RandomForestClassifier` を使って Iris データセットを学習する。
   - 学習済みモデルを `models/iris-model.joblib`（など）に保存・読み込みする責務を持つ。
   - 主な役割：
     - データの前処理（特徴量 X / ラベル y の分離）
     - train/test の分割
     - モデルの学習・保存・読み込み

2. **アプリ層 (`ml_sample/api.py`)**
   - FastAPI から呼ばれる「推論用の関数」を定義している。
   - 4 つの特徴量（sepal_length / sepal_width / petal_length / petal_width）を受け取り、
     モデルで予測したクラス（setosa / versicolor / virginica など）を返す。
   - Pydantic モデルを使って、入力の型・範囲のチェックも行う。

3. **エンドポイント層 (`main.py`)**
   - `/ml/iris/predict` エンドポイントを定義している。
   - リクエスト JSON を `ml_sample.api` の Pydantic モデルで受け取り、
     予測ロジックを呼び出してレスポンス JSON を返す。
   - 既存の `/health` や `/version` と同じ FastAPI アプリの一部として動作する。

---

## CLI コマンドとの関係

- `mlops-try train-iris`
  - `automation/cli.py` から `ml_sample.model` の「学習関数」を呼び出し、
    ローカルに Iris モデルファイルを保存する。
  - これによって、API サーバを起動したときに `/ml/iris/predict` が
    学習済みモデルを読み込んで推論できるようになる。

---

## よくある詰まりポイント（自分用メモ）

- **モデルファイルが無い場合**
  - `models/` ディレクトリや `iris-model.joblib` が無いときは、
    先に `mlops-try train-iris` を実行してモデルを作る。
- **scikit-learn が入っていない場合**
  - `pip install -r requirements.txt` をやり直す。
- **API が 422 を返す場合**
  - 入力 JSON のキー名や型（float / int）が間違っていないか確認する。
  - 例：`sepal_length` などのスペルミス、文字列になっている、など。

---

## 自分の理解（簡単まとめ）

- Iris デモは「本格的な ML プロダクト」というより、
  **「scikit-learn + FastAPI + CLI」のひな型** として位置づけている。
- 今後、別のモデルを試したいときは `ml_sample` ディレクトリを
  テンプレとしてコピー・改造していくイメージ。
