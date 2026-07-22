# gui/outputDir_widget.py
"""Output directory widget."""
from __future__ import annotations

from typing import Optional
from pathlib import Path
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget
from config.config import DEFAULT_OUTPUT_DIR
#button
class OutputDirWidget(QWidget):
    """Output directory widget."""

    output_directory = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.current_directory = DEFAULT_OUTPUT_DIR
        self.init_ui()
    
    def init_ui(self) -> None:
        """Initialize the UI components."""
        self.btn_open = QPushButton("Set Directory", self)
        self.btn_open.clicked.connect(self._open_file_dialog)

        self.directory_label = QLabel(f"Current directory: {self.current_directory}")

        self.main_layout = QHBoxLayout()
        self.main_layout.addWidget(self.btn_open)
        self.main_layout.addWidget(self.directory_label)

        self.setLayout(self.main_layout)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _open_file_dialog(self) -> None:
        dir_name = QFileDialog.getExistingDirectory(
            self,
            f"Select a directory for output files",
            "",
        )
        if dir_name:
            self.current_directory = str(Path(dir_name).resolve())
            self.directory_label.setText(f"Current directory: {self.current_directory}")
            self.output_directory.emit(self.current_directory)