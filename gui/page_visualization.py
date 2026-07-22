"""Final visualization page showing the resynchronised video.

This page reuses :class:`MediaControlsBar` and :class:`VolumeControlsBar`
to avoid duplicating the playback-control logic found in
:class:`BaseMediaPlayerWidget`.
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QUrl, Qt, pyqtSignal
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import (
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from gui.media_controls import MediaControlsBar, VolumeControlsBar


class PageVisualization(QWidget):
    """Final page that plays the resynchronised video with full controls.

    Signals
    -------
    sync_another_requested
        Emitted when the user wants to return to the configuration page.
    """

    sync_another_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._video_path: Optional[str] = None

        # --- Media player and outputs ---
        self.media_player = QMediaPlayer(self)

        self._audio_output = QAudioOutput(self)
        self._audio_output.setVolume(VolumeControlsBar.DEFAULT_VOLUME_PERCENT / 100.0)
        self.media_player.setAudioOutput(self._audio_output)

        self.video_surface = QVideoWidget(self)
        self.video_surface.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.media_player.setVideoOutput(self.video_surface)

        # --- Reusable control bars ---
        self.controls_bar = MediaControlsBar(self)
        self.controls_bar.play_toggled.connect(self._toggle_play)
        self.controls_bar.restart_requested.connect(self._restart_media)
        self.controls_bar.position_seeked.connect(self._set_media_position)

        self.volume_bar = VolumeControlsBar(self)
        self.volume_bar.volume_changed.connect(self._on_volume_changed)
        self.volume_bar.mute_toggled.connect(self._toggle_mute)
        self.controls_bar.add_control(self.volume_bar, stretch=1)

        # --- Player → controls synchronisation ---
        self.media_player.positionChanged.connect(self._on_position_changed)
        self.media_player.durationChanged.connect(self._on_duration_changed)

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        # --- Output path label ---
        self.output_path_label = QLabel("Output file: None", self)
        self.output_path_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.output_path_label.setWordWrap(True)
        self.output_path_label.setStyleSheet(
            "font-weight: bold; color: #DDDDDD; font-size: 13px;"
        )

        # --- Sync-another button ---
        self.sync_another_button = QPushButton("Synchronise another video", self)
        self.sync_another_button.setStyleSheet(
            "padding: 8px 16px; font-weight: bold; font-size: 14px;"
        )
        self.sync_another_button.clicked.connect(self.sync_another_requested.emit)

        # --- Main layout ---
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.video_surface, stretch=1)
        main_layout.addWidget(self.controls_bar)
        main_layout.addSpacing(10)
        main_layout.addWidget(self.output_path_label)
        main_layout.addSpacing(10)
        main_layout.addWidget(
            self.sync_another_button, alignment=Qt.AlignmentFlag.AlignCenter
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_video(self, video_path: str) -> None:
        """Load and start playing the final output video."""
        self._video_path = video_path
        self.output_path_label.setText(f"Output file: {video_path}")
        self.media_player.setSource(QUrl.fromLocalFile(video_path))
        self.media_player.play()
        self.controls_bar.set_playing(True)

    def reset_ui(self) -> None:
        """Stop playback and reset all controls to their initial state."""
        self.media_player.stop()
        self.media_player.setSource(QUrl())
        self._video_path = None
        self.output_path_label.setText("Output file: None")
        self.controls_bar.reset()
        self.volume_bar.reset()

    # ------------------------------------------------------------------
    # Playback handlers
    # ------------------------------------------------------------------
    def _toggle_play(self) -> None:
        is_playing = (
            self.media_player.playbackState()
            == QMediaPlayer.PlaybackState.PlayingState
        )
        if is_playing:
            self.media_player.pause()
            self.controls_bar.set_playing(False)
        else:
            self.media_player.play()
            self.controls_bar.set_playing(True)

    def _restart_media(self) -> None:
        self.media_player.setPosition(0)

    def _set_media_position(self, position: int) -> None:
        self.media_player.setPosition(position)

    def _on_position_changed(self, position: int) -> None:
        self.controls_bar.update_position(position)
        self.controls_bar.update_time_label(position, self.media_player.duration())

    def _on_duration_changed(self, duration: int) -> None:
        self.controls_bar.update_duration(duration)
        self.controls_bar.update_time_label(
            self.controls_bar.current_position, duration
        )

    # ------------------------------------------------------------------
    # Volume / mute handlers
    # ------------------------------------------------------------------
    def _on_volume_changed(self, volume: float) -> None:
        self._audio_output.setVolume(volume)
        if volume > 0 and self._audio_output.isMuted():
            self._audio_output.setMuted(False)
            self.volume_bar.set_muted(False)

    def _toggle_mute(self) -> None:
        new_muted = not self._audio_output.isMuted()
        self._audio_output.setMuted(new_muted)
        self.volume_bar.set_muted(new_muted)