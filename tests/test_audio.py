"""
Tests for ingestion/audio.py — Audio extraction module.

TDD Phase: RED — these tests are written before the implementation.
The audio extractor converts MP4 video files to mono 16kHz FLAC audio
using ffmpeg, which is the required format for Chirp 3 Speech-to-Text.

Design reference: docs/detailed_technical_design.md § 3.3
"""

import os
import json
import struct
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from ingestion.audio import (
    extract_audio,
    validate_input_file,
    AudioExtractionError,
    AudioExtractionResult,
)


# ---------------------------------------------------------------------------
# Fixtures: Create minimal valid/invalid test media files
# ---------------------------------------------------------------------------

@pytest.fixture
def valid_mp4(tmp_path):
    """Create a minimal valid MP4 file with a silent audio track using ffmpeg.

    This generates a 2-second silent video so we have a real MP4 to test against.
    """
    output = tmp_path / "test_valid.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-f", "lavfi", "-i", "color=c=black:s=320x240:r=1",
        "-t", "2",
        "-c:v", "libx264", "-c:a", "aac",
        "-shortest",
        str(output),
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=30)
    assert result.returncode == 0, f"ffmpeg failed to create test MP4: {result.stderr.decode()}"
    assert output.exists() and output.stat().st_size > 0
    return output


@pytest.fixture
def corrupt_mp4(tmp_path):
    """Create a file that looks like an MP4 but contains garbage data."""
    output = tmp_path / "corrupt.mp4"
    output.write_bytes(b"\x00\x00\x00\x1cftypisom" + os.urandom(512))
    return output


@pytest.fixture
def empty_file(tmp_path):
    """Create an empty file with .mp4 extension."""
    output = tmp_path / "empty.mp4"
    output.write_bytes(b"")
    return output


@pytest.fixture
def silent_mp4(tmp_path):
    """Create an MP4 with a video track but only silence for audio."""
    output = tmp_path / "silent.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-f", "lavfi", "-i", "color=c=black:s=320x240:r=1",
        "-t", "3",
        "-c:v", "libx264", "-c:a", "aac",
        "-shortest",
        str(output),
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=30)
    assert result.returncode == 0
    return output


@pytest.fixture
def non_mp4_file(tmp_path):
    """Create a plain text file with wrong extension."""
    output = tmp_path / "readme.txt"
    output.write_text("This is not a video file.")
    return output


@pytest.fixture
def output_dir(tmp_path):
    """Provide a clean output directory."""
    out = tmp_path / "output"
    out.mkdir()
    return out


# ---------------------------------------------------------------------------
# 4.1.1 — Happy Path: Valid MP4 produces valid FLAC
# ---------------------------------------------------------------------------

class TestExtractAudioHappyPath:
    """Tests for successful audio extraction from valid MP4 files."""

    def test_extract_audio_produces_flac_file(self, valid_mp4, output_dir):
        """Extraction should produce a .flac file in the output directory."""
        result = extract_audio(valid_mp4, output_dir)
        assert result.output_path.exists()
        assert result.output_path.suffix == ".flac"

    def test_extract_audio_output_is_mono(self, valid_mp4, output_dir):
        """Output FLAC must be mono (1 channel) per Chirp 3 requirements."""
        result = extract_audio(valid_mp4, output_dir)
        probe = _ffprobe_audio(result.output_path)
        assert probe["channels"] == 1

    def test_extract_audio_output_is_16khz(self, valid_mp4, output_dir):
        """Output FLAC must be 16kHz sample rate per Chirp 3 requirements."""
        result = extract_audio(valid_mp4, output_dir)
        probe = _ffprobe_audio(result.output_path)
        assert probe["sample_rate"] == 16000

    def test_extract_audio_output_is_flac_codec(self, valid_mp4, output_dir):
        """Output must use FLAC codec (lossless, optimal for STT)."""
        result = extract_audio(valid_mp4, output_dir)
        probe = _ffprobe_audio(result.output_path)
        assert probe["codec"] == "flac"

    def test_extract_audio_returns_result_with_metadata(self, valid_mp4, output_dir):
        """Result object should contain useful metadata about the extraction."""
        result = extract_audio(valid_mp4, output_dir)
        assert isinstance(result, AudioExtractionResult)
        assert result.input_path == valid_mp4
        assert result.output_path.exists()
        assert result.duration_seconds > 0
        assert result.file_size_bytes > 0

    def test_extract_audio_preserves_duration(self, valid_mp4, output_dir):
        """Output audio duration should approximately match input video duration."""
        result = extract_audio(valid_mp4, output_dir)
        # 2-second test video — allow ±0.5s tolerance for encoding
        assert 1.0 <= result.duration_seconds <= 3.0

    def test_extract_audio_output_filename_matches_input(self, valid_mp4, output_dir):
        """Output filename should be derived from input filename when no video_id."""
        result = extract_audio(valid_mp4, output_dir)
        assert result.output_path.stem == valid_mp4.stem


