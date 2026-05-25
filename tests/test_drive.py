"""
Tests for ingestion/drive.py — Google Drive integration module.

TDD Phase: RED — tests written before implementation.
The Drive module lists MP4 files in a shared Google Drive folder,
downloads them locally, and generates sanitized video_id identifiers.

Design reference: docs/detailed_technical_design.md § 2.3, 3.2

All Drive API calls are mocked — no real network calls in unit tests.
"""

import io
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from ingestion.drive import (
    DriveClient,
    DriveFile,
    DriveError,
    sanitize_video_id,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_DRIVE_FILES = [
    {
        "id": "file_abc123",
        "name": "Nanna / Udaya - 2025/07/06 14:22 EDT - Recording.mp4",
        "mimeType": "video/mp4",
        "size": "1073741824",  # ~1 GB
        "createdTime": "2025-07-06T18:22:00.000Z",
    },
    {
        "id": "file_def456",
        "name": "Nanna / Udaya - 2025/07/20 19:57 EDT - Recording.mp4",
        "mimeType": "video/mp4",
        "size": "671813632",  # ~640 MB
        "createdTime": "2025-07-20T23:57:00.000Z",
    },
    {
        "id": "file_ghi789",
        "name": "Nanna / Udaya - 2025/08/03 18:59 EDT - Recording.mp4",
        "mimeType": "video/mp4",
        "size": "700448768",  # ~668 MB
        "createdTime": "2025-08-03T22:59:00.000Z",
    },
    {
        "id": "file_jkl012",
        "name": "Nanna / Udaya - 2025/08/17 12:05 EDT - Recording.mp4",
        "mimeType": "video/mp4",
        "size": "998244352",  # ~952 MB
        "createdTime": "2025-08-17T16:05:00.000Z",
    },
]


@pytest.fixture
def mock_drive_service():
    """Create a mocked Google Drive API service."""
    service = MagicMock()
    return service


@pytest.fixture
def drive_client(mock_drive_service):
    """Create a DriveClient with a mocked service."""
    with patch("ingestion.drive.build_drive_service", return_value=mock_drive_service):
        client = DriveClient()
        client._service = mock_drive_service
    return client


@pytest.fixture
def output_dir(tmp_path):
    """Provide a clean download directory."""
    out = tmp_path / "downloads"
    out.mkdir()
    return out


def _mock_list_response(files):
    """Helper: build a mock Drive files().list().execute() response."""
    return {"files": files, "nextPageToken": None}


# ---------------------------------------------------------------------------
# 4.2.1 — sanitize_video_id: filename → clean identifier
# ---------------------------------------------------------------------------

class TestSanitizeVideoId:
    """Tests for the video_id sanitization function."""

    # --- Google Meet pattern ---

    def test_google_meet_filename(self):
        """Standard Google Meet recording name should produce a clean video_id."""
        name = "Nanna / Udaya - 2025/07/06 14:22 EDT - Recording.mp4"
        vid = sanitize_video_id(name)
        assert vid == "nanna_udaya_2025_07_06"

    def test_all_four_session_names(self):
        """All 4 actual session filenames should produce unique, clean video_ids."""
        names = [f["name"] for f in SAMPLE_DRIVE_FILES]
        ids = [sanitize_video_id(n) for n in names]
        # All unique
        assert len(set(ids)) == 4
        # All lowercase, no special chars
        for vid in ids:
            assert vid == vid.lower()
            assert "/" not in vid
            assert " " not in vid
            assert vid.isascii()

    # --- Zoom pattern ---

    def test_zoom_filename(self):
        """Zoom recording format should extract date + topic."""
        name = "2025-03-15 10.30.00 Gita Discussion.mp4"
        vid = sanitize_video_id(name)
        assert vid == "2025_03_15_gita_discussion"

    def test_zoom_filename_with_spaces_in_topic(self):
        """Zoom topic with multiple words should be underscore-separated."""
        name = "2026-01-20 14.00.00 Weekly Bhagavad Gita Study Group.mp4"
        vid = sanitize_video_id(name)
        assert "2026_01_20" in vid
        assert "weekly" in vid
        assert " " not in vid

    # --- date_anywhere fallback pattern ---

    def test_date_anywhere_with_slash_separator(self):
        """Filename with date using / separator should be matched."""
        name = "MyRecording 2025/07/06 session.mp4"
        vid = sanitize_video_id(name)
        assert "2025_07_06" in vid

    def test_date_anywhere_with_dash_separator(self):
        """Filename with date using - separator should be matched."""
        name = "session_2025-08-17_afternoon.mp4"
        vid = sanitize_video_id(name)
        assert "2025_08_17" in vid

    # --- Generic fallback ---

    def test_generic_fallback_no_date(self):
        """Filename with no recognizable date falls through to generic."""
        vid = sanitize_video_id("random_lecture_notes.mp4")
        assert vid == "random_lecture_notes"

    def test_generic_fallback_is_clean(self):
        """Generic fallback should still produce a clean identifier."""
        vid = sanitize_video_id("My (Special) File #2!.mp4")
        assert "/" not in vid
        assert " " not in vid
        assert vid == vid.lower()

    # --- Override ---

    def test_override_bypasses_filename(self):
        """Explicit override should be used instead of the filename."""
        vid = sanitize_video_id(
            "Nanna / Udaya - 2025/07/06 14:22 EDT - Recording.mp4",
            override="custom_session_one",
        )
        assert vid == "custom_session_one"

    def test_override_is_sanitized(self):
        """Override value should still be sanitized."""
        vid = sanitize_video_id("anything.mp4", override="My Custom ID!")
        assert vid == "my_custom_id"

    def test_override_with_empty_filename(self):
        """Override should work even if filename is empty."""
        vid = sanitize_video_id("", override="manual_id")
        assert vid == "manual_id"

    # --- Common behavior ---

    def test_strips_file_extension(self):
        """File extension should not appear in the video_id."""
        vid = sanitize_video_id("some_video.mp4")
        assert ".mp4" not in vid

    def test_replaces_slashes_and_spaces(self):
        """Slashes, spaces, and special characters become underscores."""
        vid = sanitize_video_id("A / B - 2025/01/01 10:00 EST - Rec.mp4")
        assert "/" not in vid
        assert " " not in vid

    def test_collapses_multiple_underscores(self):
        """Multiple consecutive underscores should be collapsed to one."""
        vid = sanitize_video_id("A___B___C.mp4")
        assert "___" not in vid

    def test_strips_leading_trailing_underscores(self):
        """No leading or trailing underscores in the result."""
        vid = sanitize_video_id("___test___.mp4")
        assert not vid.startswith("_")
        assert not vid.endswith("_")

    def test_empty_string_raises(self):
        """Empty filename should raise ValueError when no override."""
        with pytest.raises(ValueError, match="(?i)empty|blank"):
            sanitize_video_id("")

    def test_returns_string(self):
        """Result should always be a plain string."""
        vid = sanitize_video_id("test.mp4")
        assert isinstance(vid, str)


# ---------------------------------------------------------------------------
# 4.2.2 — DriveClient.list_video_files: folder listing
# ---------------------------------------------------------------------------

class TestDriveClientListFiles:
    """Tests for listing video files in a Drive folder."""

    def test_list_returns_drive_file_objects(self, drive_client, mock_drive_service):
        """list_video_files should return a list of DriveFile dataclass instances."""
        mock_drive_service.files.return_value.list.return_value.execute.return_value = (
            _mock_list_response(SAMPLE_DRIVE_FILES)
        )
        files = drive_client.list_video_files("folder_id_123")
        assert len(files) == 4
        assert all(isinstance(f, DriveFile) for f in files)

    def test_list_populates_all_fields(self, drive_client, mock_drive_service):
        """Each DriveFile should have id, name, size_bytes, video_id, and created_time."""
        mock_drive_service.files.return_value.list.return_value.execute.return_value = (
            _mock_list_response([SAMPLE_DRIVE_FILES[0]])
        )
        files = drive_client.list_video_files("folder_id_123")
        f = files[0]
        assert f.file_id == "file_abc123"
        assert f.name == SAMPLE_DRIVE_FILES[0]["name"]
        assert f.size_bytes == 1073741824
        assert f.video_id == sanitize_video_id(SAMPLE_DRIVE_FILES[0]["name"])
        assert f.mime_type == "video/mp4"

    def test_list_filters_mp4_only(self, drive_client, mock_drive_service):
        """Only video/mp4 files should be returned, not docs or other types."""
        mixed_files = SAMPLE_DRIVE_FILES[:2] + [
            {"id": "doc1", "name": "Notes.docx", "mimeType": "application/vnd.google-apps.document",
             "size": "1024", "createdTime": "2025-01-01T00:00:00Z"},
        ]
        mock_drive_service.files.return_value.list.return_value.execute.return_value = (
            _mock_list_response(mixed_files)
        )
        files = drive_client.list_video_files("folder_id_123")
        assert len(files) == 2
        assert all(f.mime_type == "video/mp4" for f in files)

    def test_list_empty_folder(self, drive_client, mock_drive_service):
        """Empty folder should return empty list, not error."""
        mock_drive_service.files.return_value.list.return_value.execute.return_value = (
            _mock_list_response([])
        )
        files = drive_client.list_video_files("folder_id_123")
        assert files == []

    def test_list_queries_correct_folder(self, drive_client, mock_drive_service):
        """The Drive API query should filter by the given folder ID."""
        mock_drive_service.files.return_value.list.return_value.execute.return_value = (
            _mock_list_response([])
        )
        drive_client.list_video_files("my_folder_id")
        # Verify the query includes the folder ID
        call_kwargs = mock_drive_service.files.return_value.list.call_args
        query = call_kwargs.kwargs.get("q", "") if call_kwargs.kwargs else ""
        assert "my_folder_id" in query

    def test_list_handles_pagination(self, drive_client, mock_drive_service):
        """Should follow nextPageToken to get all files across pages."""
        # Page 1: 2 files + nextPageToken
        page1 = {"files": SAMPLE_DRIVE_FILES[:2], "nextPageToken": "token_page2"}
        # Page 2: 2 files, no more pages
        page2 = {"files": SAMPLE_DRIVE_FILES[2:], "nextPageToken": None}

        mock_drive_service.files.return_value.list.return_value.execute.side_effect = [
            page1, page2
        ]
        files = drive_client.list_video_files("folder_id_123")
        assert len(files) == 4


# ---------------------------------------------------------------------------
# 4.2.3 — DriveClient.download_file: download MP4 to local path
# ---------------------------------------------------------------------------

class TestDriveClientDownload:
    """Tests for downloading files from Drive."""

    def test_download_creates_file(self, drive_client, mock_drive_service, output_dir):
        """Downloaded file should exist on disk."""
        # Mock the media download
        mock_request = MagicMock()
        mock_drive_service.files.return_value.get_media.return_value = mock_request

        # Simulate MediaIoBaseDownload behavior
        with patch("ingestion.drive.MediaIoBaseDownload") as mock_dl_class:
            mock_downloader = MagicMock()
            mock_dl_class.return_value = mock_downloader
            # Simulate: first chunk not done, second chunk done
            mock_downloader.next_chunk.side_effect = [
                (MagicMock(progress=MagicMock(return_value=0.5)), False),
                (MagicMock(progress=MagicMock(return_value=1.0)), True),
            ]

            result_path = drive_client.download_file(
                file_id="file_abc123",
                filename="test_video.mp4",
                output_dir=output_dir,
            )

        assert result_path.exists()
        assert result_path.name == "test_video.mp4"

    def test_download_to_nonexistent_dir_creates_it(
        self, drive_client, mock_drive_service, tmp_path
    ):
        """If the output directory doesn't exist, it should be created."""
        new_dir = tmp_path / "new" / "nested" / "dir"

        mock_request = MagicMock()
        mock_drive_service.files.return_value.get_media.return_value = mock_request

        with patch("ingestion.drive.MediaIoBaseDownload") as mock_dl_class:
            mock_downloader = MagicMock()
            mock_dl_class.return_value = mock_downloader
            mock_downloader.next_chunk.side_effect = [
                (MagicMock(progress=MagicMock(return_value=1.0)), True),
            ]

            result_path = drive_client.download_file(
                file_id="file_abc123",
                filename="video.mp4",
                output_dir=new_dir,
            )

        assert new_dir.exists()
        assert result_path.exists()

    def test_download_returns_path_object(
        self, drive_client, mock_drive_service, output_dir
    ):
        """download_file should return a Path object."""
        mock_request = MagicMock()
        mock_drive_service.files.return_value.get_media.return_value = mock_request

        with patch("ingestion.drive.MediaIoBaseDownload") as mock_dl_class:
            mock_downloader = MagicMock()
            mock_dl_class.return_value = mock_downloader
            mock_downloader.next_chunk.side_effect = [
                (MagicMock(progress=MagicMock(return_value=1.0)), True),
            ]

            result_path = drive_client.download_file(
                file_id="file_abc123",
                filename="video.mp4",
                output_dir=output_dir,
            )

        assert isinstance(result_path, Path)

    def test_download_api_error_raises_drive_error(
        self, drive_client, mock_drive_service, output_dir
    ):
        """Drive API errors should be wrapped in DriveError."""
        from googleapiclient.errors import HttpError

        mock_drive_service.files.return_value.get_media.side_effect = HttpError(
            resp=MagicMock(status=404), content=b"File not found"
        )

        with pytest.raises(DriveError, match="(?i)download|failed|error"):
            drive_client.download_file(
                file_id="nonexistent",
                filename="video.mp4",
                output_dir=output_dir,
            )

    def test_download_emits_drive_download_span(
        self, drive_client, mock_drive_service, output_dir, in_memory_spans
    ):
        """download_file emits a `drive.download` span with video_id + size_bytes."""
        mock_request = MagicMock()
        mock_drive_service.files.return_value.get_media.return_value = mock_request

        with patch("ingestion.drive.MediaIoBaseDownload") as mock_dl_class:
            mock_downloader = MagicMock()
            mock_dl_class.return_value = mock_downloader
            mock_downloader.next_chunk.side_effect = [
                (MagicMock(progress=MagicMock(return_value=1.0)), True),
            ]

            drive_client.download_file(
                file_id="file_abc123",
                filename="test_video.mp4",
                output_dir=output_dir,
                video_id="nanna_udaya_2025_07_06",
            )

        download_spans = [
            s for s in in_memory_spans.get_finished_spans() if s.name == "drive.download"
        ]
        assert len(download_spans) == 1
        attrs = download_spans[0].attributes
        assert attrs["video_id"] == "nanna_udaya_2025_07_06"
        assert "size_bytes" in attrs
        assert attrs["file_id"] == "file_abc123"


# ---------------------------------------------------------------------------
# 4.2.4 — DriveFile dataclass
# ---------------------------------------------------------------------------

class TestDriveFileDataclass:
    """Tests for the DriveFile dataclass."""

    def test_drive_file_has_required_fields(self):
        """DriveFile should have all fields needed by downstream pipeline steps."""
        df = DriveFile(
            file_id="abc",
            name="test.mp4",
            mime_type="video/mp4",
            size_bytes=1000,
            video_id="test",
            created_time="2025-07-06T18:22:00.000Z",
        )
        assert df.file_id == "abc"
        assert df.name == "test.mp4"
        assert df.mime_type == "video/mp4"
        assert df.size_bytes == 1000
        assert df.video_id == "test"
        assert df.created_time == "2025-07-06T18:22:00.000Z"

    def test_drive_file_video_id_matches_sanitized_name(self):
        """video_id should match what sanitize_video_id produces for the same name."""
        name = "Nanna / Udaya - 2025/07/06 14:22 EDT - Recording.mp4"
        df = DriveFile(
            file_id="abc",
            name=name,
            mime_type="video/mp4",
            size_bytes=1000,
            video_id=sanitize_video_id(name),
            created_time="2025-07-06T18:22:00.000Z",
        )
        assert df.video_id == sanitize_video_id(name)
