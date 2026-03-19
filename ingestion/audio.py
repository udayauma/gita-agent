"""
Audio extraction module for the Gita Agent ingestion pipeline.

Extracts audio from MP4 video files and converts to mono 16kHz FLAC format,
which is the optimal input format for Google Cloud Speech-to-Text V2 (Chirp 3).

Design reference: docs/detailed_technical_design.md § 3.3

Usage:
    from ingestion.audio import extract_audio

    # Without video_id (standalone usage — uses input filename):
    result = extract_audio(Path("video.mp4"), Path("output/"))
    print(result.output_path)  # output/video.flac

    # With video_id (pipeline usage — creates subdirectory):
    result = extract_audio(Path("video.mp4"), Path("output/"), video_id="nanna_udaya_2025_07_06")
    print(result.output_path)  # output/nanna_udaya_2025_07_06/audio.flac
"""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

# Supported input video extensions
SUPPORTED_EXTENSIONS = {".mp4", ".mkv", ".webm", ".avi", ".mov"}

# Target audio format settings for Chirp 3
TARGET_SAMPLE_RATE = 16000  # 16kHz
TARGET_CHANNELS = 1  # Mono
TARGET_CODEC = "flac"  # Lossless


class AudioExtractionError(Exception):
    """Raised when audio extraction fails due to invalid input or ffmpeg errors."""

    pass


@dataclass
class AudioExtractionResult:
    """Metadata about a completed audio extraction.

    Attributes:
        input_path: Path to the source video file.
        output_path: Path to the extracted FLAC audio file.
        duration_seconds: Duration of the extracted audio in seconds.
        file_size_bytes: Size of the output FLAC file in bytes.
    """

    input_path: Path
    output_path: Path
    duration_seconds: float
    file_size_bytes: int


def validate_input_file(input_path: Path) -> None:
    """Validate that the input file exists, is non-empty, and is a supported format.

    Args:
        input_path: Path to the input video file.

    Raises:
        FileNotFoundError: If the file does not exist.
        AudioExtractionError: If the file is empty or has an unsupported extension.
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if input_path.stat().st_size == 0:
        raise AudioExtractionError(f"Input file is empty (0 bytes): {input_path}")

    if input_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise AudioExtractionError(
            f"Unsupported format '{input_path.suffix}'. "
            f"Supported video formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )


def extract_audio(
    input_path: Path,
    output_dir: Path,
    video_id: str | None = None,
) -> AudioExtractionResult:
    """Extract audio from a video file and convert to mono 16kHz FLAC.

    Runs the ffmpeg command:
        ffmpeg -i input.mp4 -vn -acodec flac -ar 16000 -ac 1 output.flac

    Args:
        input_path: Path to the source video file (MP4, MKV, etc.)
        output_dir: Directory to write the output FLAC file into.
                    Created automatically if it doesn't exist.
        video_id: Optional sanitized identifier for the video. When provided,
                  output is written to output_dir/{video_id}/audio.flac.
                  When omitted, uses input filename: output_dir/{stem}.flac.

    Returns:
        AudioExtractionResult with metadata about the extracted audio.

    Raises:
        FileNotFoundError: If input_path does not exist.
        AudioExtractionError: If input is invalid or ffmpeg fails.
    """
    input_path = Path(input_path)
    output_dir = Path(output_dir)

    # Validate input
    validate_input_file(input_path)

    # Build output path based on whether video_id is provided
    if video_id:
        # Pipeline mode: output_dir/{video_id}/audio.flac
        output_subdir = output_dir / video_id
        output_subdir.mkdir(parents=True, exist_ok=True)
        output_path = output_subdir / "audio.flac"
    else:
        # Standalone mode: output_dir/{input_stem}.flac
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{input_path.stem}.flac"

    logger.info(
        "extracting_audio",
        input_path=str(input_path),
        output_path=str(output_path),
        target_sample_rate=TARGET_SAMPLE_RATE,
        target_channels=TARGET_CHANNELS,
    )

    # Run ffmpeg
    cmd = [
        "ffmpeg",
        "-y",  # Overwrite output if exists
        "-i", str(input_path),
        "-vn",  # Discard video track
        "-acodec", TARGET_CODEC,
        "-ar", str(TARGET_SAMPLE_RATE),
        "-ac", str(TARGET_CHANNELS),
        str(output_path),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 min timeout for large files
        )
    except subprocess.TimeoutExpired:
        raise AudioExtractionError(
            f"ffmpeg timed out after 600s processing: {input_path}"
        )

    if result.returncode != 0:
        raise AudioExtractionError(
            f"ffmpeg failed to extract audio (exit code {result.returncode}). "
            f"stderr: {result.stderr[-500:]}"
        )

    # Verify output was created and is non-empty
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise AudioExtractionError(
            f"ffmpeg produced no output for: {input_path}"
        )

    # Probe the output to get duration
    duration = _probe_duration(output_path)
    file_size = output_path.stat().st_size

    logger.info(
        "audio_extraction_complete",
        output_path=str(output_path),
        duration_seconds=duration,
        file_size_bytes=file_size,
    )

    return AudioExtractionResult(
        input_path=input_path,
        output_path=output_path,
        duration_seconds=duration,
        file_size_bytes=file_size,
    )


def _probe_duration(audio_path: Path) -> float:
    """Use ffprobe to get the duration of an audio file in seconds.

    Args:
        audio_path: Path to the audio file to probe.

    Returns:
        Duration in seconds as a float.
    """
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        str(audio_path),
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return float(data.get("format", {}).get("duration", 0))
    except (subprocess.TimeoutExpired, json.JSONDecodeError, ValueError):
        pass

    logger.warning("ffprobe_duration_fallback", audio_path=str(audio_path))
    return 0.0
