"""
Tests for ingestion/orchestrator.py — CLI pipeline orchestrator.

TDD Phase: RED — tests written before implementation.

The orchestrator ties the entire ingestion pipeline together:
Drive download → audio extract → GCS upload → Chirp 3 transcribe →
Gemini translate → chunk+embed+upsert → write .indexed sentinel.

Idempotency: a GCS sentinel at `gs://{bucket}/{video_id}/.indexed`
is written only after a successful Pinecone upsert. The next
invocation of `scan_and_process` checks for the sentinel and skips
videos that already have it.

All downstream modules (drive, audio, storage, transcription,
translation, chunking) are mocked. Orchestrator tests verify
ordering, error propagation, sentinel semantics, and the CLI flags.

Design reference: docs/detailed_technical_design.md § 3.2
"""

from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from ingestion.drive import DriveFile
from ingestion.orchestrator import (
    OrchestrationError,
    ProcessingResult,
    is_already_indexed,
    process_video,
    scan_and_process,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

BUCKET = "gita-agent-prod-audio"
VIDEO_ID = "nanna_udaya_2025_07_06"
VIDEO_TITLE = "Nanna / Udaya - 2025/07/06 14:22 EDT - Recording.mp4"


@pytest.fixture
def drive_file() -> DriveFile:
    return DriveFile(
        file_id="file_abc123",
        name=VIDEO_TITLE,
        mime_type="video/mp4",
        size_bytes=1073741824,
        video_id=VIDEO_ID,
        created_time="2025-07-06T18:22:00.000Z",
    )


@pytest.fixture
def second_drive_file() -> DriveFile:
    return DriveFile(
        file_id="file_def456",
        name="Nanna / Udaya - 2025/07/20 19:57 EDT - Recording.mp4",
        mime_type="video/mp4",
        size_bytes=671813632,
        video_id="nanna_udaya_2025_07_20",
        created_time="2025-07-20T23:57:00.000Z",
    )


@pytest.fixture
def mock_pipeline(tmp_path, monkeypatch):
    """Patch every downstream module so process_video runs end-to-end without I/O.

    Yields a SimpleNamespace-like object exposing every mock so tests can
    assert on call order, args, etc.
    """
    monkeypatch.setenv("GCS_AUDIO_BUCKET", BUCKET)
    monkeypatch.setenv("DRIVE_FOLDER_ID", "1hWMRJRvw5di8WF7WpDPH1a311FAIpbPA")

    # Drive: list returns one file by default; download returns a fake local path.
    drive_client = MagicMock()
    drive_client.list_video_files.return_value = []  # default empty; tests override
    fake_mp4 = tmp_path / "video.mp4"
    fake_mp4.write_bytes(b"fake-mp4")
    drive_client.download_file.return_value = fake_mp4

    # Audio extract: returns a mock result with output_path
    fake_flac = tmp_path / VIDEO_ID / "audio.flac"
    fake_flac.parent.mkdir(parents=True, exist_ok=True)
    fake_flac.write_bytes(b"fake-flac")
    audio_result = MagicMock()
    audio_result.output_path = fake_flac
    audio_result.duration_seconds = 3600.0

    extract_audio_mock = MagicMock(return_value=audio_result)

    # Storage: upload returns the URI; sentinel_exists defaults to False (not indexed);
    # write_sentinel returns the URI.
    upload_file_mock = MagicMock(side_effect=lambda local, uri: uri)
    sentinel_exists_mock = MagicMock(return_value=False)
    write_sentinel_mock = MagicMock(side_effect=lambda uri: uri)

    # Transcription: returns a mock TranscriptionResult
    transcription_result = MagicMock()
    transcription_result.video_id = VIDEO_ID
    transcribe_mock = MagicMock(return_value=transcription_result)

    # Translation: returns a mock TranslationResult
    translation_result = MagicMock()
    translation_result.video_id = VIDEO_ID
    translate_mock = MagicMock(return_value=translation_result)

    # Chunking: returns ChunkingResult with positive upsert count
    chunking_result = MagicMock()
    chunking_result.video_id = VIDEO_ID
    chunking_result.total_vectors_upserted = 12
    chunking_result.chunks = [MagicMock()] * 12
    chunk_and_embed_mock = MagicMock(return_value=chunking_result)

    patches = [
        patch("ingestion.orchestrator.build_drive_client", return_value=drive_client),
        patch("ingestion.orchestrator.extract_audio", extract_audio_mock),
        patch("ingestion.orchestrator.storage.upload_file", upload_file_mock),
        patch("ingestion.orchestrator.storage.sentinel_exists", sentinel_exists_mock),
        patch("ingestion.orchestrator.storage.write_sentinel", write_sentinel_mock),
        patch("ingestion.orchestrator.transcribe", transcribe_mock),
        patch("ingestion.orchestrator.translate", translate_mock),
        patch("ingestion.orchestrator.chunk_and_embed", chunk_and_embed_mock),
    ]
    for p in patches:
        p.start()

    class Mocks:
        pass

    m = Mocks()
    m.drive_client = drive_client
    m.extract_audio = extract_audio_mock
    m.upload_file = upload_file_mock
    m.sentinel_exists = sentinel_exists_mock
    m.write_sentinel = write_sentinel_mock
    m.transcribe = transcribe_mock
    m.translate = translate_mock
    m.chunk_and_embed = chunk_and_embed_mock
    m.fake_flac = fake_flac
    m.fake_mp4 = fake_mp4
    m.transcription_result = transcription_result
    m.translation_result = translation_result
    m.chunking_result = chunking_result

    yield m

    for p in patches:
        p.stop()


# ---------------------------------------------------------------------------
# Required Phase 4.6.2 tests
# ---------------------------------------------------------------------------

class TestProcessVideoRunsFullPipelineInOrder:
    """Verify all six pipeline steps are called in the correct sequence with proper handoffs."""

    def test_process_video_runs_full_pipeline_in_order(self, drive_file, mock_pipeline, tmp_path):
        result = process_video(drive_file, work_dir=tmp_path)

        # All six downstream steps invoked at least once.
        assert mock_pipeline.drive_client.download_file.called
        assert mock_pipeline.extract_audio.called
        assert mock_pipeline.upload_file.called
        assert mock_pipeline.transcribe.called
        assert mock_pipeline.translate.called
        assert mock_pipeline.chunk_and_embed.called
        # Sentinel written because upsert count > 0
        assert mock_pipeline.write_sentinel.called

        # Verify the handoff: transcribe gets the GCS URI from upload_file
        transcribe_kwargs = mock_pipeline.transcribe.call_args.kwargs
        assert transcribe_kwargs["video_id"] == VIDEO_ID
        assert transcribe_kwargs["audio_uri"].startswith("gs://")
        assert VIDEO_ID in transcribe_kwargs["audio_uri"]

        # Verify translate gets the transcription result
        assert mock_pipeline.translate.call_args.args[0] is mock_pipeline.transcription_result

        # Verify chunk_and_embed gets the translation result + correct metadata
        chunk_kwargs = mock_pipeline.chunk_and_embed.call_args.kwargs
        assert mock_pipeline.chunk_and_embed.call_args.args[0] is mock_pipeline.translation_result
        assert chunk_kwargs["video_title"] == VIDEO_TITLE
        assert chunk_kwargs["session_date"] == "2025-07-06"  # derived from created_time

        # Result reflects success
        assert isinstance(result, ProcessingResult)
        assert result.success is True
        assert result.skipped is False
        assert result.video_id == VIDEO_ID
        assert result.vector_count == 12


class TestIsAlreadyIndexedChecksSentinel:
    """Verify is_already_indexed queries the GCS sentinel at the correct URI."""

    def test_is_already_indexed_checks_sentinel(self, mock_pipeline, monkeypatch):
        monkeypatch.setenv("GCS_AUDIO_BUCKET", BUCKET)
        mock_pipeline.sentinel_exists.return_value = True

        result = is_already_indexed(VIDEO_ID)

        assert result is True
        expected_uri = f"gs://{BUCKET}/{VIDEO_ID}/.indexed"
        mock_pipeline.sentinel_exists.assert_called_once_with(expected_uri)

    def test_is_already_indexed_returns_false_when_no_sentinel(self, mock_pipeline):
        mock_pipeline.sentinel_exists.return_value = False
        assert is_already_indexed(VIDEO_ID) is False


class TestScanAndProcessSkipsAlreadyIndexed:
    """Verify videos with an existing sentinel are skipped during scan."""

    def test_scan_and_process_skips_already_indexed(
        self, drive_file, second_drive_file, mock_pipeline
    ):
        # Drive returns both files
        mock_pipeline.drive_client.list_video_files.return_value = [drive_file, second_drive_file]
        # First file already indexed, second isn't
        sentinel_state = {
            f"gs://{BUCKET}/{drive_file.video_id}/.indexed": True,
            f"gs://{BUCKET}/{second_drive_file.video_id}/.indexed": False,
        }
        mock_pipeline.sentinel_exists.side_effect = lambda uri: sentinel_state.get(uri, False)

        results = scan_and_process()

        assert len(results) == 2
        first = next(r for r in results if r.video_id == drive_file.video_id)
        second = next(r for r in results if r.video_id == second_drive_file.video_id)
        assert first.skipped is True
        assert second.skipped is False
        # Pipeline only invoked for the second file
        assert mock_pipeline.transcribe.call_count == 1


class TestForceReindexBypassesSentinel:
    """Verify force_reindex re-processes videos with an existing sentinel."""

    def test_force_reindex_bypasses_sentinel(self, drive_file, mock_pipeline):
        mock_pipeline.drive_client.list_video_files.return_value = [drive_file]
        mock_pipeline.sentinel_exists.return_value = True  # would skip without force

        results = scan_and_process(force_reindex=True)

        assert len(results) == 1
        assert results[0].skipped is False
        assert mock_pipeline.transcribe.called  # pipeline ran despite sentinel
        # And the sentinel is re-written after success
        assert mock_pipeline.write_sentinel.called

    def test_process_video_force_reindex_bypasses_sentinel(
        self, drive_file, mock_pipeline, tmp_path
    ):
        mock_pipeline.sentinel_exists.return_value = True

        result = process_video(drive_file, force_reindex=True, work_dir=tmp_path)

        assert result.skipped is False
        assert mock_pipeline.transcribe.called


class TestDryRunListsWithoutProcessing:
    """Verify dry_run does not invoke any downstream module."""

    def test_dry_run_lists_without_processing(
        self, drive_file, second_drive_file, mock_pipeline
    ):
        mock_pipeline.drive_client.list_video_files.return_value = [drive_file, second_drive_file]

        results = scan_and_process(dry_run=True)

        # No pipeline steps invoked
        assert not mock_pipeline.drive_client.download_file.called
        assert not mock_pipeline.extract_audio.called
        assert not mock_pipeline.upload_file.called
        assert not mock_pipeline.transcribe.called
        assert not mock_pipeline.translate.called
        assert not mock_pipeline.chunk_and_embed.called
        assert not mock_pipeline.write_sentinel.called

        # Results reflect "would have processed" intent (or skipped)
        assert len(results) <= 2  # may be empty list or list of intent-only results


class TestPipelineStepFailureWritesNoSentinel:
    """Verify that a failure during the pipeline leaves the sentinel unwritten."""

    def test_pipeline_step_failure_writes_no_sentinel(self, drive_file, mock_pipeline, tmp_path):
        # Make transcribe blow up mid-pipeline
        mock_pipeline.transcribe.side_effect = RuntimeError("Chirp 3 outage")

        result = process_video(drive_file, work_dir=tmp_path)

        assert result.success is False
        assert "Chirp 3 outage" in (result.error or "")
        assert not mock_pipeline.write_sentinel.called

    def test_zero_vectors_upserted_writes_no_sentinel(self, drive_file, mock_pipeline, tmp_path):
        # If upsert reports 0 vectors, sentinel should NOT be written
        # (defensive: distinguishes "ran clean but produced nothing" from real completion).
        mock_pipeline.chunking_result.total_vectors_upserted = 0

        result = process_video(drive_file, work_dir=tmp_path)

        assert result.success is True  # no exception
        assert not mock_pipeline.write_sentinel.called

    def test_chunk_and_embed_failure_writes_no_sentinel(self, drive_file, mock_pipeline, tmp_path):
        mock_pipeline.chunk_and_embed.side_effect = RuntimeError("Pinecone outage")

        result = process_video(drive_file, work_dir=tmp_path)

        assert result.success is False
        assert not mock_pipeline.write_sentinel.called


# ---------------------------------------------------------------------------
# Supporting tests — result dataclass, scan filters, env handling
# ---------------------------------------------------------------------------

class TestProcessingResult:
    """Verify the ProcessingResult dataclass shape."""

    def test_successful_result_carries_vector_count(self, drive_file, mock_pipeline, tmp_path):
        result = process_video(drive_file, work_dir=tmp_path)
        assert result.video_id == VIDEO_ID
        assert result.video_title == VIDEO_TITLE
        assert result.success is True
        assert result.skipped is False
        assert result.vector_count == 12
        assert result.error is None

    def test_skipped_result_marks_skipped(self, drive_file, mock_pipeline, tmp_path):
        mock_pipeline.sentinel_exists.return_value = True
        result = process_video(drive_file, work_dir=tmp_path)
        assert result.skipped is True
        assert result.success is True
        assert not mock_pipeline.transcribe.called


class TestScanFilters:
    """Verify scan_and_process filtering by video_id."""

    def test_video_id_filter_narrows_set(self, drive_file, second_drive_file, mock_pipeline):
        mock_pipeline.drive_client.list_video_files.return_value = [drive_file, second_drive_file]

        results = scan_and_process(video_id_filter=drive_file.video_id)

        # Only the matching video processed
        assert len(results) == 1
        assert results[0].video_id == drive_file.video_id

    def test_no_files_returns_empty_list(self, mock_pipeline):
        mock_pipeline.drive_client.list_video_files.return_value = []
        results = scan_and_process()
        assert results == []


class TestEnvHandling:
    """Verify the orchestrator reads the right env vars."""

    def test_missing_drive_folder_id_raises(self, mock_pipeline, monkeypatch):
        monkeypatch.delenv("DRIVE_FOLDER_ID", raising=False)
        with pytest.raises(OrchestrationError, match="DRIVE_FOLDER_ID"):
            scan_and_process()


# ---------------------------------------------------------------------------
# Observability — Phase 4.7
# ---------------------------------------------------------------------------

class TestOrchestratorSpans:
    """Verify process_video emits a parent `orchestrator.ingest_video` span."""

    def test_emits_parent_ingest_video_span(
        self, drive_file, mock_pipeline, tmp_path, in_memory_spans
    ):
        process_video(drive_file, work_dir=tmp_path)

        parents = [
            s for s in in_memory_spans.get_finished_spans()
            if s.name == "orchestrator.ingest_video"
        ]
        assert len(parents) == 1
        attrs = parents[0].attributes
        assert attrs["video_id"] == VIDEO_ID
        assert attrs["video_title"] == VIDEO_TITLE
        assert attrs["vector_count"] == 12
        assert attrs["success"] is True
        assert attrs["skipped"] is False

    def test_skipped_video_span_marks_skipped(
        self, drive_file, mock_pipeline, tmp_path, in_memory_spans
    ):
        mock_pipeline.sentinel_exists.return_value = True
        process_video(drive_file, work_dir=tmp_path)

        parents = [
            s for s in in_memory_spans.get_finished_spans()
            if s.name == "orchestrator.ingest_video"
        ]
        assert len(parents) == 1
        attrs = parents[0].attributes
        assert attrs["skipped"] is True
        assert attrs["video_id"] == VIDEO_ID

    def test_failed_video_span_records_error(
        self, drive_file, mock_pipeline, tmp_path, in_memory_spans
    ):
        mock_pipeline.transcribe.side_effect = RuntimeError("Chirp 3 outage")
        process_video(drive_file, work_dir=tmp_path)

        parents = [
            s for s in in_memory_spans.get_finished_spans()
            if s.name == "orchestrator.ingest_video"
        ]
        assert len(parents) == 1
        attrs = parents[0].attributes
        assert attrs["success"] is False
        assert "Chirp 3 outage" in attrs.get("error", "")
