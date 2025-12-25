[![CI](https://github.com/TakuyaTakahashi1/mlops_try/actions/workflows/ci.yml/badge.svg)](https://github.com/TakuyaTakahashi1/mlops_try/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11-blue)
![License](https://img.shields.io/badge/license-MIT-lightgrey)  個人の学習用に作っている「スクレイピング + API + CI/CD + 観測性 + ML デモ」の練習プロジェクトです。 URL リストから記事タイトルを定期収集し、CSV/SQLite に蓄積しつつ、FastAPI 経由で検索できるようにしています。 加えて、scikit-learn を使った Iris 分類モデルのデモ API / CLI も実装しています。
転職時のポートフォリオとして、次のポイントを意識しています。
* 型付き・テスト付きの API（FastAPI + mypy + pytest）
* GitHub Actions による自動テスト・Lint（ruff / pytest-cov）
* スクレイピングの安定化（リトライ・重複排除・日次/累積）
* 観測性（構造化ログ・ヘルスチェック）
* パッケージ化 & CLI 化（mlops-try コマンド）
* シンプルな ML デモ（Iris モデルの学習・推論・再学習）

クイックスタート
FastAPI + mypy + pytest + GitHub Actions のサンプルとしても使えます。
* 起動: uvicorn main:app --reload
* テスト: pytest -q
* 型チェック: mypy .
* API ドキュメント: http://127.0.0.1:8000/docs

主な構成
* main.py : FastAPI アプリ本体（健康診断 /health, バージョン /version, 記事検索 /articles など）
* automation/ : スクレイピング・検索ロジック
    * scrape_titles.py : titles.csv を更新するスクレイパ
    * storage.py : 記事検索ロジック
    * cli.py : mlops-try コマンドのエントリポイント（スクレイピング / ML 再学習）
    * observability.py : 構造化ログ / 計測
* ml_sample/ : Iris 分類モデルのサンプル
    * model.py : モデルの学習・保存・読み込み
    * api.py : /ml/iris/predict エンドポイント向けロジック
* data/ : 収集したデータ（daily/, titles.csv など）
* tests/ : pytest テスト一式（API / スクレイピング / ML）
* pyproject.toml : パッケージ定義 & CLI エントリポイント
* requirements.txt : ランタイム依存関係
* .env.example : 環境変数サンプル（.env の雛形）

セットアップ
1. リポジトリ取得 git clone https://github.com/TakuyaTakahashi1/mlops_try.git cd mlops_try
2. 仮想環境と依存インストール python -m venv .venv source .venv/bin/activate python -m pip install --upgrade pip python -m pip install -r requirements.txt python -m pip install -e .
3. 環境変数（.env） cp .env.example .env .env を開いて、DB_URL / API_KEY などを自分の環境に合わせて編集

使い方
1. API サーバ
source .venv/bin/activate uvicorn main:app --reload
主なエンドポイント例:
* GET /health : ヘルスチェック（設定ロード・データ存在チェックなど）
* GET /version : アプリのバージョン / Git SHA / 起動時刻
* GET /articles : 記事タイトル検索 API
* GET /articles/fts : FTS5 を使った全文検索 API
* POST /ml/iris/predict : Iris 分類モデルによる予測
2. CLI でスクレイプ（タイトル収集）
source .venv/bin/activate mlops-try scrape-titles
* 対象 URL: automation/targets.txt
* 出力:
    * data/daily/titles-YYYYMMDD.csv
    * data/titles.csv（重複排除済み）
3. ML モデルの再学習（Iris）
Iris データセット（アヤメの花の特徴量）を使ったシンプルな分類モデルです。 mlops-try train-iris で、ローカル環境でいつでも学習し直せます。
source .venv/bin/activate mlops-try train-iris
典型的な挙動:
* scikit-learn の Iris データセットを読み込み
* モデルを学習
* models/iris.joblib に保存
標準出力例:
[OK] trained Iris model saved to: models/iris.joblib
API 側の /ml/iris/predict は、このモデルファイルを読み込んで推論します。

テスト & CI
ローカルでの品質チェック:
ruff check . --fix ruff format . mypy . pytest -q
GitHub Actions では、pull request / main への push ごとに同等のチェックを自動実行しています。

Iris ML デモについて（概要）
## Iris ML デモ（再現手順）
この ML デモは「学習 → 評価 → 推論」を 同じ成果物（artifacts） を使って再現できるように設計しています。

### 1. モデル学習（train）
python -m ml_sample.train --out artifacts/model.joblib
・Iris データセットを使ってモデルを学習
・学習済みモデルは artifacts/model.joblib として保存
・学習処理は API とは独立した CLI として実行

### 2. モデル評価（eval）
python -m ml_sample.eval_cli \
  --model artifacts/model.joblib \
  --out artifacts/metrics.json

・学習済みモデルを読み込み、全データで評価
・accuracy / confusion matrix / report を JSON で出力
・artifacts/metrics.json は「今回の評価結果」を表す単一成果物

### 3. 評価結果の可視化（summary）
python -m ml_sample.metrics_summary \
  --metrics artifacts/metrics.json \
  --ascii-chart

例：
Iris accuracy chart
-------------------
2025-12-22 | ####################################### (0.9733)

### 4. 推論 API の起動（serve）
REuvicorn main:app --reload
・/ml/iris/predict エンドポイントが利用可能
・API は artifacts/model.joblib を読み込んで推論を実行

設計の意図（ML 周り）
・学習（train）と推論（API）を明確に分離
・モデル・メトリクスは artifacts/ に集約し、成果物の所在を固定
・CLI 化により、人・CI の両方で同じ手順を再現可能
・評価結果は JSON として保存し、後続処理（可視化・比較）に使える設計

今後の改善（ML / MLOps 観点）
・Docker 化による train / eval / serve の分離
・定期的な再学習（スケジューラ・CI 連携）
・モデル成果物のバージョニング（hash / metadata 管理）
・別データセットへの差し替え対応

* データセット: scikit-learn 標準の Iris データセット
* タスク: 4つの特徴量（がく片/花弁の長さ・幅）から 3種類のアヤメを分類
技術要素:
* scikit-learn による学習・推論
* モデルファイルの保存（joblib）
* FastAPI での推論 API (/ml/iris/predict)
* pytest による API / バリデーションテスト
* CLI (mlops-try train-iris) による再学習
* 評価 CLI (python -m ml_sample.eval_cli) によるメトリクス出力

ロードマップ（抜粋）
* mypy / pytest / ruff / GitHub Actions による CI 基盤
* タイトルスクレイパ（リトライ・重複排除）
* 観測ログ（構造化 JSON）、/health 拡張
* パッケージ化 & CLI (mlops-try scrape-titles)
* Iris ML デモ（モデル学習・API・再学習 CLI・評価 CLI）
* SQLite / Parquet への移行、FTS 検索、Playwright など（今後追加予定）

ライセンス
本プロジェクトは MIT License のもとで公開予定です。
## Docker での起動

このリポジトリは、Docker コンテナとしても起動できます。
FastAPI アプリと Iris ML API をまとめて立ち上げられるので、検証やデモに使いやすい構成です。

### 前提

- Docker 環境がインストールされていること（Docker Desktop など）
- プロジェクト直下に `.env` があること（`cp .env.example .env` で作成可能）

### 起動手順
docker compose up --build

起動後、次の URL にアクセスできます。
ヘルスチェック: http://localhost:8000/health
API ドキュメント (Swagger UI): http://localhost:8000/docs
Iris ML API: POST http://localhost:8000/ml/iris/predict

停止
docker compose down

Train（モデル成果物を作る）
python -m ml_sample.train --out artifacts/model.joblib
### 注意: scikit-learn のモデル互換性警告（InconsistentVersionWarning）

`*.joblib` を読み込む際に `InconsistentVersionWarning` が出る場合、保存時と実行時で scikit-learn のバージョンが異なることを意味します。
本リポジトリはデモのため警告を許容していますが、実運用では scikit-learn を固定（バージョンピン）し、同一バージョンでモデル成果物を再作成して再現性を担保します。
