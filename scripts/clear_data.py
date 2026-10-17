"""
ARGUS — Data Cleanup Script (scripts/clear_data.py)
Clears calls, cases, findings, candidates, investigations, transcripts, and pipeline runs from DB.
Clears incoming and archive folders in GCS calls bucket.
Removes legacy local CallAudio folders.
"""

import os
import sys
import shutil
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")
load_dotenv(ROOT / "backend" / ".env")

from backend.adapters.database import db_manager
from google.cloud import storage

BUCKET_NAME = os.getenv("ARGUS_CALLS_BUCKET", f"{os.getenv('ARGUS_PROJECT_ID', 'argus-compliance-prod')}-argus-calls")

TABLES_TO_CLEAR = [
    "case_activity_log",
    "compliance_case",
    "finding",
    "investigation",
    "candidate",
    "transcript_segment",
    "pipeline_stage_timing",
    "pipeline_run",
    "`call`",
]

def clear_db():
    print("[1/3] Connecting to Cloud SQL via db_manager...")
    conn = db_manager.get_raw_connection()
    try:
        conn.autocommit(True)
        with conn.cursor() as cur:
            print("\n--- Current DB Counts ---")
            for table in TABLES_TO_CLEAR:
                cur.execute(f"SELECT COUNT(*) as cnt FROM {table}")
                row = cur.fetchone()
                count = row["cnt"] if isinstance(row, dict) else row[0]
                print(f"  {table:25}: {count} rows")

            print("\nTruncating tables...")
            cur.execute("SET FOREIGN_KEY_CHECKS = 0;")
            for table in TABLES_TO_CLEAR:
                cur.execute(f"TRUNCATE TABLE {table};")
                print(f"  Truncated {table}")
            cur.execute("SET FOREIGN_KEY_CHECKS = 1;")

            print("\n--- Post-Truncate DB Counts ---")
            for table in TABLES_TO_CLEAR:
                cur.execute(f"SELECT COUNT(*) as cnt FROM {table}")
                row = cur.fetchone()
                count = row["cnt"] if isinstance(row, dict) else row[0]
                print(f"  {table:25}: {count} rows")
            print("[OK] Database cleanup completed successfully!")
    finally:
        conn.close()

def clear_gcs():
    print(f"\n[2/3] Connecting to Google Cloud Storage (Bucket: {BUCKET_NAME})...")
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)

    prefixes = ["calls/incoming/", "incoming/", "calls/archive/", "archive/"]
    deleted_count = 0

    for prefix in prefixes:
        blobs = list(bucket.list_blobs(prefix=prefix))
        if blobs:
            print(f"Found {len(blobs)} files under '{prefix}':")
            for blob in blobs:
                print(f"  Deleting: {blob.name}")
                blob.delete()
                deleted_count += 1
        else:
            print(f"  No files found under '{prefix}'.")

    print(f"[OK] Cloud Storage cleanup completed! Deleted {deleted_count} files.")

def clear_local_folders():
    print("\n[3/3] Removing legacy local CallAudio folders...")
    local_folders = [
        ROOT / "CallAudio",
        ROOT / "CallAudio-Archive",
        ROOT / "CallAudio-Failed",
    ]
    for folder in local_folders:
        if folder.exists():
            shutil.rmtree(folder)
            print(f"  Deleted directory: {folder.name}")
        else:
            print(f"  Directory not present: {folder.name}")
    print("[OK] Local folders removed successfully!")

if __name__ == "__main__":
    clear_db()
    clear_gcs()
    clear_local_folders()
    print("\n=======================================================")
    print("ALL REQUESTED DATA AND STORAGE FOLDERS HAVE BEEN CLEARED")
    print("=======================================================")
