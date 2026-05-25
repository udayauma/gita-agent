"""
Google Cloud Storage helpers for the Gita Agent ingestion pipeline.

Wraps google-cloud-storage with the small set of operations the orchestrator
needs: upload FLAC audio, download Chirp 3 JSON transcripts, list blobs
under a prefix (for resolving Chirp 3's auto-named output file), delete
prefixes (cleanup between runs), and write/check the `.indexed` sentinel
that records "this video is fully processed."

Design reference: docs/detailed_technical_design.md § 3.2

All public functions take and return GCS URIs (gs://bucket/path) so callers
don't have to think about bucket/path splitting.

Usage:
    from ingestion import storage

    storage.upload_file(Path("/tmp/audio.flac"), "gs://bucket/v1/audio.flac")
    transcript = storage.download_json("gs://bucket/v1/transcript/output.json")
    storage.write_sentinel("gs://bucket/v1/.indexed")
    if storage.sentinel_exists("gs://bucket/v1/.indexed"):
        print("already indexed")
"""

import json
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


class StorageError(Exception):
    """Raised on malformed URIs or unparseable blob contents."""


def build_storage_client():
    """Factory for storage.Client. Patched in unit tests."""
    from google.cloud import storage
    return storage.Client()


# ---------------------------------------------------------------------------
# URI parsing
# ---------------------------------------------------------------------------

def _parse_gcs_uri(uri: str) -> tuple[str, str]:
    """Parse gs://bucket/path/inside → (bucket, "path/inside")."""
    if not isinstance(uri, str) or not uri.startswith("gs://"):
        raise StorageError(f"Expected gs:// URI, got: {uri!r}")
    rest = uri[len("gs://") :]
    bucket, _, blob_path = rest.partition("/")
    if not bucket:
        raise StorageError(f"URI {uri!r} has no bucket")
    return bucket, blob_path


# ---------------------------------------------------------------------------
# Upload / Download
# ---------------------------------------------------------------------------

def upload_file(local_path: Path, gcs_uri: str) -> str:
    """Upload a local file to GCS at the given URI; return the URI."""
    bucket_name, blob_path = _parse_gcs_uri(gcs_uri)
    client = build_storage_client()
    blob = client.bucket(bucket_name).blob(blob_path)
    blob.upload_from_filename(str(local_path))
    logger.info("storage.upload_file", uri=gcs_uri, local_path=str(local_path))
    return gcs_uri


def download_json(gcs_uri: str) -> dict:
    """Download a GCS blob and parse it as JSON."""
    bucket_name, blob_path = _parse_gcs_uri(gcs_uri)
    client = build_storage_client()
    blob = client.bucket(bucket_name).blob(blob_path)
    raw = blob.download_as_bytes()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise StorageError(f"Blob at {gcs_uri} contained invalid JSON: {e}") from e


# ---------------------------------------------------------------------------
# Listing / Deletion
# ---------------------------------------------------------------------------

def list_blobs(gcs_prefix_uri: str) -> list[str]:
    """List all gs:// URIs whose blob path starts with the URI's prefix."""
    bucket_name, prefix = _parse_gcs_uri(gcs_prefix_uri)
    client = build_storage_client()
    blobs = client.list_blobs(bucket_name, prefix=prefix)
    return [f"gs://{bucket_name}/{b.name}" for b in blobs]


def delete_prefix(gcs_prefix_uri: str) -> int:
    """Delete every blob under a gs:// prefix; return the count removed."""
    bucket_name, prefix = _parse_gcs_uri(gcs_prefix_uri)
    client = build_storage_client()
    blobs = list(client.list_blobs(bucket_name, prefix=prefix))
    for b in blobs:
        b.delete()
    logger.info("storage.delete_prefix", uri=gcs_prefix_uri, count=len(blobs))
    return len(blobs)


# ---------------------------------------------------------------------------
# Sentinel pattern (idempotency)
# ---------------------------------------------------------------------------

def write_sentinel(gcs_uri: str) -> str:
    """Write an empty blob at the given URI as a completion sentinel; return URI."""
    bucket_name, blob_path = _parse_gcs_uri(gcs_uri)
    client = build_storage_client()
    blob = client.bucket(bucket_name).blob(blob_path)
    blob.upload_from_string("")
    logger.info("storage.write_sentinel", uri=gcs_uri)
    return gcs_uri


def sentinel_exists(gcs_uri: str) -> bool:
    """Return True iff a blob exists at the given URI."""
    bucket_name, blob_path = _parse_gcs_uri(gcs_uri)
    client = build_storage_client()
    blob = client.bucket(bucket_name).blob(blob_path)
    return bool(blob.exists())
