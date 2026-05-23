"""
Chirp 3 transcription module for the Gita Agent ingestion pipeline.

Wraps Google Cloud Speech-to-Text V2 (Chirp 3) BatchRecognize: builds the
RecognitionConfig with Telugu + English language codes, word-level
timestamps, and speaker diarization; submits the long-running operation;
polls for completion; fetches the JSON output from GCS; and parses it
into a TranscriptionResult dataclass.

Design reference: docs/detailed_technical_design.md § 3.4

Usage:
    from ingestion.transcription import transcribe

    result = transcribe(
        audio_uri="gs://gita-agent-prod-audio/nanna_udaya_2025_07_06/audio.flac",
        video_id="nanna_udaya_2025_07_06",
    )
    print(f"{len(result.words)} words across {result.speaker_count} speakers")
"""

import json
import os
from dataclasses import dataclass
from typing import Optional

import structlog
from google.cloud import storage
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech

logger = structlog.get_logger(__name__)

DEFAULT_PROJECT_ID = "gita-agent-prod"
DEFAULT_LANGUAGE_CODES = ("te-IN", "en-US")
DEFAULT_MODEL = "chirp_3"
DEFAULT_MIN_SPEAKERS = 1
DEFAULT_MAX_SPEAKERS = 3
DEFAULT_TIMEOUT_SECONDS = 3600.0


class TranscriptionError(Exception):
    """Raised when Chirp 3 transcription fails or produces invalid output."""


@dataclass
class TranscriptWord:
    """A single word from the transcript with timing, speaker, and language metadata."""

    text: str
    start_time: float
    end_time: float
    speaker_id: int
    language_code: Optional[str]


@dataclass
class TranscriptionResult:
    """Parsed result of a Chirp 3 BatchRecognize operation."""

    video_id: str
    words: list[TranscriptWord]
    full_text: str
    speaker_count: int
    audio_uri: str
    output_uri: str


# ---------------------------------------------------------------------------
# Patchable seams — tests replace these to avoid real API/network calls.
# ---------------------------------------------------------------------------

def build_speech_client() -> SpeechClient:
    """Factory for SpeechClient. Patched in unit tests."""
    return SpeechClient()


def _fetch_transcript_json(gcs_uri: str) -> dict:
    """Fetch a JSON blob from GCS and return its parsed dict. Patched in unit tests."""
    if not gcs_uri.startswith("gs://"):
        raise TranscriptionError(f"Expected gs:// URI, got: {gcs_uri}")
    bucket_name, _, blob_path = gcs_uri[len("gs://"):].partition("/")
    client = storage.Client()
    blob = client.bucket(bucket_name).blob(blob_path)
    return json.loads(blob.download_as_bytes())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_offset(offset) -> float:
    """Parse a duration like '1.5s', '500ms', or a number into seconds (float)."""
    if isinstance(offset, (int, float)):
        return float(offset)
    s = str(offset).strip()
    if s.endswith("ms"):
        return float(s[:-2]) / 1000.0
    if s.endswith("s"):
        return float(s[:-1])
    return float(s)


def _derive_output_uri(audio_uri: str, video_id: str) -> str:
    """Output prefix lives in the same bucket as the audio, under {video_id}/transcript/."""
    bucket = audio_uri[len("gs://"):].split("/", 1)[0]
    return f"gs://{bucket}/{video_id}/transcript/"


def _validate_inputs(audio_uri: str, video_id: str) -> None:
    if not audio_uri.startswith("gs://"):
        raise TranscriptionError(
            f"audio_uri must be a gs:// URI; got: {audio_uri}"
        )
    if not video_id:
        raise TranscriptionError("video_id must be a non-empty string")


