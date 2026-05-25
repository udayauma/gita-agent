"""
Gemini 3 Flash translation module for the Gita Agent ingestion pipeline.

Takes a TranscriptionResult (mixed Telugu/English words with speaker IDs),
groups contiguous same-speaker words into segments, sends them to Gemini
for context-aware translation that preserves Sanskrit terms and speaker
attribution, and falls back to Google Cloud Translation API on Gemini
failure.

Design reference: docs/detailed_technical_design.md § 3.5

Usage:
    from ingestion.transcription import transcribe
    from ingestion.translation import translate

    transcription = transcribe(audio_uri, video_id)
    translated = translate(transcription)
    print(translated.full_text)
"""

import json
import os
from dataclasses import dataclass
from typing import Optional

import structlog

from ingestion.observability import get_tracer
from ingestion.transcription import TranscriptionResult, TranscriptWord

logger = structlog.get_logger(__name__)

DEFAULT_MODEL = "gemini-3-flash-preview"
DEFAULT_CHUNK_SIZE_SEGMENTS = 50  # ~50 speaker-grouped segments per Gemini call
FALLBACK_TARGET_LANGUAGE = "en"
FALLBACK_SOURCE_LANGUAGE = "te"

TRANSLATION_PROMPT = """You are translating a conversation about the Bhagavad Gita \
between a father (Guru/Nanna, Speaker 1) and daughter (Student/Udaya, Speaker 2).

The text below contains Telugu and English mixed speech (code-switching).

Rules:
- Translate ALL Telugu portions to natural English.
- Keep English portions exactly as-is — do NOT paraphrase them.
- Preserve speaker attribution: each input segment carries a "speaker" number; \
output segments must keep the same speaker number.
- Preserve spiritual/philosophical terms in their original Sanskrit where \
commonly known: dharma, karma, atman, moksha, yoga, bhakti, jnana, samsara.
- Preserve the order of segments.

Input segments (JSON):
{input_json}

Respond with JSON only, matching this schema exactly:
{{"segments": [{{"speaker": <int>, "text": "<translated text>", "source_language": "<te-IN or en-US>"}}]}}
"""


class TranslationError(Exception):
    """Raised when translation fails or produces unparseable output."""


@dataclass
class TranslatedSegment:
    """A speaker-attributed, time-bounded chunk of translated English text."""

    text: str
    speaker_id: int
    start_time: float
    end_time: float
    source_language: Optional[str]


@dataclass
class TranslationResult:
    """Parsed result of a Gemini (or fallback) translation pass."""

    video_id: str
    segments: list[TranslatedSegment]
    full_text: str
    used_fallback: bool


# ---------------------------------------------------------------------------
# Patchable seams — tests replace these to avoid real API calls.
# ---------------------------------------------------------------------------

