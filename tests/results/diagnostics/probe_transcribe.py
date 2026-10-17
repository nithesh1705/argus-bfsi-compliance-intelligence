"""
ARGUS — Speech-to-Text Transcription Probe (tests/results/diagnostics/probe_transcribe.py)
Offline/live diagnostic utility for verifying Vertex AI Gemini audio transcription endpoints.
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
RESULTS_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
load_dotenv(ROOT / "backend" / ".env")

from google import genai
from google.genai import types

PROJECT_ID = os.getenv("ARGUS_PROJECT_ID", "your-gcp-project-id")
LOCATION = os.getenv("ARGUS_VERTEX_LOCATION", "us-central1")
CALLS_BUCKET = os.getenv("ARGUS_CALLS_BUCKET", f"{PROJECT_ID}-argus-calls")
MODEL_ID = os.getenv("ARGUS_GEMINI_TRANSCRIBE_MODEL", "gemini-3.5-flash")

client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
audio_uri = f"gs://{CALLS_BUCKET}/calls/_backup/RM001_CUST001_20260310_1030.wav"

prompt = """Transcribe this sales call audio accurately with speaker turns, timestamps, and verbatim speech.
Output a valid JSON list of turns matching this schema:
[
  {
    "segment_id": 1,
    "speaker_label": "Speaker 1",
    "start_ms": 0,
    "end_ms": 3500,
    "text_original": "verbatim text in original language"
  }
]"""

def main():
    print("Sending audio transcription request to Vertex AI Gemini...")
    resp = client.models.generate_content(
        model=MODEL_ID,
        contents=[types.Part.from_uri(file_uri=audio_uri, mime_type="audio/wav"), prompt],
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )

    print("Transcription Success!")
    data = json.loads(resp.text)
    print(f"Total segments extracted: {len(data)}")
    for s in data[:3]:
        print(f"[{s.get('start_ms')}ms - {s.get('end_ms')}ms] {s.get('speaker_label')}: {s.get('text_original')}")

    out_file = RESULTS_DIR / "sample_transcription_RM001_CUST001.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Saved to {out_file}")

if __name__ == "__main__":
    main()
