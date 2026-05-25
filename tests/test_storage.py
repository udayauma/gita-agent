"""
Tests for ingestion/storage.py — GCS helper module.

TDD Phase: RED — tests written before implementation.

The storage module wraps google-cloud-storage with convenience helpers used
across the ingestion pipeline: upload FLAC files, download Chirp 3 JSON
output, list blobs under a prefix (for resolving Chirp 3's auto-named
output file), delete prefixes (cleanup), and write/check the `.indexed`
sentinel that the orchestrator uses for idempotency.

Design reference: docs/detailed_technical_design.md § 3.2

All google-cloud-storage calls are mocked — no real network in unit tests.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ingestion.storage import (
    StorageError,
    delete_prefix,
    download_json,
    list_blobs,
    sentinel_exists,
    upload_file,
    write_sentinel,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

BUCKET = "gita-agent-prod-audio"


def _make_blob(name: str, content: bytes | None = None) -> MagicMock:
    """Build a mock storage.Blob with optional content."""
    blob = MagicMock()
    blob.name = name
    if content is not None:
        blob.download_as_bytes.return_value = content
    blob.exists.return_value = True
    return blob


@pytest.fixture
def mock_storage_client():
    """Mocked storage.Client with bucket() → MagicMock and list_blobs() → []."""
    client = MagicMock()
    bucket = MagicMock()
    client.bucket.return_value = bucket
    client.list_blobs.return_value = []
    return client


@pytest.fixture
def tmp_local_file(tmp_path: Path) -> Path:
    """A throwaway local file to upload."""
    p = tmp_path / "audio.flac"
    p.write_bytes(b"fake-flac-bytes")
    return p


# ---------------------------------------------------------------------------
# Required Phase 4.6.1 tests
# ---------------------------------------------------------------------------

class TestUploadFile:
    """Verify upload_file writes the local file to the correct GCS URI."""

    def test_upload_file_writes_to_correct_uri(self, mock_storage_client, tmp_local_file):
        target_uri = f"gs://{BUCKET}/nanna_udaya_2025_07_06/audio.flac"
        with patch("ingestion.storage.build_storage_client", return_value=mock_storage_client):
            result = upload_file(tmp_local_file, target_uri)

        assert result == target_uri
        mock_storage_client.bucket.assert_called_once_with(BUCKET)
        mock_storage_client.bucket.return_value.blob.assert_called_once_with(
            "nanna_udaya_2025_07_06/audio.flac"
        )
        blob_mock = mock_storage_client.bucket.return_value.blob.return_value
        blob_mock.upload_from_filename.assert_called_once_with(str(tmp_local_file))

    def test_upload_file_rejects_non_gcs_uri(self, tmp_local_file):
        with pytest.raises(StorageError, match="gs://"):
            upload_file(tmp_local_file, "/local/path/audio.flac")

    def test_upload_file_returns_input_uri(self, mock_storage_client, tmp_local_file):
        uri = f"gs://{BUCKET}/some/key.txt"
        with patch("ingestion.storage.build_storage_client", return_value=mock_storage_client):
            result = upload_file(tmp_local_file, uri)
        assert result == uri


class TestDownloadJson:
    """Verify download_json fetches a GCS blob and returns a parsed dict."""

    def test_download_json_returns_parsed_dict(self, mock_storage_client):
        payload = {"results": [{"alternatives": [{"transcript": "hello"}]}]}
        blob = _make_blob("nanna/transcript.json", content=json.dumps(payload).encode("utf-8"))
        mock_storage_client.bucket.return_value.blob.return_value = blob

        with patch("ingestion.storage.build_storage_client", return_value=mock_storage_client):
            result = download_json(f"gs://{BUCKET}/nanna/transcript.json")

        assert result == payload
        mock_storage_client.bucket.assert_called_once_with(BUCKET)

    def test_download_json_rejects_non_gcs_uri(self):
        with pytest.raises(StorageError, match="gs://"):
            download_json("/local/transcript.json")

    def test_download_json_raises_on_invalid_json(self, mock_storage_client):
        blob = _make_blob("bad.json", content=b"not valid json at all {")
        mock_storage_client.bucket.return_value.blob.return_value = blob
        with patch("ingestion.storage.build_storage_client", return_value=mock_storage_client):
            with pytest.raises(StorageError, match="JSON"):
                download_json(f"gs://{BUCKET}/bad.json")


class TestListBlobs:
    """Verify list_blobs returns all gs:// URIs under a prefix."""

    def test_list_blobs_returns_uris_under_prefix(self, mock_storage_client):
        mock_storage_client.list_blobs.return_value = [
            _make_blob("v1/transcript/output_001.json"),
            _make_blob("v1/transcript/output_002.json"),
            _make_blob("v1/transcript/manifest.json"),
        ]

        with patch("ingestion.storage.build_storage_client", return_value=mock_storage_client):
            uris = list_blobs(f"gs://{BUCKET}/v1/transcript/")

        assert uris == [
            f"gs://{BUCKET}/v1/transcript/output_001.json",
            f"gs://{BUCKET}/v1/transcript/output_002.json",
            f"gs://{BUCKET}/v1/transcript/manifest.json",
        ]
        mock_storage_client.list_blobs.assert_called_once_with(BUCKET, prefix="v1/transcript/")

    def test_list_blobs_empty_prefix_returns_empty_list(self, mock_storage_client):
        mock_storage_client.list_blobs.return_value = []
        with patch("ingestion.storage.build_storage_client", return_value=mock_storage_client):
            uris = list_blobs(f"gs://{BUCKET}/empty/")
        assert uris == []

    def test_list_blobs_rejects_non_gcs_uri(self):
        with pytest.raises(StorageError, match="gs://"):
            list_blobs("/local/path/")


