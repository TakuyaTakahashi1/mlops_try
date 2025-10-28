from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import pandas as pd

DATA = Path("data")
CSV_CUMU = DATA / "titles.csv"
SQLITE = DATA / "titles.sqlite"
PARQ_DIR = DATA / "parquet"


def bench(name: str, fn):
    t0 = time.perf_counter()
    df = fn()
    dt = (time.perf_counter() - t0) * 1000
    n = 0 if df is None else len(df)
    print(f"{name:12s} {dt:8.1f} ms  rows={n}")


def read_csv():
    if CSV_CUMU.exists():
        return pd.read_csv(CSV_CUMU, dtype=str)
    return pd.DataFrame()


def read_sqlite():
    if SQLITE.exists():
        con = sqlite3.connect(str(SQLITE))
        try:
            return pd.read_sql_query("SELECT * FROM articles", con)
        finally:
            con.close()
    return pd.DataFrame()


def read_parquet():
    files = sorted(PARQ_DIR.glob("titles-*.parquet"))
    if not files:
        return pd.DataFrame()
    dfs = [pd.read_parquet(f) for f in files]
    return pd.concat(dfs, ignore_index=True)


def main():
    bench("CSV(read)", read_csv)
    bench("SQLite(read)", read_sqlite)
    bench("Parquet(read)", read_parquet)


if __name__ == "__main__":
    main()
