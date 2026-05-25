"""
Ingestion pipeline orchestrator for the Gita Agent.

CLI entry point that runs the full ingestion pipeline for one or more
Bhagavad Gita recordings from Google Drive:

    Drive download → audio extract → GCS upload → Chirp 3 transcribe →
    Gemini translate → chunk + embed + Pinecone upsert → write .indexed sentinel

The `.indexed` sentinel at `gs://{bucket}/{video_id}/.indexed` is the
single source of truth for "this video is fully processed." It is
written only after `chunk_and_embed` reports at least one upserted
vector — so half-completed runs don't get marked as done.

Designed to run identically:
- Locally: `python -m ingestion.orchestrator [flags]`
- As a Cloud Run Job: `gcloud run jobs execute ingest-recordings --wait`
  (the Job's container ENTRYPOINT is the same Python invocation)

Design reference: docs/detailed_technical_design.md § 3.2

Usage:
    # Scan Drive, diff against sentinels, process new videos
    python -m ingestion.orchestrator

    # Process one specific video (no scan)
    python -m ingestion.orchestrator --video-id nanna_udaya_2025_07_06

    # Re-process even if already indexed
    python -m ingestion.orchestrator --force-reindex

    # List what would be processed without doing it
    python -m ingestion.orchestrator --dry-run
"""

import argparse
import os
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import structlog

from ingestion import storage
from ingestion.audio import extract_audio
from ingestion.chunking import chunk_and_embed
from ingestion.drive import DriveClient, DriveFile
from ingestion.transcription import transcribe
from ingestion.translation import translate

logger = structlog.get_logger(__name__)

SENTINEL_NAME = ".indexed"
DEFAULT_BUCKET = "gita-agent-prod-audio"


class OrchestrationError(Exception):
    """Raised on missing configuration or unrecoverable orchestrator errors."""


@dataclass
class ProcessingResult:
    """Outcome of running the pipeline against one video."""

    video_id: str
    video_title: str
    success: bool
    skipped: bool = False
    vector_count: int = 0
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Patchable seam
# ---------------------------------------------------------------------------

def build_drive_client() -> DriveClient:
    """Factory for DriveClient. Patched in unit tests."""
    return DriveClient()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bucket() -> str:
    return os.environ.get("GCS_AUDIO_BUCKET", DEFAULT_BUCKET)


def _sentinel_uri(video_id: str, bucket: Optional[str] = None) -> str:
    return f"gs://{bucket or _bucket()}/{video_id}/{SENTINEL_NAME}"


def _audio_uri(video_id: str, bucket: Optional[str] = None) -> str:
    return f"gs://{bucket or _bucket()}/{video_id}/audio.flac"


def _derive_session_date(drive_file: DriveFile) -> str:
    """ISO date YYYY-MM-DD from the Drive file's created_time (ISO 8601 timestamp)."""
    return (drive_file.created_time or "")[:10] or "unknown"


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------

def is_already_indexed(video_id: str, *, bucket: Optional[str] = None) -> bool:
    """Return True iff the `.indexed` sentinel exists for this video."""
    return storage.sentinel_exists(_sentinel_uri(video_id, bucket))


# ---------------------------------------------------------------------------
# Single-video pipeline
# ---------------------------------------------------------------------------

def process_video(
    drive_file: DriveFile,
    *,
    force_reindex: bool = False,
    bucket: Optional[str] = None,
    work_dir: Optional[Path] = None,
) -> ProcessingResult:
    """Run the full ingestion pipeline for one Drive file.

    Args:
        drive_file: File metadata from `DriveClient.list_video_files`.
        force_reindex: If True, run the pipeline even if `.indexed` exists.
        bucket: Override the GCS bucket (defaults to $GCS_AUDIO_BUCKET).
        work_dir: Local directory for the MP4 + FLAC. A tmpdir is used if None.

    Returns:
        ProcessingResult with vector_count, skipped flag, and error string on failure.
        Never raises — failures are reported via `success=False` and `error`.
    """
    bucket = bucket or _bucket()
    video_id = drive_file.video_id
    sentinel = _sentinel_uri(video_id, bucket)

    if not force_reindex and storage.sentinel_exists(sentinel):
        logger.info("orchestrator.skip_indexed", video_id=video_id)
        return ProcessingResult(
            video_id=video_id,
            video_title=drive_file.name,
            success=True,
            skipped=True,
        )

    work_dir = work_dir or Path(tempfile.mkdtemp(prefix="gita_ingest_"))
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        logger.info("orchestrator.start", video_id=video_id, video_title=drive_file.name)

        # 1. Drive download
        drive_client = build_drive_client()
        mp4_path = drive_client.download_file(
            drive_file.file_id, drive_file.name, work_dir
        )

        # 2. Audio extract
        audio_result = extract_audio(mp4_path, work_dir, video_id=video_id)

        # 3. GCS upload
        audio_uri = _audio_uri(video_id, bucket)
        storage.upload_file(audio_result.output_path, audio_uri)

        # 4. Transcribe (Chirp 3)
        transcription = transcribe(audio_uri=audio_uri, video_id=video_id)

        # 5. Translate (Gemini 3 Flash, with Cloud Translate fallback)
        translation = translate(transcription)

        # 6. Chunk + embed + Pinecone upsert
        chunking_result = chunk_and_embed(
            translation,
            video_title=drive_file.name,
            session_date=_derive_session_date(drive_file),
            upsert=True,
        )

        # 7. Sentinel — only if we actually upserted vectors
        if chunking_result.total_vectors_upserted > 0:
            storage.write_sentinel(sentinel)
            logger.info(
                "orchestrator.complete",
                video_id=video_id,
                vector_count=chunking_result.total_vectors_upserted,
            )
        else:
            logger.warning(
                "orchestrator.no_vectors_skipping_sentinel",
                video_id=video_id,
            )

        return ProcessingResult(
            video_id=video_id,
            video_title=drive_file.name,
            success=True,
            vector_count=chunking_result.total_vectors_upserted,
        )

    except Exception as e:
        logger.error("orchestrator.failed", video_id=video_id, error=str(e))
        return ProcessingResult(
            video_id=video_id,
            video_title=drive_file.name,
            success=False,
            error=str(e),
        )


