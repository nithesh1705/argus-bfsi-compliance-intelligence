"""
ARGUS — Database Adapter (backend/adapters/database.py)

Manages database connections for Cloud SQL for MySQL:
- Live: Cloud SQL Python Connector with IAM database authentication
- Mock / Local: Standard PyMySQL connection to local/container MySQL
- Safety Guard: Refuses to start in live mode against a mock database
"""

import os
import sys
import logging
from pathlib import Path
from contextlib import contextmanager
from typing import Generator, Any

# Ensure project root is in sys.path when executed directly or from subdirectories
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pymysql
import pymysql.cursors

from backend.core.config import settings

logger = logging.getLogger("argus.adapters.database")


class MockDatabaseGuardError(RuntimeError):
    """Raised when live mode attempts to connect to a mock database."""
    pass


class DatabaseManager:
    """Manages MySQL connections and transactions."""

    def __init__(self):
        self._validate_mode_safety()
        self._connector = None

    def _validate_mode_safety(self):
        """Enforces that live mode cannot write to a mock database."""
        if not settings.is_mock() and settings.DB_IS_MOCK:
            raise MockDatabaseGuardError(
                "CRITICAL SAFETY VIOLATION: ARGUS is configured in LIVE mode (ARGUS_PROVIDER_MODE=live), "
                "but ARGUS_DB_IS_MOCK=true. Live operations cannot execute against a mock database!"
            )

    def get_raw_connection(self):
        """
        Creates a raw PyMySQL connection with DictCursor.
        Uses Cloud SQL Connector if in live mode with INSTANCE_CONNECTION_NAME configured.
        """
        self._validate_mode_safety()

        # 1. Cloud Run Unix socket (when --add-cloudsql-instances is used)
        if settings.INSTANCE_CONNECTION_NAME:
            socket_path = f"/cloudsql/{settings.INSTANCE_CONNECTION_NAME}"
            if os.path.exists(socket_path):
                return pymysql.connect(
                    unix_socket=socket_path,
                    user=settings.DB_USER,
                    password=settings.DB_PASSWORD,
                    database=settings.DB_NAME,
                    cursorclass=pymysql.cursors.DictCursor,
                    autocommit=False,
                    charset="utf8mb4",
                )

        if not settings.is_mock() and settings.INSTANCE_CONNECTION_NAME:
            try:
                from google.cloud.sql.connector import Connector, IPTypes
                if self._connector is None:
                    self._connector = Connector()

                return self._connector.connect(
                    settings.INSTANCE_CONNECTION_NAME,
                    "pymysql",
                    user=settings.DB_USER,
                    password=settings.DB_PASSWORD,
                    db=settings.DB_NAME,
                    ip_type=IPTypes.PUBLIC,
                    cursorclass=pymysql.cursors.DictCursor,
                    autocommit=False,
                    charset="utf8mb4",
                )
            except Exception as exc:
                logger.warning(f"Cloud SQL Connector not used ({exc}), trying standard connection...")

        # Local / Container / Mock PyMySQL connection
        return pymysql.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME,
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,  # Enforce explicit transaction commits
            charset="utf8mb4",
        )

    @contextmanager
    def connection(self) -> Generator[Any, None, None]:
        """Context manager providing an active connection."""
        conn = self.get_raw_connection()
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def transaction(self) -> Generator[Any, None, None]:
        """Context manager providing an atomic transaction (commits on success, rolls back on exception)."""
        conn = self.get_raw_connection()
        try:
            with conn.cursor() as cursor:
                yield cursor
            conn.commit()
        except Exception as exc:
            conn.rollback()
            logger.error(f"Database transaction rolled back due to error: {exc}")
            raise
        finally:
            conn.close()


# Singleton database manager instance
db_manager = DatabaseManager()


def get_db_connection():
    """Convenience helper returning raw connection."""
    return db_manager.get_raw_connection()


if __name__ == "__main__":
    print(f"ARGUS Database Adapter")
    print(f"Provider Mode: {settings.PROVIDER_MODE}")
    print(f"DB Host: {settings.DB_HOST}:{settings.DB_PORT}")
    print(f"DB Name: {settings.DB_NAME}")
    print(f"DB User: {settings.DB_USER}")
    print(f"Connecting to database...")
    try:
        with db_manager.transaction() as cur:
            cur.execute("SELECT COUNT(*) AS total_tables FROM information_schema.tables WHERE table_schema = %s", (settings.DB_NAME,))
            res = cur.fetchone()
            print(f"[PASS] Connection successful! Total tables in '{settings.DB_NAME}': {res['total_tables']}")
    except Exception as e:
        print(f"[FAIL] Database connection failed: {e}")
        sys.exit(1)

