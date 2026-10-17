"""
ARGUS — Manual Ingestion & Demonstration Runner (scripts/process_now.py)

Usage:
  python scripts/process_now.py [--call <filename>] [--all]
"""

import sys
import argparse
from pathlib import Path

# Ensure project root in sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.adapters.storage import get_object_store
from backend.ingestion.pipeline_runner import run_pipeline_for_object


def main():
    parser = argparse.ArgumentParser(description="ARGUS On-Demand Pipeline Runner")
    parser.add_argument("--call", type=str, help="Specific call filename (e.g. RM001_CUST001_20260310_1030.wav)")
    parser.add_argument("--all", action="store_true", help="Process all available incoming calls")
    args = parser.parse_args()

    store = get_object_store()

    if args.call:
        filename = Path(args.call).name
        print(f"[ProcessNow] Processing single call: {filename}")
        res = run_pipeline_for_object(filename)
        print(f"[ProcessNow] Result: {res}")
        return

    # Process all incoming objects or default to the 10 demo scripts
    incoming_objects = store.list_objects("calls/incoming")
    if not incoming_objects:
        print("[ProcessNow] No calls found in calls/incoming. Restoring from calls/_backup/...")
        backup_objects = store.list_objects("calls/_backup")
        for b_key in backup_objects:
            fname = Path(b_key).name
            store.copy_object(b_key, f"calls/incoming/{fname}")
        incoming_objects = store.list_objects("calls/incoming")

    print(f"[ProcessNow] Found {len(incoming_objects)} incoming call objects to process:")
    for obj_key in incoming_objects:
        filename = Path(obj_key).name
        if filename.endswith(".wav") or filename.endswith(".txt"):
            print(f" -> Processing: {filename}...")
            res = run_pipeline_for_object(filename)
            print(f"    Status: {res.get('status')} | Call ID: {res.get('call_id')}")


if __name__ == "__main__":
    main()
