"""
ARGUS — Database Session Compatibility Boundary (backend/db/session.py)

Delegates to backend.adapters.database.db_manager.
"""

from backend.adapters.database import db_manager, get_db_connection

def db_transaction():
    return db_manager.transaction()

def db_connection():
    return db_manager.connection()

__all__ = ["get_db_connection", "db_transaction", "db_connection", "db_manager"]
