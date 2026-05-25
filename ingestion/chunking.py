"""
Chunking, embedding, and Pinecone upsert module for the Gita Agent.

Takes a TranslationResult (English-with-Sanskrit segments carrying speaker
IDs and time bounds), splits it into ~500-token chunks at sentence
boundaries with ~50-token overlap, computes 768-dim embeddings via
text-embedding-004, and upserts the result to Pinecone with the per-chunk
metadata defined in the design doc.

Design reference: docs/detailed_technical_design.md § 3.6

Usage:
    from ingestion.translation import translate
    from ingestion.chunking import chunk_and_embed

    translated = translate(transcription)
    result = chunk_and_embed(
        translated,
        video_title="Nanna / Udaya - 2025/07/06 ...",
        session_date="2025-07-06",
    )
    print(f"Upserted {result.total_vectors_upserted} vectors to Pinecone")
"""

import os
import re
from dataclasses import dataclass, field
from typing import Optional

import structlog

from ingestion.observability import get_tracer
from ingestion.translation import TranslationResult

logger = structlog.get_logger(__name__)

DEFAULT_CHUNK_SIZE_WORDS = 375  # ~500 tokens (per design doc § 3.6)
DEFAULT_OVERLAP_WORDS = 38  # ~50 tokens
DEFAULT_EMBEDDING_MODEL = "text-embedding-004"
DEFAULT_EMBEDDING_DIM = 768
DEFAULT_PINECONE_INDEX = "gita-videos"
PINECONE_BATCH_SIZE = 100

SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[.!?])\s+")


class ChunkingError(Exception):
    """Raised when chunking fails or receives malformed input."""


@dataclass
class Chunk:
    """A retrieval-ready chunk of translated transcript with timing + speaker provenance."""

    chunk_id: str
    video_id: str
    chunk_index: int
    text: str
    start_time: float
    end_time: float
    speaker_ids: list[int]
    source_language: Optional[str]
    metadata: dict
    embedding: Optional[list[float]] = None


@dataclass
class ChunkingResult:
    """Output of the chunk → embed → upsert pipeline."""

    video_id: str
    chunks: list[Chunk]
    total_vectors_upserted: int


# ---------------------------------------------------------------------------
# Patchable seams — tests replace these to avoid real API calls.
# ---------------------------------------------------------------------------

