"""
ARGUS — Database Migration and Seeding Runner (scripts/init_argus_db.py)

Creates the 'argus' database, executes unified Cloud SQL DDL, and populates
idempotent seed data (RMs, customers, products, transactions, reviewers, settings).
"""

import os
import sys
from pathlib import Path
import pymysql
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")
load_dotenv(ROOT / "backend" / ".env")

DB_HOST = os.getenv("ARGUS_DB_HOST", os.getenv("MYSQL_HOST", "127.0.0.1"))
DB_PORT = int(os.getenv("ARGUS_DB_PORT", os.getenv("MYSQL_PORT", 3306)))
DB_USER = os.getenv("ARGUS_DB_USER", os.getenv("MYSQL_USER", "root"))
DB_PASSWORD = os.getenv("ARGUS_DB_PASSWORD", os.getenv("MYSQL_PASSWORD", "qwerty12345"))
DB_NAME = os.getenv("ARGUS_DB_NAME", "argus")

DDL_FILE = ROOT / "data" / "schemas" / "argus_mysql_ddl.sql"
SEED_FILE = ROOT / "data" / "schemas" / "argus_mysql_seed_data.sql"


def run_sql_file(cursor, file_path: Path):
    print(f"[DB] Executing SQL script: {file_path.name}")
    with open(file_path, "r", encoding="utf-8") as f:
        sql = f.read()

    # Split by statements
    statements = sql.split(";")
    for stmt in statements:
        stmt_clean = stmt.strip()
        if stmt_clean:
            cursor.execute(stmt_clean)


def init_db():
    from backend.adapters.database import db_manager
    print(f"[DB] Connecting via db_manager (Cloud SQL Connector / PyMySQL)...")
    conn = db_manager.get_raw_connection()
    try:
        conn.autocommit(True)
        with conn.cursor() as cur:
            run_sql_file(cur, DDL_FILE)
            run_sql_file(cur, SEED_FILE)
            print("[DB] DDL and Seed Data applied successfully!")
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
