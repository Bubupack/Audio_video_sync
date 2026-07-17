"""Final-video generation: pipe raw frames to FFmpeg."""
import bisect
import logging
import subprocess
from pathlib import Path
from typing import List

import cv2
import numpy as np

from config import RenderConfig
from progress import ProgressBar

logger = logging.getLogger(__name__)


def _build_ffmpeg_command(
    width: int,
    height: int,
    fps: float,
    audio_path: Path,
    output_path: Path,
    config: RenderConfig,
) -> List[str]:
    """Build the FFmpeg command-line used to encode the final video."""
    return [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{width}x{height}",
        "-pix_fmt", "bgr24",
        "-r", str(fps),
        "-i", "-",
        "-i", str(audio_path),
        "-c:v", config.video_codec,
        "-preset", config.preset,
        "-crf", str(config.crf),
        "-c:a", config.audio_codec,
        "-b:a", config.audio_bitrate,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        "-loglevel", "error",
        str(output_path),
    ]


def _write_frame(proc: subprocess.Popen, frame: np.ndarray) -> None:
    """Write a single BGR frame to FFmpeg's stdin, or raise a clear error."""
    stdin = proc.stdin
    if stdin is None or stdin.closed:
        raise BrokenPipeError("FFmpeg stdin is closed (FFmpeg likely crashed).")
    try:
        stdin.write(frame.tobytes())
    except BrokenPipeError as exc:
        raise BrokenPipeError(
            "FFmpeg pipe broke while writing frames."
        ) from exc


def generate_final_video(
    video_path: Path,
    audio_path: Path,
    audio_peaks: List[int],
    video_peaks: List[int],
    audio_duration_ms: int,
    video_duration_ms: int,
    fps: float,
    frame_count: int,
    output_path: Path,
    config: RenderConfig,
) -> None:
    """Generate the final synchronized MKV by piping raw frames to FFmpeg.

    Args:
        video_path: Source video file.
        audio_path: Source audio file.
        audio_peaks: List of audio peak timestamps (ms).
        video_peaks: List of video peak timestamps (ms).
        audio_duration_ms: Total audio duration in milliseconds.
        video_duration_ms: Total video duration in milliseconds.
        fps: Output frame rate.
        frame_count: Total source video frames.
        output_path: Destination file path.
        config: Render configuration.

    Raises:
        RuntimeError: If FFmpeg exits with a non-zero status.
        BrokenPipeError: If FFmpeg dies mid-render.
    """
    cap = cv2.VideoCapture(str(video_path))
    try:
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        a_peaks = [0, *audio_peaks, audio_duration_ms]
        v_peaks = [0, *video_peaks, video_duration_ms]

        total_out_frames = int((audio_duration_ms / 1000) * fps)
        cmd = _build_ffmpeg_command(width, height, fps, audio_path, output_path, config)
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

        current_src_idx = -1
        current_frame: np.ndarray | None = None
        bar = ProgressBar("Rendering", total_out_frames)

        logger.info("Generating final video (direct pipe to FFmpeg)...")

        try:
            for out_idx in range(total_out_frames):
                out_time_ms = (out_idx / fps) * 1000

                segment_idx = bisect.bisect_right(a_peaks, out_time_ms) - 1
                segment_idx = max(0, min(segment_idx, len(a_peaks) - 2))

                t_start_audio, t_end_audio = a_peaks[segment_idx], a_peaks[segment_idx + 1]
                t_start_video, t_end_video = v_peaks[segment_idx], v_peaks[segment_idx + 1]

                dt_audio = t_end_audio - t_start_audio
                ratio = (out_time_ms - t_start_audio) / dt_audio if dt_audio > 0 else 0

                src_time_ms = t_start_video + ratio * (t_end_video - t_start_video)
                src_frame_idx = max(
                    0, min(int(round((src_time_ms / 1000) * fps)), frame_count - 1)
                )

                while current_src_idx < src_frame_idx:
                    ret, frame = cap.read()
                    current_src_idx += 1
                    if ret:
                        current_frame = frame

                if current_frame is not None:
                    _write_frame(proc, current_frame)

                if out_idx % 30 == 0:
                    bar.update(out_idx + 1)
            bar.finish()
        finally:
            if proc.stdin and not proc.stdin.closed:
                try:
                    proc.stdin.close()
                except BrokenPipeError:
                    logger.warning("BrokenPipeError while closing FFmpeg stdin.")

        return_code = proc.wait()
        if return_code != 0:
            raise RuntimeError(
                f"FFmpeg exited with code {return_code}. Output may be corrupted: {output_path}"
            )
    finally:
        cap.release()

    logger.info("Final video generated successfully: %s", output_path)