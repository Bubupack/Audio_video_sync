# workers/processing_worker.py
import time
from PyQt6.QtCore import QObject, pyqtSignal
import argparse
import logging
import sys
from pathlib import Path

from core.audio_analysis import get_audio_peaks
from config.config import VALID_AUDIO_EXTS, VALID_VIDEO_EXTS, AppConfig
from core.media_info import get_media_info
from core.renderer import generate_final_video
from utils.utils import validate_input_file, sanitize_filename, get_unique_output_path, format_time
from core.video_analysis import get_video_pics
logger = logging.getLogger(__name__)

class ProcessingWorker(QObject):
    """Effectue les calculs lourds en arrière-plan."""

    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, video_path: str, audio_path: str, output_dir: str) -> None:
        super().__init__()
        self.video_path = video_path
        self.audio_path = audio_path
        self.output_dir = output_dir

        self.curent_status = None
        self.curent_progress = 0
        self.processus_total_frame = 0  # Total number of frames to process, used for progress tracking
        self.start_time = None

    def run(self) -> None:
        """Méthode exécutée dans le thread secondaire."""
        try:
            """Program entry point.
    
            Returns:
                Process exit code (0 on success, non-zero on error).
            """
            try:
                output_path = self.run_pipeline()
                logger.info("Final video saved at: %s", output_path.resolve())
                self.curent_progress = 100
                self.progress.emit(100)
                self.curent_status = "Finished"
                self.status.emit("Finised")
                self.finished.emit(str(output_path.resolve()))
                return 0
            except FileNotFoundError as e:
                logger.error("Input file error: %s", e)
                self.error.emit(f"Input file error: {e}")
                return 2
            except ValueError as e:
                logger.error("Validation error: %s", e)
                self.error.emit(f"Validation error: {e}")
                return 3
            except BrokenPipeError as e:
                logger.error("Pipe error: %s", e)
                self.error.emit(f"Pipe error: {e}")
                return 4
            except RuntimeError as e:
                logger.error("Processing error: %s", e)
                self.error.emit(f"Processing error: {e}")
                return 5
            except Exception as e:  # noqa: BLE001 — top-level safety net
                logger.exception("Unexpected error: %s", e)
                self.error.emit(f"Unexpected error: {e}")
                return 1

        except Exception as exc:
            self.error.emit(str(exc))

    def run_pipeline(self) -> Path:
        """Execute the full synchronization pipeline.

        Returns:
            Path to the generated output file.
        """
        self.audio_path = Path(self.audio_path)
        self.video_path = Path(self.video_path)
        self.output_dir = Path(self.output_dir)
        validate_input_file(self.audio_path, VALID_AUDIO_EXTS, "audio")
        validate_input_file(self.video_path, VALID_VIDEO_EXTS, "video")

        self.output_dir.mkdir(parents=True, exist_ok=True)

        config = AppConfig(output_dir=self.output_dir)

        self.curent_progress = 0
        self.progress.emit(0)

        self.curent_status = "Loading media information"
        self.status.emit("Loading media information")
        logger.info("Loading media information")

        media = get_media_info(self.audio_path, self.video_path, config)

        ratio = (
            media.video_duration_ms / media.audio_duration_ms
            if media.audio_duration_ms > 0
            else 1
        )
        self.curent_progress = 1
        self.progress.emit(1)

        config.video.min_distance_ms = max(100, min(int(config.audio.min_distance_ms * ratio), 2000))

        self.curent_status = "Analyzing audio"
        self.status.emit("Analyzing audio")
        logger.info("Analyzing audio")
        audio_peaks = get_audio_peaks(media.audio_samples, media.sample_rate, config.audio)
        target_count = len(audio_peaks)

        self.curent_progress = 4
        self.progress.emit(4)

        self.curent_status = "Analyzing video motion"
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

        self.curent_progress = 54
        self.progress.emit(54)

        # --- NOUVELLE LOGIQUE DE NOMMAGE SÉCURISÉE ---
        raw_stem = f"{self.video_path.stem}_sync_{self.audio_path.stem}"
        safe_stem = sanitize_filename(raw_stem)
        
        output_path = get_unique_output_path(
            directory=self.output_dir,
            stem=safe_stem,
            suffix=f".{config.render.container}"
        )

        # ---------------------------------------------
        self.curent_status = "Generating final video"
        self.status.emit("Generating final video")
        logger.info("Generating final video")


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
        self.curent_status = "Saving the video"
        self.status.emit("Saving the video")
        logger.info("Saving the video")

        self.curent_progress = 99
        self.progress.emit(99)
        return output_path

    def update_progress(self, current: int) -> None:
        """"""
        elapsed = time.time() - self.start_time
        progress = current / self.processus_total_frame
        eta = (elapsed / progress - elapsed) if progress > 0 else 0
        self.status.emit(f"{self.curent_status}: {current}/{self.processus_total_frame} ({progress*100:.1f}%) - Time: {format_time(elapsed)}/{format_time(elapsed + eta)}")

        if self.curent_progress<54:
            self.curent_progress = 4 + int(progress*50)
        else:
            self.curent_progress = 54 + int(progress*45)

        self.progress.emit(self.curent_progress)

    def set_progressing(self, label: str, total: int) -> None:
        """"""
        self.curent_status = label
        self.status.emit(label)
        self.processus_total_frame = max(1, total)
        self.start_time = time.time()

    def finished_progress(self) -> None:
        """Emit a signal indicating that the processing is finished."""
        self.status.emit(self.curent_status)