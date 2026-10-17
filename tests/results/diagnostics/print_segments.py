"""
ARGUS — Transcript Segment Inspector (tests/results/diagnostics/print_segments.py)
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
            SELECT segment_id, idx, speaker_label, role, start_ms, end_ms, text_original, text_english, is_violation 
            FROM transcript_segment 
            WHERE call_id = 'CALL_RM001_CUST001_20260320_0900' 
            ORDER BY idx ASC
        """)
        segments = cur.fetchall()
        print(f"Total segments: {len(segments)}")
        for s in segments:
            orig = s['text_original']
            en = s['text_english']
            print(f"[{s['start_ms']/1000:.1f}s - {s['end_ms']/1000:.1f}s] {s['speaker_label']} ({s['role']}): {orig}")
            if en and en != orig:
                print(f"   -> ENGLISH: {en}")
    conn.close()

if __name__ == "__main__":
    main()
