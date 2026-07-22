"""Video motion analysis split into focused, single-responsibility functions."""
from typing import List, Tuple, Callable, Optional

import cv2
import numpy as np
from pathlib import Path
from scipy.signal import find_peaks

from config.config import VideoConfig


def _compute_resize_target(
    original_width: int, original_height: int, target_width: int
) -> Tuple[int, int]:
    """Compute the downscaled resolution, preserving aspect ratio."""
    if original_width <= target_width:
        return original_width, original_height
    scale = target_width / original_width
    return target_width, int(original_height * scale)


def _compute_motion_scores(
    video_path: Path,
    frame_count: int,
    config: VideoConfig,
    on_start: Optional[Callable[[str, int], None]] = None,
    on_progress: Optional[Callable[[int], None]] = None,
    on_finish: Optional[Callable[[], None]] = None,
) -> List[float]:
    """Read the video and compute a per-frame motion magnitude score."""
    cap = cv2.VideoCapture(str(video_path))
    try:
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")

        ret, first_frame = cap.read()
        if not ret:
            raise RuntimeError(f"Cannot read first frame from {video_path}")

        # Notification de démarrage du traitement
        if on_start:
            on_start("Analyzing video motion...", frame_count)

        target_w, target_h = _compute_resize_target(
            first_frame.shape[1], first_frame.shape[0], config.target_width
        )
        prev_gray = cv2.cvtColor(
            cv2.resize(first_frame, (target_w, target_h)), cv2.COLOR_BGR2GRAY
        )

        scores: List[float] = []
        frame_idx = 1

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            small = cv2.resize(frame, (target_w, target_h))
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

            flow = cv2.calcOpticalFlowFarneback(
                prev_gray,
                gray,
                None,
                config.farneback_pyr_scale,
                config.farneback_levels,
                config.farneback_winsize,
                config.farneback_iterations,
                config.farneback_poly_n,
                config.farneback_poly_sigma,
                config.farneback_flags,
            )
            magnitude, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
            scores.append(float(np.sum(magnitude)))
            prev_gray = gray
            frame_idx += 1

            # Mise à jour de la progression vers le Worker (ex: toutes les 5 frames)
            if on_progress and (frame_idx % 5 == 0 or frame_idx == frame_count):
                on_progress(frame_idx)

        # Notification de fin
        if on_finish:
            on_finish()

        return scores
    finally:
        cap.release()


def _detect_motion_peaks(
    scores: np.ndarray, target_count: int, fps: float, min_distance_ms: int
) -> Tuple[np.ndarray, dict]:
    """Find motion peaks, relaxing the distance constraint if too few peaks."""
    min_distance_frames = max(1, int((min_distance_ms / 1000) * fps))
    peaks_indices, properties = find_peaks(scores, distance=min_distance_frames, prominence=0)

    while len(peaks_indices) < target_count and min_distance_frames > 1:
        min_distance_frames = max(1, int(min_distance_frames * 0.8))
        peaks_indices, properties = find_peaks(
            scores, distance=min_distance_frames, prominence=0
        )

    if len(peaks_indices) > target_count:
        prominences = properties["prominences"]
        top_local = np.argsort(prominences)[-target_count:]
        peaks_indices = np.sort(peaks_indices[top_local])

    return peaks_indices, properties


def _ensure_peak_count(
    peaks_indices: np.ndarray, target_count: int, frame_total: int
) -> np.ndarray:
    """Pad with synthetic peaks when the video is too static."""
    if len(peaks_indices) >= target_count:
        return peaks_indices

    missing = target_count - len(peaks_indices)
    fictive = np.linspace(0, frame_total - 1, missing + 2, dtype=int)[1:-1]
    peaks_indices = np.sort(np.unique(np.concatenate([peaks_indices, fictive])))
    while len(peaks_indices) < target_count:
        peaks_indices = np.append(peaks_indices, frame_total - 1)
    return peaks_indices


def get_video_pics(
    video_path: Path,
    frame_count: int,
    fps: float,
    target_count: int,
    config: VideoConfig,
    on_start: Optional[Callable[[str, int], None]] = None,
    on_progress: Optional[Callable[[int], None]] = None,
    on_finish: Optional[Callable[[], None]] = None,
) -> List[int]:
    """Detect the most significant motion peaks in a video.

    Args:
        video_path: Path to the video file.
        frame_count: Total number of frames in the video.
        fps: Frames per second of the video.
        target_count: Desired number of peaks.
        config: Video-analysis parameters.
        on_start: Optional callback function triggered at the beginning.
        on_progress: Optional callback function for progress updates.
        on_finish: Optional callback function triggered when finished.

    Returns:
        List of peak timestamps in milliseconds.
    """
    if fps == 0:
        return []

    scores = _compute_motion_scores(
        video_path=video_path,
        frame_count=frame_count,
        config=config,
        on_start=on_start,
        on_progress=on_progress,
        on_finish=on_finish,
    )
    if not scores:
        return []

    peaks_indices, _ = _detect_motion_peaks(
        np.asarray(scores), target_count, fps, config.min_distance_ms
    )
    peaks_indices = _ensure_peak_count(peaks_indices, target_count, frame_count)
    return [int(round(((idx + 1) / fps) * 1000)) for idx in peaks_indices]