# ---------------------------------------------------------------------------
# Scan + diff + process
# ---------------------------------------------------------------------------

def scan_and_process(
    *,
    folder_id: Optional[str] = None,
    force_reindex: bool = False,
    video_id_filter: Optional[str] = None,
    dry_run: bool = False,
    bucket: Optional[str] = None,
) -> list[ProcessingResult]:
    """List the Drive folder, diff against sentinels, and process new videos.

    Args:
        folder_id: Drive folder ID. Defaults to $DRIVE_FOLDER_ID.
        force_reindex: Process every video, ignoring sentinels.
        video_id_filter: If set, only process the video with this video_id.
        dry_run: List what would be processed but invoke no downstream module.
        bucket: Override the GCS bucket.

    Returns:
        List of ProcessingResult — one per video considered.
        For dry_run, returns an empty list (nothing was processed).
    """
    folder_id = folder_id or os.environ.get("DRIVE_FOLDER_ID")
    if not folder_id:
        raise OrchestrationError(
            "DRIVE_FOLDER_ID must be set (env var) or passed explicitly"
        )
    bucket = bucket or _bucket()

    drive_client = build_drive_client()
    files = drive_client.list_video_files(folder_id)

    if video_id_filter:
        files = [f for f in files if f.video_id == video_id_filter]

    if dry_run:
        for f in files:
            indexed = is_already_indexed(f.video_id, bucket=bucket)
            logger.info(
                "orchestrator.dry_run",
                video_id=f.video_id,
                video_title=f.name,
                would_process=(not indexed or force_reindex),
            )
        return []

    results: list[ProcessingResult] = []
    for f in files:
        if not force_reindex and is_already_indexed(f.video_id, bucket=bucket):
            results.append(
                ProcessingResult(
                    video_id=f.video_id,
                    video_title=f.name,
                    success=True,
                    skipped=True,
                )
            )
            continue
        results.append(process_video(f, force_reindex=force_reindex, bucket=bucket))

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ingestion.orchestrator",
        description=(
            "Scan the Drive folder and process new recordings into Pinecone. "
            "Run with no args to process anything new since the last invocation."
        ),
    )
    parser.add_argument(
        "--video-id",
        help="Process only the video with this sanitized video_id (skip scan/diff)",
    )
    parser.add_argument(
        "--force-reindex",
        action="store_true",
        help="Re-process videos even if `.indexed` sentinel exists",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List what would be processed; invoke no downstream module",
    )
    return parser


def _summarize(results: list[ProcessingResult]) -> tuple[int, int, int]:
    processed = sum(1 for r in results if r.success and not r.skipped)
    skipped = sum(1 for r in results if r.skipped)
    failed = sum(1 for r in results if not r.success)
    return processed, skipped, failed


def main(argv: Optional[list[str]] = None) -> int:
    args = _build_argparser().parse_args(argv)

    try:
        results = scan_and_process(
            force_reindex=args.force_reindex,
            video_id_filter=args.video_id,
            dry_run=args.dry_run,
        )
    except OrchestrationError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 2

    if args.dry_run:
        print("Dry run complete — see logs for details.")
        return 0

    processed, skipped, failed = _summarize(results)
    print(
        f"Processed: {processed}, Skipped: {skipped}, Failed: {failed} "
        f"(total considered: {len(results)})"
    )
    for r in results:
        if not r.success:
            print(f"  FAILED {r.video_id}: {r.error}", file=sys.stderr)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
