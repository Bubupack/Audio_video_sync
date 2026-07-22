# gui/main_window.py
"""Main application window hosting the video and audio players side by side."""
from __future__ import annotations

import logging
from PyQt6.QtCore import QUrl, Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QMainWindow, QVBoxLayout, QWidget

from gui.audio_widget import AudioWidget
from gui.video_widget import VideoWidget
from gui.outputDir_widget import OutputDirWidget
from config.config import DEFAULT_OUTPUT_DIR
logger = logging.getLogger(__name__)


class PageConfig(QWidget):
    video_path = pyqtSignal(str)
    audio_path = pyqtSignal(str)
    output_directory = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        # Instantier les lecteurs
        self.video_player = VideoWidget(self)
        self.audio_player = AudioWidget(self)

        # Rediriger les signaux
        self.video_player.video_loaded.connect(self.video_path.emit)
        self.audio_player.audio_loaded.connect(self.audio_path.emit)

        # Widget du dossier de sortie
        self.output_dir_widget = OutputDirWidget()
        self.output_dir_widget.output_directory.connect(self.output_directory.emit)

        # Layout côte à côte (50% / 50%)
        side_by_side = QHBoxLayout()
        side_by_side.addWidget(self.video_player, stretch=1)
        side_by_side.addWidget(self.audio_player, stretch=1)

        # Layout principal rattaché directement à 'self'
        main_layout = QVBoxLayout(self)  # <--- Assigne le layout directement à PageConfig
        main_layout.addLayout(side_by_side)
        main_layout.addWidget(self.output_dir_widget)
        main_layout.addStretch()