class TestSentinelWriteAndCheck:
    """Verify write_sentinel + sentinel_exists round-trip consistently."""

    def test_sentinel_write_and_check(self, mock_storage_client):
        sentinel_uri = f"gs://{BUCKET}/nanna_udaya_2025_07_06/.indexed"
        blob = MagicMock()
        blob.exists.side_effect = [False, True]  # before write, after write
        mock_storage_client.bucket.return_value.blob.return_value = blob

        with patch("ingestion.storage.build_storage_client", return_value=mock_storage_client):
            assert sentinel_exists(sentinel_uri) is False
            written = write_sentinel(sentinel_uri)
            assert sentinel_exists(sentinel_uri) is True

        assert written == sentinel_uri
        # The write should put an empty (or near-empty) string blob.
        blob.upload_from_string.assert_called_once()

    def test_sentinel_exists_returns_false_for_missing_blob(self, mock_storage_client):
        blob = MagicMock()
        blob.exists.return_value = False
        mock_storage_client.bucket.return_value.blob.return_value = blob
        with patch("ingestion.storage.build_storage_client", return_value=mock_storage_client):
            assert sentinel_exists(f"gs://{BUCKET}/never_indexed/.indexed") is False

    def test_write_sentinel_rejects_non_gcs_uri(self):
        with pytest.raises(StorageError, match="gs://"):
            write_sentinel("/local/.indexed")


# ---------------------------------------------------------------------------
# Supporting tests — delete_prefix, URI parsing edge cases
# ---------------------------------------------------------------------------

class TestDeletePrefix:
    """Verify delete_prefix removes all matching blobs and returns the count."""

    def test_delete_prefix_removes_all_matching_blobs(self, mock_storage_client):
        blobs = [_make_blob("v1/a.json"), _make_blob("v1/b.json"), _make_blob("v1/c.json")]
        mock_storage_client.list_blobs.return_value = blobs

        with patch("ingestion.storage.build_storage_client", return_value=mock_storage_client):
            count = delete_prefix(f"gs://{BUCKET}/v1/")

        assert count == 3
        for b in blobs:
            b.delete.assert_called_once()

    def test_delete_prefix_returns_zero_for_empty(self, mock_storage_client):
        mock_storage_client.list_blobs.return_value = []
        with patch("ingestion.storage.build_storage_client", return_value=mock_storage_client):
            assert delete_prefix(f"gs://{BUCKET}/nothing/") == 0


class TestUriParsing:
    """Verify URI parsing edge cases are handled."""

    def test_uri_with_no_path_after_bucket(self, mock_storage_client):
        # gs://bucket (no trailing slash, no path) — list should still call with empty prefix
        mock_storage_client.list_blobs.return_value = []
        with patch("ingestion.storage.build_storage_client", return_value=mock_storage_client):
            list_blobs(f"gs://{BUCKET}/")
        mock_storage_client.list_blobs.assert_called_once_with(BUCKET, prefix="")

    def test_uri_with_deeply_nested_path(self, mock_storage_client):
        target = f"gs://{BUCKET}/a/b/c/d/e.txt"
        blob = _make_blob("a/b/c/d/e.txt", content=b'{"ok": true}')
        mock_storage_client.bucket.return_value.blob.return_value = blob
        with patch("ingestion.storage.build_storage_client", return_value=mock_storage_client):
            download_json(target)
        mock_storage_client.bucket.return_value.blob.assert_called_with("a/b/c/d/e.txt")


# ---------------------------------------------------------------------------
# Observability — Phase 4.7
# ---------------------------------------------------------------------------

class TestStorageSpans:
    """Verify upload_file and write_sentinel emit OTel spans."""

    def test_upload_file_emits_span(
        self, mock_storage_client, tmp_local_file, in_memory_spans
    ):
        target_uri = f"gs://{BUCKET}/nanna_udaya_2025_07_06/audio.flac"
        with patch("ingestion.storage.build_storage_client", return_value=mock_storage_client):
            upload_file(tmp_local_file, target_uri)

        spans = [
            s for s in in_memory_spans.get_finished_spans() if s.name == "storage.upload_file"
        ]
        assert len(spans) == 1
        attrs = spans[0].attributes
        assert attrs["uri"] == target_uri
        assert attrs["size_bytes"] == tmp_local_file.stat().st_size

    def test_write_sentinel_emits_span(self, mock_storage_client, in_memory_spans):
        sentinel_uri = f"gs://{BUCKET}/nanna_udaya_2025_07_06/.indexed"
        blob = MagicMock()
        mock_storage_client.bucket.return_value.blob.return_value = blob

        with patch("ingestion.storage.build_storage_client", return_value=mock_storage_client):
            write_sentinel(sentinel_uri)

        spans = [
            s for s in in_memory_spans.get_finished_spans() if s.name == "storage.write_sentinel"
        ]
        assert len(spans) == 1
        assert spans[0].attributes["sentinel_uri"] == sentinel_uri
