"""Application entry point for the Audio-Video Sync tool."""
from __future__ import annotations

import logging
import sys

from PyQt6.QtWidgets import QApplication, QMessageBox

from gui.main_window import MainWindow
from utils.utils import is_ffmpeg_available

logger = logging.getLogger(__name__)

def configure_logging() -> None:
    """Configure structured logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

def verify_ffmpeg_dependency() -> bool:
    """Check for FFmpeg availability, log the result, and display a GUI error if missing.

    Returns:
        bool: True if FFmpeg is detected, False otherwise.
    """
    if is_ffmpeg_available():
        logger.info("FFmpeg dependency successfully detected in system PATH.")
        return True

    logger.error("FFmpeg executable not found in system PATH. Aborting startup.")

    error_box = QMessageBox()
    error_box.setIcon(QMessageBox.Icon.Critical)
    error_box.setWindowTitle("FFmpeg Missing")
    error_box.setText("FFmpeg executable was not found on your system.")
    error_box.setInformativeText(
        "Audio-Video Sync requires FFmpeg to process audio and video streams.\n\n"
        "Quick install commands:\n"
        " • Windows (PowerShell):   winget install ffmpeg\n"
        " • macOS (Terminal):       brew install ffmpeg\n"
        " • Linux (Ubuntu/Debian):  sudo apt install ffmpeg\n\n"
        "Please install FFmpeg and restart the application."
    )
    error_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    error_box.exec()

    return False

def main() -> None:
    """Launch the Audio-Video Sync application."""
    configure_logging()
    app = QApplication(sys.argv)

    if not verify_ffmpeg_dependency():
        sys.exit(1)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()