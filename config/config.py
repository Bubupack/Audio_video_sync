"""Configuration constants and dataclasses for the application.

Centralizes all tunable parameters (magic numbers, codec settings, etc.)
into immutable, well-typed configuration objects.
"""
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

# --- Time Conversion ---
MS_PER_SECOND: Final[int] = 1000

# --- Farneback optical-flow parameters ---
FARNEBACK_PYR_SCALE: Final[float] = 0.5
FARNEBACK_LEVELS: Final[int] = 3
FARNEBACK_WINSIZE: Final[int] = 15
FARNEBACK_ITERATIONS: Final[int] = 3
FARNEBACK_POLY_N: Final[int] = 5
FARNEBACK_POLY_SIGMA: Final[float] = 1.2
FARNEBACK_FLAGS: Final[int] = 0

# --- Motion Analysis Defaults ---
DEFAULT_TARGET_WIDTH: Final[int] = 256
DEFAULT_FRAME_STRIDE: Final[int] = 2
DEFAULT_PROGRESS_INTERVAL: Final[int] = 10
DEFAULT_PEAK_RELAXATION_FACTOR: Final[float] = 0.8
DEFAULT_PEAK_PROMINENCE: Final[float] = 0.0

# --- Defaults ---
DEFAULT_AUDIO_MIN_DISTANCE_MS: Final[int] = 400
DEFAULT_VIDEO_MIN_DISTANCE_MS: Final[int] = 500
DEFAULT_PROMINENCE_FACTOR: Final[float] = 0.5
DEFAULT_CRF: Final[int] = 18
DEFAULT_PRESET: Final[str] = "fast"
DEFAULT_AUDIO_BITRATE: Final[str] = "192k"
DEFAULT_OUTPUT_DIR: Final[str] = str(Path("output").resolve())

# --- Filesystem constraints ---
FILESYSTEM_MAX_STEM_LENGTH: Final[int] = 100
INVALID_FILENAME_CHARS_REGEX: Final[re.Pattern] = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

# --- Supported Extensions (FFmpeg & PyQt6 QMediaPlayer compatible) ---
VALID_AUDIO_EXTS: Final[set[str]] = {
    ".mp3", ".wav", ".flac", ".aac", ".ogg", ".oga", ".m4a", ".opus",
    ".wma", ".aiff"
}

VALID_VIDEO_EXTS: Final[set[str]] = {
    ".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".mpg", ".mpeg",
    ".ts", ".3gp"
}


@dataclass
class AudioConfig:
    """Parameters for audio onset-peak detection."""
    min_distance_ms: int = DEFAULT_AUDIO_MIN_DISTANCE_MS
    prominence_factor: float = DEFAULT_PROMINENCE_FACTOR


@dataclass
class VideoConfig:
    """Parameters for video motion analysis via Farneback optical flow."""
    target_width: int = DEFAULT_TARGET_WIDTH
    min_distance_ms: int = DEFAULT_VIDEO_MIN_DISTANCE_MS
    frame_stride: int = DEFAULT_FRAME_STRIDE
    progress_interval: int = DEFAULT_PROGRESS_INTERVAL
    peak_relaxation_factor: float = DEFAULT_PEAK_RELAXATION_FACTOR
    peak_prominence: float = DEFAULT_PEAK_PROMINENCE
    farneback_pyr_scale: float = FARNEBACK_PYR_SCALE
    farneback_levels: int = FARNEBACK_LEVELS
    farneback_winsize: int = FARNEBACK_WINSIZE
    farneback_iterations: int = FARNEBACK_ITERATIONS
    farneback_poly_n: int = FARNEBACK_POLY_N
    farneback_poly_sigma: float = FARNEBACK_POLY_SIGMA
    farneback_flags: int = FARNEBACK_FLAGS


@dataclass
class RenderConfig:
    """Parameters for the FFmpeg encoding pipeline."""
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    crf: int = DEFAULT_CRF
    preset: str = DEFAULT_PRESET
    audio_bitrate: str = DEFAULT_AUDIO_BITRATE
    container: str = "mkv"


@dataclass
class AppConfig:
    """Top-level application configuration."""
    audio: AudioConfig = field(default_factory=AudioConfig)
    video: VideoConfig = field(default_factory=VideoConfig)
    render: RenderConfig = field(default_factory=RenderConfig)
    output_dir: Path = field(default_factory=lambda: Path(DEFAULT_OUTPUT_DIR))