"""Processing page with a cross-fade animation between audio and video covers."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPaintEvent, QPainter, QPixmap
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget

_STATUS_LABEL_STYLE = """
    QLabel {
        color: #FFFFFF;
        font-size: 15px;
        font-weight: bold;
        background-color: rgba(0, 0, 0, 0.65);
        padding: 8px 18px;
        border-radius: 8px;
    }
"""

_PROGRESS_BAR_STYLE = """
    QProgressBar {
        border: 2px solid rgba(255, 255, 255, 0.7);
        border-radius: 11px;
        background-color: rgba(0, 0, 0, 0.55);
    }
    QProgressBar::chunk {
        background-color: #007ACC;
        border-radius: 9px;
    }
"""

_PERCENTAGE_LABEL_STYLE = """
    QLabel {
        color: #FFFFFF;
        font-size: 14px;
        font-weight: bold;
        background-color: rgba(0, 0, 0, 0.65);
        padding: 3px 10px;
        border-radius: 6px;
    }
"""

_DEFAULT_BG_COLOR = QColor(25, 25, 25)


class PageProcessing(QWidget):
    """Loading page that cross-fades from the audio cover to the video cover.

    The audio cover is drawn full-screen as the background.  The video cover
    is overlaid on top with an opacity proportional to the progress percentage.
    A status label and progress bar inform the user of the current operation.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._video_pixmap: Optional[QPixmap] = None
        self._audio_pixmap: Optional[QPixmap] = None
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        # --- Status label ---
        self.status_label = QLabel("Initializing processing…", self)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(_STATUS_LABEL_STYLE)

        # --- Progress bar (no built-in text) ---
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(22)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(_PROGRESS_BAR_STYLE)

        # --- Percentage label ---
        self.percentage_label = QLabel("0%", self)
        self.percentage_label.setStyleSheet(_PERCENTAGE_LABEL_STYLE)

        # --- Progress row (bar + percentage) ---
        progress_row = QHBoxLayout()
        progress_row.addWidget(self.progress_bar, stretch=1)
        progress_row.addWidget(self.percentage_label)

        # --- Main layout (vertically centred) ---
        layout = QVBoxLayout(self)
        layout.addStretch()
        layout.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(15)
        layout.addLayout(progress_row)
        layout.addStretch()
        layout.setContentsMargins(60, 0, 60, 0)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_media_info(
        self, video_cover: Optional[QPixmap], audio_cover: Optional[QPixmap]
    ) -> None:
        """Inject the video and audio cover pixmaps and trigger a repaint."""
        self._video_pixmap = (
            video_cover if (video_cover and not video_cover.isNull()) else None
        )
        self._audio_pixmap = (
            audio_cover if (audio_cover and not audio_cover.isNull()) else None
        )
        self.update()

    def set_progress(self, value: int) -> None:
        """Update the progress percentage and repaint the cross-fade overlay."""
        self.progress_bar.setValue(value)
        self.percentage_label.setText(f"{value}%")
        self.update()

    def set_status(self, text: str) -> None:
        """Update the status message."""
        self.status_label.setText(text)

    def reset_ui(self) -> None:
        """Reset the page to its initial state."""
        self.progress_bar.setValue(0)
        self.percentage_label.setText("0%")
        self.status_label.setText("Initializing…")
        self._video_pixmap = None
        self._audio_pixmap = None
        self.update()

    # ------------------------------------------------------------------
    # Custom painting
    # ------------------------------------------------------------------
    def paintEvent(self, event: QPaintEvent) -> None:
        """Draw the audio cover as background and overlay the video cover with opacity."""
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        width, height = self.width(), self.height()

        # A. Background: audio cover (full-screen, expanding)
        if self._audio_pixmap:
            scaled_audio = self._audio_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            ax = (width - scaled_audio.width()) // 2
            ay = (height - scaled_audio.height()) // 2
            painter.drawPixmap(ax, ay, scaled_audio)
        else:
            painter.fillRect(0, 0, width, height, _DEFAULT_BG_COLOR)

        # B. Overlay: video cover (opacity = progress / 100)
        if self._video_pixmap:
            opacity = self.progress_bar.value() / 100.0
            painter.setOpacity(opacity)

            scaled_video = self._video_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            vx = (width - scaled_video.width()) // 2
            vy = (height - scaled_video.height()) // 2
            painter.drawPixmap(vx, vy, scaled_video)

        # Restore opacity for any subsequent painting operations.
        painter.setOpacity(1.0)