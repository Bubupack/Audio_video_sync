"""Abstract base widget encapsulating shared media-player logic.

Subclasses must implement :meth:`_create_display_widget` and
:meth:`_configure_player`.  Optional hooks (:meth:`_extra_controls`,
:meth:`_on_media_loaded`, :meth:`_on_reset`) allow fine-grained
customisation.
"""
from __future__ import annotations

from abc import abstractmethod
from typing import List, Optional

from PyQt6.QtCore import QUrl, Qt, pyqtSignal
from PyQt6.QtGui import QResizeEvent
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtWidgets import (
    QFileDialog,
    QPushButton,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from gui.drop_zone import DropZone
from gui.media_controls import MediaControlsBar


class BaseMediaPlayerWidget(QWidget):
    """Common scaffolding for audio/video playback widgets.

    The widget displays a :class:`DropZone` until a file is loaded, then
    swaps to the subclass-provided display surface.  Playback controls
    (play / pause / restart / position slider / time label) are provided
    by a reusable :class:`MediaControlsBar`.
    """

    media_loaded = pyqtSignal(str)

    def __init__(self, media_type: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        if media_type not in ("audio", "video"):
            raise ValueError(f"Unsupported media type: {media_type!r}")

        self._media_type = media_type
        self._current_path: Optional[str] = None

        # --- Core Qt media player ---
        self.media_player = QMediaPlayer(self)

        # --- Drop zone (drag-and-drop file input) ---
        self.drop_zone = DropZone(media_type=media_type, parent=self)
        self.drop_zone.path.connect(self.load_media)

        # --- Display surface (provided by subclass) ---
        self.display_widget = self._create_display_widget()

        # --- Subclass-specific player configuration ---
        self._configure_player()

        # --- Reusable playback controls ---
        self.controls_bar = MediaControlsBar(self)
        self.controls_bar.play_toggled.connect(self.toggle_play)
        self.controls_bar.restart_requested.connect(self.restart_media)
        self.controls_bar.position_seeked.connect(self._set_media_position)

        # --- Player → controls synchronisation ---
        self.media_player.positionChanged.connect(self._on_position_changed)
        self.media_player.durationChanged.connect(self._on_duration_changed)
        self.media_player.mediaStatusChanged.connect(self._on_media_status_changed)

        self._build_ui()

    # ------------------------------------------------------------------
    # Hooks for subclasses
    # ------------------------------------------------------------------
    @abstractmethod
    def _create_display_widget(self) -> QWidget:
        """Return the widget used to display the media (video surface, cover art, …)."""

    def _configure_player(self) -> None:
        """Optional setup — e.g. attach audio/video output to the player."""

    def _extra_controls(self) -> List[QWidget]:
        """Return additional widgets to insert into the controls row."""
        return []

    def _on_media_loaded(self, file_path: str) -> None:
        """Hook called once a file has been loaded."""

    def _on_reset(self) -> None:
        """Hook called when the player is reset."""

    def _file_filter(self) -> str:
        """Return the file dialog filter for the current media type."""
        if self._media_type == "audio":
            return "Audio Files (*.mp3 *.wav *.flac *.aac)"
        return "Video Files (*.mp4 *.mkv *.avi *.mov)"

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        # --- Open-file button ---
        self.open_button = QPushButton("Open file", self)
        self.open_button.clicked.connect(self._open_file_dialog)

        # --- Insert subclass-provided extra controls ---
        for extra in self._extra_controls():
            self.controls_bar.add_control(extra, stretch=1)

        # --- Controls layout ---
        controls_layout = QVBoxLayout()
        controls_layout.addWidget(self.controls_bar)
        controls_layout.addWidget(self.open_button)
        controls_layout.addStretch(1)

        # --- Media container (stacked: drop zone ↔ display surface) ---
        self.media_container = QWidget(self)
        self.media_layout = QStackedLayout(self.media_container)
        self.media_layout.addWidget(self.drop_zone)
        self.media_layout.addWidget(self.display_widget)
        self.media_layout.setCurrentWidget(self.drop_zone)

        # --- Main layout ---
        self.main_layout = QVBoxLayout(self)
        self.main_layout.addWidget(self.media_container)
        self.main_layout.addLayout(controls_layout)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def load_media(self, file_path: str) -> None:
        """Load a media file, swap the display surface, and start playback."""
        self._current_path = file_path
        self.media_loaded.emit(file_path)

        # Swap drop zone → display surface
        self.media_layout.setCurrentWidget(self.display_widget)

        # Enable playback controls
        self.controls_bar.set_enabled(True)

        # Load and play
        self.media_player.setSource(QUrl.fromLocalFile(file_path))
        self._on_media_loaded(file_path)
        self.media_player.play()
        self.controls_bar.set_playing(True)

    def toggle_play(self) -> None:
        """Toggle between play and pause states."""
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

    def restart_media(self) -> None:
        """Seek to the beginning of the media and play if it was stopped."""
        self.media_player.setPosition(0)
        # If the video reached the end (StoppedState), restart playback automatically.
        if self.media_player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.play()
            self.controls_bar.set_playing(True)

    def reset(self) -> None:
        """Stop playback, unload media, and show the drop zone again."""
        # 1. Stop playback and clear the source
        self.media_player.stop()
        self.media_player.setSource(QUrl())
        self._current_path = None

        # 2. Reset drop zone and switch the stacked layout
        self.drop_zone.reset()
        self.media_layout.setCurrentWidget(self.drop_zone)

        # 3. Reset the controls bar
        self.controls_bar.reset()

        # 4. Subclass-specific reset
        self._on_reset()

    @property
    def current_path(self) -> Optional[str]:
        """Return the path of the currently loaded media file."""
        return self._current_path

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _on_media_status_changed(self, status: QMediaPlayer.MediaStatus) -> None:
        """Handle end-of-media to keep controls enabled and reset the play icon."""
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            # The video finished, but we want the user to be able to replay it.
            # We keep the controls enabled and show the "Play" icon.
            self.controls_bar.set_playing(False)

    def _open_file_dialog(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            f"Select a {self._media_type} file",
            "",
            self._file_filter(),
        )
        if file_name:
            self.load_media(file_name)

    def _on_position_changed(self, position: int) -> None:
        self.controls_bar.update_position(position)
        self.controls_bar.update_time_label(position, self.media_player.duration())

    def _on_duration_changed(self, duration: int) -> None:
        self.controls_bar.update_duration(duration)
        self.controls_bar.update_time_label(
            self.controls_bar.current_position, duration
        )

    def _set_media_position(self, position: int) -> None:
        self.media_player.setPosition(position)
        self.controls_bar.update_time_label(position, self.media_player.duration())

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------
    def resizeEvent(self, event: QResizeEvent) -> None:
        """Force the display area to a strict 16:9 aspect ratio."""
        super().resizeEvent(event)
        target_height = int(self.width() * 9 / 16)
        self.media_container.setFixedHeight(target_height)