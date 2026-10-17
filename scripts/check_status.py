"""
ARGUS — Quick Call Status Inspector (scripts/check_status.py)
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")
load_dotenv(ROOT / "backend" / ".env")

from backend.adapters.database import db_manager

def main():
    conn = db_manager.get_raw_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT call_id, status, duration_s FROM `call`")
            rows = cur.fetchall()
            for r in rows:
                print(r)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
