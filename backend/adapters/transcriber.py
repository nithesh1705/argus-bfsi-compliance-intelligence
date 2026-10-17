"""
ARGUS — Speech-to-Text & Transcriber Adapter (backend/adapters/transcriber.py)

Provides Transcriber interface:
- Live: gemini-3.5-transcribe on Vertex AI with diarization, timestamps, custom vocabulary
- Mock: Deterministic synthetic audio script parser reading from data/audio/audio_scripts/
"""

import os
import re
import time
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger("argus.adapters.transcriber")

from backend.core.config import settings


class WordTimestamp:
    def __init__(self, word: str, start_ms: int, end_ms: int):
        self.word = word
        self.start_ms = start_ms
        self.end_ms = end_ms

    def to_dict(self):
        return {"word": self.word, "start_ms": self.start_ms, "end_ms": self.end_ms}


class DiarizedSegment:
    def __init__(
        self,
        segment_id: int,
        speaker_label: str,  # e.g. "Speaker 1", "Speaker 2" or "RM", "CUSTOMER"
        start_ms: int,
        end_ms: int,
        text_original: str,
        words: Optional[List[WordTimestamp]] = None,
        language: str = "en"
    ):
        self.segment_id = segment_id
        self.speaker_label = speaker_label
        self.start_ms = start_ms
        self.end_ms = end_ms
        self.text_original = text_original
        self.words = words or []
        self.language = language

    def to_dict(self) -> Dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "speaker_label": self.speaker_label,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "text_original": self.text_original,
            "words": [w.to_dict() for w in self.words],
            "language": self.language,
        }


class TranscriptionOutput:
    def __init__(
        self,
        call_id: str,
        duration_s: float,
        language: str,
        segments: List[DiarizedSegment],
        provider_used: str = "mock",
        raw_response: Optional[Dict[str, Any]] = None
    ):
        self.call_id = call_id
        self.duration_s = duration_s
        self.language = language
        self.segments = segments
        self.provider_used = provider_used
        self.raw_response = raw_response or {}


class Transcriber(ABC):
    """Abstract interface for speech transcription."""

    @abstractmethod
    def transcribe(
        self,
        audio_uri: str,
        call_id: str,
        custom_vocabulary: Optional[List[str]] = None
    ) -> TranscriptionOutput:
        """Transcribes audio from storage URI."""
        pass


