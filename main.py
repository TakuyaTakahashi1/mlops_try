# main.py
# ───────────────────────────────────────────
from pathlib import Path
from typing import Dict

import pandas as pd
from fastapi import FastAPI, Path as FPath
from pydantic import BaseModel

# ① .env を読む Settings をインポート
from settings import settings

# ──── データ準備 ────────────────────────────
CSV_PATH: Path = Path("sales.csv")

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
def total_sales() -> Dict[str, int]:
    return {"total": int(df["amount"].sum())}

@app.get(
    "/total_sales/{year}",
    response_model=TotalResp,
    summary="年間売上合計（年別）",
)
def total_sales_by_year(
    year: int = FPath(..., ge=1900, le=2100, description="4 桁の西暦"),
) -> Dict[str, int]:
    return {"total": calc_total_sales_by_year(df, year)}

# ② .env が読めているか確認用
@app.get("/health", tags=["internal"], summary="死活監視")
def health():
    return {
        "status": "ok",
        "db": settings.db_url,   # .env の DB_URL がそのまま入る
        "api": settings.api_key, # 同じく API_KEY
    }