def _build_request(
    audio_uri: str,
    output_uri: str,
    project_id: str,
) -> cloud_speech.BatchRecognizeRequest:
    config = cloud_speech.RecognitionConfig(
        auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
        language_codes=list(DEFAULT_LANGUAGE_CODES),
        model=DEFAULT_MODEL,
        features=cloud_speech.RecognitionFeatures(
            enable_word_time_offsets=True,
            enable_automatic_punctuation=True,
            diarization_config=cloud_speech.SpeakerDiarizationConfig(
                min_speaker_count=DEFAULT_MIN_SPEAKERS,
                max_speaker_count=DEFAULT_MAX_SPEAKERS,
            ),
        ),
    )
    return cloud_speech.BatchRecognizeRequest(
        recognizer=f"projects/{project_id}/locations/global/recognizers/_",
        config=config,
        files=[cloud_speech.BatchRecognizeFileMetadata(uri=audio_uri)],
        recognition_output_config=cloud_speech.RecognitionOutputConfig(
            gcs_output_config=cloud_speech.GcsOutputConfig(uri=output_uri),
        ),
    )


def _parse_results(
    payload: dict,
    audio_uri: str,
    output_uri: str,
    video_id: str,
) -> TranscriptionResult:
    words: list[TranscriptWord] = []
    transcript_parts: list[str] = []
    for result in payload.get("results", []):
        alternatives = result.get("alternatives", [])
        if not alternatives:
            continue
        alt = alternatives[0]
        language_code = result.get("languageCode")
        transcript = alt.get("transcript", "")
        if transcript:
            transcript_parts.append(transcript)
        for w in alt.get("words", []):
            words.append(
                TranscriptWord(
                    text=w["word"],
                    start_time=_parse_offset(w.get("startOffset", 0.0)),
                    end_time=_parse_offset(w.get("endOffset", 0.0)),
                    speaker_id=int(w.get("speakerLabel", 1)),
                    language_code=language_code,
                )
            )
    words.sort(key=lambda x: x.start_time)
    speaker_count = len({w.speaker_id for w in words})
    return TranscriptionResult(
        video_id=video_id,
        words=words,
        full_text=" ".join(transcript_parts).strip(),
        speaker_count=speaker_count,
        audio_uri=audio_uri,
        output_uri=output_uri,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def transcribe(
    audio_uri: str,
    video_id: str,
    *,
    project_id: Optional[str] = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> TranscriptionResult:
    """Submit audio to Chirp 3 BatchRecognize, poll to completion, return parsed result.

    Args:
        audio_uri: GCS URI of the input FLAC file (gs://bucket/path/audio.flac).
        video_id: Identifier from drive.sanitize_video_id() — used in the output path.
        project_id: GCP project for the Speech recognizer. Defaults to $GCP_PROJECT_ID
            or "gita-agent-prod".
        timeout: Max seconds to wait for the LRO. Hour-long recordings typically
            complete in a few minutes; default 1 hour is a generous ceiling.

    Returns:
        TranscriptionResult with per-word timestamps, speaker IDs, and language codes.

    Raises:
        TranscriptionError: invalid inputs, LRO failure, or unparseable output.
    """
    _validate_inputs(audio_uri, video_id)
    project = project_id or os.environ.get("GCP_PROJECT_ID", DEFAULT_PROJECT_ID)
    output_uri = _derive_output_uri(audio_uri, video_id)

    client = build_speech_client()
    request = _build_request(audio_uri, output_uri, project)
    logger.info(
        "transcription.submit",
        video_id=video_id,
        audio_uri=audio_uri,
        output_uri=output_uri,
    )

    operation = client.batch_recognize(request=request)
    try:
        operation.result(timeout=timeout)
    except Exception as e:
        logger.error("transcription.lro_failed", video_id=video_id, error=str(e))
        raise TranscriptionError(f"Chirp 3 BatchRecognize failed: {e}") from e

    # Chirp 3 writes one JSON file per input under the gcs_output_config prefix.
    # Phase 4.7 will inspect the LRO response for the exact output path; for now
    # we rely on the conventional location.
    transcript_uri = output_uri.rstrip("/") + "/transcript.json"
    payload = _fetch_transcript_json(transcript_uri)

    result = _parse_results(payload, audio_uri, output_uri, video_id)
    logger.info(
        "transcription.complete",
        video_id=video_id,
        word_count=len(result.words),
        speaker_count=result.speaker_count,
    )
    return result
