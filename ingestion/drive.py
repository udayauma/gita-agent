"""
Google Drive integration module for the Gita Agent ingestion pipeline.

Lists and downloads MP4 video files from a shared Google Drive folder,
and generates sanitized video_id identifiers for use throughout the pipeline.

Design reference: docs/detailed_technical_design.md § 2.3, 3.2

Usage:
    from ingestion.drive import DriveClient

    client = DriveClient()
    files = client.list_video_files("1hWMRJRvw5di8WF7WpDPH1a311FAIpbPA")
    for f in files:
        local_path = client.download_file(f.file_id, f.name, Path("/tmp/downloads"))
        print(f"{f.video_id} -> {local_path}")
"""

import io
import re
from dataclasses import dataclass
from pathlib import Path

import structlog
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
import google.auth

from ingestion.observability import get_tracer

logger = structlog.get_logger(__name__)

# Fields requested from the Drive API
DRIVE_FILE_FIELDS = "files(id, name, mimeType, size, createdTime), nextPageToken"

# Only these MIME types are considered video files
VIDEO_MIME_TYPES = {"video/mp4"}

# ---------------------------------------------------------------------------
# Filename Pattern Registry
# ---------------------------------------------------------------------------
# Each entry: (pattern_name, regex, extractor_function)
# Patterns are tried in order. First match wins.
# The regex must define named groups: 'speakers' and 'year', 'month', 'day'.
# If no pattern matches, a generic fallback sanitizes the entire filename.

def _extract_google_meet(match: re.Match) -> str:
    """Extract video_id from Google Meet format: 'Speaker / Speaker - YYYY/MM/DD HH:MM TZ - Recording'."""
    speakers = re.sub(r"[^a-zA-Z0-9]", "_", match.group("speakers"))
    return f"{speakers}_{match.group('year')}_{match.group('month')}_{match.group('day')}"


def _extract_zoom(match: re.Match) -> str:
    """Extract video_id from Zoom format: 'YYYY-MM-DD HH.MM.SS Topic Name'."""
    topic = re.sub(r"[^a-zA-Z0-9]", "_", match.group("topic"))
    return f"{match.group('year')}_{match.group('month')}_{match.group('day')}_{topic}"


def _extract_date_anywhere(match: re.Match) -> str:
    """Extract video_id when a date is found anywhere: uses prefix + date."""
    prefix = match.group("prefix").strip()
    prefix = re.sub(r"[^a-zA-Z0-9]", "_", prefix) if prefix else "video"
    sep = match.group("sep")  # '/' or '-'
    return f"{prefix}_{match.group('year')}_{match.group('month')}_{match.group('day')}"


FILENAME_PATTERNS: list[tuple[str, re.Pattern, callable]] = [
    (
        "google_meet",
        re.compile(r"^(?P<speakers>.+?)\s*-\s*(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})"),
        _extract_google_meet,
    ),
    (
        "zoom",
        re.compile(r"^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})\s+[\d.]+\s+(?P<topic>.+)"),
        _extract_zoom,
    ),
    (
        "date_anywhere",
        re.compile(r"^(?P<prefix>.*?)(?P<year>\d{4})(?P<sep>[/-])(?P<month>\d{2})(?P=sep)(?P<day>\d{2})"),
        _extract_date_anywhere,
    ),
]


class DriveError(Exception):
    """Raised when a Google Drive API operation fails."""

    pass


@dataclass
class DriveFile:
    """Metadata about a video file in Google Drive.

    Attributes:
        file_id: Google Drive file ID.
        name: Original filename in Drive.
        mime_type: MIME type (e.g., 'video/mp4').
        size_bytes: File size in bytes.
        video_id: Sanitized identifier derived from filename, used as the
                  canonical key throughout the pipeline (GCS paths, Pinecone IDs).
        created_time: ISO 8601 timestamp of file creation in Drive.
    """

    file_id: str
    name: str
    mime_type: str
    size_bytes: int
    video_id: str
    created_time: str


def sanitize_video_id(
    filename: str,
    override: str | None = None,
) -> str:
    """Convert a Drive filename into a clean, lowercase video identifier.

    Uses a pattern registry (FILENAME_PATTERNS) to try known recording formats
    in order. If no pattern matches, falls through to a generic fallback that
    sanitizes the entire filename. An explicit override bypasses all pattern
    matching entirely.

    Pattern priority:
        1. google_meet — "Speaker / Speaker - YYYY/MM/DD HH:MM TZ - Recording"
        2. zoom        — "YYYY-MM-DD HH.MM.SS Topic Name"
        3. date_anywhere — any filename containing YYYY/MM/DD or YYYY-MM-DD
        4. generic fallback — sanitize entire filename

    Examples:
        "Nanna / Udaya - 2025/07/06 14:22 EDT - Recording.mp4"
        → "nanna_udaya_2025_07_06"

        "2025-03-15 10.30.00 Gita Discussion.mp4"
        → "2025_03_15_gita_discussion"

    Args:
        filename: The original filename from Google Drive.
        override: Optional explicit video_id. If provided, the filename
                  is ignored and this value is sanitized and returned directly.
                  Use for one-off exceptions or manual renames.

    Returns:
        A lowercase, underscore-separated identifier string.

    Raises:
        ValueError: If the filename is empty or blank (and no override).
    """
    # If an explicit override is provided, just sanitize and return it
    if override:
        result = re.sub(r"[^a-zA-Z0-9]", "_", override.strip())
        result = result.lower()
        result = re.sub(r"_+", "_", result)
        return result.strip("_")

    if not filename or not filename.strip():
        raise ValueError("Filename cannot be empty or blank")

    # Remove file extension — don't use Path().stem because filenames
    # from Google Meet contain '/' which Path interprets as directories
    name = filename.strip()
    if "." in name:
        name = name.rsplit(".", 1)[0]

    # Try each pattern in the registry
    for pattern_name, pattern, extractor in FILENAME_PATTERNS:
        match = pattern.match(name)
        if match:
            result = extractor(match)
            logger.debug(
                "video_id_pattern_matched",
                pattern=pattern_name,
                filename=filename,
            )
            break
    else:
        # No pattern matched — generic fallback
        logger.warning(
            "video_id_no_pattern_matched",
            filename=filename,
            hint="Consider adding a new pattern to FILENAME_PATTERNS in ingestion/drive.py",
        )
        result = re.sub(r"[^a-zA-Z0-9]", "_", name)

    # Lowercase, collapse multiple underscores, strip leading/trailing
    result = result.lower()
    result = re.sub(r"_+", "_", result)
    result = result.strip("_")

    return result


