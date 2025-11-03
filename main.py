import os  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
from datetime import UTC, datetime  # noqa: E402
from pathlib import Path as PPath

import pandas as pd
from fastapi import FastAPI, Query, Request
from fastapi import Path as ApiPath
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel  # noqa: E402

from automation.storage import fts_search_articles, search_articles
from settings import settings

# main.py
# ───────────────────────────────────────────


# ──── データ準備 ────────────────────────────

# ① .env を読む Settings をインポート

CSV_PATH: PPath = PPath("sales.csv")

# sales.csv は date,amount の 2 列
#   date  : 2025-06-01
#   amount: 1200
df = pd.read_csv(CSV_PATH, dtype={"date": "string", "amount": "int"})


# 年別集計を関数で分けておくとテストしやすい
def calc_total_sales_by_year(data: pd.DataFrame, year: int) -> int:
    mask = data["date"].str.startswith(str(year))
    return int(data.loc[mask, "amount"].sum())


# ──── Pydantic レスポンスモデル ───────────────
class TotalResp(BaseModel):
    total: int


# ──── FastAPI 本体 ────────────────────────────

app = FastAPI()


@app.get("/total_sales", response_model=TotalResp, summary="全期間の売上合計")
def total_sales() -> dict[str, int]:
    return {"total": int(df["amount"].sum())}


@app.get(
    "/total_sales/{year}",
    response_model=TotalResp,
    summary="年間売上合計（年別）",
)
def total_sales_by_year(
    year: int = ApiPath(..., ge=1900, le=2100, description="4 桁の西暦"),
) -> dict[str, int]:
    return {"total": calc_total_sales_by_year(df, year)}


# ② .env が読めているか確認用
@app.get("/health", tags=["internal"], summary="死活監視")
def health():
    return {
        "status": "ok",
        "db": settings.db_url,  # .env の DB_URL がそのまま入る
        "api": settings.api_key,  # 同じく API_KEY
    }


# --- A4: version endpoint & exception handlers ---

from pydantic import BaseModel  # noqa: E402

# アプリ起動時刻（ISO8601）
_STARTED_AT = datetime.now(UTC).astimezone().isoformat(timespec="seconds")


def _git_sha_short() -> str:
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
        )  # noqa: E501  # noqa: E501
        return sha.decode("utf-8").strip()
    except Exception:
        return os.getenv("GIT_SHA", "unknown")


def _app_version() -> str:
    # .env などで APP_VERSION があればそれを使う。無ければ 0.1.0 とする。
    return os.getenv("APP_VERSION", "0.1.0")


class VersionInfo(BaseModel):
    version: str
    git_sha: str
    started_at: str
    python: str


@app.get("/version", response_model=VersionInfo)
def version() -> VersionInfo:
    return VersionInfo(
        version=_app_version(),
        git_sha=_git_sha_short(),
        started_at=_STARTED_AT,
        python=sys.version.split()[0],
    )


# 422: 既定ハンドラを呼び出して形を変えない（ロギング用途に差し替え可）
@app.exception_handler(RequestValidationError)
async def _handle_422(request: Request, exc: RequestValidationError):
    return await request_validation_exception_handler(request, exc)


# 500: 共通 JSON を返す
@app.exception_handler(Exception)
async def _handle_500(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


# テスト用のエンドポイント（本番では参照されない）
@app.get("/__error")
def _boom() -> None:  # pragma: no cover
    raise RuntimeError("boom")


@app.get("/articles")
def list_articles(
    q: str | None = Query(default=None, description="keyword (LIKE, case-insensitive)"),
    date_from: str | None = Query(
        default=None, description="inclusive ISO e.g. 2025-10-01T00:00:00"
    ),
    date_to: str | None = Query(default=None, description="exclusive ISO e.g. 2025-11-01T00:00:00"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
):
    df = search_articles(
        q=q, date_from=date_from, date_to=date_to, limit=limit, offset=offset, order=order
    )
    return df.to_dict(orient="records")


@app.get("/articles/fts")
def list_articles_fts(
    q: str = Query(..., description="FTS5 query. e.g. 'python OR blog'"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    df = fts_search_articles(q=q, limit=limit, offset=offset)
    return df.to_dict(orient="records")
