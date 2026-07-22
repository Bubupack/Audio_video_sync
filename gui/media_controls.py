"""Reusable media playback and volume control widgets.

These widgets are designed to be shared between the configuration-page
players (:class:`BaseMediaPlayerWidget` subclasses) and the final
visualization page (:class:`PageVisualization`), eliminating duplicated
control logic.
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QStyle,
    QVBoxLayout,
    QWidget,
)


class MediaControlsBar(QWidget):
    """Reusable playback controls: restart, play/pause, position slider, and time label.

    Signals
    -------
    play_toggled
        Emitted when the play/pause button is clicked.
    restart_requested
        Emitted when the restart button is clicked.
    position_seeked(int)
        Emitted when the user drags or clicks the position slider.
    """

    play_toggled = pyqtSignal()
    restart_requested = pyqtSignal()
    position_seeked = pyqtSignal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        # --- Restart button ---
        self.restart_button = QPushButton(self)
        self.restart_button.setIcon(
            self._std_icon(QStyle.StandardPixmap.SP_MediaSkipBackward)
        )
        self.restart_button.setEnabled(False)
        self.restart_button.clicked.connect(self.restart_requested.emit)

        # --- Play / Pause button ---
        self.play_button = QPushButton(self)
        self.play_button.setIcon(self._std_icon(QStyle.StandardPixmap.SP_MediaPlay))
        self.play_button.setEnabled(False)
        self.play_button.clicked.connect(self.play_toggled.emit)

        # --- Position slider ---
        self.position_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.position_slider.setRange(0, 0)
        self.position_slider.setEnabled(False)
        self.position_slider.valueChanged.connect(self.position_seeked.emit)

        # --- Time label (current / total) ---
        self.time_label = QLabel("00:00 / 00:00", self)

        # --- Slider row ---
        self._slider_row = QHBoxLayout()
        self._slider_row.addWidget(self.position_slider, stretch=1)
        self._slider_row.addWidget(self.time_label)

        # --- Buttons row (extra controls are appended here) ---
        self._buttons_row = QHBoxLayout()
        self._buttons_row.addWidget(self.restart_button)
        self._buttons_row.addWidget(self.play_button)

        # --- Main layout ---
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addLayout(self._slider_row)
        main_layout.addLayout(self._buttons_row)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def add_control(self, widget: QWidget, stretch: int = 0) -> None:
        """Append an extra control widget to the buttons row."""
        self._buttons_row.addWidget(widget, stretch=stretch)

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable all playback controls."""
        self.restart_button.setEnabled(enabled)
        self.play_button.setEnabled(enabled)
        self.position_slider.setEnabled(enabled)

    def set_playing(self, playing: bool) -> None:
        """Toggle the play/pause icon."""
        icon = (
            QStyle.StandardPixmap.SP_MediaPause
            if playing
            else QStyle.StandardPixmap.SP_MediaPlay
        )
        self.play_button.setIcon(self._std_icon(icon))

    def update_position(self, position: int) -> None:
        """Update the slider position without emitting ``position_seeked``."""
        self.position_slider.blockSignals(True)
        self.position_slider.setValue(position)
        self.position_slider.blockSignals(False)

    def update_duration(self, duration: int) -> None:
        """Set the slider range to ``[0, duration]``."""
        self.position_slider.setRange(0, duration)

    def update_time_label(self, position: int, duration: int) -> None:
        """Refresh the ``mm:ss / mm:ss`` time label."""
        self.time_label.setText(
            f"{self._format_time(position)} / {self._format_time(duration)}"
        )

    @property
    def current_position(self) -> int:
        """Return the current slider value (milliseconds)."""
        return self.position_slider.value()

    def reset(self) -> None:
        """Reset all controls to their initial (disabled) state."""
        self.position_slider.blockSignals(True)
        self.position_slider.setRange(0, 0)
        self.position_slider.setValue(0)
        self.position_slider.blockSignals(False)
        self.set_enabled(False)
        self.time_label.setText("00:00 / 00:00")
        self.set_playing(False)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _std_icon(self, pixmap: QStyle.StandardPixmap) -> QIcon:
        return self.style().standardIcon(pixmap)

    @staticmethod
    def _format_time(ms: int) -> str:
        """Convert milliseconds to a ``mm:ss`` string."""
        seconds = int(ms / 1000)
        minutes, secs = divmod(seconds, 60)
        return f"{minutes:02d}:{secs:02d}"


class VolumeControlsBar(QWidget):
    """Reusable horizontal volume control: mute toggle, volume slider, and label.

    Signals
    -------
    volume_changed(float)
        Emitted with a value in ``[0.0, 1.0]`` when the slider moves.
    mute_toggled
        Emitted when the mute button is clicked.
    """

    volume_changed = pyqtSignal(float)
    mute_toggled = pyqtSignal()

    DEFAULT_VOLUME_PERCENT = 70

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        # --- Mute toggle button ---
        self.mute_button = QPushButton(self)
        self.mute_button.setIcon(
            self._std_icon(QStyle.StandardPixmap.SP_MediaVolume)
        )
        self.mute_button.clicked.connect(self.mute_toggled.emit)

        # --- Volume slider ---
        self.volume_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(self.DEFAULT_VOLUME_PERCENT)
        self.volume_slider.valueChanged.connect(self._on_slider_changed)

        # --- Percentage label ---
        self.volume_label = QLabel(
            f"{self.DEFAULT_VOLUME_PERCENT} %", self
        )
        self.volume_label.setFixedWidth(40)

        # --- Layout ---
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.mute_button)
        layout.addWidget(self.volume_slider)
        layout.addWidget(self.volume_label)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the mute button and volume slider."""
        self.mute_button.setEnabled(enabled)
        self.volume_slider.setEnabled(enabled)

    def set_muted(self, muted: bool) -> None:
        """Update the mute icon to reflect the given mute state."""
        icon = (
            QStyle.StandardPixmap.SP_MediaVolumeMuted
            if muted
            else QStyle.StandardPixmap.SP_MediaVolume
        )
        self.mute_button.setIcon(self._std_icon(icon))

    @property
    def volume(self) -> float:
        """Return the current volume as a float in ``[0.0, 1.0]``."""
        return self.volume_slider.value() / 100.0

    def reset(self) -> None:
        """Reset volume controls to their default state."""
        self.volume_slider.blockSignals(True)
        self.volume_slider.setValue(self.DEFAULT_VOLUME_PERCENT)
        self.volume_slider.blockSignals(False)
        self.volume_label.setText(f"{self.DEFAULT_VOLUME_PERCENT} %")
        self.set_enabled(False)
        self.set_muted(False)

    # ------------------------------------------------------------------
    # Internal handlers
    # ------------------------------------------------------------------
    def _on_slider_changed(self, value: int) -> None:
        """Update the label and emit the normalised volume."""
        self.volume_label.setText(f"{value} %")
        self.volume_changed.emit(value / 100.0)

    def _std_icon(self, pixmap: QStyle.StandardPixmap) -> QIcon:
        return self.style().standardIcon(pixmap)