def build_drive_service():
    """Build an authenticated Google Drive API service.

    Uses Application Default Credentials (ADC), which works with:
    - `gcloud auth application-default login` (local dev)
    - Workload Identity (Cloud Run)
    - Service account JSON key (GOOGLE_APPLICATION_CREDENTIALS)

    Returns:
        A Google Drive API service resource.
    """
    credentials, project = google.auth.default(
        scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    return build("drive", "v3", credentials=credentials)


class DriveClient:
    """Client for interacting with Google Drive to list and download video files.

    Uses the Google Drive API v3 with read-only access.
    """

    def __init__(self, service=None):
        """Initialize the Drive client.

        Args:
            service: Optional pre-built Drive API service (for testing).
                     If not provided, builds one using ADC.
        """
        self._service = service or build_drive_service()

    def list_video_files(self, folder_id: str) -> list[DriveFile]:
        """List all MP4 video files in a Google Drive folder.

        Follows pagination to retrieve all files. Filters to video/mp4 only.

        Args:
            folder_id: Google Drive folder ID to list files from.

        Returns:
            List of DriveFile objects for each video file found.

        Raises:
            DriveError: If the API call fails.
        """
        logger.info("listing_drive_files", folder_id=folder_id)

        all_files = []
        page_token = None

        try:
            while True:
                response = self._service.files().list(
                    q=f"'{folder_id}' in parents and trashed = false",
                    fields=DRIVE_FILE_FIELDS,
                    pageSize=100,
                    pageToken=page_token,
                ).execute()

                raw_files = response.get("files", [])

                # Filter to video MIME types only
                for f in raw_files:
                    if f.get("mimeType") in VIDEO_MIME_TYPES:
                        all_files.append(
                            DriveFile(
                                file_id=f["id"],
                                name=f["name"],
                                mime_type=f["mimeType"],
                                size_bytes=int(f.get("size", 0)),
                                video_id=sanitize_video_id(f["name"]),
                                created_time=f.get("createdTime", ""),
                            )
                        )

                page_token = response.get("nextPageToken")
                if not page_token:
                    break

        except HttpError as e:
            raise DriveError(
                f"Failed to list files in folder {folder_id}: {e}"
            ) from e

        logger.info(
            "drive_files_listed",
            folder_id=folder_id,
            total_files=len(all_files),
        )
        return all_files

    def download_file(
        self,
        file_id: str,
        filename: str,
        output_dir: Path,
        video_id: str | None = None,
    ) -> Path:
        """Download a file from Google Drive to a local directory.

        Uses chunked download via MediaIoBaseDownload for large files.

        Args:
            file_id: Google Drive file ID to download.
            filename: Name to save the file as locally.
            output_dir: Directory to save the file into. Created if it doesn't exist.
            video_id: Optional sanitized identifier — attached as an OTel span
                attribute so traces can be filtered by video in Cloud Trace.

        Returns:
            Path to the downloaded local file.

        Raises:
            DriveError: If the download fails.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / filename

        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("drive.download") as span:
            span.set_attribute("file_id", file_id)
            if video_id:
                span.set_attribute("video_id", video_id)

            logger.info(
                "downloading_file",
                file_id=file_id,
                filename=filename,
                output_path=str(output_path),
            )

            try:
                request = self._service.files().get_media(fileId=file_id)
                with open(output_path, "wb") as fh:
                    downloader = MediaIoBaseDownload(fh, request)
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()
                        if status:
                            progress = status.progress()
                            logger.debug(
                                "download_progress",
                                file_id=file_id,
                                progress=f"{progress * 100:.1f}%",
                            )
            except HttpError as e:
                raise DriveError(
                    f"Failed to download file {file_id}: {e}"
                ) from e

            size_bytes = output_path.stat().st_size
            span.set_attribute("size_bytes", size_bytes)
            logger.info(
                "download_complete",
                file_id=file_id,
                output_path=str(output_path),
                size_bytes=size_bytes,
            )
            return output_path
