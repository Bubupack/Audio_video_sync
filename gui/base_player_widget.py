# gui/base_player_widget.py
"""Abstract base widget that encapsulates the shared media-player logic."""
from __future__ import annotations

from abc import abstractmethod
from typing import List, Optional

from PyQt6.QtCore import QUrl, Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
    QStackedLayout,
    QStyle,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtMultimedia import QMediaPlayer

from gui.drop_zone import DropZone


class BaseMediaPlayerWidget(QWidget):
    """Common scaffolding for audio/video playback widgets."""

    media_loaded = pyqtSignal(str)

    def __init__(self, media_type: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        if media_type not in ("audio", "video"):
            raise ValueError(f"Unsupported media type: {media_type!r}")

        self._media_type = media_type
        self._current_path: Optional[str] = None

        # Core Qt media player (no audio output by default → videos are silent)
        self.media_player = QMediaPlayer(self)

        # Drop zone + display surface (provided by subclasses)
        self.drop_zone = DropZone(media_type=media_type, parent=self)
        self.drop_zone.path.connect(self.load_media)
        self.display_widget = self._create_display_widget()

        # Subclass-specific player configuration (audio output, video output…)
        self._configure_player()

        # Player → UI synchronisation
        self.media_player.positionChanged.connect(self._on_position_changed)
        self.media_player.durationChanged.connect(self._on_duration_changed)

        self._build_ui()

    # ------------------------------------------------------------------
    # Hooks to be overridden by subclasses
    # ------------------------------------------------------------------
    @abstractmethod
    def _create_display_widget(self) -> QWidget:
        """Return the widget used to display the media (video surface, cover art…)."""

    def _configure_player(self) -> None:
        """Optional setup (e.g. attach audio/video output to the player)."""

    def _extra_controls(self) -> List[QWidget]:
        """Return additional widgets to insert next to play/restart buttons."""
        return []

    def _on_media_loaded(self, file_path: str) -> None:
        """Hook called once a file has been loaded (e.g. extract cover art)."""

    def _on_reset(self) -> None:
        """Hook called when the player is reset (override in subclasses if needed)."""

    def _file_filter(self) -> str:
        if self._media_type == "audio":
            return "Audio Files (*.mp3 *.wav *.flac *.aac)"
        return "Video Files (*.mp4 *.mkv *.avi *.mov)"

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        # Open file button
        self.btn_open = QPushButton("Open file", self)
        self.btn_open.clicked.connect(self._open_file_dialog)

        # Play / Pause button
        self.btn_play = QPushButton(self)
        self.btn_play.setIcon(self._std_icon(QStyle.StandardPixmap.SP_MediaPlay))
        self.btn_play.clicked.connect(self.toggle_play)
        self.btn_play.setEnabled(False)

        # Restart button
        self.btn_restart = QPushButton(self)
        self.btn_restart.setIcon(
            self._std_icon(QStyle.StandardPixmap.SP_MediaSkipBackward)
        )
        self.btn_restart.clicked.connect(self.restart_media)
        self.btn_restart.setEnabled(False)

        # Playback slider
        # We use valueChanged to allow seeking by clicking directly on the slider.
        # The player update uses blockSignals to avoid feedback loops.
        self.slider_playback = QSlider(Qt.Orientation.Horizontal, self)
        self.slider_playback.setRange(0, 0)
        self.slider_playback.setEnabled(False)
        self.slider_playback.valueChanged.connect(self._set_media_position)

        # Time label (Current / Total)
        self.time_label = QLabel("00:00 / 00:00", self)
        
        # Playback slider row
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(self.slider_playback, stretch=1)
        slider_layout.addWidget(self.time_label)

        # Controls row (extra controls inserted between play and the right edge)
        controls_row = QHBoxLayout()
        controls_row.addWidget(self.btn_restart)
        controls_row.addWidget(self.btn_play)
        for extra in self._extra_controls():
            controls_row.addWidget(extra, stretch=1)

        # Main controls layout
        controls_layout = QVBoxLayout()
        controls_layout.addLayout(slider_layout)
        controls_layout.addLayout(controls_row)
        controls_layout.addWidget(self.btn_open)
        controls_layout.addStretch(1)  # Prevent controls from stretching vertically

        # Media container using QStackedLayout to seamlessly swap widgets
        # without triggering layout jumps or resizing bugs.
        self.media_container = QWidget(self)
        self.media_layout = QStackedLayout(self.media_container)
        self.media_layout.addWidget(self.drop_zone)
        self.media_layout.addWidget(self.display_widget)
        self.media_layout.setCurrentWidget(self.drop_zone)

        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.addWidget(self.media_container)
        self.main_layout.addLayout(controls_layout)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def load_media(self, file_path: str) -> None:
        self._current_path = file_path
        self.media_loaded.emit(file_path)

        # Swap drop zone for the display surface seamlessly
        self.media_layout.setCurrentWidget(self.display_widget)

        self.btn_play.setEnabled(True)
        self.btn_restart.setEnabled(True)
        self.slider_playback.setEnabled(True)

        self.media_player.setSource(QUrl.fromLocalFile(file_path))
        self._on_media_loaded(file_path)
        self.media_player.play()
        self._set_play_icon(playing=True)

    def toggle_play(self) -> None:
        is_playing = (
            self.media_player.playbackState()
            == QMediaPlayer.PlaybackState.PlayingState
        )
        if is_playing:
            self.media_player.pause()
            self._set_play_icon(playing=False)
        else:
            self.media_player.play()
            self._set_play_icon(playing=True)

    def restart_media(self) -> None:
        self.media_player.setPosition(0)

    def reset(self) -> None:
        """Reset player state, stop playback, unload media, and show DropZone."""
        # 1. Stop playback & clear source
        self.media_player.stop()
        self.media_player.setSource(QUrl())
        self._current_path = None

        # 2. Reset drop zone state and switch layout view
        self.drop_zone.reset()
        self.media_layout.setCurrentWidget(self.drop_zone)

        # 3. Disable controls and reset icons
        self.btn_play.setEnabled(False)
        self.btn_restart.setEnabled(False)

        # 4. Reset slider and time label
        self.slider_playback.blockSignals(True)
        self.slider_playback.setRange(0, 0)
        self.slider_playback.setValue(0)
        self.slider_playback.setEnabled(False)
        self.slider_playback.blockSignals(False)

        self.time_label.setText("00:00 / 00:00")
        self._set_play_icon(playing=False)

        # 5. Execute subclass-specific reset logic
        self._on_reset()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _open_file_dialog(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            f"Select a {self._media_type} file",
            "",
            self._file_filter(),
        )
        if file_name:
            self.load_media(file_name)

    def _std_icon(self, pixmap: QStyle.StandardPixmap) -> QIcon:
        return self.style().standardIcon(pixmap)

    def _set_play_icon(self, playing: bool) -> None:
        icon = (
            QStyle.StandardPixmap.SP_MediaPause
            if playing
            else QStyle.StandardPixmap.SP_MediaPlay
        )
        self.btn_play.setIcon(self._std_icon(icon))

    def _format_time(self, ms: int) -> str:
        """Converts milliseconds to a mm:ss string format."""
        seconds = int(ms / 1000)
        m, s = divmod(seconds, 60)
        return f"{m:02d}:{s:02d}"

    def _update_time_label(self, position: int, duration: int) -> None:
        self.time_label.setText(
            f"{self._format_time(position)} / {self._format_time(duration)}"
        )

    def _on_position_changed(self, position: int) -> None:
        # Block signals so we don't trigger valueChanged -> setPosition loop.
        self.slider_playback.blockSignals(True)
        self.slider_playback.setValue(position)
        self.slider_playback.blockSignals(False)
        self._update_time_label(position, self.media_player.duration())

    def _on_duration_changed(self, duration: int) -> None:
        self.slider_playback.setRange(0, duration)
        self._update_time_label(self.slider_playback.value(), duration)

    def _set_media_position(self, position: int) -> None:
        self.media_player.setPosition(position)
        self._update_time_label(position, self.media_player.duration())

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------
    def resizeEvent(self, event) -> None:
        """Force the display area to a strict 16:9 aspect ratio."""
        super().resizeEvent(event)
        target_height = int(self.width() * 9 / 16)
        self.media_container.setFixedHeight(target_height)