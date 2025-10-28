from __future__ import annotations

from automation.storage import migrate_from_csv, query_count


def main() -> int:
    db_count, pq_files = migrate_from_csv()
    total = query_count()
    print(f"migrated_to_db={db_count} parquet_files_created={pq_files} total_in_db={total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