def build_gemini_model(model_name: str = DEFAULT_MODEL):
    """Factory for the Gemini GenerativeModel. Patched in unit tests."""
    import google.generativeai as genai
    api_key = os.environ.get("GOOGLE_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)


def build_translate_client():
    """Factory for the Cloud Translation V3 client. Patched in unit tests."""
    from google.cloud import translate_v3
    return translate_v3.TranslationServiceClient()


# ---------------------------------------------------------------------------
# Segmentation
# ---------------------------------------------------------------------------

@dataclass
class _SourceSegment:
    """Pre-translation segment: contiguous same-speaker words."""

    speaker_id: int
    start_time: float
    end_time: float
    text: str
    source_language: Optional[str]


def _group_into_segments(words: list[TranscriptWord]) -> list[_SourceSegment]:
    """Walk words and group contiguous same-speaker runs into segments."""
    segments: list[_SourceSegment] = []
    if not words:
        return segments

    current_speaker = words[0].speaker_id
    current_words: list[TranscriptWord] = []

    def _flush():
        if not current_words:
            return
        # Source language: use the majority language across the run, or the first word's.
        langs = [w.language_code for w in current_words if w.language_code]
        source_lang = max(set(langs), key=langs.count) if langs else None
        segments.append(
            _SourceSegment(
                speaker_id=current_speaker,
                start_time=current_words[0].start_time,
                end_time=current_words[-1].end_time,
                text=" ".join(w.text for w in current_words),
                source_language=source_lang,
            )
        )

    for w in words:
        if w.speaker_id != current_speaker:
            _flush()
            current_speaker = w.speaker_id
            current_words = [w]
        else:
            current_words.append(w)
    _flush()
    return segments


def _chunk_segments(segments: list[_SourceSegment], chunk_size: int) -> list[list[_SourceSegment]]:
    """Split a segment list into chunks of at most `chunk_size` for per-call translation."""
    return [segments[i : i + chunk_size] for i in range(0, len(segments), chunk_size)]


# ---------------------------------------------------------------------------
# Gemini path
# ---------------------------------------------------------------------------

def _build_prompt(segments: list[_SourceSegment]) -> str:
    payload = [
        {
            "speaker": s.speaker_id,
            "text": s.text,
            "source_language": s.source_language or "unknown",
        }
        for s in segments
    ]
    return TRANSLATION_PROMPT.format(input_json=json.dumps(payload, ensure_ascii=False))


def _parse_gemini_response(response_text: str) -> list[dict]:
    """Parse a Gemini JSON response, tolerating ```json fences."""
    text = response_text.strip()
    if text.startswith("```"):
        # Strip a leading ```json (or ```) fence and a trailing ``` fence.
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise TranslationError(f"Gemini response was not valid JSON: {e}") from e
    if "segments" not in data or not isinstance(data["segments"], list):
        raise TranslationError("Gemini response missing 'segments' list")
    return data["segments"]


def _translate_via_gemini(
    chunks: list[list[_SourceSegment]], model
) -> list[TranslatedSegment]:
    """Translate every chunk through Gemini and stitch results back together, preserving time bounds."""
    translated: list[TranslatedSegment] = []
    for chunk in chunks:
        prompt = _build_prompt(chunk)
        response = model.generate_content(prompt)
        parsed = _parse_gemini_response(response.text)
        if len(parsed) != len(chunk):
            raise TranslationError(
                f"Gemini returned {len(parsed)} segments for a {len(chunk)}-segment chunk"
            )
        for source, out in zip(chunk, parsed):
            translated.append(
                TranslatedSegment(
                    text=out["text"],
                    speaker_id=int(out.get("speaker", source.speaker_id)),
                    start_time=source.start_time,
                    end_time=source.end_time,
                    source_language=out.get("source_language") or source.source_language,
                )
            )
    return translated


# ---------------------------------------------------------------------------
# Cloud Translation fallback path
# ---------------------------------------------------------------------------

def _translate_via_cloud(
    segments: list[_SourceSegment], client, project_id: str
) -> list[TranslatedSegment]:
    """Translate each segment one-by-one via Cloud Translation V3."""
    translated: list[TranslatedSegment] = []
    parent = f"projects/{project_id}/locations/global"
    for seg in segments:
        # Skip translation for already-English segments.
        if seg.source_language and seg.source_language.startswith("en"):
            translated.append(
                TranslatedSegment(
                    text=seg.text,
                    speaker_id=seg.speaker_id,
                    start_time=seg.start_time,
                    end_time=seg.end_time,
                    source_language=seg.source_language,
                )
            )
            continue
        response = client.translate_text(
            request={
                "parent": parent,
                "contents": [seg.text],
                "mime_type": "text/plain",
                "source_language_code": FALLBACK_SOURCE_LANGUAGE,
                "target_language_code": FALLBACK_TARGET_LANGUAGE,
            }
        )
        translated_text = response.translations[0].translated_text
        translated.append(
            TranslatedSegment(
                text=translated_text,
                speaker_id=seg.speaker_id,
                start_time=seg.start_time,
                end_time=seg.end_time,
                source_language=seg.source_language,
            )
        )
    return translated


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def translate(
    transcription: TranscriptionResult,
    *,
    model: str = DEFAULT_MODEL,
    chunk_size: int = DEFAULT_CHUNK_SIZE_SEGMENTS,
    enable_fallback: bool = True,
    project_id: Optional[str] = None,
) -> TranslationResult:
    """Translate a TranscriptionResult to English-with-Sanskrit, preserving speaker order.

    Args:
        transcription: Output of `ingestion.transcription.transcribe()`.
        model: Gemini model name (default: gemini-3-flash-preview).
        chunk_size: Max source segments per Gemini call.
        enable_fallback: If True, fall back to Cloud Translation API on Gemini failure.
        project_id: GCP project for Cloud Translation fallback. Defaults to $GCP_PROJECT_ID
            or "gita-agent-prod".

    Returns:
        TranslationResult with per-segment English text, speaker IDs, and time bounds.

    Raises:
        TranslationError: empty input, unparseable Gemini output, or both paths failed.
    """
    if not transcription.words:
        raise TranslationError("Cannot translate an empty transcription")

    source_segments = _group_into_segments(transcription.words)
    chunks = _chunk_segments(source_segments, chunk_size)
    total_input_chars = sum(len(s.text) for s in source_segments)

    tracer = get_tracer(__name__)
    with tracer.start_as_current_span("translation.translate_segments") as span:
        span.set_attribute("video_id", transcription.video_id)
        span.set_attribute("source_segment_count", len(source_segments))
        span.set_attribute("chunk_count", len(chunks))
        span.set_attribute("total_chars", total_input_chars)

        used_fallback = False
        try:
            gemini = build_gemini_model(model)
            translated = _translate_via_gemini(chunks, gemini)
            logger.info(
                "translation.gemini_success",
                video_id=transcription.video_id,
                segment_count=len(translated),
                chunk_count=len(chunks),
            )
        except Exception as e:
            if not enable_fallback:
                if isinstance(e, TranslationError):
                    raise
                raise TranslationError(f"Gemini translation failed: {e}") from e
            logger.warning(
                "translation.gemini_failed_using_fallback",
                video_id=transcription.video_id,
                error=str(e),
            )
            try:
                project = project_id or os.environ.get("GCP_PROJECT_ID", "gita-agent-prod")
                client = build_translate_client()
                translated = _translate_via_cloud(source_segments, client, project)
                used_fallback = True
                logger.info(
                    "translation.fallback_success",
                    video_id=transcription.video_id,
                    segment_count=len(translated),
                )
            except Exception as fallback_err:
                raise TranslationError(
                    f"Both Gemini and Cloud Translation failed. Gemini: {e}; "
                    f"Cloud Translation: {fallback_err}"
                ) from fallback_err

        full_text = " ".join(seg.text for seg in translated).strip()
        span.set_attribute("segment_count", len(translated))
        span.set_attribute("used_fallback", used_fallback)
        return TranslationResult(
            video_id=transcription.video_id,
            segments=translated,
            full_text=full_text,
            used_fallback=used_fallback,
        )
