"""Media metadata retrieval (audio samples + video properties)."""
from dataclasses import dataclass

import cv2
import librosa
import numpy as np
from pathlib import Path

from config import AppConfig


@dataclass
class MediaInfo:
    """Container for media-related information required downstream."""
    audio_samples: np.ndarray
    sample_rate: int
    audio_duration_ms: int
    video_duration_ms: int
    fps: float
    frame_count: int


def get_media_info(audio_path: Path, video_path: Path, _config: AppConfig) -> MediaInfo:
    """Load audio samples and probe the video container.

    Args:
        audio_path: Path to the audio file.
        video_path: Path to the video file.
        _config: Application configuration (reserved for future use).

    Returns:
        A :class:`MediaInfo` populated with both audio and video metadata.

    Raises:
        RuntimeError: If the video cannot be opened.
    """
    samples, sample_rate = librosa.load(str(audio_path), sr=None)
    audio_duration_ms = int(len(samples) / sample_rate * 1000)

    cap = cv2.VideoCapture(str(video_path))
    try:
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        video_duration_ms = int(frame_count / fps * 1000) if fps > 0 else 0
    finally:
        cap.release()

    return MediaInfo(
        audio_samples=samples,
        sample_rate=sample_rate,
        audio_duration_ms=audio_duration_ms,
        video_duration_ms=video_duration_ms,
        fps=fps,
        frame_count=frame_count,
    )