# ---------------------------------------------------------------------------
# 4.1.2 — video_id support (pipeline mode)
# ---------------------------------------------------------------------------

class TestExtractAudioWithVideoId:
    """Tests for the video_id parameter used in the ingestion pipeline."""

    def test_video_id_creates_subdirectory(self, valid_mp4, output_dir):
        """When video_id is provided, output goes into output_dir/{video_id}/."""
        result = extract_audio(valid_mp4, output_dir, video_id="nanna_udaya_2025_07_06")
        assert result.output_path.parent.name == "nanna_udaya_2025_07_06"

    def test_video_id_output_named_audio_flac(self, valid_mp4, output_dir):
        """When video_id is provided, output file is always named 'audio.flac'."""
        result = extract_audio(valid_mp4, output_dir, video_id="nanna_udaya_2025_07_06")
        assert result.output_path.name == "audio.flac"

    def test_video_id_full_path_structure(self, valid_mp4, output_dir):
        """Full output path should be output_dir/video_id/audio.flac."""
        vid = "nanna_udaya_2025_07_06"
        result = extract_audio(valid_mp4, output_dir, video_id=vid)
        expected = output_dir / vid / "audio.flac"
        assert result.output_path == expected

    def test_video_id_produces_valid_flac(self, valid_mp4, output_dir):
        """Output with video_id should still be valid mono 16kHz FLAC."""
        result = extract_audio(valid_mp4, output_dir, video_id="test_session")
        probe = _ffprobe_audio(result.output_path)
        assert probe["codec"] == "flac"
        assert probe["sample_rate"] == 16000
        assert probe["channels"] == 1

    def test_multiple_video_ids_no_collision(self, valid_mp4, output_dir):
        """Different video_ids produce separate subdirectories, no overwriting."""
        r1 = extract_audio(valid_mp4, output_dir, video_id="session_a")
        r2 = extract_audio(valid_mp4, output_dir, video_id="session_b")
        assert r1.output_path != r2.output_path
        assert r1.output_path.exists()
        assert r2.output_path.exists()

    def test_without_video_id_uses_input_stem(self, valid_mp4, output_dir):
        """Without video_id, should fall back to input filename behavior."""
        result = extract_audio(valid_mp4, output_dir)
        assert result.output_path.stem == valid_mp4.stem
        assert result.output_path.parent == output_dir


# ---------------------------------------------------------------------------
# 4.1.3 — Error Handling: Corrupt, empty, and missing files
# ---------------------------------------------------------------------------

