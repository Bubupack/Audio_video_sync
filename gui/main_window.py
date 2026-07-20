# gui/main_window.py
"""Main application window hosting the video and audio players side by side."""
from __future__ import annotations

import logging

from PyQt6.QtWidgets import QHBoxLayout, QMainWindow, QVBoxLayout, QWidget

from gui.audio_widget import AudioWidget
from gui.video_widget import VideoWidget
from gui.outputDir_widget import OutputDirWidget
from config.config import DEFAULT_OUTPUT_DIR
logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Audio-Video Sync")
        self.resize(960, 540)
        
        # Initialize paths
        self.video_path: str = ""
        self.audio_path: str = ""
        self.output_directory: str = DEFAULT_OUTPUT_DIR

        # Instantiate the two players
        self.video_player = VideoWidget(self)
        self.audio_player = AudioWidget(self)

        # Forward media-loaded signals
        self.video_player.video_loaded.connect(self._on_video_received)
        self.audio_player.audio_loaded.connect(self._on_audio_received)

        # Output directory widget
        self.output_dir_widget = OutputDirWidget()

        # Connect the output directory signal to a handler
        self.output_dir_widget.output_directory.connect(self._on_output_directory_changed)

        # Add the output directory widget to the main layout
        # Side-by-side layout (50% / 50%)
        side_by_side = QHBoxLayout()
        side_by_side.addWidget(self.video_player, stretch=1)
        side_by_side.addWidget(self.audio_player, stretch=1)

        # Top-aligned main layout
        main_layout = QVBoxLayout()
        main_layout.addLayout(side_by_side)
        main_layout.addWidget(self.output_dir_widget)
        main_layout.addStretch()

        container = QWidget(self)
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    # ------------------------------------------------------------------
    # Signal handlers
    # ------------------------------------------------------------------
    def _on_audio_received(self, path: str) -> None:
        self.audio_path = path
        logger.info("Audio loaded: %s", path)

    def _on_video_received(self, path: str) -> None:
        self.video_path = path
        logger.info("Video loaded: %s", path)

    def _on_output_directory_changed(self, new_dir: str) -> None:
        self.output_directory = new_dir
        logger.info("Output directory changed to: %s", new_dir)