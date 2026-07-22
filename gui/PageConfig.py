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


class PageConfig(QWidget):
    def __init__(self) -> None:
        super().__init__()
        # Instantiate the two players
        self.video_player = VideoWidget(self)
        self.audio_player = AudioWidget(self)

        # Output directory widget
        self.output_dir_widget = OutputDirWidget()

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