class TestExtractAudioErrorHandling:
    """Tests for proper error handling on invalid inputs."""

    def test_extract_audio_rejects_corrupt_mp4(self, corrupt_mp4, output_dir):
        """Corrupt MP4 should raise AudioExtractionError, not crash."""
        with pytest.raises(AudioExtractionError, match="(?i)extract|corrupt|invalid"):
            extract_audio(corrupt_mp4, output_dir)

    def test_extract_audio_rejects_empty_file(self, empty_file, output_dir):
        """Empty file should raise AudioExtractionError."""
        with pytest.raises(AudioExtractionError, match="(?i)empty|invalid|size"):
            extract_audio(empty_file, output_dir)

    def test_extract_audio_rejects_nonexistent_file(self, output_dir):
        """Non-existent file should raise FileNotFoundError."""
        fake_path = Path("/tmp/does_not_exist_at_all.mp4")
        with pytest.raises(FileNotFoundError):
            extract_audio(fake_path, output_dir)

    def test_extract_audio_rejects_non_video_file(self, non_mp4_file, output_dir):
        """Non-video file (e.g., .txt) should raise AudioExtractionError."""
        with pytest.raises(AudioExtractionError, match="(?i)unsupported|format|video"):
            extract_audio(non_mp4_file, output_dir)

    def test_extract_audio_creates_output_dir_if_missing(self, valid_mp4, tmp_path):
        """If output directory doesn't exist, it should be created automatically."""
        new_output = tmp_path / "new_subdir" / "audio"
        result = extract_audio(valid_mp4, new_output)
        assert new_output.exists()
        assert result.output_path.exists()


# ---------------------------------------------------------------------------
# 4.1.3 — Edge Cases: Silent tracks, overwrite behavior
# ---------------------------------------------------------------------------

class TestExtractAudioEdgeCases:
    """Tests for edge cases in audio extraction."""

    def test_extract_audio_handles_silent_track(self, silent_mp4, output_dir):
        """Silent audio track should still produce a valid FLAC (silence is valid data)."""
        result = extract_audio(silent_mp4, output_dir)
        assert result.output_path.exists()
        assert result.file_size_bytes > 0

    def test_extract_audio_overwrites_existing_output(self, valid_mp4, output_dir):
        """If output file already exists, it should be overwritten."""
        # First extraction
        result1 = extract_audio(valid_mp4, output_dir)
        size1 = result1.file_size_bytes

        # Second extraction — should overwrite, not error
        result2 = extract_audio(valid_mp4, output_dir)
        assert result2.output_path.exists()
        assert result2.file_size_bytes > 0


# ---------------------------------------------------------------------------
# 4.1.4 — Input Validation (standalone function)
# ---------------------------------------------------------------------------

class TestValidateInputFile:
    """Tests for the input validation helper function."""

    def test_validate_accepts_valid_mp4(self, valid_mp4):
        """Valid MP4 file should pass validation without error."""
        validate_input_file(valid_mp4)  # Should not raise

    def test_validate_rejects_nonexistent(self):
        """Non-existent path should fail validation."""
        with pytest.raises(FileNotFoundError):
            validate_input_file(Path("/tmp/nope.mp4"))

    def test_validate_rejects_empty(self, empty_file):
        """Empty file should fail validation."""
        with pytest.raises(AudioExtractionError, match="(?i)empty|size"):
            validate_input_file(empty_file)

    def test_validate_rejects_unsupported_extension(self, non_mp4_file):
        """Non-video extensions should fail validation."""
        with pytest.raises(AudioExtractionError, match="(?i)unsupported|format"):
            validate_input_file(non_mp4_file)


# ---------------------------------------------------------------------------
# Helper: Probe audio file properties via ffprobe
# ---------------------------------------------------------------------------

def _ffprobe_audio(audio_path: Path) -> dict:
    """Use ffprobe to inspect audio file properties.

    Returns dict with keys: codec, sample_rate, channels, duration.
    """
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-select_streams", "a:0",
        str(audio_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, f"ffprobe failed: {result.stderr}"
    data = json.loads(result.stdout)
    stream = data["streams"][0]
    return {
        "codec": stream["codec_name"],
        "sample_rate": int(stream["sample_rate"]),
        "channels": int(stream["channels"]),
        "duration": float(stream.get("duration", 0)),
    }
