"""Output directory selection widget."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from config.config import DEFAULT_OUTPUT_DIR


class OutputDirWidget(QWidget):
    """Widget that lets the user choose an output directory.

    Signals
    -------
    output_directory(str)
        Emitted when the user selects a new directory.
    """

    output_directory = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._current_directory: str = DEFAULT_OUTPUT_DIR
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.select_button = QPushButton("Set Directory", self)
        self.select_button.clicked.connect(self._open_file_dialog)

        self.directory_label = QLabel(
            f"Current directory: {self._current_directory}"
        )

        layout = QHBoxLayout(self)
        layout.addWidget(self.select_button)
        layout.addWidget(self.directory_label)

    # ------------------------------------------------------------------
    # Internal handlers
    # ------------------------------------------------------------------
    def _open_file_dialog(self) -> None:
        dir_name = QFileDialog.getExistingDirectory(
            self,
            "Select a directory for output files",
            "",
        )
        if dir_name:
            self._current_directory = str(Path(dir_name).resolve())
            self.directory_label.setText(
                f"Current directory: {self._current_directory}"
            )
            self.output_directory.emit(self._current_directory)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @property
    def current_directory(self) -> str:
        """Return the currently selected output directory."""
        return self._current_directory