def embed_text(text: str, model: str = DEFAULT_EMBEDDING_MODEL) -> list[float]:
    """Embed text via text-embedding-004. Patched in unit tests."""
    import google.generativeai as genai
    api_key = os.environ.get("GOOGLE_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
    response = genai.embed_content(model=f"models/{model}", content=text)
    return list(response["embedding"])


def build_pinecone_index(name: str):
    """Build a Pinecone Index client. Patched in unit tests."""
    from pinecone import Pinecone
    api_key = os.environ.get("PINECONE_API_KEY")
    if not api_key:
        raise ChunkingError("PINECONE_API_KEY is not set")
    pc = Pinecone(api_key=api_key)
    return pc.Index(name)


# ---------------------------------------------------------------------------
# Sentence-level intermediate representation
# ---------------------------------------------------------------------------

@dataclass
class _Sentence:
    """A single sentence with its parent segment's speaker_id, time bounds, and language."""

    text: str
    speaker_id: int
    start_time: float
    end_time: float
    source_language: Optional[str]
    word_count: int = field(init=False)

    def __post_init__(self):
        self.word_count = len(self.text.split())


def _split_segment_into_sentences(segment_text: str) -> list[str]:
    """Regex-split on sentence terminators, dropping empties."""
    pieces = SENTENCE_BOUNDARY_RE.split(segment_text.strip())
    return [p.strip() for p in pieces if p.strip()]


def _segments_to_sentences(translation: TranslationResult) -> list[_Sentence]:
    """Flatten the translation's segments into a sentence stream, inheriting per-segment metadata."""
    sentences: list[_Sentence] = []
    for seg in translation.segments:
        pieces = _split_segment_into_sentences(seg.text)
        if not pieces:
            continue
        # All sentences in a segment share the segment's speaker, language, and time bounds.
        # (Word-level time alignment doesn't survive translation; segment bounds are the finest grain.)
        for piece in pieces:
            sentences.append(
                _Sentence(
                    text=piece,
                    speaker_id=seg.speaker_id,
                    start_time=seg.start_time,
                    end_time=seg.end_time,
                    source_language=seg.source_language,
                )
            )
    return sentences


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def _build_chunk(
    sentences: list[_Sentence],
    chunk_index: int,
    video_id: str,
    video_title: str,
    session_date: str,
) -> Chunk:
    text = " ".join(s.text for s in sentences)
    start_time = min(s.start_time for s in sentences)
    end_time = max(s.end_time for s in sentences)
    speaker_ids = sorted({s.speaker_id for s in sentences})
    # Source language: majority across the chunk.
    langs = [s.source_language for s in sentences if s.source_language]
    source_language = max(set(langs), key=langs.count) if langs else None
    metadata = {
        "video_id": video_id,
        "video_title": video_title,
        "chunk_index": chunk_index,
        "start_time_seconds": start_time,
        "end_time_seconds": end_time,
        "speakers": [f"Speaker {sid}" for sid in speaker_ids],
        "source_language": source_language,
        "session_date": session_date,
        "text": text,  # Pinecone metadata includes text for retrieval display
    }
    return Chunk(
        chunk_id=f"{video_id}_chunk_{chunk_index}",
        video_id=video_id,
        chunk_index=chunk_index,
        text=text,
        start_time=start_time,
        end_time=end_time,
        speaker_ids=speaker_ids,
        source_language=source_language,
        metadata=metadata,
    )


def _select_overlap_sentences(
    chunk_sentences: list[_Sentence], overlap_words: int
) -> list[_Sentence]:
    """Pick the tail sentences whose combined word count ~ overlap_words."""
    selected: list[_Sentence] = []
    total = 0
    for s in reversed(chunk_sentences):
        if total >= overlap_words:
            break
        selected.append(s)
        total += s.word_count
    return list(reversed(selected))


def split_into_chunks(
    translation: TranslationResult,
    *,
    video_title: str,
    session_date: str,
    chunk_size_words: int = DEFAULT_CHUNK_SIZE_WORDS,
    overlap_words: int = DEFAULT_OVERLAP_WORDS,
) -> list[Chunk]:
    """Split a translation into size-bounded, sentence-aligned, overlapping chunks."""
    if not translation.segments or not translation.full_text.strip():
        raise ChunkingError("Cannot chunk an empty translation")

    tracer = get_tracer(__name__)
    with tracer.start_as_current_span("chunking.split_into_chunks") as span:
        span.set_attribute("video_id", translation.video_id)
        span.set_attribute("chunk_size_words", chunk_size_words)
        span.set_attribute("overlap_words", overlap_words)

        sentences = _segments_to_sentences(translation)
        if not sentences:
            raise ChunkingError("Translation produced no parseable sentences")

        chunks: list[Chunk] = []
        current: list[_Sentence] = []
        current_word_count = 0
        chunk_index = 0

        for s in sentences:
            # Adding this sentence would exceed the budget AND we already have content → flush.
            if current and (current_word_count + s.word_count) > chunk_size_words:
                chunks.append(
                    _build_chunk(current, chunk_index, translation.video_id, video_title, session_date)
                )
                chunk_index += 1
                # Seed the next chunk with overlap from the flushed one.
                overlap = _select_overlap_sentences(current, overlap_words)
                current = list(overlap)
                current_word_count = sum(o.word_count for o in current)
            current.append(s)
            current_word_count += s.word_count

        if current:
            chunks.append(
                _build_chunk(current, chunk_index, translation.video_id, video_title, session_date)
            )

        avg_chars = (sum(len(c.text) for c in chunks) / len(chunks)) if chunks else 0
        span.set_attribute("sentence_count", len(sentences))
        span.set_attribute("chunk_count", len(chunks))
        span.set_attribute("avg_chunk_chars", avg_chars)

        logger.info(
            "chunking.split_complete",
            video_id=translation.video_id,
            chunk_count=len(chunks),
            sentence_count=len(sentences),
        )
        return chunks


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------

def embed_chunks(chunks: list[Chunk], model: str = DEFAULT_EMBEDDING_MODEL) -> list[Chunk]:
    """Compute an embedding for each chunk and attach it in place."""
    tracer = get_tracer(__name__)
    with tracer.start_as_current_span("embedding.embed_chunks") as span:
        span.set_attribute("chunk_count", len(chunks))
        span.set_attribute("model", model)

        for c in chunks:
            c.embedding = embed_text(c.text, model=model)
            if len(c.embedding) != DEFAULT_EMBEDDING_DIM:
                raise ChunkingError(
                    f"Embedding for {c.chunk_id} has {len(c.embedding)} dims, expected {DEFAULT_EMBEDDING_DIM}"
                )

        span.set_attribute("vector_count", len(chunks))
        logger.info("chunking.embed_complete", chunk_count=len(chunks), model=model)
        return chunks


# ---------------------------------------------------------------------------
# Pinecone upsert
# ---------------------------------------------------------------------------

def upsert_chunks(chunks: list[Chunk], index_name: str = DEFAULT_PINECONE_INDEX) -> int:
    """Upsert embedded chunks to Pinecone in batches, return the count upserted."""
    if not chunks:
        return 0
    for c in chunks:
        if c.embedding is None:
            raise ChunkingError(f"Chunk {c.chunk_id} has no embedding; call embed_chunks first")

    tracer = get_tracer(__name__)
    with tracer.start_as_current_span("storage.upsert_pinecone") as span:
        span.set_attribute("index_name", index_name)
        span.set_attribute("vector_count", len(chunks))

        index = build_pinecone_index(index_name)
        upserted = 0
        batch_count = 0
        for batch_start in range(0, len(chunks), PINECONE_BATCH_SIZE):
            batch = chunks[batch_start : batch_start + PINECONE_BATCH_SIZE]
            vectors = [
                {"id": c.chunk_id, "values": c.embedding, "metadata": c.metadata}
                for c in batch
            ]
            index.upsert(vectors=vectors)
            upserted += len(batch)
            batch_count += 1

        span.set_attribute("batch_count", batch_count)
        logger.info("chunking.upsert_complete", count=upserted, index=index_name)
        return upserted


# ---------------------------------------------------------------------------
# Public orchestrator
# ---------------------------------------------------------------------------

def chunk_and_embed(
    translation: TranslationResult,
    *,
    video_title: str,
    session_date: str,
    chunk_size_words: int = DEFAULT_CHUNK_SIZE_WORDS,
    overlap_words: int = DEFAULT_OVERLAP_WORDS,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    upsert: bool = True,
    index_name: str = DEFAULT_PINECONE_INDEX,
) -> ChunkingResult:
    """Run the full chunk → embed → (optionally) upsert pipeline.

    Args:
        translation: Output of `ingestion.translation.translate()`.
        video_title: Original Drive filename for metadata.
        session_date: ISO date string for metadata (e.g., "2025-07-06").
        chunk_size_words: Soft cap on chunk size in words (~tokens × 0.75).
        overlap_words: Target overlap between adjacent chunks, in words.
        embedding_model: text-embedding model name.
        upsert: If False, return chunks with embeddings but skip Pinecone.
        index_name: Pinecone index to upsert into.

    Returns:
        ChunkingResult with the embedded chunks and upserted count.
    """
    chunks = split_into_chunks(
        translation,
        chunk_size_words=chunk_size_words,
        overlap_words=overlap_words,
        video_title=video_title,
        session_date=session_date,
    )
    chunks = embed_chunks(chunks, model=embedding_model)
    upserted = upsert_chunks(chunks, index_name=index_name) if upsert else 0
    return ChunkingResult(
        video_id=translation.video_id,
        chunks=chunks,
        total_vectors_upserted=upserted,
    )
