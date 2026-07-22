# gui/drop_zone.py
"""Drag-and-drop area that accepts a single audio or video file."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QLabel, QWidget

from config.config import VALID_AUDIO_EXTS, VALID_VIDEO_EXTS
from utils.utils import validate_input_file

logger = logging.getLogger(__name__)

_VALID_EXTENSIONS = {
    "audio": VALID_AUDIO_EXTS,
    "video": VALID_VIDEO_EXTS,
}


class DropZone(QLabel):
    """A QLabel-based drop area restricted to one media type."""

    path = pyqtSignal(str)

    def __init__(
        self,
        media_type: str = "video",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        if media_type not in _VALID_EXTENSIONS:
            raise ValueError(f"Unsupported media type: {media_type!r}")
        self._media_type = media_type
        self._current_path: Optional[str] = None
        self._build_ui()

    def _build_ui(self) -> None:
        self.setText(
            f"Drag & drop your {self._media_type} here\n"
            f"or use the button below"
        )
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            """
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 8px;
                background-color: #f0f0f0;
                color: #555;
                font-size: 14px;
            }
            """
        )
        self.setAcceptDrops(True)

    # ------------------------------------------------------------------
    # Drag & drop events
    # ------------------------------------------------------------------
    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        urls = event.mimeData().urls()
        if not urls:
            return
        file_path = Path(urls[0].toLocalFile())
        try:
            validate_input_file(
                file_path,
                _VALID_EXTENSIONS[self._media_type],
                self._media_type,
            )
        except ValueError as exc:
            logger.error("Invalid %s file: %s", self._media_type, exc)
            return
        self.load(str(file_path))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def load(self, file_path: str) -> None:
        self._current_path = file_path
        self.path.emit(file_path)

    def reset(self) -> None:
        """Reset the drop zone state."""
        self._current_path = None

    @property
    def current_path(self) -> Optional[str]:
        return self._current_path