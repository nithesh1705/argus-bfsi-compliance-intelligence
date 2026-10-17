"""
ARGUS — Live Test Evidence Exporter
Exports database state, benchmark results, stage timings, SHA-256 hashes, and token metrics to test_evidence/
"""

import os
import sys
import json
import hashlib
import pymysql
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.adapters.database import get_db_connection
from backend.core.config import settings

EVIDENCE_DIR = PROJECT_ROOT / "tests" / "results"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def export_hashes():
    hashes = {}
    tests_dir = PROJECT_ROOT / "tests" / "test_files"
    for p in sorted(tests_dir.glob("*.py")):
        hashes[f"tests/test_files/{p.name}"] = compute_sha256(p)
    
    gt_path = PROJECT_ROOT / "backend" / "benchmark" / "ground_truth.json"
    if gt_path.exists():
        hashes["backend/benchmark/ground_truth.json"] = compute_sha256(gt_path)
    
    out_file = EVIDENCE_DIR / "test_file_hashes.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(hashes, f, indent=2)
    print(f"[OK] Exported test hashes to {out_file}")
    return hashes

def export_tables():
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    tables = [
        "call", "transcript_segment", "candidate", "investigation", 
        "finding", "compliance_case", "case_activity_log", 
        "pipeline_run", "pipeline_stage_timing", "provider_health",
        "rm", "customer", "product", "regulation_chunk_registry"
    ]
    
    summary = {}
    for table in tables:
        try:
            cursor.execute(f"SELECT * FROM `{table}`")
            rows = cursor.fetchall()
            # Convert non-serializable objects (datetime, Decimal, etc.)
            for r in rows:
                for k, v in r.items():
                    if hasattr(v, "isoformat"):
                        r[k] = v.isoformat()
                    elif hasattr(v, "__str__") and not isinstance(v, (int, float, str, bool, list, dict, type(None))):
                        r[k] = str(v)
            
            summary[table] = len(rows)
            out_file = EVIDENCE_DIR / f"table_{table}.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(rows, f, indent=2)
        except Exception as e:
            print(f"Error exporting table {table}: {e}")
            summary[table] = f"ERROR: {e}"
            
    cursor.close()
    conn.close()
    print(f"[OK] Exported {len(tables)} tables to {EVIDENCE_DIR}")
    return summary

def main():
    print("[1/2] Computing SHA-256 hashes...")
    hashes = export_hashes()
    print("[2/2] Exporting database tables...")
    counts = export_tables()
    print("Table counts:", counts)

if __name__ == "__main__":
    main()
