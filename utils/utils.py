"""Small utility helpers shared across modules."""
from __future__ import annotations

import base64
import logging
import re
from pathlib import Path
from typing import Optional

import shutil
import cv2
from PyQt6.QtGui import QImage, QPixmap
from mutagen import File
from mutagen.flac import Picture

from config.config import (
    FILESYSTEM_MAX_STEM_LENGTH,
    INVALID_FILENAME_CHARS_REGEX,
)

logger = logging.getLogger(__name__)


def format_time(seconds: float) -> str:
    """Format a duration in seconds into a human-readable string.

    Args:
        seconds: Duration in seconds. Negative values produce "N/A".

    Returns:
        A formatted string like "02m 05s" or "01h 15m 02s".
    """
    if seconds < 0:
        return "N/A"
    seconds = int(seconds)
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}h {minutes:02d}m {sec:02d}s"
    if minutes > 0:
        return f"{minutes:02d}m {sec:02d}s"
    return f"{sec:02d}s"


def validate_input_file(path: Path, valid_extensions: set[str], kind: str) -> None:
    """Ensure an input file exists and has a valid extension.

    Args:
        path: Path to the file.
        valid_extensions: Allowed lowercase extensions (e.g. {".mp3", ".wav"}).
        kind: Human label ("audio"/"video") used in error messages.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file extension is not allowed.
    """
    if not path.exists():
        raise FileNotFoundError(f"{kind.capitalize()} file not found: {path}")
    if path.suffix.lower() not in valid_extensions:
        raise ValueError(
            f"Invalid {kind} extension '{path.suffix}'. "
            f"Allowed: {sorted(valid_extensions)}"
        )


def sanitize_filename(stem: str, max_length: int = FILESYSTEM_MAX_STEM_LENGTH) -> str:
    """Sanitize a filename stem for cross-platform safety.

    - Replaces spaces with underscores.
    - Removes special characters invalid on Windows.
    - Truncates the name equally (preserving start and end) if too long.

    Args:
        stem: The original file name without extension.
        max_length: Maximum allowed length for the stem.

    Returns:
        A safe, sanitized string.
    """
    if not stem:
        return "output"

    # 1. Replace spaces with underscores
    safe_stem = stem.replace(" ", "_")
    
    # 2. Remove invalid special characters
    safe_stem = INVALID_FILENAME_CHARS_REGEX.sub("", safe_stem)
    
    # 3. Clean up multiple/border dots and underscores
    safe_stem = re.sub(r"_+", "_", safe_stem).strip("._")
    
    if not safe_stem:
        return "output"

    # 4. Intelligent equal truncation if the name is too long
    if len(safe_stem) > max_length:
        half = (max_length - 1) // 2
        safe_stem = f"{safe_stem[:half]}_sync_{safe_stem[-half:]}"
        
    return safe_stem


def get_unique_output_path(directory: Path, stem: str, suffix: str) -> Path:
    """Generate a unique file path, appending a number if the file already exists.

    Args:
        directory: Target directory.
        stem: The sanitized file name without extension.
        suffix: The file extension (e.g., ".mkv").

    Returns:
        A unique, non-existing Path.
    """
    directory.mkdir(parents=True, exist_ok=True)
    base_path = directory / f"{stem}{suffix}"
    
    if not base_path.exists():
        return base_path
        
    counter = 1
    while True:
        new_path = directory / f"{stem}_{counter}{suffix}"
        if not new_path.exists():
            return new_path
        counter += 1


def extract_embedded_cover(file_path: str) -> Optional[bytes]:
    """Extract raw cover-art bytes from any media file supported by mutagen.

    Supports:
    1. Native pictures (FLAC, OGG with METADATA_BLOCK_PICTURE).
    2. ID3 APIC frames (MP3).
    3. MP4 'covr' atom.
    4. Base64-encoded FLAC picture in Vorbis comments.

    Args:
        file_path: Path to the media file.

    Returns:
        Raw image bytes if a cover is found, otherwise None.
    """
    try:
        media = File(file_path)
        if media is None:
            return None

        # 1. Native pictures (FLAC, OGG with METADATA_BLOCK_PICTURE)
        if hasattr(media, "pictures") and media.pictures:
            # Prefer front cover (type 3), fallback to first available
            preferred = next((p for p in media.pictures if p.type == 3), None)
            return (preferred or media.pictures[0]).data

        # 2. ID3 APIC frames (MP3)
        if media.tags and hasattr(media.tags, "keys"):
            for key in media.tags.keys():
                if key.startswith("APIC"):
                    return media.tags[key].data

        # 3. MP4 'covr' atom
        tags = media.tags if (hasattr(media, "tags") and media.tags) else media
        if tags and "covr" in tags:
            return bytes(tags["covr"][0])

        # 4. Base64-encoded FLAC picture in Vorbis comments
        if "metadata_block_picture" in media:
            raw = base64.b64decode(media["metadata_block_picture"][0])
            return Picture(raw).data

    except Exception:
        logger.debug("No embedded cover art found in %s", file_path)

    return None


def extract_video_thumbnail(video_path: str) -> Optional[QPixmap]:
    """Extract the embedded cover art or capture the first video frame.

    Tries to read an embedded cover from metadata first. If none is found,
    falls back to capturing the first frame of the video via OpenCV.

    Args:
        video_path: Path to the video file.

    Returns:
        A QPixmap of the cover/thumbnail, or None if extraction fails.
    """
    # 1. Attempt extraction from file metadata
    cover_bytes = extract_embedded_cover(video_path)
    if cover_bytes:
        pixmap = QPixmap()
        if pixmap.loadFromData(cover_bytes):
            return pixmap

    # 2. Fallback: Capture the first frame via OpenCV
    try:
        cap = cv2.VideoCapture(video_path)
        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            return None

        # Convert BGR (OpenCV) to RGB (Qt)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w

        # Create QImage from numpy array buffer
        q_image = QImage(
            frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888
        )
        # CRITICAL: Copy the image data so it remains valid if the numpy
        # array is garbage-collected before the QPixmap is displayed.
        return QPixmap.fromImage(q_image.copy())

    except Exception as exc:
        logger.error("Failed to extract video frame for %s: %s", video_path, exc)
        return None


def is_ffmpeg_available() -> bool:
    """Check if the FFmpeg executable is accessible within the system PATH.

    Returns:
        bool: True if ffmpeg executable is found, False otherwise.
    """
    return shutil.which("ffmpeg") is not None