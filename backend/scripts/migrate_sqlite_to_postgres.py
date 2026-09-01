"""SAFE, OPTIONAL, manual migration of data from an existing SQLite
database into PostgreSQL. This is never run automatically.

Usage (dry run — shows counts, migrates nothing):
    python scripts/migrate_sqlite_to_postgres.py --sqlite-path ../bhusuraksha.db

Usage (actually migrate — DATABASE_URL must already point at Postgres):
    DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db \
        python scripts/migrate_sqlite_to_postgres.py --sqlite-path ../bhusuraksha.db --confirm

Behavior:
  - Refuses to run if DATABASE_URL is not a postgresql+psycopg:// URL.
  - Refuses to run if the target already has ANY rows in these tables,
    unless --force is also passed (never silently overwrites).
  - Without --confirm, only prints source/target record counts and exits
    (a dry run) — nothing is written.
  - Preserves primary key IDs (so foreign keys/relationships stay intact)
    and resets PostgreSQL's sequences afterward to match.
  - Validates migrated counts against source counts and prints a summary.
"""
import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from app.database import DATABASE_URL, SessionLocal, engine  # noqa: E402

# (table, ordered columns) — order matters: zones/monitoring_regions must
# be migrated before tables with a zone_id/source_id foreign key into them.
TABLES = [
    ("zones", None),
    ("alerts", None),
    ("reports", None),
    ("weather_observations", None),
    ("monitoring_regions", None),
    ("landslide_events", None),
]

# SQLite has no native boolean type — it stores 0/1 integers, which
# PostgreSQL's boolean columns refuse to accept implicitly. Coerce these
# explicitly rather than letting the insert fail with a type mismatch.
BOOLEAN_COLUMNS = {
    "zones": {"historical_landslide"},
    "alerts": {"is_active"},
    "monitoring_regions": {"is_landslide_prone"},
}


def _coerce_row(table, row_dict):
    for column in BOOLEAN_COLUMNS.get(table, ()):
        if column in row_dict and row_dict[column] is not None:
            row_dict[column] = bool(row_dict[column])
    return row_dict


def _table_columns(sqlite_conn, table):
    cursor = sqlite_conn.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cursor.fetchall()]


def _sqlite_count(sqlite_conn, table):
    try:
        return sqlite_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    except sqlite3.OperationalError:
        return 0  # table doesn't exist in this SQLite file (e.g. older schema)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sqlite-path", required=True, help="Explicit path to the source SQLite .db file")
    parser.add_argument("--confirm", action="store_true", help="Actually perform the migration (default: dry run)")
    parser.add_argument("--force", action="store_true", help="Allow migrating into a target that already has data")
    args = parser.parse_args()

    sqlite_path = Path(args.sqlite_path)
    if not sqlite_path.exists():
        print(f"Error: SQLite file not found: {sqlite_path}")
        sys.exit(1)

    if not DATABASE_URL.startswith("postgresql"):
        print(f"Error: DATABASE_URL must point at PostgreSQL to migrate into. Current: {engine.dialect.name}")
        print("Set DATABASE_URL to your postgresql+psycopg://... connection string and re-run.")
        sys.exit(1)

    sqlite_conn = sqlite3.connect(str(sqlite_path))
    sqlite_conn.row_factory = sqlite3.Row

    print("=" * 60)
    print("BHUSURAKSHA AI - SQLITE -> POSTGRESQL MIGRATION")
    print("=" * 60)
    print(f"Source SQLite: {sqlite_path}")
    print(f"Target: PostgreSQL ({engine.url.host}:{engine.url.port}/{engine.url.database})")
    print()

    source_counts = {table: _sqlite_count(sqlite_conn, table) for table, _ in TABLES}

    with engine.connect() as conn:
        target_counts_before = {}
        for table, _ in TABLES:
            try:
                target_counts_before[table] = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            except Exception:
                target_counts_before[table] = None

    print(f"{'Table':<24}{'SQLite':>10}{'PostgreSQL (before)':>22}")
    for table, _ in TABLES:
        print(f"{table:<24}{source_counts[table]:>10}{str(target_counts_before[table]):>22}")
    print()

    if not args.confirm:
        print("Dry run only (no --confirm passed). Nothing was migrated.")
        sqlite_conn.close()
        return

    already_populated = [t for t, c in target_counts_before.items() if c]
    if already_populated and not args.force:
        print(f"Refusing to migrate: target already has data in: {', '.join(already_populated)}")
        print("Pass --force to migrate anyway (existing rows are kept; new rows are added alongside them).")
        sqlite_conn.close()
        sys.exit(1)

    db = SessionLocal()
    try:
        for table, _ in TABLES:
            if source_counts[table] == 0:
                continue
            columns = _table_columns(sqlite_conn, table)
            rows = sqlite_conn.execute(f"SELECT * FROM {table}").fetchall()

            col_list = ", ".join(columns)
            placeholders = ", ".join(f":{c}" for c in columns)
            insert_stmt = text(f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})")

            try:
                for row in rows:
                    db.execute(insert_stmt, _coerce_row(table, dict(row)))

                # Preserve IDs, but keep PostgreSQL's own next-id sequence
                # consistent afterward so future inserts don't collide.
                db.execute(
                    text(
                        f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                        f"COALESCE((SELECT MAX(id) FROM {table}), 1))"
                    )
                )
                db.commit()
            except Exception as exc:  # noqa: BLE001 - must fail clearly, not with a raw traceback
                db.rollback()
                print(f"\nError migrating table '{table}': {exc.__class__.__name__}: {exc}")
                print("Rolled back this table's changes. Earlier committed tables were NOT rolled back.")
                sys.exit(1)

            print(f"Migrated {len(rows)} row(s) into {table}.")

    finally:
        db.close()
        sqlite_conn.close()

    with engine.connect() as conn:
        target_counts_after = {
            table: conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() for table, _ in TABLES
        }

    print()
    print("=" * 60)
    print("MIGRATION SUMMARY")
    print("=" * 60)
    all_valid = True
    for table, _ in TABLES:
        expected = target_counts_before[table] + source_counts[table] if target_counts_before[table] else source_counts[table]
        actual = target_counts_after[table]
        ok = actual == expected or (already_populated and actual >= source_counts[table])
        all_valid = all_valid and ok
        print(f"{table}:")
        print(f"  SQLite: {source_counts[table]}")
        print(f"  PostgreSQL after migration: {actual}")
    print()
    print("All counts validated successfully." if all_valid else "WARNING: some counts did not match expectations — review manually.")


if __name__ == "__main__":
    main()
