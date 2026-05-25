"""
Tests for ingestion/translation.py — Gemini 3 Flash translation module.

TDD Phase: RED — tests written before implementation.

The translation module takes a TranscriptionResult (mixed Telugu/English with
speaker IDs), groups contiguous same-speaker words into segments, sends them
to Gemini 3 Flash for context-aware translation (preserving Sanskrit terms
and speaker attribution), and falls back to Cloud Translation API on Gemini
failure.

Design reference: docs/detailed_technical_design.md § 3.5

All Gemini API calls and Cloud Translate calls are mocked — no real network
or billed API calls in unit tests. End-to-end validation happens in Phase
4.8 against real transcripts.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from ingestion.transcription import (
    TranscriptionResult,
    TranscriptWord,
)
from ingestion.translation import (
    TranslatedSegment,
    TranslationError,
    TranslationResult,
    translate,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VIDEO_ID = "nanna_udaya_2025_07_06"


def _make_word(text: str, start: float, end: float, speaker: int, lang: str) -> TranscriptWord:
    return TranscriptWord(
        text=text, start_time=start, end_time=end, speaker_id=speaker, language_code=lang,
    )


@pytest.fixture
def mixed_transcript() -> TranscriptionResult:
    """A short mixed Telugu/English transcript: Nanna asks, Udaya responds in English."""
    words = [
        # Speaker 1 (Nanna), Telugu — explaining karma
        _make_word("నమస్కారం", 0.0, 0.8, 1, "te-IN"),
        _make_word("ఈరోజు", 0.8, 1.3, 1, "te-IN"),
        _make_word("కర్మ", 1.3, 1.8, 1, "te-IN"),
        _make_word("గురించి", 1.8, 2.3, 1, "te-IN"),
        _make_word("మాట్లాడుదాం", 2.3, 3.0, 1, "te-IN"),
        # Speaker 2 (Udaya), English response
        _make_word("okay", 3.5, 3.8, 2, "en-US"),
        _make_word("Nanna", 3.8, 4.2, 2, "en-US"),
        _make_word("I", 4.2, 4.4, 2, "en-US"),
        _make_word("am", 4.4, 4.6, 2, "en-US"),
        _make_word("ready", 4.6, 5.0, 2, "en-US"),
        # Speaker 1 (Nanna), Telugu — invoking dharma
        _make_word("ధర్మం", 5.5, 6.0, 1, "te-IN"),
        _make_word("అంటే", 6.0, 6.5, 1, "te-IN"),
        _make_word("ఏంటి", 6.5, 7.0, 1, "te-IN"),
    ]
    return TranscriptionResult(
        video_id=VIDEO_ID,
        words=words,
        full_text="నమస్కారం ఈరోజు కర్మ గురించి మాట్లాడుదాం okay Nanna I am ready ధర్మం అంటే ఏంటి",
        speaker_count=2,
        audio_uri=f"gs://gita-agent-prod-audio/{VIDEO_ID}/audio.flac",
        output_uri=f"gs://gita-agent-prod-audio/{VIDEO_ID}/transcript/",
    )


@pytest.fixture
def english_only_transcript() -> TranscriptionResult:
    words = [
        _make_word("What", 0.0, 0.3, 1, "en-US"),
        _make_word("is", 0.3, 0.5, 1, "en-US"),
        _make_word("dharma", 0.5, 1.0, 1, "en-US"),
        _make_word("Udaya", 1.0, 1.5, 1, "en-US"),
        _make_word("It", 2.0, 2.2, 2, "en-US"),
        _make_word("is", 2.2, 2.4, 2, "en-US"),
        _make_word("righteousness", 2.4, 3.2, 2, "en-US"),
    ]
    return TranscriptionResult(
        video_id="english_only",
        words=words,
        full_text="What is dharma Udaya It is righteousness",
        speaker_count=2,
        audio_uri="gs://b/english_only/audio.flac",
        output_uri="gs://b/english_only/transcript/",
    )


def _gemini_response(segments: list[dict]) -> MagicMock:
    """Build a mock Gemini GenerateContentResponse with a JSON .text body."""
    resp = MagicMock()
    resp.text = json.dumps({"segments": segments})
    return resp


@pytest.fixture
def mock_gemini_model_telugu_translated():
    """Gemini returns context-aware English translation, preserving Sanskrit + speakers."""
    model = MagicMock()
    model.generate_content.return_value = _gemini_response([
        {"speaker": 1, "text": "Greetings. Today let us discuss karma.", "source_language": "te-IN"},
        {"speaker": 2, "text": "okay Nanna I am ready", "source_language": "en-US"},
        {"speaker": 1, "text": "What is dharma?", "source_language": "te-IN"},
    ])
    return model


@pytest.fixture
def mock_gemini_model_english_passthrough():
    """Gemini returns English input unchanged."""
    model = MagicMock()
    model.generate_content.return_value = _gemini_response([
        {"speaker": 1, "text": "What is dharma Udaya", "source_language": "en-US"},
        {"speaker": 2, "text": "It is righteousness", "source_language": "en-US"},
    ])
    return model


# ---------------------------------------------------------------------------
# Required Phase 4.4 tests
# ---------------------------------------------------------------------------

class TestGeminiTranslatesTeluguToEnglish:
    """Verify Telugu segments are translated to English via Gemini."""

    def test_gemini_translates_telugu_to_english(self, mixed_transcript, mock_gemini_model_telugu_translated):
        with patch("ingestion.translation.build_gemini_model", return_value=mock_gemini_model_telugu_translated):
            result = translate(mixed_transcript)

        assert isinstance(result, TranslationResult)
        # The Telugu greeting should now read in English.
        assert any("karma" in seg.text.lower() for seg in result.segments)
        assert any("dharma" in seg.text.lower() for seg in result.segments)
        # full_text should be roman-script (no Telugu characters remaining for translated segments).
        telugu_chars_in_translated_segments = any(
            any("ఀ" <= ch <= "౿" for ch in seg.text)
            for seg in result.segments
            if seg.source_language == "te-IN"
        )
        assert not telugu_chars_in_translated_segments

    def test_translation_calls_gemini_exactly_once_for_short_input(
        self, mixed_transcript, mock_gemini_model_telugu_translated
    ):
        with patch("ingestion.translation.build_gemini_model", return_value=mock_gemini_model_telugu_translated):
            translate(mixed_transcript)
        # 13-word input fits well under the chunk size; one Gemini call expected.
        assert mock_gemini_model_telugu_translated.generate_content.call_count == 1


class TestEnglishPassthrough:
    """Verify already-English input is returned unchanged."""

    def test_english_passthrough(self, english_only_transcript, mock_gemini_model_english_passthrough):
        with patch("ingestion.translation.build_gemini_model", return_value=mock_gemini_model_english_passthrough):
            result = translate(english_only_transcript)

        assert "What is dharma" in result.full_text
        assert "righteousness" in result.full_text
        # Original English wording (specifically "Udaya") should still be present.
        joined = " ".join(seg.text for seg in result.segments)
        assert "Udaya" in joined


class TestSanskritTermsPreserved:
    """Verify Sanskrit terms survive translation verbatim."""

    SANSKRIT_TERMS = ["dharma", "karma", "atman", "moksha", "yoga"]

    def test_sanskrit_terms_preserved_when_present(self, mixed_transcript):
        # mixed_transcript has 3 speaker-contiguous runs: speakers [1, 2, 1].
        # The mock must return one output segment per input segment, in order.
        model = MagicMock()
        model.generate_content.return_value = _gemini_response([
            {"speaker": 1, "text": "Let us discuss karma along the path of yoga.", "source_language": "te-IN"},
            {"speaker": 2, "text": "okay Nanna I am ready to learn about moksha and atman.", "source_language": "en-US"},
            {"speaker": 1, "text": "What is dharma?", "source_language": "te-IN"},
        ])
        with patch("ingestion.translation.build_gemini_model", return_value=model):
            result = translate(mixed_transcript)
        joined = " ".join(seg.text for seg in result.segments).lower()
        for term in self.SANSKRIT_TERMS:
            assert term in joined, f"Sanskrit term {term!r} was not preserved"

    def test_prompt_instructs_sanskrit_preservation(self, mixed_transcript, mock_gemini_model_telugu_translated):
        with patch("ingestion.translation.build_gemini_model", return_value=mock_gemini_model_telugu_translated):
            translate(mixed_transcript)
        call_args = mock_gemini_model_telugu_translated.generate_content.call_args
        prompt = call_args.args[0] if call_args.args else call_args.kwargs.get("contents", "")
        prompt_str = str(prompt).lower()
        # The prompt must call out at least one of the canonical Sanskrit terms by name.
        assert any(term in prompt_str for term in ["dharma", "karma", "sanskrit"]), (
            "Prompt does not instruct Gemini to preserve Sanskrit terms"
        )


class TestSpeakerLabelsPreserved:
    """Verify speaker_id attribution survives translation."""

    def test_speaker_labels_preserved(self, mixed_transcript, mock_gemini_model_telugu_translated):
        with patch("ingestion.translation.build_gemini_model", return_value=mock_gemini_model_telugu_translated):
            result = translate(mixed_transcript)
        speaker_ids = {seg.speaker_id for seg in result.segments}
        # Input had Speakers 1 (Nanna) and 2 (Udaya); both must survive.
        assert 1 in speaker_ids
        assert 2 in speaker_ids

    def test_each_speaker_segment_has_integer_id(self, mixed_transcript, mock_gemini_model_telugu_translated):
        with patch("ingestion.translation.build_gemini_model", return_value=mock_gemini_model_telugu_translated):
            result = translate(mixed_transcript)
        for seg in result.segments:
            assert isinstance(seg.speaker_id, int)
            assert seg.speaker_id >= 1

    def test_speaker_order_is_preserved(self, mixed_transcript, mock_gemini_model_telugu_translated):
        # Input order is speaker 1 → 2 → 1; translated output must keep that order.
        with patch("ingestion.translation.build_gemini_model", return_value=mock_gemini_model_telugu_translated):
            result = translate(mixed_transcript)
        speaker_sequence = [seg.speaker_id for seg in result.segments]
        assert speaker_sequence == [1, 2, 1]


class TestFallbackToTranslateApi:
    """Verify the module falls back to Cloud Translation API when Gemini fails."""

    def test_fallback_to_translate_api(self, mixed_transcript):
        # Gemini raises; the module must catch and route to Cloud Translation.
        gemini = MagicMock()
        gemini.generate_content.side_effect = RuntimeError("Gemini API outage")

        translate_client = MagicMock()
        # Cloud Translation returns one TranslateTextResponse per segment input.
        translate_client.translate_text.return_value = MagicMock(
            translations=[
                MagicMock(translated_text="Greetings. Today let us discuss karma."),
            ]
        )

        with patch("ingestion.translation.build_gemini_model", return_value=gemini), \
             patch("ingestion.translation.build_translate_client", return_value=translate_client):
            result = translate(mixed_transcript, enable_fallback=True)

        assert result.used_fallback is True
        assert len(result.segments) > 0
        # Cloud Translation must have been called at least once.
        assert translate_client.translate_text.called

    def test_fallback_disabled_propagates_gemini_error(self, mixed_transcript):
        gemini = MagicMock()
        gemini.generate_content.side_effect = RuntimeError("Gemini API outage")

        with patch("ingestion.translation.build_gemini_model", return_value=gemini):
            with pytest.raises(TranslationError):
                translate(mixed_transcript, enable_fallback=False)


# ---------------------------------------------------------------------------
# Supporting tests — segmentation, timing, chunking, error paths
# ---------------------------------------------------------------------------

class TestSegmentation:
    """Verify the module correctly groups words into speaker-contiguous segments."""

    def test_segment_time_bounds_match_first_and_last_word(
        self, mixed_transcript, mock_gemini_model_telugu_translated
    ):
        with patch("ingestion.translation.build_gemini_model", return_value=mock_gemini_model_telugu_translated):
            result = translate(mixed_transcript)
        # First segment in mixed_transcript spans words 0.0s → 3.0s.
        assert result.segments[0].start_time == 0.0
        assert result.segments[0].end_time == 3.0
        # Second segment spans 3.5s → 5.0s.
        assert result.segments[1].start_time == 3.5
        assert result.segments[1].end_time == 5.0

    def test_segment_count_matches_speaker_contiguity(
        self, mixed_transcript, mock_gemini_model_telugu_translated
    ):
        # mixed_transcript: speaker runs of [1, 2, 1] → 3 segments.
        with patch("ingestion.translation.build_gemini_model", return_value=mock_gemini_model_telugu_translated):
            result = translate(mixed_transcript)
        assert len(result.segments) == 3


class TestTranslationResult:
    """Verify the public dataclass shape and invariants."""

    def test_result_carries_video_id(self, mixed_transcript, mock_gemini_model_telugu_translated):
        with patch("ingestion.translation.build_gemini_model", return_value=mock_gemini_model_telugu_translated):
            result = translate(mixed_transcript)
        assert result.video_id == VIDEO_ID

    def test_used_fallback_false_when_gemini_succeeds(
        self, mixed_transcript, mock_gemini_model_telugu_translated
    ):
        with patch("ingestion.translation.build_gemini_model", return_value=mock_gemini_model_telugu_translated):
            result = translate(mixed_transcript)
        assert result.used_fallback is False

    def test_full_text_joins_all_segments(self, mixed_transcript, mock_gemini_model_telugu_translated):
        with patch("ingestion.translation.build_gemini_model", return_value=mock_gemini_model_telugu_translated):
            result = translate(mixed_transcript)
        for seg in result.segments:
            assert seg.text in result.full_text


class TestErrorHandling:
    """Verify the module raises TranslationError on malformed input or unparseable output."""

    def test_rejects_empty_transcription(self):
        empty = TranscriptionResult(
            video_id="empty",
            words=[],
            full_text="",
            speaker_count=0,
            audio_uri="gs://b/empty/audio.flac",
            output_uri="gs://b/empty/transcript/",
        )
        with pytest.raises(TranslationError, match="empty"):
            translate(empty)

    def test_raises_on_unparseable_gemini_response(self, mixed_transcript):
        gemini = MagicMock()
        bad = MagicMock()
        bad.text = "not valid json at all {"
        gemini.generate_content.return_value = bad
        with patch("ingestion.translation.build_gemini_model", return_value=gemini):
            with pytest.raises(TranslationError):
                translate(mixed_transcript, enable_fallback=False)
