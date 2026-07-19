# gui/video_widget.py
"""Video player widget. Audio is intentionally disabled."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtMultimedia import QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import QSizePolicy, QWidget

from gui.base_player_widget import BaseMediaPlayerWidget


class VideoWidget(BaseMediaPlayerWidget):
    """Video player widget. Videos are played silently by design."""

    video_loaded = BaseMediaPlayerWidget.media_loaded  # alias for clarity

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(media_type="video", parent=parent)

    # ------------------------------------------------------------------
    # BaseMediaPlayerWidget hooks
    # ------------------------------------------------------------------
    def _create_display_widget(self) -> QVideoWidget:
        self.video_surface = QVideoWidget(self)
        self.video_surface.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Ignored,
        )
        return self.video_surface

    def _configure_player(self) -> None:
        # Attach the video output so frames are rendered on screen.
        self.media_player.setVideoOutput(self.video_surface)

        # We attach an audio output but keep it muted at all times so the
        # video is guaranteed to stay silent (per project requirement).
        self._audio_output = QAudioOutput(self)
        self._audio_output.setMuted(True)
        self._audio_output.setVolume(0.0)
        self.media_player.setAudioOutput(self._audio_output)