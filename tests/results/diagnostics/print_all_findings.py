"""
ARGUS — Finding Diagnostic Inspector (tests/results/diagnostics/print_all_findings.py)
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")
load_dotenv(ROOT / "backend" / ".env")

from backend.adapters.database import get_db_connection

def main():
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT finding_id, category, severity, timestamp_start, timestamp_end, quote_original, citation_label
            FROM finding 
            WHERE call_id = 'CALL_RM001_CUST001_20260320_0900'
            ORDER BY finding_id ASC
        """)
        findings = cur.fetchall()
        for f in findings:
            print(f"Finding: {f['finding_id']} | Cat: {f['category']} | [{f['timestamp_start']}s - {f['timestamp_end']}s]: \"{f['quote_original']}\"")
    conn.close()

if __name__ == "__main__":
    main()
