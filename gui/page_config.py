"""Configuration page hosting the video player, audio player, and output selection."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from config.config import DEFAULT_OUTPUT_DIR
from gui.audio_widget import AudioWidget
from gui.output_dir_widget import OutputDirWidget
from gui.video_widget import VideoWidget
from utils.utils import extract_video_thumbnail

logger = logging.getLogger(__name__)


class PageConfig(QWidget):
    """Configuration page where the user selects video, audio, and output folder.

    Signals
    -------
    video_path(str)
        Emitted when the video path changes.
    audio_path(str)
        Emitted when the audio path changes.
    output_directory(str)
        Emitted when the output directory changes.
    start_requested
        Emitted when the user clicks the *Start* button.
    """

    video_path = pyqtSignal(str)
    audio_path = pyqtSignal(str)
    output_directory = pyqtSignal(str)
    start_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        # --- Internal path storage ---
        self._video_path: Optional[str] = None
        self._audio_path: Optional[str] = None
        self._output_dir: Optional[str] = DEFAULT_OUTPUT_DIR

        # --- Sub-widgets ---
        self.video_player = VideoWidget(self)
        self.audio_player = AudioWidget(self)
        self.output_dir_widget = OutputDirWidget(self)

        # --- Action buttons ---
        self.start_button = QPushButton("Start processing", self)
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self.start_requested.emit)

        self.reset_button = QPushButton("Reset media", self)
        self.reset_button.clicked.connect(self.reset)

        # --- Signal wiring ---
        self.video_player.video_loaded.connect(self._on_video_loaded)
        self.audio_player.audio_loaded.connect(self._on_audio_loaded)
        self.output_dir_widget.output_directory.connect(self._on_output_dir_changed)

        self._build_ui()
        self._update_start_button_state()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        side_by_side = QHBoxLayout()
        side_by_side.addWidget(self.video_player, stretch=1)
        side_by_side.addWidget(self.audio_player, stretch=1)

        actions_row = QHBoxLayout()
        actions_row.addWidget(self.reset_button)
        actions_row.addWidget(self.start_button)

        main_layout = QVBoxLayout(self)
        main_layout.addLayout(side_by_side)
        main_layout.addWidget(self.output_dir_widget)
        main_layout.addLayout(actions_row)
        main_layout.addStretch()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def _update_start_button_state(self) -> None:
        """Enable the *Start* button only when video, audio, and output are valid."""
        has_valid_video = bool(self._video_path and Path(self._video_path).is_file())
        has_valid_audio = bool(self._audio_path and Path(self._audio_path).is_file())
        has_valid_output = bool(self._output_dir and Path(self._output_dir).is_dir())
        self.start_button.setEnabled(
            has_valid_video and has_valid_audio and has_valid_output
        )

    # ------------------------------------------------------------------
    # Signal handlers
    # ------------------------------------------------------------------
    def _on_video_loaded(self, path: str) -> None:
        self._video_path = path
        self.video_path.emit(path)
        self._update_start_button_state()

    def _on_audio_loaded(self, path: str) -> None:
        self._audio_path = path
        self.audio_path.emit(path)
        self._update_start_button_state()

    def _on_output_dir_changed(self, path: str) -> None:
        self._output_dir = path
        self.output_directory.emit(path)
        self._update_start_button_state()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @property
    def current_video_path(self) -> Optional[str]:
        """Return the currently selected video file path."""
        return self._video_path

    @property
    def current_audio_path(self) -> Optional[str]:
        """Return the currently selected audio file path."""
        return self._audio_path

    @property
    def current_output_dir(self) -> Optional[str]:
        """Return the currently selected output directory."""
        return self._output_dir

    def get_audio_cover(self) -> Optional[QPixmap]:
        """Return the cover-art pixmap extracted by the audio player."""
        return self.audio_player.get_cover_pixmap()

    def get_video_cover(self) -> Optional[QPixmap]:
        """Generate and return a thumbnail pixmap from the loaded video."""
        if self._video_path:
            return extract_video_thumbnail(self._video_path)
        return None

    def reset(self) -> None:
        """Reset the audio/video players and their paths (keeps the output dir)."""
        # 1. Reset graphical widgets and drop zones
        self.video_player.reset()
        self.audio_player.reset()

        # 2. Clear in-memory video and audio paths (keep the output directory)
        self._video_path = None
        self._audio_path = None

        # 3. Notify listeners that media paths are now empty
        self.video_path.emit("")
        self.audio_path.emit("")

        # 4. Refresh the Start button state
        self._update_start_button_state()