"""
Tests for ingestion/chunking.py — text splitter, embedder, and Pinecone upserter.

TDD Phase: RED — tests written before implementation.

The chunking module takes a TranslationResult (English-with-Sanskrit segments
carrying speaker IDs and time bounds), splits it into ~500-token chunks at
sentence boundaries with ~50-token overlap, computes 768-dim embeddings via
text-embedding-004, and upserts the result to Pinecone with metadata.

Design reference: docs/detailed_technical_design.md § 3.6

All embedding API calls and Pinecone operations are mocked — no real network
or billed calls in unit tests.
"""

from unittest.mock import MagicMock, patch

import pytest

from ingestion.translation import TranslatedSegment, TranslationResult
from ingestion.chunking import (
    Chunk,
    ChunkingError,
    ChunkingResult,
    chunk_and_embed,
    embed_chunks,
    split_into_chunks,
    upsert_chunks,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VIDEO_ID = "nanna_udaya_2025_07_06"
VIDEO_TITLE = "Nanna / Udaya - 2025/07/06 14:22 EDT - Recording"
SESSION_DATE = "2025-07-06"

# Realistic chunking parameters for the test fixtures below.
CHUNK_SIZE_WORDS = 50  # smaller than prod (375) so test transcripts can produce multiple chunks
OVERLAP_WORDS = 10
EMBEDDING_DIM = 768


def _make_segment(text: str, speaker: int, start: float, end: float, lang: str = "te-IN") -> TranslatedSegment:
    return TranslatedSegment(
        text=text, speaker_id=speaker, start_time=start, end_time=end, source_language=lang,
    )


@pytest.fixture
def long_translation() -> TranslationResult:
    """A multi-segment translation long enough to force several chunks at CHUNK_SIZE_WORDS=50."""
    # Roughly 220 words of sentence-rich English with mixed speakers.
    segments = [
        _make_segment(
            "Greetings Udaya. Today we will discuss the concept of dharma. "
            "Dharma is one of the most fundamental ideas in the Bhagavad Gita. "
            "It refers to one's duty in life, the righteous path one must follow. "
            "Krishna explains this to Arjuna on the battlefield of Kurukshetra.",
            speaker=1, start=0.0, end=20.0, lang="te-IN",
        ),
        _make_segment(
            "Yes Nanna, I have read Chapter Two. Arjuna is confused about his duty as a warrior. "
            "He does not want to fight against his own family. What does Krishna tell him?",
            speaker=2, start=20.5, end=35.0, lang="en-US",
        ),
        _make_segment(
            "Krishna tells him that his dharma as a kshatriya is to fight a righteous war. "
            "He explains the concept of karma yoga, the path of selfless action. "
            "Act without attachment to the fruits of your actions. "
            "This is the essence of the second chapter. "
            "Krishna also introduces the idea of the eternal atman, the soul that never dies.",
            speaker=1, start=35.5, end=60.0, lang="te-IN",
        ),
        _make_segment(
            "What about moksha Nanna? When does Krishna talk about liberation?",
            speaker=2, start=60.5, end=68.0, lang="en-US",
        ),
        _make_segment(
            "Moksha is discussed throughout the Gita but most clearly in the later chapters. "
            "It is the ultimate goal, freedom from the cycle of samsara. "
            "Through devotion or bhakti, through knowledge or jnana, and through action or karma yoga, "
            "one can attain moksha. The Gita teaches that all paths lead to the same truth.",
            speaker=1, start=68.5, end=92.0, lang="te-IN",
        ),
    ]
    full_text = " ".join(s.text for s in segments)
    return TranslationResult(
        video_id=VIDEO_ID,
        segments=segments,
        full_text=full_text,
        used_fallback=False,
    )


@pytest.fixture
def short_translation() -> TranslationResult:
    segments = [
        _make_segment("Hello. This is short. Just three sentences.", speaker=1, start=0.0, end=3.0, lang="en-US"),
    ]
    return TranslationResult(
        video_id="short_video",
        segments=segments,
        full_text=segments[0].text,
        used_fallback=False,
    )


def _mock_embedding(dim: int = EMBEDDING_DIM) -> list[float]:
    return [0.01] * dim


@pytest.fixture
def mock_embed_fn():
    """Patchable embedder that returns a fixed 768-dim vector per call."""
    return MagicMock(return_value=_mock_embedding())


@pytest.fixture
def mock_pinecone_index():
    """Patchable Pinecone Index with a no-op upsert that records calls."""
    index = MagicMock()
    index.upsert.return_value = MagicMock(upserted_count=0)
    return index


# ---------------------------------------------------------------------------
# Required Phase 4.5 tests
# ---------------------------------------------------------------------------

class TestChunkSizeWithinLimit:
    """Verify no chunk exceeds the configured size budget."""

    def test_chunk_size_within_limit(self, long_translation):
        chunks = split_into_chunks(
            long_translation,
            chunk_size_words=CHUNK_SIZE_WORDS,
            overlap_words=OVERLAP_WORDS,
            video_title=VIDEO_TITLE,
            session_date=SESSION_DATE,
        )
        # Tolerate up to one sentence of overshoot (sentences are atomic).
        for c in chunks:
            word_count = len(c.text.split())
            assert word_count <= CHUNK_SIZE_WORDS * 1.3, (
                f"Chunk {c.chunk_index} has {word_count} words, exceeds soft limit"
            )

    def test_multiple_chunks_produced_when_text_is_long(self, long_translation):
        chunks = split_into_chunks(
            long_translation,
            chunk_size_words=CHUNK_SIZE_WORDS,
            overlap_words=OVERLAP_WORDS,
            video_title=VIDEO_TITLE,
            session_date=SESSION_DATE,
        )
        assert len(chunks) >= 3, f"Expected multiple chunks from ~220 words / 50-word budget; got {len(chunks)}"


class TestChunkOverlap:
    """Verify adjacent chunks share overlap text."""

    def test_chunk_overlap(self, long_translation):
        chunks = split_into_chunks(
            long_translation,
            chunk_size_words=CHUNK_SIZE_WORDS,
            overlap_words=OVERLAP_WORDS,
            video_title=VIDEO_TITLE,
            session_date=SESSION_DATE,
        )
        assert len(chunks) >= 2

        for prev, curr in zip(chunks, chunks[1:]):
            prev_words = prev.text.split()
            curr_words = curr.text.split()
            # The last `OVERLAP_WORDS` words of prev should appear in the first half of curr.
            tail = prev_words[-OVERLAP_WORDS:]
            head_search_space = " ".join(curr_words[: OVERLAP_WORDS * 3])
            tail_substr = " ".join(tail)
            assert tail_substr in head_search_space, (
                f"Overlap missing between chunk {prev.chunk_index} and {curr.chunk_index}"
            )

    def test_overlap_word_count_is_close_to_target(self, long_translation):
        chunks = split_into_chunks(
            long_translation,
            chunk_size_words=CHUNK_SIZE_WORDS,
            overlap_words=OVERLAP_WORDS,
            video_title=VIDEO_TITLE,
            session_date=SESSION_DATE,
        )
        for prev, curr in zip(chunks, chunks[1:]):
            prev_set = set(prev.text.split())
            curr_set = set(curr.text.split())
            shared = prev_set & curr_set
            # Allow generous tolerance: shared words ≥ OVERLAP_WORDS / 2 (sentence-boundary rounding).
            assert len(shared) >= OVERLAP_WORDS // 2


class TestChunkSplitsOnSentenceBoundary:
    """Verify chunks end at sentence boundaries (don't split mid-sentence)."""

    def test_chunk_splits_on_sentence_boundary(self, long_translation):
        chunks = split_into_chunks(
            long_translation,
            chunk_size_words=CHUNK_SIZE_WORDS,
            overlap_words=OVERLAP_WORDS,
            video_title=VIDEO_TITLE,
            session_date=SESSION_DATE,
        )
        for c in chunks:
            stripped = c.text.rstrip()
            assert stripped.endswith((".", "?", "!")), (
                f"Chunk {c.chunk_index} does not end at a sentence boundary: {stripped[-40:]!r}"
            )

    def test_chunk_starts_on_sentence_or_after_overlap(self, long_translation):
        # First chunk should start with a capital letter (start of a sentence).
        chunks = split_into_chunks(
            long_translation,
            chunk_size_words=CHUNK_SIZE_WORDS,
            overlap_words=OVERLAP_WORDS,
            video_title=VIDEO_TITLE,
            session_date=SESSION_DATE,
        )
        first = chunks[0].text.lstrip()
        assert first[:1].isupper() or first[:1].isalpha()


class TestEmbeddingDimension:
    """Verify embeddings are exactly 768-dimensional."""

    def test_embedding_dimension(self, long_translation, mock_embed_fn):
        chunks = split_into_chunks(
            long_translation,
            chunk_size_words=CHUNK_SIZE_WORDS,
            overlap_words=OVERLAP_WORDS,
            video_title=VIDEO_TITLE,
            session_date=SESSION_DATE,
        )
        with patch("ingestion.chunking.embed_text", mock_embed_fn):
            embedded = embed_chunks(chunks)
        for c in embedded:
            assert c.embedding is not None
            assert len(c.embedding) == EMBEDDING_DIM, (
                f"Chunk {c.chunk_index} embedding has {len(c.embedding)} dims, expected {EMBEDDING_DIM}"
            )

    def test_embed_called_once_per_chunk(self, long_translation, mock_embed_fn):
        chunks = split_into_chunks(
            long_translation,
            chunk_size_words=CHUNK_SIZE_WORDS,
            overlap_words=OVERLAP_WORDS,
            video_title=VIDEO_TITLE,
            session_date=SESSION_DATE,
        )
        with patch("ingestion.chunking.embed_text", mock_embed_fn):
            embed_chunks(chunks)
        assert mock_embed_fn.call_count == len(chunks)


class TestMetadataAttachedToChunk:
    """Verify each chunk carries the metadata fields specified in the design doc."""

    REQUIRED_METADATA_KEYS = {
        "video_id",
        "video_title",
        "chunk_index",
        "start_time_seconds",
        "end_time_seconds",
        "speakers",
        "source_language",
        "session_date",
    }

    def test_metadata_attached_to_chunk(self, long_translation):
        chunks = split_into_chunks(
            long_translation,
            chunk_size_words=CHUNK_SIZE_WORDS,
            overlap_words=OVERLAP_WORDS,
            video_title=VIDEO_TITLE,
            session_date=SESSION_DATE,
        )
        for c in chunks:
            missing = self.REQUIRED_METADATA_KEYS - set(c.metadata.keys())
            assert not missing, f"Chunk {c.chunk_index} missing metadata keys: {missing}"
            assert c.metadata["video_id"] == VIDEO_ID
            assert c.metadata["video_title"] == VIDEO_TITLE
            assert c.metadata["session_date"] == SESSION_DATE
            assert c.metadata["chunk_index"] == c.chunk_index
            assert isinstance(c.metadata["start_time_seconds"], (int, float))
            assert isinstance(c.metadata["end_time_seconds"], (int, float))
            assert c.metadata["start_time_seconds"] <= c.metadata["end_time_seconds"]
            assert isinstance(c.metadata["speakers"], list)
            assert len(c.metadata["speakers"]) >= 1

    def test_metadata_speakers_match_chunk_segments(self, long_translation):
        chunks = split_into_chunks(
            long_translation,
            chunk_size_words=CHUNK_SIZE_WORDS,
            overlap_words=OVERLAP_WORDS,
            video_title=VIDEO_TITLE,
            session_date=SESSION_DATE,
        )
        # The combined set of speakers across all chunks must cover both Nanna (1) and Udaya (2).
        all_speakers = set()
        for c in chunks:
            all_speakers.update(c.metadata["speakers"])
        # Speakers stored as labels like "Speaker 1" per design doc.
        assert "Speaker 1" in all_speakers
        assert "Speaker 2" in all_speakers


# ---------------------------------------------------------------------------
# Supporting tests — upsert, orchestrator, error paths
# ---------------------------------------------------------------------------

class TestUpsertChunks:
    """Verify Pinecone upsert is called with the expected payload shape."""

    def test_upsert_passes_all_chunks(self, long_translation, mock_embed_fn, mock_pinecone_index):
        chunks = split_into_chunks(
            long_translation,
            chunk_size_words=CHUNK_SIZE_WORDS,
            overlap_words=OVERLAP_WORDS,
            video_title=VIDEO_TITLE,
            session_date=SESSION_DATE,
        )
        with patch("ingestion.chunking.embed_text", mock_embed_fn):
            embedded = embed_chunks(chunks)
        with patch("ingestion.chunking.build_pinecone_index", return_value=mock_pinecone_index):
            count = upsert_chunks(embedded, index_name="gita-videos")
        assert mock_pinecone_index.upsert.called
        assert count == len(embedded)

    def test_upsert_vector_has_required_fields(self, long_translation, mock_embed_fn, mock_pinecone_index):
        chunks = split_into_chunks(
            long_translation,
            chunk_size_words=CHUNK_SIZE_WORDS,
            overlap_words=OVERLAP_WORDS,
            video_title=VIDEO_TITLE,
            session_date=SESSION_DATE,
        )
        with patch("ingestion.chunking.embed_text", mock_embed_fn):
            embedded = embed_chunks(chunks)
        with patch("ingestion.chunking.build_pinecone_index", return_value=mock_pinecone_index):
            upsert_chunks(embedded, index_name="gita-videos")
        # Inspect the first batch passed to upsert.
        call = mock_pinecone_index.upsert.call_args
        vectors = call.kwargs.get("vectors") or call.args[0]
        first = vectors[0]
        # Pinecone vectors are dicts (or tuples) with id, values, metadata.
        assert "id" in first and "values" in first and "metadata" in first
        assert first["id"].startswith(VIDEO_ID)
        assert len(first["values"]) == EMBEDDING_DIM


class TestChunkAndEmbedOrchestrator:
    """Verify the top-level chunk_and_embed orchestrator."""

    def test_orchestrator_returns_chunking_result(self, long_translation, mock_embed_fn, mock_pinecone_index):
        with patch("ingestion.chunking.embed_text", mock_embed_fn), \
             patch("ingestion.chunking.build_pinecone_index", return_value=mock_pinecone_index):
            result = chunk_and_embed(
                long_translation,
                video_title=VIDEO_TITLE,
                session_date=SESSION_DATE,
                chunk_size_words=CHUNK_SIZE_WORDS,
                overlap_words=OVERLAP_WORDS,
                upsert=True,
            )
        assert isinstance(result, ChunkingResult)
        assert result.video_id == VIDEO_ID
        assert len(result.chunks) >= 1
        assert result.total_vectors_upserted == len(result.chunks)

    def test_orchestrator_skips_upsert_when_disabled(self, long_translation, mock_embed_fn, mock_pinecone_index):
        with patch("ingestion.chunking.embed_text", mock_embed_fn), \
             patch("ingestion.chunking.build_pinecone_index", return_value=mock_pinecone_index):
            result = chunk_and_embed(
                long_translation,
                video_title=VIDEO_TITLE,
                session_date=SESSION_DATE,
                chunk_size_words=CHUNK_SIZE_WORDS,
                overlap_words=OVERLAP_WORDS,
                upsert=False,
            )
        assert not mock_pinecone_index.upsert.called
        assert result.total_vectors_upserted == 0


class TestErrorHandling:
    """Verify the module raises ChunkingError on malformed input."""

    def test_rejects_empty_translation(self):
        empty = TranslationResult(
            video_id="empty", segments=[], full_text="", used_fallback=False,
        )
        with pytest.raises(ChunkingError, match="empty"):
            split_into_chunks(
                empty,
                chunk_size_words=CHUNK_SIZE_WORDS,
                overlap_words=OVERLAP_WORDS,
                video_title=VIDEO_TITLE,
                session_date=SESSION_DATE,
            )

    def test_short_text_produces_single_chunk(self, short_translation):
        chunks = split_into_chunks(
            short_translation,
            chunk_size_words=CHUNK_SIZE_WORDS,
            overlap_words=OVERLAP_WORDS,
            video_title="short title",
            session_date="2025-01-01",
        )
        assert len(chunks) == 1
        assert chunks[0].chunk_index == 0
