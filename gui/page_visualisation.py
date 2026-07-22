# gui/page_visualisation.py
from typing import Optional

from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
    QStyle,
    QVBoxLayout,
    QWidget,
)


class PageVisualisation(QWidget):
    """Page finale de prévisualisation de la vidéo resynchronisée."""

    sync_another_requested = pyqtSignal()  # Signal pour retourner à la configuration

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.video_path: Optional[str] = None

        # 1. Initialisation du lecteur multimédia et des sorties
        self.media_player = QMediaPlayer(self)

        self._audio_output = QAudioOutput(self)
        self._audio_output.setVolume(0.7)  # Volume par défaut à 70%
        self.media_player.setAudioOutput(self._audio_output)

        self.video_surface = QVideoWidget(self)
        # La vidéo prend le maximum d'espace disponible tout en préservant son ratio
        self.video_surface.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.media_player.setVideoOutput(self.video_surface)

        # 2. Synchronisation du lecteur vers l'interface
        self.media_player.positionChanged.connect(self._on_position_changed)
        self.media_player.durationChanged.connect(self._on_duration_changed)

        self._build_ui()

    def _build_ui(self) -> None:
        # --- Boutons & Sliders de contrôle ---
        self.btn_play = QPushButton(self)
        self.btn_play.setIcon(self._std_icon(QStyle.StandardPixmap.SP_MediaPlay))
        self.btn_play.clicked.connect(self._toggle_play)

        self.btn_restart = QPushButton(self)
        self.btn_restart.setIcon(
            self._std_icon(QStyle.StandardPixmap.SP_MediaSkipBackward)
        )
        self.btn_restart.clicked.connect(self._restart_media)

        # Barre de défilement temporel
        self.slider_playback = QSlider(Qt.Orientation.Horizontal, self)
        self.slider_playback.setRange(0, 0)
        self.slider_playback.valueChanged.connect(self._set_media_position)

        self.time_label = QLabel("00:00 / 00:00", self)

        # Contrôles de volume
        self.btn_mute = QPushButton(self)
        self.btn_mute.setIcon(self._std_icon(QStyle.StandardPixmap.SP_MediaVolume))
        self.btn_mute.clicked.connect(self._toggle_mute)

        self.slider_volume = QSlider(Qt.Orientation.Horizontal, self)
        self.slider_volume.setRange(0, 100)
        self.slider_volume.setValue(70)
        self.slider_volume.valueChanged.connect(self._change_volume)

        self.volume_label = QLabel("70 %", self)
        self.volume_label.setFixedWidth(40)

        # --- Layouts des contrôles ---
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(self.slider_playback, stretch=1)
        slider_layout.addWidget(self.time_label)

        controls_row = QHBoxLayout()
        controls_row.addWidget(self.btn_restart, stretch=2)
        controls_row.addWidget(self.btn_play, stretch=2)
        controls_row.addWidget(self.btn_mute, stretch=2)
        controls_row.addWidget(self.slider_volume, stretch=4)
        controls_row.addWidget(self.volume_label, stretch=1)

        # --- Information de sortie et bouton d'action ---
        self.lbl_output_path = QLabel("Fichier de sortie : Aucun", self)
        self.lbl_output_path.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_output_path.setWordWrap(True)
        self.lbl_output_path.setStyleSheet(
            "font-weight: bold; color: #DDDDDD; font-size: 13px;"
        )

        self.btn_sync_another = QPushButton("Synchroniser une autre vidéo", self)
        self.btn_sync_another.setStyleSheet(
            "padding: 8px 16px; font-weight: bold; font-size: 14px;"
        )
        self.btn_sync_another.clicked.connect(self.sync_another_requested.emit)

        # --- Layout Principal ---
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.video_surface, stretch=1)  # La vidéo prend tout l'espace disponible
        main_layout.addLayout(slider_layout)
        main_layout.addLayout(controls_row)
        main_layout.addSpacing(10)
        main_layout.addWidget(self.lbl_output_path)
        main_layout.addSpacing(10)
        main_layout.addWidget(
            self.btn_sync_another, alignment=Qt.AlignmentFlag.AlignCenter
        )

    # ------------------------------------------------------------------
    # API Publique
    # ------------------------------------------------------------------
    def set_video(self, video_path: str) -> None:
        """Charge et démarre la vidéo de sortie finale."""
        self.video_path = video_path
        self.lbl_output_path.setText(f"Fichier de sortie : {video_path}")
        self.media_player.setSource(QUrl.fromLocalFile(video_path))
        self.media_player.play()
        self._set_play_icon(playing=True)

    def reset_ui(self) -> None:
        """Arrête la lecture et réinitialise les contrôles."""
        self.media_player.stop()
        self.media_player.setSource(QUrl())
        self.video_path = None
        self.lbl_output_path.setText("Fichier de sortie : Aucun")

        self.slider_playback.blockSignals(True)
        self.slider_playback.setRange(0, 0)
        self.slider_playback.setValue(0)
        self.slider_playback.blockSignals(False)

        self.time_label.setText("00:00 / 00:00")
        self._set_play_icon(playing=False)

    # ------------------------------------------------------------------
    # Handlers & Helpers
    # ------------------------------------------------------------------
    def _toggle_play(self) -> None:
        is_playing = (
            self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        )
        if is_playing:
            self.media_player.pause()
            self._set_play_icon(playing=False)
        else:
            self.media_player.play()
            self._set_play_icon(playing=True)

    def _restart_media(self) -> None:
        self.media_player.setPosition(0)

    def _set_media_position(self, position: int) -> None:
        self.media_player.setPosition(position)

    def _toggle_mute(self) -> None:
        currently_muted = self._audio_output.isMuted()
        self._audio_output.setMuted(not currently_muted)
        self.btn_mute.setIcon(
            self._std_icon(
                QStyle.StandardPixmap.SP_MediaVolumeMuted
                if not currently_muted
                else QStyle.StandardPixmap.SP_MediaVolume
            )
        )

    def _change_volume(self, value: int) -> None:
        volume = value / 100.0
        self._audio_output.setVolume(volume)
        self.volume_label.setText(f"{value} %")

        if volume > 0 and self._audio_output.isMuted():
            self._audio_output.setMuted(False)
            self.btn_mute.setIcon(
                self._std_icon(QStyle.StandardPixmap.SP_MediaVolume)
            )

    def _on_position_changed(self, position: int) -> None:
        self.slider_playback.blockSignals(True)
        self.slider_playback.setValue(position)
        self.slider_playback.blockSignals(False)
        self._update_time_label(position, self.media_player.duration())

    def _on_duration_changed(self, duration: int) -> None:
        self.slider_playback.setRange(0, duration)
        self._update_time_label(self.slider_playback.value(), duration)

    def _update_time_label(self, position: int, duration: int) -> None:
        self.time_label.setText(
            f"{self._format_time(position)} / {self._format_time(duration)}"
        )

    def _set_play_icon(self, playing: bool) -> None:
        icon = (
            QStyle.StandardPixmap.SP_MediaPause
            if playing
            else QStyle.StandardPixmap.SP_MediaPlay
        )
        self.btn_play.setIcon(self._std_icon(icon))

    @staticmethod
    def _format_time(ms: int) -> str:
        seconds = int(ms / 1000)
        m, s = divmod(seconds, 60)
        return f"{m:02d}:{s:02d}"

    def _std_icon(self, pixmap: QStyle.StandardPixmap) -> QIcon:
        return self.style().standardIcon(pixmap)