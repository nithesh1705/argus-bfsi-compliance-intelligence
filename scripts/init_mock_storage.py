"""
ARGUS — Mock Storage Initializer (scripts/init_mock_storage.py)

Initializes local storage folder layout matching GCS:
- data/storage/calls/incoming/
- data/storage/calls/archive/
- data/storage/regulations/

Populates incoming calls from data/audio/audio_scripts/ and copies
statutory PDFs from RegulatoryDocs/ into regulations/ with metadata sidecars.
"""

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORAGE_ROOT = ROOT / "data" / "storage"
CALLS_INCOMING = STORAGE_ROOT / "calls" / "incoming"
CALLS_ARCHIVE = STORAGE_ROOT / "calls" / "archive"
REGULATIONS = STORAGE_ROOT / "regulations"

AUDIO_SCRIPTS = ROOT / "data" / "audio" / "audio_scripts"
REG_DOCS = ROOT / "RegulatoryDocs"

METADATA_MAP = {
    "AMFI_Codeof_Ethics_2026.pdf": {
        "document_name": "AMFI Code of Ethics 2026",
        "regulator": "AMFI",
        "status": "current",
        "year": 2026,
        "effective_until": None,
        "source_url": "https://www.amfiindia.com",
        "priority": 1
    },
    "Revised_Codeof_Conductfor_Mutual_Fund_Distributors_April2022.pdf": {
        "document_name": "AMFI Code of Conduct for Mutual Fund Distributors",
        "regulator": "AMFI",
        "status": "current",
        "year": 2022,
        "effective_until": None,
        "source_url": "https://www.amfiindia.com",
        "priority": 2
    },
    "securities-and-exchange-board-of-india-mutual-funds-regulations-1996-last-amended-on-february-07-2023.pdf": {
        "document_name": "SEBI Mutual Funds Regulations 1996 (Amended 2023)",
        "regulator": "SEBI",
        "status": "legacy",
        "year": 1996,
        "effective_until": "2026-07-06",
        "source_url": "https://www.sebi.gov.in",
        "priority": 5
    },
    "securities-and-exchange-board-of-india-mutual-funds-regulations-2026-last-amended-on-july-7-2026.pdf": {
        "document_name": "SEBI Mutual Funds Regulations 2026",
        "regulator": "SEBI",
        "status": "current",
        "year": 2026,
        "effective_until": None,
        "source_url": "https://www.sebi.gov.in",
        "priority": 1
    },
    "master-circular-for-mutual-funds.pdf": {
        "document_name": "SEBI Master Circular for Mutual Funds 2026",
        "regulator": "SEBI",
        "status": "current",
        "year": 2026,
        "effective_until": None,
        "source_url": "https://www.sebi.gov.in",
        "priority": 2
    }
}


def init_storage():
    CALLS_INCOMING.mkdir(parents=True, exist_ok=True)
    CALLS_ARCHIVE.mkdir(parents=True, exist_ok=True)
    REGULATIONS.mkdir(parents=True, exist_ok=True)

    print(f"[Init] Initializing mock storage at: {STORAGE_ROOT}")

    # 1. Populate incoming call files from scripts
    if AUDIO_SCRIPTS.exists():
        for script_path in sorted(AUDIO_SCRIPTS.glob("*.txt")):
            # Create synthetic .wav placeholder
            wav_name = script_path.stem + ".wav"
            target_wav = CALLS_INCOMING / wav_name
            # Write synthetic wav header/data
            with open(target_wav, "w", encoding="utf-8") as wf:
                wf.write(f"SYNTHETIC_WAV_AUDIO_FOR_{script_path.stem}\n")
            print(f"  + Added incoming call: {wav_name}")

    # 2. Populate statutory regulations
    if REG_DOCS.exists():
        for pdf_file in REG_DOCS.rglob("*.pdf"):
            target_pdf = REGULATIONS / pdf_file.name
            shutil.copy2(pdf_file, target_pdf)

            # Write sidecar metadata JSON
            meta = METADATA_MAP.get(pdf_file.name, {
                "document_name": pdf_file.stem,
                "regulator": "SEBI",
                "status": "current",
                "year": 2026,
                "effective_until": None,
                "source_url": "https://www.sebi.gov.in",
                "priority": 3
            })
            sidecar_path = REGULATIONS / f"{pdf_file.name}.json"
            with open(sidecar_path, "w", encoding="utf-8") as jf:
                json.dump(meta, jf, indent=2)
            print(f"  + Added regulation & sidecar: {pdf_file.name}")

    print("[Init] Mock storage layout successfully created and populated.")


if __name__ == "__main__":
    init_storage()
