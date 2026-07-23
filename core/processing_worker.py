# workers/processing_worker.py
"""Background worker for executing the synchronization pipeline."""
import time
import logging
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

from core.audio_analysis import get_audio_peaks
from config.config import VALID_AUDIO_EXTS, VALID_VIDEO_EXTS, AppConfig
from core.media_info import get_media_info
from core.renderer import generate_final_video
from utils.utils import validate_input_file, sanitize_filename, get_unique_output_path, format_time
from core.video_analysis import get_video_pics

logger = logging.getLogger(__name__)

# Progress phase boundaries (in percentage)
PROGRESS_INIT = 0
PROGRESS_AUDIO_START = 4
PROGRESS_VIDEO_START = 5
PROGRESS_VIDEO_END = 52
PROGRESS_RENDER_START = 52
PROGRESS_RENDER_END = 99
PROGRESS_DONE = 100


class ProcessingWorker(QObject):
    """Performs heavy computations in a background thread."""

    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, video_path: str | Path, audio_path: str | Path, output_dir: str | Path) -> None:
        super().__init__()
        self.video_path = Path(video_path)
        self.audio_path = Path(audio_path)
        self.output_dir = Path(output_dir)

        self.current_status: str | None = None
        self.current_progress = 0
        self.process_total_frames = 0  # Total number of frames to process, used for progress tracking
        self.start_time: float | None = None

    def run(self) -> None:
        """Method executed in the secondary thread."""
        try:
            output_path = self.run_pipeline()
            logger.info("Final video saved at: %s", output_path.resolve())
            
            self.current_progress = PROGRESS_DONE
            self.progress.emit(PROGRESS_DONE)
            self.current_status = "Finished"
            self.status.emit("Finished")
            self.finished.emit(str(output_path.resolve()))
            
        except FileNotFoundError as e:
            logger.error("Input file error: %s", e)
            self.error.emit(f"Input file error: {e}")
        except ValueError as e:
            logger.error("Validation error: %s", e)
            self.error.emit(f"Validation error: {e}")
        except BrokenPipeError as e:
            logger.error("Pipe error: %s", e)
            self.error.emit(f"Pipe error: {e}")
        except RuntimeError as e:
            logger.error("Processing error: %s", e)
            self.error.emit(f"Processing error: {e}")
        except Exception as e:  # noqa: BLE001 — top-level safety net
            logger.exception("Unexpected error: %s", e)
            self.error.emit(f"Unexpected error: {e}")

    def run_pipeline(self) -> Path:
        """Execute the full synchronization pipeline.

        Returns:
            Path to the generated output file.
        """
        validate_input_file(self.audio_path, VALID_AUDIO_EXTS, "audio")
        validate_input_file(self.video_path, VALID_VIDEO_EXTS, "video")

        self.output_dir.mkdir(parents=True, exist_ok=True)
        config = AppConfig(output_dir=self.output_dir)

        self._update_progress(PROGRESS_INIT, "Loading media information")
        media = get_media_info(self.audio_path, self.video_path, config)

        ratio = (
            media.video_duration_ms / media.audio_duration_ms
            if media.audio_duration_ms > 0
            else 1
        )
        config.video.min_distance_ms = max(
            100, min(int(config.audio.min_distance_ms * ratio), 2000)
        )

        self._update_progress(PROGRESS_AUDIO_START, "Analyzing audio")
        audio_peaks = get_audio_peaks(media.audio_samples, media.sample_rate, config.audio)
        target_count = len(audio_peaks)

        self.current_status = "Analyzing video motion"
        self.status.emit("Analyzing video motion")
        logger.info("Analyzing video motion")

        video_peaks = get_video_pics(
            self.video_path,
            media.frame_count,
            media.fps,
            target_count,
            config.video,
            on_start=self.set_progressing,
            on_progress=self.update_progress,
            on_finish=self.finished_progress,
        )

        self._update_progress(PROGRESS_RENDER_START, "Generating final video")

        # --- SECURE NAMING LOGIC ---
        raw_stem = f"{self.video_path.stem}_sync_{self.audio_path.stem}"
        safe_stem = sanitize_filename(raw_stem)
        
        output_path = get_unique_output_path(
            directory=self.output_dir,
            stem=safe_stem,
            suffix=f".{config.render.container}"
        )

        generate_final_video(
            self.video_path,
            self.audio_path,
            audio_peaks,
            video_peaks,
            media.audio_duration_ms,
            media.video_duration_ms,
            media.fps,
            media.frame_count,
            output_path,
            config.render,
            on_start=self.set_progressing,
            on_progress=self.update_progress,
            on_finish=self.finished_progress,
        )

        self._update_progress(PROGRESS_RENDER_END, "Saving the video")
        
        return output_path

    def update_progress(self, current_frame: int) -> None:
        """Callback for progress updates during video processing and rendering."""
        if not self.start_time or self.process_total_frames == 0:
            return

        elapsed = time.time() - self.start_time
        progress_ratio = current_frame / self.process_total_frames
        eta = (elapsed / progress_ratio - elapsed) if progress_ratio > 0 else 0
        
        self.status.emit(
            f"{self.current_status}: {current_frame}/{self.process_total_frames} "
            f"({progress_ratio*100:.1f}%) - Time: {format_time(elapsed)}/{format_time(elapsed + eta)}"
        )

        # Calculate global progress based on the current phase
        if self.current_progress < PROGRESS_RENDER_START:
            self.current_progress = PROGRESS_VIDEO_START + int(
                progress_ratio * (PROGRESS_VIDEO_END - PROGRESS_VIDEO_START)
            )
        else:
            self.current_progress = PROGRESS_RENDER_START + int(
                progress_ratio * (PROGRESS_RENDER_END - PROGRESS_RENDER_START)
            )

        self.progress.emit(self.current_progress)

    def set_progressing(self, label: str, total: int) -> None:
        """Callback triggered when a processing phase starts."""
        self.current_status = label
        self.status.emit(label)
        self.process_total_frames = max(1, total)
        self.start_time = time.time()

    def finished_progress(self) -> None:
        """Callback triggered when a processing phase finishes."""
        # Currently no-op, but reserved for future use (e.g. phase transition logging)
        pass
    
    def _update_progress(self, progress: int, status: str) -> None:
        """Helper to update both progress and status simultaneously."""
        self.current_progress = progress
        self.current_status = status
        self.progress.emit(progress)
        self.status.emit(status)
        logger.info(status)