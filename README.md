# mlops-try

[![CI](https://github.com/TakuyaTakahashi1/mlops_try/actions/workflows/ci.yml/badge.svg)](https://github.com/TakuyaTakahashi1/mlops_try/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11-blue)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

個人の学習用に作っている「スクレイピング + API + CI/CD + 観測性」の練習プロジェクトです。
URL リストから記事タイトルを定期収集し、CSV に蓄積しつつ、FastAPI 経由で検索できるようにしています。

転職時のポートフォリオとして、次のポイントを意識しています。

- 型付き・テスト付きの API（FastAPI + mypy + pytest）
- GitHub Actions による自動テスト・Lint（ruff / pytest-cov）
- スクレイピングの安定化（リトライ・重複排除・日次/累積）
- 観測性（構造化ログ・ヘルスチェック）
- パッケージ化 & CLI 化（`mlops-try` コマンド）

---

## クイックスタート

FastAPI + mypy + pytest + GitHub Actions のサンプルとしても使えます。

- 起動: `uvicorn main:app --reload`
- テスト: `pytest -q`
- 型チェック: `mypy .`
- API ドキュメント: `http://127.0.0.1:8000/docs`

---

## 主な構成

- `main.py` : FastAPI アプリ本体（/health, /version など）
- `automation/` : スクレイピング・検索ロジック
  - `scrape_titles.py` : `titles.csv` を更新するスクレイパ
  - `storage.py` : 記事検索ロジック
  - `cli.py` : `mlops-try` コマンドのエントリポイント
  - `observability.py` : 構造化ログ / 計測
- `data/` : 収集したデータ（`daily/`, `titles.csv`）
- `tests/` : pytest テスト
- `pyproject.toml` : パッケージ定義 & CLI エントリポイント
- `requirements.txt` : ランタイム依存関係
- `.env.example` : 環境変数サンプル（`.env` の雛形）

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
- `http://127.0.0.1:8000/docs` : Swagger UI

### 2. CLI でスクレイプ

- `source .venv/bin/activate`
- `mlops-try scrape-titles`

挙動:

- 対象 URL: `automation/targets.txt`
- 出力:
  - `data/daily/titles-YYYYMMDD.csv`
  - `data/titles.csv`（重複排除済み）

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
- ⏳ SQLite / Parquet への移行、FTS 検索、Playwright など（今後追加予定）

---

## ライセンス

本プロジェクトは MIT License のもとで公開予定です。
