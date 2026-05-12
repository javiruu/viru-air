from __future__ import annotations

import argparse

from sqlalchemy import MetaData, create_engine, select, text


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate data from sqlite DB to postgres DB")
    parser.add_argument("--sqlite-url", required=True)
    parser.add_argument("--postgres-url", required=True)
    args = parser.parse_args()

    sqlite_engine = create_engine(args.sqlite_url)
    pg_engine = create_engine(args.postgres_url)

    src_meta = MetaData()
    src_meta.reflect(bind=sqlite_engine)

    with pg_engine.begin() as conn:
        conn.execute(text("SET session_replication_role = replica"))
    try:
        for table_name in src_meta.sorted_tables:
            src_table = src_meta.tables[table_name.name]
            print(f"copying {src_table.name} ...")
            rows = []
            with sqlite_engine.connect() as src_conn:
                rows = [dict(r._mapping) for r in src_conn.execute(select(src_table)).fetchall()]

            if not rows:
                print("  0 rows")
                continue

            with pg_engine.begin() as dst_conn:
                dst_table = MetaData()
                dst_table.reflect(bind=pg_engine, only=[src_table.name])
                dst_conn.execute(dst_table.tables[src_table.name].insert(), rows)
            print(f"  {len(rows)} rows")
    finally:
        with pg_engine.begin() as conn:
            conn.execute(text("SET session_replication_role = DEFAULT"))


if __name__ == "__main__":
    main()