class MockTranscriber(Transcriber):
    """
    Mock Transcriber that parses the 10 demo call scripts from data/audio/audio_scripts/
    into high-fidelity diarized segments with synthetic timestamps.
    """

    def __init__(self, scripts_dir: Optional[Path] = None):
        if not settings.is_mock():
            raise RuntimeError(
                f"ABSOLUTE RULE 1 VIOLATION: Mock adapter 'MockTranscriber' instantiated "
                f"while ARGUS_PROVIDER_MODE='{settings.PROVIDER_MODE}'. Mock usage is strictly prohibited in live mode!"
            )
        self.scripts_dir = scripts_dir or (Path(__file__).resolve().parents[2] / "data" / "audio" / "audio_scripts")

    def _parse_timestamp(self, ts_str: str) -> int:
        """Parse [M:SS] or [MM:SS] to milliseconds."""
        parts = ts_str.strip("[]").split(":")
        minutes = int(parts[0])
        seconds = int(parts[1])
        return (minutes * 60 + seconds) * 1000

    def transcribe(
        self,
        audio_uri: str,
        call_id: str,
        custom_vocabulary: Optional[List[str]] = None
    ) -> TranscriptionOutput:
        # Match call_id or filename to script file
        # e.g. CALL_RM001_CUST001_20260310_1030 or RM001_CUST001_20260310_1030.wav
        clean_name = call_id.replace("CALL_", "").replace(".wav", "").replace(".mp3", "")
        script_file = self.scripts_dir / f"{clean_name}.txt"

        if not script_file.exists():
            # If not found directly, attempt search by stem
            candidates = list(self.scripts_dir.glob(f"*{clean_name}*.txt"))
            if candidates:
                script_file = candidates[0]
            else:
                # Fallback to the first available script to allow general offline runs
                all_scripts = sorted(self.scripts_dir.glob("*.txt"))
                if all_scripts:
                    script_file = all_scripts[0]
                else:
                    raise FileNotFoundError(f"Mock Transcriber: No audio scripts found in {self.scripts_dir}")

        with open(script_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Parse metadata header
        language = "en"
        duration_s = 90.0
        lang_match = re.search(r"Language:\s*([^\n\r]+)", content, re.IGNORECASE)
        if lang_match:
            lang_val = lang_match.group(1).strip().lower()
            if "hindi" in lang_val and "english" in lang_val:
                language = "hi-en"
            elif "tamil" in lang_val:
                language = "ta"
            elif "hindi" in lang_val:
                language = "hi"
            else:
                language = "en"

        # Parse dialogue lines matching pattern: [M:SS] SPEAKER: Text
        dialogue_pattern = re.compile(r"^\[(\d+:\d{2})\]\s*(RM|CUSTOMER|Speaker\s*\d+):\s*(.+)$", re.MULTILINE)
        matches = dialogue_pattern.findall(content)

        segments = []
        for idx, (ts_str, speaker, text) in enumerate(matches):
            start_ms = self._parse_timestamp(ts_str)
            # Estimate end_ms based on next segment or duration
            if idx + 1 < len(matches):
                next_ts = self._parse_timestamp(matches[idx + 1][0])
                end_ms = max(start_ms + 1000, next_ts - 200)
            else:
                end_ms = start_ms + int(len(text.split()) * 350)  # ~350ms per word
            
            # Synthetic word timestamps
            words = []
            word_list = text.split()
            word_duration = max(50, (end_ms - start_ms) // max(1, len(word_list)))
            curr_w_start = start_ms
            for w in word_list:
                words.append(WordTimestamp(word=w, start_ms=curr_w_start, end_ms=curr_w_start + word_duration))
                curr_w_start += word_duration

            # In mock transcription, speaker_label is speaker turn identifier
            speaker_label = "Speaker 1" if speaker.upper() == "RM" else "Speaker 2"
            segments.append(
                DiarizedSegment(
                    segment_id=idx + 1,
                    speaker_label=speaker_label,
                    start_ms=start_ms,
                    end_ms=end_ms,
                    text_original=text.strip(),
                    words=words,
                    language=language
                )
            )

        if segments:
            duration_s = segments[-1].end_ms / 1000.0

        return TranscriptionOutput(
            call_id=call_id,
            duration_s=duration_s,
            language=language,
            segments=segments,
            provider_used="mock",
            raw_response={"source_script": script_file.name, "segments_parsed": len(segments)}
        )


class VertexGeminiTranscriber(Transcriber):
    """
    Live Transcriber adapter using Vertex AI Gemini audio ingestion.
    Extracts diarized speaker turns, millisecond timestamps, and verbatim speech.
    """

    def __init__(self, model_id: Optional[str] = None):
        self.model_id = model_id or settings.GEMINI_TRANSCRIBE_MODEL or "gemini-3.5-flash"

    def transcribe(
        self,
        audio_uri: str,
        call_id: str,
        custom_vocabulary: Optional[List[str]] = None
    ) -> TranscriptionOutput:
        try:
            import json
            from google import genai
            from google.genai import types

            # =========================================================================
            # PREVIOUS: Vertex AI 2.5 Flash for Transcribe (Commented Out)
            # =========================================================================
            # client = genai.Client(
            #     vertexai=True,
            #     project=settings.PROJECT_ID,
            #     location=settings.VERTEX_LOCATION,  # us-central1
            # )
            # model_to_use = "gemini-2.5-flash"

            # =========================================================================
            # CURRENT: Gemini 3.5 Flash for Transcribe (location="global")
            # Note: gemini-3.5-transcribe-preview rejects response_mime_type="application/json"
            # on multimodal audio requests. gemini-3.5-flash natively handles structured JSON.
            # =========================================================================
            try:
                client = genai.Client(
                    enterprise=True,
                    project=settings.PROJECT_ID,
                    location="global",
                )
            except TypeError:
                client = genai.Client(
                    vertexai=True,
                    project=settings.PROJECT_ID,
                    location="global",
                )
            model_to_use = self.model_id or settings.GEMINI_TRANSCRIBE_MODEL or "gemini-3.5-flash"

            # Build audio part
            if audio_uri.startswith("gs://"):
                audio_part = types.Part.from_uri(file_uri=audio_uri, mime_type="audio/wav")
            else:
                local_path = Path(audio_uri)
                if not local_path.exists():
                    raise FileNotFoundError(f"Audio file not found: {audio_uri}")
                with open(local_path, "rb") as af:
                    audio_part = types.Part.from_bytes(data=af.read(), mime_type="audio/wav")

            vocab_clause = ""
            if custom_vocabulary:
                vocab_clause = f"\nPay special attention to financial products, regulatory terms, and entities: {', '.join(custom_vocabulary[:50])}."

            prompt = (
                "You are an expert audio transcriber and diarizer for banking and investment sales calls.\n"
                "Transcribe this audio recording verbatim with exact 2-speaker diarization and millisecond timestamps.\n"
                "The conversation may be in English, Hindi, Tamil, or code-mixed Hinglish.\n"
                f"{vocab_clause}\n"
                "Return a valid JSON array of objects representing chronological speaker turns:\n"
                "[\n"
                "  {\n"
                '    "segment_id": 1,\n'
                '    "speaker_label": "Speaker 1",\n'
                '    "start_ms": 0,\n'
                '    "end_ms": 3500,\n'
                '    "text_original": "verbatim speech in the original language spoken",\n'
                '    "language": "en"\n'
                "  }\n"
                "]\n"
                "Ensure timestamps are strictly monotonic and within the true audio duration."
            )

            gen_config_kwargs = {"temperature": 0.0}
            if "transcribe" not in model_to_use:
                gen_config_kwargs["response_mime_type"] = "application/json"
            gen_config = types.GenerateContentConfig(**gen_config_kwargs)

            max_retries = 3
            backoff = 2.0
            resp = None
            for attempt in range(1, max_retries + 1):
                try:
                    resp = client.models.generate_content(
                        model=model_to_use,
                        contents=[audio_part, prompt],
                        config=gen_config,
                    )
                    break
                except Exception as exc:
                    err_str = str(exc)
                    if ("429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "503" in err_str or "UNAVAILABLE" in err_str or "Deadline" in err_str) and attempt < max_retries:
                        logger.warning(f"[Retry {attempt}/{max_retries}] Transient Vertex AI error in transcribe: {exc}. Retrying in {backoff}s...")
                        time.sleep(backoff)
                        backoff *= 2.0
                    else:
                        raise

            raw_text = resp.text.strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            turns = json.loads(raw_text.strip())
            if not isinstance(turns, list):
                if isinstance(turns, dict) and "segments" in turns:
                    turns = turns["segments"]
                else:
                    turns = [turns]

            segments = []
            detected_languages = set()
            for idx, turn in enumerate(turns):
                seg_id = turn.get("segment_id", idx + 1)
                speaker = turn.get("speaker_label", f"Speaker {(idx % 2) + 1}")
                start_ms = int(turn.get("start_ms", 0))
                end_ms = int(turn.get("end_ms", start_ms + 1000))
                text = str(turn.get("text_original", "")).strip()
                lang = turn.get("language", "en")
                detected_languages.add(lang)

                words = []
                word_list = text.split()
                if word_list:
                    word_duration = max(50, (end_ms - start_ms) // len(word_list))
                    w_start = start_ms
                    for w in word_list:
                        words.append(WordTimestamp(word=w, start_ms=w_start, end_ms=w_start + word_duration))
                        w_start += word_duration

                segments.append(
                    DiarizedSegment(
                        segment_id=seg_id,
                        speaker_label=speaker,
                        start_ms=start_ms,
                        end_ms=end_ms,
                        text_original=text,
                        words=words,
                        language=lang,
                    )
                )

            duration_s = (segments[-1].end_ms / 1000.0) if segments else 0.0
            primary_language = list(detected_languages)[0] if len(detected_languages) == 1 else "multi"

            return TranscriptionOutput(
                call_id=call_id,
                duration_s=duration_s,
                language=primary_language,
                segments=segments,
                provider_used=f"vertexai:{model_to_use}",
                raw_response={"turns_count": len(segments), "model": model_to_use},
            )
        except Exception as exc:
            raise RuntimeError(f"VertexGeminiTranscriber live execution failed: {exc}")


def get_transcriber(model_id: Optional[str] = None) -> Transcriber:
    """Factory creating Transcriber based on ARGUS_PROVIDER_MODE."""
    if settings.is_mock():
        return MockTranscriber()
    return VertexGeminiTranscriber(model_id=model_id or settings.GEMINI_TRANSCRIBE_MODEL)
