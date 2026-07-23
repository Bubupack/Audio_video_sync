"""Video motion analysis split into focused, single-responsibility functions."""
from pathlib import Path
from typing import Callable, List, Optional, Tuple

import av
import cv2
import numpy as np
from scipy.signal import find_peaks

from config.config import MS_PER_SECOND, VideoConfig


def _compute_resize_target(
    original_width: int, original_height: int, target_width: int
) -> Tuple[int, int]:
    """Compute downscaled resolution while preserving aspect ratio."""
    if original_width <= target_width:
        return original_width, original_height
    scale = target_width / original_width
    return target_width, int(original_height * scale)


def _extract_grayscale_frame(av_frame: av.VideoFrame) -> np.ndarray:
    """Extract grayscale array safely with zero-copy Y-plane extraction when possible."""
    # YUV formats (yuv420p, nv12, yuv422p, etc.) store luminance directly in plane 0
    if "yuv" in av_frame.format.name or "nv" in av_frame.format.name:
        # Extract Y-plane memory block as an uint8 array
        y_plane = np.frombuffer(av_frame.planes[0], dtype=np.uint8)

        # Account for potential memory padding (line stride) and slice to actual width
        line_stride = av_frame.planes[0].line_size
        y_frame = y_plane.reshape((av_frame.height, line_stride))

        return y_frame[:, : av_frame.width]

    # Fallback conversion for non-YUV color spaces (RGB, RGBA, etc.)
    return av_frame.to_ndarray(format="gray")


def _compute_motion_scores(
    video_path: Path,
    frame_count: int,
    config: VideoConfig,
    on_start: Optional[Callable[[str, int], None]] = None,
    on_progress: Optional[Callable[[int], None]] = None,
    on_finish: Optional[Callable[[], None]] = None,
) -> List[float]:
    """Read video via PyAV and calculate Farneback optical flow motion scores."""
    try:
        container = av.open(str(video_path))
    except Exception as err:
        raise RuntimeError(f"Cannot open video: {video_path}") from err

    try:
        if not container.streams.video:
            raise RuntimeError(f"No video stream found in: {video_path}")

        stream = container.streams.video[0]
        stream.thread_type = "AUTO"

        frame_iterator = container.decode(stream)

        try:
            first_av_frame = next(frame_iterator)
        except (StopIteration, av.AVError) as err:
            raise RuntimeError(f"Cannot read first frame from {video_path}") from err

        if on_start:
            on_start("Analyzing video motion", frame_count)

        first_gray = _extract_grayscale_frame(first_av_frame)
        target_w, target_h = _compute_resize_target(
            first_av_frame.width, first_av_frame.height, config.target_width
        )
        prev_gray = cv2.resize(first_gray, (target_w, target_h))

        scores: List[float] = []
        frame_idx = 1

        for av_frame in frame_iterator:
            frame_idx += 1

            # Skip intermediate frames to lower CPU load according to stride setting
            if (frame_idx % config.frame_stride) != 0:
                continue

            gray_frame = _extract_grayscale_frame(av_frame)
            gray = cv2.resize(gray_frame, (target_w, target_h))

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

            if on_progress and (
                frame_idx % config.progress_interval == 0 or frame_idx == frame_count
            ):
                on_progress(frame_idx)

        if on_finish:
            on_finish()

        return scores
    finally:
        container.close()


def _detect_motion_peaks(
    scores: np.ndarray, target_count: int, fps: float, config: VideoConfig
) -> Tuple[np.ndarray, dict]:
    """Find motion peaks, iteratively relaxing the distance constraint if needed."""
    min_distance_frames = max(1, int((config.min_distance_ms / MS_PER_SECOND) * fps))
    peaks_indices, properties = find_peaks(
        scores, distance=min_distance_frames, prominence=config.peak_prominence
    )

    while len(peaks_indices) < target_count and min_distance_frames > 1:
        min_distance_frames = max(
            1, int(min_distance_frames * config.peak_relaxation_factor)
        )
        peaks_indices, properties = find_peaks(
            scores, distance=min_distance_frames, prominence=config.peak_prominence
        )

    if len(peaks_indices) > target_count:
        prominences = properties["prominences"]
        top_local = np.argsort(prominences)[-target_count:]
        peaks_indices = np.sort(peaks_indices[top_local])

    return peaks_indices, properties


def _ensure_peak_count(
    peaks_indices: np.ndarray, target_count: int, frame_total: int
) -> np.ndarray:
    """Pad peak index array with evenly spaced synthetic indices if necessary."""
    if len(peaks_indices) >= target_count:
        return peaks_indices

    missing = target_count - len(peaks_indices)
    # Generate evenly spaced synthetic peaks, excluding boundary frames
    fictive = np.linspace(0, frame_total - 1, missing + 2, dtype=int)[1:-1]
    peaks_indices = np.sort(np.unique(np.concatenate([peaks_indices, fictive])))

    # Fallback padding if unique values did not yield sufficient indices
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
    """Detect the most significant motion peak timestamps (in ms) in a video sequence.

    Args:
        video_path: Path to the video file.
        frame_count: Total frame count in the video.
        fps: Frames per second of the video stream.
        target_count: Desired number of peaks to select.
        config: Video analysis configuration parameters.
        on_start: Optional callback triggered on process initialization.
        on_progress: Optional progress update callback.
        on_finish: Optional callback triggered upon task completion.

    Returns:
        A list of peak timestamps expressed in milliseconds.
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
        np.asarray(scores), target_count, fps, config
    )
    peaks_indices = _ensure_peak_count(peaks_indices, target_count, frame_count)

    # Convert peak frame indices to millisecond timestamps
    return [
        int(round(((idx + 1) / fps) * MS_PER_SECOND)) for idx in peaks_indices
    ]