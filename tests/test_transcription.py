"""
Tests for ingestion/transcription.py — Chirp 3 transcription module.

TDD Phase: RED — tests written before implementation.

The transcription module wraps Google Cloud Speech-to-Text V2 (Chirp 3)
BatchRecognize: builds the RecognitionConfig, submits the long-running
operation, polls for completion, fetches the JSON output from GCS, and
parses it into a TranscriptionResult dataclass.

Design reference: docs/detailed_technical_design.md § 3.4

All Cloud Speech API calls and GCS reads are mocked — no real network
or billed API calls in unit tests. End-to-end validation happens in
Phase 4.7 against one real recording.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from ingestion.transcription import (
    TranscriptionError,
    TranscriptionResult,
    TranscriptWord,
    transcribe,
)


# ---------------------------------------------------------------------------
# Fixtures — simulated Chirp 3 BatchRecognize JSON output
# ---------------------------------------------------------------------------
# Chirp 3 writes results to gcs_output_config.uri as JSON. The shape below
# matches the speech_v2 BatchRecognizeResults proto serialized to JSON:
# https://cloud.google.com/speech-to-text/v2/docs/reference/rest/v2/BatchRecognizeResults

SAMPLE_TELUGU_TRANSCRIPT_JSON = {
    "results": [
        {
            "alternatives": [
                {
                    "transcript": "నమస్కారం ఉదయ ఈరోజు మనం భగవద్గీత గురించి మాట్లాడుదాం",
                    "confidence": 0.94,
                    "words": [
                        {"word": "నమస్కారం", "startOffset": "0.0s", "endOffset": "0.8s", "speakerLabel": "1"},
                        {"word": "ఉదయ", "startOffset": "0.8s", "endOffset": "1.2s", "speakerLabel": "1"},
                        {"word": "ఈరోజు", "startOffset": "1.2s", "endOffset": "1.7s", "speakerLabel": "1"},
                        {"word": "మనం", "startOffset": "1.7s", "endOffset": "2.0s", "speakerLabel": "1"},
                        {"word": "భగవద్గీత", "startOffset": "2.0s", "endOffset": "2.9s", "speakerLabel": "1"},
                        {"word": "గురించి", "startOffset": "2.9s", "endOffset": "3.4s", "speakerLabel": "1"},
                        {"word": "మాట్లాడుదాం", "startOffset": "3.4s", "endOffset": "4.2s", "speakerLabel": "1"},
                    ],
                }
            ],
            "languageCode": "te-IN",
            "resultEndOffset": "4.2s",
        },
        {
            "alternatives": [
                {
                    "transcript": "okay Nanna I am ready",
                    "confidence": 0.91,
                    "words": [
                        {"word": "okay", "startOffset": "4.5s", "endOffset": "4.8s", "speakerLabel": "2"},
                        {"word": "Nanna", "startOffset": "4.8s", "endOffset": "5.2s", "speakerLabel": "2"},
                        {"word": "I", "startOffset": "5.2s", "endOffset": "5.4s", "speakerLabel": "2"},
                        {"word": "am", "startOffset": "5.4s", "endOffset": "5.6s", "speakerLabel": "2"},
                        {"word": "ready", "startOffset": "5.6s", "endOffset": "6.0s", "speakerLabel": "2"},
                    ],
                }
            ],
            "languageCode": "en-US",
            "resultEndOffset": "6.0s",
        },
        {
            "alternatives": [
                {
                    "transcript": "మంచిది అధ్యాయం రెండు చదువు",
                    "confidence": 0.93,
                    "words": [
                        {"word": "మంచిది", "startOffset": "6.3s", "endOffset": "6.8s", "speakerLabel": "1"},
                        {"word": "అధ్యాయం", "startOffset": "6.8s", "endOffset": "7.4s", "speakerLabel": "1"},
                        {"word": "రెండు", "startOffset": "7.4s", "endOffset": "7.8s", "speakerLabel": "1"},
                        {"word": "చదువు", "startOffset": "7.8s", "endOffset": "8.3s", "speakerLabel": "1"},
                    ],
                }
            ],
            "languageCode": "te-IN",
            "resultEndOffset": "8.3s",
        },
    ]
}


@pytest.fixture
def mock_speech_client():
    """Mocked SpeechClient with a BatchRecognize LRO that resolves immediately.

    The LRO response carries `results` (a dict keyed by input audio URI) where
    each value has a `uri` pointing at the actual transcript JSON output. We
    return a single canonical entry; the transcription module's single-input
    fast path falls back to the only value present regardless of key.
    """
    client = MagicMock()
    operation = MagicMock()
    operation.done.return_value = True
    file_result = MagicMock(uri="gs://gita-agent-prod-audio/test_video/transcript/auto_named.json")
    response = MagicMock()
    response.results = {"test-input": file_result}
    operation.result.return_value = response
    client.batch_recognize.return_value = operation
    return client


@pytest.fixture
def mock_transcript_json():
    """Mocked GCS fetch returning the canonical sample JSON."""
    return SAMPLE_TELUGU_TRANSCRIPT_JSON


@pytest.fixture
def transcribe_with_mocks(mock_speech_client, mock_transcript_json):
    """
    Patch both the SpeechClient factory and the GCS JSON fetcher,
    then invoke transcribe() with canonical inputs.
    """
    with patch("ingestion.transcription.build_speech_client", return_value=mock_speech_client), \
         patch("ingestion.transcription.storage.download_json", return_value=mock_transcript_json):
        result = transcribe(
            audio_uri="gs://gita-agent-prod-audio/test_video/audio.flac",
            video_id="test_video",
        )
    return result


# ---------------------------------------------------------------------------
# Required Phase 4.3 tests
# ---------------------------------------------------------------------------

class TestChirp3ReturnsTeluguText:
    """Verify Telugu transcript text reaches the parsed result."""

    def test_chirp3_returns_telugu_text(self, transcribe_with_mocks):
        result = transcribe_with_mocks
        assert isinstance(result, TranscriptionResult)
        # At least one Telugu word from the sample must appear in the full text.
        assert "భగవద్గీత" in result.full_text
        assert "నమస్కారం" in result.full_text

    def test_telugu_words_carry_language_code(self, transcribe_with_mocks):
        telugu_words = [w for w in transcribe_with_mocks.words if w.language_code == "te-IN"]
        assert len(telugu_words) > 0
        assert any(w.text == "భగవద్గీత" for w in telugu_words)


class TestChirp3DetectsEnglishSegments:
    """Verify code-switched English segments are preserved with en-US language code."""

    def test_chirp3_detects_english_segments(self, transcribe_with_mocks):
        result = transcribe_with_mocks
        english_words = [w for w in result.words if w.language_code == "en-US"]
        assert len(english_words) >= 1
        english_text = " ".join(w.text for w in english_words)
        assert "Nanna" in english_text
        assert "ready" in english_text

    def test_english_and_telugu_coexist_in_same_transcript(self, transcribe_with_mocks):
        languages = {w.language_code for w in transcribe_with_mocks.words}
        assert "te-IN" in languages
        assert "en-US" in languages


class TestDiarizationIdentifiesTwoSpeakers:
    """Verify diarization assigns distinct speaker IDs to Nanna and Udaya."""

    def test_diarization_identifies_two_speakers(self, transcribe_with_mocks):
        result = transcribe_with_mocks
        speaker_ids = {w.speaker_id for w in result.words}
        assert len(speaker_ids) >= 2
        assert result.speaker_count >= 2

    def test_speaker_ids_are_integers(self, transcribe_with_mocks):
        for word in transcribe_with_mocks.words:
            assert isinstance(word.speaker_id, int)
            assert word.speaker_id >= 1

    def test_each_speaker_has_attributed_words(self, transcribe_with_mocks):
        words_by_speaker: dict[int, list[TranscriptWord]] = {}
        for w in transcribe_with_mocks.words:
            words_by_speaker.setdefault(w.speaker_id, []).append(w)
        # Both speaker 1 (Nanna) and speaker 2 (Udaya) should have words.
        assert len(words_by_speaker.get(1, [])) > 0
        assert len(words_by_speaker.get(2, [])) > 0


class TestWordTimestampsAreSequential:
    """Verify per-word timestamps are monotonically non-decreasing across the transcript."""

    def test_word_timestamps_are_sequential(self, transcribe_with_mocks):
        words = transcribe_with_mocks.words
        for i in range(1, len(words)):
            assert words[i].start_time >= words[i - 1].start_time, (
                f"Word {i} ({words[i].text!r} @ {words[i].start_time}s) starts before "
                f"word {i-1} ({words[i-1].text!r} @ {words[i-1].start_time}s)"
            )

    def test_word_end_time_after_start_time(self, transcribe_with_mocks):
        for w in transcribe_with_mocks.words:
            assert w.end_time >= w.start_time, (
                f"{w.text!r} has end_time {w.end_time} < start_time {w.start_time}"
            )

    def test_timestamps_are_floats_in_seconds(self, transcribe_with_mocks):
        for w in transcribe_with_mocks.words:
            assert isinstance(w.start_time, float)
            assert isinstance(w.end_time, float)
            # Sanity: a recording shouldn't exceed ~10 hours.
            assert 0.0 <= w.start_time < 36000.0


# ---------------------------------------------------------------------------
# Supporting tests — config, LRO handling, error paths
# ---------------------------------------------------------------------------

class TestBatchRecognizeRequest:
    """Verify the BatchRecognizeRequest is built with the design-doc config."""

    def test_request_uses_chirp_3_model(self, mock_speech_client, mock_transcript_json):
        with patch("ingestion.transcription.build_speech_client", return_value=mock_speech_client), \
             patch("ingestion.transcription.storage.download_json", return_value=mock_transcript_json):
            transcribe(audio_uri="gs://b/a.flac", video_id="test_video")
        call_args = mock_speech_client.batch_recognize.call_args
        request = call_args.kwargs.get("request") or call_args.args[0]
        assert request.config.model == "chirp_3"

    def test_request_includes_telugu_and_english(self, mock_speech_client, mock_transcript_json):
        with patch("ingestion.transcription.build_speech_client", return_value=mock_speech_client), \
             patch("ingestion.transcription.storage.download_json", return_value=mock_transcript_json):
            transcribe(audio_uri="gs://b/a.flac", video_id="test_video")
        call_args = mock_speech_client.batch_recognize.call_args
        request = call_args.kwargs.get("request") or call_args.args[0]
        assert "te-IN" in request.config.language_codes
        assert "en-US" in request.config.language_codes

    def test_request_enables_word_timestamps_and_diarization(self, mock_speech_client, mock_transcript_json):
        with patch("ingestion.transcription.build_speech_client", return_value=mock_speech_client), \
             patch("ingestion.transcription.storage.download_json", return_value=mock_transcript_json):
            transcribe(audio_uri="gs://b/a.flac", video_id="test_video")
        call_args = mock_speech_client.batch_recognize.call_args
        request = call_args.kwargs.get("request") or call_args.args[0]
        assert request.config.features.enable_word_time_offsets is True
        assert request.config.features.diarization_config.max_speaker_count >= 2

    def test_request_points_at_supplied_audio_uri(self, mock_speech_client, mock_transcript_json):
        with patch("ingestion.transcription.build_speech_client", return_value=mock_speech_client), \
             patch("ingestion.transcription.storage.download_json", return_value=mock_transcript_json):
            transcribe(audio_uri="gs://my-bucket/some_video/audio.flac", video_id="some_video")
        call_args = mock_speech_client.batch_recognize.call_args
        request = call_args.kwargs.get("request") or call_args.args[0]
        assert request.files[0].uri == "gs://my-bucket/some_video/audio.flac"


class TestErrorHandling:
    """Verify the module raises TranscriptionError on malformed input or API failure."""

    def test_rejects_non_gcs_audio_uri(self, mock_speech_client):
        with patch("ingestion.transcription.build_speech_client", return_value=mock_speech_client):
            with pytest.raises(TranscriptionError, match="gs://"):
                transcribe(audio_uri="/local/path/audio.flac", video_id="v1")

    def test_rejects_empty_video_id(self, mock_speech_client):
        with patch("ingestion.transcription.build_speech_client", return_value=mock_speech_client):
            with pytest.raises(TranscriptionError, match="video_id"):
                transcribe(audio_uri="gs://b/a.flac", video_id="")

    def test_raises_when_lro_fails(self, mock_transcript_json):
        client = MagicMock()
        operation = MagicMock()
        operation.done.return_value = True
        operation.exception.return_value = RuntimeError("Chirp 3 internal error")
        operation.result.side_effect = RuntimeError("Chirp 3 internal error")
        client.batch_recognize.return_value = operation
        with patch("ingestion.transcription.build_speech_client", return_value=client), \
             patch("ingestion.transcription.storage.download_json", return_value=mock_transcript_json):
            with pytest.raises(TranscriptionError):
                transcribe(audio_uri="gs://b/a.flac", video_id="v1")


# ---------------------------------------------------------------------------
# Observability — Phase 4.7
# ---------------------------------------------------------------------------

class TestTranscriptionSpans:
    """Verify the batch_recognize span + LRO poll sub-span are emitted."""

    def test_emits_batch_recognize_span_with_lro_child(
        self, mock_speech_client, mock_transcript_json, in_memory_spans
    ):
        with patch("ingestion.transcription.build_speech_client", return_value=mock_speech_client), \
             patch("ingestion.transcription.storage.download_json", return_value=mock_transcript_json):
            transcribe(
                audio_uri="gs://gita-agent-prod-audio/test_video/audio.flac",
                video_id="test_video",
            )

        spans = in_memory_spans.get_finished_spans()
        parents = [s for s in spans if s.name == "transcription.batch_recognize"]
        children = [s for s in spans if s.name == "transcription.poll_lro"]

        assert len(parents) == 1
        assert len(children) == 1

        parent = parents[0]
        child = children[0]
        assert parent.attributes["video_id"] == "test_video"
        assert parent.attributes["audio_uri"] == "gs://gita-agent-prod-audio/test_video/audio.flac"
        assert child.parent.span_id == parent.context.span_id
