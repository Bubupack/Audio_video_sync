"""Main application window orchestrating configuration, processing, and visualization."""
from __future__ import annotations

import logging

from PyQt6.QtCore import QThread
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QStackedWidget

from core.processing_worker import ProcessingWorker
from gui.page_config import PageConfig
from gui.page_processing import PageProcessing
from gui.page_visualization import PageVisualization

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Top-level window that switches between the three application pages.

    Page flow::

        PageConfig → PageProcessing → PageVisualization
             ↑                                │
             └────────────────────────────────┘
                      (sync another)
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Audio-Video Sync")
        self.resize(960, 540)

        # --- Page stack ---
        self.pages = QStackedWidget(self)
        self.setCentralWidget(self.pages)

        self.page_config = PageConfig(self)
        self.page_processing = PageProcessing(self)
        self.page_visualization = PageVisualization(self)

        self.pages.addWidget(self.page_config)
        self.pages.addWidget(self.page_processing)
        self.pages.addWidget(self.page_visualization)

        # --- Inter-page signal wiring ---
        self.page_config.start_requested.connect(self._start_processing)
        self.page_visualization.sync_another_requested.connect(self._restart_app)

        # --- Thread / worker handles ---
        self._thread: QThread | None = None
        self._worker: ProcessingWorker | None = None

    # ------------------------------------------------------------------
    # Processing lifecycle
    # ------------------------------------------------------------------
    def _start_processing(self) -> None:
        """Collect validated paths, start the worker thread, and show the progress page."""
        video_path = self.page_config.current_video_path
        audio_path = self.page_config.current_audio_path
        output_dir = self.page_config.current_output_dir

        video_cover = self.page_config.get_video_cover()
        audio_cover = self.page_config.get_audio_cover()

        # 1. Prepare the UI: reset config page, update processing page, and switch view.
        self.page_config.reset()
        self.page_processing.reset_ui()
        self.page_processing.set_media_info(video_cover, audio_cover)
        self.pages.setCurrentWidget(self.page_processing)

        # 2. Create worker and thread.
        self._thread = QThread()
        self._worker = ProcessingWorker(video_path, audio_path, output_dir)
        self._worker.moveToThread(self._thread)

        # 3. Connect signals.
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self.page_processing.set_progress)
        self._worker.status.connect(self.page_processing.set_status)
        self._worker.finished.connect(self._on_processing_finished)
        self._worker.error.connect(self._on_processing_error)

        # 4. Clean-up connections.
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        # 5. Start.
        self._thread.start()

    def _on_processing_finished(self, generated_video_path: str) -> None:
        """Switch to the visualization page when processing succeeds."""
        logger.info("Processing completed successfully.")
        self.page_visualization.set_video(generated_video_path)
        self.pages.setCurrentWidget(self.page_visualization)

    def _on_processing_error(self, error_message: str) -> None:
        """Show an error dialog and return to the configuration page."""
        logger.error("Processing error: %s", error_message)
        QMessageBox.critical(
            self,
            "Error",
            f"An error occurred during processing:\n{error_message}",
        )
        if self._thread and self._thread.isRunning():
            self._thread.quit()
        self.pages.setCurrentWidget(self.page_config)

    def _restart_app(self) -> None:
        """Reset all pages and return to the configuration page."""
        self.page_visualization.reset_ui()
        self.page_config.reset()
        self.pages.setCurrentWidget(self.page_config)