# mlops-try

[![CI](https://github.com/TakuyaTakahashi1/mlops_try/actions/workflows/ci.yml/badge.svg)](https://github.com/TakuyaTakahashi1/mlops_try/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11-blue)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

個人の学習用に作っている **「スクレイピング + API + CI/CD + 観測性 + ML デモ」練習プロジェクト** です。
URL リストから記事タイトルを定期収集し、CSV/SQLite に蓄積しつつ、FastAPI 経由で検索できるようにしています。
一部では機械学習（Iris データを使った分類モデル）のデモAPIも提供しています。

転職時のポートフォリオとして、次のポイントを意識しています。

- 型付き・テスト付きの API（FastAPI + mypy + pytest）
- GitHub Actions による自動テスト・Lint（ruff / pytest-cov）
- スクレイピングの安定化（リトライ・重複排除・日次/累積）
- 観測性（構造化ログ・ヘルスチェック）
- パッケージ化 & CLI 化（`mlops-try` コマンド）
- 小さな ML デモ（Iris データ）を既存APIに組み込む

---

## クイックスタート

FastAPI + mypy + pytest + GitHub Actions のサンプルとしても使えます。

- 起動: `uvicorn main:app --reload`
- テスト: `pytest -q`
- 型チェック: `mypy .`
- API ドキュメント: `http://127.0.0.1:8000/docs`

---

## 主な構成

- `main.py` : FastAPI アプリ本体（/health, /version, /articles, /ml/iris/predict など）
- `automation/` : スクレイピング・検索ロジック
  - `scrape_titles.py` : `titles.csv` を更新するスクレイパ（URLリスト→タイトル収集）
  - `storage.py` : 記事検索ロジック（SQLite/FTS）
  - `cli.py` : `mlops-try` コマンドのエントリポイント
  - `observability.py` : 構造化ログ / 計測
- `ml_sample/` : ML デモ用モジュール
  - `model.py` : Iris データで学習したモデルの保存・読み込み・予測
- `data/` : 収集したデータ（`daily/`, `titles.csv` など）
- `tests/` : pytest テスト（API, スクレイピング, ML デモ）
- `pyproject.toml` : パッケージ定義 & CLI エントリポイント
- `requirements.txt` : ランタイム依存関係
- `.env.example` : 環境変数サンプル（`.env` の雛形）
- `Dockerfile` / `docker-compose.yml` : コンテナ実行用設定
- `.github/workflows/` : CI/CD ワークフロー

---

## セットアップ

- リポジトリ取得

  - `git clone https://github.com/TakuyaTakahashi1/mlops_try.git`
  - `cd mlops_try`

- 仮想環境と依存インストール

  - `python -m venv .venv`
  - `source .venv/bin/activate`
  - `python -m pip install --upgrade pip`
  - `python -m pip install -r requirements.txt`
  - `python -m pip install -e .`

- 環境変数（`.env`）は、`.env.example` からコピーして使う想定です。

  - `cp .env.example .env`
  - `.env` を開いて、`DB_URL` / `API_KEY` などを自分の環境に合わせて編集

---

## 使い方

### 1. API サーバ

- `source .venv/bin/activate`
- `uvicorn main:app --reload`

エンドポイント例:

- `http://127.0.0.1:8000/health` : ヘルスチェック
- `http://127.0.0.1:8000/version` : バージョン情報
- `http://127.0.0.1:8000/docs` : Swagger UI（全エンドポイントの確認）

### 2. CLI でスクレイプ

- `source .venv/bin/activate`
- `mlops-try scrape-titles`

挙動:

- 対象 URL: `automation/targets.txt`
- 出力:
  - `data/daily/titles-YYYYMMDD.csv`
  - `data/titles.csv`（重複排除済み）

### 3. ML デモ（Iris 分類）

このリポジトリには、機械学習の最小ループ（学習→保存→予測→API→テスト）を確認するための **Iris データのデモAPI** が含まれています。

- モデルの役割
  - 4つの数値（`sepal_length`, `sepal_width`, `petal_length`, `petal_width`）を入力すると、
    3クラスのどれかを予測してクラス番号＋ラベル名を返します。
  - モデルの中身（学習・予測）は `scikit-learn` に任せ、
    API・テスト・CI などの「周りの仕組み」をこのプロジェクト側で用意しています。

- エンドポイント

  - `POST /ml/iris/predict`

- 使い方（Swagger UI 経由）

  1. `uvicorn main:app --reload` で起動
  2. ブラウザで `http://127.0.0.1:8000/docs` を開く
  3. `POST /ml/iris/predict` を選択 → 「Try it out」
  4. リクエスト例（目安）:

     ```json
     {
       "sepal_length": 5.1,
       "sepal_width": 3.5,
       "petal_length": 1.4,
       "petal_width": 0.2
     }
     ```

  5. 「Execute」を押すと、例として次のようなレスポンスが返ります:

     ```json
     {
       "predicted_class": 0,
       "predicted_label": "setosa"
     }
     ```

- 実装のポイント

  - `ml_sample/model.py` にて
    - 組み込みデータ（Iris）を読み込み
    - ロジスティック回帰モデルを学習
    - `models/iris.joblib` に保存
    - `ensure_model()` / `predict()` で API から利用しやすい形にラップ
  - FastAPI 側からは、**「4つの数値 → 予測結果」** の形だけを意識すればよいように設計

---

## テスト & CI

ローカルでの品質チェック:

- `ruff check . --fix`
- `ruff format .`
- `mypy .`
- `pytest -q`

GitHub Actions では、pull request / main への push ごとに同等のチェックを自動実行しています。

---

## ロードマップ（抜粋）

- ✅ mypy / pytest / ruff / GitHub Actions による CI 基盤
- ✅ タイトルスクレイパ（リトライ・重複排除）
- ✅ 観測ログ（構造化 JSON）、`/health` 拡張
- ✅ パッケージ化 & CLI (`mlops-try scrape-titles`)
- ✅ Iris データを使った小さな ML デモAPI（`/ml/iris/predict`）
- ⏳ SQLite / Parquet への移行、FTS 検索、Playwright など（今後追加予定）

---

## ライセンス

本プロジェクトは MIT License のもとで公開予定です。
