"""Audio player widget with embedded cover-art display and volume controls."""
from __future__ import annotations

import base64
import logging
from typing import List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QResizeEvent
from PyQt6.QtMultimedia import QAudioOutput
from PyQt6.QtWidgets import QLabel, QSizePolicy, QStyle, QWidget
from mutagen import File
from mutagen.flac import Picture

from gui.base_player_widget import BaseMediaPlayerWidget
from gui.media_controls import VolumeControlsBar
from utils.utils import extract_embedded_cover

logger = logging.getLogger(__name__)


class AudioWidget(BaseMediaPlayerWidget):
    """Audio player widget displaying embedded cover art and volume controls."""

    audio_loaded = BaseMediaPlayerWidget.media_loaded  # semantic alias

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(media_type="audio", parent=parent)

    # ------------------------------------------------------------------
    # BaseMediaPlayerWidget hooks
    # ------------------------------------------------------------------
    def _create_display_widget(self) -> QLabel:
        self.cover_label = QLabel(self)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Force the label to obey the layout size instead of the pixmap size.
        self.cover_label.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Ignored,
        )
        self._cover_pixmap: Optional[QPixmap] = None
        return self.cover_label

    def _configure_player(self) -> None:
        self.audio_output = QAudioOutput(self)
        self.media_player.setAudioOutput(self.audio_output)

    def _extra_controls(self) -> List[QWidget]:
        self.volume_bar = VolumeControlsBar(self)
        self.volume_bar.volume_changed.connect(self._on_volume_changed)
        self.volume_bar.mute_toggled.connect(self._toggle_mute)
        self.volume_bar.set_enabled(False)
        return [self.volume_bar]

    def _on_media_loaded(self, file_path: str) -> None:
        # Enable volume controls and apply the default volume.
        self.volume_bar.set_enabled(True)
        self.audio_output.setVolume(self.volume_bar.volume)

        self.cover_label.setText("Loading cover art…")
        self._extract_cover(file_path)

    def _on_reset(self) -> None:
        """Reset audio-specific controls and the cover-art display."""
        self.volume_bar.reset()
        self._cover_pixmap = None
        self.cover_label.clear()
        self.cover_label.setText("")

    # ------------------------------------------------------------------
    # Cover-art extraction
    # ------------------------------------------------------------------
    def _extract_cover(self, file_path: str) -> None:
        """Attempt to read embedded cover art from the audio file."""
        try:
            image_data = extract_embedded_cover(file_path)
            if image_data:
                pixmap = QPixmap()
                if pixmap.loadFromData(image_data):
                    self._cover_pixmap = pixmap
                    self.cover_label.setText("")
                    self._refresh_cover()
                    return

            self._cover_pixmap = None
            self.cover_label.setText("No embedded cover art")
        except Exception as exc:
            logger.exception("Failed to extract cover art from %s", file_path)
            self._cover_pixmap = None
            self.cover_label.setText("Error reading cover art")

    def _refresh_cover(self) -> None:
        """Re-scale the cover pixmap to fit the current label size."""
        if not self._cover_pixmap or self._cover_pixmap.isNull():
            return
        scaled = self._cover_pixmap.scaled(
            self.cover_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.cover_label.setPixmap(scaled)

    # ------------------------------------------------------------------
    # Volume / mute handlers
    # ------------------------------------------------------------------
    def _on_volume_changed(self, volume: float) -> None:
        self.audio_output.setVolume(volume)
        # Automatically unmute when the user raises the volume above zero.
        if volume > 0 and self.audio_output.isMuted():
            self.audio_output.setMuted(False)
            self.volume_bar.set_muted(False)

    def _toggle_mute(self) -> None:
        new_muted = not self.audio_output.isMuted()
        self.audio_output.setMuted(new_muted)
        self.volume_bar.set_muted(new_muted)

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------
    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._refresh_cover()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_cover_pixmap(self) -> Optional[QPixmap]:
        """Return the current cover-art pixmap (or ``None`` if not available)."""
        return self._cover_pixmap