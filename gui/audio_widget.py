# gui/audio_widget.py
"""Audio player widget with embedded cover-art display and volume controls."""
from __future__ import annotations

import base64
import logging
from typing import List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtMultimedia import QAudioOutput
from PyQt6.QtWidgets import (
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
    QStyle,
    QWidget,
)
from mutagen import File
from mutagen.flac import Picture

from gui.base_player_widget import BaseMediaPlayerWidget

logger = logging.getLogger(__name__)


class AudioWidget(BaseMediaPlayerWidget):
    """Audio player widget with cover art and volume controls."""

    audio_loaded = BaseMediaPlayerWidget.media_loaded  # alias for clarity

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
        # Mute toggle button
        self.btn_mute = QPushButton(self)
        self.btn_mute.setIcon(
            self._std_icon(QStyle.StandardPixmap.SP_MediaVolume)
        )
        self.btn_mute.clicked.connect(self._toggle_mute)
        self.btn_mute.setEnabled(False)

        # Volume slider
        self.slider_volume = QSlider(Qt.Orientation.Horizontal, self)
        self.slider_volume.setRange(0, 100)
        self.slider_volume.setValue(70)
        self.slider_volume.valueChanged.connect(self._change_volume)
        self.slider_volume.setEnabled(False)

        # Volume label (0 to 100)
        self.volume_label = QLabel(f"{self.slider_volume.value()} %", self)
        self.volume_label.setFixedWidth(40)  # Keep it compact to avoid layout jumps

        return [self.btn_mute, self.slider_volume, self.volume_label]

    def _on_media_loaded(self, file_path: str) -> None:
        # Enable audio-only controls and apply default volume.
        self.btn_mute.setEnabled(True)
        self.slider_volume.setEnabled(True)
        self.audio_output.setVolume(self.slider_volume.value() / 100.0)

        self.cover_label.setText("Loading cover art…")
        self._extract_cover(file_path)

    # ------------------------------------------------------------------
    # Cover-art extraction
    # ------------------------------------------------------------------
    def _extract_cover(self, file_path: str) -> None:
        try:
            audio = File(file_path)
            if audio is None:
                self.cover_label.setText("Cannot read file")
                return

            image_data = self._read_cover_bytes(audio)
            if image_data:
                pixmap = QPixmap()
                if pixmap.loadFromData(image_data):
                    self._cover_pixmap = pixmap
                    self.cover_label.setText("")
                    self._refresh_cover()
                    return

            self._cover_pixmap = None
            self.cover_label.setText("No embedded cover art")
        except Exception as exc:  # noqa: BLE001 — mutagen can raise many errors
            logger.exception("Failed to extract cover art from %s", file_path)
            self._cover_pixmap = None
            self.cover_label.setText("Error reading cover art")

    @staticmethod
    def _read_cover_bytes(audio) -> Optional[bytes]:
        # 1) Native pictures (FLAC, OGG with METADATA_BLOCK_PICTURE…)
        if hasattr(audio, "pictures") and audio.pictures:
            preferred = next((p for p in audio.pictures if p.type == 3), None)
            return (preferred or audio.pictures[0]).data

        # 2) ID3 APIC frames (MP3)
        if audio.tags and hasattr(audio.tags, "keys"):
            for key in audio.tags.keys():
                if key.startswith("APIC"):
                    return audio.tags[key].data

        # 3) MP4 'covr' atom
        tags = audio.tags if (hasattr(audio, "tags") and audio.tags) else audio
        if tags and "covr" in tags:
            return bytes(tags["covr"][0])

        # 4) Base64-encoded FLAC picture in Vorbis comments
        if "metadata_block_picture" in audio:
            raw = base64.b64decode(audio["metadata_block_picture"][0])
            return Picture(raw).data

        return None

    def _refresh_cover(self) -> None:
        if not self._cover_pixmap or self._cover_pixmap.isNull():
            return
        scaled = self._cover_pixmap.scaled(
            self.cover_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.cover_label.setPixmap(scaled)

    # ------------------------------------------------------------------
    # Volume / mute
    # ------------------------------------------------------------------
    def _toggle_mute(self) -> None:
        currently_muted = self.audio_output.isMuted()
        self.audio_output.setMuted(not currently_muted)
        self.btn_mute.setIcon(
            self._std_icon(
                QStyle.StandardPixmap.SP_MediaVolume
                if currently_muted
                else QStyle.StandardPixmap.SP_MediaVolumeMuted
            )
        )

    def _change_volume(self, value: int) -> None:
        volume = value / 100.0
        self.audio_output.setVolume(volume)
        self.volume_label.setText(f"{value} %")

        # Unmute automatically if the user pushes the slider above zero.
        if volume > 0 and self.audio_output.isMuted():
            self.audio_output.setMuted(False)
            self.btn_mute.setIcon(
                self._std_icon(QStyle.StandardPixmap.SP_MediaVolume)
            )

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------
    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh_cover()