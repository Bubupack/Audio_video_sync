"""Small utility helpers shared across modules."""
import re
from pathlib import Path
from typing import Optional
from PyQt6.QtGui import QImage, QPixmap
import cv2
import base64
from mutagen import File
from mutagen.flac import Picture
import logging
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

def _read_video_cover_bytes(video_path: str) -> Optional[bytes]:
    """Tente d'extraire les octets d'une pochette/miniature intégrée dans les métadonnées de la vidéo."""
    try:
        video = File(video_path)
        if video is None:
            return None

        # 1. MP4 / MOV (atome 'covr')
        tags = getattr(video, "tags", None) or video
        if tags and "covr" in tags:
            return bytes(tags["covr"][0])

        # 2. Images natives / pièces jointes (ex: MKV, OGV)
        if hasattr(video, "pictures") and video.pictures:
            preferred = next((p for p in video.pictures if p.type == 3), None)
            return (preferred or video.pictures[0]).data

        # 3. Trame ID3 APIC (si présente dans certains conteneurs)
        if tags and hasattr(tags, "keys"):
            for key in tags.keys():
                if key.startswith("APIC"):
                    return tags[key].data

        # 4. Bloc d'image Vorbis/FLAC encodé en Base64
        if "metadata_block_picture" in video:
            raw = base64.b64decode(video["metadata_block_picture"][0])
            return Picture(raw).data

    except Exception:
        logger.debug("Aucune métadonnée d'image trouvée dans %s", video_path)

    return None


def extract_video_thumbnail(video_path: str) -> Optional[QPixmap]:
    """Extrait la pochette/miniature intégrée de la vidéo si elle existe.

    Si aucune pochette n'est trouvée, extrait la première image (frame) de la vidéo via OpenCV.
    """
    # ------------------------------------------------------------------
    # 1. Tentative d'extraction depuis les métadonnées du fichier
    # ------------------------------------------------------------------
    cover_bytes = _read_video_cover_bytes(video_path)
    if cover_bytes:
        pixmap = QPixmap()
        if pixmap.loadFromData(cover_bytes):
            return pixmap

    # ------------------------------------------------------------------
    # 2. Fallback : Capture de la première frame de la vidéo via OpenCV
    # ------------------------------------------------------------------
    try:
        cap = cv2.VideoCapture(video_path)
        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            return None

        # Conversion BGR (OpenCV) vers RGB (Qt)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w

        q_image = QImage(
            frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888
        )
        return QPixmap.fromImage(q_image)

    except Exception as exc:
        logger.error("Échec de l'extraction de la frame vidéo pour %s: %s", video_path, exc)
        return None